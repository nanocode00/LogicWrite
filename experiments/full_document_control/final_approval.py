"""Evidence-bound final approval policy, with real issuance deliberately disabled.

A host-configured test source exercises the policy only. Caller/model JSON and
hashes cannot authenticate humans. No production identity or durable store exists
here; policy success NEVER authorizes delivery, stage transitions or file writes.
"""
import copy
import time

import expression
import final_semantic_validator as semantic
import final_validator

pipeline = expression.pipeline
REQUEST_VERSION = 'final-approval-request-v1'
RECORD_VERSION = 'final-approval-record-v1'
REPORT_VERSION = 'final-approval-policy-v1'
MAX_LIFETIME_SECONDS = 86400
MAX_VALIDATION_AGE_SECONDS = 900
# These two legacy notices describe absent stages, not unresolved document facts.
# Whole-output semantics are covered by the bound semantic report, while approval
# is evaluated separately here; neither upstream report is rewritten.
_STAGE_NOTICES = {'FINAL_SEMANTIC_REVIEW_NOT_IMPLEMENTED', 'FINAL_APPROVAL_NOT_IMPLEMENTED'}
_RECORD_FIELDS = {'version', 'approval_id', 'request_sha256', 'scope', 'actor', 'decision',
                  'reason', 'issued_at', 'expires_at', 'resolutions', 'record_sha256'}


def _snapshots(bundle, result, destinations):
    return [('source', snap) for snap in [bundle['document_snapshot'], *(destinations or [])]] + [
        ('output', snap) for snap in result.get('output_snapshots', [])]


def build_approval_request(bundle, analysis, org, preview, result, audit, *, destination_snapshots=None):
    """Bind actual bodies, fixed policy, complete scope and validation observations.

    This request is data, not proof that a validation or a human review occurred.
    The evaluator independently verifies the live final-audit receipt each time.
    """
    artifacts = {'bundle': bundle, 'writing_contract': bundle['writing_contract'],
                 'analysis': analysis, 'organization': org, 'expression': preview,
                 'candidate': result, 'destinations': destination_snapshots or [], 'final_audit': audit}
    hashes = {key: pipeline.canonical_json_digest(value) for key, value in artifacts.items()}
    structural = final_validator.validate_final_result(bundle, analysis, org, preview, result,
                                                      destination_snapshots=destination_snapshots)
    sem = audit.get('semantic_report', {})
    reviews = [{'item_id': 'semantic:' + check, 'kind': 'semantic', 'check_id': check,
                'status': sem.get('checks', {}).get(check, {}).get('status', 'unresolved')}
               for check in semantic.CHECKS]
    for index, finding in enumerate(structural['findings']):
        if finding['severity'] != 'ERROR' and finding['rule_id'] not in _STAGE_NOTICES:
            reviews.append({'item_id': 'structural:' + str(index) + ':' + pipeline.canonical_json_digest(finding),
                            'kind': 'structural', 'finding': copy.deepcopy(finding)})
    refs = [semantic._ref(side, snap) for side, snap in _snapshots(bundle, result, destination_snapshots)]
    scope = {'kind': 'complete_candidate_set', 'snapshot_refs': refs,
             'candidate_sha256': hashes['candidate'], 'contract_sha256': hashes['writing_contract']}
    request = {'version': REQUEST_VERSION, 'policy_version': REPORT_VERSION,
               'artifact_hashes': hashes, 'scope': scope,
               'validation': {'structural_report_sha256': structural['report_sha256'],
                   'structural': structural['gate_state'], 'structural_checks': structural['checks'],
                   'semantic_report_sha256': sem.get('report_sha256'),
                   'semantic': sem.get('overall_judgment', 'unresolved'),
                   'semantic_execution': sem.get('execution', {}).get('state'),
                   'execution_receipt_fresh': semantic.has_fresh_execution_receipt(sem, MAX_VALIDATION_AGE_SECONDS),
                   'audit_receipt_valid': semantic.verify_final_audit(bundle, analysis, org, preview, result,
                       audit, destination_snapshots=destination_snapshots)['valid']},
               'required_human_reviews': reviews, 'max_lifetime_seconds': MAX_LIFETIME_SECONDS,
               'max_validation_age_seconds': MAX_VALIDATION_AGE_SECONDS,
               'revalidation_conditions': ['any_artifact_or_policy_change', 'expired_or_revoked_decision',
                   'lost_or_invalid_validation_receipt', 'each_policy_evaluation'],
               'issuance_enabled': False}
    return expression.seal(request, 'request_sha256')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _authenticated_record(record, request, source, now, observation):
    if (not isinstance(record, dict) or set(record) != _RECORD_FIELDS
            or record['version'] != RECORD_VERSION or not _text(record['approval_id'])
            or record['request_sha256'] != request['request_sha256'] or record['scope'] != request['scope']
            or not expression.organization.verify_self_digest(record, 'record_sha256')[0]
            or not _text(record['reason']) or not isinstance(record['decision'], str)
            or record['decision'] not in {'approve', 'reject', 'hold'}
            or not isinstance(record['resolutions'], list)):
        return False
    # Caller data never registers evidence. Source is configured by the trusted
    # host, outside model input; only a test source is supported in this release.
    if source is None or source.mode != 'test_only' or not _text(source.source_id):
        return False
    stored = copy.deepcopy(source.lookup(record['approval_id']))
    if isinstance(stored, dict):
        observation.update({key: stored.get(key) for key in
            ('subject', 'issuer', 'actor_kind', 'revoked', 'revoked_at', 'revocation_reason')})
    if (not isinstance(stored, dict) or stored.get('revoked') is not False
            or stored.get('record') != record or stored.get('actor_kind') != 'human'
            or not _text(stored.get('subject')) or stored.get('issuer') != source.source_id
            or record['actor'] != {'subject': stored['subject'], 'issuer': stored['issuer'], 'kind': 'human'}):
        return False
    issued, expires = record['issued_at'], record['expires_at']
    return (type(issued) is int and type(expires) is int
            and issued <= now < expires and 0 < expires - issued <= MAX_LIFETIME_SECONDS)


def _unresolved(request, record, snapshots):
    required = {item['item_id']: item for item in request['required_human_reviews']}
    resolved = set()
    rows = record['resolutions']
    ids = [row.get('item_id') if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(key, str) or key not in required for key in ids) or len(set(ids)) != len(ids):
        return list(required.values())
    for row in rows:
        if (set(row) == {'item_id', 'judgment', 'reason', 'evidence'}
                and row['judgment'] == 'accepted' and _text(row['reason'])
                and isinstance(row['evidence'], list) and row['evidence']
                and all(semantic._valid_span(span, snapshots) for span in row['evidence'])
                and {key for key, snap in snapshots.items() if snap['content']}.issubset(
                    {(span['side'], span['document_id']) for span in row['evidence']})):
            resolved.add(row['item_id'])
    return [item for key, item in required.items() if key not in resolved]


def evaluate_final_approval(bundle, analysis, org, preview, result, audit, decision_record=None, *,
                            destination_snapshots=None, evidence_source=None):
    """Verify current validation and an explicit human decision; fail closed.

    `evidence_source` is trusted HOST configuration, never a model/caller record
    field. Only test-only lookup adapters are accepted. No approval issuer or
    persistence/authentication implementation is included. Re-evaluate before use;
    exported report JSON is an audit observation, never reusable authorization.
    """
    report = {'version': REPORT_VERSION, 'policy_state': 'INVALID', 'gate_state': 'REVIEW',
              'issuance_enabled': False, 'trust_mode': 'unconfigured', 'approval_evidence_valid': False,
              'delivery_approved': False, 'stage_transition_allowed': False,
              'request': None, 'decision_record': None, 'evidence_observation': {},
              'unresolved_items': [], 'findings': []}
    def finish(state, reason):
        report['policy_state'] = state
        report['findings'].append({'rule_id': reason})
        return expression.seal(report, 'report_sha256')
    try:
        # Snapshot caller data: a trusted-source callback must not race mutations
        # into a successful result. A second live check runs after the lookup.
        report['decision_record'] = copy.deepcopy(decision_record)
        request = build_approval_request(bundle, analysis, org, preview, result, audit,
                                         destination_snapshots=destination_snapshots)
        report['request'] = request
        report['unresolved_items'] = copy.deepcopy(request['required_human_reviews'])
        if (not request['validation']['audit_receipt_valid']
                or not request['validation']['execution_receipt_fresh']):
            return finish('INVALID', 'VALIDATION_EVIDENCE_INVALID_OR_LOST')
        if (request['validation']['structural'] == 'FAIL'
                or any(row['status'] == 'violated' for row in audit['semantic_report']['checks'].values())):
            report['gate_state'] = 'FAIL'
            return finish('BLOCKED', 'CONFIRMED_VALIDATION_VIOLATION')
        if result.get('delivery_state') != 'candidate' or not result.get('output_snapshots'):
            return finish('HOLD', 'COMPLETE_CANDIDATE_REQUIRED')
        if decision_record is None:
            return finish('UNAPPROVED', 'EXPLICIT_HUMAN_DECISION_REQUIRED')
        if not _authenticated_record(report['decision_record'], request, evidence_source, time.time(),
                                     report['evidence_observation']):
            return finish('INVALID', 'UNTRUSTED_STALE_REVOKED_OR_MALFORMED_DECISION')
        # Repeat both body binding and receipt verification after external lookup.
        current = build_approval_request(bundle, analysis, org, preview, result, audit,
                                         destination_snapshots=destination_snapshots)
        if current != request or not current['validation']['audit_receipt_valid']:
            return finish('INVALID', 'INPUT_OR_VALIDATION_CHANGED_DURING_APPROVAL')
        # Fresh expiry/revocation observation after lookup, with no second callback.
        if not report['decision_record']['issued_at'] <= time.time() < report['decision_record']['expires_at']:
            return finish('INVALID', 'DECISION_EXPIRED_DURING_VERIFICATION')
        report['trust_mode'] = 'test_only'
        report['approval_evidence_valid'] = True
        record = report['decision_record']
        snapshots = {(side, snap['document_id']): snap for side, snap in
                     _snapshots(bundle, result, destination_snapshots)}
        report['unresolved_items'] = _unresolved(request, record, snapshots)
        if record['decision'] == 'reject':
            return finish('REJECTED', 'EXPLICIT_HUMAN_REJECTION')
        if record['decision'] == 'hold':
            return finish('HOLD', 'EXPLICIT_HUMAN_HOLD')
        if audit['semantic_report']['execution']['state'] not in {'not_run', 'completed'}:
            return finish('HOLD', 'VALIDATION_EXECUTION_REQUIRES_RERUN')
        if report['unresolved_items']:
            return finish('HOLD', 'EVIDENCED_HUMAN_REVIEW_INCOMPLETE')
        return finish('APPROVED', 'TEST_POLICY_SATISFIED_REAL_ISSUANCE_DISABLED')
    except Exception:
        # Authority errors may include secrets. No exception text is exported.
        report['approval_evidence_valid'] = False
        return finish('INVALID', 'APPROVAL_VERIFICATION_FAILED')


def verify_approval_report(bundle, analysis, org, preview, result, audit, report, **kwargs):
    """Re-evaluate a policy observation against current receipts and source state.

    `valid` describes current evidence for this exact observation, including a
    rejection/hold. It never grants issuance or delivery. Self-hashes alone cannot
    authenticate an exported report.
    """
    try:
        current = evaluate_final_approval(bundle, analysis, org, preview, result, audit,
                                         report['decision_record'], **kwargs)
        valid = (current['approval_evidence_valid'] and current == report
                 and expression.organization.verify_self_digest(report, 'report_sha256')[0])
    except Exception:
        valid = False
    return {'valid': bool(valid), 'issuance_enabled': False, 'delivery_approved': False,
            'stage_transition_allowed': False,
            'reason': None if valid else 'FORGED_STALE_OR_UNVERIFIABLE_APPROVAL_REPORT'}

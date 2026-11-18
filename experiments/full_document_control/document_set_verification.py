"""Independent post-output checks for pinned G1/G2 document sets.

Pins and reviewer identities belong to the host. A digest binds a snapshot
and does not authenticate its author. Reports and HITL records grant no writes.
"""
import copy
import re

import document_set as core
import document_set_reconstruction as reconstruction
import document_set_final_validator as structure
from document_set_final_validator import candidate_row
from pipeline import parse_markdown_blocks

VERSION = 'document-set-verification-v1'
REQUIREMENTS = 'document-set-requirements-v1'
MODES = {'g2c', 'external_shadow'}
ERRORS = (ValueError, TypeError, KeyError, AttributeError, OverflowError)
HTML_COMMENT = re.compile(r'<!--.*?(?:-->|$)', re.DOTALL)
PRESENTATION_TAG = re.compile(r'</?(?:em|strong|b|i|u|span|mark|br)\s*/?>', re.IGNORECASE)
PROSE_BLOCKS = {'paragraph', 'heading', 'list', 'blockquote', 'table'}
TOKEN = re.compile(r'[^\W_]+', re.UNICODE)
PREREQUISITE_DECISIONS = {
    'EXPLICIT_STRUCTURE_PROHIBITION_REQUIRES_REVIEW': 'Confirm whether the proposed layout change is permitted by the explicit constraint.',
    'LOCAL_SOURCE_CONTEXT_UNRESOLVED': 'Confirm the missing document authority or source context.',
    'PLACEMENT_SECTION_CHANGE_UNRESOLVED': 'Confirm whether the proposed placement preserves the section scope.',
    'MOVE_SECTION_CONTEXT_UNRESOLVED': 'Confirm whether the proposed move preserves source and destination section scope.',
    'CONTEXT_DEPENDENCE_REVIEW_REQUIRED': 'Determine which conditions and references must move with the passage.',
    'MOVE_WOULD_EMPTY_SOURCE_DOCUMENT': 'Decide whether the original document must retain the passage.',
}


class _Rejected(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise _Rejected(reason)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _ids(values, known):
    return isinstance(values, list) and all(_text(v) and v in known for v in values) and len(set(values)) == len(values)


def _span(side, doc, start=0, end=None):
    text = doc['content']
    end = len(text) if end is None else end
    span = dict(side=side, document_id=doc['document_id'], snapshot_sha256=doc['sha256'],
                start=start, end=end, byte_start=len(text[:start].encode('utf-8')),
                byte_end=len(text[:end].encode('utf-8')), quote=text[start:end])
    if side == 'source':
        span.update(provenance=doc['provenance'], source_scope=doc['source_scope'],
                    authority=doc['authority'], role=doc['role'])
    return span


def _exact_line(doc, quote):
    # Match complete lines so extra negation, changed precision, dates or
    # split conditions cannot pass as substrings.
    matches = list(re.finditer(r'(?m)^' + re.escape(quote) + r'(?=\r?$)', doc['content']))
    if not matches:
        return None, False
    blocks = parse_markdown_blocks(dict(doc, snapshot_id=doc['document_id'] + ':candidate'))
    comments = [m.span() for m in HTML_COMMENT.finditer(doc['content'])]
    for match in matches:
        start, end = match.span()
        if (not any(left < end and start < right for left, right in comments)
                and any(block['kind'] in PROSE_BLOCKS and block['start'] <= start < end <= block['end']
                        for block in blocks)):
            return _span('candidate', doc, start, end), True
    return _span('candidate', doc, *matches[0].span()), False


def _source_ref(ref, sources):
    doc = sources[ref['document_id']]
    quote = ref['quote']
    _require(_text(quote), 'EMPTY_SOURCE_QUOTE')
    start = ref.get('start')
    if start is None:
        start = doc['content'].find(quote)
        _require(start >= 0 and doc['content'].find(quote, start + 1) < 0, 'AMBIGUOUS_SOURCE_QUOTE')
    _require(type(start) is int and start >= 0 and doc['content'][start:start + len(quote)] == quote,
             'SOURCE_QUOTE_MISMATCH')
    return _span('source', doc, start, start + len(quote))


def _read_requirements(requirements, sources, outputs, tasks):
    _require(set(requirements) == {'version', 'obligations', 'format_policies'}
             and requirements['version'] == REQUIREMENTS
             and isinstance(requirements['obligations'], list)
             and isinstance(requirements['format_policies'], dict), 'INVALID_REQUIREMENTS')
    obligations = {}
    for row in requirements['obligations']:
        cid = row['check_id']
        _require(_text(cid) and ':' not in cid and cid not in obligations
                 and cid not in {'coverage', 'lineage', 'semantic_coverage', 'formatting'}
                 and row['kind'] in {'exact_line', 'semantic', 'policy_relation'}
                 and _ids(row['document_ids'], outputs) and _ids(row['task_ids'], tasks)
                 and (row['document_ids'] or row['kind'] == 'policy_relation')
                 and _text(row['decision_owner']) and _text(row['decision_needed'])
                 and isinstance(row['source_refs'], list) and row['source_refs'], 'INVALID_OBLIGATION')
        evidence = [_source_ref(ref, sources) for ref in row['source_refs']]
        for ref in row['source_refs']:
            context = ref.get('context', {})
            _require(isinstance(context, dict) and set(context) <= {'date', 'applicability'}
                     and all(_text(value) for value in context.values()), 'INVALID_SOURCE_CONTEXT')
        _require(row['kind'] != 'policy_relation' or len({s['document_id'] for s in evidence}) >= 2,
                 'TWO_POLICY_SOURCES_REQUIRED')
        obligations[cid] = (row, evidence)
    for did, policy in requirements['format_policies'].items():
        _require(did in outputs and sources[did]['access'] == 'format_only'
                 and set(policy) == {'kind', 'source_sha256', 'candidate_sha256', 'basis', 'issuer'}
                 and policy['kind'] == 'reviewed_whitespace'
                 and policy['source_sha256'] == sources[did]['sha256']
                 and _text(policy['candidate_sha256']) and _text(policy['basis'])
                 and _text(policy['issuer']), 'INVALID_FORMAT_POLICY')
    return obligations


def _load_candidates(result, sources):
    _require(isinstance(result['candidates'], list), 'INVALID_CANDIDATE_LIST')
    candidates, duplicates = {}, set()
    for row in result['candidates']:
        _require(isinstance(row, dict) and set(row) == {'document_id', 'content', 'sha256', 'source_sha256', 'source_path'}
                 and all(isinstance(v, str) for v in row.values()) and _text(row['document_id']),
                 'INVALID_CANDIDATE_ROW')
        did = row['document_id']
        _require(core._digest(row['content']) == row['sha256'], 'CANDIDATE_CONTENT_HASH_MISMATCH')
        if did in sources:
            _require(row == candidate_row(sources[did], row['content']), 'CANDIDATE_SOURCE_BINDING_MISMATCH')
        if did in candidates:
            duplicates.add(did)
        else:
            candidates[did] = row
    return candidates, duplicates


def _effects(tasks, units):
    reads, writes = {}, {}
    for tid, task in tasks.items():
        read = {e['document_id'] for e in task['source_evidence']}
        write = {units[u]['document_id'] for u in task['unit_ids'] if u in units}
        if task['target_document_id'] is not None:
            write.add(task['target_document_id'])
        reads[tid] = read | write
        writes[tid] = set() if task['action'] == 'KEEP' else write
    return reads, writes


def _scoped_native_lineage(bound, states, result, outputs):
    # When a global audit fails, localize it with the same trusted layout, but
    # compare actual bytes separately from the candidate-supplied trace.
    docs, scopes, _, units, blocks = bound
    order = structure._physical_order(blocks, scopes, reconstruction._operations(bound, states))
    context = (docs, {(u['document_id'], u['block_id']): uid for uid, u in units.items()})
    trace = result.get('trace')
    grouped = {did: [] for did in scopes}
    trace_identifiable = isinstance(trace, list)
    if trace_identifiable:
        for row in trace:
            try:
                grouped[row['output']['document_id']].append(row)
            except (TypeError, KeyError):
                trace_identifiable = False
    status = {}
    for did in scopes.keys() & outputs.keys():
        candidate = outputs[did]
        if not structure._check_document(candidate, docs[did], order[did], None, context):
            status[did] = 'violated'
        else:
            rows = iter(grouped[did])
            valid = trace_identifiable and structure._check_document(candidate, docs[did], order[did], rows, context)
            status[did] = 'passed' if valid and next(rows, None) is None else 'unresolved'
    return status, {did for did in status if status[did] != 'passed'}


def _authority(source, output, scope, allowed, mode, native_scope, policy):
    if source is None or source['access'] == 'read_only':
        return 'violated', 'UNAUTHORIZED_OUTPUT'
    if source['access'] == 'pending':
        return 'unresolved', 'PENDING_WRITE_AUTHORITY'
    if not scope:
        return 'violated', 'UNAUTHORIZED_OUTPUT'
    if output['content'] == source['content']:
        return 'passed', 'UNCHANGED'
    pending = source['authority'] is None or source['role'] is None or bool(source['pending_questions'])
    if source['access'] == 'format_only':
        before, after = source['content'], output['content']
        same_nonspace = re.sub(r'\s+', '', before) == re.sub(r'\s+', '', after)
        before_tokens = TOKEN.findall(PRESENTATION_TAG.sub('', before))
        after_tokens = TOKEN.findall(PRESENTATION_TAG.sub('', after))
        if not same_nonspace and before_tokens != after_tokens:
            return 'violated', 'FORMAT_LEXICAL_CHANGE'
        if pending:
            return 'unresolved', 'PENDING_WRITE_AUTHORITY'
        if (policy and policy['candidate_sha256'] == output['sha256']
                and before.split() == after.split()):
            return 'passed', 'INDEPENDENT_WHITESPACE_POLICY_MATCH'
        return 'unresolved', 'FORMAT_TRANSFORMATION_NEEDS_POLICY_AND_EVIDENCE'
    if pending:
        return 'unresolved', 'PENDING_WRITE_AUTHORITY'
    if not allowed:
        return 'violated', 'NO_ELIGIBLE_GRANTED_WRITE_TASK'
    if mode == 'external_shadow':
        return 'unresolved', 'EXTERNAL_WRITE_SCOPE_UNVERIFIED'
    if native_scope == 'violated':
        return 'violated', 'CONTENT_OUTSIDE_PLANNED_LAYOUT'
    if native_scope != 'passed':
        return 'unresolved', 'CHANGED_OUTPUT_TRACE_UNVERIFIED'
    return 'passed', 'PINNED_TASK_AND_TRACE_SUPPORT_WRITE'


def _check(status, reason, docs, evidence=(), tasks=(), *, kind='mechanical'):
    return dict(status=status, reason=reason, document_ids=sorted(set(docs)),
                evidence=list(evidence), task_ids=sorted(set(tasks)), kind=kind)


def _obligation(row, evidence, outputs):
    targets = row['document_ids']
    missing = []
    found = []
    unclear = []
    for did in targets:
        candidate = outputs.get(did)
        if row['kind'] == 'exact_line':
            for ref in evidence:
                match, prose = _exact_line(candidate, ref['quote']) if candidate else (None, False)
                if match:
                    found.append(match)
                    if not prose:
                        unclear.append(match)
                else:
                    missing.append(dict(document_id=did, required_quote=ref['quote']))
        if candidate and (row['kind'] != 'exact_line' or any(m['document_id'] == did for m in missing)):
            found.append(_span('candidate', candidate))
    if row['kind'] != 'exact_line':
        status, reason = 'unresolved', 'INDEPENDENT_MEANING_REVIEW_REQUIRED'
    elif missing:
        status, reason = 'violated', 'REQUIRED_EXACT_EXPOSURE_MISSING'
    elif unclear:
        status, reason = 'unresolved', 'EXACT_TEXT_FOUND_WITH_UNVERIFIED_PROSE_EXPOSURE'
    else:
        status, reason = 'passed', 'REQUIRED_EXACT_EXPOSURE_PRESENT'
    return dict(_check(status, reason, targets, evidence + found, row['task_ids'],
                       kind='mechanical' if row['kind'] == 'exact_line' else 'semantic'),
                missing=missing, unclear_exposure=unclear,
                source_context=[dict(document_id=ref['document_id'], quote=ref['quote'], **ref['context'])
                                for ref in row['source_refs'] if ref.get('context')])


def _semantic_reviews(checks, review, pin, bindings, obligations, sources, outputs):
    if review is None:
        _require(pin is None, 'MISSING_PINNED_REVIEW')
        return 'not_run'
    _require(pin == core.contract_digest(review) and set(review) == {'bindings', 'reviewer_id', 'reviews'}
             and review['bindings'] == bindings and _text(review['reviewer_id'])
             and isinstance(review['reviews'], dict) and review['reviews'].keys() <= obligations.keys(),
             'INDEPENDENT_REVIEW_BINDING_REJECTED')
    for cid, row in review['reviews'].items():
        check = checks[cid]
        obligation, required = obligations[cid]
        _require(check['kind'] == 'semantic' and row['status'] in {'passed', 'violated', 'unresolved'}
                 and _text(row['reason']) and isinstance(row['evidence'], list), 'INVALID_INDEPENDENT_REVIEW')
        cited = []
        for evidence in row['evidence']:
            did, side = evidence['document_id'], evidence['side']
            _require(side in {'source', 'candidate'}, 'INVALID_REVIEW_SIDE')
            doc = (sources if side == 'source' else outputs)[did]
            start, end = evidence['start'], evidence['end']
            _require(type(start) is int and type(end) is int and ((0 <= start < end <= len(doc['content'])) or start == end == 0 and not doc['content'])
                     and evidence == _span(side, doc, start, end), 'INVALID_REVIEW_CITATION')
            cited.append(evidence)
        if row['status'] != 'unresolved':
            _require(all(any(c['side'] == 'source' and c['document_id'] == s['document_id']
                             and c['start'] <= s['start'] and c['end'] >= s['end'] for c in cited)
                         for s in required)
                     and set(obligation['document_ids']) <= {c['document_id'] for c in cited if c['side'] == 'candidate'},
                     'INCOMPLETE_REVIEW_EVIDENCE')
        check.update(status=row['status'], reason=row['reason'], independent_evidence=cited,
                     reviewer_id=review['reviewer_id'])
    return 'bound' if review['reviews'] else 'empty'


def _self_checks(result, checks):
    authority = [cid for cid in checks if cid.startswith('authority:')]
    obligation = [cid for cid in checks if 'missing' in checks[cid]]
    mappings = {
        'within_authority': ['coverage', *authority],
        'completeness_verified': ['coverage', *obligation, 'semantic_coverage'],
        'constraints_compliance': ['coverage', *authority, *obligation, 'semantic_coverage'],
        'cross_document_consistency': [cid for cid in obligation if checks[cid].get('obligation_kind') == 'policy_relation']
        + ['semantic_coverage'],
    }
    claims = []
    for field in ('final_checks', 'self_review', 'within_authority'):
        if field not in result:
            continue
        values = result[field]
        rows = values.items() if isinstance(values, dict) else [(field, values)]
        for name, claim in rows:
            linked = mappings.get(name, [name] if name in checks else [])
            statuses = {checks[cid]['status'] for cid in linked}
            status = 'unresolved'
            reason = 'CLAIM_NOT_MAPPED_OR_NOT_MACHINE_READABLE'
            if claim is True or (isinstance(claim, str) and claim.lower() in {'passed', 'pass', 'supported'}):
                if 'violated' in statuses:
                    status, reason = 'violated', 'SUCCESS_CLAIM_CONTRADICTED'
                elif statuses == {'passed'}:
                    status, reason = 'passed', 'SUCCESS_CLAIM_SUPPORTED'
                else:
                    reason = 'SUCCESS_CLAIM_HAS_UNRESOLVED_OR_MISSING_EVIDENCE'
            claims.append(dict(field=field, claim_id=name, claim=claim, check_ids=linked,
                               status=status, reason=reason))
    return claims


def _propagate(seeds, tasks):
    held = set(seeds)
    while True:
        added = {tid for tid, task in tasks.items() if set(task['depends_on']) & held} - held
        if not added:
            return held
        held.update(added)


def _impact(checks, obligations, plan, tasks, reads, changed, native_states, outputs):
    held = {tid for tid, task in tasks.items() if task['status'] != 'eligible'}
    held.update(tid for tid, (state, _) in native_states.items() if state not in {'ready', 'preserved'})
    questions = []
    for row in plan['hitl_questions']:
        affected = _propagate(row['dependent_task_ids'], tasks)
        held.update(affected)
        docs = set(row['document_ids']) | {e['document_id'] for e in row['evidence']}
        questions.append(dict(row, origin='g2_plan', check_id=None, upstream_question_id=row['question_id'],
                              question_id='g2:' + row['question_id'], held_task_ids=sorted(affected),
                              candidate_evidence=[_span('candidate', outputs[d]) for d in sorted(docs & outputs.keys())]))
    for cid, check in checks.items():
        if (check['status'] == 'passed' or cid == 'semantic_coverage'
                or check['reason'] == 'EXTERNAL_CANDIDATE_HAS_NO_G2C_EXECUTION_LINEAGE'):
            continue
        docs = set(check['document_ids'])
        if cid in obligations:
            obligation, evidence = obligations[cid]
            if obligation['kind'] == 'policy_relation':
                docs.update(e['document_id'] for e in evidence)
        # No task read/write scope means independence is unknown. G2 has
        # explicit document evidence even for KEEP tasks; decomposition is held.
        seeds = set(check['task_ids'])
        seeds.update(tid for tid, scope in reads.items() if scope & docs or not scope)
        affected = _propagate(seeds, tasks)
        check['task_ids'] = sorted(affected)
        held.update(affected)
        requires_decision = (check['status'] == 'unresolved' and (
            cid in obligations or check['reason'] in PREREQUISITE_DECISIONS or check['reason'] in {'PENDING_WRITE_AUTHORITY',
            'FORMAT_TRANSFORMATION_NEEDS_POLICY_AND_EVIDENCE'}))
        if requires_decision:
            owner = obligations[cid][0]['decision_owner'] if cid in obligations else 'Document authority owner'
            decision = (obligations[cid][0]['decision_needed'] if cid in obligations
                        else PREREQUISITE_DECISIONS.get(
                            check['reason'], 'Confirm permitted changes and supply independent evidence for the affected document'))
            questions.append(dict(question_id='g3:' + cid, check_id=cid, origin='g3_verification',
                                  status='unresolved', document_ids=sorted(docs),
                                  evidence=check['evidence'], source_context=check.get('source_context', []),
                                  decision_owner=owner,
                                  question=decision, decision_needed=decision,
                                  held_task_ids=sorted(affected)))
    held = _propagate(held, tasks)
    independent = sorted(tasks.keys() - held)
    for question in questions:
        question['independent_task_ids'] = independent
    return dict(held_task_ids=sorted(held), independent_task_ids=independent, changed_document_ids=sorted(changed),
                native_task_states={tid: dict(state=state, reasons=reasons)
                                    for tid, (state, reasons) in native_states.items()}), questions


def verify_document_set(result, requirements, *, contract, analysis, plan, plan_request,
                        candidate_request, trusted_contract_sha256, trusted_request_sha256,
                        trusted_candidate_request_sha256, trusted_requirements_sha256,
                        trusted_candidate_sha256, mode='g2c', independent_review=None,
                        trusted_review_sha256=None):
    """Verify full candidate snapshots; mode is host-selected, never inferred.

    `accepted` means input bindings were authenticated by caller pins. Check
    verdicts are separate. Missing independent evidence leaves REVIEW.
    """
    report = dict(version=VERSION, gate_state='REVIEW', semantic_judgment='unresolved',
                  delivery_approved=False, stage_transition_allowed=False, accepted=False,
                  bindings=None, checks={}, self_checks=[], hitl_questions=[], impact=None,
                  execution=dict(state='rejected', semantic_review='not_run', model_calls=0),
                  reasons=[])
    try:
        (result, requirements, contract, analysis, plan, plan_request, candidate_request,
         independent_review) = copy.deepcopy((result, requirements, contract, analysis, plan,
                                             plan_request, candidate_request, independent_review))
        _require(mode in MODES and core.contract_digest(result) == trusted_candidate_sha256
                 and core.contract_digest(requirements) == trusted_requirements_sha256,
                 'EXTERNAL_PIN_MISMATCH')
        pins = dict(trusted_contract_sha256=trusted_contract_sha256, trusted_request_sha256=trusted_request_sha256,
                    trusted_candidate_request_sha256=trusted_candidate_request_sha256)
        bound = reconstruction._bind(
            contract, analysis, plan, plan_request, candidate_request, **pins)
        sources, scopes, tasks, units, _ = bound
        obligations = _read_requirements(requirements, sources, scopes, tasks)
        outputs, duplicates = _load_candidates(result, sources)
        bindings = dict(mode=mode, contract_sha256=trusted_contract_sha256,
                        analysis_sha256=plan['analysis_sha256'], plan_sha256=plan['plan_sha256'],
                        request_sha256=trusted_request_sha256, candidate_request_sha256=trusted_candidate_request_sha256,
                        verifier_version=VERSION, requirements_sha256=trusted_requirements_sha256, candidate_sha256=trusted_candidate_sha256)
        missing = scopes.keys() - outputs.keys()
        extra = outputs.keys() - scopes.keys()
        bad_coverage = missing | extra | duplicates
        changed = {did for did in outputs if did not in sources or outputs[did]['content'] != sources[did]['content']}
        reads, writes = _effects(tasks, units)
        checks = {'coverage': dict(_check('violated' if bad_coverage else 'passed',
                                        'OUTPUT_SET_MISMATCH' if bad_coverage else 'OUTPUT_SET_MATCHES_CONTRACT',
                                        bad_coverage or scopes.keys(),
                                        [_span('source', sources[d]) for d in sorted(missing)]
                                        + [_span('candidate', outputs[d]) for d in sorted(extra | duplicates)]),
                                   missing_document_ids=sorted(missing), extra_document_ids=sorted(extra),
                                   duplicate_document_ids=sorted(duplicates))}
        audits = {}
        scoped_native = {}
        native_states = {}
        if mode == 'g2c':
            # Reuse the deterministic layout/partition checker as supplemental
            # evidence. Discard embedded verdicts and separate generator claims.
            native = {k: v for k, v in result.items()
                      if k not in {'final_checks', 'self_review', 'within_authority'}}
            native['structure'] = None
            audits = reconstruction.validate_candidate_result(native, contract, analysis, plan, plan_request,
                                                                 candidate_request, **pins)
            native_states = reconstruction._decisions(bound, candidate_request)
            native_passed = audits['status'] == 'passed'
            if native_passed:
                scoped_native = dict.fromkeys(scopes, 'passed')
                affected = set()
            else:
                scoped_native, affected = _scoped_native_lineage(bound, native_states, result, outputs)
                affected = affected or bad_coverage or changed or scopes.keys()
            checks['lineage'] = _check('passed' if native_passed else 'violated',
                                       'LAYOUT_TRACE_BOUND' if native_passed else 'LAYOUT_TRACE_OR_LEDGER_INVALID',
                                       affected or scopes.keys(),
                                       [_span('candidate', outputs[d]) for d in sorted(affected & outputs.keys())])
        else:
            checks['lineage'] = _check('unresolved', 'EXTERNAL_CANDIDATE_HAS_NO_G2C_EXECUTION_LINEAGE', changed,
                                       kind='provenance')
        granted = set(candidate_request['task_ids'])
        for did, output in outputs.items():
            source = sources.get(did)
            allowed = {tid for tid, docs in writes.items() if did in candidate_request['document_ids']
                       and tid in granted and did in docs and tasks[tid]['status'] == 'eligible'
                       and (mode != 'g2c' or native_states[tid][0] == 'ready')}
            policy = requirements['format_policies'].get(did)
            status, reason = _authority(source, output, did in scopes, allowed, mode, scoped_native.get(did), policy)
            evidence = [_span('source', source)] if source else []
            evidence.append(_span('candidate', output))
            checks['authority:' + did] = _check(status, reason, {did}, evidence, allowed)
            if reason == 'INDEPENDENT_WHITESPACE_POLICY_MATCH':
                checks['authority:' + did]['format_policy'] = policy
        for did, source in sources.items():
            if source['access'] == 'read_only' and did not in outputs:
                checks['authority:' + did] = _check('passed', 'REFERENCE_NOT_PROMOTED_TO_OUTPUT',
                                                      {did}, [_span('source', source)])
        for cid, (row, evidence) in obligations.items():
            checks[cid] = dict(_obligation(row, evidence, outputs), obligation_kind=row['kind'])
        for tid, (state, reasons) in native_states.items():
            if state != 'held' or tasks[tid]['required_hitl_question_ids']:
                continue
            for reason in reasons:
                if reason in PREREQUISITE_DECISIONS:
                    evidence = [_span('source', sources[d]) for d in sorted(reads[tid])]
                    evidence += [_span('candidate', outputs[d]) for d in sorted(reads[tid] & outputs.keys())]
                    checks['prerequisite:' + tid] = _check('unresolved', reason, reads[tid], evidence, [tid],
                                                           kind='authorization')
                    break
        checks['semantic_coverage'] = _check('unresolved', 'GENERAL_SEMANTIC_COVERAGE_NOT_ESTABLISHED',
                                             changed, kind='semantic')
        reviewed = _semantic_reviews(checks, independent_review, trusted_review_sha256, bindings,
                                     obligations, sources, outputs)
        impact, questions = _impact(checks, obligations, plan, tasks, reads, changed, native_states, outputs)
        report.update(accepted=True, bindings=dict(bindings, independent_review_sha256=trusted_review_sha256),
                      checks=checks, self_checks=_self_checks(result, checks), hitl_questions=questions,
                      impact=impact, execution=dict(state='completed', semantic_review=reviewed, model_calls=0,
                                                     supplemental_structure=audits))
    except _Rejected as exc:
        report['reasons'].append(str(exc))
    except ERRORS as exc:
        report['reasons'].append(reconstruction.validation.binding_error(exc))
    report['report_sha256'] = core.contract_digest(report)
    return report


def is_current_report(report, result, requirements, **inputs):
    """Replay independent checks with current external pins before reuse."""
    current = verify_document_set(result, requirements, **inputs)
    return current['accepted'] and report == current


def bind_hitl_record(report, record, *, trusted_report_sha256, lookup):
    """Bind a human decision from a host-configured authenticated lookup.

    The lookup is responsible for authentication and owner authorization. A
    bound record is audit evidence only. Verify report freshness with
    is_current_report before relying on it for a replan under new pins.
    """
    try:
        digest = core.contract_digest({k: v for k, v in report.items() if k != 'report_sha256'})
        if not report['accepted'] or report['report_sha256'] != digest or digest != trusted_report_sha256:
            return False
        if (set(record) != {'version', 'record_id', 'report_sha256', 'question_id', 'actor', 'decision'}
                or record['version'] != 'document-set-hitl-record-v1'
                or record['report_sha256'] != digest
                or not all(_text(record[k]) for k in ('record_id', 'actor', 'decision'))):
            return False
        matches = [q for q in report['hitl_questions'] if q['question_id'] == record['question_id']]
        if len(matches) != 1:
            return False
        expected = dict(record=record, actor_kind='human', authorized_owner=matches[0]['decision_owner'],
                        revoked=False)
        return lookup(record['record_id']) == expected
    except ERRORS:
        return False

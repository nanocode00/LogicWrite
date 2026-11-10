"""Independent Expression validation of actual fragments against current inputs.

Text patterns detect concrete protected-token losses and known distortions. They
never prove general semantic equivalence. Whole-document delivery remains REVIEW.
"""
from collections import Counter
import re

import expression
import semantic_validator

pipeline = expression.pipeline
organization = expression.organization
VERSION = 'expression-validation-v1'
NUMBER = re.compile(r'(?<![A-Za-z0-9_])[+-]?v?\d+(?:[.,]\d+)*(?:%|초|분|시간|일|년|개|건|ms|s|MB|GB)?', re.I)
NEGATION = re.compile(r'지원하지\s*않|동작하지\s*않|필요하지\s*않|불가능|금지|않으며|않는다|없(?:다|습니다|어요|으며|고|는|음)|\bnot\b|\bnever\b', re.I)
LIMITS = re.compile(r'때만|경우에만|한해서|초기\s*실험|사전\s*다운로드|수동으로|이번\s*릴리스|for this release|only if', re.I)


def _approval_claim(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if ((key in {'gate_state', 'status', 'validation_state'} and item == 'PASS')
                    or (key in {'delivery_approved', 'next_stage_allowed', 'stage_transition_allowed', 'approved', 'passed'} and item is True)):
                return True
            if _approval_claim(item):
                return True
    elif isinstance(value, list):
        return any(_approval_claim(item) for item in value)
    return False


def validate_expression_result(bundle, analysis, organization_plan, result, *,
                               destination_snapshots=None, validation_report=None):
    """Return FAIL on confirmed violations and REVIEW on all incomplete semantics.

    No report passed in the result is trusted. All checks run again, including
    current independent Organization verification. Malformed artifacts fail closed.
    """
    findings = []

    def finding(rule, message, severity='ERROR', fragment_id=None):
        row = {'rule_id': rule, 'severity': severity, 'message': message}
        if fragment_id:
            row['fragment_id'] = fragment_id
        if row not in findings:
            findings.append(row)

    upstream_state = 'REVIEW'
    try:
        _validate(bundle, analysis, organization_plan, result, destination_snapshots,
                  validation_report, finding)
        upstream = organization.validate_organization_plan(
            bundle, analysis, organization_plan, destination_snapshots=destination_snapshots,
            validation_report=validation_report)
        upstream_state = upstream['gate_state']
        if upstream_state in {'FAIL', 'STOPPED'}:
            finding('UPSTREAM_ORGANIZATION_INVALID', '; '.join(upstream['diagnostics']))
        else:
            finding('UPSTREAM_APPROVAL_NOT_GRANTED', 'Preview is isolated from authorized stage execution', 'WARNING')
    except Exception as exc:
        # Do not echo arbitrary exception strings (adapter/model data may contain secrets).
        finding('INVALID_EXPRESSION_SCHEMA', 'Validation could not complete: ' + type(exc).__name__)

    violated = any(f['severity'] == 'ERROR' for f in findings)
    report = {'version': VERSION, 'gate_state': 'FAIL' if violated else 'REVIEW',
              'expression_checks_state': 'violated' if violated else
                  ('unresolved' if any(f['rule_id'] in {'SEMANTIC_EQUIVALENCE_UNVERIFIED', 'CONTRACT_CONSTRAINT_UNRESOLVED'} for f in findings)
                   else 'passed'),
              'semantic_fidelity': 'unresolved', 'full_document_validation': 'not_run',
              'upstream_gate_state': upstream_state,
              'delivery_approved': False, 'next_stage_allowed': False,
              'stage_transition_allowed': False, 'findings': findings,
              'revision_sha256': result.get('revision_sha256') if isinstance(result, dict) else None}
    return expression.seal(report, 'report_sha256')


def _validate(bundle, analysis, org, result, destination_snapshots, validation_report, finding):
    if not organization.verify_self_digest(analysis, 'analysis_sha256')[0]:
        finding('STALE_EXPRESSION_INPUT', 'Analysis self-digest mismatch')
    if not organization.verify_self_digest(org, 'plan_sha256')[0]:
        finding('STALE_EXPRESSION_INPUT', 'Organization self-digest mismatch')
    if not organization.verify_self_digest(result, 'revision_sha256')[0]:
        finding('REVISION_DIGEST_MISMATCH', 'Revision body digest mismatch')
    plan = result['expression_plan']
    if not organization.verify_self_digest(plan, 'plan_sha256')[0]:
        finding('EXPRESSION_PLAN_DIGEST_MISMATCH', 'ExpressionPlan digest mismatch')
    if (result.get('version') != expression.RESULT_VERSION or plan.get('version') != expression.PLAN_VERSION
            or plan.get('producer') != expression.VERSION or result['meta'].get('producer') != expression.VERSION):
        finding('INVALID_EXPRESSION_SCHEMA', 'Unsupported artifact version or producer')
    expected_refs = expression.input_references(bundle, analysis, org)
    if (plan.get('analysis_ref') != expected_refs['analysis_ref']
            or plan.get('organization_ref') != expected_refs['organization_ref']
            or result.get('organization_ref') != expected_refs['organization_ref']):
        finding('STALE_EXPRESSION_INPUT', 'Revision references do not bind current inputs and versions')
    snapshot = bundle['document_snapshot']
    if pipeline.digest_text(snapshot['content']) != snapshot['sha256']:
        finding('STALE_EXPRESSION_INPUT', 'Source snapshot digest mismatch')
    if (analysis.get('snapshot_sha256') != snapshot['sha256']
            or analysis.get('snapshot_version') != snapshot['version']
            or analysis.get('contract_sha256') != pipeline.canonical_json_digest(bundle['writing_contract'])):
        finding('STALE_EXPRESSION_INPUT', 'Source analysis no longer binds current snapshot or contract')
    if _approval_claim(result):
        finding('UNAUTHORIZED_EXPRESSION_APPROVAL', 'Expression artifacts cannot grant PASS or delivery approval')
    if (result.get('delivery_state') != 'preview' or result.get('output_snapshots') != []
            or result['meta'].get('preview_only') is not True or result['meta'].get('execution_mode') != 'preview'):
        finding('UNSUPPORTED_DELIVERY_STATE', 'Only source-bound excerpt previews are implemented')

    constraints = expression.contract_constraints(bundle['writing_contract'])
    if plan.get('constraints') != constraints:
        finding('CONTRACT_CONSTRAINT_MISMATCH', 'Plan altered current contract obligations')
    if constraints['unresolved']:
        finding('CONTRACT_CONSTRAINT_UNRESOLVED', 'Natural-language contract constraints require semantic/human review', 'WARNING')
    if constraints['register'] not in {'한다체', '합니다체', '해요체'}:
        finding('CONTRACT_CONSTRAINT_UNRESOLVED', 'Unsupported or unspecified register', 'WARNING')

    # Resolve original quotes AGAIN from the current source, not the plan's copies.
    blocks = {b['block_id']: b for b in pipeline.parse_markdown_blocks(snapshot)}
    units = {u['id']: u for u in analysis['units']}
    if len(units) != len(analysis['units']):
        finding('EXPRESSION_COVERAGE_MISMATCH', 'Duplicate source unit IDs')
    placements = {p['unit_id']: p for p in org['placements']}
    entries = {e['unit_id']: e for e in plan['entries']}
    if set(entries) != set(units) or len(entries) != len(plan['entries']):
        finding('EXPRESSION_COVERAGE_MISMATCH', 'Plan omitted, duplicated or invented units')
    expected = {}
    for uid, unit in units.items():
        spans = pipeline.resolve_block_quotes(unit['quotes'], blocks, snapshot)
        if spans != unit.get('source_spans'):
            finding('EXPRESSION_TRACE_MISMATCH', 'Analysis source span differs from independently resolved quote')
        for element in unit['elements']:
            if pipeline.resolve_block_quotes(element['quotes'], blocks, snapshot) != element['source_spans']:
                finding('EXPRESSION_TRACE_MISMATCH', 'Element provenance differs from source')
        entry = entries.get(uid, {})
        if entry.get('placement') != placements.get(uid):
            finding('UNAUTHORIZED_ORGANIZATION_CHANGE', 'Expression altered placement, removal or consolidation for ' + uid)
        if entry.get('operation') not in expression.OPERATIONS:
            finding('UNAUTHORIZED_ORGANIZATION_CHANGE', 'Expression cannot MOVE/REMOVE/ADD/CONSOLIDATE units')
        excluded = any(expression.span_excluded(s, blocks, constraints) for s in spans)
        if (entry.get('source_spans') != spans or entry.get('protected_elements') != unit['elements']
                or entry.get('relations') != unit['relations'] or entry.get('excluded') != excluded
                or entry.get('id') != 'expr-' + uid):
            finding('EXPRESSION_TRACE_MISMATCH', 'Plan rewrote source inventory or protection for ' + uid)
        for index, span in enumerate(spans):
            expected[f'fragment-{uid}-{index}'] = (uid, span, excluded)

    fragments = {f['fragment_id']: f for f in result['preview_fragments']}
    changes = {c['fragment_id']: c for c in result['change_set']}
    traces = {t['output_spans'][0]['fragment_id']: t for t in result['trace']}
    for name, rows, mapping in [('fragments', result['preview_fragments'], fragments),
                                ('changes', result['change_set'], changes), ('trace', result['trace'], traces)]:
        if set(mapping) != set(expected) or len(mapping) != len(rows):
            finding('EXPRESSION_COVERAGE_MISMATCH', name + ' must track every source excerpt exactly once')

    for fid, (uid, source, excluded) in expected.items():
        if fid not in fragments or fid not in changes or fid not in traces:
            continue
        fragment, change, trace = fragments[fid], changes[fid], traces[fid]
        before, after = source['quote'], fragment['content']
        sha = pipeline.digest_text(after)
        operation = 'KEEP' if before == after else entries[uid]['operation']
        out = {'fragment_id': fid, 'snapshot_sha256': sha, 'start': 0, 'end': len(after)}
        if (not after.strip() or fragment.get('unit_id') != uid or fragment.get('source_span') != source
                or fragment.get('coverage') != 'excerpt' or fragment.get('sha256') != sha
                or fragment.get('placement_ref') != pipeline.canonical_json_digest(placements[uid])):
            finding('EXPRESSION_TRACE_MISMATCH', 'Fragment identity/provenance/content mismatch', fragment_id=fid)
        if (change.get('source_span') != source or change.get('before') != before
                or change.get('before_sha256') != pipeline.digest_text(before)
                or change.get('after') != after or change.get('after_sha256') != sha
                or change.get('output_span') != out or change.get('unit_id') != uid
                or change.get('operation') != operation or change.get('expression_entry_id') != 'expr-' + uid
                or change.get('producer') != expression.VERSION):
            finding('EXPRESSION_TRACE_MISMATCH', 'ChangeSet does not bind the real before/after ranges', fragment_id=fid)
        if (trace.get('unit_refs') != [uid] or trace.get('source_spans') != [source]
                or trace.get('output_spans') != [out] or trace.get('treatment') != operation
                or trace.get('element_refs') != [e['id'] for e in units[uid]['elements']]
                or trace.get('justification') != 'expr-' + uid):
            finding('EXPRESSION_TRACE_MISMATCH', 'Bidirectional unit/element trace mismatch', fragment_id=fid)
        if before != after and entries[uid]['operation'] == 'KEEP':
            finding('UNAUTHORIZED_EXPRESSION_OPERATION', 'KEEP cannot conceal text changes', fragment_id=fid)
        generation = fragment.get('generation', {})
        if _approval_claim(generation):
            finding('GENERATOR_APPROVAL_CLAIM', 'Generator supplied approval fields', fragment_id=fid)
        if generation.get('status') == 'execution_error':
            finding('GENERATION_ERROR', 'Generator failed; original excerpt must remain available', 'WARNING', fid)
            if before != after:
                finding('EXPRESSION_TRACE_MISMATCH', 'Failed generation changed the original excerpt', fragment_id=fid)
        # Independently inspect actual output, never generation/findings claims.
        _audit_text(before, after, units[uid], excluded, constraints, fid, finding)

    # Reported blocking errors cannot be silently discarded by successful rules.
    for reported in result.get('findings', []):
        if reported.get('severity') == 'ERROR' or reported.get('blocking') is True:
            finding('REPORTED_BLOCKING_FINDING', 'Revision carries an unresolved blocking finding')
    finding('FULL_DOCUMENT_VALIDATION_NOT_IMPLEMENTED',
            'Excerpt previews do not reconstruct or validate every affected document', 'WARNING')


def _audit_text(before, after, unit, excluded, constraints, fid, finding):
    def emit(rule, message, severity='ERROR'):
        finding(rule, message, severity, fid)

    if excluded:
        if before != after:
            emit('EXCLUDED_CONTEXT_MODIFIED', 'Code, command, quote, heading, table or excluded block changed')
        return
    # Preserve inline code, URLs, literal quotations, explicit immutable strings.
    protected = [m.group(0) for m in expression.INLINE_PROTECTED.finditer(before)]
    protected += [s for s in constraints['preserve'] if s in before]
    for literal in protected:
        if after.count(literal) < before.count(literal):
            emit('EXCLUDED_CONTEXT_MODIFIED', 'Protected inline context or explicit literal changed')
    if Counter(NUMBER.findall(before)) != Counter(NUMBER.findall(after)):
        emit('PROTECTED_INFORMATION_LOSS', 'Numeric, unit or version tokens were removed, changed or added')
    for element in unit['elements']:
        if element['kind'] in {'identifier', 'quantity', 'attribution', 'time_scope'}:
            value = str(element['value'])
            if value in before and value not in after:
                emit('PROTECTED_INFORMATION_LOSS', 'Protected literal lost: ' + element['id'])
    if before != after:
        # Token loss is a conservative blocker, not a semantic equivalence proof.
        if NEGATION.search(before) and not NEGATION.search(after):
            emit('PROTECTED_INFORMATION_LOSS', 'Explicit negation disappeared')
        for limit in LIMITS.finditer(before):
            if limit.group(0) not in after:
                emit('PROTECTED_INFORMATION_LOSS', 'Explicit required limit disappeared')
        polarity = semantic_validator._check_polarity_reversal(before, after)
        if polarity and polarity[0] == 'contradicted':
            emit('POLARITY_REVERSAL', polarity[2])
        modality = semantic_validator._check_modality_overstatement(before, after)
        if modality:
            emit('CLAIM_OVERSTATEMENT', modality)
        unsupported = semantic_validator._check_unsupported_addition(before, before, after)
        if unsupported:
            emit('UNSUPPORTED_CLAIM', unsupported)
        emit('SEMANTIC_EQUIVALENCE_UNVERIFIED',
             'Changed expression requires independent semantic/human review; token checks do not prove equivalence', 'WARNING')
    prose = expression.INLINE_PROTECTED.sub('', after).strip()
    for old, new in constraints['terminology'].items():
        if old in prose.replace(new, '') and old != new:
            emit('CONTRACT_TERM_VIOLATION', 'Explicit noncanonical term remains in editable prose')
    if any(term in prose for term in constraints['forbid']):
        emit('CONTRACT_TERM_VIOLATION', 'Explicit forbidden phrase present')
    register = constraints['register']
    endings = {'한다체': r'(?:습니다|입니다|해요|이에요|예요)\.',
               '합니다체': r'(?:한다|이다|있다|없다|초다|해요)\.',
               '해요체': r'(?:한다|이다|있다|없다|습니다|입니다)\.'}
    if re.search(endings.get(register, r'(?!)') + r'(?=\s|$)', prose):
        emit('CONTRACT_REGISTER_VIOLATION', 'Explicit incompatible Korean sentence ending in editable prose')

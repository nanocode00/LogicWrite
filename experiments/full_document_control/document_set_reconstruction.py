"""Pinned G2-C execution for isolated, source-preserving document-set candidates."""
import copy
import re

import document_set as core
import document_set_planning as planning
import document_set_final_validator as validation

VERSION = 'core-document-set-reconstruction-v1'
CANDIDATE_REQUEST = 'core-document-set-candidate-request-v1'
SEMANTIC_GAPS = ('GENERAL_SEMANTIC_PRESERVATION_UNRESOLVED',
                 'READER_PURPOSE_UNRESOLVED', 'NATURAL_LANGUAGE_CONSTRAINTS_UNRESOLVED')
ERRORS = (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError)
CONTEXT_CUE = re.compile(
    r'\b(?:above|below|previous|preceding|following|former|latter|next|then|'
    r'therefore|otherwise|however|provided|assuming|subject to|so long as|'
    r'in case|depending on|as described|see|refer to|instead|this|that|these|those|'
    r'must|shall|required|prohibit(?:ed|s)?|forbid(?:den|s)?|not|no|never|without|until|unless)\b|상기|아래|위의|앞서|이전|다음|'
    r'이때|따라서|에 따라|[가-힣]\s+시(?=\s|[,.:]|$)|참조|단,|한해서|한하여|전제|필수|금지|불가|하지 않|해서는 안', re.IGNORECASE)
STRUCTURE_PROHIBITION = re.compile(
    r"\b(?:do not|don't|never|must not|may not|no)\s+(?:move|reorder|relocate|rearrange|"
    r"restructure|change the order)\b|"
    r"\b(?:keep|preserve|retain|maintain)\s+(?:the\s+)?(?:original|existing|current)"
    r"\s+(?:paragraph\s+|section\s+)?(?:order|sequence|position|placement)\b|"
    r"(?:이동|재배치|순서 변경).{0,18}(?:금지|하지\s*마|하지\s*말|안 됨)|"
    r"(?:기존|현재|원래|원문).{0,18}(?:순서|위치|배치).{0,12}(?:유지|보존)",
    re.IGNORECASE)
MARKUP = re.compile(r'^[ \t]|[\[\]<>`\\|]| {2,}$|^[-=]+$', re.MULTILINE)


def make_candidate_request(plan, *, task_ids, document_ids):
    """Bind intent to the exact plan. Callers retain this request's digest separately.

    document_ids grants writes to both sides of each edit. Full preservation
    snapshots are returned for every G1 output scope, even outside that grant.
    """
    return dict(schema_version=CANDIDATE_REQUEST, mode='isolated_candidate',
                plan_sha256=plan['plan_sha256'], task_ids=list(task_ids),
                document_ids=list(document_ids))


def _bind(contract, analysis, plan, plan_request, candidate_request, *,
          trusted_contract_sha256, trusted_request_sha256, trusted_candidate_request_sha256):
    expected = planning.plan_document_set(
        contract, analysis, plan_request, trusted_contract_sha256=trusted_contract_sha256,
        trusted_request_sha256=trusted_request_sha256)
    if expected['gate_state'] == 'FAIL':
        codes = ','.join(expected['reasons'])
        raise ValueError('UPSTREAM_BINDING_REJECTED', codes)
    if core.contract_digest(plan) != core.contract_digest(expected):
        raise ValueError('PLAN_REPLAY_MISMATCH')
    if (not isinstance(candidate_request, dict)
            or set(candidate_request) != {'schema_version', 'mode', 'plan_sha256', 'task_ids', 'document_ids'}
            or candidate_request['schema_version'] != CANDIDATE_REQUEST
            or candidate_request['mode'] != 'isolated_candidate'
            or candidate_request['plan_sha256'] != expected['plan_sha256']
            or core.contract_digest(candidate_request) != trusted_candidate_request_sha256):
        raise ValueError('CANDIDATE_REQUEST_BINDING_REJECTED')
    docs = {d['document_id']: d for d in contract['documents']}
    scopes = {s['document_id']: s['scope_id'] for s in contract['output_scopes']}
    rows = {t['task_id']: t for t in expected['tasks']}
    for field, allowed in (('task_ids', rows), ('document_ids', scopes)):
        values = candidate_request[field]
        if not planning._ids(values) or not set(values) <= allowed.keys():
            raise ValueError('CANDIDATE_REQUEST_SCOPE_INVALID')
    if contract['document_set_completeness'] != 'complete' or any(
            docs[doc]['completeness'] != 'complete' for doc in scopes):
        raise ValueError('FULL_OUTPUT_SNAPSHOTS_UNAVAILABLE')
    return (docs, scopes, rows, {u['unit_id']: u for u in analysis['units']},
            {d['document_id']: d['blocks'] for d in analysis['documents']})


def _effects(task, units):
    reads = {u['document_id'] for u in task['source_evidence']}
    reads.update(units[u]['document_id'] for u in task['unit_ids'] + task['evidence_unit_ids'] if u in units)
    writes = {units[u]['document_id'] for u in task['unit_ids'] if u in units}
    for key in ('anchor_unit_id', 'primary_unit_id'):
        uid = task['parameters'].get(key)
        if isinstance(uid, str) and uid in units:
            reads.add(units[uid]['document_id'])
    if task['target_document_id'] is not None:
        writes.add(task['target_document_id'])
    return (set() if task['action'] == 'KEEP' else writes), reads | writes


def _preflight(task, docs, units, blocks, grant, plan_rows, effects):
    if task['status'] != 'eligible':
        return task['status'], task['reasons']
    action = task['action']
    if task['task_id'] not in grant['task_ids']:
        return 'denied', ['CANDIDATE_TASK_NOT_GRANTED']
    if action == 'KEEP':
        return 'preserved', []
    if action not in {'PLACE', 'MOVE'}:
        return 'unsupported', ['NO_VERIFIED_DOCUMENT_SET_TRANSFORM']
    writes, reads = effects[task['task_id']]
    if not writes <= set(grant['document_ids']):
        return 'denied', ['CANDIDATE_DOCUMENT_NOT_GRANTED']
    if any(not docs[d]['output_target'] or docs[d]['access'] != 'edit' for d in writes):
        return 'denied', ['DOCUMENT_ACCESS_DENIED']
    if any(STRUCTURE_PROHIBITION.search(obligation['text'])
           for obligation in task['preservation_obligations'] if obligation['kind'] == 'uninterpreted_constraint'):
        return 'held', ['EXPLICIT_STRUCTURE_PROHIBITION_REQUIRES_REVIEW']
    if any(docs[d]['pending_questions'] or docs[d]['completeness'] != 'complete'
           or docs[d]['access'] == 'pending' or docs[d]['authority'] is None
           or docs[d]['role'] is None for d in reads):
        return 'held', ['LOCAL_SOURCE_CONTEXT_UNRESOLVED']
    source = units[task['unit_ids'][0]]
    target = task['target_document_id']
    anchor = units[task['parameters']['anchor_unit_id']] if action == 'PLACE' else None
    if anchor and source['section_unit_ids'] != anchor['section_unit_ids']:
        return 'held', ['PLACEMENT_SECTION_CHANGE_UNRESOLVED']
    if anchor and source['quote'].strip() == anchor['quote'].strip():
        return 'held', ['PLACEMENT_IDENTICAL_PARAGRAPHS']
    for doc in writes:
        if docs[doc]['content'].startswith('\ufeff'):
            return 'held', ['DOCUMENT_ENCODING_BOUNDARY_UNSUPPORTED']
        if any(b['kind'] not in {'heading', 'paragraph', 'blank'} for b in blocks[doc]):
            return 'held', ['UNSUPPORTED_STRUCTURAL_CONTEXT']
        if action == 'MOVE':
            headings = [b for b in blocks[doc] if b['kind'] == 'heading']
            first = next(b for b in blocks[doc] if b['kind'] != 'blank')
            if headings and (len(headings) != 1 or headings[0] != first
                             or not first['text'].startswith('# ')):
                return 'held', ['MOVE_SECTION_CONTEXT_UNRESOLVED']
    for unit in units.values():
        if unit['document_id'] not in writes:
            continue
        observations = unit['observations']
        if (observations['conditions'] or observations['exceptions'] or CONTEXT_CUE.search(unit['quote'])
                or (unit['kind'] == 'paragraph' and MARKUP.search(unit['quote']))):
            return 'held', ['CONTEXT_DEPENDENCE_REVIEW_REQUIRED']
    # A standalone output cannot be empty. Keep an emptying edit on hold.
    source_blocks = blocks[source['document_id']]
    if action == 'MOVE' and not any(
            b['kind'] != 'blank' and b['block_id'] != source['block_id'] for b in source_blocks):
        return 'held', ['MOVE_WOULD_EMPTY_SOURCE_DOCUMENT']
    for other_id, (other_writes, other_reads) in effects.items():
        if other_id == task['task_id']:
            continue
        other = plan_rows[other_id]
        if other['action'] == 'KEEP':
            if set(other['unit_ids'] + other['evidence_unit_ids']) & set(task['unit_ids']):
                return 'held', ['PLANNED_KEEP_CONFLICT']
        elif writes & other_reads or other_writes & reads:
            # Document-level isolation also covers order, append boundaries and
            # evidence read by held/denied/unsupported tasks.
            return 'held', ['DOCUMENT_READ_WRITE_CONFLICT']
    if any(u['unit_id'] != source['unit_id'] and u['document_id'] == target
           and u['kind'] == 'paragraph' and u['quote'].strip() == source['quote'].strip()
           for u in units.values()):
        return 'held', ['DESTINATION_ALREADY_CONTAINS_PARAGRAPH' if action == 'MOVE'
                        else 'PLACEMENT_IDENTICAL_PARAGRAPHS']
    if anchor:
        ordered = [b['block_id'] for b in source_blocks if b['kind'] != 'blank']
        delta = 1 if task['parameters']['position'] == 'after' else -1
        if ordered.index(source['block_id']) == ordered.index(anchor['block_id']) + delta:
            return 'preserved', ['ALREADY_AT_REQUESTED_POSITION']
    return 'ready', []


def _decisions(bound, grant):
    docs, _, rows, units, blocks = bound
    effects = {tid: _effects(row, units) for tid, row in rows.items()}
    states = {tid: _preflight(row, docs, units, blocks, grant, rows, effects) for tid, row in rows.items()}
    # Only explicit preserved KEEP dependencies can be consumed in this
    # independent-task executor. No sequential write effects are supported.
    changed = True
    while changed:
        changed = False
        for tid, row in rows.items():
            state, _ = states[tid]
            if state not in {'ready', 'preserved'}:
                continue
            if any(states[dep][0] != 'preserved' or rows[dep]['action'] != 'KEEP'
                   for dep in row['depends_on']):
                states[tid] = ('held', ['DEPENDENCY_NOT_INDEPENDENTLY_SATISFIED'])
                changed = True
    return states


def _operations(bound, states):
    _, _, rows, units, _ = bound
    operations = []
    for tid, (status, _) in states.items():
        if status != 'ready':
            continue
        row = rows[tid]
        source = units[row['unit_ids'][0]]
        anchor = units.get(row['parameters'].get('anchor_unit_id'))
        operations.append(dict(task_id=tid, action=row['action'], source_document_id=source['document_id'],
                               source_block_id=source['block_id'], target_document_id=row['target_document_id'],
                               anchor_block_id=anchor['block_id'] if anchor else None,
                               position=row['parameters'].get('position', 'append')))
    return operations


def _layouts(blocks, scopes, operations):
    layouts = {did: [(did, b, None) for b in blocks[did]] for did in scopes}
    for op in operations:
        source, target = op['source_document_id'], op['target_document_id']
        src = layouts[source]
        index = next(i for i, (_, b, _) in enumerate(src) if b['block_id'] == op['source_block_id'])
        _, block, _ = src.pop(index)
        dest = layouts[target]
        index = len(dest)
        if op['anchor_block_id'] is not None:
            index = next(i for i, (_, b, _) in enumerate(dest) if b['block_id'] == op['anchor_block_id'])
            index += op['position'] == 'after'
        dest.insert(index, (source, block, op))
    return layouts


def _render_document(doc, layout):
    spans = []
    prefix = ''
    last_op = None
    for source, block, op in layout:
        # Blank source blocks remain at their original sites. Insert only the
        # minimum missing breaks immediately next to a relocated paragraph.
        previous_op = op or last_op
        gap = validation.boundary_gap(prefix, block, op, last_op, doc['content'])
        if gap:
            spans.append((None, None, previous_op, gap))
            prefix += gap
        spans.append((source, block, op, block['text']))
        prefix += block['text']
        last_op = op
    return spans, prefix


def _audit(bound, states, *, did_execute):
    _, _, rows, _, _ = bound
    audit = []
    for tid, row in rows.items():
        state, reasons = states[tid]
        if state == 'ready':
            state = 'executed' if did_execute else 'failed'
            reasons = [] if did_execute else ['ATOMIC_CANDIDATE_DISCARDED']
        audit.append(dict(task_id=tid, action=row['action'], planned_status=row['status'],
                          status=state, reasons=reasons, depends_on=row['depends_on'],
                          unit_ids=row['unit_ids'], target_document_id=row['target_document_id'],
                          basis=row['reason'], source_evidence=row['source_evidence'],
                          preservation_obligations=row['preservation_obligations'],
                          required_hitl_question_ids=row['required_hitl_question_ids'],
                          conflicts=row['conflicts'], verification='passed' if state == 'executed' else 'not_run'))
    return audit


def _result():
    return dict(schema_version=VERSION, mode='isolated_candidate', gate_state='FAIL',
                semantic_judgment='unresolved', delivery_approved=False, stage_transition_allowed=False,
                b2_reconstruction_success=False, request_complete=False, model_calls=0,
                execution_state='failed', bindings=None, output_scopes=[], candidates=[], change_ledger={},
                trace=[], tasks=[], hitl_questions=[], planned=[], executed=[], preserved=[], held=[],
                denied=[], unsupported=[], failed=[], reasons=list(SEMANTIC_GAPS), structure=None)


def _set_audit(result, bound, states, *, did_execute):
    result['tasks'] = _audit(bound, states, did_execute=did_execute)
    result['planned'] = [row['task_id'] for row in result['tasks']]
    for status in ('executed', 'preserved', 'held', 'denied', 'unsupported', 'failed'):
        result[status] = [row['task_id'] for row in result['tasks'] if row['status'] == status]


def _bindings(plan, candidate_request_sha256):
    return {**{key: plan[key] for key in ('contract_sha256', 'analysis_sha256', 'request_sha256', 'plan_sha256')},
            'candidate_request_sha256': candidate_request_sha256}


def _finish_status(result):
    unresolved = result['held'] or result['denied'] or result['unsupported'] or result['hitl_questions']
    result['execution_state'] = 'partial_candidate' if unresolved else 'candidate'
    if unresolved:
        result['reasons'].append('UNRESOLVED_PLANNING_OR_CANDIDATE_SCOPE')


def reconstruct_document_set(contract, analysis, plan, plan_request, candidate_request, *,
                             trusted_contract_sha256, trusted_request_sha256, trusted_candidate_request_sha256):
    """Generate and check full snapshots in memory. A failed transaction emits no snapshots."""
    result = _result()
    pins = dict(trusted_contract_sha256=trusted_contract_sha256, trusted_request_sha256=trusted_request_sha256,
                trusted_candidate_request_sha256=trusted_candidate_request_sha256)
    try:
        # Use one private baseline for both the grant check and the transaction.
        contract, analysis, plan, plan_request, candidate_request = copy.deepcopy(
            (contract, analysis, plan, plan_request, candidate_request))
        bound = _bind(contract, analysis, plan, plan_request, candidate_request, **pins)
        states = _decisions(bound, candidate_request)
    except ERRORS as exc:
        result['reasons'].append(validation.binding_error(exc))
        return result
    docs, scopes, _, units, blocks = bound
    result.update(bindings=_bindings(plan, trusted_candidate_request_sha256),
                  output_scopes=contract['output_scopes'], hitl_questions=plan['hitl_questions'])
    _set_audit(result, bound, states, did_execute=False)
    try:
        operations = _operations(bound, states)
        layouts = _layouts(blocks, scopes, operations)
        trace, candidates = [], []
        unit_ids = {(u['document_id'], u['block_id']): uid for uid, u in units.items()}
        for did, layout in layouts.items():
            doc = docs[did]
            spans, text = _render_document(doc, layout)
            candidate = validation.candidate_row(doc, text)
            candidates.append(candidate)
            offset = 0
            for source, block, op, piece in spans:
                trace.append(validation.trace_row(docs, unit_ids, candidate, source, block, op, piece, offset))
                offset += len(piece)
        draft = dict(result, gate_state='REVIEW', candidates=candidates, trace=trace,
                     change_ledger=validation.document_ledger(candidates, scopes, trace),
                     reasons=list(SEMANTIC_GAPS))
        _set_audit(draft, bound, states, did_execute=True)
        _finish_status(draft)
        report = validate_candidate_result(draft, contract, analysis, plan, plan_request, candidate_request, **pins)
        if report['status'] == 'passed':
            return dict(draft, structure=report)
        result['structure'] = report
        result['reasons'].append('ATOMIC_CANDIDATE_VALIDATION_FAILED')
    except ERRORS + (RuntimeError,):
        result['reasons'].append('ATOMIC_CANDIDATE_RENDER_FAILED')
    return result


def validate_candidate_result(result, contract, analysis, plan, plan_request, candidate_request, *,
                              trusted_contract_sha256, trusted_request_sha256, trusted_candidate_request_sha256):
    """Replay the pinned authorization and independently check the supplied result."""
    try:
        bound = _bind(contract, analysis, plan, plan_request, candidate_request,
                      trusted_contract_sha256=trusted_contract_sha256, trusted_request_sha256=trusted_request_sha256,
                      trusted_candidate_request_sha256=trusted_candidate_request_sha256)
        states = _decisions(bound, candidate_request)
        expected = _result()
        expected.update(gate_state='REVIEW', bindings=_bindings(plan, trusted_candidate_request_sha256),
                        output_scopes=contract['output_scopes'], hitl_questions=plan['hitl_questions'])
        _set_audit(expected, bound, states, did_execute=True)
        _finish_status(expected)
    except ERRORS as exc:
        return validation.report([validation.binding_error(exc)])
    return validation.validate_structure(result, expected, bound, _operations(bound, states),
                                         contract, trusted_contract_sha256, candidate_request)

"""Independent structural audit for pinned G2-C plans and candidate snapshots.

Checks the observed document text and ledger against an original-offset ordering
model. No reconstruction routine or claimed validation status is consumed.
"""
import re

import document_set as core
from final_validator import span_partition_issues
from reconstruction import paragraph_separator, pipeline

VERSION = 'core-document-set-structure-v1'
BINDING_ERRORS = {
    'UPSTREAM_BINDING_REJECTED', 'PLAN_REPLAY_MISMATCH', 'CANDIDATE_REQUEST_BINDING_REJECTED',
    'CANDIDATE_REQUEST_SCOPE_INVALID', 'FULL_OUTPUT_SNAPSHOTS_UNAVAILABLE',
}


def binding_error(exc):
    code = exc.args[0] if exc.args else None
    if code == 'UPSTREAM_BINDING_REJECTED':
        return code + ':' + exc.args[1]
    return code if isinstance(code, str) and code in BINDING_ERRORS else 'INVALID_CANDIDATE_BINDING'


def report(reasons, digest=None, permission_status=None):
    return dict(schema_version=VERSION, status='failed' if reasons else 'passed',
                g1_permission_status=permission_status,
                gate_state='FAIL' if reasons else 'REVIEW', reasons=reasons,
                candidate_result_sha256=digest, semantic_judgment='unresolved',
                delivery_approved=False, stage_transition_allowed=False)


def candidate_row(source, text):
    return dict(document_id=source['document_id'], source_sha256=source['sha256'],
                source_path=source['provenance']['path'], content=text, sha256=pipeline.digest_text(text))


def _span(document, start, end):
    text = document['content']
    return dict(document_id=document['document_id'], sha256=document['sha256'], start=start, end=end,
                byte_start=len(text[:start].encode('utf-8')), byte_end=len(text[:end].encode('utf-8')))


def trace_row(docs, unit_ids, candidate, source, block, op, text, offset):
    return dict(source=_span(docs[source], block['start'], block['end']) if block else None,
                source_provenance=docs[source]['provenance'] if block else None,
                source_block_id=block['block_id'] if block else None,
                unit_id=unit_ids.get((source, block['block_id'])) if block else None,
                task_id=op['task_id'] if op else None,
                treatment='SEPARATOR' if block is None else op['action'] if op else 'KEEP',
                output=_span(candidate, offset, offset + len(text)), text=text)


def document_ledger(candidates, scopes, trace):
    ledgers = {
        row['document_id']: dict(scope_id=scopes[row['document_id']], source_sha256=row['source_sha256'],
                                  output_sha256=row['sha256'], changed=row['source_sha256'] != row['sha256'],
                                  incoming=[], outgoing=[], changes=[])
        for row in candidates
    }
    for i, row in enumerate(trace):
        output = row['output']['document_id']
        source = row['source']['document_id'] if row['source'] else None
        ledgers[output]['incoming'].append(i)
        if source is not None:
            ledgers[source]['outgoing'].append(i)
        if row['task_id'] is not None:
            ledgers[output]['changes'].append(i)
            if source is not None and source != output:
                ledgers[source]['changes'].append(i)
    return ledgers


def boundary_gap(prefix, block, op, previous_op, baseline):
    if not prefix or not (op or previous_op):
        return ''
    newline = '\r\n' if '\r\n' in baseline and '\n' not in baseline.replace('\r\n', '') else '\n'
    if block['kind'] == 'blank':
        return '' if prefix.endswith('\n') else newline
    if re.search(r'\n[ \t]*\r?\n$', prefix):
        return ''
    # A moved CRLF paragraph still ends a line in a LF destination and vice versa.
    if prefix.endswith('\n'):
        return newline
    return paragraph_separator(prefix, newline)


def _physical_order(blocks, scopes, operations):
    """Calculate expected source block identities by their original coordinate slots."""
    coordinates = {doc: {b['block_id']: i * 2 for i, b in enumerate(blocks[doc])} for doc in scopes}
    subjects = {(op['source_document_id'], op['source_block_id']): op for op in operations}
    order = {doc: [] for doc in scopes}
    for doc in scopes:
        for index, block in enumerate(blocks[doc]):
            op = subjects.get((doc, block['block_id']))
            target, position = doc, index * 2
            if op:
                target = op['target_document_id']
                if op['position'] == 'append':
                    position = len(blocks[target]) * 2
                else:
                    anchor = coordinates[target][op['anchor_block_id']]
                    position = anchor + (1 if op['position'] == 'after' else -1)
            order[target].append((position, doc, block, op))
    return {doc: sorted(rows, key=lambda row: row[0]) for doc, rows in order.items()}


def _matches_trace(trace, expected):
    return core.contract_digest(next(trace, None)) == core.contract_digest(expected)


def _check_document(candidate, source_doc, order, trace, context):
    # A missing iterator requests a layout/bytes check without trace evidence.
    docs, unit_ids = context
    if not order:
        return False
    content = candidate['content']
    cursor = 0
    previous = None
    significant = []
    for _, source_id, block, op in order:
        gap = boundary_gap(content[:cursor], block, op, previous, source_doc['content'])
        if gap:
            expected_gap = trace_row(docs, unit_ids, candidate, None, None, op or previous, gap, cursor)
            if (trace is not None and not _matches_trace(trace, expected_gap)) or content[cursor:cursor + len(gap)] != gap:
                return False
            cursor += len(gap)
        text = block['text']
        expected = trace_row(docs, unit_ids, candidate, source_id, block, op, text, cursor)
        if (trace is not None and not _matches_trace(trace, expected)) or content[cursor:cursor + len(text)] != text:
            return False
        if block['kind'] != 'blank':
            significant.append((block['kind'], cursor, text.rstrip('\r\n')))
        cursor += len(text)
        previous = op
    if cursor != len(content):
        return False
    if content != source_doc['content']:
        # The same bytes can change Markdown meaning by merging with a neighbor
        # or by changing block kind. Reparse the actual snapshot to detect that.
        snapshot = dict(candidate, snapshot_id=candidate['document_id'] + ':candidate')
        parsed = pipeline.parse_markdown_blocks(snapshot)
        observed = [(b['kind'], b['start'], b['text'].rstrip('\r\n')) for b in parsed if b['kind'] != 'blank']
        if observed != significant:
            return False
    return True


def _complete_partitions(trace, candidates, docs):
    ranges = {side: {d['document_id']: [] for d in candidates} for side in ('source', 'output')}
    for row in trace:
        for side, documents in ranges.items():
            span = row[side]
            if span is not None:
                documents[span['document_id']].append((span['start'], span['end']))
    for row in candidates:
        did = row['document_id']
        for side, length in (('source', len(docs[did]['content'])), ('output', len(row['content']))):
            if list(span_partition_issues(sorted(ranges[side][did]), length)):
                return False
    return True


def validate_structure(result, expected, bound, operations, contract, trusted_contract_sha256, grant):
    docs, scopes, tasks, units, blocks = bound
    try:
        metadata = {k: v for k, v in result.items() if k not in {'candidates', 'trace', 'change_ledger', 'structure'}}
        expected_metadata = {k: v for k, v in expected.items() if k not in {'candidates', 'trace', 'change_ledger', 'structure'}}
        if set(result) != set(expected) or core.contract_digest(metadata) != core.contract_digest(expected_metadata):
            return report(['EXECUTION_METADATA_OR_APPROVAL_BOUNDARY_MISMATCH'])
        candidates = result['candidates']
        permission = core.validate_candidates(contract, candidates, trusted_contract_sha256=trusted_contract_sha256)
        if permission['gate_state'] == 'FAIL' or 'FORMAT_CHANGE_REQUIRES_REVIEW' in permission['reasons']:
            return report(['CANDIDATE_COVERAGE_OR_ACCESS_VIOLATION', *permission['reasons']])
        if [row['document_id'] for row in candidates] != list(scopes):
            return report(['OUTPUT_SCOPE_ORDER_MISMATCH'])
        changed_documents = {row['document_id'] for row in candidates
                             if row['content'] != docs[row['document_id']]['content']}
        required_changes = set()
        for op in operations:
            affected = {op['source_document_id'], op['target_document_id']}
            required_changes.update(affected)
            tid = op['task_id']
            if (tid not in grant['task_ids'] or tasks[tid]['status'] != 'eligible'
                    or not affected <= set(grant['document_ids'])
                    or any(docs[d]['access'] != 'edit' for d in affected)):
                return report(['OPERATION_NOT_AUTHORIZED'])
        if changed_documents != required_changes:
            return report(['EXECUTED_TASK_DOCUMENT_DIFF_MISMATCH'])
        if not isinstance(result['trace'], list):
            return report(['EXTRA_OR_INVALID_TRACE'])
        order = _physical_order(blocks, scopes, operations)
        rows = iter(result['trace'])
        units_by_block = {(u['document_id'], u['block_id']): uid for uid, u in units.items()}
        for candidate in candidates:
            did = candidate['document_id']
            if not _check_document(candidate, docs[did], order[did], rows, (docs, units_by_block)):
                return report(['OUTPUT_LAYOUT_OR_TRACE_MISMATCH'])
        end = object()
        if next(rows, end) is not end:
            return report(['EXTRA_OR_INVALID_TRACE'])
        if not _complete_partitions(result['trace'], candidates, docs):
            return report(['SOURCE_OR_OUTPUT_PARTITION_MISMATCH'])
        ledger = document_ledger(candidates, scopes, result['trace'])
        if core.contract_digest(ledger) != core.contract_digest(result['change_ledger']):
            return report(['DOCUMENT_LEDGER_MISMATCH'])
        artifact = {k: v for k, v in result.items() if k != 'structure'}
        checked = report([], core.contract_digest(artifact), permission['permission_status'])
        if result['structure'] is not None and core.contract_digest(result['structure']) != core.contract_digest(checked):
            return report(['EMBEDDED_STRUCTURE_REPORT_MISMATCH'])
        return checked
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
        return report(['INVALID_CANDIDATE_STRUCTURE'])

"""Independent full-document coverage, placement, provenance and policy gate.

This gate verifies actual candidate text against original source ranges and
upstream artifacts. Structural success never stands in for semantic approval.
"""
import expression
import expression_validator
import reconstruction

pipeline = expression.pipeline
CHECKS = ('SNAPSHOT_INTEGRITY', 'FULL_COVERAGE', 'PROTECTED_INFORMATION', 'ORGANIZATION_FIDELITY',
          'EXPRESSION_FIDELITY', 'BIDIRECTIONAL_TRACE', 'CROSS_DOCUMENT_INTEGRITY', 'APPROVAL_BOUNDARY')
VERSION = 'final-document-validation-v1'


def validate_final_result(bundle, analysis, org, preview, result, *, destination_snapshots=None):
    checks = dict.fromkeys(CHECKS, 'passed')
    findings = []
    def finding(check, rule, message, severity='ERROR'):
        findings.append({'check_id': check, 'rule_id': rule, 'message': message, 'severity': severity})
        if severity == 'ERROR':
            checks[check] = 'violated'
        elif checks[check] == 'passed':
            checks[check] = 'unresolved'
    try:
        _validate(bundle, analysis, org, preview, result, destination_snapshots, finding)
    except reconstruction.IncompleteSnapshot:
        checks.update({k: 'unresolved' for k, v in checks.items() if v == 'passed'})
        severity = 'WARNING' if isinstance(result, dict) and result.get('delivery_state') == 'preview' and not result.get('output_snapshots') else 'ERROR'
        finding('FULL_COVERAGE', 'FULL_SNAPSHOT_UNAVAILABLE', 'Complete input snapshots cannot be established', severity)
    except (KeyError, ValueError, TypeError, IndexError, AttributeError):
        checks.update({k: 'unresolved' for k, v in checks.items() if v == 'passed'})
        finding('SNAPSHOT_INTEGRITY', 'INVALID_FINAL_ARTIFACT', 'Cannot independently resolve the complete candidate')
    violated = any(v == 'violated' for v in checks.values())
    report = {'version': VERSION, 'gate_state': 'FAIL' if violated else 'REVIEW',
              'checks': checks, 'check_versions': dict.fromkeys(CHECKS, '1'),
              'semantic_fidelity': 'not_run', 'delivery_approved': False, 'stage_transition_allowed': False,
              'revision_sha256': result.get('revision_sha256') if isinstance(result, dict) else None,
              'analysis_sha256': analysis.get('analysis_sha256'), 'organization_sha256': org.get('plan_sha256'),
              'findings': findings}
    return expression.seal(report, 'report_sha256')


def _validate(bundle, analysis, org, preview, result, destinations, finding):
    if expression_validator._approval_claim(result):
        finding('APPROVAL_BOUNDARY', 'UNAUTHORIZED_FINAL_APPROVAL', 'Candidate cannot authorize PASS or delivery')
    docs = reconstruction.source_documents(bundle, destinations)
    source_doc = bundle['document_snapshot']['document_id']
    source = docs[source_doc]
    if not expression.organization.verify_self_digest(result, 'revision_sha256')[0]:
        finding('SNAPSHOT_INTEGRITY', 'REVISION_DIGEST_MISMATCH', 'Revision body digest mismatch')
    if result.get('version') != reconstruction.VERSION:
        finding('SNAPSHOT_INTEGRITY', 'FINAL_VERSION_MISMATCH', 'Unsupported reconstruction version')
    refs = reconstruction.references(bundle, analysis, org, preview, docs)
    if any(result.get(k) != v for k, v in refs.items()):
        finding('SNAPSHOT_INTEGRITY', 'STALE_FINAL_INPUT', 'Candidate binds different source artifacts')
    if result.get('expression_plan') != preview.get('expression_plan'):
        finding('EXPRESSION_FIDELITY', 'EXPRESSION_PLAN_REPLACED', 'Candidate altered expression intent')
    preview_report = expression_validator.validate_expression_result(bundle, analysis, org, preview,
                                                    destination_snapshots=destinations)
    for f in preview_report['findings']:
        if f['severity'] == 'ERROR':
            finding('EXPRESSION_FIDELITY', f['rule_id'], f['message'])
        elif f['rule_id'] in {'GENERATION_ERROR', 'GENERATION_RECORD_UNVERIFIED'}:
            finding('EXPRESSION_FIDELITY', f['rule_id'], f['message'], 'WARNING')
    if result.get('delivery_state') == 'preview':
        if result.get('output_snapshots'):
            finding('FULL_COVERAGE', 'PREVIEW_WITH_OUTPUT_DOCUMENTS', 'Incomplete reconstruction cannot expose full snapshots')
        for f in result.get('findings', []):
            finding('FULL_COVERAGE', f['rule_id'], f['message'], f.get('severity', 'WARNING'))
        finding('FULL_COVERAGE', 'RECONSTRUCTION_HELD', 'No structurally complete candidate is available', 'WARNING')
        for check in ('PROTECTED_INFORMATION', 'ORGANIZATION_FIDELITY', 'BIDIRECTIONAL_TRACE', 'CROSS_DOCUMENT_INTEGRITY', 'APPROVAL_BOUNDARY'):
            finding(check, 'FULL_DOCUMENT_CHECK_NOT_RUN', 'No complete candidate exists for this check', 'WARNING')
        return
    if result.get('delivery_state') != 'candidate' or result.get('preview_fragments') != []:
        finding('FULL_COVERAGE', 'INVALID_DELIVERY_STATE', 'Candidate requires full snapshots and no excerpt fragments')
    outputs = {s['document_id']: s for s in result['output_snapshots']}
    if set(outputs) != set(docs) or len(outputs) != len(result['output_snapshots']):
        finding('CROSS_DOCUMENT_INTEGRITY', 'PARTIAL_ATOMIC_CHANGESET', 'Every source and destination document must be present exactly once')
        return
    for doc, snap in outputs.items():
        sha = pipeline.digest_text(snap['content'])
        if (snap.get('sha256') != sha or snap.get('coverage') != 'complete' or snap.get('media_type') != 'text/markdown'
                or snap.get('snapshot_id') != doc + ':candidate:' + sha[:12]
                or snap.get('version') != str(docs[doc]['version']) + '.candidate.' + sha[:12]):
            finding('SNAPSHOT_INTEGRITY', 'OUTPUT_SNAPSHOT_INVALID', 'Output identity, version or digest mismatch')
    ledger = result['block_ledger']
    if result.get('change_set') != ledger:
        finding('BIDIRECTIONAL_TRACE', 'CHANGESET_LEDGER_MISMATCH', 'ChangeSet does not describe every source/output segment')
    # Exact source coverage is independent of the generator's claimed coverage.
    for doc, snap in docs.items():
        rows = sorted((r for r in ledger if r.get('source_document_id') == doc), key=lambda r: r['start'])
        cursor = 0
        for row in rows:
            if row['start'] != cursor or not row['start'] < row['end'] <= len(snap['content']):
                finding('FULL_COVERAGE', 'SOURCE_COVERAGE_GAP_OR_OVERLAP', 'Source bytes were lost or reused without explicit consolidation')
            cursor = row['end']
        if cursor != len(snap['content']):
            finding('FULL_COVERAGE', 'SOURCE_COVERAGE_INCOMPLETE', 'Source tail is untracked')
    for doc, snap in outputs.items():
        rows = sorted((r for r in ledger if r['output_document_id'] == doc and not r.get('alias')), key=lambda r: r['output_start'])
        cursor = 0
        for row in rows:
            if row['output_start'] != cursor or not row['output_start'] < row['output_end'] <= len(snap['content']):
                finding('FULL_COVERAGE', 'OUTPUT_COVERAGE_GAP_OR_OVERLAP', 'Output contains untraced, overlapping or missing text')
            cursor = row['output_end']
        if cursor != len(snap['content']):
            finding('FULL_COVERAGE', 'UNSUPPORTED_NEW_OUTPUT', 'Output text has no complete provenance')
    _check_physical_order(bundle, analysis, org, docs, ledger, finding)
    units = {u['id']: u for u in analysis['units']}
    entries = {e['unit_id']: e for e in preview['expression_plan']['entries']}
    constraints = expression.contract_constraints(bundle['writing_contract'])
    allowed_patches = {}
    for fragment in preview['preview_fragments']:
        span = fragment['source_span']
        if reconstruction.bounded_text(entries[fragment['unit_id']], span['quote'], fragment['content'], constraints):
            allowed_patches[(span['start'], span['end'])] = fragment['content']
    # Replay each source-derived segment, not a concatenation of preview fragments.
    for row in ledger:
        snap = outputs[row['output_document_id']]
        actual = snap['content'][row['output_start']:row['output_end']]
        if actual != row['text']:
            finding('BIDIRECTIONAL_TRACE', 'LEDGER_OUTPUT_MISMATCH', 'Ledger does not match actual output slice')
        doc = row['source_document_id']
        if doc is None:
            if row['treatment'] != 'SEPARATOR' or not actual or actual.strip():
                finding('BIDIRECTIONAL_TRACE', 'UNSUPPORTED_NEW_CLAIM', 'Only whitespace separators may lack a source')
            continue
        expected = docs[doc]['content'][row['start']:row['end']]
        if doc == source_doc:
            for (start, end), after in sorted(allowed_patches.items(), reverse=True):
                if row['start'] <= start < end <= row['end']:
                    expected = expected[:start-row['start']] + after + expected[end-row['start']:]
        if expected != actual:
            finding('PROTECTED_INFORMATION', 'UNAUTHORIZED_SOURCE_CHANGE', 'Actual output loses or changes source information outside a bounded edit')
        if row.get('alias'):
            group = next((g for g in org.get('consolidation_groups', []) if g['id'] == row.get('group_id')), {})
            if group.get('blocked') is not False or group.get('compatibility_status') != 'compatible':
                finding('ORGANIZATION_FIDELITY', 'UNAUTHORIZED_CONSOLIDATION', 'Source alias lacks a verified consolidation group')
    placements = {p['unit_id']: p for p in org['placements']}
    scopes = {s['scope_id']: expression.organization.parse_output_scope_entry(s)['document_id']
              for s in bundle['writing_contract']['output_scopes']}
    traces = {t['unit_refs'][0]: t for t in result['trace']}
    if set(traces) != set(units) or len(traces) != len(result['trace']):
        finding('BIDIRECTIONAL_TRACE', 'INFORMATION_UNIT_OMITTED', 'Every original unit must have exactly one trace')
    for uid, unit in units.items():
        trace = traces.get(uid)
        if not trace:
            continue
        if (trace.get('unit_refs') != [uid] or trace.get('source_spans') != unit['source_spans']
                or trace.get('element_refs') != [e['id'] for e in unit['elements']]
                or len(trace.get('output_spans', [])) != len(unit['source_spans'])):
            finding('BIDIRECTIONAL_TRACE', 'UNIT_TRACE_INVALID', 'Unit/element provenance was changed or omitted')
            continue
        plc = placements[uid]
        expected_doc = scopes[plc['targets'][0]['scope_id']] if plc['action'] == 'MOVE' else source_doc
        for src, out in zip(unit['source_spans'], trace['output_spans']):
            snap = outputs.get(out['document_id'])
            if (not snap or out['document_id'] != expected_doc or snap['sha256'] != out.get('snapshot_sha256')
                    or not 0 <= out['start'] < out['end'] <= len(snap['content'])
                    or snap['content'][out['start']:out['end']] != out.get('quote')):
                finding('ORGANIZATION_FIDELITY', 'ACTUAL_PLACEMENT_MISMATCH', 'Actual unit is not in its independently verified destination')
                continue
            expected_text = allowed_patches.get((src['start'], src['end']), src['quote'])
            if out['quote'] != expected_text:
                finding('PROTECTED_INFORMATION', 'UNIT_INFORMATION_LOSS', 'Actual unit text lost source facts or held expressions')
            # Bind trace locations to provenance ledger; matching text elsewhere is insufficient.
            mapped = []
            rows = sorted((r for r in ledger if r['source_document_id'] == source_doc
                           and r['start'] < src['end'] and src['start'] < r['end']), key=lambda r: r['start'])
            for row in rows:
                local_start, local_end = max(row['start'], src['start']), min(row['end'], src['end'])
                delta = sum(len(text) - (end-start) for (start, end), text in allowed_patches.items()
                            if row['start'] <= start < end <= local_start)
                start = row['output_start'] + local_start - row['start'] + delta
                end_delta = sum(len(text) - (end-start) for (start, end), text in allowed_patches.items()
                                if local_start <= start < end <= local_end)
                mapped.append((row['output_document_id'], start, start + local_end - local_start + end_delta))
            expected_location = (mapped[0][0], mapped[0][1], mapped[-1][2]) if mapped else None
            contiguous = all(a[0] == b[0] and a[2] == b[1] for a, b in zip(mapped, mapped[1:]))
            if not contiguous or (out['document_id'], out['start'], out['end']) != expected_location:
                finding('BIDIRECTIONAL_TRACE', 'TRACE_SOURCE_OUTPUT_MISMATCH', 'Unit trace is detached from its actual source segment')
        target = plc.get('targets', [{}])[0]
        anchor = traces.get(target.get('anchor_unit_id'))
        relative = target.get('anchor_relative_position')
        if anchor and relative in {'before', 'after'}:
            a, b = trace['output_spans'][0], anchor['output_spans'][0]
            if a['document_id'] == b['document_id'] and not (
                    (relative == 'before' and a['end'] <= b['start']) or (relative == 'after' and b['end'] <= a['start'])):
                finding('ORGANIZATION_FIDELITY', 'PLACEMENT_ORDER_MISMATCH', 'Explicit placement order was not respected')
    for f in result.get('findings', []):
        if f['severity'] == 'ERROR':
            finding('FULL_COVERAGE', f['rule_id'], f['message'])
        elif f['rule_id'] in {'SECTION_PATH_UNRESOLVED', 'EXPRESSION_CHANGE_HELD', 'ORGANIZATION_PROPOSAL_HELD'}:
            check = 'EXPRESSION_FIDELITY' if f['rule_id'] == 'EXPRESSION_CHANGE_HELD' else 'ORGANIZATION_FIDELITY'
            finding(check, f['rule_id'], f['message'], 'WARNING')
    finding('EXPRESSION_FIDELITY', 'FINAL_SEMANTIC_REVIEW_NOT_IMPLEMENTED', 'Whole-document semantic review has not run', 'WARNING')
    finding('APPROVAL_BOUNDARY', 'FINAL_APPROVAL_NOT_IMPLEMENTED', 'No trusted semantic/human approval path exists', 'WARNING')


def _check_physical_order(bundle, analysis, org, docs, ledger, finding):
    """Independently derive authorized node order from source blocks and plan.

    Coverage alone is insufficient: even unchanged text cannot be reordered or
    transferred arbitrarily. Destination-origin text has no move authorization.
    """
    doc = bundle['document_snapshot']['document_id']
    blocks = pipeline.parse_markdown_blocks(docs[doc])
    by_id = {b['block_id']: b for b in blocks}
    units = {u['id']: u for u in analysis['units']}
    plcs = {p['unit_id']: p for p in org['placements']}
    scopes = {s['scope_id']: expression.organization.parse_output_scope_entry(s)['document_id']
              for s in bundle['writing_contract']['output_scopes']}
    unit_blocks = {}
    for uid, unit in units.items():
        spans = unit['source_spans']
        if len(spans) == 1:
            block = by_id[spans[0]['block_id']]
            if block['kind'] == 'paragraph' and block['text'].strip() == spans[0]['quote']:
                unit_blocks[uid] = block['block_id']
    orders = {key: [(key, 'original')] if key != doc else [(doc, b['block_id']) for b in blocks] for key in docs}
    moves, aliases = {}, {}
    for uid, plc in plcs.items():
        if plc['disposition'] != 'placed':
            continue
        if plc['action'] == 'MOVE' and uid in unit_blocks:
            bid = unit_blocks[uid]
            moves[bid] = scopes[plc['targets'][0]['scope_id']]
        if plc['action'] == 'CONSOLIDATE' and uid in unit_blocks and plc.get('consolidated_into') in unit_blocks:
            group = next((g for g in org.get('consolidation_groups', []) if g['id'] == plc.get('consolidation_group_id')), {})
            primary = plc['consolidated_into']
            if uid in group.get('member_unit_ids', []) and primary in group.get('member_unit_ids', []):
                aliases[unit_blocks[uid]] = (unit_blocks[primary], group['id'])
    for target in set(moves.values()):
        if any(b['kind'] == 'unsupported' for b in pipeline.parse_markdown_blocks(docs[target])):
            finding('CROSS_DOCUMENT_INTEGRITY', 'UNSAFE_DESTINATION_BOUNDARY', 'MOVE would append into an unresolved Markdown construct')
    for bid, target in moves.items():
        orders[doc].remove((doc, bid))
        orders[target].append((doc, bid))
    for bid in aliases:
        orders[doc].remove((doc, bid))
    # Re-resolve existing heading paths independently of the reconstruction code.
    heading_paths, stack = [], []
    for block in blocks:
        if block['kind'] == 'heading':
            text = block['text'].strip()
            level = len(text) - len(text.lstrip('#'))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, text[level:].strip()))
            heading_paths.append((block['block_id'], level, [t for _, t in stack]))
    sections = {}
    for uid, plc in plcs.items():
        if uid not in unit_blocks or plc['action'] != 'KEEP':
            continue
        key = (doc, unit_blocks[uid])
        target = plc['targets'][0]
        anchor = target.get('anchor_unit_id')
        relative = target.get('anchor_relative_position')
        if anchor in unit_blocks and relative in {'before', 'after'}:
            anchor_key = (doc, unit_blocks[anchor])
            orders[doc].remove(key)
            orders[doc].insert(orders[doc].index(anchor_key) + (relative == 'after'), key)
        elif target.get('section_path'):
            path = target['section_path']
            found = [(bid, level) for bid, level, titles in heading_paths
                     if len(path) <= len(titles) and titles[-len(path):] == path]
            if len(found) == 1:
                sections[key] = (*found[0], target.get('relative_order', 0))
            else:
                finding('ORGANIZATION_FIDELITY', 'SECTION_PATH_UNRESOLVED', 'Symbolic section has no unique existing heading', 'WARNING')
    for heading, level in sorted({(v[0], v[1]) for v in sections.values()}):
        selected = sorted((k for k in orders[doc] if k in sections and sections[k][0] == heading),
                          key=lambda k: (sections[k][2], by_id[k[1]]['start']))
        for key in selected:
            orders[doc].remove(key)
        index = orders[doc].index((doc, heading)) + 1
        while index < len(orders[doc]):
            block = by_id[orders[doc][index][1]]
            if block['kind'] == 'heading':
                text = block['text'].strip()
                if len(text) - len(text.lstrip('#')) <= level:
                    break
            index += 1
        orders[doc][index:index] = selected
    # Whitespace is syntax in Markdown. Only the exact newline separator at a
    # verified incoming MOVE boundary may be synthesized, never arbitrary indent.
    for target_doc in docs:
        rows = sorted((r for r in ledger if not r.get('alias') and r['output_document_id'] == target_doc),
                      key=lambda r: r['output_start'])
        prefix = ''
        for index, row in enumerate(rows):
            if row['source_document_id'] is None:
                following = rows[index+1] if index+1 < len(rows) else None
                block = next((b for b in blocks if following and following['source_document_id'] == doc
                              and following['start'] == b['start']), None)
                expected = '\n' if prefix.endswith('\n') else '\n\n'
                if (not prefix or prefix.endswith('\n\n') or not block
                        or moves.get(block['block_id']) != target_doc or target_doc == doc or row['text'] != expected):
                    finding('PROTECTED_INFORMATION', 'UNAUTHORIZED_MARKDOWN_SEPARATOR', 'Source-less whitespace is not an authorized MOVE boundary')
            elif row['source_document_id'] == doc:
                block = next((b for b in blocks if row['start'] == b['start']), None)
                if block and moves.get(block['block_id']) == target_doc and target_doc != doc and not prefix.endswith('\n\n'):
                    finding('PROTECTED_INFORMATION', 'MISSING_MOVE_SEPARATOR', 'Incoming paragraph would concatenate with destination syntax')
            prefix += row['text']
    actual = {key: [] for key in docs}
    piece_cursors = {}
    for row in sorted((r for r in ledger if not r.get('alias') and r['source_document_id'] is not None),
                      key=lambda r: (r['output_document_id'], r['output_start'])):
        source_doc, target_doc = row['source_document_id'], row['output_document_id']
        if source_doc != doc:
            if target_doc != source_doc or row['treatment'] != 'KEEP':
                finding('CROSS_DOCUMENT_INTEGRITY', 'UNAUTHORIZED_DESTINATION_TRANSFER', 'Existing destination content must remain unchanged in its own document')
            keys = [((source_doc, 'original'), row['start'], row['end'], 0, len(docs[source_doc]['content']))]
        else:
            keys = [((doc, b['block_id']), max(row['start'], b['start']), min(row['end'], b['end']), b['start'], b['end'])
                    for b in blocks if row['start'] < b['end'] and b['start'] < row['end']]
        for key, start, end, base_start, base_end in keys:
            if not actual[target_doc] or actual[target_doc][-1] != key:
                actual[target_doc].append(key)
            previous = piece_cursors.get(key, base_start)
            if start != previous:
                finding('ORGANIZATION_FIDELITY', 'BLOCK_PIECE_ORDER_MISMATCH', 'Source pieces were reversed inside a retained block')
            piece_cursors[key] = end
    if actual != orders:
        finding('ORGANIZATION_FIDELITY', 'UNAUTHORIZED_BLOCK_ORDER', 'Actual document order differs from authorized block placement')
    for row in ledger:
        if not row.get('alias'):
            continue
        block = next((b for b in blocks if row['source_document_id'] == doc
                      and (row['start'], row['end']) == (b['start'], b['end'])), None)
        if not block or block['block_id'] not in aliases:
            finding('ORGANIZATION_FIDELITY', 'UNAUTHORIZED_CONSOLIDATION_MEMBER', 'Alias is not an authorized secondary member')
            continue
        primary, group_id = aliases[block['block_id']]
        primary_block = by_id[primary]
        primary_rows = [r for r in ledger if not r.get('alias') and r['source_document_id'] == doc
                        and primary_block['start'] <= r['start'] < r['end'] <= primary_block['end']]
        if (not primary_rows or row.get('group_id') != group_id or row['treatment'] != 'CONSOLIDATE'
                or row['output_document_id'] != doc
                or row['output_start'] != min(r['output_start'] for r in primary_rows)
                or row['output_end'] != max(r['output_end'] for r in primary_rows)):
            finding('ORGANIZATION_FIDELITY', 'CONSOLIDATION_PRIMARY_MISMATCH', 'Alias does not reference its designated whole primary block')



def verify_final_report(bundle, analysis, org, preview, result, report, **kwargs):
    expected = validate_final_result(bundle, analysis, org, preview, result, **kwargs)
    valid = expression.organization.verify_self_digest(report, 'report_sha256')[0] and report == expected
    return {'valid': valid, 'gate_state': expected['gate_state'] if valid else 'FAIL',
            'reason': None if valid else 'FORGED_OR_STALE_FINAL_REPORT'}

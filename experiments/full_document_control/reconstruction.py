"""Source-preserving, read-only full Markdown candidate reconstruction.

Complete snapshots are structural candidates, never authorizations. Expressions
outside the bounded deterministic edit set are held; unsupported structural plans
remain previews. No source file is written.
"""
import copy
import expression
import expression_validator

pipeline = expression.pipeline
organization = expression.organization
VERSION = 'full-document-reconstruction-v1'


class IncompleteSnapshot(ValueError):
    pass


class OutputScopeError(ValueError):
    def __init__(self, rule_id):
        self.rule_id = rule_id
        super().__init__(rule_id)


def validate_document_scopes(bundle, destinations):
    """Output snapshots are explicit targets, not arbitrary reference material."""
    allowed = set()
    for scope in bundle['writing_contract']['output_scopes']:
        parsed = organization.parse_output_scope_entry(scope)
        if parsed and isinstance(parsed['document_id'], str) and parsed['document_id'].strip():
            allowed.add(parsed['document_id'])
    if bundle['document_snapshot']['document_id'] not in allowed:
        raise OutputScopeError('UNAUTHORIZED_SOURCE_DOCUMENT')
    for snap in destinations:
        if snap['document_id'] not in allowed:
            raise OutputScopeError('UNAUTHORIZED_DESTINATION_DOCUMENT')


def issue(rule, message, severity='WARNING'):
    return {'rule_id': rule, 'message': message, 'severity': severity}


def source_documents(bundle, destinations):
    destinations = list(destinations or [])
    validate_document_scopes(bundle, destinations)
    documents = {}
    for snap in [bundle['document_snapshot']] + destinations:
        doc = snap['document_id']
        if doc in documents or not snap.get('version') or not snap.get('content'):
            raise ValueError('Invalid or duplicate complete document snapshot')
        if snap.get('coverage') != 'complete' or not snap.get('snapshot_id') or snap.get('media_type') != 'text/markdown':
            raise IncompleteSnapshot('Complete Markdown snapshot metadata is required')
        if pipeline.digest_text(snap['content']) != snap.get('sha256'):
            raise ValueError('Corrupt document snapshot')
        documents[doc] = copy.deepcopy(snap)
    return documents


def resolve_section(blocks, path):
    stack, found = [], []
    for block in blocks:
        if block['kind'] != 'heading':
            continue
        stripped = block['text'].strip()
        level = len(stripped) - len(stripped.lstrip('#'))
        title = stripped[level:].strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        titles = [title for _, title in stack]
        if path and len(path) <= len(titles) and titles[-len(path):] == path:
            found.append((block['block_id'], level))
    return found[0] if len(found) == 1 else None


def references(bundle, analysis, org, preview, documents):
    return {**expression.input_references(bundle, analysis, org),
            'expression_preview_sha256': preview.get('revision_sha256'),
            'source_refs': [{'document_id': doc, 'snapshot_id': s.get('snapshot_id'),
                             'version': s['version'], 'sha256': s['sha256']}
                            for doc, s in documents.items()]}


def bounded_text(entry, before, after, constraints):
    if before == after:
        return True
    expected = expression.DeterministicGenerator().generate({
        'before': before, 'operation': entry['operation'], 'constraints': constraints,
        'excluded': entry['excluded']})['text']
    return expected == after


def reconstruct_documents(bundle, analysis, org, preview, *, destination_snapshots=None):
    findings = []
    result = {'version': VERSION, 'meta': {'execution_mode': 'isolated_candidate', 'delivery_approved': False},
              'organization_ref': copy.deepcopy(preview.get('organization_ref')),
              'expression_plan': copy.deepcopy(preview.get('expression_plan')),
              'delivery_state': 'preview', 'output_snapshots': [], 'preview_fragments': copy.deepcopy(preview.get('preview_fragments', [])),
              'change_set': [], 'trace': [], 'block_ledger': [], 'findings': findings,
              'delivery_approved': False, 'stage_transition_allowed': False}
    try:
        docs = source_documents(bundle, destination_snapshots)
        result.update(references(bundle, analysis, org, preview, docs))
        validation = expression_validator.validate_expression_result(bundle, analysis, org, preview,
                                         destination_snapshots=destination_snapshots)
        if validation['gate_state'] == 'FAIL':
            findings.extend(f for f in validation['findings'] if f['severity'] == 'ERROR')
            return expression.seal(result, 'revision_sha256')
        _construct(bundle, analysis, org, preview, docs, result)
    except OutputScopeError as exc:
        findings.append(issue(exc.rule_id, 'Document is not a concrete output scope in the Writing Contract', 'ERROR'))
    except IncompleteSnapshot:
        findings.append(issue('FULL_SNAPSHOT_UNAVAILABLE', 'Complete source/destination snapshot metadata is unavailable'))
    except (KeyError, ValueError, TypeError, IndexError):
        findings.append(issue('RECONSTRUCTION_INPUT_INVALID', 'Cannot resolve complete source artifacts', 'ERROR'))
    return expression.seal(result, 'revision_sha256')


def _construct(bundle, analysis, org, preview, docs, result):
    source_doc = bundle['document_snapshot']['document_id']
    source = docs[source_doc]
    units = {u['id']: u for u in analysis['units']}
    placements = {p['unit_id']: p for p in org['placements']}
    entries = {e['unit_id']: e for e in preview['expression_plan']['entries']}
    constraints = expression.contract_constraints(bundle['writing_contract'])
    findings = result['findings']
    patches = {}
    all_spans = [s for u in units.values() for s in u['source_spans']]
    proposed = {}
    for fragment in preview['preview_fragments']:
        span, text = fragment['source_span'], fragment['content']
        key = (span['start'], span['end'])
        if not bounded_text(entries[fragment['unit_id']], span['quote'], text, constraints):
            findings.append(issue('EXPRESSION_CHANGE_HELD', 'Unverified semantic edit retained as original source'))
            text = span['quote']
        if key in proposed and proposed[key] != text:
            findings.append(issue('OVERLAPPING_REVISIONS', 'Shared source range has conflicting text', 'ERROR'))
            return
        proposed[key] = text
        if text != span['quote']:
            patches[key] = text
    for (start, end), text in patches.items():
        for span in all_spans:
            if start < span['end'] and span['start'] < end and (span['start'], span['end']) != (start, end):
                findings.append(issue('OVERLAPPING_REVISIONS', 'Changed range intersects a distinct unit range', 'ERROR'))
                return
    blocks = pipeline.parse_markdown_blocks(source)
    nodes = {}
    unit_node = {}
    for block in blocks:
        cuts = {block['start'], block['end']}
        block_units = []
        for uid, unit in units.items():
            for span in unit['source_spans']:
                if span['block_id'] == block['block_id']:
                    cuts.update((span['start'], span['end']))
                    block_units.append(uid)
        pieces = []
        points = sorted(cuts)
        for start, end in zip(points, points[1:]):
            before = source['content'][start:end]
            after = patches.get((start, end), before)
            pieces.append({'source_document_id': source_doc, 'start': start, 'end': end,
                           'text': after, 'treatment': 'REVISE' if before != after else 'KEEP'})
        node = {'id': block['block_id'], 'kind': block['kind'], 'pieces': pieces,
                'start': block['start'], 'end': block['end'], 'doc': source_doc}
        nodes[block['block_id']] = node
        for uid in set(block_units):
            spans = units[uid]['source_spans']
            # Structural operations require one complete standalone paragraph.
            if (len(spans) == 1 and block['kind'] == 'paragraph'
                    and source['content'][block['start']:block['end']].strip() == spans[0]['quote']):
                unit_node[uid] = node['id']
    layouts = {source_doc: list(nodes.values())}
    for doc, snap in docs.items():
        if doc != source_doc:
            layouts[doc] = [{'id': doc + ':original', 'kind': 'existing_document', 'doc': doc,
                            'pieces': [{'source_document_id': doc, 'start': 0, 'end': len(snap['content']),
                                        'text': snap['content'], 'treatment': 'KEEP'}]}]
    scopes = {organization.parse_output_scope_entry(s)['scope_id']: organization.parse_output_scope_entry(s)
              for s in bundle['writing_contract']['output_scopes']}
    requests = {}
    aliases = []
    for uid, plc in placements.items():
        if plc['disposition'] in {'blocked', 'flagged'}:
            findings.append(issue('ORGANIZATION_PROPOSAL_HELD', 'Blocked placement remains at its source'))
            continue
        if plc['action'] == 'REMOVE' or plc['disposition'] == 'omitted':
            findings.append(issue('REMOVAL_AUTHORIZATION_UNAVAILABLE', 'No authorized omission executor exists'))
            return
        targets = plc.get('targets', [])
        if len(targets) != 1:
            findings.append(issue('STRUCTURAL_PLAN_UNRESOLVED', 'Exactly one resolvable placement target required'))
            return
        target = targets[0]
        doc = scopes[target['scope_id']]['document_id']
        if plc['action'] == 'MOVE':
            if uid not in unit_node or doc not in layouts:
                findings.append(issue('PARTIAL_BLOCK_MOVE_HELD', 'MOVE needs a whole unprotected paragraph and full destination'))
                return
            node_id = unit_node[uid]
            if node_id in requests and requests[node_id] != doc:
                findings.append(issue('CONFLICTING_BLOCK_PLACEMENT', 'Shared block has competing destinations', 'ERROR'))
                return
            requests[node_id] = doc
        elif plc['action'] == 'CONSOLIDATE':
            primary = plc.get('consolidated_into')
            group = next((g for g in org.get('consolidation_groups', []) if g['id'] == plc.get('consolidation_group_id')), {})
            if (uid not in unit_node or primary not in unit_node or group.get('blocked') is not False
                    or group.get('compatibility_status') != 'compatible'
                    or units[uid]['source_spans'][0]['quote'] != units[primary]['source_spans'][0]['quote']):
                findings.append(issue('CONSOLIDATION_HELD', 'Only verified exact standalone duplicates can be materialized'))
                return
            aliases.append((unit_node[uid], unit_node[primary], group['id']))
    # Never move/delete a block that also carries an independently retained unit.
    for uid, unit in units.items():
        for span in unit['source_spans']:
            block_id = span['block_id']
            if block_id in requests and (placements[uid]['action'] != 'MOVE'
                    or scopes[placements[uid]['targets'][0]['scope_id']]['document_id'] != requests[block_id]):
                findings.append(issue('CONFLICTING_BLOCK_PLACEMENT', 'Shared source block has a surviving source obligation', 'ERROR'))
                return
    for target in set(requests.values()):
        if any(b['kind'] == 'unsupported' for b in pipeline.parse_markdown_blocks(docs[target])):
            findings.append(issue('UNSAFE_DESTINATION_BOUNDARY', 'Destination has an unresolved Markdown construct; append is held'))
            return
    for node_id, doc in requests.items():
        node = nodes[node_id]
        layouts[source_doc].remove(node)
        node['doc'] = doc
        for piece in node['pieces']:
            piece['treatment'] = 'MOVE'
        layouts[doc].append(node)
    alias_nodes = {}
    for secondary, primary, group in aliases:
        if secondary == primary or secondary in requests or primary in requests:
            findings.append(issue('CONSOLIDATION_HELD', 'Overlapping structural operations are unresolved'))
            return
        if nodes[secondary]['pieces'] != nodes[primary]['pieces']:
            # Source offsets differ, compare actual full text instead.
            if ''.join(p['text'] for p in nodes[secondary]['pieces']) != ''.join(p['text'] for p in nodes[primary]['pieces']):
                findings.append(issue('CONSOLIDATION_HELD', 'Duplicate output text must match exactly'))
                return
        layouts[source_doc].remove(nodes[secondary])
        alias_nodes[secondary] = (primary, group)
    # Explicit existing anchors take precedence. Unknown section labels are held,
    # never converted into invented headings.
    section_requests = {}
    for uid, plc in placements.items():
        if plc['action'] != 'KEEP' or uid not in unit_node:
            continue
        target = plc['targets'][0]
        node = nodes[unit_node[uid]]
        anchor_uid = target.get('anchor_unit_id')
        relation = target.get('anchor_relative_position')
        if anchor_uid and relation in {'before', 'after'}:
            if anchor_uid not in unit_node or unit_node[anchor_uid] == node['id']:
                findings.append(issue('PLACEMENT_ANCHOR_UNRESOLVED', 'Structural anchor is not a standalone paragraph'))
                return
            layout = layouts[source_doc]
            anchor = nodes[unit_node[anchor_uid]]
            if node not in layout or anchor not in layout:
                findings.append(issue('PLACEMENT_ANCHOR_UNRESOLVED', 'Anchor moved to another document'))
                return
            layout.remove(node)
            layout.insert(layout.index(anchor) + (relation == 'after'), node)
        elif target.get('section_path'):
            resolved = resolve_section(blocks, target['section_path'])
            if resolved:
                section_requests[node['id']] = (resolved[0], resolved[1], target.get('relative_order', 0))
            else:
                findings.append(issue('SECTION_PATH_UNRESOLVED', 'Section label does not resolve to one existing heading'))
    for heading_id, level in sorted({(v[0], v[1]) for v in section_requests.values()}):
        layout = layouts[source_doc]
        selected = sorted((node for node in layout if node['id'] in section_requests
                           and section_requests[node['id']][0] == heading_id),
                          key=lambda n: (section_requests[n['id']][2], n['start']))
        for node in selected:
            layout.remove(node)
        index = layout.index(nodes[heading_id]) + 1
        while index < len(layout):
            item = layout[index]
            if item['kind'] == 'heading':
                title = source['content'][item['start']:item['end']].strip()
                if len(title) - len(title.lstrip('#')) <= level:
                    break
            index += 1
        layout[index:index] = selected
    for uid, plc in placements.items():
        target = plc.get('targets', [{}])[0] if plc.get('targets') else {}
        anchor_uid, relative = target.get('anchor_unit_id'), target.get('anchor_relative_position')
        if uid in unit_node and anchor_uid in unit_node and relative in {'before', 'after'}:
            layout = layouts[source_doc]
            node, anchor = nodes[unit_node[uid]], nodes[unit_node[anchor_uid]]
            if node in layout and anchor in layout and ((relative == 'before') != (layout.index(node) < layout.index(anchor))):
                findings.append(issue('PLACEMENT_ORDER_UNRESOLVED', 'Competing placement order cannot be materialized'))
                return
    ledger, snapshots = [], []
    node_output = {}
    for doc, layout in layouts.items():
        content = ''
        for node in layout:
            # Ensure moved paragraphs do not concatenate with existing text.
            if node.get('doc') != source_doc and node['id'] in requests and content and not content.endswith('\n\n'):
                separator = '\n' if content.endswith('\n') else '\n\n'
                ledger.append({'source_document_id': None, 'start': None, 'end': None, 'text': separator,
                               'treatment': 'SEPARATOR', 'output_document_id': doc, 'output_start': len(content),
                               'output_end': len(content) + len(separator), 'alias': False})
                content += separator
            node_output[node['id']] = (doc, len(content))
            for piece in node['pieces']:
                row = {**piece, 'output_document_id': doc, 'output_start': len(content),
                       'output_end': len(content) + len(piece['text']), 'alias': False}
                ledger.append(row)
                content += piece['text']
        sha = pipeline.digest_text(content)
        snapshots.append({'document_id': doc, 'snapshot_id': doc + ':candidate:' + sha[:12],
                          'version': str(docs[doc]['version']) + '.candidate.' + sha[:12],
                          'coverage': 'complete', 'media_type': 'text/markdown', 'content': content, 'sha256': sha})
    for secondary, (primary, group) in alias_nodes.items():
        doc, out_start = node_output[primary]
        node = nodes[secondary]
        text = ''.join(p['text'] for p in node['pieces'])
        ledger.append({'source_document_id': source_doc, 'start': node['start'], 'end': node['end'],
                       'text': text, 'treatment': 'CONSOLIDATE', 'output_document_id': doc,
                       'output_start': out_start, 'output_end': out_start + len(text), 'alias': True, 'group_id': group})
    trace = []
    snapshots_by_doc = {s['document_id']: s for s in snapshots}
    for uid, unit in units.items():
        output_spans = []
        for span in unit['source_spans']:
            covered = sorted((r for r in ledger if r['source_document_id'] == source_doc
                              and r['start'] < span['end'] and span['start'] < r['end']), key=lambda r: r['start'])
            mapped = []
            for row in covered:
                start, end = max(span['start'], row['start']), min(span['end'], row['end'])
                delta = sum(len(text) - (finish-begin) for (begin, finish), text in patches.items()
                            if row['start'] <= begin < finish <= start)
                local_delta = sum(len(text) - (finish-begin) for (begin, finish), text in patches.items()
                                  if start <= begin < finish <= end)
                out_start = row['output_start'] + start - row['start'] + delta
                out_end = out_start + end - start + local_delta
                mapped.append((row['output_document_id'], out_start, out_end))
            if mapped and all(prev[0] == nxt[0] and prev[2] == nxt[1] for prev, nxt in zip(mapped, mapped[1:])):
                doc, start, end = mapped[0][0], mapped[0][1], mapped[-1][2]
                snap = snapshots_by_doc[doc]
                output_spans.append({'document_id': doc, 'snapshot_sha256': snap['sha256'],
                                     'start': start, 'end': end, 'quote': snap['content'][start:end]})
        trace.append({'unit_refs': [uid], 'element_refs': [e['id'] for e in unit['elements']],
                      'source_spans': copy.deepcopy(unit['source_spans']), 'output_spans': output_spans})
    result.update(delivery_state='candidate', preview_fragments=[], output_snapshots=snapshots,
                  block_ledger=ledger, trace=trace, change_set=copy.deepcopy(ledger))

"""Expression Refinement v1: pure, source-bound previews; never writes documents.

A generator is a callable(request) -> {'text': str}, or an object with generate.
It proposes text only. Approval, placement and independent validation are external.
"""
import copy
from pathlib import Path
import re
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import organization

pipeline = organization.pipeline
VERSION = 'expression-refinement-prototype-v1'
PLAN_VERSION = 'expression-plan-v1'
RESULT_VERSION = 'revision-result-v1'
OPERATIONS = {'KEEP', 'REVISE', 'COMPRESS'}
EXCLUDED_KINDS = {'heading', 'table', 'code_block', 'blockquote', 'unsupported'}
INLINE_PROTECTED = re.compile(r'(`+)[^`\n]+\1|https?://[^\s<>]+|"[^"\n]+"|“[^”\n]+”|‘[^’\n]+’')


def seal(value, field):
    value[field] = pipeline.canonical_json_digest({k: v for k, v in value.items() if k != field})
    return value


def contract_constraints(contract):
    """Parse explicit prototype directives without changing WritingContract schema.

    Other natural-language constraints remain unresolved human obligations.
    """
    constraints = {'register': contract.get('register'), 'terminology': {},
                   'preserve': [], 'forbid': [], 'exclude_blocks': [], 'unresolved': []}
    for rule in contract.get('constraints', []):
        if isinstance(rule, str) and rule.startswith('TERM: ') and ' => ' in rule:
            old, new = rule[6:].split(' => ', 1)
            if old and new and old not in constraints['terminology']:
                constraints['terminology'][old] = new
            else:
                constraints['unresolved'].append(rule)
        elif isinstance(rule, str) and rule.startswith('PRESERVE: ') and rule[10:]:
            constraints['preserve'].append(rule[10:])
        elif isinstance(rule, str) and rule.startswith('FORBID: ') and rule[8:]:
            constraints['forbid'].append(rule[8:])
        elif isinstance(rule, str) and rule.startswith('EXCLUDE_BLOCK: ') and rule[15:]:
            constraints['exclude_blocks'].append(rule[15:])
        else:
            constraints['unresolved'].append(rule)
    # Logical design includes richer terminology; this prototype cannot silently
    # interpret a contract field unsupported by the existing input resolver.
    if 'terminology' in contract:
        constraints['unresolved'].append('Unsupported terminology field; use TERM directives')
    return constraints


def span_excluded(span, blocks, constraints):
    """Use the full original block even when the extraction cites only a substring."""
    block = blocks[span['block_id']]
    if block['kind'] in EXCLUDED_KINDS or span['block_id'] in constraints['exclude_blocks']:
        return True
    for match in INLINE_PROTECTED.finditer(block['text']):
        start, end = block['start'] + match.start(), block['start'] + match.end()
        if span['start'] < end and start < span['end']:
            if not (span['start'] <= start and end <= span['end']):
                return True  # Fragment cuts through an immutable inline context.
    return False


def input_references(bundle, analysis, org_plan):
    return {
        'analysis_ref': {'version': analysis.get('version'), 'analysis_sha256': analysis.get('analysis_sha256'),
                         'snapshot_id': bundle['document_snapshot']['snapshot_id'],
                         'snapshot_version': bundle['document_snapshot']['version'],
                         'snapshot_sha256': bundle['document_snapshot']['sha256'],
                         'contract_version': bundle['writing_contract']['version'],
                         'contract_sha256': pipeline.canonical_json_digest(bundle['writing_contract'])},
        'organization_ref': {'version': org_plan.get('version'), 'plan_sha256': org_plan.get('plan_sha256')},
    }


def build_expression_plan(bundle, analysis, organization_plan, *, operations=None,
                          destination_snapshots=None, validation_report=None):
    """Build a plan for each source unit. Invalid upstream plans are not editable."""
    report = organization.validate_organization_plan(
        bundle, analysis, organization_plan, destination_snapshots=destination_snapshots,
        validation_report=validation_report)
    if report['gate_state'] in {'FAIL', 'STOPPED'}:
        raise ValueError('UPSTREAM_ORGANIZATION_INVALID: ' + '; '.join(report['diagnostics']))
    operations = operations or {}
    units = {u['id']: u for u in analysis['units']}
    if set(operations) - set(units) or any(op not in OPERATIONS for op in operations.values()):
        raise ValueError('Expression operations must be KEEP/REVISE/COMPRESS on existing units')
    constraints = contract_constraints(bundle['writing_contract'])
    placements = {p['unit_id']: p for p in organization_plan['placements']}
    blocks = {b['block_id']: b for b in pipeline.parse_markdown_blocks(bundle['document_snapshot'])}
    entries = []
    for uid, unit in units.items():
        spans = copy.deepcopy(unit.get('source_spans', []))
        if not spans:
            raise ValueError('Source spans required for Expression preview: ' + uid)
        for span in spans:
            block = blocks.get(span.get('block_id'), {})
            content = bundle['document_snapshot']['content']
            if (span.get('snapshot_sha256') != bundle['document_snapshot']['sha256']
                    or type(span.get('start')) is not int or type(span.get('end')) is not int
                    or not 0 <= span['start'] < span['end'] <= len(content)
                    or content[span['start']:span['end']] != span.get('quote')
                    or not block or not block['start'] <= span['start'] < span['end'] <= block['end']):
                raise ValueError('Invalid source span for ' + uid)
        excluded = any(span_excluded(s, blocks, constraints) for s in spans)
        entries.append({'id': 'expr-' + uid, 'unit_id': uid,
                        'source_spans': spans, 'placement': copy.deepcopy(placements[uid]),
                        'operation': operations.get(uid, 'KEEP' if excluded else 'REVISE'),
                        'excluded': excluded, 'protected_elements': copy.deepcopy(unit.get('elements', [])),
                        'relations': copy.deepcopy(unit.get('relations', [])),
                        'rationale': 'Improve expression within the existing placement; preserve every source element',
                        'evidence': [s['block_id'] for s in spans]})
    plan = {'version': PLAN_VERSION, 'producer': VERSION, 'id': 'expression-preview-plan',
            **input_references(bundle, analysis, organization_plan), 'constraints': constraints,
            'entries': entries}
    return seal(plan, 'plan_sha256')


class DeterministicGenerator:
    """Bounded Korean endings, explicit terminology, and repeated-word cleanup.

    These rules generate candidates, not a proof of general semantic equivalence.
    Protected inline spans are left byte-for-byte intact.
    """
    def generate(self, request):
        before = request['before']
        if request['excluded'] or request['operation'] == 'KEEP':
            return {'text': before}
        constraints = request['constraints']

        def edit(text):
            for old, new in constraints.get('terminology', {}).items():
                # Match canonical occurrences first so repeated refinement is idempotent.
                pattern = re.compile(re.escape(new) + '|' + re.escape(old))
                text = pattern.sub(lambda match: match.group(0) if match.group(0) == new else new, text)
            if request['operation'] == 'COMPRESS':
                text = re.sub(r'(?<!\w)([가-힣A-Za-z]+)(?:[ \t]+\1)+(?!\w)', r'\1', text)
                text = re.sub(r'[ \t]{2,}', ' ', text)
            register = constraints.get('register')
            endings = {
                '합니다체': [('이다.', '입니다.'), ('초다.', '초입니다.'), ('한다.', '합니다.'),
                           ('있다.', '있습니다.'), ('없다.', '없습니다.')],
                '해요체': [('이다.', '이에요.'), ('초다.', '초예요.'), ('한다.', '해요.'),
                         ('있다.', '있어요.'), ('없다.', '없어요.')],
                '한다체': [('입니다.', '이다.'), ('합니다.', '한다.'), ('있습니다.', '있다.'),
                         ('없습니다.', '없다.')],
            }
            for old, new in endings.get(register, []):
                text = re.sub(re.escape(old) + r'(?=\s|$)', lambda _: new, text)
            return text

        pieces, offset = [], 0
        for match in INLINE_PROTECTED.finditer(before):
            pieces.extend([edit(before[offset:match.start()]), match.group(0)])
            offset = match.end()
        pieces.append(edit(before[offset:]))
        return {'text': ''.join(pieces)}


def generate_revision_result(bundle, analysis, organization_plan, *, generator=None,
                             operations=None, destination_snapshots=None, validation_report=None):
    """Generate isolated excerpt snapshots. Does not execute an Organization action."""
    plan = build_expression_plan(bundle, analysis, organization_plan, operations=operations,
                                 destination_snapshots=destination_snapshots, validation_report=validation_report)
    generator = generator or DeterministicGenerator()
    generate = generator.generate if hasattr(generator, 'generate') else generator
    fragments, changes, trace, findings = [], [], [], []
    for entry in plan['entries']:
        for index, span in enumerate(entry['source_spans']):
            fid = f"fragment-{entry['unit_id']}-{index}"
            before = span['quote']
            request = {'unit_id': entry['unit_id'], 'before': before, 'operation': entry['operation'],
                       'excluded': entry['excluded'], 'constraints': copy.deepcopy(plan['constraints']),
                       'protected_elements': copy.deepcopy(entry['protected_elements']),
                       'relations': copy.deepcopy(entry['relations']), 'source_span': copy.deepcopy(span)}
            try:
                response = generate(copy.deepcopy(request))
                if not isinstance(response, dict) or not isinstance(response.get('text'), str) or not response['text'].strip():
                    raise ValueError('Generator must return a nonempty text string')
                # Store only JSON-safe response fields needed for the audit.
                record = {'status': 'completed', 'response': copy.deepcopy(response)}
                pipeline.canonical_json_digest(record)
                after = response['text']
            except Exception as exc:
                after = before
                record = {'status': 'execution_error', 'error_type': type(exc).__name__}
                findings.append({'rule_id': 'GENERATION_ERROR', 'severity': 'WARNING', 'fragment_id': fid,
                                 'message': 'Original source preserved; generator failed'})
            operation = 'KEEP' if before == after else entry['operation']
            sha = pipeline.digest_text(after)
            output_span = {'fragment_id': fid, 'snapshot_sha256': sha, 'start': 0, 'end': len(after)}
            fragments.append({'fragment_id': fid, 'unit_id': entry['unit_id'], 'coverage': 'excerpt',
                              'source_span': copy.deepcopy(span), 'content': after, 'sha256': sha,
                              'placement_ref': pipeline.canonical_json_digest(entry['placement']),
                              'context': {'source_block_id': span['block_id'], 'organization_disposition': entry['placement']['disposition'],
                                          'unresolved_plan': True}, 'generation': record})
            changes.append({'id': 'change-' + fid, 'fragment_id': fid, 'unit_id': entry['unit_id'],
                            'expression_entry_id': entry['id'], 'operation': operation,
                            'source_span': copy.deepcopy(span), 'output_span': copy.deepcopy(output_span),
                            'before': before, 'before_sha256': pipeline.digest_text(before), 'after': after,
                            'after_sha256': sha, 'producer': VERSION})
            trace.append({'unit_refs': [entry['unit_id']],
                          'element_refs': [e['id'] for e in entry['protected_elements']],
                          'source_spans': [copy.deepcopy(span)], 'output_spans': [copy.deepcopy(output_span)],
                          'treatment': operation, 'justification': entry['id']})
    result = {'version': RESULT_VERSION, 'meta': {'producer': VERSION, 'preview_only': True,
              'execution_mode': 'preview', 'stage_transition_allowed': False},
              'organization_ref': copy.deepcopy(plan['organization_ref']), 'expression_plan': plan,
              'output_snapshots': [], 'preview_fragments': fragments, 'change_set': changes,
              'trace': trace, 'findings': findings, 'delivery_state': 'preview',
              'delivery_approved': False, 'next_stage_allowed': False}
    return seal(result, 'revision_sha256')


def create_expression_preview(bundle, analysis, organization_plan, **kwargs):
    from expression_validator import validate_expression_result
    result = generate_revision_result(bundle, analysis, organization_plan, **kwargs)
    report = validate_expression_result(bundle, analysis, organization_plan, result,
                                       destination_snapshots=kwargs.get('destination_snapshots'),
                                       validation_report=kwargs.get('validation_report'))
    return {'revision_result': result, 'validation_report': report, 'preview_only': True,
            'next_stage_allowed': False}


def execute_authorized_expression(bundle, analysis, organization_plan, *, validation_report=None,
                                  destination_snapshots=None):
    report = organization.validate_organization_plan(bundle, analysis, organization_plan,
                validation_report=validation_report, destination_snapshots=destination_snapshots)
    return {'status': 'NOT_IMPLEMENTED', 'gate_state': 'FAIL' if report['gate_state'] == 'FAIL' else 'REVIEW',
            'reason': 'Authorized Expression execution and full-document final validation are not implemented',
            'upstream_gate_state': report['gate_state'], 'stage_transition_allowed': False,
            'delivery_approved': False, 'next_stage_allowed': False}


def main(argv=None):
    """Read JSON artifacts and print an audited preview; no write/overwrite option."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_bundle', type=Path)
    parser.add_argument('analysis', type=Path)
    parser.add_argument('organization_plan', type=Path)
    parser.add_argument('--operations', type=Path, help='JSON mapping unit IDs to KEEP/REVISE/COMPRESS')
    parser.add_argument('--destination-snapshots', type=Path, help='JSON list of destination snapshots')
    args = parser.parse_args(argv)
    def read(path):
        return pipeline.load_json_bytes(path.read_bytes())
    try:
        preview = create_expression_preview(read(args.input_bundle), read(args.analysis), read(args.organization_plan),
                    operations=read(args.operations) if args.operations else None,
                    destination_snapshots=read(args.destination_snapshots) if args.destination_snapshots else None)
    except Exception as exc:
        print(json.dumps({'status': 'execution_error', 'error_type': type(exc).__name__,
                          'delivery_approved': False, 'next_stage_allowed': False}))
        return 2
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Reproduce G2-C candidates and audits from input-only IR and separate synthetic cases."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/full_document_control'))
import document_set as core
import document_set_analysis as analysis
import document_set_planning as planning
import document_set_reconstruction as reconstruction
from ir_document_set_adapter import from_ir_input


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _synthetic(include_hold):
    specifications = [
        ('catalog', '# Catalog\n\nRecord the item label.\n\nPhotograph the storage shelf.\n'),
        ('log', '# Log\n\nArchive the inventory.\n'),
    ]
    if include_hold:
        specifications.extend([
            ('operations', '# Operations\n\nIf the alarm sounds, wait.\n'),
            ('safety', '# Safety\n\nReport the drill date.\n'),
        ])
    docs = []
    for did, content in specifications:
        sha = core._digest(content)
        docs.append(dict(document_id=did, role=did, authority='Synthetic document owner', access='edit',
                         completeness='complete', source_scope=None, content=content, sha256=sha,
                         provenance=dict(kind='supplied_snapshot', source_id='g2-c-synthetic',
                                         path=did + '.md', snapshot_sha256=sha),
                         output_target=True, purpose=None, audience=None, explicit_constraints=[],
                         pending_questions=[]))
    return dict(schema_version=core.VERSION, contract_id='synthetic-partial' if include_hold else 'synthetic-move',
                request='Apply the explicitly proposed paragraph relocations.', context='Offline synthetic example',
                audience=None, purpose=None, explicit_constraints=['Preserve all existing conditions.'],
                pending_questions=[], origin=dict(source_id='g2-c-synthetic',
                                                  input_sha256=core.contract_digest(specifications), format='synthetic'),
                document_set_completeness='complete', documents=docs,
                output_scopes=[dict(scope_id=d['document_id'] + '-output', document_id=d['document_id']) for d in docs],
                additional_permissions=dict.fromkeys(('external_lookup', 'create_document', 'apply_files'), 'not_granted'),
                delivery=dict(mode='reviewable_candidate_only', required='Review only'))


def _proposals(artifact, scenario):
    units = {u['quote'].strip(): u['unit_id'] for u in artifact['units'] if u['kind'] == 'paragraph'}
    if scenario == 'synthetic-move':
        changes = [('move-photo', 'MOVE', 'Photograph the storage shelf.', 'log', dict(placement='append'))]
    elif scenario == 'synthetic-partial':
        changes = [
            ('place-label', 'PLACE', 'Record the item label.', 'catalog',
             dict(anchor_unit_id=units['Photograph the storage shelf.'], position='after')),
            ('move-alarm', 'MOVE', 'If the alarm sounds, wait.', 'safety', dict(placement='append')),
        ]
    else:
        changes = []
    return [dict(task_id=tid, action=action, unit_ids=[units[text]], target_document_id=target,
                 evidence_unit_ids=[units[text]], reason='Explicit synthetic relocation proposal',
                 parameters=parameters, depends_on=[]) for tid, action, text, target, parameters in changes]


def build_record(name, contract):
    # For this local input-only demonstration the trusted caller constructs and
    # pins both requests. Generic Core receives pins independently of artifacts.
    pin = core.contract_digest(contract)
    artifact = analysis.analyze_document_set(contract, trusted_contract_sha256=pin)
    plan_request = planning.make_request(_proposals(artifact, name))
    request_pin = core.contract_digest(plan_request)
    plan = planning.plan_document_set(contract, artifact, plan_request,
                                      trusted_contract_sha256=pin, trusted_request_sha256=request_pin)
    grant = reconstruction.make_candidate_request(
        plan, task_ids=[t['task_id'] for t in plan['tasks'] if t['status'] == 'eligible'],
        document_ids=[s['document_id'] for s in contract['output_scopes']])
    inputs = dict(contract=contract, analysis=artifact, plan=plan, plan_request=plan_request,
                  candidate_request=grant, trusted_contract_sha256=pin,
                  trusted_request_sha256=request_pin, trusted_candidate_request_sha256=core.contract_digest(grant))
    result = reconstruction.reconstruct_document_set(**inputs)
    independently_checked = reconstruction.validate_candidate_result(result, **inputs)
    if independently_checked['status'] != 'passed' or independently_checked != result['structure']:
        raise ValueError('Offline structural verification failed')
    return dict(inputs=inputs, result=result)


def build_results():
    inputs = ROOT / 'evaluation/integrated_reconstruction/inputs'
    records = {f'IR-{i:03}': build_record(f'IR-{i:03}', from_ir_input(_read(inputs / f'IR-{i:03}.json')))
               for i in (1, 2, 3)}
    records['synthetic-move'] = build_record('synthetic-move', _synthetic(include_hold=False))
    records['synthetic-partial'] = build_record('synthetic-partial', _synthetic(include_hold=True))
    expected = {'IR-001': (2, []), 'IR-002': (2, []), 'IR-003': (1, []),
                'synthetic-move': (2, ['move-photo']), 'synthetic-partial': (4, ['place-label'])}
    summary = []
    for name, record in records.items():
        result = record['result']
        outputs = result['change_ledger']
        changed = [did for did, row in outputs.items() if row['changed']]
        if (len(outputs), result['executed']) != expected[name] or (name.startswith('IR-') and changed):
            raise ValueError('Offline candidate differs from the expected scenario shape')
        summary.append(dict(
            scenario=name, input_documents=len(record['inputs']['contract']['documents']),
            output_documents=list(outputs), changed_documents=changed, executed=result['executed'],
            planned_statuses=dict(Counter(t['planned_status'] for t in result['tasks'])),
            execution_statuses=dict(Counter(t['status'] for t in result['tasks'])),
            held={t['task_id']: t['reasons'] for t in result['tasks'] if t['status'] == 'held'},
            hitl_questions=len(result['hitl_questions']), execution_state=result['execution_state'],
            structure=result['structure'], gate_state=result['gate_state'], model_calls=result['model_calls']))
    return records, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New evidence directory')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output directory already exists')
    records, summary = build_results()
    args.output.mkdir(parents=True)
    for name, result in dict(records, summary=summary).items():
        (args.output / (name + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

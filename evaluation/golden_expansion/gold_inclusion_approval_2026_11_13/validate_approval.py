"""Read-only validation of user inclusion intent; never activates a dataset."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASIS = '2bee75af63a0c26a3b3c44c6605d67b2ffbb4bf7'
PRESERVATION_SHA = 'be61fbf0715a774535f0f201040a991973678cda50be4b44650bf4664b451b93'
DECLARATION_SHA = '7973b2f4d54365c34a387eee4a2183e11325b2fec883681fbfbf4c63c4d03555'
PACKAGE = 'evaluation/golden_expansion/gold_inclusion_approval_2026_11_13/'
FINAL_PATH = 'evaluation/golden_expansion/user_final_2026_11_11/events.json'
ACTIVE_PATH = 'evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
IDS = [f'GC-{i:03}' for i in range(1, 13)] + [f'SP-{i:03}' for i in range(13, 18)]
ARTIFACTS = {'README.md', 'VALIDATION.md', 'approval-declaration.json', 'events.json', 'record.schema.json',
             'preserved-files.json', 'validate_approval.py', 'test_approval.py'}
spec = importlib.util.spec_from_file_location(
    'gold_intent_final_submission', ROOT / 'evaluation/golden_expansion/user_final_2026_11_11/validate_submission.py')
final = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def reference(path, pointer):
    return {'path': path, 'sha256': sha((ROOT / path).read_bytes()), 'pointer': pointer}


def validate():
    manifest = load(HERE / 'artifact-manifest.json')
    require(set(manifest) == ARTIFACTS, 'artifact manifest coverage')
    for name, digest in manifest.items():
        require(sha((HERE / name).read_bytes()) == digest, 'artifact changed: ' + name)
    # Pins are reviewed together with code and Git; not a user authentication claim.
    require(sha((HERE / 'preserved-files.json').read_bytes()) == PRESERVATION_SHA,
            'preservation baseline changed')
    for name, digest in load(HERE / 'preserved-files.json').items():
        require(sha((ROOT / name).read_bytes()) == digest, 'existing file changed: ' + name)
    require(sha((HERE / 'approval-declaration.json').read_bytes()) == DECLARATION_SHA,
            'user declaration or scope changed')
    declaration = load(HERE / 'approval-declaration.json')
    require(declaration['case_ids'] == IDS and declaration['basis_commit'] == BASIS,
            'declaration coverage/basis')
    # Validate unchanged final submission provenance and every upstream reference.
    final_summary = final.validate()
    finals = load(ROOT / FINAL_PATH)['events']
    require(final_summary['recorded'] == 17 and final_summary['approve_for_development_gold'] is None,
            'historical final approval state changed')
    schema = load(HERE / 'record.schema.json')
    Draft202012Validator.check_schema(schema)
    record = load(HERE / 'events.json')
    errors = list(Draft202012Validator(schema).iter_errors(record))
    require(not errors, 'approval record schema invalid: ' + '; '.join(e.message for e in errors))
    require(record['schema_version'] == 'gold-inclusion-intent-history-v1' and record['basis_commit'] == BASIS,
            'record schema/basis')
    require([e['case_id'] for e in record['events']] == IDS, 'event coverage/order')
    previous = None
    for i, (event, old_final) in enumerate(zip(record['events'], finals)):
        cid = IDS[i]
        require(event['event_id'] == 'gold-inclusion-intent-' + cid, 'event ID')
        require(event['kind'] == 'user_development_gold_inclusion_approval_recorded', 'event kind')
        require(event['actor_type'] == 'human' and event['recorder_type'] == 'ai', 'source attribution')
        require(all(event[k] is None for k in ('user_approved_at', 'signature', 'authentication')),
                'invented user metadata')
        require(event['approve_for_development_gold'] is True and event['activate_development_gold'] is False,
                'inclusion/activation boundary')
        require(event['case_id'] == old_final['case_id'] and event['input_sha256'] == old_final['input_sha256'],
                'case/input binding')
        require(event['final_reference'] == reference(FINAL_PATH, f'/events/{i}')
                and event['final_event_sha256'] == final.event_digest(old_final), 'final history binding')
        # HERE may be an isolated test copy; use its source bytes, with the fixed repository path.
        expected_source = {'path': PACKAGE + 'approval-declaration.json',
                           'sha256': sha((HERE / 'approval-declaration.json').read_bytes()), 'pointer': '/statement'}
        require(event['declaration_reference'] == expected_source, 'declaration binding')
        require(event['previous_event_sha256'] == previous, 'event chain')
        previous = final.event_digest(event)
    require(record['terminal_event_sha256'] == previous, 'terminal event seal')
    active = load(ROOT / ACTIVE_PATH)
    require(active['active_case_ids'] == [f'SP-{i:03}' for i in range(1, 13)], 'active gold scope changed')
    require(not set(IDS).intersection(active['active_case_ids']), 'new cases unexpectedly active')
    return {'approved_count': 17, 'duplicates': 0, 'missing': 0, 'final_judgment_changes': 0,
            'final_distribution': dict(Counter(e['payload']['judgment'] for e in finals)),
            'original_files_unchanged': True, 'active_gold_count': len(active['active_case_ids']),
            'activation_performed': False, 'method': 'single_user_with_ai_counterreview',
            'externally_authenticated': False}


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False))

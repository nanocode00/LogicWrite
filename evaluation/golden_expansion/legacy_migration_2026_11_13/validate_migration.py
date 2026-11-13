"""Read-only legacy-evidence migration and staged v3 validation.

No formal human events are synthesized. Pending policy never confers eligibility.
"""
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGE = 'evaluation/golden_expansion/legacy_migration_2026_11_13'
V3_PACKAGE = 'evaluation/g3_g4/development_gold_v3_2026-11-13'
V3 = ROOT / V3_PACKAGE
BASE = '606f7b428b4cf9ea32a7ddcf50c3e3745a67a78a'
EXPANSION = 'evaluation/golden_expansion'
COUNTER = EXPANSION + '/codex_counterreview_2026_11_11'
FINAL = EXPANSION + '/user_final_2026_11_11'
APPROVAL = EXPANSION + '/gold_inclusion_approval_2026_11_13'
V2_PATH = 'evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
CONSUMERS = ['evaluation/core_pipeline_2026_11_11/evaluate.py', 'evaluation/source_candidate_semantics/run.py']
IDS = [f'GC-{i:03}' for i in range(1, 13)] + [f'SP-{i:03}' for i in range(13, 18)]
PINS = {'preserved-files.json': 'c7cf41077053319a1e2b48c9de74bc7222e3b59c7c3738d7265f24676729b426',
        'policy.json': 'b51460e14de51e66867fc3ac9c619bf02990847776edce1404b5795f1652fc1f',
        'continuation-request.json': 'd6ff6f6e365355d478c6ebae1b49d504da9a2a1486e072a32f8c27d7aac75a32'}
ARTIFACTS = {'migration/' + name for name in (
    'README.md', 'PLAN.md', 'policy.json', 'continuation-request.json', 'preserved-files.json',
    'legacy-records.json', 'validate_migration.py', 'test_migration.py')}
ARTIFACTS |= {'v3/' + name for name in ('README.md', 'development-gold.json', 'activation-proposal.json', 'validate.py')}
STAGES = [
    ('initial', '93d5252f9348004f9ce38b886b73e458eff3c3c1',
     EXPANSION + '/counterreview_2026_11_11/initial-judgments.json'),
    ('ai_counterreview', '8ace3d46a7aad4f58bafc30e45c70d0cce673742', COUNTER + '/gc01_06.raw.json'),
    ('user_final', '1ec8031608c20731895dc1a96524b30949bb0ed4', FINAL + '/events.json'),
    ('inclusion', 'dc8083d04d40dcd06face398336f0b8f923f1eb2', APPROVAL + '/events.json'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location('migration_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def artifact_path(name, here=HERE, v3=V3):
    prefix, relative = name.split('/', 1)
    need(prefix in {'migration', 'v3'}, 'unknown artifact prefix')
    boundary = here if prefix == 'migration' else v3
    path = (boundary / relative).resolve()
    need(path.is_relative_to(boundary.resolve()), 'unsafe artifact path')
    return path


def ref(root, path, pointer='', here=HERE, v3=V3):
    if path.startswith(PACKAGE + '/'):
        target = here / path[len(PACKAGE) + 1:]
    elif path.startswith(V3_PACKAGE + '/'):
        target = v3 / path[len(V3_PACKAGE) + 1:]
    else:
        target = root / path
    return {'path': path, 'sha256': sha(target.read_bytes()), 'pointer': pointer}


def verify_order(root=ROOT, stages=STAGES):
    """Git causal ancestry and immutable source blobs; no claim of human clock time."""
    result = []
    previous = None
    for stage, commit, path in stages:
        process = subprocess.run(['git', '-C', str(root), 'show', commit + ':' + path],
                                 capture_output=True)
        need(process.returncode == 0, 'historical Git source unavailable: ' + stage)
        need(process.stdout == (root / path).read_bytes(), 'historical source changed: ' + path)
        if previous:
            check = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', previous, commit],
                                   capture_output=True)
            need(check.returncode == 0 and previous != commit, 'historical stage order invalid')
        result.append({'stage': stage, 'source_commit': commit, 'source': ref(root, path),
                       'order_basis': 'git_ancestry_and_source_reference_links'})
        previous = commit
    # All three AI batches must belong to the same independently recorded review stage.
    for batch in ('gc01_06', 'gc07_12', 'sp13_17'):
        path = COUNTER + '/' + batch + '.raw.json'
        raw = subprocess.run(['git', '-C', str(root), 'show', STAGES[1][1] + ':' + path], capture_output=True)
        need(raw.returncode == 0 and raw.stdout == (root / path).read_bytes(), 'AI batch stage mismatch')
    return result


def build_records(root=ROOT, here=HERE, v3=V3):
    for name, digest in PINS.items():
        need(sha((here / name).read_bytes()) == digest, 'pinned policy/request/baseline changed: ' + name)
    policy = load(here / 'policy.json')
    need(policy['user_policy_approval'] is None, 'unreviewed policy authorization')
    counter = module('counter', root / COUNTER / 'validate.py')
    summary, initials, collected, failures = counter.verify()
    need(summary['completed'] == 17 and not failures, 'insufficient counterreview execution evidence')
    final = module('final', root / FINAL / 'validate_submission.py')
    final.validate()
    inclusion = module('inclusion', root / APPROVAL / 'validate_approval.py')
    inclusion.validate()
    old = module('v2', (root / V2_PATH).parent / 'validate.py')
    need(old.validate((root / V2_PATH).parent, root)['workflow_eligible'] == 12, 'v2 eligibility invalid')
    order = verify_order(root)
    finals = load(root / FINAL / 'events.json')['events']
    approvals = load(root / APPROVAL / 'events.json')['events']
    registry = load(root / EXPANSION / 'registry.json')['cases']
    registered = {r['case_id']: r for r in registry}
    request = load(here / 'continuation-request.json')
    need([r['case_id'] for r in initials] == IDS == [r['case_id'] for r in finals]
         == [r['case_id'] for r in approvals], 'legacy scope/order mismatch')
    rows = []
    for i, (initial, human, approved) in enumerate(zip(initials, finals, approvals)):
        cid = IDS[i]
        need(initial['input_sha256'] == human['input_sha256'] == approved['input_sha256'], 'input identity')
        need(initial['initial_judgment'] == human['payload']['judgment'], 'initial/final discrepancy')
        need(approved['final_event_sha256'] == final.event_digest(human)
             and approved['approve_for_development_gold'] is True, 'approval/final binding')
        need(approved['final_reference'] == ref(root, FINAL + '/events.json', f'/events/{i}'), 'approval pointer')
        inp = load(root / initial['input_path'])
        registry_index = next(n for n, r in enumerate(registry) if r['case_id'] == cid)
        for parent in registered[cid].get('parent_inputs', []):
            need(sha((root / parent['path']).read_bytes()) == parent['sha256'], 'parent input SHA')
        raw = collected[cid]['result']
        need(raw['evidence'] and raw['review_status'] == 'complete', 'insufficient AI supporting evidence')
        label = human['payload']['judgment']
        retention = None
        if label == 'UNRESOLVED':
            need(cid in request['unresolved_case_ids'] and bool(initial['initial_reason']), 'missing retained reason')
            retention = {'reason': initial['initial_reason'], 'attribution': 'user_reason_retained_by_current_request',
                         'original_reason': ref(root, COUNTER + '/initial-judgments.json', f'/cases/{i}/initial_reason'),
                         'reaffirmation': ref(root, PACKAGE + '/continuation-request.json', '/unresolved_statement', here, v3)}
        rows.append({
            'case_id': cid, 'input': ref(root, initial['input_path']),
            'initial_human': {'source': ref(root, COUNTER + '/initial-judgments.json', f'/cases/{i}'),
                              'judgment': initial['initial_judgment'], 'reason': initial['initial_reason']},
            'ai_review': {'source': human['counterreview_reference'], 'execution': human['execution_reference'],
                          'supporting_evidence': raw['evidence'], 'attributed_to': 'independent_Codex_review',
                          'evidence_attributed_to_human': False, 'execution_completed': True},
            'final_human': {'source': ref(root, FINAL + '/events.json', f'/events/{i}'),
                            'event_sha256': final.event_digest(human), 'judgment': label,
                            'response': human['payload']['counterargument_response'],
                            'response_target': 'AI counterargument validity assessment',
                            'additional_reason': human['payload']['rationale']},
            'inclusion': {'source': ref(root, APPROVAL + '/events.json', f'/events/{i}'),
                          'event_sha256': final.event_digest(approved), 'declaration': approved['declaration_reference'],
                          'approved': True},
            'reason_retention': retention,
            'unrecorded_formal_fields': {'challenge_id': None, 'challenge_decision': None,
                                         'user_final_evidence': None, 'user_reviewed_at': None,
                                         'authenticated_identity': None, 'signature': None,
                                         'confidence_limitations_user_confirmed': None,
                                         'blinded_to_prior_judgments': None},
            'lineage': {'registry': ref(root, EXPANSION + '/registry.json', f'/cases/{registry_index}'),
                        'parent_inputs': registered[cid].get('parent_inputs', []),
                        'source_provenance': [d['provenance'] for d in inp['source_documents']],
                        'source_families': sorted({d['provenance']['repository'] for d in inp['source_documents']
                                                   if d['provenance']['repository']}),
                        'construction': inp['construction']},
            'legacy_evidence_validated': True, 'qualifies_under_proposed_policy': True,
            'activation_eligible': False, 'blockers': ['MIGRATION_POLICY_APPROVAL_REQUIRED'],
            'development_only': True, 'independent_multi_human_complete': False,
        })
    return {'schema_version': 'legacy-review-evidence-bundle-v1', 'basis_commit': BASE,
            'status': 'evidence_validated_policy_pending', 'record_type': 'migration_bundle_not_formal_user_events',
            'policy': ref(root, PACKAGE + '/policy.json', '', here, v3),
            'continuation_request': ref(root, PACKAGE + '/continuation-request.json', '', here, v3),
            'ordered_source_stages': order, 'case_count': 17, 'cases': rows}


def build_candidate(root=ROOT, here=HERE, v3=V3):
    records = load(here / 'legacy-records.json')
    need(records == build_records(root, here, v3), 'legacy bundle differs from original sources')
    prior = load(root / V2_PATH)
    rows = prior['cases'].copy()
    for i, item in enumerate(records['cases']):
        rows.append({'case_id': item['case_id'], 'user_final_judgment': item['final_human']['judgment'],
                     'input_sha256': item['input']['sha256'], 'input_reference': item['input'],
                     'review_method': 'legacy_single_user_ai_counterreview',
                     'migration_reference': ref(root, PACKAGE + '/legacy-records.json', f'/cases/{i}', here, v3),
                     'final_reference': item['final_human']['source'],
                     'inclusion_reference': item['inclusion']['source'],
                     'inclusion_event_sha256': item['inclusion']['event_sha256'],
                     'development_gold_inclusion_approved': True, 'legacy_evidence_validated': True,
                     'development_gold_eligible': False, 'independent_multi_human_complete': False,
                     'lineage': item['lineage'], 'blockers': ['MIGRATION_POLICY_APPROVAL_REQUIRED']})
    case_ids = [r['case_id'] for r in rows]
    need(case_ids == [f'SP-{i:03}' for i in range(1, 13)] + IDS and len(set(case_ids)) == 29, 'v3 inventory')
    distribution = dict(Counter(r['user_final_judgment'] for r in rows))
    need(distribution == {'PRESERVED': 12, 'VIOLATION': 9, 'UNRESOLVED': 8}, 'v3 answer distribution')
    return {'schema_version': '3.0.0', 'dataset_id': 'single-user-development-gold-v3-20261113',
            'dataset_role': 'development_only', 'status': 'candidate_pending_migration_policy_approval',
            'active': False, 'active_case_ids': [], 'case_count': 29, 'case_ids': case_ids,
            'distribution': distribution, 'previous_dataset': ref(root, V2_PATH),
            'migration_policy': ref(root, PACKAGE + '/policy.json', '', here, v3),
            'independent_holdout': False, 'independent_multi_human_complete': False,
            'source_family_independence_claimed': False, 'cases': rows}


def build_activation_proposal(root=ROOT, here=HERE, v3=V3):
    return {'status': 'proposed_not_active', 'policy_approval': None,
            'current_active_dataset': ref(root, V2_PATH),
            'candidate_dataset': ref(root, V3_PACKAGE + '/development-gold.json', '', here, v3),
            'consumers_unchanged': [ref(root, p) for p in CONSUMERS],
            'activation_performed': False, 'blockers': ['MIGRATION_POLICY_APPROVAL_REQUIRED']}


def validate(root=ROOT, here=HERE, v3=V3):
    manifest = load(here / 'artifact-manifest.json')
    need(set(manifest) == ARTIFACTS, 'artifact inventory changed')
    for name, digest in manifest.items():
        need(sha(artifact_path(name, here, v3).read_bytes()) == digest, 'artifact changed: ' + name)
    need(sha((here / 'preserved-files.json').read_bytes()) == PINS['preserved-files.json'], 'preservation baseline changed')
    for name, digest in load(here / 'preserved-files.json').items():
        need(sha((root / name).read_bytes()) == digest, 'existing file changed: ' + name)
    records = load(here / 'legacy-records.json')
    need(records == build_records(root, here, v3), 'legacy bundle differs from original sources')
    candidate = load(v3 / 'development-gold.json')
    need(candidate == build_candidate(root, here, v3), 'v3 candidate differs from source judgments or policy')
    need(load(v3 / 'activation-proposal.json') == build_activation_proposal(root, here, v3), 'activation proposal changed')
    for path in CONSUMERS:
        need(V2_PATH in (root / path).read_text(), 'active reference no longer v2')
    return {'legacy_evidence_validated': 17, 'new_activation_eligible': 0, 'existing_eligible': 12,
            'candidate_count': 29, 'candidate_distribution': candidate['distribution'],
            'current_active_count': 12, 'newly_activated': 0, 'policy_status': 'approval_required',
            'existing_files_unchanged': True}


def require_activation_ready(root=ROOT, here=HERE, v3=V3):
    validate(root, here, v3)
    raise ValueError('migration policy approval required; current active dataset remains v2')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-activation-ready', action='store_true')
    args = parser.parse_args()
    print(json.dumps(validate(), ensure_ascii=False))
    if args.require_activation_ready:
        try:
            require_activation_ready()
        except ValueError as error:
            parser.exit(2, str(error) + '\n')

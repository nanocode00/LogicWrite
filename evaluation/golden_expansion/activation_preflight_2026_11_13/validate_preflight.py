"""Snapshot-specific, read-only preflight. This is not an alternate eligibility policy."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGE = 'evaluation/golden_expansion/activation_preflight_2026_11_13'
BASE = 'dc15379e63394a04f513721cfbea4fa590802bc0'
BASELINE_SHA = '32cb33e67cceb1eb4cc3aa7a244e056f3c91298261f1e4822d941cbe81d13b4a'
EXPANSION = 'evaluation/golden_expansion'
COUNTER = EXPANSION + '/codex_counterreview_2026_11_11'
FINAL = EXPANSION + '/user_final_2026_11_11'
APPROVAL = EXPANSION + '/gold_inclusion_approval_2026_11_13'
ACTIVE = 'evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
CONSUMERS = ['evaluation/core_pipeline_2026_11_11/evaluate.py', 'evaluation/source_candidate_semantics/run.py']
IDS = [f'GC-{i:03}' for i in range(1, 13)] + [f'SP-{i:03}' for i in range(13, 18)]
ARTIFACTS = {'PLAN.md', 'README.md', 'validate_preflight.py', 'test_preflight.py', 'preserved-files.json', 'report.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location('preflight_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def reference(root, path, pointer=''):
    return {'path': path, 'sha256': sha((root / path).read_bytes()), 'pointer': pointer}


def build_report(root=ROOT):
    """Evaluate only this pinned snapshot; no inferred events or evidence conversion."""
    counter = module('counter', root / COUNTER / 'validate.py')
    counter_summary, initials, _, failures = counter.verify()
    need(counter_summary['completed'] == 17 and not failures, 'incomplete AI review')
    final = module('final', root / FINAL / 'validate_submission.py')
    final.validate()
    approval = module('approval', root / APPROVAL / 'validate_approval.py')
    approval.validate()
    v2 = module('v2', (root / ACTIVE).parent / 'validate.py')
    need(v2.validate((root / ACTIVE).parent, root)['workflow_eligible'] == 12, 'v2 no longer eligible')
    workflow = module('workflow', root / EXPANSION / 'review.py')
    registry = load(root / EXPANSION / 'registry.json')['cases']
    registered = {row['case_id']: row for row in registry}
    finals = load(root / FINAL / 'events.json')['events']
    approvals = load(root / APPROVAL / 'events.json')['events']
    active = load(root / ACTIVE)
    need([row['case_id'] for row in finals] == IDS == [row['case_id'] for row in approvals], 'scope/order')
    rows = []
    for i, (initial, final_event, inclusion) in enumerate(zip(initials, finals, approvals)):
        cid = IDS[i]
        need(initial['case_id'] == cid, 'initial order')
        prepared_path = EXPANSION + f'/prepared/{cid}.workflow.json'
        formal_record = load(root / prepared_path)
        assessment = workflow.assess(formal_record)
        # This report deliberately has no path that turns transcription into human events.
        need(formal_record['events'] == [] and not assessment['development_gold_eligible'],
             'formal review state changed; new preflight design required')
        inp = load(root / initial['input_path'])
        final_label = final_event['payload']['judgment']
        blockers = ['FORMAL_REVIEW_CHAIN_NOT_RECORDED', 'USER_INITIAL_FORM_INCOMPLETE',
                    'USER_FINAL_EVIDENCE_NOT_SUBMITTED', 'CHALLENGE_RESPONSES_NOT_BOUND',
                    'FINAL_CONFIDENCE_LIMITATIONS_NOT_CONFIRMED']
        if final_label == 'UNRESOLVED':
            blockers.append('FINAL_UNRESOLVED_ISSUES_NOT_SUBMITTED')
        registry_index = next(n for n, row in enumerate(registry) if row['case_id'] == cid)
        rows.append({
            'case_id': cid, 'input': reference(root, initial['input_path']),
            'initial': reference(root, COUNTER + '/initial-judgments.json', f'/cases/{i}'),
            'initial_reason': initial['initial_reason'],
            'counterreview': final_event['counterreview_reference'],
            'counterreview_execution': final_event['execution_reference'],
            'final': reference(root, FINAL + '/events.json', f'/events/{i}'),
            'final_event_sha256': final.event_digest(final_event),
            'user_final_judgment': final_label,
            'user_counterargument_response': final_event['payload']['counterargument_response'],
            'user_additional_reason': final_event['payload']['rationale'],
            'inclusion': reference(root, APPROVAL + '/events.json', f'/events/{i}'),
            'inclusion_event_sha256': final.event_digest(inclusion),
            'inclusion_declaration': inclusion['declaration_reference'],
            'inclusion_approved': inclusion['approve_for_development_gold'],
            'formal_workflow': reference(root, prepared_path), 'formal_assessment': assessment,
            'user_reviewed_at': final_event['user_reviewed_at'],
            'formal_final_unresolved_issues': None,
            'eligible_for_activation': False, 'blockers': blockers,
            'registry': reference(root, EXPANSION + '/registry.json', f'/cases/{registry_index}'),
            'parent_inputs': registered[cid].get('parent_inputs', []),
            'source_provenance': [doc['provenance'] for doc in inp['source_documents']],
            'source_families': sorted({doc['provenance']['repository'] for doc in inp['source_documents']
                                       if doc['provenance']['repository']}),
            'construction': inp['construction'],
        })
    need(all(r['inclusion_approved'] is True for r in rows), 'inclusion missing')
    for consumer in CONSUMERS:
        need(ACTIVE in (root / consumer).read_text(), 'active consumer changed')
    target = Counter(active['active_distribution'])
    target.update(row['user_final_judgment'] for row in rows)
    need(dict(target) == {'PRESERVED': 12, 'VIOLATION': 9, 'UNRESOLVED': 8}, 'target arithmetic')
    return {'schema_version': 'development-gold-activation-preflight-v1', 'basis_commit': BASE,
            'status': 'blocked', 'dataset_role': 'development_only',
            'independent_holdout': False, 'independent_multi_human_complete': False,
            'active_dataset': reference(root, ACTIVE), 'active_count': 12,
            'active_case_ids': active['active_case_ids'], 'active_cases': active['cases'],
            'active_distribution': active['active_distribution'],
            'unchanged_consumers': [reference(root, p) for p in CONSUMERS],
            'new_inclusion_approved': 17, 'new_eligible': 0, 'new_activated': 0,
            'eligible_case_ids': [], 'blocked_case_ids': IDS,
            'v3_dataset_path': None, 'v3_active_index_path': None,
            'target_only': {'not_active': True, 'count': 29, 'distribution': dict(target)},
            'policy': [reference(root, EXPANSION + '/review.py'),
                       reference(root, EXPANSION + '/record.schema.json')],
            'cases': rows}


def validate(here=HERE, root=ROOT):
    manifest = load(here / 'artifact-manifest.json')
    need(set(manifest) == ARTIFACTS, 'manifest scope changed')
    for name, digest in manifest.items():
        need(sha((here / name).read_bytes()) == digest, 'preflight artifact changed: ' + name)
    need(sha((here / 'preserved-files.json').read_bytes()) == BASELINE_SHA, 'baseline changed')
    for name, digest in load(here / 'preserved-files.json').items():
        need(sha((root / name).read_bytes()) == digest, 'existing file changed: ' + name)
    report = build_report(root)
    need(load(here / 'report.json') == report, 'stored preflight report mismatch')
    return report


def require_activation_ready(report):
    need(report['status'] == 'ready' and report['new_eligible'] == 17
         and not report['blocked_case_ids'], 'activation blocked: 17 cases lack complete formal review evidence')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-activation-ready', action='store_true')
    args = parser.parse_args()
    report = validate()
    print(json.dumps({key: report[key] for key in ('status', 'new_inclusion_approved', 'new_eligible',
                                                   'new_activated', 'active_count', 'active_distribution')}))
    if args.require_activation_ready:
        try:
            require_activation_ready(report)
        except ValueError as error:
            parser.exit(2, str(error) + '\n')

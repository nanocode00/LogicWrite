#!/usr/bin/env python3
"""Read-only criteria lineage checks, never a semantic verdict or human approval."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('integrated_base_validation', ROOT / 'validate.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

REQUESTS = {'IR-001': {f'CR-001-0{i}' for i in range(1, 6)}, 'IR-002': {'CR-002-01'}}
ALLOWED = {
    'IR-001': {'evidence', 'D.inferred_requirements', 'D.decision_criteria', 'D.confirmation',
               'Q.invariants', 'Q.forbidden_outcomes', 'Q.acceptable_bundles', 'Q.reader_tasks'},
    'IR-002': {'Q.invariants', 'Q.reader_tasks', 'Q.acceptable_bundles'},
}


def verify_hash(root, path, expected):
    v.require(v.digest(v.local(root, path).read_bytes()) == expected, 'stale hash: ' + path)


def flatten(record, prefix=''):
    result = {}
    for key, value in record.items():
        path = prefix + key
        if isinstance(value, dict):
            result.update(flatten(value, path + '.'))
        else:
            result[path] = value
    return result


def preserved_items(parent, child, group, exempt):
    old = parent
    new = child
    for key in group.split('.'):
        old, new = old[key], new[key]
    v.require([x['id'] for x in old] == [x['id'] for x in new], 'criterion IDs changed')
    for a, b in zip(old, new):
        if a['id'] not in exempt:
            v.require(a == b, 'unauthorized criterion: ' + group + '.' + a['id'])


def request_location(record, location):
    value = record
    for part in location.split('.'):
        if isinstance(value, list):
            matches = [x for x in value if isinstance(x, dict) and x.get('id') == part]
            v.require(len(matches) == 1, 'invalid request location: ' + location)
            value = matches[0]
        else:
            v.require(isinstance(value, dict) and part in value, 'invalid request location: ' + location)
            value = value[part]
    return value


def verify_correction(root, manifest):
    correction = manifest['correction']
    for prefix in ('parent_manifest', 'parent_criteria', 'prior_review', 'prior_change_requests'):
        verify_hash(root, correction[prefix + '_path'], correction[prefix + '_sha256'])
    prior_manifest = v.read(root, correction['parent_manifest_path'])
    v.require(prior_manifest['cases'][0]['criteria_sha256'] == correction['parent_criteria_sha256'], 'correction parent criteria binding')
    v.require(prior_manifest['reviews'][2]['sha256'] == correction['prior_review_sha256'], 'correction prior review binding')
    expected_manifest = copy.deepcopy(prior_manifest)
    expected_manifest['correction'] = correction
    expected_manifest['cases'][0]['criteria_sha256'] = manifest['cases'][0]['criteria_sha256']
    expected_manifest['reviews'][2]['snapshot_path'] = manifest['reviews'][2]['snapshot_path']
    expected_manifest['reviews'][2]['sha256'] = manifest['reviews'][2]['sha256']
    v.require(expected_manifest == manifest, 'unauthorized correction manifest change')
    old = v.read(root, correction['parent_criteria_path'])
    current = v.read(root, 'criteria/v2/IR-001.json')
    expected = copy.deepcopy(old)
    expected['Q']['invariants'][2]['criterion'] = current['Q']['invariants'][2]['criterion']
    expected['Q']['reader_tasks'][2] = current['Q']['reader_tasks'][2]
    v.require(expected == current, 'unauthorized correction criterion change')
    prior_review = v.read(root, correction['prior_review_path'])
    current_review = v.read(root, 'reviews/IR-003.json')
    expected_review = copy.deepcopy(prior_review)
    for key in ('initial_judgment', 'answer_exposure', 'counterreview', 'adjudication'):
        expected_review[key] = current_review[key]
    v.require(expected_review == current_review, 'unauthorized correction review change')
    v.require(current_review['initial_judgment'] == '당장 추가하거나 뺄 내용이 보이지 않으며, 수정 권한과 회의 대상을 확인하면 될 것으로 보인다.', 'initial human judgment provenance')
    v.schema_check(root, 'review', prior_review)


def validate(root=ROOT):
    root = Path(root).resolve()
    # This validates all three unchanged v1 inputs/answers/references and live reviews.
    v.validate_package(root)
    m = v.read(root, 'criteria/v2/manifest.json')
    v.schema_check(root, 'criteria-lineage', m)
    v.require(v.unique(m['cases'], 'case_id') == set(REQUESTS), 'criteria revision case set')
    count = 0
    for e in m['cases']:
        cid = e['case_id']
        for prefix, expected_path in [('criteria', f'criteria/v2/{cid}.json'),
                                      ('parent', f'answers/{cid}.json'),
                                      ('input', f'inputs/{cid}.json'),
                                      ('reference_output', f'reference_outputs/{cid}.json')]:
            v.require(e[prefix + '_path'] == expected_path, 'unexpected lineage path')
            verify_hash(root, expected_path, e[prefix + '_sha256'])
        v.require(v.unique(e['change_requests'], 'id') == REQUESTS[cid], 'change request coverage')
        count += len(e['change_requests'])
        parent = v.read(root, e['parent_path'])
        child = v.read(root, e['criteria_path'])
        inp = v.read(root, e['input_path'])
        v.schema_check(root, 'answer', child)
        for request in e['change_requests']:
            for location in request['locations']:
                request_location(child, location)
        v.require(child['case_id'] == cid and child['input_sha256'] == e['input_sha256'], 'criteria input binding')
        old, new = flatten(parent), flatten(child)
        v.require(old.keys() == new.keys(), 'criteria structure changed')
        for key in old:
            v.require(old[key] == new[key] or key in ALLOWED[cid], 'unauthorized criterion: ' + key)
        docs = {d['document_id']: d for d in inp['documents']}
        refs = v.check_evidence(child['evidence'], docs)
        for items in [child['D']['inferred_requirements'], child['D']['decision_criteria'],
                      child['Q']['invariants'], child['Q']['forbidden_outcomes']]:
            v.unique(items, 'id')
            for item in items:
                v.require(set(item['evidence_refs']) <= refs, 'unknown evidence ref')
        if cid == 'IR-001':
            preserved_items(parent, child, 'D.decision_criteria', {'D1', 'D2', 'D3', 'D4'})
            preserved_items(parent, child, 'Q.invariants', {'Q1', 'Q3', 'Q4'})
            preserved_items(parent, child, 'Q.forbidden_outcomes', {'F1'})
            v.require(child['evidence'][:len(parent['evidence'])] == parent['evidence'], 'old evidence changed')
            v.require(bool(child['D']['confirmation']), 'missing HITL boundary')
            # No input modification: an epistemic policy conflict can require HITL
            # even when all documents are supplied (availability.gaps is empty).
        else:
            preserved_items(parent, child, 'Q.invariants', {'Q1'})
        v.require(child['Q']['reader_tasks'] == [x['criterion'] for x in child['Q']['invariants']], 'reader task drift')
        required = v.unique(child['Q']['invariants'], 'id')
        v.require(v.unique(child['Q']['acceptable_bundles'], 'id') == {'A', 'B'}, 'alternatives changed')
        for bundle in child['Q']['acceptable_bundles']:
            v.require(set(bundle['must_satisfy']) == required, 'alternative skips invariant')
        v.require(child['Q']['reference_output_path'] == e['reference_output_path'], 'historical reference drift')
    verify_correction(root, m)
    v.require(v.unique(m['reviews'], 'case_id') == {'IR-001', 'IR-002', 'IR-003'}, 'review set')
    for e in m['reviews']:
        cid = e['case_id']
        v.require(e['current_path'] == f'reviews/{cid}.json', 'current review path')
        snapshot = 'clarification-01' if cid == 'IR-003' else 'recorded-2026-11-16'
        v.require(e['snapshot_path'] == f'reviews/history/{snapshot}/{cid}.json', 'snapshot review path')
        v.require(e['prior_path'] == f'reviews/history/before-criteria-v2/{cid}.json', 'prior review path')
        v.require(e['prior_revision'] == '6d6f32140b951cac025701ef42995ddba43565e0', 'prior revision drift')
        for key in ('current_path', 'snapshot_path'):
            verify_hash(root, e[key], e['sha256'])
        verify_hash(root, e['prior_path'], e['prior_sha256'])
        for key in ('current_path', 'snapshot_path', 'prior_path'):
            review = v.read(root, e[key])
            v.schema_check(root, 'review', review)
            v.require(review['case_id'] == cid, 'review case binding')
            verify_hash(root, f'inputs/{cid}.json', review['input_sha256'])
            v.require(review['gold_inclusion_approval'] is None, 'gold approval outside scope')
    return dict(criteria_version=m['version'], revised_cases=2, change_requests_implemented=count,
                historical_reference_outputs='preserved_not_revalidated_for_v2',
                post_revision_human_review='pending', gold_eligible=False,
                semantic_quality='not_measured')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), ensure_ascii=False, indent=2))

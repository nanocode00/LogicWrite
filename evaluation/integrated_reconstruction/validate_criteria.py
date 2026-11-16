#!/usr/bin/env python3
"""Read-only criteria lineage checks, never a semantic verdict or human approval."""
import argparse
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
    v.require(v.unique(m['reviews'], 'case_id') == {'IR-001', 'IR-002', 'IR-003'}, 'review set')
    for e in m['reviews']:
        cid = e['case_id']
        v.require(e['current_path'] == f'reviews/{cid}.json', 'current review path')
        v.require(e['snapshot_path'] == f'reviews/history/recorded-2026-11-16/{cid}.json', 'snapshot review path')
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

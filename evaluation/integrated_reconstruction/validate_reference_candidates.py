#!/usr/bin/env python3
"""Read-only v2 reference candidate integrity; no semantic approval or publishing."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('candidate_criteria_validation', ROOT / 'validate_criteria.py')
criteria = importlib.util.module_from_spec(spec)
spec.loader.exec_module(criteria)
v = criteria.v


def validate(root=ROOT):
    root = Path(root).resolve()
    criteria.validate(root)
    m = v.read(root, 'reference_outputs/v2_candidates/manifest.json')
    v.schema_check(root, 'candidate-lineage', m)
    criteria.verify_hash(root, m['criteria_manifest_path'], m['criteria_manifest_sha256'])
    criteria.verify_hash(root, m['review_path'], m['review_sha256'])
    v.require(v.unique(m['cases'], 'case_id') == {'IR-001', 'IR-002'}, 'candidate case set')
    document_count = 0
    for e in m['cases']:
        cid = e['case_id']
        expected_paths = {'input': f'inputs/{cid}.json', 'criteria': f'criteria/v2/{cid}.json',
                          'reference': f'reference_outputs/v2_candidates/{cid}.json',
                          'parent_reference': f'reference_outputs/{cid}.json'}
        for key, path in expected_paths.items():
            v.require(e[key + '_path'] == path, 'unexpected candidate lineage path')
            criteria.verify_hash(root, path, e[key + '_sha256'])
        inp = v.read(root, e['input_path'])
        answer = v.read(root, e['criteria_path'])
        ref = v.read(root, e['reference_path'])
        v.schema_check(root, 'reference', ref)
        v.require(ref['case_id'] == cid and ref['input_sha256'] == e['input_sha256'], 'candidate input binding')
        source = {d['document_id']: d for d in inp['documents']}
        writable = {id for id, doc in source.items() if doc['access'] in ('edit', 'format_only')}
        v.require(v.unique(ref['documents'], 'document_id') == writable, 'incomplete or unauthorized document set')
        returned = {d['document_id']: d for d in ref['documents']}
        for id, doc in returned.items():
            v.require(v.digest(doc['content'].encode()) == doc['sha256'], 'candidate document hash')
            if source[id]['access'] == 'format_only':
                v.require(doc['content'].split() == source[id]['content'].split(), 'format-only content changed')
        document_count += len(returned)
        v.check_links(ref['documents'], source)
        v.require(ref['bundle'] in {b['id'] for b in answer['Q']['acceptable_bundles']}, 'unknown candidate alternative')
        evidence = v.check_evidence(answer['evidence'], source)
        v.require(set(e['review_evidence_refs']) <= evidence, 'unknown candidate review evidence')
        reviewed = {x['id'] for group in [answer['D']['decision_criteria'], answer['Q']['invariants'],
                                         answer['Q']['forbidden_outcomes']] for x in group}
        v.require(set(e['reviewed_criteria']) == reviewed, 'missing criteria review coverage')
        # Fixture-specific preservation choices, not a general semantic evaluator.
        for passage in e['frozen_passages']:
            id, quote = passage['document_id'], passage['source_quote']
            v.require(id in returned and quote in source[id]['content'], 'unknown source frozen passage')
            v.require(quote in returned[id]['content'], 'candidate frozen passage changed')
        if cid == 'IR-001':
            v.require(ref['unresolved_questions'] and ref['deferred_scope'], 'missing candidate HITL context')
            v.require(len(e['frozen_passages']) == 2, 'missing candidate preservation choices')
        else:
            v.require(not e['frozen_passages'], 'unexpected frozen passage rule')
    return dict(candidate_cases=2, whole_documents=document_count,
                structural_integrity='PASS', semantic_approval='not_granted',
                review_type='ai_counterexample_analysis_not_human_review',
                post_revision_human_review=None, gold_inclusion_approval=None,
                gold_eligible=False, model_performance='not_measured', executed_by_system=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), ensure_ascii=False, indent=2))

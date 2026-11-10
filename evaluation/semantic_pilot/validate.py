#!/usr/bin/env python3
"""Validate data structure, bindings and review records; never judge semantics."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, name):
    require(isinstance(name, str) and not Path(name).is_absolute(), 'relative path required')
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), 'path escapes dataset')
    require(path.is_file(), f'missing file: {name}')
    return path


def read_json(root, name):
    return json.loads(local_path(root, name).read_text(encoding='utf-8'))


def check_evidence(evidence, inp):
    for item in evidence:
        docs = {d['document_id']: d for d in inp[item['side'] + '_documents']}
        require(item['document_id'] in docs, 'unknown evidence document')
        text = docs[item['document_id']]['content']
        require(text is not None, 'evidence in unavailable document')
        start, end = item['start'], item['end']
        require(0 <= start < end <= len(text), 'evidence offsets out of bounds')
        require(text[start:end] == item['quote'], 'evidence quote differs from span')


def validate_pair(inp, answer, root=ROOT):
    for name, record in [('input', inp), ('answer', answer)]:
        schema = read_json(root, name + '.schema.json')
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda e: str(e.path))
        require(not errors, f'{name} schema: ' + '; '.join(e.message for e in errors))
    require(inp['case_id'] == answer['case_id'], 'case ID mismatch')
    path = local_path(root, answer['input_path'])
    require(answer['input_path'] == f"inputs/{inp['case_id']}.json", 'input path mismatch')
    require(digest(path.read_bytes()) == answer['input_sha256'], 'stale answer/input binding')
    # Validate supplied object against its bound serialized file as well.
    require(json.loads(path.read_text()) == inp, 'input object differs from bound file')
    for side in ['source', 'candidate']:
        docs = inp[side + '_documents']
        ids = [d['document_id'] for d in docs]
        require(len(ids) == len(set(ids)), 'duplicate document IDs')
        for doc in docs:
            text = doc['content']
            if doc['availability'] == 'not_provided':
                require(text is None and doc['sha256'] is None, 'unavailable document has content')
            else:
                require(isinstance(text, str) and bool(text), 'available document lacks content')
                require(digest(text.encode('utf-8')) == doc['sha256'], 'content hash mismatch')
            p = doc['provenance']
            if p['kind'] == 'public_git':
                require(all(p[k] for k in ['repository', 'version', 'url', 'snapshot_path', 'snapshot_sha256', 'git_blob_sha']), 'public provenance incomplete')
                raw = local_path(root, p['snapshot_path']).read_bytes()
                require(digest(raw) == p['snapshot_sha256'], 'snapshot hash mismatch')
                blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                require(blob == p['git_blob_sha'], 'Git blob mismatch')
                require(text == raw.decode('utf-8'), 'public original differs from full snapshot')
    candidate_ids = {d['document_id'] for d in inp['candidate_documents']}
    scopes = inp['writing_contract']['output_document_ids']
    require(len(scopes) == len(set(scopes)) and set(scopes) == candidate_ids, 'output scope mismatch')
    requirements = inp['writing_contract']['required_information']
    require(len({r['id'] for r in requirements}) == len(requirements), 'duplicate requirement IDs')
    for finding in answer['findings']:
        check_evidence(finding['evidence'], inp)
    sides = {e['side'] for f in answer['findings'] for e in f['evidence']}
    require(sides == {'source', 'candidate'}, 'both-side evidence required')
    require(set(answer['focus']) == {f['error_type'] for f in answer['findings']}, 'focus/findings mismatch')
    expected_severity = {'PRESERVED': {'none'}, 'VIOLATION': {'minor', 'major', 'critical'}, 'UNRESOLVED': {'undetermined'}}
    require(all(f['severity'] in expected_severity[answer['expected_judgment']] for f in answer['findings']), 'judgment/severity mismatch')
    if answer['expected_judgment'] == 'UNRESOLVED':
        require(bool(inp['missing_context']), 'unresolved case needs explicit evidence gap')
    reviews = answer['reviews']
    ids = [r['reviewer_id'] for r in reviews]
    require(len(ids) == len(set(ids)), 'duplicate reviewer')
    for review in reviews:
        require(review['input_sha256'] == answer['input_sha256'], 'stale human review')
        check_evidence(review['evidence'], inp)
    for disagreement in answer['disagreements']:
        require(set(disagreement['reviewer_ids']) <= set(ids), 'unknown disagreement reviewer')
        require(len(set(disagreement['reviewer_ids'])) >= 2, 'disagreement needs distinct reviewers')
        require((disagreement['resolution'] is None) == (disagreement['resolved_by'] is None), 'incomplete resolution')
    if len({r['judgment'] for r in reviews}) > 1:
        require(bool(answer['disagreements']), 'different judgments need disagreement record')
    if answer['status'] == 'provisional':
        require(not answer['gold_eligible'] and answer['adjudication'] is None, 'provisional cannot be gold/adjudicated')
    else:
        require(len(reviews) >= 2 and all(r['blinded_to_ai_proposal'] for r in reviews), 'two blinded human reviews required')
        if answer['status'] == 'reviewed':
            require(not answer['gold_eligible'] and answer['adjudication'] is None, 'reviewed is not adjudicated gold')
        else:
            adj = answer['adjudication']
            require(adj is not None, 'missing human adjudication')
            require(adj['adjudicator_id'] not in ids, 'adjudicator must be independent')
            require(adj['input_sha256'] == answer['input_sha256'], 'stale adjudication')
            require(all(d['resolution'] is not None for d in answer['disagreements']), 'unresolved disagreement')
    return True


def validate_dataset(root=ROOT):
    manifest = read_json(root, 'manifest.json')
    require(manifest['split'] == 'development_only', 'pilot cannot be holdout')
    require(manifest['status'] == 'provisional_not_gold', 'pilot is not human gold')
    rows = manifest['cases']
    require(len(rows) == manifest['case_count'] == 12, 'pilot must contain 12 cases')
    ids = [r['case_id'] for r in rows]
    require(set(ids) == {f'SP-{i:03}' for i in range(1, 13)} and len(set(ids)) == 12, 'case ID inventory mismatch')
    require(Counter(r['expected_judgment'] for r in rows) == {'PRESERVED': 4, 'VIOLATION': 4, 'UNRESOLVED': 4}, '4/4/4 composition mismatch')
    for side in ['input', 'answer']:
        actual = {str(p.relative_to(root)) for p in (root / (side + 's')).glob('*.json')}
        require(actual == {r[side + '_path'] for r in rows}, 'orphan/missing files')
    require(Counter(r['source_kind'] for r in rows) == {'public_source_based': 3, 'controlled_synthetic': 9}, 'source composition mismatch')
    for row in rows:
        for side in ['input', 'answer']:
            path = local_path(root, row[side + '_path'])
            require(digest(path.read_bytes()) == row[side + '_sha256'], f'manifest hash mismatch: {path.name}')
        inp = read_json(root, row['input_path'])
        answer = read_json(root, row['answer_path'])
        require(row['case_id'] == inp['case_id'] == answer['case_id'], 'manifest ID mismatch')
        require(row['source_kind'] == inp['source_kind'] and row['expected_judgment'] == answer['expected_judgment'], 'manifest metadata mismatch')
        require(answer['status'] == 'provisional', 'this pilot must remain provisional')
        has_public = any(d['provenance']['kind'] == 'public_git' for d in inp['source_documents'])
        require(has_public == (inp['source_kind'] == 'public_source_based'), 'source kind/provenance mismatch')
        validate_pair(inp, answer, root)
    for snapshot in manifest['source_snapshots']:
        require(digest(local_path(root, snapshot['path']).read_bytes()) == snapshot['sha256'], 'source snapshot mismatch')
    return len(rows)


if __name__ == '__main__':
    count = validate_dataset()
    print(f'Validated {count} provisional development cases (4/4/4); semantic labels NOT verified.')

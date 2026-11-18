#!/usr/bin/env python3
"""Read-only evaluation integrity. Does not decide semantic correctness or grant approval."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def local(root, path):
    require(isinstance(path, str) and not Path(path).is_absolute(), 'relative path required')
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()) and target.is_file(), 'missing or escaping path: ' + path)
    return target


def read(root, path):
    return json.loads(local(root, path).read_text(encoding='utf-8'))


def schema_check(root, name, value):
    schema = read(root, name + '.schema.json')
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    require(not errors, name + ': ' + '; '.join(e.message for e in errors))


def unique(items, key):
    ids = [x[key] for x in items]
    require(len(set(ids)) == len(ids), 'duplicate ' + key)
    return set(ids)


def check_evidence(items, docs):
    ids = unique(items, 'id')
    for e in items:
        require(e['document_id'] in docs, 'unknown evidence document')
        text = docs[e['document_id']]['content']
        require(0 <= e['start'] < e['end'] <= len(text), 'evidence bounds')
        require(text[e['start']:e['end']] == e['quote'], 'evidence quote mismatch')
    return ids


def check_input(root, inp):
    version = inp.get('schema_version')
    require(version in ('integrated-input-v1', 'integrated-input-v2'), 'unknown input version')
    schema_check(root, 'input-v2' if version == 'integrated-input-v2' else 'input', inp)
    if version == 'integrated-input-v2':
        incomplete = (inp['availability']['document_set'] != 'complete'
                      or any(d['completeness'] == 'excerpt' for d in inp['documents']))
        require(not incomplete or bool(inp['availability']['gaps']), 'incomplete input requires declared gaps')
    unique(inp['documents'], 'document_id')
    unique(inp['documents'], 'path')
    for d in inp['documents']:
        path = PurePosixPath(d['path'])
        require(not path.is_absolute() and '..' not in path.parts, 'document path escapes')
        require(digest(d['content'].encode()) == d['sha256'], 'document hash mismatch')
    # Schema allowlist rejects answer/review/action-label fields. Natural-language
    # answer leakage is a separate human review, not inferred by regex.


def export_input(root, cid):
    require(re.fullmatch(r'IR-[0-9]{3}', cid), 'invalid case ID')
    value = read(root, f'inputs/{cid}.json')
    check_input(root, value)
    require(value['case_id'] == cid, 'case ID mismatch')
    return value


def check_links(output, source_docs):
    paths = {d['path'] for d in source_docs.values()}
    for d in output:
        base = PurePosixPath(source_docs[d['document_id']]['path']).parent
        for target in re.findall(r'\]\(([^ )]+)\)', d['content']):
            if '://' in target or target.startswith(('#', 'mailto:')):
                continue
            parts = []
            for part in (base / target.split('#', 1)[0]).parts:
                if part == '..':
                    require(bool(parts), 'link escapes document set')
                    parts.pop()
                elif part != '.':
                    parts.append(part)
            require('/'.join(parts) in paths, 'broken local link: ' + target)


def validate_package(root=ROOT):
    root = Path(root).resolve()
    meta = read(root, 'cases.json')
    require(unique(meta, 'case_id') == {'IR-001', 'IR-002', 'IR-003'}, 'representative case set mismatch')
    evidence_count = 0
    for m in meta:
        cid = m['case_id']
        for key in ('input', 'answer', 'review'):
            require(m[key + '_path'] == f'{key}s/{cid}.json', 'unexpected record path')
        inp = export_input(root, cid)
        ans = read(root, m['answer_path'])
        review = read(root, m['review_path'])
        for name, record in [('answer', ans), ('review', review)]:
            schema_check(root, name, record)
            require(record['case_id'] == cid, 'case ID mismatch')
            require(record['input_sha256'] == digest(local(root, m['input_path']).read_bytes()), 'stale input binding')
        require(review['gold_inclusion_approval'] is None, 'approval is outside this draft package')
        docs = {d['document_id']: d for d in inp['documents']}
        evidence = check_evidence(ans['evidence'], docs)
        evidence_count += len(evidence)
        constraint_pointers = [c['input_pointer'] for c in ans['D']['explicit_constraints']]
        require(set(constraint_pointers) == {f'/explicit_constraints/{i}' for i in range(len(inp['explicit_constraints']))}, 'constraint trace mismatch')
        require(len(constraint_pointers) == len(set(constraint_pointers)), 'duplicate constraint pointer')
        for c in ans['D']['explicit_constraints']:
            require(c['interpretation'] == inp['explicit_constraints'][int(c['input_pointer'].rsplit('/', 1)[1])], 'explicit constraint drift')
        for items in [ans['D']['inferred_requirements'], ans['D']['decision_criteria'], ans['Q']['invariants'], ans['Q']['forbidden_outcomes']]:
            unique(items, 'id')
            for item in items:
                require(set(item['evidence_refs']) <= evidence, 'unknown evidence ref')
        required = unique(ans['Q']['invariants'], 'id')
        unique(ans['Q']['acceptable_bundles'], 'id')
        for bundle in ans['Q']['acceptable_bundles']:
            require(set(bundle['must_satisfy']) == required, 'alternative skips invariant')
        require(not ans['D']['confirmation'] or bool(inp['availability']['gaps']), 'unexplained confirmation')
        out = read(root, ans['Q']['reference_output_path'])
        schema_check(root, 'reference', out)
        require(out['case_id'] == cid and out['input_sha256'] == ans['input_sha256'], 'stale reference binding')
        require(out['bundle'] in {b['id'] for b in ans['Q']['acceptable_bundles']}, 'unknown bundle')
        returned = unique(out['documents'], 'document_id')
        writable = {id for id, d in docs.items() if d['access'] in ('edit', 'format_only')}
        require(returned == writable, 'incomplete or unauthorized whole-document output')
        for d in out['documents']:
            require(digest(d['content'].encode()) == d['sha256'], 'output hash mismatch')
            if docs[d['document_id']]['access'] == 'format_only':
                # Conservative lexical protection; this is not a general semantic test.
                require(d['content'].split() == docs[d['document_id']]['content'].split(), 'format-only content changed')
        check_links(out['documents'], docs)
        require(m['source_family'] == 'synthetic-author-cluster-20261113' and not m['independent_real_source'], 'source independence inflated')
        require(m['split'] == 'exposed_development', 'exposed material is not a holdout')
    return dict(cases=len(meta),exact_citations=evidence_count,human_review='pending',gold_eligible=False,semantic_quality='not_measured')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--input', metavar='CASE_ID', help='emit only the model input; never answers or review metadata')
    args = parser.parse_args()
    result = export_input(args.root, args.input) if args.input else validate_package(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

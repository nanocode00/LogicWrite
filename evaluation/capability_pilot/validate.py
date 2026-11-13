#!/usr/bin/env python3
"""Read-only structural integrity checks. This does not score D/Q or approve gold."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def local(root, path):
    require(isinstance(path, str) and not Path(path).is_absolute(), 'relative path required')
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()), 'path escapes package')
    require(target.is_file(), 'missing file: ' + path)
    return target


def read(root, path):
    return json.loads(local(root, path).read_text(encoding='utf-8'))


def schema_check(root, name, record):
    schema = read(root, name + '.schema.json')
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(record))
    require(not errors, f'{name} schema: ' + '; '.join(e.message for e in errors))


def check_evidence(evidence, docs):
    ids = set()
    for e in evidence:
        require(e['id'] not in ids, 'duplicate evidence ID')
        ids.add(e['id'])
        require(e['document_id'] in docs, 'unknown evidence document')
        doc = docs[e['document_id']]
        text = doc['content']
        require(isinstance(text, str), 'evidence in unavailable document')
        require(0 <= e['start'] < e['end'] <= len(text), 'evidence bounds')
        require(text[e['start']:e['end']] == e['quote'], 'evidence quote mismatch')
    return ids


def replay(raw, transformations):
    text = raw
    for change in transformations:
        op, part = change['operation'], change['text']
        if op == 'append':
            text += part
        else:
            require(part in text, 'transform source absent')
            text = text.replace(part, '', 1)
            if op == 'move_to_end':
                text += '\n' + part
            else:
                require(op == 'remove_first', 'unknown transformation')
    return text


def validate_pair(root, meta, sources):
    cid = meta['case_id']
    inp, answer, review = [read(root, meta[k + '_path']) for k in ('input', 'answer', 'review')]
    for name, value in [('input', inp), ('answer', answer), ('review', review)]:
        schema_check(root, name, value)
        require(value['case_id'] == cid, 'case ID mismatch')
    for key in ('input', 'answer', 'review'):
        require(meta[key + '_path'] == f'{key}s/{cid}.json', 'unexpected case path')
    bound = digest(local(root, meta['input_path']).read_bytes())
    require(answer['input_sha256'] == review['input_sha256'] == bound, 'stale input binding')
    require(review['initial_ai_proposal'] == meta['answer_path'], 'proposal path mismatch')
    docs_list = inp['source_documents'] + inp['destination_documents'] + inp['supporting_evidence']
    docs = {d['document_id']: d for d in docs_list}
    require(len(docs) == len(docs_list), 'duplicate document IDs')
    for doc in docs_list:
        text = doc['content']
        if doc['availability'] == 'not_provided':
            require(text is None and doc['sha256'] is None and doc['completeness'] == 'unknown', 'unavailable document has content')
        else:
            require(isinstance(text, str) and bool(text), 'provided document empty')
            require(digest(text.encode('utf-8')) == doc['sha256'], 'document hash mismatch')
        origin = doc['origin']
        if origin['kind'] in ('public_snapshot', 'controlled_public'):
            require(origin['source_key'] in sources, 'unknown source')
            source = sources[origin['source_key']]
            require(meta['source_family'] == source['family_id'], 'source family misassigned')
            raw = local(root, source['document']['path']).read_bytes().decode('utf-8')
            require(text == replay(raw, origin['transformations']), 'document provenance transformation mismatch')
    scope = inp['allowed_edit_scope']['document_ids']
    require(len(scope) == len(set(scope)), 'duplicate output scope')
    require(set(scope) <= set(docs), 'unknown output document')
    outputs = inp['contract']['output_document_ids']
    require(len(outputs) == len(set(outputs)) and set(outputs) <= set(docs), 'invalid output document')
    require(set(scope) <= set(outputs), 'contract/scope mismatch')
    require(all('read-only' in docs[k]['role'] for k in set(outputs) - set(scope)), 'uneditable output must be explicitly read-only')
    require(all('read-only' not in docs[k]['role'] for k in scope), 'read-only document in scope')
    evidence_ids = check_evidence(answer['evidence'], docs)
    d = answer['D']
    for field in ('obligations', 'required_decisions', 'optional_decisions', 'forbidden_outcomes', 'acceptable_alternatives', 'relations'):
        items = d[field]
        if items and 'id' in items[0]:
            require(len({x['id'] for x in items}) == len(items), 'duplicate D item ID: ' + field)
        for item in items:
            require(set(item['evidence_refs']) <= evidence_ids, 'unknown D evidence ref')
    for field in ('protected_facts', 'task_checks'):
        require(len({x['id'] for x in answer['Q'][field]}) == len(answer['Q'][field]), 'duplicate Q item ID')
        for item in answer['Q'][field]:
            require(set(item['evidence_refs']) <= evidence_ids, 'unknown Q evidence ref')
    req, forbidden = d['required_effects'], d['forbidden_effects']
    require(set(req) == {x['id'] for x in d['required_decisions']}, 'required decision/effect mismatch')
    require(set(forbidden) == {x['id'] for x in d['forbidden_outcomes']}, 'forbidden decision/effect mismatch')
    require(not set(req) & set(forbidden), 'required and forbidden ID collision')
    for alt in d['acceptable_alternatives']:
        effects = alt['effects']
        require(set(effects) == set(req) | set(forbidden), 'incomplete alternative bundle')
        require(all(effects[k] == v for k, v in req.items()), 'alternative misses required effect')
        require(all(effects[k] != v for k, v in forbidden.items()), 'alternative requires forbidden effect')
    unresolved = d['applicability']['state'] == 'unresolved'
    require(unresolved == bool(d['unresolved_questions']), 'unresolved questions mismatch')
    require(not unresolved or bool(inp['availability']['gaps']), 'unresolved needs input gap')
    require(unresolved or not inp['availability']['gaps'] or inp['availability']['candidate_output'] == 'fragment_only', 'unaccounted input gaps')
    require(answer['metrics']['D']['abstention']['expected'] == unresolved, 'abstention mismatch')
    require(answer['metrics']['D']['required_decision_recall']['denominator'] == len(req), 'recall denominator mismatch')
    require(answer['metrics']['D']['forbidden_outcome_count']['denominator'] == len(forbidden), 'forbidden denominator mismatch')
    if answer['Q']['applicability'] == 'unresolved_contract':
        require(unresolved and inp['availability']['candidate_output'] != 'fragment_only', 'Q contract gap differs from partial output')
    if inp['availability']['candidate_output'] == 'fragment_only':
        require(answer['Q']['applicability'] == 'not_evaluated_incomplete', 'partial Q must be incomplete')
    for coverage in meta['subscenario_evidence'].values():
        require(set(coverage['evidence_refs']) <= evidence_ids, 'coverage evidence absent')
        # Resolve real JSON pointer, rather than accepting a path-shaped string.
        value = answer
        for part in coverage['answer_pointer'].strip('/').split('/'):
            value = value[part]
        require(bool(value), 'coverage criterion empty')
    return inp, answer, review


def validate_package(root=ROOT, require_reviews=True):
    root = Path(root).resolve()
    source_rows = read(root, 'sources.json')
    sources = {s['repository']: s for s in source_rows}
    require(len(sources) == len(source_rows), 'duplicate source key')
    for source in source_rows:
        require(source['rights_status'] == 'license_text_checked', 'unverified rights')
        require(source['redistribution'] == 'permitted_with_retained_license_and_notices', 'redistribution unclear')
        require(len(source['commit']) == 40, 'source commit not pinned')
        for record in [source['document'], source['license']] + source['notices']:
            raw = local(root, record['path']).read_bytes()
            require(digest(raw) == record['sha256'], 'snapshot/license hash mismatch')
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            require(blob == record['git_blob_sha'], 'git blob mismatch')
            require('/' + source['commit'] + '/' in record['url'], 'source URL not immutable')
    cases = read(root, 'cases.json')
    require(len({c['case_id'] for c in cases}) == len(cases), 'duplicate case')
    subscenarios = read(root, 'subscenarios.json')
    counts = Counter(c['primary_type'] for c in cases)
    require(set(counts) == set(subscenarios) and all(n >= 4 for n in counts.values()), 'type counts insufficient')
    require(sum(c['calibration'] for c in cases) == 9, 'nine calibration cases required')
    require({c['primary_type'] for c in cases if c['calibration']} == set(subscenarios), 'calibration type missing')
    review_count = 0
    for c in cases:
        cid = c['case_id']
        require(c['status'] == 'provisional' and c['split'] == 'development', 'candidate status/split changed')
        require(set(c['subscenario_ids']) <= set(subscenarios[c['primary_type']]), 'unknown subscenario')
        require(set(c['subscenario_ids']) == set(c['subscenario_evidence']), 'coverage evidence mismatch')
        require(c['complexity'] in ('simple','compound') and c['risk'] in ('ordinary','high'), 'invalid axes')
        if c['source_key'] in sources:
            require(c['source_family'] == sources[c['source_key']]['family_id'], 'source family mismatch')
        else:
            require(c['source_key'] == c['source_family'] == 'synthetic-author-batch-20261113', 'synthetic family inflation')
        inp, answer, review = validate_pair(root, c, sources)
        record = review['independent_ai_counterreview']
        if record:
            path = local(root, record['path'])
            require(digest(path.read_bytes()) == record['sha256'], 'raw review hash mismatch')
            data = json.loads(path.read_text())
            schema_check(root, 'raw_review', data)
            require(len({x['case_id'] for x in data['cases']}) == len(data['cases']), 'duplicate raw review case')
            item = data
            for key in record['case_pointer'].strip('/').split('/'):
                item = item[int(key)] if isinstance(item, list) else item[key]
            require(item['case_id'] == cid and item['input_sha256'] == record['reviewed_input_sha256'], 'raw review case binding')
            require(record['superseded_input'] == (item['input_sha256'] != answer['input_sha256']), 'review revision marker mismatch')
            reviewed_input = inp
            if record['superseded_input']:
                reviewed_path = local(root, f'reviewed_inputs/{cid}.json')
                require(digest(reviewed_path.read_bytes()) == item['input_sha256'], 'superseded review input missing')
                reviewed_input = json.loads(reviewed_path.read_text())
            docs = {d['document_id']: d for d in reviewed_input['source_documents'] + reviewed_input['destination_documents'] + reviewed_input['supporting_evidence']}
            for e in item['evidence']:
                require(e['document_id'] in docs and e['quote'] in docs[e['document_id']]['content'], 'raw review evidence mismatch')
            require(item['evidence'], 'raw review evidence absent')
            review_count += 1
        elif require_reviews:
            raise ValueError('independent AI review missing: ' + cid)
    for kind, required_subs in subscenarios.items():
        rows = [c for c in cases if c['primary_type'] == kind]
        covered = {s for c in rows for s in c['subscenario_ids']}
        require(covered == set(required_subs), 'required subscenario gap: ' + kind)
        require({'simple','compound'} <= {c['complexity'] for c in rows}, 'complexity gap: ' + kind)
        require('high' in {c['risk'] for c in rows}, 'risk gap: ' + kind)
    reconciliations = read(root, 'ai_reconciliation.json')
    require({r['case_id'] for r in reconciliations} == {c['case_id'] for c in cases}, 'review history case set mismatch')
    for reconciliation in reconciliations:
        cid = reconciliation['case_id']
        require(reconciliation['actor_type'] == 'ai' and reconciliation['human_adjudication'] is None, 'AI reconciliation is not human adjudication')
        for record in reconciliation['review_history']:
            path = local(root, record['path'])
            require(digest(path.read_bytes()) == record['sha256'], 'historical review hash mismatch')
            data = json.loads(path.read_text())
            schema_check(root, 'raw_review', data)
            item = data
            for key in record['case_pointer'].strip('/').split('/'):
                item = item[int(key)] if isinstance(item, list) else item[key]
            require(item['case_id'] == cid and item['input_sha256'] == record['reviewed_input_sha256'], 'historical review binding')
            selected = f'reviewed_inputs/{cid}.json' if record['superseded_input'] else f'inputs/{cid}.json'
            previous_raw = local(root, selected).read_bytes()
            require(digest(previous_raw) == item['input_sha256'], 'previous reviewed input hash mismatch')
            previous = json.loads(previous_raw)
            docs = {d['document_id']: d for d in previous['source_documents'] + previous['destination_documents'] + previous['supporting_evidence']}
            for evidence in item['evidence']:
                require(evidence['document_id'] in docs and evidence['quote'] in docs[evidence['document_id']]['content'], 'historical review quote mismatch')
    responses = read(root, 'human_responses.json')
    schema_check(root, 'human_response', responses)
    response_ids = [x['case_id'] for x in responses['cases']]
    require(len(response_ids) == len(set(response_ids)) and set(response_ids) == {c['case_id'] for c in cases}, 'human response case set mismatch')
    holdout = read(root, 'holdout_registry.json')
    require(holdout['families'] == [] and holdout['status'] == 'not_collected', 'public pilot cannot become holdout')
    if (root / 'protected_baseline.json').exists():
        baseline = read(root, 'protected_baseline.json')
        repo = root.parent.parent
        if (repo / 'evaluation/active_development_gold.json').is_file():
            for path, expected in baseline['files'].items():
                require(digest((repo / path).read_bytes()) == expected, 'protected existing file changed: ' + path)
    return {'cases':len(cases),'by_type':dict(sorted(counts.items())), 'calibration':9,'public_originals':len(sources),'source_family_clusters':len({c['source_family'] for c in cases}),'independent_ai_reviews':review_count,'human_reviews':0,'formal_gold_approvals':0,'holdout':0,'semantic_validation':'human_pending'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--allow-pending-ai', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(validate_package(args.root, not args.allow_pending_ai), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'invalid: {error}\n')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Separate, append-only development review records; no AI-authored human judgments."""
import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
LIMITS = ['single_human_reviewer', 'ai_assistance_is_not_independent_human_review', 'not_independent_holdout']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def event_digest(event):
    return digest(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_schema(record):
    schema = json.loads((HERE / 'record.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(record))
    require(not errors, 'record schema invalid: ' + '; '.join(e.message for e in errors))


def evidence_ok(items, inp):
    for ev in items:
        docs = {d['document_id']: d for d in inp[ev['side'] + '_documents']}
        require(ev['document_id'] in docs, 'unknown evidence document')
        text = docs[ev['document_id']]['content']
        require(text is not None, 'evidence in missing document')
        require(0 <= ev['start'] < ev['end'] <= len(text), 'evidence outside text')
        require(text[ev['start']:ev['end']] == ev['quote'], 'evidence quote mismatch')


def new_record(case_id, pilot=PILOT):
    require(case_id in {f'SP-{n:03}' for n in range(1,13)}, 'case outside pilot')
    record = dict(schema_version='1.0.0',case_id=case_id,
                  input_sha256=digest((pilot / f'inputs/{case_id}.json').read_bytes()),
                  ai_proposal_sha256=digest((pilot / f'answers/{case_id}.json').read_bytes()),
                  method='single_user_ai_counterreview', dataset_role='development_only',
                  confidence_limits=LIMITS.copy(),events=[])
    assess(record,pilot)
    return record


def assess(record, pilot=PILOT):
    validate_schema(record)
    cid = record['case_id']
    require(cid in {f'SP-{n:03}' for n in range(1,13)}, 'case outside pilot')
    raw = (pilot / f'inputs/{cid}.json').read_bytes()
    require(digest(raw) == record['input_sha256'], 'stale input binding')
    require(digest((pilot / f'answers/{cid}.json').read_bytes()) == record['ai_proposal_sha256'], 'stale AI proposal binding')
    inp = json.loads(raw)
    state, eligible, final = 'ai_provisional', False, None
    seen, previous, user, initial, counter = set(), None, None, None, None
    last_timestamp = None
    for event in record['events']:
        require(event['event_id'] not in seen, 'duplicate event ID')
        seen.add(event['event_id'])
        require(event['previous_event_sha256'] == previous, 'history hash chain mismatch')
        try:
            timestamp = datetime.fromisoformat(event['recorded_at'])
            require(timestamp.tzinfo is not None, 'event timestamp needs timezone')
            require(last_timestamp is None or timestamp >= last_timestamp, 'event time moves backwards')
            last_timestamp = timestamp
        except (ValueError, TypeError) as exc:
            raise ValueError('invalid event timestamp') from exc
        kind, p = event['kind'], event['payload']
        if kind in {'user_initial','user_final','reopen'}:
            require(event['actor_type']=='human' and p['human_confirmed'], 'human confirmation required')
            if user is None:
                user = event['actor_id']
            require(event['actor_id']==user, 'single-user record cannot switch human identity')
        else:
            require(event['actor_type']=='ai' and event['actor_id']!=user, 'AI is assistance, not human review')
        if kind=='user_initial':
            require(state in {'ai_provisional','reopened'}, 'initial review out of order')
            form=p['form']
            require(form['case_id']==cid and form['input_sha256']==record['input_sha256'], 'initial form binding mismatch')
            require(form['reviewer_id']==user, 'initial form reviewer mismatch')
            require(not form['blinded_to_prior_judgments'] or p['ai_proposal_exposure']=='not_seen', 'AI exposure conflicts with blinding declaration')
            evidence_ok(form['evidence'],inp)
            if form['judgment']=='UNRESOLVED':
                require(form['missing_information'], 'initial unresolved requires missing information')
            if form['judgment']=='VIOLATION':
                require(form['findings'], 'initial violation requires findings')
            initial=event['event_id'];state='user_initial_reviewed'
        elif kind=='ai_counterreview':
            require(state=='user_initial_reviewed' and p['initial_event_id']==initial, 'counterreview must bind current initial')
            require(p['separate_review'], 'separate AI review required')
            require(set(p['review_scope'])=={'counterexamples','missing_conditions','contradictions'} and len(p['review_scope'])==3, 'incomplete counterreview scope')
            ids=[c['challenge_id'] for c in p['challenges']]
            require(len(ids)==len(set(ids)), 'duplicate challenge ID')
            require(bool(ids) or bool(p['no_challenge_reason']), 'empty AI counterreview needs explanation')
            for challenge in p['challenges']:
                evidence_ok(challenge['evidence'],inp)
            counter=event;state='ai_counterreview_completed'
        elif kind=='user_final':
            require(state=='ai_counterreview_completed' and p['counterreview_event_id']==counter['event_id'], 'final must bind current counterreview')
            expected={c['challenge_id'] for c in counter['payload']['challenges']}
            ids=[r['challenge_id'] for r in p['responses']]
            require(len(ids)==len(set(ids)) and set(ids)==expected, 'each challenge requires exactly one response')
            deferred=any(r['decision']=='defer' for r in p['responses'])
            require(not (deferred and p['approve_for_development_gold']), 'deferred challenge prevents development gold')
            require(not p['unresolved_issues'] or p['judgment']=='UNRESOLVED' or not p['approve_for_development_gold'], 'unresolved issues cannot be hidden by gold label')
            if p['judgment']=='UNRESOLVED':
                require(p['unresolved_issues'], 'unresolved final needs explicit issues')
            evidence_ok(p['evidence'],inp)
            state='user_final_confirmed';eligible=p['approve_for_development_gold'];final=p['judgment']
        else:
            require(state=='user_final_confirmed', 'reopen requires prior final')
            state='reopened';eligible=False;final=None;initial=None;counter=None
        previous=event_digest(event)
    return dict(review_level=state, development_gold_eligible=eligible,
                independent_multi_human_complete=False, final_judgment=final,
                method=record['method'], confidence_limits=record['confidence_limits'])


def append_event(record, event, pilot=PILOT):
    assess(record,pilot)
    result=copy.deepcopy(record)
    supplied=copy.deepcopy(event)
    require('previous_event_sha256' not in supplied, 'history link is derived by append')
    supplied['previous_event_sha256']=event_digest(result['events'][-1]) if result['events'] else None
    result['events'].append(supplied)
    assess(result,pilot)
    return result


def assess_independent_record(answer, pilot=PILOT):
    # Validate a NEW independent-review sidecar with the unchanged legacy rules.
    # It does not overwrite the original answer or its guided-user history.
    require(answer.get('status') in {'reviewed','adjudicated'}, 'independent status requires reviewed/adjudicated record')
    spec=importlib.util.spec_from_file_location('pilot_legacy_validation',pilot / 'validate.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    cid=answer['case_id']
    require(cid in {f'SP-{n:03}' for n in range(1,13)}, 'case outside pilot')
    original=json.loads((pilot / f'answers/{cid}.json').read_text())
    review_fields={'status','gold_eligible','reviews','disagreements','adjudication'}
    require({k:v for k,v in original.items() if k not in review_fields} ==
            {k:v for k,v in answer.items() if k not in review_fields}, 'independent sidecar changed original AI proposal')
    inp=json.loads((pilot / f'inputs/{cid}.json').read_text())
    legacy.validate_pair(inp,answer,pilot)
    complete=answer['status']=='adjudicated'
    return dict(review_level='independent_multi_human_adjudicated' if complete else 'independent_multi_human_reviewed',
                development_gold_eligible=complete and answer['gold_eligible'],
                independent_multi_human_complete=complete,
                final_judgment=answer['adjudication']['judgment'] if complete else None,
                method='independent_multi_human', legacy_gold_eligible=answer['gold_eligible'])


def save_new(path, record):
    assess(record)
    # Exclusive creation preserves previous snapshots and refuses in-place rewriting.
    with Path(path).open('x',encoding='utf-8') as file:
        file.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('case_id');init.add_argument('--output',type=Path,required=True)
    check=sub.add_parser('check');check.add_argument('record',type=Path)
    append=sub.add_parser('append');append.add_argument('record',type=Path);append.add_argument('--event',type=Path,required=True);append.add_argument('--output',type=Path,required=True)
    independent=sub.add_parser('check-independent');independent.add_argument('record',type=Path)
    args=parser.parse_args()
    if args.command=='check-independent':
        print(json.dumps(assess_independent_record(json.loads(args.record.read_text())),ensure_ascii=False,indent=2))
        raise SystemExit(0)
    if args.command=='init':
        result=new_record(args.case_id);save_new(args.output,result)
    else:
        result=json.loads(args.record.read_text())
        if args.command=='append':
            result=append_event(result,json.loads(args.event.read_text()));save_new(args.output,result)
    print(json.dumps(assess(result),ensure_ascii=False,indent=2))

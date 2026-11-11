#!/usr/bin/env python3
"""Registry-bound SP/GC review; actual human events must be supplied, never inferred."""
import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
spec=importlib.util.spec_from_file_location('frozen_single_user_review',HERE.parent/'semantic_pilot/user_review_v1/workflow.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
sha=legacy.digest
require=legacy.require

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def row(cid):
    rows={r['case_id']:r for r in load(HERE/'registry.json')['cases']}
    require(cid in rows,'case outside registered review inventory')
    return rows[cid]
def resolve(name):
    path=(HERE/name).resolve()
    require(path.is_relative_to((ROOT/'evaluation').resolve()),'reference outside evaluation')
    return path

def new_record(cid):
    r=row(cid)
    record=dict(schema_version='1.0.0',case_id=cid,input_sha256=r['input_sha256'],ai_proposal_sha256=r['answer_sha256'],method='single_user_ai_counterreview',dataset_role='development_only',confidence_limits=legacy.LIMITS.copy(),events=[])
    assess(record)
    return record

def assess(record):
    errors=list(Draft202012Validator(load(HERE/'record.schema.json')).iter_errors(record))
    require(not errors,'record schema invalid: '+'; '.join(e.message for e in errors))
    r=row(record['case_id']);ip=resolve(r['input_path']);ap=resolve(r['answer_path'])
    require(sha(ip.read_bytes())==r['input_sha256']==record['input_sha256'],'stale input binding')
    require(sha(ap.read_bytes())==r['answer_sha256']==record['ai_proposal_sha256'],'stale AI binding')
    inp=load(ip);require(inp['case_id']==record['case_id'],'input ID mismatch')
    state='ai_provisional';eligible=False;final=None;previous=None;seen=set();user=None;initial=None;counter=None;last=None
    for event in record['events']:
        require(event['event_id'] not in seen,'duplicate event ID');seen.add(event['event_id'])
        require(event['previous_event_sha256']==previous,'history hash chain mismatch')
        stamp=datetime.fromisoformat(event['recorded_at'])
        require(stamp.tzinfo is not None and (last is None or stamp>=last),'invalid event timestamp');last=stamp
        kind,p=event['kind'],event['payload']
        if kind in {'user_initial','user_final','reopen'}:
            require(event['actor_type']=='human' and p['human_confirmed'],'human confirmation required')
            if user is None:user=event['actor_id']
            require(event['actor_id']==user,'single human identity required')
        else:require(event['actor_type']=='ai' and event['actor_id']!=user,'AI is assistance only')
        if kind=='user_initial':
            require(state in {'ai_provisional','reopened'},'initial review out of order')
            f=p['form'];require(f['case_id']==record['case_id'] and f['input_sha256']==record['input_sha256'] and f['reviewer_id']==user,'initial binding mismatch')
            require(not f['blinded_to_prior_judgments'] or p['ai_proposal_exposure']=='not_seen','inconsistent blinding')
            legacy.evidence_ok(f['evidence'],inp)
            require(f['judgment']!='UNRESOLVED' or bool(f['missing_information']),'unresolved needs missing information')
            require(f['judgment']!='VIOLATION' or bool(f['findings']),'violation needs findings')
            initial=event['event_id'];state='user_initial_reviewed'
        elif kind=='ai_counterreview':
            require(state=='user_initial_reviewed' and p['initial_event_id']==initial,'counterreview needs current user initial')
            require(p['separate_review'] and len(p['review_scope'])==3 and set(p['review_scope'])=={'counterexamples','missing_conditions','contradictions'},'separate complete counterreview required')
            ids=[c['challenge_id'] for c in p['challenges']]
            require(len(ids)==len(set(ids)) and (bool(ids) or bool(p['no_challenge_reason'])),'invalid challenges')
            for c in p['challenges']:legacy.evidence_ok(c['evidence'],inp)
            counter=event;state='ai_counterreview_completed'
        elif kind=='user_final':
            require(state=='ai_counterreview_completed' and p['counterreview_event_id']==counter['event_id'],'final needs current counterreview')
            expected={c['challenge_id'] for c in counter['payload']['challenges']};ids=[x['challenge_id'] for x in p['responses']]
            require(len(ids)==len(set(ids)) and set(ids)==expected,'every challenge needs one response')
            require(not any(x['decision']=='defer' for x in p['responses']) or not p['approve_for_development_gold'],'deferred challenge blocks gold')
            require(not p['unresolved_issues'] or p['judgment']=='UNRESOLVED' or not p['approve_for_development_gold'],'unresolved issues hidden')
            require(p['judgment']!='UNRESOLVED' or bool(p['unresolved_issues']),'unresolved final needs issues')
            legacy.evidence_ok(p['evidence'],inp)
            state='user_final_confirmed';eligible=p['approve_for_development_gold'];final=p['judgment']
        else:
            require(state=='user_final_confirmed','reopen needs final');state='reopened';eligible=False;final=None;initial=None;counter=None
        previous=legacy.event_digest(event)
    return dict(review_level=state,development_gold_eligible=eligible,final_judgment=final,independent_multi_human_complete=False)

def append_event(record,event):
    assess(record);result=copy.deepcopy(record);event=copy.deepcopy(event)
    require('previous_event_sha256' not in event,'history link derived by append')
    event['previous_event_sha256']=legacy.event_digest(result['events'][-1]) if result['events'] else None
    result['events'].append(event);assess(result);return result

def save_new(path,record):
    assess(record)
    with Path(path).open('x',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('init');p.add_argument('case_id');p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('check');p.add_argument('record',type=Path)
    p=sub.add_parser('append');p.add_argument('record',type=Path);p.add_argument('--event',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='init':save_new(args.output,new_record(args.case_id))
    elif args.command=='check':print(json.dumps(assess(load(args.record)),ensure_ascii=False))
    else:save_new(args.output,append_event(load(args.record),load(args.event)))

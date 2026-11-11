#!/usr/bin/env python3
"""Validate append-only activation of SP-009 after actual user reconfirmation."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PREFIX='evaluation/g3_g4/development_gold_v2_2026-11-11/'


def need(ok,message):
    if not ok:raise ValueError(message)


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(root,name,repo):
    if name.startswith(PREFIX):p=(root/name[len(PREFIX):]).resolve();boundary=root
    else:p=(repo/name).resolve();boundary=repo
    need(p.is_relative_to(boundary.resolve()) and p.is_file(),'invalid reference');return p


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def validate(root=HERE,repo=REPO):
    m=read(root/'development-gold.json')
    need(m['schema_version']=='2.0.0' and m['dataset_role']=='development_only','v2 development only')
    old_path=ref(root,m['previous_manifest_path'],repo);need(sha(old_path)==m['previous_manifest_sha256'],'previous manifest changed')
    prior=read(old_path);legacy=module('v2_prior_final_validation',old_path.parent/'validate.py')
    need(legacy.validate(old_path.parent,repo)['active_development_gold']==11,'previous layer changed')
    lockpath=ref(root,m['append_preservation_path'],repo);need(sha(lockpath)==m['append_preservation_sha256'],'append preservation hash')
    lock=read(lockpath);need(lock['baseline_commit']=='943492ad81d5f9d60291f9dbde2cf79b509cf892' and len(lock['files'])==178,'append preservation scope')
    for name,h in lock['files'].items():need(sha(ref(root,name,repo))==h,'previous evaluation file changed: '+name)
    for key in ['user_approval_path','user_approval_sha256','preservation_path','preservation_sha256','followup_path','followup_sha256','user_final_distribution']:
        need(m[key]==prior[key],'inherited approved metadata changed')
    rows=m['cases'];need(len(rows)==12 and {r['case_id'] for r in rows}=={f'SP-{n:03}' for n in range(1,13)},'case inventory')
    before={r['case_id']:r for r in prior['cases']}
    for row in rows:
        if row['case_id']!='SP-009':need(row==before[row['case_id']],'previous active case changed')
    row=next(r for r in rows if r['case_id']=='SP-009')
    source=ref(root,row['source_counterreview_path'],repo)
    need(row['source_counterreview_path']=='evaluation/g3_g4/sp009_followup_2026-11-11/SP-009.counterreview.json','must use fresh counterreview')
    need(sha(source)==row['source_counterreview_sha256'],'counterreview hash')
    sp=ref(root,row['snapshot_path'],repo);need(sha(sp)==row['snapshot_sha256'],'final snapshot hash')
    rec=read(sp);need(rec['events'][:-1]==read(source)['events'],'prior events changed')
    wf=module('v2_original_workflow',repo/'evaluation/semantic_pilot/user_review_v1/workflow.py');a=wf.assess(rec,repo/'evaluation/semantic_pilot')
    need([e['kind'] for e in rec['events']]==['user_initial','ai_counterreview','user_final'],'event order')
    need(rec['case_id']=='SP-009' and a['review_level']==row['review_level']=='user_final_confirmed','SP009 final state')
    need(a['final_judgment']==row['user_final_judgment']=='UNRESOLVED','SP009 abstention label')
    need(a['development_gold_eligible'] is True and row['development_gold_eligible'] is True,'eligible must be verified')
    need(a['independent_multi_human_complete'] is False and row['independent_multi_human_complete'] is False,'not independent multi-human gold')
    need(row['input_sha256']==before['SP-009']['input_sha256'] and row['review_method']==before['SP-009']['review_method'],'input/method changed')
    cp=ref(root,m['sp009_reconfirmation_path'],repo);need(sha(cp)==m['sp009_reconfirmation_sha256'],'confirmation hash')
    c=read(cp);need(c['case_id']=='SP-009' and c['actor_type']=='human' and c['reviewer_id']=='repository-user' and c['user_quote']=='응','actual user reply required')
    need(c['judgment']=='UNRESOLVED' and c['development_inclusion_approved'] is True and c['blinded_to_prior_judgments'] is False,'reconfirmation/inclusion required')
    need(c['question']=='이 새 검토 결과까지 확인하신 뒤, SP-009를 UNRESOLVED로 최종 확정하고 개발용 골드 포함을 승인하시나요?','reply context missing')
    need(c['counterreview_path']==row['source_counterreview_path'] and c['counterreview_sha256']==sha(source),'confirmation must bind fresh AI result')
    event=rec['events'][-1];p=event['payload'];need(event['recorded_at']==c['recorded_at'],'recording timestamp mismatch')
    need(p['approve_for_development_gold'] and p['human_confirmed'] and p['unresolved_issues'] and not row['blockers'],'human approval and abstention reason required')
    need(m['user_approved_count']==m['workflow_eligible_count']==12,'12 approved and eligible')
    need(len(m['active_case_ids'])==12 and set(m['active_case_ids'])==set(before),'active case registry')
    need(all(r['development_gold_eligible'] and not r['independent_multi_human_complete'] for r in rows),'active review levels')
    need(Counter(r['user_final_judgment'] for r in rows)==m['active_distribution']=={'PRESERVED':4,'VIOLATION':4,'UNRESOLVED':4},'active balance')
    return {'user_approved':12,'workflow_eligible':12,'distribution':m['active_distribution'],'preserved_files':178}


if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False,indent=2))

#!/usr/bin/env python3
"""Final review layer. Frozen preparation validators are intentionally unchanged."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PREFIX='evaluation/g3_g4/final_review_2026-11-11/'
APPROVED={f'SP-{n:03}':('PRESERVED' if n<=4 else 'VIOLATION' if n<=8 else 'UNRESOLVED') for n in range(1,13)}


def need(condition,message):
    if not condition:raise ValueError(message)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def repo_file(repo,name):
    path=(repo/name).resolve();need(path.is_relative_to(repo.resolve()) and path.is_file(),'invalid repository reference');return path


def final_file(root,name):
    need(name.startswith(PREFIX),'final snapshot outside new layer')
    path=(root/name[len(PREFIX):]).resolve();need(path.is_relative_to(root.resolve()) and path.is_file(),'invalid final file reference');return path


def validate(root=HERE,repo=REPO):
    manifest=read(root/'development-gold.json')
    need(manifest['dataset_role']=='development_only','not a holdout')
    ap=final_file(root,manifest['user_approval_path']);need(digest(ap)==manifest['user_approval_sha256'],'approval hash mismatch')
    approvals=read(ap)['cases'];need(len(approvals)==12 and {a['case_id'] for a in approvals}==set(APPROVED),'12 explicit approvals required')
    amap={a['case_id']:a for a in approvals}
    for cid,a in amap.items():
        need(a['actor_type']=='human' and a['reviewer_id']=='repository-user' and a['user_development_gold_approved'] is True,'explicit human inclusion approval required')
        need(a['judgment']==APPROVED[cid] and bool(a['rationale']),'approval differs from explicit user decision')
        need(a['blinded_to_prior_judgments'] is False,'no retrospective blinding')
        need(a['approval_date']=='2026-11-11' and bool(a['recorded_at']),'approval date/capture time missing')
    pp=final_file(root,manifest['preservation_path']);need(digest(pp)==manifest['preservation_sha256'],'preservation lock hash mismatch')
    lock=read(pp)
    need(lock['baseline_commit']=='4fd828dbef9db16303e37c0da6d67d7b1cff5b6c' and len(lock['files'])==153,'preservation scope changed')
    for name,expected in lock['files'].items():need(digest(repo_file(repo,name))==expected,'previous evaluation file changed: '+name)
    pilot=repo/'evaluation/semantic_pilot'
    spec=importlib.util.spec_from_file_location('g3_final_legacy_workflow',pilot/'user_review_v1/workflow.py');wf=importlib.util.module_from_spec(spec);spec.loader.exec_module(wf)
    rows=manifest['cases'];need(len(rows)==12 and {r['case_id'] for r in rows}==set(APPROVED),'final manifest case inventory')
    actual_active=[];active_labels=[]
    for row in rows:
        cid=row['case_id'];a=amap[cid]
        need(row['user_final_judgment']==a['judgment'] and row['user_development_gold_approved'] is True,'manifest/approval mismatch')
        need(approvals[int(row['approval_pointer'].split('/')[-1])]['case_id']==cid,'approval pointer mismatch')
        ip=pilot/f'inputs/{cid}.json';old=pilot/f'answers/{cid}.json'
        need(row['input_sha256']==a['input_sha256']==digest(ip),'input hash mismatch')
        need(a['ai_proposal_sha256']==digest(old),'AI source hash mismatch')
        wf.evidence_ok(a['evidence'],read(ip))
        sp=final_file(root,row['snapshot_path']);need(digest(sp)==row['snapshot_sha256'],'snapshot hash mismatch')
        record=read(sp);result=wf.assess(record,pilot)
        need(record['events'][-1]['recorded_at']==a['recorded_at'],'event/approval capture time mismatch')
        need(record['case_id']==cid and result['review_level']==row['review_level'],'snapshot case/level mismatch')
        need(row['review_method']==result['method']=='single_user_ai_counterreview','review method mismatch')
        need(result['development_gold_eligible']==row['development_gold_eligible'],'eligibility must be computed')
        need(result['independent_multi_human_complete'] is False and row['independent_multi_human_complete'] is False,'not independent multi-human gold')
        if cid=='SP-009':
            need(row['source_counterreview_path'] is None and row['source_counterreview_sha256'] is None,'SP009 old AI must not be retroactively bound')
            need([e['kind'] for e in record['events']]==['user_initial'],'SP009 requires a fresh cycle')
            need(record['events'][0]['payload']['form']['judgment']=='UNRESOLVED','SP009 current explicit decision must be retained')
            need(result['review_level']=='user_initial_reviewed' and not result['development_gold_eligible'],'SP009 blocked before fresh AI/user reconfirmation')
            need(set(row['blockers'])=={'FRESH_AI_COUNTERREVIEW_REQUIRED','USER_RECONFIRMATION_AFTER_COUNTERREVIEW_REQUIRED'},'SP009 exact blockers')
        else:
            source=repo_file(repo,row['source_counterreview_path']);need(digest(source)==row['source_counterreview_sha256'],'source counterreview hash mismatch')
            prior=read(source)
            need(record['events'][:-1]==prior['events'],'previous event prefix changed')
            need([e['kind'] for e in record['events']]==['user_initial','ai_counterreview','user_final'],'final event order')
            event=record['events'][-1];p=event['payload']
            need(p['judgment']==a['judgment'] and p['approve_for_development_gold'] is True and p['human_confirmed'] is True,'final user decision missing')
            need(p['rationale']=='사용자 최신 명시적 최종 승인 전사: '+a['rationale'] and p['evidence']==a['evidence'],'final reason/evidence mismatch')
            need(result['final_judgment']==a['judgment'] and result['development_gold_eligible'],'final workflow not eligible')
            need(not row['blockers'],'eligible case cannot have blocking steps')
            if cid=='SP-003':
                need(prior['events'][0]['payload']['form']['judgment']=='UNRESOLVED' and p['judgment']=='PRESERVED','SP003 judgment change history')
                need(p['responses'][0]['decision']=='accept' and a['non_blocking_followups'],'SP003 challenge response/followup required')
            if p['judgment']=='UNRESOLVED':need(bool(p['unresolved_issues']),'abstention reason must be retained')
            actual_active.append(cid);active_labels.append(a['judgment'])
    need(manifest['user_approved_count']==12 and manifest['workflow_eligible_count']==len(actual_active)==11,'approval/eligible counts')
    need(set(manifest['active_case_ids'])==set(actual_active) and len(manifest['active_case_ids'])==11,'active registry mismatch')
    need(Counter(a['judgment'] for a in approvals)==manifest['user_final_distribution']=={'PRESERVED':4,'VIOLATION':4,'UNRESOLVED':4},'user final distribution')
    need(Counter(active_labels)==manifest['active_distribution']=={'PRESERVED':4,'VIOLATION':4,'UNRESOLVED':3},'active distribution')
    six=amap['SP-006'];need(len(six['error_findings'])==2 and {f['error_type'] for f in six['error_findings']}=={'NEGATION_REVERSAL','QUANTITY_UNIT_CHANGE'},'SP006 two distinct errors required')
    for finding in six['error_findings']:wf.evidence_ok(finding['evidence'],read(pilot/'inputs/SP-006.json'))
    need({p.name for p in (root/'final').glob('*.json')}=={c+'.json' for c in actual_active},'orphan/missing final snapshot')
    need({p.name for p in (root/'pending').glob('*.json')}=={'SP-009.initial.json'},'pending snapshot inventory')
    fp=final_file(root,manifest['followup_path']);need(digest(fp)==manifest['followup_sha256'],'followup hash mismatch')
    follow=read(fp);need(digest(repo_file(repo,follow['source_path']))==follow['source_sha256'],'derivative source changed')
    need(follow['status']=='design_only_no_new_cases' and {x['suggested_id'] for x in follow['proposals']}=={f'SP-{n:03}' for n in range(13,18)},'derivative plan inventory')
    need(all(not x['formal_id_assigned'] and not x['input_created'] and not x['label_created'] for x in follow['proposals']),'derivatives must remain design only')
    return {'user_final_decisions':12,'active_development_gold':11,'blocked_cases':['SP-009'],'preserved_files':len(lock['files'])}


if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False,indent=2))

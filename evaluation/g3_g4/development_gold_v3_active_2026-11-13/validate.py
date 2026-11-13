"""Explicitly authorized activation layer; historical policies and v2 stay immutable."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKAGE='evaluation/g3_g4/development_gold_v3_active_2026-11-13'
CONSUMER_PACKAGE='evaluation/development_gold_active'
CONSUMERS=ROOT/CONSUMER_PACKAGE
INDEX=ROOT/'evaluation/active_development_gold.json'
BASE='9777dbd8321a0f7e7f89bd7116af2e0555c656e0'
V2='evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
CANDIDATE='evaluation/g3_g4/development_gold_v3_2026-11-13/development-gold.json'
LEGACY='evaluation/golden_expansion/legacy_migration_2026_11_13'
FINAL='evaluation/golden_expansion/user_final_2026_11_11'
IDS=[f'GC-{i:03}' for i in range(1,13)]+[f'SP-{i:03}' for i in range(13,18)]
BASELINE_SHA='4516de328a1f72a004a1492c7f93c6a4d003c654ccc71f7464682073f11f8a3d'
APPROVAL_SHA='bc128e8dbc44884d6d51acfbbe1cc70455d786ead3c0f49d8ac3a9b20501cd27'
STATEMENT='GC-001~012, SP-013~017 총 17건에 한해 `legacy-review-migration-v1` 정책 적용을 승인한다. 기존 사용자 판단 및 개발용 골드 포함 승인도 그대로 유지한다.'
ARTIFACTS={'activation/'+n for n in ('README.md','PLAN.md','VALIDATION.md','policy-approval.json',
    'activation-history.json','development-gold.json','preserved-files.json','validate.py')}
ARTIFACTS|={'consumers/'+n for n in ('README.md','runtime.py','source_candidate.py','core_diagnostics.py','test_active.py')}
ARTIFACTS.add('index')


def load(path):return json.loads(path.read_text())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,msg):
    if not ok:raise ValueError(msg)
def module(name,path):
    spec=importlib.util.spec_from_file_location('activation_'+name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def artifact(name,here=HERE,consumers=CONSUMERS,index=INDEX):
    if name=='index':return index
    prefix,relative=name.split('/',1)
    need(prefix in {'activation','consumers'},'artifact prefix')
    base=here if prefix=='activation' else consumers
    path=(base/relative).resolve();need(path.is_relative_to(base.resolve()),'unsafe artifact');return path


def ref(root,path,pointer='',here=HERE,consumers=CONSUMERS,index=INDEX):
    if path.startswith(PACKAGE+'/'):p=here/path[len(PACKAGE)+1:]
    elif path.startswith(CONSUMER_PACKAGE+'/'):p=consumers/path[len(CONSUMER_PACKAGE)+1:]
    elif path=='evaluation/active_development_gold.json':p=index
    else:p=root/path
    return {'path':path,'sha256':sha(p.read_bytes()),'pointer':pointer}


def history(root):
    migration=module('legacy',root/LEGACY/'validate_migration.py')
    summary=migration.validate()
    need(summary['legacy_evidence_validated']==17,'legacy evidence incomplete')
    return migration,load(root/LEGACY/'legacy-records.json')


def build_approval(root=ROOT):
    migration,records=history(root)
    final=module('canonical',root/FINAL/'validate_submission.py')
    events=[];previous=None
    for i,row in enumerate(records['cases']):
        event={'event_id':'legacy-policy-apply-'+row['case_id'],'kind':'user_legacy_policy_application_approved',
            'case_id':row['case_id'],'input_sha256':row['input']['sha256'],'approved':True,
            'policy_id':'legacy-review-migration-v1','policy':ref(root,LEGACY+'/policy.json'),
            'review_bundle':ref(root,LEGACY+'/legacy-records.json',f'/cases/{i}'),
            'final_reference':row['final_human']['source'],'final_event_sha256':row['final_human']['event_sha256'],
            'inclusion_reference':row['inclusion']['source'],'inclusion_event_sha256':row['inclusion']['event_sha256'],
            'source_pointer':'/statement','source_statement_sha256':sha(STATEMENT.encode()),
            'actor_type':'human','recorder_type':'ai','user_approved_at':None,
            'previous_event_sha256':previous}
        previous=final.event_digest(event);events.append(event)
    return {'schema_version':'legacy-policy-application-approval-v1','source_kind':'current_user_message_transcription',
        'statement':STATEMENT,'activation_instruction_quote':'검증을 통과한 신규 17건에 적격성 부여',
        'policy_id':'legacy-review-migration-v1','policy':ref(root,LEGACY+'/policy.json'),
        'case_ids':IDS,'approved':True,'actor_type':'human','recorder_type':'ai',
        'user_approved_at':None,'signature':None,'authenticated_identity':None,'externally_authenticated':False,
        'historical_events_rewritten':False,'case_approvals':events,'terminal_event_sha256':previous}


def build_active(root=ROOT,here=HERE,consumers=CONSUMERS,index=INDEX):
    approval=load(here/'policy-approval.json')
    need(sha((here/'policy-approval.json').read_bytes())==APPROVAL_SHA,'explicit policy approval changed')
    need(approval==build_approval(root),'approval scope or source mismatch')
    candidate=load(root/CANDIDATE)
    final=module('active_canonical',root/FINAL/'validate_submission.py')
    rows=[dict(r) for r in candidate['cases'][:12]]
    for i,row in enumerate(candidate['cases'][12:]):
        event=approval['case_approvals'][i]
        need(row['case_id']==event['case_id'] and row['input_sha256']==event['input_sha256'],'approval case/input mismatch')
        rows.append(dict(row,development_gold_eligible=True,blockers=[],
            policy_approval=ref(root,PACKAGE+'/policy-approval.json',f'/case_approvals/{i}',here,consumers,index),
            policy_approval_event_sha256=final.event_digest(event)))
    return {'schema_version':'3.0.0','dataset_id':'single-user-development-gold-v3-20261113-active',
        'dataset_role':'development_only','active':True,'case_count':29,
        'active_case_ids':candidate['case_ids'],'cases':rows,'active_distribution':candidate['distribution'],
        'previous_dataset':ref(root,V2),'candidate_dataset':ref(root,CANDIDATE),
        'migration_policy':ref(root,LEGACY+'/policy.json'),
        'policy_approval':ref(root,PACKAGE+'/policy-approval.json','',here,consumers,index),
        'independent_holdout':False,'independent_multi_human_complete':False,
        'source_family_independence_claimed':False}


def build_history(root=ROOT,here=HERE,consumers=CONSUMERS,index=INDEX):
    return {'schema_version':'development-gold-activation-history-v1',
        'kind':'development_gold_activation_recorded','actor_type':'ai','source':'explicit_user_request_after_validation',
        'user_event_time':None,'previous_dataset':ref(root,V2),
        'active_dataset':ref(root,PACKAGE+'/development-gold.json','',here,consumers,index),
        'policy_approval':ref(root,PACKAGE+'/policy-approval.json','',here,consumers,index),
        'preserved_existing_count':12,'newly_eligible_case_ids':IDS,'newly_activated_count':17,
        'active_count':29,'distribution':{'PRESERVED':12,'VIOLATION':9,'UNRESOLVED':8},
        'model_results_reaggregated':False,'original_judgments_modified':False,'v2_overwritten':False}


def build_index(root=ROOT,here=HERE,consumers=CONSUMERS,index=INDEX):
    return {'schema_version':'active-development-gold-index-v1','dataset_role':'development_only',
        'active_dataset':ref(root,PACKAGE+'/development-gold.json','',here,consumers,index),
        'activation_history':ref(root,PACKAGE+'/activation-history.json','',here,consumers,index),
        'active_count':29,'active_distribution':{'PRESERVED':12,'VIOLATION':9,'UNRESOLVED':8},
        'consumers':{name:ref(root,CONSUMER_PACKAGE+'/'+file,'',here,consumers,index) for name,file in
            [('semantic_evaluation','source_candidate.py'),('core_diagnostics','core_diagnostics.py')]},
        'historical_v2_consumers':{'semantic_evaluation':'evaluation/source_candidate_semantics/run.py',
                                 'core_diagnostics':'evaluation/core_pipeline_2026_11_11/evaluate.py'}}


def validate(root=ROOT,here=HERE,consumers=CONSUMERS,index=INDEX):
    manifest=load(here/'artifact-manifest.json');need(set(manifest)==ARTIFACTS,'activation artifact inventory changed')
    for name,digest in manifest.items():
        need(sha(artifact(name,here,consumers,index).read_bytes())==digest,'activation artifact changed: '+name)
    need(sha((here/'preserved-files.json').read_bytes())==BASELINE_SHA,'preservation baseline changed')
    baseline=load(here/'preserved-files.json')
    for name,digest in baseline.items():need(sha((root/name).read_bytes())==digest,'existing file changed: '+name)
    expected=build_active(root,here,consumers,index);active=load(here/'development-gold.json')
    need(active==expected,'active dataset/answers/eligibility mismatch')
    need(load(here/'activation-history.json')==build_history(root,here,consumers,index),'activation history mismatch')
    need(load(index)==build_index(root,here,consumers,index),'active reference/consumer mismatch')
    need(len(active['cases'])==len(set(active['active_case_ids']))==29,'active inventory')
    from collections import Counter
    need(Counter(r['user_final_judgment'] for r in active['cases'])==active['active_distribution'], 'answer distribution')
    return {'policy':'legacy-review-migration-v1','policy_approved_cases':17,'newly_eligible':17,
        'active_count':29,'distribution':active['active_distribution'],'existing_files_preserved':len(baseline),
        'consumer_reference':PACKAGE+'/development-gold.json','v2_preserved':True}


if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))

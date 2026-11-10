#!/usr/bin/env python3
"""Validate G3 preparation and G4 development candidates, never confirm human labels."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PILOT=HERE.parent/'semantic_pilot'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def local(root,name):
    p=(root/name).resolve()
    require(p.is_relative_to(root.resolve()) and p.is_file(),'invalid local file reference')
    return p


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def validate_assignments(assignments):
    seen={}
    for item in assignments:
        key=item['family'].casefold()
        require(item['split'] in {'development','holdout'},'invalid split')
        require(key not in seen or seen[key]==item['split'],'repository family crosses splits')
        seen[key]=item['split']


def validate_g3(root=HERE,pilot=PILOT):
    lock=load(pilot/'independent_review/preserved-files.json')
    for name,expected in lock['files'].items():require(sha((pilot/name).read_bytes())==expected,'original pilot changed')
    progress=load(root/'g3-progress.json');rows=progress['cases']
    require(progress['status']=='preparation_only' and len(rows)==12,'G3 is preparation only')
    require({r['case_id'] for r in rows}=={f'SP-{i:03}' for i in range(1,13)},'G3 case inventory')
    require(progress['priority_order']==['SP-003','SP-011','SP-009','SP-010','SP-012'],'G3 priority inventory')
    require({str(p.relative_to(root)) for p in (root/'prepared').glob('*.json')}=={r['prepared_workflow_path'] for r in rows},'G3 prepared inventory')
    wf=module('g3_frozen_workflow',pilot/'user_review_v1/workflow.py')
    for row in rows:
        cid=row['case_id'];ap=pilot/f'answers/{cid}.json';ip=pilot/f'inputs/{cid}.json';a=load(ap)
        require(row['input_path']==f'../semantic_pilot/inputs/{cid}.json' and row['answer_path']==f'../semantic_pilot/answers/{cid}.json','G3 source reference')
        require(row['input_sha256']==sha(ip.read_bytes())==a['input_sha256'],'G3 input binding')
        require(row['answer_sha256']==sha(ap.read_bytes()),'G3 answer binding')
        require(row['existing_ai_judgment']==a['expected_judgment'],'G3 AI label changed')
        require(row['existing_user_judgment']==a['reviews'][0]['judgment'] and row['existing_user_review_pointer']=='/reviews/0','G3 user label changed')
        require(row['historical_review_status']=='guided_user_review_completed','historical review status changed')
        require(row['existing_user_blinded'] is False and a['reviews'][0]['blinded_to_ai_proposal'] is False,'no retrospective blinding')
        p=local(root,row['prepared_workflow_path']);require(sha(p.read_bytes())==row['prepared_workflow_sha256'],'prepared record hash')
        record=load(p);result=wf.assess(record,pilot)
        require(record['case_id']==cid and record['events']==[],'no new G3 review events')
        require(result['review_level']==row['new_workflow_level']=='ai_provisional','no status-only promotion')
        require(result['development_gold_eligible'] is False and row['development_gold_eligible'] is False,'no user final approval')
        require(row['ai_counterreview_status']=='not_run' and row['user_final_status']=='not_confirmed','no fabricated completed reviews')
        require(row['priority']==(cid in progress['priority_order']) and bool(row['questions']),'G3 priority/questions')
    require(Counter(r['existing_ai_judgment'] for r in rows)=={'PRESERVED':4,'VIOLATION':4,'UNRESOLVED':4},'AI balance changed')
    require(Counter(r['existing_user_judgment'] for r in rows)=={'PRESERVED':3,'VIOLATION':4,'UNRESOLVED':5},'user balance changed')
    return len(rows)


def validate_g4(root=HERE,pilot=PILOT):
    manifest=load(root/'manifest.json');rows=manifest['cases'];sources=load(root/'sources.json');plan=load(root/'split-plan.json')
    require(manifest['status']=='provisional_not_gold' and manifest['split']=='development_only','no G4 gold/holdout promotion')
    require(sha(local(root,manifest['source_registry_path']).read_bytes())==manifest['source_registry_sha256'],'source registry hash')
    require(len(rows)==12 and {r['case_id'] for r in rows}=={f'GC-{n:03}' for n in range(1,13)},'G4 case inventory')
    require(Counter(r['expected_judgment'] for r in rows)=={'PRESERVED':4,'VIOLATION':4,'UNRESOLVED':4},'G4 balance')
    require(plan['holdout_collection_status']=='planned_not_collected' and not plan['holdout_sources'] and plan['holdout_content_or_labels_in_this_repository'] is False,'holdout not collected here')
    legacy_repos=set(load(pilot.parent.parent/'tests/fixtures/real-world-candidates.json')['summary']['source_repositories'])|{'nanocode00/LogicWrite'}
    legacy_keys={name.casefold() for name in legacy_repos}
    registry={s['source_id']:s for s in sources};require(len(registry)==len(sources)==4,'four source families required')
    for s in sources:
        require(s['repository'].casefold() not in legacy_keys and s['family'].casefold() not in legacy_keys,'old development repository reused')
        require(s['is_fork'] is False and s['family']==s['upstream_repository']==s['repository'],'upstream family mismatch')
        require(len(s['commit'])==40 and all(c in '0123456789abcdef' for c in s['commit']),'commit not pinned')
        require(s['spdx'] in {'Apache-2.0','BSD-3-Clause'} and s['license'] is not None,'license not captured')
        for key in ['document','license','notice']:
            ref=s.get(key)
            if ref is None:continue
            raw=local(root,ref['local_path']).read_bytes()
            require(sha(raw)==ref['sha256'],'source/license/notice SHA mismatch')
            require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==ref['git_blob_sha'],'Git blob mismatch')
            require(ref['url']==f"https://github.com/{s['repository']}/blob/{s['commit']}/{ref['path']}",'source URL/ref mismatch')
    require(set(plan['known_development_families'])==legacy_repos|{s['family'] for s in sources},'development family exclusion list incomplete')
    validate_assignments([{'family':f,'split':'development'} for f in plan['known_development_families']]+plan['holdout_sources'])
    old=module('g4_reused_pair_validator',pilot/'validate.py')
    readable=module('g4_readable_renderer',pilot/'independent_review/export.py')
    for side in ['input','answer']:
        require({str(p.relative_to(root)) for p in (root/(side+'s')).glob('*.json')}=={r[side+'_path'] for r in rows},'orphan/missing candidate file')
    for row in rows:
        s=registry[row['source_id']];require(row['split']=='development' and row['repository_family']==s['family'],'candidate split/family mismatch')
        ip=local(root,row['input_path']);ap=local(root,row['answer_path']);inp=load(ip);a=load(ap)
        require(sha(ip.read_bytes())==row['input_sha256'] and sha(ap.read_bytes())==row['answer_sha256'],'candidate manifest hash')
        require(row['case_id']==inp['case_id']==a['case_id'] and row['expected_judgment']==a['expected_judgment'],'candidate ID/label mismatch')
        require(a['status']=='provisional' and a['gold_eligible'] is False and a['reviews']==[] and a['adjudication'] is None,'no G4 human/gold records')
        prov=inp['source_documents'][0]['provenance']
        require(prov['repository']==s['repository'] and prov['version']==s['commit'] and prov['snapshot_sha256']==s['document']['sha256'],'input provenance differs from registry')
        old.validate_pair(inp,a,root)
        rendered=local(root,row['readable_input_path']).read_bytes()
        require(sha(rendered)==row['readable_input_sha256'] and rendered==readable.render_input(inp),'readable view differs from input')
    return len(rows)


def validate_all(root=HERE,pilot=PILOT):return {'g3_prepared':validate_g3(root,pilot),'g4_provisional_development':validate_g4(root,pilot)}


if __name__=='__main__':
    print(json.dumps(validate_all(),indent=2))
    print('No new human judgments, final gold or holdout data confirmed.')

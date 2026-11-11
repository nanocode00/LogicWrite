#!/usr/bin/env python3
"""Check provisional records, immutable history, source bytes, evidence, and review isolation."""
import importlib.util
import json
from pathlib import Path
from jsonschema import Draft202012Validator
import review
import export
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent

def validate():
    lock=review.load(HERE/'preserved-files.json')
    for name,h in lock['files'].items():review.require(review.sha((ROOT/name).read_bytes())==h,'existing evaluation changed: '+name)
    registry=review.load(HERE/'registry.json');rows=registry['cases'];ids={r['case_id'] for r in rows}
    review.require(len(rows)==17 and ids=={f'GC-{n:03}' for n in range(1,13)}|{f'SP-{n:03}' for n in range(13,18)},'inventory mismatch')
    spec=importlib.util.spec_from_file_location('pair_validator',HERE.parent/'semantic_pilot/validate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    for row in rows:
        ip=review.resolve(row['input_path']);ap=review.resolve(row['answer_path']);inp=review.load(ip);a=review.load(ap)
        review.require(review.sha(ip.read_bytes())==row['input_sha256'] and review.sha(ap.read_bytes())==row['answer_sha256'],'registry binding')
        review.require(row['status']=='provisional' and row['development_gold_eligible'] is False and row['user_final_judgment'] is None,'registry promotion forbidden')
        review.require(a['status']=='provisional' and a['gold_eligible'] is False and a['reviews']==[] and a['adjudication'] is None,'AI cannot supply human judgment')
        v.validate_pair(inp,a,HERE if row['case_id'].startswith('SP') else HERE.parent/'g3_g4')
        review.require(review.assess(review.new_record(row['case_id']))['development_gold_eligible'] is False,'blank review promoted')
        prepared=review.load(HERE/'prepared'/f'{row["case_id"]}.workflow.json')
        review.require(prepared['events']==[] and not review.assess(prepared)['development_gold_eligible'],'prepared review must stay empty')
        for parent in row.get('parent_inputs',[]):review.require(review.sha((ROOT/parent['path']).read_bytes())==parent['sha256'],'parent binding')
    audit=review.load(HERE/'public-source-recheck.json')
    review.require(len(audit)==10 and all(r['matches_pinned_local'] for r in audit),'public retrieval failed')
    expected_sources={}
    for source in review.load(HERE.parent/'g3_g4/sources.json'):
        for kind in ['document','license','notice']:
            ref=source.get(kind)
            if ref:
                url=f'https://raw.githubusercontent.com/{source["repository"]}/{source["commit"]}/{ref["path"]}'
                expected_sources[url]=ref['sha256']
    review.require({r['url']:r['sha256'] for r in audit}==expected_sources,'remote check differs from pinned registry')
    advisory_ids=set()
    for name in ['gc-independent-ai-review.json','sp-independent-ai-review.json']:
        advisory=review.load(HERE/name)
        for case in advisory['results']:
            review.require(case['case_id'] not in advisory_ids,'duplicate AI advisory')
            advisory_ids.add(case['case_id'])
            review.require(case['input_sha256']==review.row(case['case_id'])['input_sha256'],'stale AI advisory')
            inp=review.load(review.resolve(review.row(case['case_id'])['input_path']))
            # Review formats share evidence records but advisory layout is independently authored.
            for ev in case.get('evidence',[]):
                if isinstance(ev,dict) and {'side','document_id','start','end','quote'}<=ev.keys():review.legacy.evidence_ok([ev],inp)
    review.require(advisory_ids==ids,'independent AI advisory inventory')
    files=export.payload()
    review.require(len([n for n in files if n.startswith('forms/')])==17,'blank form inventory')
    for name,raw in files.items():
        review.require(not any(s in name for s in ['answers/','workflow','counterreview']),'answer leaked in export')
        if name.startswith(('cases/','forms/')):
            review.require((HERE/name).read_bytes()==raw,'stale readable input or blank form')
        if name.startswith('forms/'):
            f=json.loads(raw);review.require(f['judgment'] is None and f['form_status']=='blank','nonblank review form')
    return dict(candidates=17,gc=12,sp_derivatives=5,user_judgment_pending=17,new_gold=0,preserved_existing_files=len(lock['files']),input_only_files=len(files))

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))

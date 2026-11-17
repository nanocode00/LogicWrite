#!/usr/bin/env python3
"""Read-only mechanical summaries; no semantic verdict, model calls or gold edits."""
import argparse
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import comparison_v2 as v


def summarize(root,prior_smoke_root=None,release=None):
    rows=[]
    for target in v.TARGETS:
        cid,arm=target.split('/')
        source_root=prior_smoke_root if target=='IR-003/B0' and prior_smoke_root else root
        folder=source_root/('smoke' if target=='IR-003/B0' else 'remaining')/cid/arm
        rec=folder/'execution.json'
        if not rec.exists():
            rows.append({'target':target,'state':'not_run','D':'unobserved'});continue
        record=json.loads(rec.read_text())
        row={'target':target,'state':record['state'],'D':'unobserved',
             'calls':record['calls'],'usage':record.get('usage'),'seconds':record.get('seconds'),
             'http_status':record.get('http_status'),'finish_reasons':record.get('finish_reasons'),
             'reason':record.get('reason'),'candidate_checks':[],
             'human_final_judgment':None}
        row['execution_source']=str(folder)
        if target=='IR-003/B0' and release is not None:
            row['settlement_release']=str(release)
            row['original_execution_state']=row['state']
            row['effective_execution_state']='response_complete_after_audited_settlement'
        inp=v.base.export_input(v.base.GOLD,cid)
        source={d['document_id']:d for d in inp['documents']}
        path=folder/'candidate.json'
        if not path.exists() and (folder/'diagnostic-candidate.json').exists():
            path=folder/'diagnostic-candidate.json'
            row['candidate_is_diagnostic_after_protocol_failure']=True
        if path.exists():
            data=json.loads(path.read_text())
            row['candidate_sha256']=v.base.digest(path.read_bytes())
            for doc in data['documents']:
                old=source[doc['document_id']];text=doc['content']
                normalize=lambda value:'\n'.join(re.sub(r'^[-*] ','',line).strip() for line in value.splitlines() if line.strip())
                row['candidate_checks'].append({'document_id':doc['document_id'],'access':old['access'],
                    'byte_identical':text==old['content'],'normalized_list_marker_equal':normalize(text)==normalize(old['content']),
                    'characters':len(text),'source_characters':len(old['content']),
                    'links':re.findall(r'\]\(([^)]+)\)',text),
                    'source_code_blocks_preserved_literal':[block in text for block in re.findall(r'```.*?```',old['content'],re.S)]})
            row['assessment_boundary']='mechanical diagnostics only; no Q/F/HITL semantic verdict'
        rows.append(row)
    return {'protocol':v.PROTOCOL,'rows':rows,'human_final_judgment':None}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    parser.add_argument('--prior-smoke-root',type=Path)
    parser.add_argument('--settlement-release',type=Path)
    args=parser.parse_args();print(json.dumps(summarize(args.root,args.prior_smoke_root,args.settlement_release),ensure_ascii=False,indent=2))

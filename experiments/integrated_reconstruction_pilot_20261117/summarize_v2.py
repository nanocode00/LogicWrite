#!/usr/bin/env python3
"""Read-only mechanical summaries; no semantic verdict, model calls or gold edits."""
import argparse
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import comparison_v2 as v


def summarize(root):
    rows=[]
    for target in v.TARGETS:
        cid,arm=target.split('/')
        folder=root/('smoke' if target=='IR-003/B0' else 'remaining')/cid/arm
        rec=folder/'execution.json'
        if not rec.exists():
            rows.append({'target':target,'state':'not_run','D':'unobserved'});continue
        record=json.loads(rec.read_text())
        row={'target':target,'state':record['state'],'D':'unobserved',
             'calls':record['calls'],'usage':record.get('usage'),'seconds':record.get('seconds'),
             'http_status':record.get('http_status'),'finish_reasons':record.get('finish_reasons'),
             'reason':record.get('reason'),'candidate_checks':[],
             'human_final_judgment':None}
        inp=v.base.export_input(v.base.GOLD,cid)
        source={d['document_id']:d for d in inp['documents']}
        path=folder/'candidate.json'
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
    args=parser.parse_args();print(json.dumps(summarize(args.root),ensure_ascii=False,indent=2))

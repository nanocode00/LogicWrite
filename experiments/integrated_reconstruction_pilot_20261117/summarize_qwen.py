#!/usr/bin/env python3
"""Offline Qwen diagnostics only; never sends model requests or assigns semantic grades."""
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import comparison_qwen as q


def summarize(root):
    manifest=json.loads((q.base.GOLD/'development_gold/manifest.json').read_text())
    cases={x['case_id']:x for x in manifest['cases']}
    rows=[]
    for target in q.TARGETS:
        folder=root/({'Probe-A':'probe-a','Probe-B':'probe-b'}.get(target,'evaluation/'+target))
        row={'target':target,'state':'not_run','human_final_judgment':None}
        if (folder/'execution.json').exists():
            rec=json.loads((folder/'execution.json').read_text())
            for field in ('state','reason','calls','usage','seconds','http_status','model_returned','provider_returned','finish_reasons','reasoning_tokens'):
                if field in rec:row[field]=rec[field]
            row['evidence_path']=str(folder.relative_to(root))
            row['response_sha256']=q.base.digest((folder/'response.json').read_bytes()) if (folder/'response.json').exists() else None
        if target.startswith('IR-'):
            cid,arm=target.split('/');entry=cases[cid]
            inp=q.base.export_input(q.base.GOLD,cid)
            row['input_sha256']=q.base.digest((q.base.GOLD/entry['input_path']).read_bytes())
            row['criteria_path']=entry['criteria_path'];row['criteria_sha256']=q.base.digest((q.base.GOLD/entry['criteria_path']).read_bytes())
            row['D']='unobserved'
            if (folder/'candidate.json').exists():
                data=json.loads((folder/'candidate.json').read_text())
                source={x['document_id']:x for x in inp['documents']}
                row['documents']=[]
                for d in data['documents']:
                    old=source[d['document_id']];text=d['content']
                    # Diagnostics identify text changes, not whether their meaning is authorized.
                    row['documents'].append({'document_id':d['document_id'],'access':old['access'],
                        'exact_unchanged':text==old['content'],'characters':len(text),'source_characters':len(old['content']),
                        'source_codeblocks_preserved':[block in text for block in re.findall(r'```.*?```',old['content'],re.S)],
                        'links':re.findall(r'\]\(([^)]+)\)',text)})
                row['candidate_sha256']=q.base.digest((folder/'candidate.json').read_bytes())
        rows.append(row)
    pairs=[]
    for cid in cases:
        paths=[root/'evaluation'/cid/arm/'request.json' for arm in ('B0','B1')]
        if all(p.exists() for p in paths):
            a,b=[json.loads(p.read_text()) for p in paths]
            pairs.append({'case_id':cid,'identical_user_input':a['messages'][1]==b['messages'][1],
                          'identical_generation_settings':{k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'},
                          'B1_only_addition_is_generic_improved_prompt':b['messages'][0]['content']==q.base.BASE+'\n'+q.base.IMPROVED+q.v.DELIVERY,
                          'B0_common_prompt_verified':a['messages'][0]['content']==q.base.BASE+q.v.DELIVERY,
                          'input_only_user_message':json.loads(a['messages'][1]['content'])==q.base.export_input(q.base.GOLD,cid)})
    return {'protocol':q.PROTOCOL,'kind':'automatic_diagnostics_not_semantic_judgment','rows':rows,'pairs':pairs,
            'human_final_judgment':None,'reference_similarity_scoring':False}

if __name__=='__main__':print(json.dumps(summarize(Path(sys.argv[1])),ensure_ascii=False,indent=2))

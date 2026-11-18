"""Input-only G2-A/B artifact reproduction. No model/evaluation/runner imports.

Writes new result files only; supplied snapshot paths are never opened. IR source
files are read solely by this development adapter, never by generic Core modules.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/full_document_control'))
import document_set as core
import document_set_analysis as analysis
import document_set_planning as planning
from ir_document_set_adapter import from_ir_input


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_results():
    results={};summary=[]
    for n in (1,2,3):
        name=f'IR-{n:03}'
        contract=from_ir_input(_read(ROOT/'evaluation/integrated_reconstruction/inputs'/f'{name}.json'))
        request=planning.make_request([])
        results[name]=_pair(contract,request)
    here=Path(__file__).resolve().parent
    results['synthetic']=_pair(_read(here/'g2_ab_synthetic_input.json'),_read(here/'g2_ab_synthetic_request.json'))
    for name,pair in results.items():
        a,p=pair['analysis'],pair['plan']
        summary.append(dict(input_id=name,documents=len(a['documents']),units=len(a['units']),
            coverage_status=a['coverage_status'],relations=dict(Counter(r['kind'] for r in a['relations'])),
            task_statuses=dict(Counter(t['status'] for t in p['tasks'])),hitl_questions=len(p['hitl_questions']),
            confirmed_semantic_conflicts=len(a['confirmed_semantic_conflicts']),semantic_analysis_complete=False,
            organization_complete=p['organization_complete'],execution_state=p['execution_state'],
            contract_sha256=a['contract_sha256'],analysis_sha256=a['analysis_sha256'],plan_sha256=p['plan_sha256']))
    return results,summary


def _pair(contract,request):
    pin=core.contract_digest(contract);request_pin=core.contract_digest(request)
    a=analysis.analyze_document_set(contract,trusted_contract_sha256=pin)
    p=planning.plan_document_set(contract,a,request,trusted_contract_sha256=pin,trusted_request_sha256=request_pin)
    if a['gate_state']=='FAIL' or p['gate_state']=='FAIL': raise ValueError('Offline artifact rejected')
    return dict(analysis=a,plan=p)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory only')
    args=parser.parse_args()
    if args.output.exists(): parser.error('Output directory already exists; preserve previous evidence')
    results,summary=build_results()
    args.output.mkdir(parents=True)
    for name,pair in results.items():
        for kind,artifact in pair.items():
            (args.output/f'{name}-{kind}.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()

"""Read-only G0 legacy probes and G1 IR mapping / validator_shadow evidence.

Never a B2 generator or model runner. Only strict IR input and frozen candidate
files are opened; answer, criteria, reference and human-review files are excluded.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / 'experiments/full_document_control'
if str(CORE) not in sys.path:
    sys.path.insert(0,str(CORE))
import document_set
import final_semantic_validator
import integration
import ir_document_set_adapter
import pipeline

PILOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'evaluation/integrated_reconstruction/inputs'
QWEN = PILOT / 'qwen-comparison-20261117/evaluation'


def _read(path):
    raw=path.read_bytes()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def build_evidence():
    """Return reproducible offline evidence; no model callback or disk writes."""
    contracts={};mappings=[];shadow=[];legacy=[];hashes={}
    for path in sorted(INPUTS.glob('*.json')):
        raw,sha=_read(path);hashes[str(path.relative_to(ROOT))]=sha
        contract=ir_document_set_adapter.from_ir_input(raw)
        pin=document_set.contract_digest(contract)
        admission=document_set.validate_contract(contract,expected_sha256=pin)
        contracts[raw['case_id']]=contract
        mappings.append({'case_id':raw['case_id'],'input_file_sha256':sha,
            'contract_sha256':pin,'admission':admission,'documents':[
                {k:d[k] for k in ('document_id','role','authority','access','completeness','output_target','sha256')}
                for d in contract['documents']], 'pending_questions':contract['pending_questions'],
            'reconstruction':document_set.prepare_reconstruction(contract,trusted_contract_sha256=pin)})
        # Characterize the old input gate; never relax or repeatedly invoke it
        # as a substitute for document-set analysis/reconstruction.
        editable=next(d for d in raw['documents'] if d['access'] in {'edit','format_only'})
        wc={'contract_id':'g0-legacy-probe','version':'1','document_type':'markdown',
            'audience':'probe only','purpose':'characterize admission only','language':'ko','register':'한다체',
            'output_scopes':[{'scope_id':'probe','document_id':editable['document_id']}],
            'required_information':[],'constraints':[]}
        bundle=integration.markdown_bundle(editable['content'],wc)
        pipeline.validate_input_bundle(bundle)
        one={'single_scope_admitted':True}
        multiple=copy.deepcopy(bundle)
        multiple['writing_contract']['output_scopes'].append({'scope_id':'another','document_id':'another'})
        try:
            pipeline.validate_input_bundle(multiple)
            one.update(multiple_scope_admitted=True)
        except ValueError as exc:
            one.update(multiple_scope_admitted=False,block_reason=str(exc))
        stopped=integration.run_pipeline(multiple)
        one.update(case_id=raw['case_id'],integrated_status=stopped['status'],
            candidate_generated=stopped['revision_result'] is not None,
            stage_transition_allowed=stopped['stage_transition_allowed'])
        legacy.append(one)
        for candidate_path in sorted((QWEN / raw['case_id']).glob('*/candidate.json')):
            candidate,csha=_read(candidate_path);hashes[str(candidate_path.relative_to(ROOT))]=csha
            by_id={d['document_id']:d for d in raw['documents']}
            rows=[{'document_id':d['document_id'],'source_sha256':by_id[d['document_id']]['sha256'],
                   'source_path':by_id[d['document_id']]['path'],'content':d['content'],
                   'sha256':hashlib.sha256(d['content'].encode()).hexdigest()} for d in candidate['documents']]
            permission=document_set.validate_candidates(contract,rows,trusted_contract_sha256=pin)
            snapshots=[]; outputs=[]
            candidate_by_id={d['document_id']:d for d in candidate['documents']}
            for d in raw['documents']:
                snapshot={'document_id':d['document_id'],'snapshot_id':'source:'+d['document_id']+':'+d['sha256'],
                    'version':'supplied-v1','coverage':'complete','content':d['content'],'sha256':d['sha256']}
                snapshots.append(snapshot)
                # Read-only references retained in the review context are copies
                # of input evidence, explicitly not Qwen-generated output claims.
                text=candidate_by_id.get(d['document_id'],d)['content']
                output_sha=hashlib.sha256(text.encode()).hexdigest()
                outputs.append(dict(snapshot,snapshot_id='external-pair:'+d['document_id']+':'+output_sha,
                    version='external-pair-v1',content=text,sha256=output_sha))
            evaluation_contract={'contract_id':'g0-shadow:'+raw['case_id'],'version':'1',
                'audience':'Unresolved; see supplied context','purpose':raw['request'],
                'output_document_ids':[d['document_id'] for d in raw['documents']],
                'required_information':[],'constraints':raw['explicit_constraints']}
            report=final_semantic_validator.evaluate_snapshot_pair(snapshots,outputs,evaluation_contract,
                context={'request':raw['request'],'context':raw['context'],
                         'document_metadata':[{k:d[k] for k in ('document_id','role','authority','access')}
                                              for d in raw['documents']]})
            shadow.append({'mode':'validator_shadow','case_id':raw['case_id'],
                'baseline':candidate_path.parent.name,'candidate_path':str(candidate_path.relative_to(ROOT)),
                'candidate_file_sha256':csha,'pair_composition':'Qwen writable candidates plus unchanged input read_only references',
                'b2_generated':False,'model_calls':0,'permission_report':permission,
                'legacy_external_semantic_report':report,
                'diffs':[{'document_id':row['document_id'],
                    'unchanged':row['content']==by_id[row['document_id']]['content'],
                    'source_chars':len(by_id[row['document_id']]['content']),
                    'candidate_chars':len(row['content'])} for row in rows]})
    return {'version':'b2-g0-g1-offline-v1','mode':'offline_admission_and_validator_shadow',
        'model_calls':0,'b2_reconstruction_success':False,'semantic_judgment':'unresolved',
        'delivery_approved':False,'source_hashes':hashes,'legacy_probes':legacy,
        'ir_mappings':mappings,'validator_shadow':shadow},contracts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True,help='New directory only')
    args=parser.parse_args()
    if args.output_dir.exists(): parser.error('Output directory already exists; preserve existing evidence')
    report,contracts=build_evidence()
    args.output_dir.mkdir(parents=True)
    def save(name,value):
        (args.output_dir/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    save('offline-evidence.json',report)
    for case_id,contract in contracts.items():save(case_id+'.contract.json',contract)
    print(json.dumps({'mode':report['mode'],'legacy_probes':len(report['legacy_probes']),
        'ir_mappings':len(contracts),'validator_shadow':len(report['validator_shadow']),
        'model_calls':0,'b2_reconstruction_success':False}))


if __name__=='__main__':main()

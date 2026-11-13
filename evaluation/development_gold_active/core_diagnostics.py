"""Active v3 input-only Core diagnostics; never masquerades as SP accuracy."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime

legacy=runtime.module('core_v2_engine',runtime.ROOT/'evaluation/core_pipeline_2026_11_11/evaluate.py')
predict=legacy.predict
native_probes=legacy.native_probes


def run_predictions():
    rows=[]
    for cid in runtime.CASE_IDS:
        path=runtime.input_path(cid)
        row=predict(legacy.read(path))
        row.update(input_path=str(path.relative_to(runtime.ROOT)),input_sha256=legacy.file_sha(path))
        rows.append(row)
    return {'schema_version':'1','mode':'deterministic_readonly_diagnostics','real_model':'not_run',
            'reference_labels_loaded':False,'cases':rows}


def compare(predictions):
    gold_path=runtime.active_reference()
    gold=legacy.read(gold_path);expected={r['case_id']:r for r in gold['cases']}
    rows_in=predictions['cases']
    if len(rows_in)!=29 or {p['case_id'] for p in rows_in}!=set(runtime.CASE_IDS):
        raise ValueError('incomplete or duplicate v3 diagnostic inventory')
    rows=[]
    for i,p in enumerate(rows_in):
        cid=p['case_id'];r=expected[cid];path=runtime.input_path(cid)
        if (p['input_path']!=str(path.relative_to(runtime.ROOT)) or
            p['input_sha256']!=r['input_sha256'] or legacy.file_sha(path)!=r['input_sha256']):
            raise ValueError('prediction/reference input binding mismatch')
        witnesses=[w for w in p['witnesses'] if w['status']=='violated']
        rows.append({'case_id':cid,'expected':r['user_final_judgment'],
            'comparison_scope':p['comparison_scope'],'sp_prediction':None,
            'comparison_is_sp_accuracy':False,'delivery_approved':False,
            'input_path':p['input_path'],'input_sha256':p['input_sha256'],
            'reference_path':runtime.GOLD_PATH,'reference_pointer':'/cases/'+str(gold['cases'].index(r)),
            'prediction_pointer':f'/cases/{i}','witness_rule_ids':p['witness_rule_ids'],
            'bounded_violation_witness_count':len(witnesses),
            'limitations':p['limitations']})
    return {'dataset_role':'development_only','reference_manifest_sha256':legacy.file_sha(gold_path),
            'active_reference_path':runtime.GOLD_PATH,'active_index_path':runtime.INDEX_PATH,
            'comparison_is_sp_accuracy':False,'reason':'Core diagnostics are not three-way semantic predictions',
            'cases':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('predict','native'):
        sub.add_parser(name).add_argument('output',type=Path)
    p=sub.add_parser('compare');p.add_argument('predictions',type=Path);p.add_argument('output',type=Path)
    args=parser.parse_args()
    result=run_predictions() if args.command=='predict' else native_probes() if args.command=='native' else compare(legacy.read(args.predictions))
    legacy.write(args.output,result)
if __name__=='__main__':main()

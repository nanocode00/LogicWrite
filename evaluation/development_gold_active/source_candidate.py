"""Active v3 semantic evaluation; original v2 consumer remains reproducible."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime

legacy=runtime.module('source_v2_engine',runtime.ROOT/'evaluation/source_candidate_semantics/run.py')
legacy.GOLD=runtime.ROOT/runtime.GOLD_PATH
legacy.IDS=set(runtime.CASE_IDS)
legacy.INPUTS=runtime.IndependentInputs()
_predict=legacy.predict
_compare=legacy.compare
CliReviewer=legacy.CliReviewer


def predict(case_ids,**kwargs):
    if not case_ids or len(set(case_ids))!=len(case_ids) or not set(case_ids)<=set(runtime.CASE_IDS):
        raise ValueError('unique active v3 case IDs required')
    return _predict(case_ids,**kwargs)


def compare(predictions):
    legacy.GOLD=runtime.active_reference()  # Labels enter only after prediction materialization.
    result=_compare(predictions)
    for row,prediction in zip(result['cases'],predictions['cases']):
        semantic=prediction['result']
        row['reproduce']=f"python3 evaluation/development_gold_active/source_candidate.py predict /tmp/{row['case_id']}.json --case {row['case_id']}"
        # Completed cited abstention is distinguishable from missing/unexecuted review.
        # Existing definitive-only accuracy denominator is preserved.
        row['three_way_observation']=(row['actual'] if row['included_in_metric'] else
            'UNRESOLVED' if row['all_checks_reviewed'] and semantic['semantic_judgment']=='unresolved' else None)
    result['active_index_path']=runtime.INDEX_PATH
    return result


legacy.predict=predict
legacy.compare=compare
if __name__=='__main__':legacy.main()

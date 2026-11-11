"""Read-only validation of user-submitted finals, without gold activation."""
import collections,hashlib,importlib.util,json,pathlib
from jsonschema import Draft202012Validator
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PR25='740de2e3c51f8f7b2a8357269012929483a376a1'
# Reuse the existing canonical event hash, without manufacturing legacy events.
spec=importlib.util.spec_from_file_location('submission_legacy_hash',ROOT/'evaluation/semantic_pilot/user_review_v1/workflow.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
event_digest=legacy.event_digest
IDS=[f'GC-{i:03}' for i in range(1,13)]+[f'SP-{i:03}' for i in range(13,18)]
EXPECTED=['PRESERVED','VIOLATION','UNRESOLVED']*4+['VIOLATION']+['PRESERVED']*4
COUNTER='evaluation/golden_expansion/codex_counterreview_2026_11_11/'
def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def ref(path,pointer):return dict(path=path,sha256=sha((ROOT/path).read_bytes()),pointer=pointer)
def resolve_reference(r):
 p=(ROOT/r['path']).resolve();require(p.is_relative_to((ROOT/'evaluation').resolve()),'reference outside evaluation');require(sha(p.read_bytes())==r['sha256'],'reference SHA mismatch')
 obj=load(p)
 for key in r['pointer'].lstrip('/').split('/'):
  key=key.replace('~1','/').replace('~0','~');obj=obj[int(key)] if isinstance(obj,list) else obj[key]
 return obj

def check_event(e,row):
 p=e['payload']
 require(e['case_id']==row['case_id'],'case mismatch')
 require(p==dict(counterargument_response=row['counterargument_response'],judgment=row['judgment'],matches_initial=True,rationale=row['additional_reason'],approve_for_development_gold=None),'user submission values or approval mismatch')
 require(e['actor_type']=='human' and e['recorder_type']=='ai','source/recorder attribution')
 require(e['user_reviewed_at'] is None and e['signature'] is None,'invented review timestamp/signature')

def validate():
 # All validation paths are read-only; no repair, rendering, approval or writes.
 for name,digest in load(HERE/'artifact-manifest.json').items():require(sha((HERE/name).read_bytes())==digest,'submission artifact changed: '+name)
 for name,digest in load(HERE/'preserved-files.json').items():require(sha((ROOT/name).read_bytes())==digest,'existing file changed: '+name)
 source=load(HERE/'submission.json');record=load(HERE/'events.json')
 require(source['basis_commit']==PR25 and source['basis_pr']==25,'source basis mismatch')
 require(source['source_kind']=='user_message_transcription' and source['externally_authenticated'] is False,'submission provenance')
 require(source['user_reviewed_at'] is None and source['signature'] is None,'invented source metadata')
 require([r['case_id'] for r in source['cases']]==IDS,'submission coverage/order')
 require([r['judgment'] for r in source['cases']]==EXPECTED,'user judgments differ from supplied table')
 require(source['collection_groups']==[IDS[:4],IDS[4:8],IDS[8:12],IDS[12:16],IDS[16:]],'collection grouping')
 schema=load(HERE/'event.schema.json');Draft202012Validator.check_schema(schema)
 require([e['case_id'] for e in record['events']]==IDS,'event coverage/order')
 require(record['schema_version']=='user-final-submission-v1' and record['basis_commit']==PR25,'record schema/basis')
 previous=None
 for i,(e,row) in enumerate(zip(record['events'],source['cases'])):
  errors=list(Draft202012Validator(schema).iter_errors(e));require(not errors,'event schema invalid: '+'; '.join(x.message for x in errors))
  require(e['event_id']=='user-final-submission-'+row['case_id'],'event ID')
  require(e['previous_event_sha256']==previous,'event chain mismatch')
  require(e['collection_order']==i+1 and e['collection_group']==i//4+1,'collection order/group')
  require(row['counterargument_response']=='동의' and row['additional_reason']=='추가 의견 없음' and row['approve_for_development_gold'] is None,'submitted response/reason/approval')
  check_event(e,row)
  require(e['submission_reference']==dict(path='evaluation/golden_expansion/user_final_2026_11_11/submission.json',sha256=sha((HERE/'submission.json').read_bytes()),pointer=f'/cases/{i}'),'submission reference')
  initial=resolve_reference(e['initial_reference']);require(e['initial_reference']['path']==COUNTER+'initial-judgments.json' and e['initial_reference']['pointer']==f'/cases/{i}','initial reference target')
  require(e['input_sha256']==initial['input_sha256']==sha((ROOT/initial['input_path']).read_bytes()),'input binding')
  require(initial['case_id']==e['case_id'] and initial['initial_judgment']==row['judgment'],'initial/final difference')
  ai=resolve_reference(e['counterreview_reference']);require(ai['case_id']==e['case_id'] and ai['input_sha256']==e['input_sha256'],'counterreview case/input binding')
  batch='gc01_06' if i<6 else 'gc07_12' if i<12 else 'sp13_17';idx=i if i<6 else i-6 if i<12 else i-12
  require(e['counterreview_reference']['path']==COUNTER+batch+'.raw.json' and e['counterreview_reference']['pointer']==f'/cases/{idx}','counterreview target')
  execution=resolve_reference(e['execution_reference']);require(e['execution_reference']['path']==COUNTER+batch+'.execution.json' and e['execution_reference']['pointer']=='/status' and execution=='completed','execution reference')
  previous=event_digest(e)
 require(record['terminal_event_sha256']==previous,'terminal seal mismatch')
 return dict(recorded=17,final_distribution=dict(collections.Counter(e['payload']['judgment'] for e in record['events'])),changed_from_initial=0,counterargument_agreements=17,approve_for_development_gold=None,existing_files_unchanged=True,provenance='User-submitted transcription; not externally authenticated raw chat or signature')
if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))

"""Offline verification and human review package rendering. Never invokes models."""
import collections,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
LABELS={'PRESERVED','VIOLATION','UNRESOLVED'}
BATCHES=['gc01_06','gc07_12','sp13_17']
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def require(ok,message):
 if not ok:raise ValueError(message)
def check_identity(result,initial):
 for k in ['case_id','input_sha256','initial_judgment']:require(result.get(k)==initial[k],'identity mismatch: '+k)
def check_quote(inp,e):
 try:
  ptr=e['pointer'];require(isinstance(ptr,str) and ptr.startswith('/'),'invalid pointer')
  v=inp
  for k in ptr[1:].split('/'):
   require(not re.search(r'~(?![01])',k),'invalid pointer escape')
   k=k.replace('~1','/').replace('~0','~')
   if isinstance(v,list):require(bool(re.fullmatch(r'0|[1-9][0-9]*',k)),'invalid array index');v=v[int(k)]
   else:v=v[k]
  require(isinstance(v,str),'quote target is not string')
  require(isinstance(e['quote'],str) and bool(e['quote'].strip()) and e['quote'] in v,'quote not exact substring')
 except (KeyError,IndexError,TypeError) as err:raise ValueError('invalid quote pointer') from err

def main():
 for name,digest in load(OUT/'preserved-files.json').items():require(sha((ROOT/name).read_bytes())==digest,'preserved file changed: '+name)
 initial=load(OUT/'initial-judgments.json')['cases']
 require((OUT/'initial-judgments.json').read_bytes()==(ROOT/'evaluation/golden_expansion/counterreview_2026_11_11/initial-judgments.json').read_bytes(),'initial history changed')
 require(len(initial)==17 and len({r['case_id'] for r in initial})==17,'initial coverage')
 baseline={r['case_id']:r for r in initial};collected={};failures=[]
 for batch in BATCHES:
  request=load(OUT/(batch+'.request.json'));execution=load(OUT/(batch+'.execution.json'))
  require(sha((OUT/(batch+'.request.json')).read_bytes())==execution['request_sha256'],'request hash')
  require(execution['fork_turns']=='none' and execution['requested_model_override'] is None,'context/model override')
  require(set(request)=={'instructions','cases'},'request fields')
  trace_bytes=(OUT/execution['tool_trace_path']).read_bytes()
  require(sha(trace_bytes)==execution['tool_trace_sha256'],'host tool trace hash')
  trace=json.loads(trace_bytes)
  require(trace['runtime_model']==execution['actual_model']=='gpt-6.1-sol','host model identity')
  require(trace['agent_path']==execution['agent_name'] and trace['session_id']==execution['child_session_id'],'host agent identity')
  for c in request['cases']:
   require(set(c)=={'initial','input'},'case request fields');r=c['initial'];require(r==baseline[r['case_id']],'initial mismatch')
   raw=(ROOT/r['input_path']).read_bytes();require(sha(raw)==r['input_sha256'],'input SHA');require(json.loads(raw)==c['input'],'full input mismatch')
   require(set(c['input']) <= {'schema_version','case_id','task','source_kind','construction','source_documents','candidate_documents','writing_contract','missing_context','supplied_observations'},'unexpected input field')
  try:
   require(execution['status']=='completed','agent execution incomplete')
   raw=(OUT/(batch+'.raw.json')).read_bytes();require(sha(raw)==execution['raw_response_sha256'],'raw response hash')
   response=json.loads(raw);require(isinstance(response['read_audit'],dict),'read audit');require(response['read_audit']['files_read']==[execution['isolated_request_path']],'reviewer read allowlist report')
   require([r['case_id'] for r in response['cases']]==execution['case_ids'],'response coverage/order')
   for r,c in zip(response['cases'],request['cases']):
    cid=c['initial']['case_id']
    try:
     check_identity(r,c['initial']);require(r['review_status']=='complete','review not complete');require(r['independent_recommendation'] in LABELS,'label')
     require(type(r['matches_initial']) is bool and r['matches_initial']==(r['independent_recommendation']==r['initial_judgment']),'match mismatch')
     for field in ['strongest_counterargument','counterargument_validity','rationale','remaining_uncertainty','user_question']:require(isinstance(r[field],str) and bool(r[field].strip()),'missing '+field)
     require(isinstance(r['evidence'],list) and bool(r['evidence']),'missing evidence')
     for e in r['evidence']:check_quote(c['input'],e)
     collected[cid]=dict(initial=c['initial'],result=r,batch=batch)
    except (ValueError,KeyError,TypeError) as err:failures.append(dict(case_id=cid,error=str(err),batch=batch))
  except (ValueError,KeyError,TypeError,FileNotFoundError) as err:
   failures.extend(dict(case_id=c['initial']['case_id'],error=str(err),batch=batch) for c in request['cases'])
 forms=[];table=['# Codex 독립 반례 검토 — 사용자 최종 판단 대기','','최초 판단과 Codex AI 반례를 구분한다. AI 권장 판단은 사용자 최종 판단이나 개발용 골드 포함 승인이 아니다. Qwen 결과는 이번 집계에서 제외했다.','','| ID | 사용자 최초 판단 | Codex 권장 | 일치 | 반론·정확한 근거·사용자 응답 |','|---|---|---|---|---|']
 for initial_row in initial:
  cid=initial_row['case_id'];form=dict(case_id=cid,input_sha256=initial_row['input_sha256'],counterargument_response=None,response_options=['동의','반박','보류'],response_reason=None,user_final_judgment=None,approve_for_development_gold=None);forms.append(form)
  if cid not in collected:table.append(f'| {cid} | {initial_row["initial_judgment"]} | 검토 실패 | — | 원인: validation.json |');continue
  item=collected[cid];r=item['result'];body=['# '+cid,'','## 사용자 최초 판단',r['initial_judgment']+' — '+initial_row['initial_reason'],'','입력 SHA-256: `'+r['input_sha256']+'`','','## 독립 Codex AI의 가장 강한 반론',r['strongest_counterargument'],'','## AI의 반론 타당성 평가',r['counterargument_validity'],'','## 정확한 인용 근거']
  for e in r['evidence']:body+=['',f'- `{e["pointer"]}`','','```text',e['quote'],'```']
  body+=['','## 독립 AI 권장 판단',r['independent_recommendation'],'','## 판단 근거',r['rationale'],'','## 남은 불확실성',r['remaining_uncertainty'],'','## 사용자 확인 사항',r['user_question'],'','## 사용자 응답 (미작성)','','반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류','','근거: ______','','사용자 최종 판단: ______','','개발용 골드 포함 승인: 미결정']
  (OUT/'cases').mkdir(exist_ok=True);(OUT/'cases'/(cid+'.md')).write_text('\n'.join(body)+'\n')
  table.append(f'| {cid} | {r["initial_judgment"]} | {r["independent_recommendation"]} | {"일치" if r["matches_initial"] else "불일치"} | [사례 검토](cases/{cid}.md) |')
 disagreements=[cid for cid,c in collected.items() if not c['result']['matches_initial']]
 table+=['',f'검증 완료 {len(collected)}건 / 검토 실패 {len(failures)}건.','','최초 판단과 불일치: '+(', '.join(disagreements) or '없음'),'','의미 판정 UNRESOLVED와 실행·검증 실패는 구분한다. 실패 재시도 시 원인을 해결하고 새 attempt에 입력 전용 요청만 전달한다. 성공 사례는 재호출하지 않는다.']
 (OUT/'REVIEW-PACKAGE.md').write_text('\n'.join(table)+'\n');
 if (OUT/'human-response-forms.json').exists():require(load(OUT/'human-response-forms.json')==forms,'human forms changed; refuse overwrite')
 else:save(OUT/'human-response-forms.json',forms)
 result=dict(completed=len(collected),failed=len(failures),disagreements=disagreements,recommendation_distribution=dict(collections.Counter(c['result']['independent_recommendation'] for c in collected.values())),cases=[dict(case_id=cid,batch=c['batch'],quote_count=len(c['result']['evidence']),recommendation=c['result']['independent_recommendation'],matches_initial=c['result']['matches_initial']) for cid,c in collected.items()],failures=failures)
 save(OUT/'validation.json',result)
 manifest=OUT/'artifact-manifest.json'
 if manifest.exists():
  for name,digest in load(manifest).items():require(sha((OUT/name).read_bytes())==digest,'artifact changed: '+name)
 print(json.dumps(result,ensure_ascii=False))
 require(len(collected)+len(failures)==17,'total coverage')
if __name__=='__main__':main()

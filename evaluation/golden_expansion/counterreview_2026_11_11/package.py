"""Revalidate preserved local evidence and generate advisory-only human review package."""
import json,pathlib,collections
import run
from retry import EXTRA
O=run.OUT

def main():
 rows=run.inputs(); report=[]; md=['# 사용자 최종 검토 대기 패키지','','최초 판단은 사용자 메시지의 기록이다. 아래 AI 반례·권장 판단은 독립 로컬 모델의 자문이며 사용자 최종 판단이나 골드 포함 승인이 아니다. 모든 사람 응답란은 미작성이다.','','| ID | 최초 판단 | AI 권장 | 일치 | 검증 상태 | 반론·근거 |','|---|---|---|---|---|---|']
 forms=[]
 for row in rows:
  cid=row['case_id'];d=O/cid
  if (O/'retry-01'/cid/'execution.json').exists(): d=O/'retry-01'/cid
  relative=d.relative_to(O).as_posix()
  ex=json.loads((d/'execution.json').read_text());item=dict(case_id=cid,initial_judgment=row['initial_judgment'],status='failed',error=ex.get('error'))
  try:
   req=json.loads((d/'request.json').read_text());raw=(d/'response.json').read_bytes();rsp=json.loads(raw)
   assert run.sha(json.dumps(req,ensure_ascii=False).encode())==ex['request_sha256']
   assert run.sha(raw)==ex['raw_response_sha256']
   inp=json.loads((run.ROOT/row['input_path']).read_bytes())
   assert ex['input_sha256']==row['input_sha256']
   expected=run.PROMPT+(EXTRA if 'retry-01' in d.parts else '')+json.dumps(dict(initial=row,input=inp),ensure_ascii=False)
   assert req['prompt']==expected,'request isolation/full input mismatch'
   assert rsp['model']==run.MODEL and rsp['done'] is True and rsp.get('done_reason')!='length'
   assert rsp['prompt_eval_count']+req['options']['num_predict']<req['options']['num_ctx'],'context budget'
   r=run.validate(json.loads(rsp['response']),row,inp)
   # Independent evidence validation; does not overwrite original execution outcome.
   run.write(d/'review.json',r)
   item.update(attempt_path=relative,status='validated',error=None,recommendation=r['independent_recommendation'],matches_initial=r['independent_recommendation']==row['initial_judgment'],quote_count=len(r['evidence']))
   body=['# '+cid,'','## 사용자 최초 판단',row['initial_judgment']+' — '+row['initial_reason'],'입력 SHA-256: `'+row['input_sha256']+'`','','## 독립 AI 반례',r['strongest_counterargument'],'','## AI의 반론 타당성 평가',r['counterargument_validity'],'','## 정확한 인용 근거']
   for e in r['evidence']:body+=['',f"- `{e['pointer']}`",'', '```text',e['quote'],'```']
   body+=['','## AI 권장 판단',r['independent_recommendation'],'','## 남은 불확실성',r['remaining_uncertainty'],'','## 사용자 확인 사항',r['user_question'],'','## 사용자 응답 (미작성)','','반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류','','근거: ______','','사용자 최종 판단: ______','','개발용 골드 포함 승인: 미결정']
   if cid=='GC-003': body[2:2]=['실행자 품질 점검: AI 권장 라벨은 UNRESOLVED이나 타당성 설명은 PRESERVED를 주장한다. 의미상 결론 불일치로 검토 완료에서 제외. 사람 판단을 요청하며 원시 AI 결과는 수정하지 않았다.','']
   if cid=='GC-002': body[2:2]=['실행자 품질 점검: AI는 Python 3.10+ → 3.8+를 범위 축소라고 표현했다. 최소 버전이 낮아지므로 이 표현은 잘못되었다. 원시 AI 권장 판단은 그대로 보존한다.','']
   (d/'REVIEW.md').write_text('\n'.join(body)+'\n')

  except Exception as err:item.update(error=type(err).__name__+': '+str(err))
  if cid=='GC-003' and item['status']=='validated':
   item.update(status='failed',error='semantic_inconsistency: recommendation is UNRESOLVED but validity rationale argues PRESERVED; operator audit, no model correction',matches_initial=None)
  if cid=='GC-002': item['quality_note']='AI calls Python 3.10+ -> 3.8+ a scope reduction; numeric minimum decreases, so this description is erroneous. Recommendation retained as raw advisory only.'
  report.append(item)
  forms.append(dict(case_id=cid,input_sha256=row['input_sha256'],review_status=item['status'],counterargument_response=None,response_options=['동의','반박','보류'],response_reason=None,user_final_judgment=None,approve_for_development_gold=None))
  md.append(f"| {cid} | {row['initial_judgment']} | {item.get('recommendation','—')} | {item.get('matches_initial','—')} | {item['status']} | [검토 자료]({relative}/REVIEW.md) |" if item['status']=='validated' else f"| {cid} | {row['initial_judgment']} | {item.get('recommendation','—')} | 판정 제외 | 실패 | [원시 검토]({relative}/REVIEW.md): {item['error']} |")
 counts=collections.Counter(r['status'] for r in report);mismatch=[r['case_id'] for r in report if r.get('matches_initial') is False]
 run.write(O/'validation.json',dict(cases=report,counts=dict(counts),disagreements=mismatch,method='Exact request reconstruction; raw input/request/response hashes; response completion/context budget; all quotes resolved against original input. /input prefix accepted as wrapper reference. Original execution logs preserved.'))
 run.write(O/'human-response-forms.json',forms)
 calls=[]
 for ep in sorted(O.glob('**/execution.json')):
  e=json.loads(ep.read_text());calls.append(dict(path=str(ep.relative_to(O)),case_id=e['case_id'],requested_model=e['requested_model'],actual_model=e.get('actual_model'),status=e['status'],seconds=e['seconds'],error=e.get('error')))
 run.write(O/'calls.json',dict(total_actual_calls=len(calls),calls=calls))
 md+=['','품질 주의: GC-002의 AI 반론에는 Python 3.10+ → 3.8+ 변경을 지원 범위 축소로 표현한 오류가 있다. GC-003은 권장 라벨과 타당성 설명이 상충하여 완료 집계에서 제외한다. 원시 응답은 수정하지 않았다.','','검증 완료: '+str(counts['validated'])+' / 실패: '+str(counts['failed']),'','최초 판단과 불일치: '+(', '.join(mismatch) or '없음'),'','실패는 UNRESOLVED 의미 판정과 별개다. 실패 사례 재시도는 원인(시간 초과·형식·인용·문맥 예산)을 해결한 후 새 attempt 디렉터리에 저장해야 한다. 최초 실패 4건에 한해 형식 지시를 강화한 1회 재시도를 수행했다. 추가 자동 재시도는 없다.','', '원시 실행 상태와 재검증 상태는 구분한다. 최초 실행의 `/input` 포인터 거부는 검증기 문제이며 원시 응답을 재검증하여 복구했다. 정확한 인용 검증은 의미 판단의 타당성이나 모델의 원격 인증을 보증하지 않는다.']
 (O/'REVIEW-PACKAGE.md').write_text('\n'.join(md)+'\n')
 print(dict(counts),mismatch)
if __name__=='__main__':main()

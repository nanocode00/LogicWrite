"""Explicit rendering into a NEW directory only; never overwrite review material."""
import argparse,json,pathlib
import validate

def build_outputs(initial,collected,failures,result):
 outputs={}
 forms=[];table=['# Codex 독립 반례 검토 — 사용자 최종 판단 대기','','최초 판단과 Codex AI 반례를 구분한다. AI 권장 판단은 사용자 최종 판단이나 개발용 골드 포함 승인이 아니다. Qwen 결과는 이번 집계에서 제외했다.','','| ID | 사용자 최초 판단 | Codex 권장 | 일치 | 반론·정확한 근거·사용자 응답 |','|---|---|---|---|---|']
 for initial_row in initial:
  cid=initial_row['case_id'];form=dict(case_id=cid,input_sha256=initial_row['input_sha256'],counterargument_response=None,response_options=['동의','반박','보류'],response_reason=None,user_final_judgment=None,approve_for_development_gold=None);forms.append(form)
  if cid not in collected:table.append(f'| {cid} | {initial_row["initial_judgment"]} | 검토 실패 | — | 원인: validation.json |');continue
  item=collected[cid];r=item['result'];body=['# '+cid,'','## 사용자 최초 판단',r['initial_judgment']+' — '+initial_row['initial_reason'],'','입력 SHA-256: `'+r['input_sha256']+'`','','## 독립 Codex AI의 가장 강한 반론',r['strongest_counterargument'],'','## AI의 반론 타당성 평가',r['counterargument_validity'],'','## 정확한 인용 근거']
  for e in r['evidence']:body+=['',f'- `{e["pointer"]}`','','```text',e['quote'],'```']
  body+=['','## 독립 AI 권장 판단',r['independent_recommendation'],'','## 판단 근거',r['rationale'],'','## 남은 불확실성',r['remaining_uncertainty'],'','## 사용자 확인 사항',r['user_question'],'','## 사용자 응답 (미작성)','','반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류','','근거: ______','','사용자 최종 판단: ______','','개발용 골드 포함 승인: 미결정']
  outputs['cases/'+cid+'.md']=('\n'.join(body)+'\n').encode()
  table.append(f'| {cid} | {r["initial_judgment"]} | {r["independent_recommendation"]} | {"일치" if r["matches_initial"] else "불일치"} | [사례 검토](cases/{cid}.md) |')
 disagreements=[cid for cid,c in collected.items() if not c['result']['matches_initial']]
 table+=['',f'검증 완료 {len(collected)}건 / 검토 실패 {len(failures)}건.','','최초 판단과 불일치: '+(', '.join(disagreements) or '없음'),'','의미 판정 UNRESOLVED와 실행·검증 실패는 구분한다. 실패 재시도 시 원인을 해결하고 새 attempt에 입력 전용 요청만 전달한다. 성공 사례는 재호출하지 않는다.']
 outputs['REVIEW-PACKAGE.md']=('\n'.join(table)+'\n').encode()
 outputs['human-response-forms.json']=(json.dumps(forms,ensure_ascii=False,indent=2)+'\n').encode()
 outputs['validation.json']=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
 return outputs

def render(destination):
 destination=pathlib.Path(destination)
 if destination.exists() or destination.is_symlink():
  raise FileExistsError('render destination must not exist: '+str(destination))
 if destination.resolve().is_relative_to(validate.OUT.resolve()):
  raise ValueError('render destination must be outside the source package')
 # All source integrity and evidence checks finish before creating any output.
 result,initial,collected,failures=validate.verify()
 outputs=build_outputs(initial,collected,failures,result)
 destination.mkdir()
 for name,content in outputs.items():
  target=destination/name
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as handle:handle.write(content)
 return destination

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',required=True,type=pathlib.Path)
 print(render(parser.parse_args().output))
if __name__=='__main__':main()

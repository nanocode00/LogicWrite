# Qwen3 235B Instruct 독립 B0/B1 비교

2026-11-17 · PR #36 · 프로토콜 `integrated-qwen-instruct-20261117-v1`.

**Probe 2회와 평가 6회를 실행하여 동일 조건·전체 문서 후보의 비교 쌍 3개를 확보했다.** HTTP/형식/실행 프로토콜 완료와 의미 평가 성공은 구분한다. AI 검토에서는 세 사례 모두 결함이 남으며, 특히 IR-003/B1의 format_only 경계 위반을 관측했다. 사람 최종 의미 판정은 모두 미확정이다. 기존 DeepSeek 결과와 합산해 품질을 비교하지 않는다.

## 실행 설정과 입력 통제

- 모델 `qwen/qwen3-235b-a22b-2507`, provider 요청 `deepinfra/fp8`, 실제 응답 provider `DeepInfra`. temperature0, 평가 max_tokens12000, timeout600초, JSON object 모드. 비사고 Instruct이므로 reasoning 파라미터를 보내지 않았다. 모든 응답은 reasoning_tokens=0을 명시했다.
- [공식 endpoint](https://openrouter.ai/api/v1/models/qwen/qwen3-235b-a22b-2507/endpoints)와 [모델 소개](https://openrouter.ai/qwen/qwen3-235b-a22b-2507)를 확인했다. 이 모델의 비사고 특성은 공식 소개와 부합한다. 각 요청 전 저장한 endpoint metadata는 fp8 일반 서비스, input $.09/M·output $.55/M, context262144, max completion16384, max_tokens/temperature/response_format 지원, status0이었다. 실제 확인 시각은 각 execution.json의 endpoint.checked_at에 있다(2026-11-17 UTC 08:11 이후). Flex/priority/provider fallback을 사용하지 않았다.
- 응답 모델 ID는 요청 ID와 일치한다. 공급자의 가중치 hash·serving revision·물리 backend는 API 응답에서 확인되지 않았다. fp8은 고정 요청 및 endpoint 선언으로 확인한 것이며 자체 가중치 검사 결과가 아니다.
- BASE/IMPROVED 일반 지침과 기존 공통 DELIVERY만 사용했다. 세 쌍 모두 user 입력·생성 설정이 동일하고 B1에 일반 IMPROVED만 추가됐음을 `automatic-summary.json`에서 검사했다. 전송 user 메시지는 export_input 결과와 정확히 같다. 기준·정답·참고 출력·검수·진단 태그·이전 응답을 모델에 전송하지 않았다. 추가 평가용 모델 호출도 없다.
- 출력 문서는 `evaluation/IR-00x/Bx/candidate.json`에만 저장했다. 실제 프로젝트 문서 적용·발행은 없다. 모델 요청과 원본 응답·usage·시간·상태·endpoint·키 상태를 각 실행 폴더에 보존했다. 원본 응답을 참고 출력으로 바꾸지 않았다.

## 원장 활성화와 비용 통제

기존 blocked 원장은 이전 ledger-final과 정확히 일치했고, legacy 요청과 캠페인 비용 합이 $.0134719416이었다. GET /key usage $.01347194와 정밀도 오차 범위에서 일치했으며 pending=false였다. lifetime limit $.25, reset 없음, BYOK없음도 확인했다.

`activation/ledger-before.json`, `activation.json`, `ledger-after.json`은 사용자 승인에 의한 새 캠페인 활성화 기록이다. **기존 blocked=true·block_reason 및 DeepSeek attempts를 그대로 보존**하고 active_campaign에 Qwen만 지정했다. 원장을 초기화하거나 기존 실패를 해제·정상화하지 않았다. 옛 실행기는 전역 blocked 때문에 계속 실행할 수 없다. 기존 run.py/comparison_v2.py는 수정하지 않았다.

새 runner는 shared lock, 최대8회·고정 순서·중복 금지, 신규$.06 및 전역$.20, 요청 직전 키/endpoint/단가/용량 확인을 적용한다. 입력 UTF8bytes+4096와 최대 출력의 비용을 사전 표시·예약했다. 전체 계획 추정은 $.04622531이었다. 추정은 tokenizer나 실제 공급자 상한 강제의 증명이 아니다. 비용·토큰/모델/provider/출력 오류나 불명 청구는 해당 캠페인을 차단한다. 확인된 비용은 다른 검사보다 먼저 정산하며 timeout/불명 비용은 pending 예약을 남긴다. 자동 재시도·병렬·새 폴더를 이용한 횟수 초기화는 없다.

실행 중 /key 반영 지연은 알려진 cost를 원장에 유지하고 max(서버,로컬)로 통제했다. 미확인 추가 사용량을 허용한 것은 아니다. 마지막 읽기 전용 키 조회에서는 정산이 완료됐다(`settlement-final.json`). 생성 요청은 총8회이며 추가 호출을 하지 않았다.

| 항목 | USD |
|---|---:|
| Probe 2회 | 0.00005424 |
| B0 평가 3회 | 0.00210450 |
| B1 평가 3회 | 0.00248068 |
| 신규 캠페인 합계 | **0.00463942** |
| 기존 비용 포함 전역 누적 | **0.0181113616** |
| 신규 $.06 대비 미사용 예산 | 0.05536058 |
| 전역 $.20 대비 미사용 예산 | 0.1818886384 |
| 최종 키 usage / limit_remaining | 0.01811136 / **0.23188864** |

남은 금액은 추가 호출 승인이 아니다. IR-003/B1의 AI 권한 검토 후 Qwen 캠페인도 semantic_format_only_violation으로 차단했다. `operator-stop-before.json`, `operator-stop-event.json`, `ledger-final.json`이 그 기록이며 비용·기존 실패는 보존했다. 마지막 8번째 호출 이후 발견했으므로 실제로 생략된 후속 요청은 없다. 사람 최종 판정으로 둔갑시키지 않았다.

## 호출별 실제 결과

모든 호출 HTTP200, 같은 모델/DeepInfra, reasoning0이다. Probe A의 length만 의도한 cap stress 종료로 허용하며 평가의 length는 실패로 처리하도록 구현했다.

| 요청 | 입력 토큰 | 출력 토큰 | 비용 USD | 시간 초 | finish_reason |
|---|---:|---:|---:|---:|---|
| Probe-A | 35 | 64 | 0.00003835 | 3.841 | length |
| Probe-B | 36 | 23 | 0.00001589 | 1.703 | stop |
| IR-001/B0 | 2409 | 1152 | 0.00085041 | 78.748 | stop |
| IR-001/B1 | 2523 | 1274 | 0.00092777 | 94.595 | stop |
| IR-002/B0 | 1987 | 1027 | 0.00074368 | 45.916 | stop |
| IR-002/B1 | 2101 | 1316 | 0.00091289 | 56.187 | stop |
| IR-003/B0 | 1369 | 704 | 0.00051041 | 36.890 | stop |
| IR-003/B1 | 1483 | 921 | 0.00064002 | 39.461 | stop |

Probe A는 짧은 독립 숫자목록으로 64토큰 제한을 준수했다. Probe B는 독립 demo 전체 JSON 문서를 정확히 반환했다. 두 probe에 평가 사례는 쓰지 않았다. 작은 cap 통과는 12000 제한의 일반 보장이 아니지만, 이번 평가 6회도 모두 12000 이내였고 절단은 관측되지 않았다. 모델 generation 시간의 요약이며 wall time에는 검사·GET·내용 검토가 추가된다.

## 자동 검사와 AI 의미 평가 초안

자동 검사는 JSON 구조·편집 가능 전체 후보 존재·빈 본문·read_only 수정·모델/provider·토큰·비용·요청 쌍 통제를 확인했다. 이 검사는 format_only의 단어 변경이나 안전 조건의 의미적 누락까지 보장하지 않는다. 모델 final_checks는 검증 증거로 신뢰하지 않는다.

`assessment-draft.json`에 6개 후보 각각의 D ID, Q1–Q4, F ID, 5개 Q품질축(0–3), HITL, 정확 인용과 입력/기준/후보 hash를 기록했다. `assessment-evidence-check.json`은 인용26건·해시의 기계 검증이며 의미 판단의 승인이 아니다. **D는 모두 unobserved**다. 사후 검토 메모로 D를 역산하지 않았다. 참고 출력과 문자열 유사도를 채점에 사용하지 않았다.

| 사례 | B0 AI 초안 | B1 AI 초안 | 비교/실패 유형 |
|---|---|---|---|
| IR-001 | README 원문 유지, usage 설치→실행 정렬. 폴더 존재 전제 누락, 후원 정책 충돌 미검출. Windows 미검증을 미지원으로 표현한 검토 질문도 부정확 | 두 편집 가능 문서를 모두 원문 반환. 설치→실행 순서 개선도 없고 같은 전제·정책 확인 누락. 제약을 오해해 독립 작업까지 보류 | B1 퇴행: 과잉 보류·편집 회피. 양쪽 Q2/Q3/Q4 결함, F2 폴더 전제 누락. B1은 F1 독립 개선 보류도 관측. 일기 삭제를 보류하고 원문 보존한 부분 자체는 적절 |
| IR-002 | 환경별60/30 구별·ID/24시간·역사 원문 보존. ops에서 500 초과 중단/당직 확인 전 재개 금지 누락. 혼합기간 관찰을 현행 정책 초기 성과로 귀속 | 같은 ops 안전 누락. 표본 한계와 장기 안정성 미입증을 명시해 관찰 표현 개선. 충분한 근거가 있는데 안정성 문구 처리를 다시 확인 질문으로 둠 | B1 일부 개선이나 Q2 안전 과업 실패는 공통. 자체 검증은 둘 다 조건 충족을 잘못 주장. 좁은 F2는 조건 변조/재개 허용 문구를 대상으로 하므로 해당 ID 판정은 재검수하되 누락의 중대성은 별도 유지 |
| IR-003 | meeting 전체 원문 무수정. 사실·공개 제한 보존, public/ 접근 불가 명시. 질문은 대체로 불확실성 설명이며 구체적 권한 요청 부족 | “실패다.”→“실패.” 어미 삭제를 format_only로 정당화. 사실 수치·승인 제한은 보존하나 불필요한 내용 변경. 질문도 직접 확인 요청보다 설명 중심 | B1 퇴행: format_only 경계 위반(F1) 및 잘못된 자체 승인. B0 무수정은 정당하며 변경이 없다는 이유로 실패 처리하지 않음. 안전 서식도 불가능하다는 B0 보류 근거는 과도 |

IR-001은 후원 문구 원문이 남았다는 이유만으로 정책 임의 확정이라고 단정하지 않았다. 문제는 충돌·양쪽 근거·HITL 확인을 빠뜨린 점이다. 일기 정보 제거/분리 확인과 기술 결정 보존은 서로 다른 판단이며, 두 후보 모두 기술 이력을 직접 수정하지 않았다. README에 정책 검토 메모를 새로 넣지는 않았다.

IR-002의 적용일은 문서군 전체(읽기 전용 ADR 포함)에서 확인 가능하다. 설계/운영 문서에 동일 조건을 모두 반복하도록 강제하지 않았다. 반면 운영서만으로 확인해야 하는 중단/재개 조건은 다른 문서에 있다는 이유로 면제하지 않았다. B0가 일반 안정성을 명시 보장했다고 과장하지 않으며 잘못된 정책기간 귀속과 한계 누락을 구분한다. B1도 ops 안전 누락을 좋은 문체로 상쇄할 수 없다.

IR-003/B1의 final_checks는 인증 경로 단계 중단을 실패 원인으로 표현한다. 근본 원인 확정으로 읽히는지(F2)는 사람 재검수가 필요하다. format_only의 어미 수정은 별개로 명확한 권한 문제 초안이다. 두 후보 모두 회의 대상을 확정하거나 외부 공개본을 만들지 않았다. 다만 답할 수 있는 구체적 회의 대상·공유 범위·내용 수정 권한 질문이 부족하다.

효율: B0 출력 합2883토큰/161.555초, B1 출력 합3511토큰/190.243초다. 비용과 출력 길이는 B1이 더 컸지만 완성도 향상으로 해석하지 않는다. B0/B1의 출력 길이 차이에는 검토 메모 길이도 포함된다. 품질 축의 합산 평균·D/Q 총점·일반 성능 향상 주장은 하지 않는다.

## 실행 재현과 검증

사용한 명령의 기본 형태는 아래와 같다. **기존 디렉터리는 재사용할 수 없고 현재 원장도 이미 차단되어 있다. 아래 유료 명령을 다시 실행하라는 안내가 아니다.**

```sh
python3 -B experiments/integrated_reconstruction_pilot_20261117/comparison_qwen.py --phase prepare --output NEW_DRY_DIRECTORY
python3 -B experiments/integrated_reconstruction_pilot_20261117/comparison_qwen.py --phase activate --execute --output NEW_ACTIVATION_DIRECTORY
python3 -B experiments/integrated_reconstruction_pilot_20261117/comparison_qwen.py --phase request --target Probe-A --execute --output NEW_TARGET_DIRECTORY
```

실제 경로는 dry-run/, activation/, probe-a/, probe-b/, evaluation/IR-001/B0부터 IR-003/B1까지다. 각 단계 로그와 plan/request/input/response/execution을 보존했다. 요청별 source commit은 새 runner 작성 전 HEAD이며, 동시에 기록한 runner/base/shared SHA-256이 최종 소스와 일치함을 검증했다.

새 단위 테스트는 가짜 API로 비용 보존·상한 초과·불명 비용 pending·동일 요청 재실행 금지·다른 실패 활성화 금지·정확한 provider/JSON 설정·독립 캠페인 예산·9번째 요청 금지를 확인한다. 전체 파일럿 및 통합 평가 회귀, 개발 골드 registry, 보존 검사를 실행 전후에 수행했다. 상세 로그는 pre-/post-* 파일이다. 검사 실측 수치는 아래 검증 결과에 기록한다. `.env`와 키·인증 헤더는 결과에 넣지 않았다.

## 다음 Core 후보와 실제 문서 평가

이번 B0/B1은 직접 모델 작성 경로다. Core/B2 기능 구현·확장·승인 정책 변경은 하지 않았다. 다음은 사용자 판단이 필요한 개선 후보다.

1. 문서별 권한을 단어 수준 diff와 연결하고 format_only에서 내용 변경을 차단할 수 있는지 검토한다. 모델 자체 권한 선언에 의존하지 않는다.
2. 필수 실행 전제와 운영 안전 조건을 목적 문서에서 확인하는 검증을 검토한다. 문서 간 무조건 반복과 독자 과업상 필요한 배치를 구별한다.
3. 정책 충돌을 찾되 원문 보존·HITL·독립 개선을 분리하고, 과잉 보류 및 허위 자체 검증을 검출하는 사례를 확장한다.
4. 실제 한국어 문서는 독립 작성자/조직의 승인 이력이 있는 운영 런북·설계·ADR 묶음, README/정책 충돌, 수정 불필요 및 format_only 회의 자료를 우선 수집한다. 원문/수정본·권한·공유 범위·이력을 확보하고 이번 합성 가족과 분리한다.

추가 사람 검수 쟁점은 F1/F2의 좁은 정의와 안전 누락의 별도 중대성, 원문 정책 충돌 보존의 허용 범위, 어미 수정과 서식 경계, 무수정 후보의 질문 적절성이다. 다음 파일럿은 사전 기준 캘리브레이션, 독립 실자료, 다회 반복과 모델 revision 기록, 비용/출력 상한의 다양한 길이 검증을 별도 승인된 예산 아래 설계한다. 자연 출력의 D unobserved와 사전 계획 제출 실험은 분리한다. 현재 3개 합성 사례·1개 출처 가족으로 일반 성능을 주장하지 않는다.

**최종 사람 의미 평가와 Core 수정 여부는 사용자에게 남긴다. 후속 유료 호출 승인도 현재 없다.**

검증 실측: 실행 전 파일럿 55건(후속 안전 테스트 추가 후57건)·통합63건 PASS, 최종 파일럿 **58/58**·통합 **63/63** PASS. 개발용 골드 및 보존 검사 실행 전후 PASS(기존 근거545개·보호 PR 객체421개·파일럿 근거21개 불변). 실제 응답 인용 **26/26**·기준/후보 해시·요청 쌍3건·토큰 단가별 비용 정산 검증 PASS. 기존 추적 파일 변경0개, 최종 원장 pending=false. 이번 의미 검토는 최종 사람 승인을 부여하지 않는다.

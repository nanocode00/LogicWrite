# 혼합 의미 판정 보완 검증

기준 PR #24 head: `51dff5d5d6cd318debd117c95b836b3035cf981e`. 이 수정에서 실모델·외부 AI 호출은 **0회**다. 합성 callback과 가짜 429 transport 응답만 결정론적 테스트에 사용했다. 사람 정답이나 새 골드를 생성하지 않았다.

| 확인 항목 | 명령 / 결과 |
| --- | --- |
| 원인 재현 red | `python3 -m unittest discover -s experiments/full_document_control -p test_source_candidate_adapter.py`. 1 contradicted/overstated + 1 unresolved + 5 supported가 unresolved로 사라지는 두 subtest 실패. 새 상태 필드 부재의 추가 오류도 [core-red.txt](core-red.txt)에 보존 |
| 사후 비교 red | `python3 -m unittest discover -s evaluation/source_candidate_semantics -p test_run.py`. 혼합 위반 표시 부재 및 분모 제외 보고서의 위조 요청 바인딩 미거부를 [runner-red.txt](runner-red.txt)에 재현 |
| 어댑터 green | 같은 어댑터 명령: **20개 통과**, [core-green.txt](core-green.txt) |
| 입력/정답 분리 및 비교 green | 같은 실행 도구 명령: **15개 통과**, [runner-green.txt](runner-green.txt). 신규 필드 없는 이전 확정 기록 호환성 포함 |
| 기존 최종 의미 검증 포함 전체 회귀 | `python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/all-tests.json`: **578개 통과**, Core 디렉터리 362개 포함. [전체 명령·출력·Python 파일 해시](all-tests.json) |
| 모델 미실행·429·예산·timeout·잘못된 응답 | 위 테스트의 기존 회귀 통과. 429는 mock transport이며 실제 provider를 호출하지 않음 |
| G3 및 PR #22 불변 | [preservation.json](preservation.json): main 기존 평가 186개 + PR #22 검수 자료 81개 바이트 일치 |
| 과거 실제 실행 기록 보존 | 기존 offline/429 파일럿 예측 파일을 새 compare로 읽어도 평가 완료 0·정확도 null. [historical-compatibility.json](historical-compatibility.json). 과거 파일을 재작성하거나 모델을 재실행하지 않음 |

## 판정과 분모

유효한 전체 7개 응답에서 위반이 하나라도 있으면 다른 응답의 unresolved와 관계없이 contradicted/FAIL이다. 모든 응답 supported일 때만 supported/REVIEW다. 위반 없이 unresolved가 남으면 unresolved/REVIEW다. 일부 응답 누락·인용/요청 바인딩 오류 등 전체 검토가 유효하지 않은 경우에는 위반을 임의로 확정하지 않는다.

`coverage.complete`와 `evaluated`는 기존의 모든 판단 확정 의미를 유지한다. 추가 필드 `all_checks_reviewed`, `all_judgments_definitive`, `violation_confirmed`, `model_execution_state`로 전체 검토·확정성·위반·실행 실패를 구별한다. 혼합 판정은 partially_evaluated로 표시하며 정확도 분모에서는 제외하지만 관측 위반·확인 위반 수에는 남긴다. 사후 비교는 이 제외 보고서도 요청/인용/항목별 판정까지 재검증한다.

## 기록의 신뢰 한계

입력/요청 SHA, snapshot 참조, 정확 인용, 응답 판정과 요약 판정의 일치는 **데이터 일관성**을 검사한다. 실제 모델 실행·모델 신원·내용 진실성을 인증하지 않는다. 저장된 파일은 advisory evidence이며 독립적으로 검증 가능한 실행 증거가 없으므로 `evidence_trust.model_execution_authenticated=false`다. 일관된 합성 응답도 같은 형식을 만들 수 있으며 이 테스트의 합성 판정은 모델 성능 근거가 아니다. provider 메타데이터나 자체 해시만으로 이 한계를 해소하지 않는다.

레거시 Core 승인·receipt·재구성 경로는 변경하지 않았다. 모든 전달/단계 승인 플래그는 false이며 PR 병합과 사람 최종 판정은 수행하지 않는다. 기존 `records/all-tests.json` 및 과거 artifact manifest는 `51dff5d`의 역사적 근거로 보존한다.

# v3 활성화 사전 점검 — 신규 17건 보류

현재 v2의 SP-001~012 **12건은 유지**한다. 신규 GC-001~012 / SP-013~017은 **포함 승인 17건, 기술적 활성화 적격 0건, 신규 활성화 0건**이다. v3 데이터셋·v3 활성 인덱스는 생성하지 않았다. 목표 29건 및 분포 PRESERVED 12 / VIOLATION 9 / UNRESOLVED 8은 목표 합계이며 실제 활성 상태가 아니다.

| 파일 | 역할 |
|---|---|
| report.json | 사례별 원본 입력·최초 판단·Codex 결과/실행·최종 판단·포함 승인·정식 워크플로의 SHA/JSON pointer 연결, 보류 사유와 출처/파생 관계. 활성 데이터셋이 아님 |
| validate_preflight.py | 현재 스냅샷 한정 읽기 전용 점검. 기존 검증기와 정식 review.assess를 호출하며 대체 적격 정책을 만들지 않음 |
| test_preflight.py | 승인과 적격 구분, 활성화 차단, UNRESOLVED·변조·삭제·범위 변경·읽기 전용 회귀 |
| preserved-files.json | 기준 main의 추적 파일 562개 SHA. v2·기존 평가 기록·정책·현재 평가 소비자 포함 |
| artifact-manifest.json | 정확한 파일 목록 및 해시. 보고서는 원본에서 재계산해 비교하므로 manifest만 재작성해도 내용 위조 탐지 |
| PLAN.md | 사용자 요구와 이번 작업의 범위·절차 |

## 실제 충족한 조건

17건 모두 최초 판단·이유와 입력 SHA 연결, 별도 Codex 반례 검토 및 정확한 입력 인용, 완료 실행 기록, 사례별 사용자 `동의`·최종 판단, PR #27 포함 승인 true가 존재한다. 각 기존 읽기 전용 검증기가 통과하며 입력·증거·해시 체인은 유효하다. AI의 판단 설명을 사용자 정답이나 사용자 근거로 복사하지 않았다.

기존 최종 판단 PRESERVED 8 / VIOLATION 5 / UNRESOLVED 4와 과거 승인 null을 보존한다. GC-003/006/009/012의 최초 사용자 이유는 각각 전체 내용 재수신 또는 이동 문서 본문 필요이며 report.json에 원문 그대로 참조한다. 이 4건은 **자료 부족에 대한 유효한 판단**이다. 보류 사유는 UNRESOLVED라는 라벨이 아니라 정식 검토 이력의 미충족이다. 부족한 문서 자체를 확보해야 UNRESOLVED가 적격해진다는 주장은 하지 않는다.

## 미충족 조건과 영향 사례

다음 다섯 조건은 **신규 17건 전부**에 해당한다. 사례별 목록은 report.json의 cases/blockers와 blocked_case_ids에 있다.

| 코드 | 기존 정책의 요구 및 현재 부족한 자료 |
|---|---|
| FORMAL_REVIEW_CHAIN_NOT_RECORDED | prepared/*.workflow.json의 events는 빈 배열이며 review.assess는 ai_provisional / development_gold_eligible=false. 별도 #26/#27을 user_final로 간주할 수 없음 |
| USER_INITIAL_FORM_INCOMPLETE | 정식 initial form과 동일 human actor_id 연결이 미작성. reviewer_id는 이벤트 actor_id와 일치해야 한다. reviewed_at·blinded_to_prior_judgments는 필수 **키**이나 값은 null을 허용하고, initial evidence는 빈 배열도 허용한다. VIOLATION findings와 UNRESOLVED missing_information은 비어 있으면 안 된다 |
| USER_FINAL_EVIDENCE_NOT_SUBMITTED | user_final 스키마는 최소 1개 evidence(side/document_id/start/end/quote)를 요구. #26은 최종 라벨과 '추가 의견 없음' 및 참조만 기록하며 사용자 작성 증거 배열이 아님 |
| CHALLENGE_RESPONSES_NOT_BOUND | 정식 counterreview event ID 및 challenge_id별 accept/reject/defer와 rationale 연결 없음. 실제 사례별 '동의'는 존재하지만 이를 임의로 세부 반론 수락·해결로 변환하지 않음 |
| FINAL_CONFIDENCE_LIMITATIONS_NOT_CONFIRMED | 정식 user_final의 confidence_limitations 및 동일 human actor_id/human_confirmed를 가진 순서·시각 연결 이벤트 미제출. 알려진 단일 사용자 한계를 사용자 확인 이벤트로 합성하지 않음 |

GC-003/006/009/012에는 FINAL_UNRESOLVED_ISSUES_NOT_SUBMITTED도 적용된다. 초기 이유와 AI의 부족 문맥 설명은 존재하지만 **최종 user_final.payload.unresolved_issues로 사용자가 확인한 별도 필드는 없다**. 이를 비어 있지 않은 새 사용자 최종 사유로 자동 전사하지 않았다. 최종 evidence는 최소 1개가 필요하지만 초기 evidence와 달리 이는 선택 사항이 아니다.

정식 event.recorded_at은 기록 시각이며 user reviewed_at과 구별된다. reviewed_at의 null 허용을 지키되 현재 저장 시각을 과거 사용자 검토 시각으로 사용하거나 과거 순서의 이벤트를 소급 생성하지 않는다. 기존 정책은 동일 actor_id를 요구하지만 **외부 인증 신원이나 전자서명을 요구하지는 않는다**. 그런 인증·서명이 없다는 사실 자체를 추가 차단 정책으로 만들지 않았으며, 허위로 생성하지도 않았다.

## 안전한 별도 경로가 가능한지

별도 스키마의 SHA/범위/출처는 안전하게 검증할 수 있지만, 정식 워크플로의 사용자 증거·반론별 응답·초기/최종 양식 요구를 삭제할 수는 없다. 현재 자료를 자동으로 활성화하는 경로는 이 조건을 생략하거나 AI 자료를 사용자 제출로 잘못 귀속해야 하므로 구현하지 않는다. 이번 검증기는 **차단 여부를 재현하는 경로**이며 우회 승인 경로가 아니다.

## 출처와 평가 한계

report.json은 GC의 repository/version/git_blob_sha/원문 snapshot 참조와 SP의 registry parent_inputs/SHA를 그대로 연결한다. GC 12건은 psf/requests, encode/httpx, pallets/click, prometheus/prometheus의 4개 계열에서 파생되었다. SP-013/014는 SP-003/011, SP-015는 SP-009, SP-016은 SP-010, SP-017은 SP-012의 통제 파생 사례다. 따라서 향후 사례 수와 독립 원문 계열 수를 구별하고 parent/family별 집계 또는 분리를 해야 한다. 단일 사용자+AI 보조의 개발용 자료이며 독립 홀드아웃·복수 독립 인간 검수 완료가 아니다.

## 실행 및 후속 단계

```sh
# 무결성 점검 성공과 활성화 준비 성공은 다르다. 아래 기본 명령은 status=blocked를 정상 보고한다.
python3 -B evaluation/golden_expansion/activation_preflight_2026_11_13/validate_preflight.py
# 자동화의 활성화 전제 조건: 현재 exit 2로 차단된다.
python3 -B evaluation/golden_expansion/activation_preflight_2026_11_13/validate_preflight.py --require-activation-ready
python3 -B -m unittest discover -s evaluation/golden_expansion/activation_preflight_2026_11_13 -v
python3 -B evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-preflight-regression.json
```

기존 v2 manifest와 두 평가 소비자(core_pipeline evaluate.py, source_candidate_semantics run.py)의 v2 참조를 그대로 검증한다. 새로운 활성 버전 참조를 등록하지 않는다. report.json의 active_cases는 v2의 12개 행과 스냅샷 참조를 그대로 보존한 감사용 복사이며 새 골드가 아니다.

실행 결과: 신규 회귀 7개 및 전체 18개 디렉터리 642개 테스트 통과. 테스트 전후 Python 입력 SHA 동일. 기준 main의 기존 추적 파일 562개를 Git blob bytes 및 SHA로 전수 비교해 변경 0건을 확인했다. 기본 사전 점검은 무결성 성공/status=blocked이며 활성화 전제 검사 옵션은 의도대로 exit 2다. 로컬 실행 결과이며 원격 CI 통과를 뜻하지 않는다.

기존 17건의 **판단·반례·최종 판단·포함 승인은 이미 실제 제출된 기록**이므로 의미 판단을 다시 받지 않는다. `../formal_review_reuse_2026_11_13/`의 `transcription.json`은 출처 SHA/JSON pointer와 연결된 불변 이력의 서식 변환본이고, `format-mapping.json`은 필드 매핑 초안, `suggestions.json`은 **사용자가 아직 채택하지 않은** 근거 인용 34개다. 재사용 가능 증빙과 아직 부족한 정식 필드는 `../formal_review_reuse_2026_11_13/EVIDENCE_COVERAGE.md`에 구분했다. 과거 시각·AI 인용·사례 단위 '동의'를 새 사용자 증거/반론별 응답으로 꾸며 쓰지 않는다. 현재 `review.py`의 필수 요건이 충족된 것으로 주장하지 않으며, 후속 확인이 필요한 경우 이미 확정한 라벨이 아닌 실제 미기록 필드만 대상으로 한다. 자료가 충족되면 별도 작업에서 v3 29건/12·9·8 및 활성 참조를 구현·검증한다. 현재 PR은 ChatGPT 독립 검수 대기이며 자동 병합하지 않는다.

# 사용자 최종 판단 제출 이력 — 골드 승인 미결정

PR #25의 기준 커밋 `740de2e3c51f8f7b2a8357269012929483a376a1`에서 17건의 Codex 반례 검토를 확인한 사용자가 이 대화에 제출한 최종 판단을 기록했다. **최종 판단 기록만 수행했으며 개발용 골드 포함 승인·활성화·기존 정답 수정은 하지 않았다.**

| 파일 | 역할 |
|---|---|
| [submission.json](submission.json) | 사용자가 제출한 값과 수집 순서의 구조화 전사. 외부에서 검증된 원시 채팅 이벤트나 전자서명이 아님 |
| [events.json](events.json) | 사례별 최초 판단·입력·Codex 원시 검토·실행·사용자 제출 출처를 SHA-256과 JSON pointer로 연결한 추가 전용 최종 판단 이력 |
| [event.schema.json](event.schema.json) | 사용자 판단의 출처와 AI 기록자의 역할을 구분하고 골드 승인을 null로 제한하는 별도 이벤트 스키마 |
| [preserved-files.json](preserved-files.json) | 기준 PR의 모든 추적 파일 SHA-256. 입력·최초 판단·원시 AI 결과·실행 증거·기존 골드 포함 |
| [artifact-manifest.json](artifact-manifest.json) | 새 이력의 변경·삭제 탐지용 파일 해시. Git 이력과 함께 검수하며 암호학적 사용자 인증으로 주장하지 않음 |
| [validate_submission.py](validate_submission.py) | 읽기 전용 검증기. 렌더링·승인·골드 활성화 기능 없음 |

## 기록된 제출값

총 17건: **PRESERVED 8 / VIOLATION 5 / UNRESOLVED 4**. 최초 판단 대비 변경 0건. AI 반론 평가 `동의` 17건, 추가 판단 이유 `추가 의견 없음` 17건, 개발용 골드 포함 승인 **null(미결정)** 17건이다. 동의는 독립 AI의 반론 평가에 대한 사용자 응답이며 반박 시도가 성공했다는 별도의 판단을 생성한 것이 아니다.

수집 순서는 GC-001~004 → GC-005~008 → GC-009~012 → SP-013~016 → SP-017이다. collection_order와 collection_group은 사용자 지정 순서이지 실제 검토 시간의 추정치가 아니다. user_reviewed_at과 signature는 모두 null이다. 사용자 이름·검토 시각·전자서명·외부 인증을 만들지 않았다. actor_type=human은 판단 제출의 출처, recorder_type=ai는 기록을 구조화한 주체다. 최초 이유 및 AI 분석은 참조로만 연결하며 사용자 최종 판단 이유로 복사하지 않았다.

UNRESOLVED 4건도 유효한 사용자 최종 판단이다. 검토 실행 실패가 아니며 골드 적격 판정과도 별개다.

## 기존 이벤트 정책과의 경계

`evaluation/golden_expansion/review.py` 및 record.schema.json의 기존 user_final은 boolean 골드 승인, 구체적인 시각, 사용자 증거 및 UNRESOLVED 사유 등을 필수로 요구하고 승인 여부로 적격성을 계산한다. 이번 제출에는 골드 승인이 미결정이며 시각과 추가 근거를 제공하지 않았다. 이를 채우기 위해 false를 승인 미결정으로 오기하거나, 사용자가 작성하지 않은 이유·증거·시각을 만들지 않았다.

따라서 기존 정책/스키마를 변경하지 않고 **별도 user_final_submission_recorded 이벤트**를 추가했다. 해시 체인은 기존 `user_review_v1/workflow.py`의 event_digest를 그대로 재사용한다. 기존 준비된 workflow나 human-response-forms.json에 이벤트를 주입하지 않는다. 이 기록은 사용자 최종 판단의 정식 추가 이력이나 기존 워크플로 승인 이벤트·골드 적격성의 대체물이 아니다. 승인 단계는 별도 명시적 사용자 요청 없이는 진행하지 않는다.

## 검증과 이력 보존

```sh
python3 evaluation/golden_expansion/user_final_2026_11_11/validate_submission.py
python3 -m unittest discover -s evaluation/golden_expansion/user_final_2026_11_11 -v
python3 evaluation/golden_expansion/codex_counterreview_2026_11_11/validate.py
```

검증은 기존 파일과 신규 manifest를 먼저 검사하고 17건 범위·중복·수집 순서·사용자 제출값·초기 판단 차이·입력/AI 참조·이벤트 체인·null 승인·출처 분리를 확인한다. 어떠한 결과물도 수정하지 않는다. 수정·삭제된 이벤트는 실패하며 이전 기록으로 복구하거나 덮어쓰지 않는다. 향후 정정이 필요하면 새 제출 이력을 추가하고 원래 파일은 남겨야 한다. manifest 자체는 Git 검수에 묶인 변경 탐지 수단이며 공격자가 코드·해시·Git 기준까지 모두 바꾼 상황의 인증을 보증하지 않는다.

검수자는 사용자 제출 전사와 참조 원본을 확인해야 한다. 기존 최종 승인 정책과 다른 별도 제출 스키마이며, 골드 포함 승인은 전 사례 미결정이라는 점을 주의한다. PR #25는 변경하지 않고 그 브랜치를 기반으로 한 스택 PR에서 검수한다.

실행 검증 결과: 전체 회귀 16개 디렉터리 / 624개 테스트 통과. 상세 출력은 regression-results.json에 보존했다.

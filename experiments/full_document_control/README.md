# 전체 문서 처리 및 실행 제어 프로토타입

상태: **전체 Markdown 문서 스냅샷의 블록 범위 관리, 독립 검증 게이트, 단계 실행 제어를 시험하는 실행 가능한 프로토타입**. 정식 공통 스키마 동결, Information Organization / Expression Refinement 본구현, 자동 의미 검증 엔진, 문서 전달 승인을 뜻하지 않는다.

## 목적과 해결하려는 구조적 한계

기존 실험([최소 검증 게이트](../minimal_gate/README.md), [정보 추출·분석](../extraction_analysis/README.md), [추출·평가 분리 A/B](../extraction_ab/README.md))은 발췌문 단위로 동작했기 때문에 문서 전체의 누락 여부를 관리하지 못했고, 특정 프롬프트나 2단계 분리의 우월성도 입증되지 않았다.

이 프로토타입은 프롬프트 지시문에 의존하는 대신 **프로그램이 문서 범위와 단계 전환을 강제**하는 두 가지 구조를 구현한다.

1. **전체 Markdown 문서 스냅샷 처리 (`DocumentSnapshot` → 블록 분할 → 정보 추출·통합):**
   - 원문 전체와 UTF-8 SHA-256 다이제스트를 고정(`coverage: "complete"`)하고, 0부터 시작하는 유니코드 코드 포인트 반개구간 `[start, end)`으로 제목(`heading`), 문단(`paragraph`), 표(`table`), 코드 블록(`code_block`), 목록(`list`), 인용(`blockquote`)과 비대상 구분자(`blank`, `thematic_break`), 미지원 문법(`unsupported`)을 빈틈·겹침 없이 분할한다.
   - 제외 블록에는 `exclusion_reason`을 남기고, 미지원 문법(예: 닫히지 않은 코드 펜스, 원시 HTML 블록, 각주/링크 정의 등)은 조용히 버리거나 완료로 처리하지 않고 `unsupported`(`unresolved`)로 기록한다.
   - 문맥 길이에 맞춰 여러 창(window)으로 나누더라도 각 창은 단일 `DocumentSnapshot` 다이제스트와 블록 개요를 유지하며 독립된 문서처럼 취급하지 않는다. 이때 전체 원문을 매 호출마다 반복 전달하지 않고 인접 블록·상위 제목 문맥만 포함해 렌더링된 프롬프트 전체 크기(`max_prompt_chars`)를 엄격히 제한하며, 단일 블록이 예산을 초과하면 무제한 전달하지 않고 `OVERSIZED_BLOCK_EXCEEDS_PROMPT_BUDGET`(`unresolved` → `REVIEW`)으로 명시적 보류한다. 또한 분할된 창 사이의 교차 관계를 별도 사후 통합(`build_cross_window_relation_prompt` / `cross_window_relations_raw`)으로 연결할 수 있다.
   - 블록 내부 및 블록 경계를 가로지르는 주장·조건 관계(`qualifies`, `depends_on`, `supports` 등)와 계약상 필수 보호 정보(`required_information`)를 문서 전체 단위 목록(`units`), `requirement_bindings`, `coverage_ledger`로 통합한다. 보호 조건 연결(`requires_condition_link`)은 조건 요소 스팬이 단위 스팬 내부에 속하는지, 관계 방향(`조건 --qualifies--> 주장` 또는 `주장 --depends_on--> 조건`)과 실질 주장 단위 여부, 관계 이유(`reason`) 및 출처 어휘 앵커 대응을 검증하되, 이를 의미적 진실의 증명으로 주장하지 않고(`structural_correspondence_only_not_semantic_proof`) 모호한 연결은 `unresolved`(`REVIEW`)로 보류한다.
   - **전체 블록을 처리했다는 범위 추적(`BLOCK_COVERAGE`)과 의미 정보를 올바르게 추출했다는 판단(`SEMANTIC_FIDELITY`)을 엄격히 구별한다.**

2. **독립 검증 게이트와 단계 실행 제어 (`Validation Gate` + `ExecutionController`):**
   - 고정된 `ValidationPlan`(`SNAPSHOT_AND_CONTRACT`, `BLOCK_COVERAGE`, `UNIT_AND_SPAN_INTEGRITY`, `PROTECTED_TRACEABILITY`, `SEMANTIC_FIDELITY`)에 따라 각 필수 검사의 실행 여부·버전·산출물 다이제스트를 대조하며, 호출자가 임의로 변조·약화한 `ValidationPlan`(`UNAUTHORIZED_VALIDATION_PLAN_OVERRIDE`)을 거부한다.
   - 외부에서 전달된 `ValidationReport`의 `gate_state`, `delivery_approved`, `next_stage_allowed`, 개별 검사 상태(`SEMANTIC_FIDELITY: "passed"` 등)나 재계산된 SHA-256 다이제스트만으로 후속 단계 진입을 승인하지 않는다. `can_advance_to_organization()` 및 `OrganizationBoundaryAdapter`는 진입 직전에 `analysis_sha256`·`plan_sha256`·`report_sha256` 내용 무결성을 검증하고 신뢰 가능한 입력·계약·분석 결과를 바탕으로 독립 검증 게이트를 재수행해 위조된 검사 결과(`FORGED_OR_TAMPERED_CHECK_RESULTS`)를 차단한다.
   - 모델 출력에 포함된 자기승인(`gate_state: "PASS"`, `delivery_approved: true`) 시도는 무결성 위반(`FAIL`)으로 거부한다.
   - 결정론적 구조·참조·보호 정보 검사가 모두 통과해도 `SEMANTIC_FIDELITY`가 미검증(`not_run` 또는 `unresolved`)이면 항상 `REVIEW`(`delivery_approved: false`, `next_stage_allowed: false`)를 유지한다.
   - `ExecutionController`와 다음 단계 경계 어댑터(`OrganizationBoundaryAdapter`)는 `PASS` 외 모든 상태(`REVIEW`, `FAIL`, `STOPPED`)의 후속 단계 진입을 코드로 차단한다.
   - 모델/제공자 호출 실패(비정상 종료 코드, 타임아웃, 잘못된 JSON, 다중 창 부분 실행 실패)를 구조화된 예외 처리로 포착해 워크플로가 비제어 예외로 중단되지 않도록 보장한다. 이전 성공 창(`completed_window_ids`)과 실패 창(`failed_window_id`)의 실행 기록(`window_records`), 응답 다이제스트, 종료 코드/타임아웃 여부를 보존하고 원시 오류 문자열의 비밀정보(토큰, API 키, 비밀번호 등)를 마스킹(`[REDACTED]`)한다.
   - 입력 스냅샷·작성 계약·검증 계획이 바뀌면 기존 분석 및 검증 보고서를 즉시 무효화(`invalidation_log`)하고 재사용을 거부한다.
   - 재시도 횟수 상한(`max_attempts`)을 강제하며, 한도 도달 시 마지막 결함 상태(`last_gate_state: "FAIL"`)와 복귀 대상 단계(`return_to_stage`), 실패 근거를 보존한 채 `STOPPED`로 종료한다.

## 실행 방법

저장소 루트에서 Python 3 표준 라이브러리만으로 실행한다.

### 1. 프롬프트 확인

```bash
python3 experiments/full_document_control/pipeline.py prompt experiments/full_document_control/sample_input.json
```

### 2. 단위·E2E 회귀 테스트 및 실제 모델 CLI 파이프라인 실행

```bash
# 단위·E2E 회귀 테스트 실행 (9개 필수 시나리오 포함)
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py' -v

# 로컬 Antigravity CLI(agy)를 통한 실제 모델 호출 및 게이트·제어 실행
python3 experiments/full_document_control/pipeline.py run \
  --input experiments/full_document_control/sample_input.json \
  --provider agy \
  --model gemini-4-argon-medium \
  --max-attempts 1 \
  --save-run-dir experiments/full_document_control/runs/new-run
```

`runs/` 디렉터리는 `.gitignore`로 제외하며 원시 프롬프트·응답·메타데이터·결과 보고서를 로컬에 보존한다.

## 실제 실행 결과 (`FD-001`)

`sample_doc.md`(길이 476 코드 포인트, UTF-8 SHA-256 `9bd99e83dfb7f100e4ca90cf1ac03eaeb3ca8572e8c8774c5883164b4240d7fd`) 및 `sample_input.json`을 대상으로 로컬 `agy` CLI(`gemini-4-argon-medium`, plan mode, text output)를 호출해 전체 파이프라인을 실행했다.

- 프롬프트 SHA-256: `38f59df8755eb22fc518fe0366c0ba7abfc6e55b0b27dbdc0680da064d4dc5dc`
- 원시 응답 SHA-256: `07d29dfc66eddfad4b118942079dbf0794b6040ac8519444b7d457ab39226d92` (종료 코드 `0`, 49.90초)
- 블록 처리: 전체 15개 블록(`heading` 3, `paragraph` 1, `table` 1, `code_block` 1, `list` 1, `thematic_break` 1, `blank` 7)이 `[0, 476)` 구간에 빈틈·겹침 없이 분할되었고, 추출 대상 7개 블록 모두에서 총 10개 정보 단위가 추출되었다.
- 블록 간 관계: `B015` 목록의 오프라인 캐시 조건(`U009`)이 `B003` 문단의 로컬 실행 주장(`U002`)을 `qualifies`로 한정하고, `B015`의 macOS 수동 재설치 제약(`U010`)이 `B007` 표의 macOS 패키지 항목(`U006`)을 `qualifies`로 한정하는 등 블록 간 관계 6건이 원문 스팬과 함께 연결되었다.
- 검증 게이트 및 실행 제어:
  - `SNAPSHOT_AND_CONTRACT`: `passed`
  - `BLOCK_COVERAGE`: `passed`
  - `UNIT_AND_SPAN_INTEGRITY`: `passed`
  - `PROTECTED_TRACEABILITY`: `passed` (계약상 필수 보호 항목 6건 모두 요소·스팬·조건 관계 추적 확인)
  - `SEMANTIC_FIDELITY`: `unresolved` (미해결 질문 2건 및 독립 의미 검수 미실행)
  - 최종 상태: `gate_state: "REVIEW"`, `delivery_approved: false`, `next_stage_allowed: false`, `next_stage_invoked: false`, `return_to_stage: "human_or_semantic_review"`

## 검증 시나리오 요약

`test_pipeline.py`는 다음 9개 필수 시나리오와 경계 조건을 검증한다.

1. 정상적인 문서 전체 입력과 `[0, len(content))` 무누락·비겹침 블록 범위 추적
2. 일부 추출 대상 블록 누락(`missing`) 및 중복 처리(`duplicate`) 시 `BLOCK_COVERAGE` 실패
3. 서로 다른 블록에 위치한 주장과 조건 연결 및 다중 창(window) 분할 시 관계 보존
4. 표(`B007`), 코드 블록(`B009`), 목록(`B015`)에 포함된 필수 버전·패키지·명령·조건 추출 및 추적
5. 잘못된 출처 인용/오프셋 참조 및 필수 보호 정보 누락·무단 생략(`omit_candidate`) 차단
6. 필수 검사 결과 행 누락(`CHECK_RESULT_MISSING`) 시 `STOPPED` 전환 및 스푸핑된 `PASS` 거부
7. 입력 스냅샷 또는 작성 계약 변경 후 이전 검증 보고서 재사용 시도 무효화(`STALE_VALIDATION_REPORT_INVALIDATED`)
8. 실패(`FAIL`), 중단(`STOPPED`), 미검증(`REVIEW`) 분석 결과의 `OrganizationBoundaryAdapter` 진입 차단 및 유한 재시도 상한(`max_attempts`) 강제
9. 결정론적 구조 검사 4종이 모두 `passed`여도 `SEMANTIC_FIDELITY`가 `not_run`/`unresolved`이면 `REVIEW`로 남아 의미적 `PASS`로 오인되지 않음을 확인
10. **P1-1 (보고서 위조·변조 방어):** `SEMANTIC_FIDELITY: "passed"` 위조 및 `report_sha256` 재계산, 분석 본문 변조 후 다이제스트 재계산, 필수 검사를 제외한 임의 `ValidationPlan` 교체, `OrganizationBoundaryAdapter` 직접 호출 우회 시도를 모두 독립 재검증으로 차단
11. **P1-2 (전체 프롬프트 문맥 예산 제한):** 긴 문서 다중 창 분할 시 지시문·계약·블록 개요·인접 문맥·대상 블록을 포함한 전체 프롬프트 길이(`max_prompt_chars`) 준수, 초대형 단일 블록 명시적 보류(`OVERSIZED_BLOCK_EXCEEDS_PROMPT_BUDGET` → `REVIEW`), 창 간 관계 사후 통합(`build_cross_window_relation_prompt`) 검증
12. **P2-1 (모델 호출 실패 구조화 처리):** 제공자 비정상 종료, 타임아웃, 다중 창 부분 실행 실패(`W001` 성공 후 `W002` 실패), 원시 오류 로그 내 비밀정보 마스킹(`[REDACTED]`) 및 재시도 상한 준수 검증
13. **P2-2 (보호 조건 연결 대응 검증):** 무관한 `supports` 관계, 제목 블록/역방향 `qualifies` 연결, 단위 스팬 외부의 요소 스팬(`ELEMENT_SPAN_NOT_IN_UNIT_SPAN`), 근거 없는 관계 이유(`FAIL`) 및 출처 어휘 앵커 미공유 모호 연결(`unresolved` → `REVIEW`) 구분 검증

## 한계

- 프롬프트 예산(`max_prompt_chars`)은 오프라인에서 제공자별 토크나이저를 직접 호출하지 않으므로 유니코드 코드 포인트 길이를 기준으로 상한을 강제하며(`budget_policy.token_vs_char_policy`), 한국어·UTF-8 다중 토큰 특성을 고려해 보수적으로 설정해야 한다.

- 블록 전체 범위와 필수 문자열·관계 연결이 확인되어도 정규화된 문장(`statement`)이나 판단 이유(`reason`/`exposure`)에서 발생하는 미묘한 의미 왜곡·주장 범위 확대를 결정론적 검사만으로 완벽히 잡아낼 수는 없으므로 `SEMANTIC_FIDELITY`를 자동 `PASS`로 처리하지 않는다.
- 현재 Markdown 파서는 줄 단위 블록 구조(제목, 문단, 파이프 표, 펜스 코드 블록, 목록, 인용, 구분선, 공백)를 다루며, 중첩 복합 구조나 원시 HTML/각주 등은 `unsupported`로 분류해 사람 검토(`REVIEW`)로 보류한다.
- Information Organization 및 Expression Refinement의 실제 편집 로직은 포함하지 않으며, 경계 어댑터(`OrganizationBoundaryAdapter`)로 단계 전환 통제만 검증한다.

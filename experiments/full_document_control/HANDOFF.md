# HANDOFF — 전체 문서 처리 및 실행 제어 프로토타입 (PR #10 보완 완료)

- **브랜치:** `prototype/full-document-control`
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** PR #10 코드 검토 보완 항목 (`P1-1`, `P1-2`, `P2-1`, `P2-2`) 구현 및 재검증 완료

## 단계 계획 및 보완 이력

1. **Stage 1–4 (초기 구현 완료):** 전체 Markdown 문서 스냅샷(`DocumentSnapshot`), 비겹침·무누락 블록 분할기, 독립 검증 게이트(`ValidationGate`), 단계 실행 제어기(`ExecutionController`), `OrganizationBoundaryAdapter`, 로컬 `agy` CLI 실제 실행(`runs/FD-001-live/`) 및 Draft PR #10 생성
2. **PR #10 보완 1 (`P1-1`, `P2-2` 완료):**
   - `P1-1`: `verify_self_digest()`, `verify_canonical_plan_policy()` 추가 및 `can_advance_to_organization()` / `OrganizationBoundaryAdapter.enter_organization_stage()`에서 후속 단계 진입 직전 독립 검증 게이트(`validate_analysis_gate`) 재수행. 외부에서 주입·위조된 `SEMANTIC_FIDELITY: "passed"`, 변조 후 재계산된 `analysis_sha256`/`report_sha256`, 약화된 `ValidationPlan` 교체 시도를 모두 `FAIL`로 차단.
   - `P2-2`: `_evaluate_condition_link()` 및 `_element_spans_within_unit_spans()`로 조건 요소 스팬의 단위 스팬 포함 여부(`ELEMENT_SPAN_NOT_IN_UNIT_SPAN`), 유효한 관계 방향(`조건 --qualifies--> 주장` 또는 `주장 --depends_on--> 조건`), 실질 주장 단위(`_is_substantive_claim_unit`), 관계 이유(`reason`) 및 출처 어휘 앵커 대응을 검증. 모호한 연결은 `unresolved`(`REVIEW`)로 보류하며 구조적 대응 확인(`structural_correspondence_only_not_semantic_proof`)을 의미적 진실 증명으로 주장하지 않음.
3. **PR #10 보완 2 (`P1-2`, `P2-1` 완료):**
   - `P1-2`: `plan_extraction_windows()` 및 `build_window_prompt()`에서 지시문·계약·블록 개요·인접 문맥·대상 블록을 포함한 실제 렌더링 프롬프트 전체 크기 상한(`max_prompt_chars`) 강제. 전체 원문을 매 호출에 반복하지 않고 인접 블록과 상위 제목만 제한적으로 포함하며, 단일 블록이 예산을 초과하면 무제한 전달하지 않고 `oversized_block_ids`(`OVERSIZED_BLOCK_EXCEEDS_PROMPT_BUDGET` → `unresolved` → `REVIEW`)로 보류. 다중 창 분할 시 창 간 조건·의존 관계를 연결하는 `build_cross_window_relation_prompt()` 및 `cross_window_relations_raw` 통합 경로 추가. 문자 수 예산과 토큰 예산의 차이를 `budget_policy`에 명시.
   - `P2-1`: `ExecutionController.run()` 내부 `model_responder` 호출을 구조화된 예외 처리로 감싸 제공자 비정상 종료(`MODEL_PROVIDER_EXIT_ERROR`), 타임아웃(`MODEL_CALL_TIMEOUT`), 잘못된 응답(`MODEL_RESPONSE_PARSE_ERROR`), 다중 창 부분 실행 실패 시 비제어 예외 없이 `STOPPED` 반환. 이전 성공 창 기록(`completed_window_ids`, `window_records`)과 실패 창/단계·응답 다이제스트·종료 코드를 보존하고, `sanitize_error_text()`로 원시 로그 내 비밀정보(Bearer 토큰, API 키, 비밀번호 등)를 마스킹(`[REDACTED]`).

## 변경 파일

- `experiments/full_document_control/.gitignore`
- `experiments/full_document_control/HANDOFF.md`
- `experiments/full_document_control/README.md`
- `experiments/full_document_control/pipeline.py`
- `experiments/full_document_control/sample_doc.md`
- `experiments/full_document_control/sample_input.json`
- `experiments/full_document_control/test_pipeline.py`

## 커밋

- `e7759d2`: prototype: implement full-document snapshot partitioning and extraction aggregation
- `4cd8320`: prototype: add independent validation gate and plan reconciliation
- `0a0f002`: prototype: implement stage execution controller, boundary adapter, and E2E tests
- `ac5fedb`: docs: add full-document control README, handoff record, and live execution summary
- `00e5346`: fix(full-document-control): prevent gate bypass via report forgery and tighten condition link verification (P1-1, P2-2)
- PR #10 보완 커밋 2: 프롬프트 문맥 예산 상한 강제, 모델 호출 실패 구조화 처리 및 문서 갱신 (`P1-2`, `P2-1`)

## 테스트 결과

- 총 104개 테스트 통과 (`full_document_control` 29개, `minimal_gate` 31개, `extraction_analysis` 27개, `extraction_ab` 17개)

## 미해결 문제

- 없음 (독립 의미 검증기는 미구현 상태이며, 외부 보고서가 `SEMANTIC_FIDELITY: passed`를 위조 제출하더라도 독립 재검증으로 `FAIL` 차단하고 정상 구조 통과 시 `REVIEW`로 보류함)

## 다음 작업

- 보완 커밋을 `origin/prototype/full-document-control`에 푸시하고 Draft PR #10 본문을 갱신한 뒤 사용자 검토 대기 (병합하지 않음)

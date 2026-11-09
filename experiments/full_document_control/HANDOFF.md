# HANDOFF — 전체 문서 처리 및 실행 제어 프로토타입

- **브랜치:** `prototype/full-document-control`
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** Stage 2 완료 → Stage 3 진행 예정 (총 4단계)

## 단계 계획

1. **Stage 1 (완료):** 전체 Markdown 문서 스냅샷(`DocumentSnapshot`), 비겹침·무누락 블록 분할기, 블록/창(window) 단위 정보 추출 및 전체 문서 통합(`AnalysisResult`)
2. **Stage 2 (완료):** 독립 검증 게이트(`ValidationGate`) 및 고정 `ValidationPlan` 대조기(`reconcile_validation_plan`)
3. **Stage 3:** 단계 실행 제어기(`ExecutionController`), 산출물 무효화, 유한 재시도 제어, 다음 단계 경계 어댑터(`OrganizationBoundaryAdapter`), CLI
4. **Stage 4:** 9개 필수 시나리오 E2E/회귀 테스트, 실제 Markdown 문서 실행 검증, `README.md` 정리 및 Draft PR 생성

## 완료 사항

- `pipeline.py` Stage 2 구현:
  - `build_validation_plan`: 버전 고정 `ValidationPlan`(`SNAPSHOT_AND_CONTRACT`, `BLOCK_COVERAGE`, `UNIT_AND_SPAN_INTEGRITY`, `PROTECTED_TRACEABILITY`, `SEMANTIC_FIDELITY`) 생성
  - `reconcile_validation_plan`: 예상 필수 검사와 실제 검사 결과 행의 완전성·검사 버전 일치·산출물 다이제스트 일치 대조, `CHECK_RESULT_MISSING` 시 `STOPPED` 및 `last_gate_state: "FAIL"` 보존
  - `validate_analysis_gate`: 분석 모듈과 독립적으로 입력·계약·스냅샷 다이제스트, 전체 블록 처리 범위(누락·중복·미지원 블록), 단위/요소/출처 스팬 무결성, 필수 보호 정보·조건 연결 추적성을 검증하고 의미 검증 미수행 시 항상 `REVIEW`(`delivery_approved: False`) 유지 및 자기승인 시도 차단

## 변경 파일

- `experiments/full_document_control/pipeline.py`
- `experiments/full_document_control/test_pipeline.py`
- `experiments/full_document_control/HANDOFF.md`

## 커밋

- `e7759d2`: prototype: implement full-document snapshot partitioning and extraction aggregation
- Stage 2 커밋: 독립 검증 게이트 및 ValidationPlan 대조 구현

## 테스트 결과

- 총 83개 테스트 통과 (Stage 1~2 신규 8개 + 기존 실험 75개)

## 미해결 문제

- 없음

## 다음 작업

- Stage 3 구현: `OrganizationBoundaryAdapter`, `ExecutionController`(재시도 상한, 실패 원인/단계 복귀 기록, 입력·계약 변경 시 기존 검증 결과 무효화, `REVIEW`/`FAIL`/`STOPPED` 시 다음 단계 차단), CLI 및 Markdown 렌더러 추가 후 커밋

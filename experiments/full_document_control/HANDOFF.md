# HANDOFF — 전체 문서 처리 및 실행 제어 프로토타입

- **브랜치:** `prototype/full-document-control`
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** Stage 3 완료 → Stage 4 진행 예정 (총 4단계)

## 단계 계획

1. **Stage 1 (완료):** 전체 Markdown 문서 스냅샷(`DocumentSnapshot`), 비겹침·무누락 블록 분할기, 블록/창(window) 단위 정보 추출 및 전체 문서 통합(`AnalysisResult`)
2. **Stage 2 (완료):** 독립 검증 게이트(`ValidationGate`) 및 고정 `ValidationPlan` 대조기(`reconcile_validation_plan`)
3. **Stage 3 (완료):** 단계 실행 제어기(`ExecutionController`), 산출물 무효화, 유한 재시도 제어, 다음 단계 경계 어댑터(`OrganizationBoundaryAdapter`), CLI, 9개 필수 E2E/회귀 테스트
4. **Stage 4:** 실제 모델 CLI 실행 확인, `README.md` 작성, 최종 Git/테스트 상태 검증 및 Draft PR 생성

## 완료 사항

- `pipeline.py` Stage 3 구현:
  - `can_advance_to_organization`: 다음 단계(`Information Organization`) 전달 조건을 코드로 정의하고 `ValidationPlan` 재대조 및 상류 산출물 변경 감지 수행
  - `OrganizationBoundaryAdapter`: 미구현 Organization 모듈 대신 호출 여부·차단 시도를 관측하고 `PASS` 외 모든 상태(`REVIEW`, `FAIL`, `STOPPED`) 및 무효화된 보고서의 진입을 차단
  - `ExecutionController`: `DocumentSnapshot → Extraction & Analysis → Validation Gate → Next Stage 판단` 흐름 제어, `max_attempts` 재시도 상한 및 초과 시 `STOPPED`(`last_gate_state` 보존), 실패 원인 및 `return_to_stage` 기록, 입력·계약·계획 변경 시 `invalidation_log` 기록 및 기존 검증 결과 무효화
  - CLI(`prompt`, `run`) 및 안전한 들여쓰기 블록 기반 Markdown 보고서 렌더러(`render_markdown_report`) 추가
- `test_pipeline.py` Stage 3 & 4 필수 9개 E2E 시나리오 및 CLI 테스트 작성 완료 (총 93개 테스트 통과)

## 변경 파일

- `experiments/full_document_control/pipeline.py`
- `experiments/full_document_control/test_pipeline.py`
- `experiments/full_document_control/HANDOFF.md`

## 커밋

- `e7759d2`: prototype: implement full-document snapshot partitioning and extraction aggregation
- `4cd8320`: prototype: add independent validation gate and plan reconciliation
- Stage 3 커밋: 단계 실행 제어기, Organization 경계 어댑터 및 9개 필수 E2E 테스트 추가

## 테스트 결과

- 총 93개 테스트 통과 (신규 18개 + 기존 실험 75개)

## 미해결 문제

- 없음

## 다음 작업

- Stage 4: `sample_input.json` 대상 실제 CLI/모델 파이프라인 실행 확인(`runs/` 아래 로컬 보존), `experiments/full_document_control/README.md` 작성, `HANDOFF.md` 최종 갱신 후 커밋 및 Draft PR 생성

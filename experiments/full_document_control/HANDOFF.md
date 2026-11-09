# HANDOFF — 전체 문서 처리 및 실행 제어 프로토타입

- **브랜치:** `prototype/full-document-control`
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** Stage 1 완료 → Stage 2 진행 예정 (총 4단계)

## 단계 계획

1. **Stage 1 (완료):** 전체 Markdown 문서 스냅샷(`DocumentSnapshot`), 비겹침·무누락 블록 분할기, 블록/창(window) 단위 정보 추출 및 전체 문서 통합(`AnalysisResult`)
2. **Stage 2:** 독립 검증 게이트(`ValidationGate`) 및 고정 `ValidationPlan` 대조기(`reconcile`)
3. **Stage 3:** 단계 실행 제어기(`ExecutionController`), 산출물 무효화, 유한 재시도 제어, 다음 단계 경계 어댑터(`OrganizationBoundaryAdapter`), CLI
4. **Stage 4:** 9개 필수 시나리오 E2E/회귀 테스트, 실제 Markdown 문서 실행 검증, `README.md` 정리 및 Draft PR 생성

## 완료 사항

- `sample_doc.md` 및 `sample_input.json` 작성 (완전한 Markdown 문서 스냅샷, 제목·문단·표·코드 블록·구분선·목록, 블록 간 조건·의존성, 필수 보호 정보 6건 포함)
- `pipeline.py` Stage 1 구현:
  - `validate_input_bundle`: 완전 스냅샷(`coverage == "complete"`), UTF-8 SHA-256 다이제스트, 계약 필수 필드·출력 범위·필수 보호 항목 검증
  - `parse_markdown_blocks` / `verify_block_partition`: `[0, len(content))` 전체 범위를 빈틈·겹침 없이 분할하고 추출 대상(`heading`, `paragraph`, `table`, `code_block`, `list`, `blockquote`), 제외 대상(`blank`, `thematic_break` + `exclusion_reason`), 미지원 구조(`unsupported` + `unsupported_reason`)를 구분
  - `plan_extraction_windows` / `build_window_prompt` / `assemble_document_analysis`: 문맥 길이 분할 시에도 단일 문서 스냅샷·전체 블록 개요를 유지하고, 블록별 인용 오프셋·블록 간 관계(`cross_block`)·요구사항 바인딩·전체 블록 `coverage_ledger`를 통합하며 `semantic_fidelity: "not_run"`과 `delivery_approved: False`를 유지

## 변경 파일

- `experiments/full_document_control/.gitignore`
- `experiments/full_document_control/HANDOFF.md`
- `experiments/full_document_control/sample_doc.md`
- `experiments/full_document_control/sample_input.json`
- `experiments/full_document_control/pipeline.py`
- `experiments/full_document_control/test_pipeline.py`

## 커밋

- Stage 1 커밋: 전체 문서 스냅샷·블록 분할·정보 추출 통합 구현

## 테스트 결과

- 총 79개 테스트 통과 (Stage 1 신규 4개 + 기존 실험 75개)

## 미해결 문제

- 없음

## 다음 작업

- Stage 2 구현: `pipeline.py`에 독립 `ValidationGate`(`ValidationPlan`, `reconcile_validation_plan`, `validate_analysis_gate`) 추가 및 `test_pipeline.py`에 Stage 2 검증 게이트 테스트 작성 후 커밋

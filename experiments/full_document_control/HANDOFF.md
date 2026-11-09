# HANDOFF — 전체 문서 처리 및 실행 제어 프로토타입

- **브랜치:** `prototype/full-document-control`
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** Stage 4 완료 (전 단계 완료)

## 단계 계획

1. **Stage 1 (완료):** 전체 Markdown 문서 스냅샷(`DocumentSnapshot`), 비겹침·무누락 블록 분할기, 블록/창(window) 단위 정보 추출 및 전체 문서 통합(`AnalysisResult`)
2. **Stage 2 (완료):** 독립 검증 게이트(`ValidationGate`) 및 고정 `ValidationPlan` 대조기(`reconcile_validation_plan`)
3. **Stage 3 (완료):** 단계 실행 제어기(`ExecutionController`), 산출물 무효화, 유한 재시도 제어, 다음 단계 경계 어댑터(`OrganizationBoundaryAdapter`), CLI, 9개 필수 E2E/회귀 테스트
4. **Stage 4 (완료):** 실제 모델 CLI 실행 확인, `README.md` 작성, 최종 Git/테스트 상태 검증 및 Draft PR 생성

## 완료 사항

- `sample_doc.md` 및 `sample_input.json` 대상 로컬 `agy` CLI(`gemini-4-argon-medium`) 실제 호출 파이프라인 실행 완료:
  - 프롬프트 SHA-256: `38f59df8755eb22fc518fe0366c0ba7abfc6e55b0b27dbdc0680da064d4dc5dc`
  - 원시 응답 SHA-256: `07d29dfc66eddfad4b118942079dbf0794b6040ac8519444b7d457ab39226d92`
  - 15개 전체 블록 무누락 분할, 7개 추출 대상 블록에서 10개 단위 및 블록 간 관계 6건 추출, 결정론적 검사 4종 `passed`, `SEMANTIC_FIDELITY: unresolved`, 최종 `gate_state: REVIEW`, `next_stage_invoked: False` 확인 (`runs/FD-001-live/`에 로컬 보존, Git 제외)
- `experiments/full_document_control/README.md` 작성 완료
- 전체 테스트(신규 18개 + 기존 75개 = 93개) 통과 및 기존 파일 무변경 확인

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
- Stage 4 커밋: 문서화(`README.md`, `HANDOFF.md`) 및 실제 실행 결과 정리

## 테스트 결과

- 총 93개 테스트 통과 (`full_document_control` 18개, `minimal_gate` 31개, `extraction_analysis` 27개, `extraction_ab` 17개)

## 미해결 문제

- 없음 (구조·범위·보호 정보 검사와 별개로 의미적 정확성 자동 판정은 미구현 상태이며 정책대로 `REVIEW`로 다음 단계 진행을 차단함)

## 다음 작업

- Draft PR 생성 후 사용자 검토 대기 (병합하지 않음)

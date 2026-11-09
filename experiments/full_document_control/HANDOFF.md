# HANDOFF — 의미 충실도 검증기(Semantic Fidelity Validator) 구현 완료

- **브랜치:** `prototype/semantic-fidelity-validator` (기준: `main` `490e714`)
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** 의미 충실도 검증기(`SemanticFidelityValidator`), 14개 고정 벤치마크 평가 세트(`semantic_eval_cases.py`), 종합 테스트(`test_semantic_validator.py`), 기존 테스트 108개 호환성 유지(총 125개 테스트 통과), Validation Gate 및 ExecutionController 연동 완료.

## 주요 구현 내용

1. **독립 의미 검증기 (`experiments/full_document_control/semantic_validator.py`):**
   - 정보 추출 모듈이 자기 결과를 승인하지 않도록 평가 경계 분리.
   - **양방향 검사:**
     - `analysis_to_source`: 추출 단위 statement, elements, relations, assessment(reason, exposure, preservation)의 의미 왜곡 검사.
     - `source_to_analysis`: DocumentSnapshot 블록 내 절/조건 단위 역방향 누락 검사(`CRITICAL_OMISSION`).
   - **8대 의미 오류 범주 및 보류 탐지:**
     1. `CLAIM_OVERSTATEMENT`: 요구사항/계획(`needs to`, `can still be added later`, 초기 실험 빌드 등)을 검증된 패키지/런타임 동작 사실로 왜곡하는 오류(RW-001 A/B E-REQ-A1/A2 핵심 회귀 방지).
     2. `POLARITY_REVERSAL`: 긍정/부정, 가능/불가능, 지원/미지원, 차단/비차단 반전.
     3. `CONDITION_LOSS`: 릴리스 범위 조건(`For this release`), 캐시 조건 생략 및 일반화, 한정 조건 단위의 부당한 `omit_candidate` 생략.
     4. `QUANTITY_OR_SCOPE_DISTORTION`: 수치·단위(30초→30분), 버전, 포트 번호, 비교/적용 대상(Ubuntu↔macOS, PKG↔DMG) 왜곡.
     5. `UNSUPPORTED_ADDITION`: 원문에 없는 암호화(AES-256), 자동 복구 데몬(systemd), 정량 성능 향상 수치 조작.
     6. `CRITICAL_OMISSION`: 원문 블록 내 필수 조건·한계 절의 추출 결과 누락.
     7. `RELATION_DISTORTION`: 관계 종류 왜곡, 결론→전제 supports 역방향 연결(RW-001 E-REL-A1/A2), 역방향 qualifies, 근거 앵커 미공유.
     8. `ASSESSMENT_RATIONALE_DISTORTION`: 단위 statement는 정확하더라도 `assessment.exposure`나 `assessment.reason`에서만 의미를 확대하는 오류(RW-001 E-REQ-B2 회귀 방지).
     9. `AMBIGUOUS_SOURCE_EVIDENCE` / `UNVERIFIED_EVALUATOR_QUOTE` / `EVALUATOR_JUDGMENT_CONFLICT` / `INCOMPLETE_SEMANTIC_COVERAGE` → `unresolved`(`REVIEW`).
   - **평가자 인용구 및 필드 경로 코드 재검증:**
     - 모델 평가자가 제출한 모든 인용구를 `resolve_block_quotes()`를 통해 원본 `DocumentSnapshot` 코드 포인트 구간에 대해 엄격히 재검증. 조작되거나 일치하지 않는 인용구는 `UNVERIFIED_EVALUATOR_QUOTE`로 보류.
     - 모든 필드 경로는 RFC 6901 JSON Pointer로 `AnalysisResult`에 실제 존재하는지 재검증.
   - **자기승인 거부 및 1차 구현 자동 PASS 금지 불변조건:**
     - 모델이 `passed: true`, `delivery_approved: true`, `gate_state: "PASS"`를 출력해도 무단 승인 시도(`UNAUTHORIZED_EVALUATOR_APPROVAL_CLAIM`)로 거부(`FAIL`).
     - 첫 구현 정책에 따라 모든 항목이 `supported`로 판정되어도 자동 `PASS`하지 않고 `REVIEW`(`SEMANTIC_SUPPORTED_AWAITING_APPROVAL`) 상태를 유지하여 독립적인 사람/정책 검토를 강제.
   - **다중 창 프롬프트 예산 상한 및 미검토 범위 추적:**
     - `max_prompt_chars` 상한 내에서 의미 검토 창을 분할하고, 예산 초과나 응답 누락으로 검토되지 못한 단위/블록은 `INCOMPLETE_SEMANTIC_COVERAGE`(`unresolved` → `REVIEW`)로 기록.
   - **위·변조 방어 및 업스트림 산출물 무효화:**
     - `SemanticFidelityReport`에 SHA-256 자기 다이제스트(`semantic_report_sha256`) 및 업스트림 산출물(`input_sha256`, `contract_sha256`, `snapshot_sha256`, `analysis_sha256`) 바인딩 강제.
     - 원문, 계약, 분석 결과가 변경되면 기존 의미 검증 결과는 `STALE_SEMANTIC_REPORT_INVALIDATED`로 즉시 무효화.
     - 독립 결정론적 의미 감사를 항상 병행 재수행하여, 위조된 외부 보고서가 결정론적 오류를 은폐할 수 없도록 차단.

2. **고정 벤치마크 및 회귀 테스트 세트 (`experiments/full_document_control/semantic_eval_cases.py`):**
   - FD-001 및 RW-001 패키징 의사결정 노트를 기반으로 14개 고정 사례 구축 (기존 골드 파일 변경 없음).
   - 정상 사례 2건, 8대 오류 유형별 사례 8건, 원문 모호성 보류 1건, 미탐/오탐/모델충돌 경계 사례 3건.
   - **평가 결과:**
     - 결정론 감사 단독 모드: TP 8, TN 2, FP 1, FN 1 (의미적 순서 의존성 미탐), unresolved hold 1 (총 14건 중 13건 일치).
     - 모델 stub 결합 모드: TP 9, TN 2, FP 1, FN 0, unresolved hold 2 (총 14건 중 13건 일치, FN 해소).

3. **테스트 및 검증:**
   - 신규 17개 종합 테스트 (`experiments/full_document_control/test_semantic_validator.py`)
   - 기존 108개 테스트 전체 통과 유지: 총 125개 테스트 100% 통과 (`full_document_control` 50개, `minimal_gate` 31개, `extraction_analysis` 27개, `extraction_ab` 17개).

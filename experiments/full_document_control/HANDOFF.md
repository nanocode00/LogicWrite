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
   - **보고서 위조·은폐 방어 (P1):**
     - SHA-256 다이제스트는 내용 무결성 확인용이며 평가자 신뢰성 증명이 아님을 명시.
     - 모델 평가기를 사용한 보고서는 원시 실행 기록(`evaluator_records` / `evaluator_raw_responses`)으로 재구성하여 검증. 신뢰 가능한 기록이 없으면 `UNVERIFIED_MODEL_EXECUTION_RECORD`(`REVIEW`) 보류.
     - 모델이 찾은 오류를 보고서에서 삭제/조작한 경우 `FORGED_OR_OMITTED_SEMANTIC_FINDINGS`로 차단.
   - **정확한 필드 단위 검토 범위 추적 (P1):**
     - `get_required_semantic_field_paths()`로 단위 ID뿐만 아니라 `statement`, `elements`, `relations`, `assessment.exposure`, `assessment.reason`, `assessment.preservation`, 블록별 누락 검사 경로를 완전 열거.
     - 일부 필드만 반환된 경우 단위 검토 완료를 불허하고 `INCOMPLETE_SEMANTIC_COVERAGE`(`REVIEW`, `is_complete: false`)로 처리.
   - **규칙 기반 오탐 해소 (P2, EVAL-13):**
     - `_check_polarity_reversal`에서 양보절 대조 표현(`하더라도 ... 지원하지 않으므로`)을 인식해 오탐을 해소하고 FP를 0건으로 개선.
   - **평가자 인용구 및 필드 경로 코드 재검증:**
     - 모델 평가자가 제출한 모든 인용구를 `resolve_block_quotes()`를 통해 원본 `DocumentSnapshot` 코드 포인트 구간에 대해 엄격히 재검증. 조작되거나 일치하지 않는 인용구는 `UNVERIFIED_EVALUATOR_QUOTE`로 보류.
     - 모든 필드 경로는 RFC 6901 JSON Pointer로 `AnalysisResult`에 실제 존재하는지 재검증.
   - **자기승인 거부 및 1차 구현 자동 PASS 금지 불변조건:**
     - 모델이 `passed: true`, `delivery_approved: true`, `gate_state: "PASS"`를 출력해도 무단 승인 시도(`UNAUTHORIZED_EVALUATOR_APPROVAL_CLAIM`)로 거부(`FAIL`).
     - 첫 구현 정책에 따라 모든 항목이 `supported`로 판정되어도 자동 `PASS`하지 않고 `REVIEW`(`SEMANTIC_SUPPORTED_AWAITING_APPROVAL`) 상태를 유지하여 독립적인 사람/정책 검토를 강제.
   - **업스트림 산출물 무효화:**
     - 원문, 계약, 분석 결과가 변경되면 기존 의미 검증 결과는 `STALE_SEMANTIC_REPORT_INVALIDATED`로 즉시 무효화.

2. **고정 벤치마크 및 회귀 테스트 세트 (`experiments/full_document_control/semantic_eval_cases.py`):**
   - FD-001 및 RW-001 패키징 의사결정 노트를 기반으로 14개 고정 사례 구축.
   - **개선 후 벤치마크 결과:**
     - 결정론 감사 단독: TP 8, TN 3, FP 0 (EVAL-13 오탐 해소), FN 1 (EVAL-12 의미적 순서 의존성), Holds 1.
     - 모델 stub 결합: TP 9 (EVAL-12 모델 탐지), TN 3, FP 0, FN 0, Holds 2 (14건 전체 100% 일치).

3. **실제 LLM(`gemini-3.8-flash-low`) 14개 벤치마크 2차 평가 (`run_live_semantic_evaluation.py`):**
   - 총 소요 시간: 1187.28초, 14개 사례 전체 실행 완료.
   - **TP 9건:** EVAL-03~10 8대 오류 전수 탐지 및 EVAL-12(선후 관계 왜곡)를 모델 단독으로 정확히 탐지(`det_src: model_evaluator`, `CLAIM_OVERSTATEMENT`)하여 `FAIL` 차단 성공.
   - **TN 3건:** 정상 사례 3건(EVAL-01, EVAL-02, EVAL-13) 모두 누락 필드 재검토를 통해 완전 검토(`coverage_complete: true`) 및 `supported` 판정 획득. (게이트 상태는 정책상 `REVIEW` 대기).
   - **FP 0건, FN 0건:** 오탐과 미탐 모두 0건 달성.
   - **Holds 1건:** EVAL-11(원문 모호성) 정확히 `unresolved`(`REVIEW`) 보류.
   - 산출물: `experiments/full_document_control/runs/live_eval_gemini_3_8_flash_v2/` 및 `live_semantic_eval_v2_summary.json` (이전 1차 결과도 `runs/live_eval_gemini_3_8_flash/`에 보존).

4. **최종 P1 2건 안정화 보완 (실행 증거 출처 검증 및 재검토 예산 상한):**
   - **실행 증거 출처 검증 및 등록 경로 엄격 제한 (P1-1):**
     - `trusted_execution_evidence` 인자 이름이나 외부 딕셔너리의 자체 해시만으로 실행 기록을 신뢰하지 않도록 출처 검증 경계를 강화.
     - 검증 증거 등록 경로는 검증 게이트의 실제 실행 경계([`validate_semantic_fidelity`](file:///home/honorbear/LogicWrite/experiments/full_document_control/semantic_validator.py#L2200)) 내부로 엄격히 제한되며, 내부 전용 실행 토큰(`_INTERNAL_EXECUTION_TOKEN`)을 통해서만 인메모리 신뢰 레지스트리([`_TRUSTED_EVIDENCE_REGISTRY`](file:///home/honorbear/LogicWrite/experiments/full_document_control/semantic_validator.py#L11))에 등록됩니다.
     - 외부 호출자가 `register_trusted_execution_evidence()`를 통해 위조된 증거를 임의 등록하려는 시도는 무시/거부(`return False`)되며, 자체 계산된 해시를 가진 딕셔너리를 직접 주입할 수 없습니다.
     - 호출자가 보고서와 증거의 SHA-256을 모두 다시 계산하여 조작된 쌍을 제출하는 경우 게이트 신뢰 기록과의 불일치를 감지하여 `DISCREPANT_EXECUTION_RECORD`(`FAIL`)로 차단.
     - 게이트 경계의 실행 기록이 존재하지 않거나 프로세스 재시작 등으로 출처가 인증되지 않은 외부 제출물은 `UNVERIFIED_MODEL_EXECUTION_RECORD`(`REVIEW`)로 안전하게 보류.
     - 업스트림 원문, 계약, 분석 결과가 변경되면 기존 증거는 즉시 무효화(`invalidate_trusted_evidence_for_artifacts`).
     - **신뢰 기록 보존 범위, 프로세스 재시작 시 동작 및 한계:** 신뢰 기록은 현재 세션/프로세스 수명 동안 인메모리로 유지됩니다. 프로세스 재시작 시 레지스트리는 초기화되므로, 외부 모델 보고서 단독으로는 승인될 수 없으며 게이트가 관할하는 현재 프로세스 경계 내에서 독립 재검증을 수행해야 `supported` 승인 후보로 전환됩니다. SHA-256은 내용 무결성 검증용이며 외부 주체의 신원 인증 수단이 아닙니다. 또한 동일 Python 프로세스 내에서 임의 코드를 실행하여 전역 딕셔너리를 직접 조작하는 공격자는 언어 런타임 특성상 완전히 방어할 수 없으므로, 향후 프로덕션 환경에서는 프로세스 격리 및 서명 기반 증명 체계가 권장됩니다.
   - **누락 필드 재검토 프롬프트 예산 상한 강제 (P1-2):**
     - 최초 평가와 누락 필드 재검토 모두에 동일한 `max_prompt_chars` 상한을 엄격히 강제.
     - 재검토 지시문, 계약, 대상 단위, 원문 블록, 누락 필드 경로 목록을 모두 합산해 상한 초과 여부를 사전에 계산.
     - 다수의 누락 필드로 인해 단일 재검토 프롬프트가 예산을 초과하는 경우 `plan_semantic_missing_fields_retry_prompts`를 통해 단위/블록 단위의 작은 창들로 자동 분할(Partitioning)하되, 호출 상한(`max_retry_calls`)을 유지하여 무제한 호출을 차단.
     - 단일 필드와 필수 문맥조차 예산 내에 들어가지 않는 극단적 케이스는 모델을 호출하지 않고 안전하게 `unresolved`(`INCOMPLETE_SEMANTIC_COVERAGE` -> `REVIEW`)로 보류.
     - 재검토 실패나 분할 보류 시에도 1차 응답에서 이미 확인된 유효 판정을 덮어쓰거나 축소하지 않고 그대로 보존.

5. **테스트 및 검증:**
   - 의미 검증기 종합 테스트: 총 36개 테스트 통과 (`test_semantic_validator.py`, P1 반례 테스트 9건 추가).
   - 전체 회귀 테스트 통과: 총 144개 테스트 100% 통과 (`full_document_control` 69개, `minimal_gate` 31개, `extraction_analysis` 27개, `extraction_ab` 17개).

## 6. Information Organization(정보 재구성) 모듈 구현 및 P1/P2 후속 보완 완료

- **브랜치:** `prototype/information-organization` (기준: `main` `0ed1577`, PR #13)
- **디렉터리:** `experiments/full_document_control/`
- **현재 단계:** `OrganizationPlan` 생성기, 7대 결정론적 검증 불변조건을 갖춘 독립 계획 검증기(`validate_organization_plan`), P1 4건(상위 게이트 우회 방지, 차단성 findings 반영, MOVE 목적지 독립 검증, 중복 통합 의미 동등성 보장) 및 P2 1건(`AnalysisResult` 무결성 재검증) 보완 완료. 종합 테스트 14건 및 기존 회귀 144건 호환성 유지(총 158개 테스트 100% 통과).

### 주요 구현 및 P1/P2 보완 내용

1. **상위 게이트 승인 우회 방지 (P1-1):**
   - 상위 검증 보고서 부재(`validation_report=None`) 시 계획 자체 검사가 통과하더라도 최종 상태를 `PASS`로 승격하지 않고 안전하게 `REVIEW`를 유지하도록 보장.
   - 외부에서 전달한 문자열 `gate_state='PASS'`를 신뢰하지 않고, 기존 `pipeline.can_advance_to_organization()`을 통해 실행 기록 및 검증 보고서의 진위를 독립 재검증. 조작된 보고서는 `FORGED_UPSTREAM_GATE_APPROVAL`(`FAIL`)로 즉시 차단.
   - Plan Preview(`preview_only: True`)는 상위 상태와 무관하게 `delivery_approved: False`, `next_stage_allowed: False`로 강제.

2. **차단성 Findings 반영 및 독립 불변조건 재검증 (P1-2):**
   - 계획 내 `blocking=True` 또는 `severity='ERROR'`인 finding이 존재하면 7개 검사와 무관하게 최종 검증 상태를 `FAIL`로 처리.
   - 호출자가 `plan['findings']`를 비우거나 `blocking=False`로 조작하더라도, 검증기 내부에서 원본 입력과 배치를 직접 재평가하여 필수 정보 누락, 미선언 이동 등을 독립적으로 탐지·차단.
   - 미확정 목적지나 근거 부족 등 미해결 항목은 `REVIEW` 상태로 안전하게 보류.

3. **MOVE 목적지 독립 검증 (P1-3):**
   - 계획 내부의 `destination_reviews.allows_confirmed_move` 플래그를 신뢰하지 않고, 원본 Writing Contract의 `output_scopes` 및 제공된 목적지 스냅샷을 독립 재검증.
   - 목적지 스냅샷의 `document_id`, 내용 텍스트, `sha256` 해시(`digest_text`), `version`을 직접 대조하여 불일치 시 `corrupted_destination_snapshot` 또는 `invalid_destination_version`(`FAIL`)으로 차단.
   - 실존 스냅샷이 없는 잠정 역할(`destination_role`)은 확정 배치(`disposition: placed`)를 불허하고 제안(`disposition: blocked`, `REVIEW`)으로만 보류.
   - 소스 문서의 한정 조건이 목적지로 이동된 주장과 분리되어 유실되는 현상(`MOVE_SEVERS_REQUIRED_CONDITION`) 차단.

4. **중복 통합의 의미 동등성 보장 (P1-4):**
   - 단순 수치·버전·조건·플랫폼 불충돌만으로 통합을 확정하던 경로를 전면 개편.
   - 원문 statement 정규화 및 주장 요소(claim elements)를 기준으로 의미 동등성을 독립 검토.
   - 결정론적으로 의미 동등성이 증명되지 않는 상이한 주장은 `distinct_claims`로 분류하여 통합을 차단(`blocked: True`, `INCOMPATIBLE_CONSOLIDATION_CANDIDATE`).
   - 어휘적 유사성이 있으나 결정론적으로 동등성을 단정할 수 없는 후보는 `unverified_semantic_equivalence`(`REVIEW`)로 보류.
   - 향후 LLM 의미 검토기를 플러그인할 수 있도록 `semantic_reviewer` 호출 인터페이스 구비.
   - 통합 시 구성원 전원의 원문 statement, 블록 ID, quotes, source_spans, 기여 elements, 계약 보호 의무를 `member_contributions`에 온전히 보존.

5. **`AnalysisResult` 본문 무결성 재검증 (P2):**
   - `AnalysisResult`의 자체 SHA-256 다이제스트(`verify_self_digest`)를 독립 재계산하여, 분석 본문만 변조하고 이전 해시를 유지한 공격을 `ANALYSIS_DIGEST_CORRUPTED`(`FAIL`)로 차단.
   - `DocumentSnapshot` 내용 다이제스트(`digest_text(content)`) 및 Writing Contract 정규 다이제스트와 분석 결과 간의 바인딩을 전수 재확인.
   - 변조되거나 불일치하는 스냅샷·계약 바인딩을 가진 이전 계획의 재사용 시도를 원천 거부.

### 테스트 및 검증 결과

- 신규 Information Organization 종합 및 반례 테스트: 총 14개 시나리오 100% 통과 (`test_organization.py`).
  1. 상위 검증 보고서 부재 시 PASS 승격 차단 및 REVIEW 유지 (`test_scenario_1`)
  2. 위조된 상위 PASS 보고서 차단 (`test_scenario_2`)
  3. 차단성 finding 삭제·조작 우회 차단 (`test_scenario_3`)
  4. 미선언 MOVE 목적지의 정상 위장 차단 (`test_scenario_4`)
  5. 목적지 스냅샷 해시·버전·내용 불일치 차단 (`test_scenario_5`)
  6. 서로 다른 주장의 부당 중복 통합 차단 (`test_scenario_6`)
  7. 조건·수치 부재이나 의미가 다른 주장의 통합 차단 (`test_scenario_7`)
  8. 분석 본문 변조 후 이전 다이제스트 유지 차단 (`test_scenario_8`)
  9. 정상 Preview의 REVIEW 상태 유지 (`test_scenario_9`)
  10. 정상 후보 배치 및 기존 보호 정보 보존 (`test_scenario_10`)
  11. REVIEW 상태에서 Organization 단계 무단 진입 차단 (`test_scenario_11`)
  12. 단위 누락 및 중복 배치 차단 (`test_scenario_12`)
  13. 검증된 목적지 스냅샷 기반 유효한 MOVE 계획 통과 (`test_scenario_13`)
  14. 의미 동등성 검증 중복 통합 및 기여 요소 보존 통과 (`test_scenario_14`)
- 전체 회귀 테스트 통과: 총 158개 테스트 100% 통과 (`full_document_control` 83개, `minimal_gate` 31개, `extraction_analysis` 27개, `extraction_ab` 17개).

### 다음 단계 (재개 지점)
- Expression Refinement(표현 수정) 모듈 프로토타입 구현 및 OrganizationPlan 기반 수정 계획(`ExpressionPlan`, `RevisionResult`) 연동.
- 다중 문서 스냅샷 로더 및 실제 cross-document 변경 세트 어댑터 확장.

### 다음 단계 (재개 지점)
- Expression Refinement(표현 수정) 모듈 프로토타입 구현 및 OrganizationPlan 기반 수정 계획(`ExpressionPlan`, `RevisionResult`) 연동.
- 다중 문서 스냅샷 로더 및 실제 cross-document 변경 세트 어댑터 확장.


## 7. PR #13 MOVE 검증 최종 P1 보완 (2026-11-10)

- 기준 커밋: `066da79`, 브랜치: `prototype/information-organization`.
- 실제 배치 대상의 문서 ID를 계약의 scope 및 원본 문서와 대조한다. `action`과 무관하게 모든 확정 배치에 목적지 스냅샷·버전·다이제스트 검증을 적용한다. `KEEP`/`CONSOLIDATE` 외부 배치, `REMOVE`+targets, 원본 scope/대상 문서 모순은 `INCONSISTENT_PLACEMENT`로 차단한다. 차단/보류된 제안은 실제 이동으로 취급하지 않는다.
- 원본 AnalysisResult의 `qualifies`(조건→주장), `depends_on`(주장→필수 정보)와 requirement binding의 검증된 조건 연결에서 의존성을 재구성한다. 모든 주장 배치 문서에서 조건이 함께 배치되거나 검증 가능한 노출이 있어야 하며, 주장만 이동하거나 조건만 이동하여 분리되면 `MOVE_SEVERS_REQUIRED_CONDITION`으로 차단한다. 배치의 `retained_elements`에서 원본 요소 ID가 빠지는 것도 차단한다.
- 별도 노출 증거는 주장 target의 `condition_links`로 제공한다. 필드: `condition_unit_id`, `document_id`, `snapshot_sha256`, `version`, `start`, `end`, `quote`. 인용은 해당 목적지의 독립 검증에 사용한 실제 스냅샷에서 `[start:end]`와 정확히 일치하고, 원본 조건 단위의 전체 statement여야 한다. 다른 버전/중복 스냅샷, 일부 인용, 단순 URL이나 계획의 보존 주장은 증거가 아니다.
- `supports`는 필수 의존 관계로 취급하지 않는다. 미확정 관계 상태/신뢰도, 누락된 의존 단위는 `MOVE_DEPENDENCY_INTEGRITY: unresolved`로 기록하고 `REVIEW`를 유지한다. 상위 Validation Gate, Semantic Fidelity Validator, Preview의 단계 전환 금지 정책은 변경하지 않았다.
- 반례 우선 검증: 최초 추가 15건 중 11건 실패(10 failures, 미구현 검사 ID로 인한 1 error), 추가 경계 6건 중 3건 실패를 확인한 뒤 수정했다. 총 21개 테스트 추가. 기존 158개 테스트를 유지하되, 기존 정상 macOS MOVE 사례는 수동 재설치 조건도 동반 이동하도록 보완했다(기존 단독 이동은 이번 P1의 실제 반례).
- 최종 로컬 검증: full_document_control 104개, minimal_gate 31개, extraction_analysis 27개, extraction_ab 17개, 총 179개 통과. `git diff --check` 통과. 실제 문서 수정/외부 LLM 호출/후속 모듈 구현은 수행하지 않았다.
- 구조적 한계: 원본 분석의 관계/요소 정확성은 기존 독립 의미 검증 및 상위 게이트의 책임이다. 같은 문서 내 구체적 가독성·조건 인접성의 의미 판단은 수행하지 않으며, 연결 증거는 전체 statement의 정확 인용만 인정하므로 의역·외부 URL만 있는 연결은 승인하지 않는다. 스냅샷 해시는 내용 무결성 확인이며 외부 저장소의 신원 인증이 아니다. 여기서 검증하는 것은 적용 전 후보 계획이며 실제 적용 후 문서의 의미 검증을 대체하지 않는다.

## 8. Expression Refinement Preview 프로토타입 (2026-11-10)

- **기준/브랜치:** `main` `f248468` → `prototype/expression-refinement`. 기존 179개 회귀 테스트 및 기존 Gate·Organization·Semantic Fidelity Validator 구현은 그대로 유지한다.
- **구현:** [`expression.py`](expression.py)의 출처 고정 ExpressionPlan, provider 독립 생성 인터페이스, 제한된 한국어 문체 변환·명시 용어 치환·반복 단어/공백 압축, RevisionResult의 변경 전후·단위/요소 trace. [`expression_validator.py`](expression_validator.py)는 원본 quotes를 다시 해석해 참조·다이제스트·배치·누락·보호 요소·수정 제외 구간 및 실제 결과의 알려진 의미 왜곡을 검사한다. 실행/계약/스키마 차이/축약 예시는 [`EXPRESSION.md`](EXPRESSION.md)에 모았다.
- **승인 경계:** 항상 `delivery_state: preview`, `output_snapshots: []`. 상위 REVIEW 아래에서도 격리된 발췌 후보는 생성하지만 실제 단계 진입·원본 덮어쓰기는 하지 않는다. 승인 실행은 `NOT_IMPLEMENTED`. 자체 검사 상태와 최종 전달 승인을 분리하고, 모든 결과에서 의미 검증 미완료 및 최종 승인 불허를 명시한다. 일반적인 의미 동일성을 문자열 검사로 증명하지 않는다.
- **반례/독립 검토:** 신규 테스트를 먼저 준비하고, 추가 경계 결함도 실패를 확인한 뒤 수정했다. 수치·단위·버전/식별자 손실, 부정·조건·범위 왜곡, 신규 AES-256 주장, 코드·명령·인용·URL 수정, 오래된 참조, 단위 누락·중복·발명, 재해시 후 배치·보호 목록 변조, 루트/생성 응답/조각 내부의 허위 PASS·승인 주장 등을 검증한다. 독립 코드 검토에서 발견한 부정 종결 변환 오탐·포함 관계 용어 오탐·한글 인접 수치 미탐·조각 내부 승인 주장 누락도 회귀 테스트로 고정했다.
- **최종 로컬 검증:** 신규 Expression 테스트 52개와 기존 179개, 총 **231개 통과**. full_document_control 156개, minimal_gate 31개, extraction_analysis 27개, extraction_ab 17개. 문서의 Python 변환 예제를 실제 실행해 `30초다.` → `30초입니다.` 및 `REVIEW`를 확인했다. CLI 테스트는 입력 파일 바이트 보존도 확인한다. `git diff --check` 통과. 이 숫자는 실제 LLM/홀드아웃 의미 평가나 원격 CI 결과가 아니다.
- **미구현/한계:** 전체 문서 재조립, candidate 스냅샷, 실제 승인 경로, 표현 의미 검증 모델/사람 승인 등록, 문서 전체 조건 인접성·문체/모순 재검증, 파일 적용·배포는 미구현이다. 안전한 의역도 보호 문자값 검사에서 거부될 수 있으며, 알려지지 않은 왜곡은 REVIEW로 보류된다. 계약의 자유 형식 자연어 제약은 미해결로 남긴다. 스냅샷 해시는 인증 수단이 아니며 임의 Python 생성 어댑터는 보안 샌드박스로 격리하지 않는다.
- **문서 초안 위임:** Antigravity에 README/HANDOFF/EXPRESSION 문서만 요청했으나 `429 RESOURCE_EXHAUSTED`로 종료되어 변경 파일이 없었다. 재시도 없이 Codex가 실제 코드·테스트에 대조해 작성했다.
- **후속 작업:** 전체 관련 문서 스냅샷의 재구성·독립 의미 검증·승인 근거를 갖춘 전달 경로는 별도 설계/평가가 필요하다. RAG·LangGraph·자동 배포는 구현하지 않았다.

## 9. PR #14 응답 최소 저장·실패 상태·인용 보호 보완 (2026-11-10)

- **기준/범위:** `bf0c085`, 기존 `prototype/expression-refinement` 브랜치. expression.py·expression_validator.py·test_expression.py·EXPRESSION.md·이 HANDOFF만 수정한다. 전체 문서 재구성·새 표현 수정 기능·상위 게이트 정책은 추가/변경하지 않는다.
- **응답 저장:** 생성 응답 전체와 임의 메타데이터는 보관하지 않는다. 생성 텍스트는 조각 content와 기존 전후 change_set에만 반영한다. generation은 상태·고정 오류 코드·승인 주장 boolean·실행 기록 ID만 가진다. 비직렬화 메타데이터도 생성 성공과 분리해 폐기하며, text가 잘못돼도 중첩 승인 주장은 먼저 신호로 남긴다. 어댑터의 Python stdout/stderr 및 사전 설정된 표준 logging 출력은 호출 중 억제하고 설정을 복구한다. 예외 문자열·예외 클래스명은 결과에 남기지 않는다.
- **실패/조작 검증:** 생성 실패·잘못된 응답은 원문 복구 후에도 `GENERATION_ERROR`, 자체 검사 unresolved, 최종 REVIEW다. 별도 확정 위반은 기존처럼 FAIL이다. 응답 대신 최소 실행 신호·실행 ID·계획/입출력 해시만 가진 프로세스 내부 기록과 대조한다. 실패를 completed로 바꾸거나 승인 신호/발견 사항을 숨기거나 과거 실행의 성공 기록을 이식하면 불일치를 차단한다. 기록을 확인할 수 없으면 성공으로 간주하지 않고 `GENERATION_RECORD_UNVERIFIED`로 보류한다. 레지스트리는 최대 4,096건이며 프로세스 재시작/만료 후 외부 JSON만으로 실행을 인증할 수 없다.
- **작은따옴표:** 경계 ASCII 인용·부분 발췌·인용 내부 축약형/복수 소유격을 보호한다. 일반 `don't`, `users'`, `O'Reilly's`는 인용 쌍으로 묶지 않는다. 닫히지 않은 경계 인용은 줄 끝까지 보호한다. 기존 큰따옴표·곡선 따옴표·인라인 코드·코드 블록·URL 보호를 유지한다.
- **검증:** 신규 25개(기존 Expression 52개 → 77개) 및 기존 전체 231개를 유지하여 총 **256개 통과**: full_document_control 181개, minimal_gate 31개, extraction_analysis 27개, extraction_ab 17개. `git diff --check` 통과. 실제 비밀정보 대신 sentinel을 사용해 결과·CLI·표준 로깅의 비노출을 검증했다. 반례 실패 확인 후 수정했으며, 독립 검토의 사전 설정 로깅 우회·인용 내부 복수 소유격 지적도 재현/수정 후 재검토했다. 원격 CI나 실제 LLM 평가 통과를 뜻하지 않는다.
- **한계:** 출력 억제는 동기식 프로토타입의 프로세스 전역 설정이다. OS 파일 디스크립터·별도 프로세스·네트워크까지 차단하는 샌드박스, 영속 서명 기반 실행 인증, 같은 프로세스의 임의 Python 코드 방어는 아니다. 정규식 인용 판별은 중첩/여러 줄 인용·선행 아포스트로피 축약형에서 과보호/모호성이 남는다. 미확정 결과와 최종 전달은 기존처럼 REVIEW/승인 불허를 유지한다. 상세 정책은 [EXPRESSION.md](EXPRESSION.md)를 참조한다.

## 10. 전체 문서 후보 파이프라인 통합 (2026-11-10)

- **병합/기준:** PR #14를 최신 HEAD `8f3e663`와 기존 256개 회귀 통과를 확인한 뒤 Ready로 전환하고 병합했다. 병합 커밋 `8792bff4fa699673e9956b72585eb0a7557f7f96`으로 로컬 main을 fast-forward한 후 새 `prototype/final-pipeline-integration` 브랜치를 생성했다. 등록된 원격 CI 결과는 없었으며 로컬 검증과 구분한다.
- **실행:** [`integration.py`](integration.py)의 읽기 전용 CLI/API에서 Markdown+계약 → 기존 분석 조립/게이트 → 격리된 조직화/표현 계획 → 전체 후보 → 최종 검사까지 실행한다. 기본 분석은 원문 블록 목록이며 목적·관계의 의미 판단은 미확정이다. 기존 기록된 추출 응답도 재사용할 수 있으나 현재 입력 참조가 일치해야 한다.
- **재구성:** [`reconstruction.py`](reconstruction.py)는 전체 원문 span 원장, 제한된 표현 변환, 기존 제목/기준점에 따른 독립 문단 배치, 전체 목적지로의 원자적 MOVE, 정확히 같은 독립 문단의 검증된 중복 통합을 지원한다. 수정되지 않은 문자·코드·표·인용도 추적한다. 부분 중첩 수정·의미 미확정 재작성·안전하지 않은 이동/구조 경계는 보류한다. 원본·목적지를 직접 쓰지 않는다.
- **독립 최종 검사:** [`final_validator.py`](final_validator.py)의 고정 8개 검사군이 실제 출력, 원본/출력 전체 범위, 블록/조각 순서, 목적지 기존 내용, 통합 secondary/primary 및 출현 위치, 길이 변화를 반영한 양방향 추적, 현재 상위 참조를 다시 대조한다. 검사 누락·변조·오래된 최종 보고서는 재검증으로 거부한다. 구조 검사 passed와 최종 전달 승인은 다르며, 신뢰 가능한 전체 의미 검토/사람 승인 경로가 없어 최종 PASS는 없다.
- **제어:** 원인 모듈 식별·저장된 하위 산출물 무효화·현재 입력 재검증을 제공한다. 확인된 위반 또는 생성기 실행 실패 등 복구 근거가 없는 경우 재시도 없이 STOPPED로 반환하고 last_gate_state를 보존한다. REVIEW 아래 후보 계산은 승인된 단계 진입이 아니다.
- **실제 문서 확인:** 기존 `docs/logicwrite-project-proposal.md` 4,614바이트를 별도의 검토 계약으로 CLI에서 처리했다. 전체 후보 1개·문체 변환 범위 10개, 원본 바이트 불변. 스냅샷/전체 범위/보호 문자값/양방향 추적/문서 집합 검사는 passed, 배치/표현 의미/승인은 unresolved, 최종 REVIEW였다. 실행 계약과 방법은 [INTEGRATION.md](INTEGRATION.md)에 기록했다. 기존 과제 문서 및 평가 데이터 자체는 변경하지 않았다.
- **테스트:** 신규 E2E/통합 테스트 44개와 기존 256개, 총 **300개 통과**(full_document_control 225, minimal_gate 31, extraction_analysis 27, extraction_ab 17). 실제 Markdown 파일 CLI, 입력 바이트 불변, 동일 입력 후보 내용 일치, 문체/압축, 원자적 MOVE/통합, 조건·부정·수치 손실, 범위/추적/승인/보고서 무결성 및 안전 중단을 포함한다. `git diff --check` 통과.
- **검토 근거:** 독립 검토가 제시한 블록 순서·목적지 내용·통합 구성원·공백 구문·반복 문장 출처·미종결 목적지 코드 펜스 문제는 모두 실패 반례 확인 후 수정했다. 마지막 독립 재확인 호출은 도구 측 위험 분류로 중단되어 완료 근거에 포함하지 않았다. 최종 수치는 로컬 전체 테스트 결과이며 원격 CI·일반 문서 의미 보존 성능·최종 독립 승인 근거가 아니다.
- **차이/한계:** 파일 추출 입력은 기존 단일-scope 계약 그대로다. 다중 문서 API는 이미 바인딩된 상위 분석/계획과 완전한 목적지 스냅샷을 받으며 다중 문서의 자동 의미 분석·승인 경로는 없다. 추상 섹션은 유일한 실제 제목으로 해석되지 않으면 unresolved다. 문단 부분 구조 편집·의미적 통합·전체 문서의 사실/모순/가독성 판단·자동 수정/재시도·파일 적용·RAG·LangGraph는 미구현이다. 상세 계약과 사용법은 INTEGRATION.md를 단일 참조로 사용한다.


## 11. PR #15 출력 문서 범위 검증 보완 (2026-11-10)

- **기준/범위:** `d83a8b4`, 기존 `prototype/final-pipeline-integration`. Reconstruction·Final Validator·통합 테스트 및 실행/HANDOFF 문서만 보완하며 기존 Analysis/Organization/Expression/승인 정책은 변경하지 않는다.
- **입력 검증:** `source_documents()`가 문서 등록 전에 별도 계약 검사로 구체적인 허용 문서 ID를 구성한다. 미선언 원본은 `UNAUTHORIZED_SOURCE_DOCUMENT`, 미선언 목적지는 `UNAUTHORIZED_DESTINATION_DOCUMENT` 오류와 빈 출력 Preview로 반환한다. 역할만 선언된 scope를 임의 ID로 구체화하지 않는다. 중복·다이제스트·버전·완전성 검사는 기존대로 유지한다.
- **독립 최종 검증:** 수집기 결과를 신뢰하지 않고 현재 계약을 직접 다시 읽어 입력 원본/목적지 및 모든 output_snapshots ID를 검사한다. 미선언 출력은 `UNAUTHORIZED_OUTPUT_DOCUMENT`로 FAIL이다. 범위 위반은 불완전한 스냅샷·Preview에서도 FAIL을 유지하고 미실행 검사를 passed로 표시하지 않는다. 동반된 승인 위조도 별도로 보존한다. 기존 문서 누락·중복 및 원자적 ChangeSet 검사를 유지한다.
- **문맥 구분:** destination_snapshots는 명시적 출력 대상이며 참고자료 로더가 아니다. source_material 등 참고 문맥을 자동으로 출력으로 승격하지 않는다. 선언된 미수정 목적지는 기존 내용을 KEEP으로 보존할 수 있다. 참고자료 로딩·검색 기능은 추가하지 않았다.
- **검증:** 신규 14개 중 수정 전 9개 실패를 재현한 뒤 보완했다. 원본 불일치·선언/미선언 혼합·미수정 미선언 문서·ID/해시 변경·역할 전용 scope·수집기 오류와 독립된 최종 검사·중복 목적지/출력·참고자료 비승격·선언된 미사용 목적지·중첩 target 문서 참조를 포함한다. 기존 300개와 신규 14개, 총 **314개 통과**(full_document_control 239, minimal_gate 31, extraction_analysis 27, extraction_ab 17). `git diff --check` 통과. 정상 단일 문서/MOVE/중복 통합 및 최종 REVIEW 경계는 유지한다.
- **한계:** 허용 여부는 호출자가 제공한 현재 Writing Contract의 구체적 ID를 기준으로 하며 계약 작성자 인증을 추가하지 않는다. 기존 단일-scope 파일 분석 제약, 전체 의미 검토·사람 승인·파일 반영 미구현 등 통합 프로토타입의 한계는 그대로다. 상세 정책은 [INTEGRATION.md](INTEGRATION.md)를 참조한다.

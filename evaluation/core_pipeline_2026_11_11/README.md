# Core 실행 검증 — 2026-11-11

기준은 PR #21이 병합된 main `29dd271c5e367044af765cc0ff9e81db52de7160`이다. **확인한 결함 1건을 8줄로 수정했다.** 조직화 모듈이 `coverage: partial` 등 명시적 불완전 목적지에도 `allows_confirmed_move: true`를 반환했다. 수정 후 보류한다. 기존 전체 재구성 단계는 이미 불완전 목적지를 거부했으므로, 이번 결과는 기존에 잘못된 최종 PASS/납품 승인이 있었다는 증거가 아니다.

## 실행 결과와 경계

| 대상 | 수정 전 | 수정 후 | 근거 |
| --- | --- | --- | --- |
| 기존 Core 회귀 | 340 통과 | 기존 340 + 신규 2 = 342 통과 | [기준선](records/baseline-tests.txt), [전체 실행 기록](records/all-tests-after.json) |
| 원래 main 전체 디렉터리 테스트 | 534 통과 | 기존 534 + 신규 9 = 543 통과 | [main](records/all-tests-baseline.json), [수정본](records/all-tests-after.json) |
| 신규 평가 어댑터 | 없음 | 7 통과 | 전체 실행 기록의 `evaluation/core_pipeline_2026_11_11` 행 |
| 같은 통제 native 입력 18건 | 명시적 부분 목적지 1건에서 기대 불일치 | 18건 기대 gate/종료/이동 결정 일치 | [수정 전](records/native-before.json), [수정 후](records/native-after.json) |
| SP 개발 골드 12건 | 입력/확정 정답 읽기 분리 | Core의 SP 3분류 예측은 0건 | [예측 단계](records/sp-predictions.json), [사후 대조](records/sp-comparison.json) |
| 실모델 의미 검증 | 미실행 | 미실행 | 기록의 `real_model: not_run` |

기존 459건이라는 부분 검증 범위보다 넓게, 저장소의 `test_*.py`가 있는 모든 디렉터리를 별도 Python 프로세스로 실행했다. [run_checks.py](run_checks.py)는 모듈명이 중복되는 기존 평가 디렉터리를 한 인터프리터에 합치지 않는다. 테스트 출력과 명령은 각 suite 행에 있다. 실모델 평가의 실행 불가능을 주장하지 않는다. 문서 초안용 별도 Antigravity 시도는 할당량 제한으로 실패했으며, 위 기록은 Core 실모델 실행이나 AI 검수 결과가 아니다.

## 실제 코드 경로

| 모듈 | 실제 역할 / 이번 확인 |
| --- | --- |
| `pipeline.py` | 입력 계약과 완전 스냅샷 검증 → Markdown block/추출 창 → 응답 조립 → 분석 gate. `can_advance_to_organization` 및 승인된 실행 경로는 별도 검증 증거를 요구한다. 최종 의미/승인 호출 wrapper도 제공한다. |
| `semantic_validator.py` | Source→Analysis의 결정론적 의미 진단 및 별도 reviewer 응답 검증/실행 증거. SP의 문서 전후 3분류 API가 아니다. |
| `organization.py` | 단위 배치·조건 관계·목적지 문맥·병합 호환성 검증. 이번 수정은 `evaluate_destination_scope`의 명시적 불완전 coverage 거부다. |
| `expression.py` | 제한된 결정론적 표현 수정, 생성 receipt/승인 주장 방어, 조직화 계획 검증. 임의의 외부 수정본을 검증된 생성 결과로 수입하는 API가 아니다. |
| `reconstruction.py` | source와 목적지 전체를 재구성하고 출력/ledger/trace 생성. 목적지에 완전한 Markdown 메타데이터를 요구한다. |
| `final_validator.py` | 원문·출력·변경집합·실제 배치·trace와 승인 경계의 구조 검증. 자체 `semantic_fidelity: not_run`을 의미 통과로 해석하지 않는다. |
| `final_semantic_validator.py` | 전체 source/목적지/output 검토 요청, 리터럴 증거와 선택적 reviewer, 현재 입력에 묶인 receipt. 구조 오류는 별도로 재계산하며 reviewer를 차단한다. |
| `final_approval.py` | 검증 현재성·receipt·명시적 사람 결정/근거 확인. 현재 정책 증거 연결은 `test_only`; 실제 발급은 비활성, `delivery_approved`/전이 허용은 false다. |
| `integration.py` | `analyze_source → validate_analysis_gate → organization → expression → reconstruction → validate_final_output → validate_final_approval_policy`. REVIEW 상태에서도 격리 후보 미리보기를 만들 수 있으나 승인된 단계 전이는 아니다. FAIL/실행 오류는 STOPPED다. |
| `repair_loop.py` | 상위 분석 gate 재검사 → 독립 최종 감사 → 책임 모듈 진단 → 해당 모듈부터 하위·승인 자료 무효화 → 재생성 → 전체 감사. 반복/진전 없음/예산/시도 제한으로 종료하고 승인하지 않는다. |

`integration.analyze_source` 기본값은 문자 그대로의 block inventory이며 추론된 목적·조건 관계를 제공하지 않는다. 실제 기존 `sample_input.json` 실행은 요구 정보와 관계 검증에서 **분석 FAIL → STOPPED**, 최종 감사 미진입, 납품 승인 false였다([전체 baseline 산출물](records/baseline-pipeline.json)). 단순 통제 입력은 source-only 후보를 생성하되 최종 REVIEW다. 이 두 경로를 문서 설명만으로 성공 처리하지 않았다.

조직화의 예전 최소 목적지 형식(content/hash/version만 제공)은 호환성을 위해 유지했다. coverage가 **명시됐고 complete가 아닐 때만** 새로 보류한다. 완전성 메타데이터가 없는 이 예전 형식이 재구성 단계에서도 허용된다는 뜻은 아니다. 조직화와 전체 재구성의 지원 범위 차이는 남아 있으며, 승인 정책은 변경하지 않았다.

## SP 평가 과제와의 대응 한계

SP 확정 정답은 `development_gold_v2_2026-11-11/development-gold.json`의 12건(4/4/4)이다. 입력 파일 해시가 활성 정답 행과 같을 때만 사후 비교한다. 기존 입력·확정 답·검수 기록은 변경하지 않았다. 개발용 사례이며 독립 홀드아웃이 아니다.

`evaluate.py predict`는 고정된 `inputs/SP-001~012.json`만 읽는다. `compare`는 저장된 예측 파일을 받은 뒤에야 확정 정답 manifest를 읽는다. 답/정답 읽기 금지와 외부 정답 필드 거부, 입력 해시 불일치를 테스트한다. Core에 전달하는 객체에는 확정 정답이 없고 입력/예측의 해시를 기록한다.

현재 Core는 SP의 전후 다문서·작성 계약·승인된 기준 버전 선택 과제를 그대로 받지 않는다. 평가 어댑터는 제공된 문서와 같은 위치의 행을 리터럴 진단에 대응시키며, 행 수가 다르면 문서 전체로 대응시킨다. 이 ledger는 **진단용 위치 대응**이며 실제 Core 생성 receipt/정확한 편집 계보가 아니다. 내부 `_deterministic`만 호출한 결과를 full audit, Core gate, 의미 보존 확정 답으로 제시하지 않는다. 행 재배치/동시 문장 변화는 오탐 또는 미탐 원인이 될 수 있다.

별도의 `source_only_pipeline`은 진단용 계약 아래 원문 자체를 처리한 실제 격리 pipeline 실행이다. SP 계약의 필수 요구·노출 정책을 해석한 결과나 SP 수정본을 평가한 결과가 아니다. `required_information=[]`은 이 통제 source inventory의 계약이고 SP 요구를 면제한 평가가 아니다. 출력의 `sp_prediction`과 `actual_core_gate_for_sp_candidate`는 모두 null이며 정확도를 산출하지 않는다.

| 사례 | 사용자 확정 기대 | 실제 제한된 진단 / 오류 유형 | 후속 우선순위 |
| --- | --- | --- | --- |
| SP-001~004 | PRESERVED | 변경 문구 의미 검수 필요. 보존 정답을 재확정할 API가 없어 미해결. 리터럴 위반 확증/오탐 없음. | P2 의미 등가·계약 어댑터 평가 |
| SP-005 | VIOLATION | 요구를 사실로 바꾼 표현에서 위반 확증 없음: 이 진단의 미탐. | P2 주장/양태 의미 검수 |
| SP-006 | VIOLATION | 부정·수량·종결 표현이 함께 변해 엄격한 같은-skeleton 규칙은 위반 확증 없이 문맥 검토로 남음: 미탐. | P2 복합 변화 의미 검수 |
| SP-007 | VIOLATION | 필수 조건 삭제의 의미 위반 확증 없음: 미탐. | P2 조건/노출 정책 검수 |
| SP-008 | VIOLATION | 근거 없는 주장 추가의 의미 위반 확증 없음: 미탐. | P2 추가 주장 근거 검수 |
| SP-009 | UNRESOLVED | 목적지 수정 전후 전체 미제공: 미지원, 검사하지 않은 내용을 채우지 않음. | P2 전체 목적지 확보 |
| SP-010 | UNRESOLVED | 원문 후보 ID와 결과 ID 불일치, 승인 기준 버전 선택기 없음: 미지원. 높은 버전을 임의로 선택하지 않음. | P2 권한자의 기준 버전 근거 |
| SP-011 | UNRESOLVED | 다문서 행 진단은 가능하나 조건의 현지 노출 계약을 결정하지 못해 미해결. | P2 사용자 조건·관계 검수 |
| SP-012 | UNRESOLVED | 부분 수정 결과: 미지원, 전체 출력으로 가정하지 않음. | P2 전체 결과 확보 |

위 4건의 미탐은 **이 결정론적 진단에서 위반 확증이 없었다**는 뜻이다. Core가 PASS/납품 승인을 냈다는 뜻이 아니며, 미실행 실모델의 미탐률도 아니다. 3건의 미지원 제외 9건을 억지로 3분류 점수로 만들지 않는다. 사례별 입력·출력 JSON Pointer·오류 유형·재현·정답 위치는 [sp-comparison.json](records/sp-comparison.json), 실제 witness 위치는 [sp-predictions.json](records/sp-predictions.json)에 있다.

## native 집중 검증과 수정 전후

[수정 전](records/native-before.json)과 [수정 후](records/native-after.json)은 동일한 평가 도구를 각각 원래 main/Core 수정본에 실행했다. 각 행에는 기대/실제 결과·모듈·입력 위치·출력/근거 Pointer·재현 방법·우선순위가 있다. 합성 입력은 `native_case`/`native_probes`에 고정했고 외부 사실이나 사용자 승인으로 취급하지 않는다.

| 사례 | 확인 결과 / 근거의 한계 |
| --- | --- |
| N-01 수치·단위 / N-02 부정 / N-04 조건→항상 | 전체 감사 FAIL이며, 각 `QUANTITY_SCOPE`/`POLARITY_CONDITIONS`에 독립적인 결정론적 위반 witness도 있다. 입력을 위조한 후보여서 구조 FAIL도 함께 발생한다. |
| N-03 근거 없는 추가 | 전체 감사 FAIL은 구조적 계보/허용 변경 안전 차단이다. 의미 판별기가 새 주장 자체의 무근거를 확증했다고 주장하지 않는다. |
| N-05 원문 유지 | REVIEW, 미실행 의미 검수와 명시적 승인 부재를 보존한다. |
| N-06 목적지 없음/부분/전체 (3행) | 없음은 보류, 전체는 조직화 단계 이동 가능. 부분은 수정 전 true(미탐) → 수정 후 false. P1 결함 수정 대상이다. |
| N-07 반복 / N-08 예산 / N-09 시도 제한 | REPEATED_STATE / BUDGET_EXHAUSTED / MAX_ATTEMPTS. 시도 제한 사례는 max_attempts=0이며 실제 여러 번의 모델 수정을 수행한 증거가 아니다. |
| N-10 표현 생성 오류 복구 | 표현과 재구성 재생성 후 VALIDATION_INCOMPLETE. 의미 검수를 완료하거나 납품 승인한 복구가 아니다. |
| N-11 부분 출력 / N-12 부분 원문 | 각각 최종 FAIL / pipeline STOPPED. |
| N-13 진전 없음 | 잘못된 unit 참조를 유지하고 justification만 바꾼 실제 adapter를 실행해 NO_VERIFIED_PROGRESS, FAIL. |
| N-14 상위 수정 | analysis 수정 후 organization/expression/reconstruction 및 최종/승인 산출물 무효화, 하위 3개 재생성, 전체 감사 재실행 후 REVIEW. |
| N-15 조건 분리 / N-16 조건 동반 이동 | 합성 관계를 명시한 입력에서 조건 분리는 표현 생성 전 거부. 원문·목적지 전체가 있고 조건과 주장 동반 이동 시 REVIEW이며 기존 목적지 내용 보존. |

미해결 P2는 일반 의미 변경·복합 부정/수치 변화·조건 계약·추가 주장 판단, SP 기준 버전 권한 해석, 실모델 검증이다. 이번에 이 의미 규칙을 넓혀 데이터를 맞추거나 테스트를 완화하지 않았다. destination 결함만 실제 red 테스트(3개 subtest 실패) → 최소 수정 → green으로 확인했다([red](records/destination-red.txt), [green](records/destination-green.txt)).

## 재현

```bash
python3 evaluation/core_pipeline_2026_11_11/evaluate.py predict /tmp/sp-predictions.json
python3 evaluation/core_pipeline_2026_11_11/evaluate.py compare /tmp/sp-predictions.json /tmp/sp-comparison.json
python3 evaluation/core_pipeline_2026_11_11/evaluate.py native /tmp/native-after.json
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'
python3 -m unittest discover -s evaluation/core_pipeline_2026_11_11 -p 'test_*.py'
python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/all-tests.json
```

수정 전 비교는 별도 `29dd271` checkout의 Core 경로로 실행한다. 이 설정은 코드 위치만 바꾸며 정답 파일을 runtime에 공급하지 않는다.

```bash
LOGICWRITE_CORE_CODE_ROOT=/path/to/baseline/experiments/full_document_control \
  python3 evaluation/core_pipeline_2026_11_11/evaluate.py native /tmp/native-before.json
python3 evaluation/core_pipeline_2026_11_11/run_checks.py \
  --repo /path/to/baseline --output /tmp/all-tests-baseline.json
```

실행 UUID/receipt와 시간은 매번 달라질 수 있다. gate·규칙·종료·하위 무효화 결과를 비교해야 하며 저장된 receipt를 재사용 가능한 승인으로 취급하면 안 된다. 기준선 코드 SHA-256은 [baseline.json](records/baseline.json)에 있다.

`all-tests-*.json`의 `source_commit`은 실행 당시 HEAD일 뿐 작업 트리 전체 버전이 아니다. 수정본의 8줄 변경과 신규 테스트는 당시에 미커밋이었다. 해당 실행 뒤 테스트 대상 Python 변경 없이 `tested_tree_observed_after_run`에 tracked diff SHA-256·작업 트리 상태·Python 파일별 SHA-256을 추가했다. `run_checks.py`의 provenance 기록 기능 자체는 이 실행 뒤 추가됐으며 테스트 대상 모듈이 아니었다. 이후 재실행에서는 전후 코드 fingerprint를 자동 저장한다.

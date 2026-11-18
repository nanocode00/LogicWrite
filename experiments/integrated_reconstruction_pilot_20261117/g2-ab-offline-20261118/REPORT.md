# G2-A/B 구현 결과 — 2026-11-18

문서군 공동 **원문 분석과 조건부 작업 계획 API**를 추가했다. 실제 문서 후보 생성·적용, G2-C, G3 변경, G4 비교, 신규 유료 API 호출은 없다. 포괄적인 자연어 요청을 완성된 의미 편집 계획으로 자동 변환하지 않으며, IR 기본 결과의 `eligible`은 전부 원문 KEEP이다. 의미 분석·작업 분해 완료나 B2 성공으로 집계하지 않는다.

## 변경 파일과 인터페이스

| 새 파일 | 역할 |
|---|---|
| `experiments/full_document_control/document_set_analysis.py` | `analyze_document_set(contract, *, trusted_contract_sha256)` → `core-document-set-analysis-v1`; 전체 문서 원문 블록, 출처·권한·범위·해시, 공유 관계/불확실성 |
| `experiments/full_document_control/document_set_planning.py` | `make_request(tasks, *, issues=None, question_scopes=None)`, `plan_document_set(contract, analysis, request, *, trusted_contract_sha256, trusted_request_sha256)` → `core-document-set-plan-v1`; 작업별 상태·보존 의무·부분 HITL |
| `experiments/full_document_control/test_document_set_g2.py` | 일반 합성 변형 및 IR input-only 회귀 |
| `../g2_ab_offline.py`, `../test_b2_g2_ab_offline.py` | 원본 IR 입력과 별도 합성 입력만 사용하는 오프라인 재현 및 누설·재현성 검사 |
| `../g2_ab_synthetic_input.json`, `../g2_ab_synthetic_request.json` | IR 정답과 독립적인 문서군·명시적 요청/질문 예시 |
| `../G2_AB_IMPLEMENTATION.md`, 이 디렉터리 JSON | 설계 결정·검증 및 실행 가능한 분석/계획 예시 |

기존 `document_set.py`, `pipeline.py`, `organization.py`, `reconstruction.py`와 G1 스키마/단일 문서 API는 변경하지 않았다. 기존 parser/partition 검사를 재사용하며, 단일 문서 파이프라인이나 Organization/Reconstruction 실행기를 반복 호출하지 않는다. 출처 경로는 문자열로만 취급한다.

## 신뢰 경계와 분석 예시

호출자는 모델/후보 밖에서 G1 계약 해시와 명시적 계획 요청 해시를 먼저 고정한다. 최초 계약과 이슈/질문 범위의 진위는 호출자 책임이며 hash가 실제 권한을 인증하지 않는다. 계획기는 원본 계약으로 분석을 재생성해 전체 JSON을 대조한다. 원문·권한·분석의 변조, 누락, 오래된 분석 및 자기 해시를 다시 붙인 위조를 거부한다. 모델/평가 정답 필드나 임의 확장 필드를 계약·요청에 추가할 수 없다.

[IR-002 분석](IR-002-analysis.json)의 `design` 원문 5–7행은 하나의 원자적 정보 단위다. `document_id`, 문서 SHA-256, 정확 인용과 인용 SHA, codepoint/UTF-8 byte/행 범위, 역할·근거 위상·access, 절 경로, 주장 원문 및 수치/조건/예외/상태의 **문자열 관찰**을 보존한다. 조건과 주장은 같은 `preservation_group`에서 분리되지 않는다. 공백/구분선도 문서 `blocks`에서 명시적으로 추적하며 모든 제공 바이트를 partition 검사한다.

공유 그래프의 `exact_text`는 완전한 문단 바이트 동일성만 뜻한다. `shared_literal_candidate`는 같은 숫자/인라인 코드의 등장, `explicit_reference`는 제공 경로와의 연결만 뜻한다. 모두 `semantic_status=unresolved`다. `condition_claim_cooccurrence` 역시 원문에 함께 등장한다는 관찰이며 실제 논리 관계의 인증이 아니다. 독자·목적·필수 제약의 의미 관련성은 `reader_relevance.status=unresolved`로 남긴다. 지원하지 않는 Markdown과 발췌/미완성 입력은 `unanalysed`에 기록하고 `coverage_status=incomplete`; 원문 위치를 확보했다는 이유로 분석 성공으로 승격하지 않는다.

## 작업 계획·HITL 예시

명시적 task는 `task_id`, `action`, `unit_ids`, `target_document_id`, `reason`, `evidence_unit_ids`, `depends_on`, `parameters`를 받는다. 결과에는 출처 인용, 적용 권한, 보존 의무, 충돌/불확실성, 필수 질문, 현재 상태·사유, 조건부 executor mapping을 추가한다. source/target/anchor 권한은 evidence 참고 권한과 분리한다. `unplanned_unit_ids`는 명시적 제안이 다루지 않은 단위를 드러낸다.

[합성 요청](../g2_ab_synthetic_request.json)과 [계획](synthetic-plan.json):

| 작업 | 상태 | 이유 |
|---|---|---|
| `independent-placement` | eligible | edit 문서의 완전한 문단을 같은 문서의 기존 문단 앵커 뒤로 배치하는 명시적 제안. 정책 질문과의 원문·참조 의존성이 없음 |
| `policy-revision` | held | 상반된 상업 지원 문구에 관한 **호출자 보고** 질문과 조건 문맥에 의존 |
| `format-content-denied` | denied | format_only 문서에 내용 REVISE 요청 |
| `remove-unsupported` | unsupported | 현재 Core의 삭제 실행 지원 없음 |

`commercial-policy` 질문은 양쪽 정확 인용·출처·해시·권한, 불명확한 정책, 결정자(Product policy maintainer), 결정 사항, 의존 작업과 보류 작업을 포함한다. 이 질문은 **자동 분석기가 확정한 충돌이 아니라 고정된 호출자 제안**이다. 해결했다고 기록하거나 내용 변경 승인으로 사용하지 않는다.

전역 pending 질문의 영향 범위를 알 수 없으면 변경을 보류한다. 호출자가 별도로 고정한 `question_scopes`가 있는 경우에만 전역 질문을 해당 문서/정보 단위에 한정한다. 문서 자체 질문은 축소할 수 없다. 명시 링크·공유 리터럴 후보·상위 절 문맥·목적지와 작업 의존성을 따라 질문 영향을 전달한다. 알 수 없는 의존 작업, cycle, 충돌하는 배치/앵커, 미해결 참조는 보류하고 독립 작업은 남긴다.

지원은 계획 형태의 적격성이다. KEEP(읽기 전용은 reference_only), 제한된 문단 PLACE, 다른 edit 목적지 끝 append MOVE, 기존 expression의 제한된 REVISE/COMPRESS 설정, 같은 문서·문맥의 정확 동일 문단 CONSOLIDATE만 검토한다. 조건 문맥을 바꿀 가능성이 있으면 보류한다. format_only 내용 변경은 거부하고 별도 변환 정책이 없는 FORMAT도 보류한다. 범용 의역·새 문서·복잡한 목적지 내부 MOVE/REMOVE는 unsupported 또는 권한 거부다.

`eligible`에도 원문/필수 제약 보존과 별도 의미 검토 의무가 남는다. 자유문장 제약을 기계적으로 모두 충족했다고 주장하지 않는다. 모든 결과는 REVIEW, semantic unresolved, execution not_run, execution_allowed=false, delivery_approved=false, stage_transition_allowed=false다. `organization_complete=false`는 포괄 요청의 의미적 작업 분해를 완료했다는 주장을 차단한다.

## IR-001–003 적용 결과

[요약 JSON](summary.json), 사례별 `*-analysis.json`과 `*-plan.json` 참조.

| 입력 | 문서 | 정보 단위 | 원문 범위 | 기본 계획 | HITL |
|---|---:|---:|---|---|---:|
| IR-001 | 7/7 | 37 | 전체 제공 자료 포함 | KEEP eligible 37 + 요청 작업 분해 held 1 | 1 |
| IR-002 | 4/4 | 19 | 전체 제공 자료 포함 | KEEP eligible 19 + 요청 작업 분해 held 1 | 1 |
| IR-003 | 3/3 | 11 | 전체 제공 자료 포함 | KEEP eligible 11 + 요청 작업 분해 held 1 | 3 |

기본 계획에 사례별 변경 정답·우선순위·특정 결과 문구를 넣지 않았다. IR-003의 전역 질문 2건은 유지되고 포괄 요청 분해에 연결되며, 문서 내용/공유 범위를 확정하지 않는다. 원문 보존 KEEP는 변경 권한을 요구하지 않으므로 전역 질문만으로 막지 않는다. 전체 문서군이 수용됐다는 것과 의미 분석/실행 성공은 별개다.

## 실제 원문에서 관찰한 충돌과 단순 미확정의 구분

아래는 **이 작업에서 제공 원문을 정적으로 읽어 관찰한 사항**이며, 결정론적 분석기의 자동 충돌 발견 결과가 아니다. 평가 답안·기준·사람 판정을 분석기에 전달하지 않았다.

- IR-001 README 21행은 “기부는 … 할 수 있습니다”, FUNDING 2행은 “금전 후원은 받지 않습니다”라고 쓴다. 참여 경로의 안내에 상반된 함의가 있으며 현행 정책을 정할 승인 근거는 이 두 문장만으로 부족하다. 기존 문구를 임의 변경하지 않고 정책 담당자의 판단이 필요하다.
- IR-002 design 5–7행은 “모든 환경에서 30초”, ADR 2–7행은 적용일 이후 운영 환경 60초·개발 환경 30초를 명시한다. 이는 같은 현재 적용 범위에 대한 수치/조건 충돌이다. 과거 30초 기록은 시점이 다르므로 그 자체가 현재 정책과 모순이라는 뜻은 아니다.
- IR-002 design 14–15행의 안정적 서비스 단정은 weekly의 기간·소표본·시점 혼재 및 일반 안정성 미입증 설명과 근거 위상이 맞지 않는다. 단순히 95%라는 숫자가 같다는 이유로 동등한 주장이라고 처리할 수 없다.

반면 공유 숫자/명령, 정확 문단 중복, 독자·목적 관련성, IR-003의 회의 대상·공유 범위·내용 권한은 별도의 확인/추가 분석 항목이다. 자동 분석 결과의 `confirmed_semantic_conflicts=[]`와 `semantic_analysis_complete=false`는 이 한계를 명시한다. 이 세 건의 정적 관찰을 Core의 의미 검증 PASS나 사례별 점수로 바꾸지 않았다.

## 검증·보존

[최종 공식 검증 JSON](evidence-validation.json): **PASS, 31 suites / 917 tests, failures/errors/skips/expected failures/unexpected successes 모두 0**. Core 431개, 파일럿 63개를 포함한다. 새 테스트는 Core 32개 + 파일럿 4개다. 1차 916개 PASS 뒤 읽기·쓰기 의존성 회귀를 추가해 새 결과 경로로 917개를 다시 검증했다. Red→Green 경로와 최종 공식 결과를 기록한다. 최종 검토에서 작업이 다른 작업의 읽기 근거를 변경하는 경우도 보류하도록 추가했다. 코드 리뷰에서 상위 절 조건, 조건이 있는 목적지, 참조 문서 안의 단위 범위 HITL 누락, 미해결 링크를 재현해 보류/의존성 검사로 수정했다. 최초 parser 연결 시 누락했던 snapshot SHA를 기존 partition API 계약에 맞춰 보완했다. 초기 테스트의 무효 변조(기존 edit 값을 edit로 재설정)와 빈 REVISE 설정을 수정했으며 기대 상태나 기존 검증 기준을 완화하지 않았다.

[보존 검사](preservation.json): 시작 HEAD `7970ef7caad6fea2a7295597ffa8efa0709083d3`의 기존 추적 파일 **1,072개 SHA-256 모두 일치**, 다른 워크트리 **15곳의 Git 상태 일치**. 원본·골드·평가 기준·사람 판단, Qwen/DeepSeek 기록·예산 원장, 기존 G1/Core와 다른 워크트리를 보존했다. `.env`를 읽거나 변경하지 않았다. 모델/API 호출 0회이며 생성기는 실제 후보 문서를 만들지 않는다.

재현:

```sh
python3 -m unittest discover -s experiments/full_document_control
python3 -m unittest discover -s experiments/integrated_reconstruction_pilot_20261117
python3 experiments/integrated_reconstruction_pilot_20261117/g2_ab_offline.py --output /tmp/logicwrite-g2-new-output
python3 tools/evidence_validation/run.py --output /tmp/logicwrite-g2-new-evidence.json
```

오프라인 결과 디렉터리는 새 경로만 허용한다. 공식 runner는 저장소 밖 새 결과 경로를 사용하며 역사 증거/현재 Core 검증을 구분한다. 실제 최종 원본은 `/tmp/logicwrite-g2-ab-evidence-final-20261118.json`이고 이 디렉터리에 복사했다. 공식 JSON의 `current_code`는 실행 중 고정된 source snapshot을 기록하며, 실행 후 추가한 검증 JSON 복사본/보고서 결과 설명 자체를 포함하는 순환 해시는 주장하지 않는다. 원격 CI 결과와도 구별한다.

## 현재 한계와 G2-C 연결 시 필요한 일

G2-A는 문서군 전체의 원문 기반 분석/추적 기반이며 범용 의미 주장 추출·정책 우선순위·충돌 발견·동등성·독자 관련성을 확정하지 않는다. 단순 cue 정규식은 완전한 언어 분석기가 아니고 자연어 조건을 모두 찾는다고 보장하지 않는다. G2-B는 출처가 고정된 명시적 제안을 판단하며, 포괄 요청을 자율적으로 완성된 Organization으로 만드는 단계는 미확정이다. 관계가 분명하지 않으면 보류하므로 과잉 보류 가능성이 있다. 큰 문서군의 index/closure 성능 한도도 별도 측정하지 않았다.

G2-C에는 이 계획을 기존 단일 문서 Organization/Expression/Reconstruction 계약으로 안전하게 연결할 전용 bridge, 완전한 source/destination snapshot/계획 pin 재검사, 범위별 보류와 변경 trace/보존 ledger, 읽기 전용/format_only 보호, 결정 후 새 계약·재계획이 필요하다. `eligible`을 실행 승인으로 쓰면 안 된다. 의미 관계/제약을 검토할 별도 인터페이스와 검토 증거를 추가하더라도 자체 확정이나 G3 승인 우회는 불가하다. 이 작업에서는 G2-C를 시작하지 않는다.

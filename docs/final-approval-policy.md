# Core 2-B: 최종 승인 계약과 증거 검증

## 현재 지원 범위

실제 승인 발급은 비활성화되어 있다. 승인자 인증과 영속 증거 저장소가 구현되어 있지 않으므로, 정책 검사를 만족해도 `gate_state: REVIEW`, `delivery_approved: false`, `stage_transition_allowed: false`, `issuance_enabled: false`다. 확인된 구조·의미 위반은 FAIL이다. `policy_state: APPROVED`는 명시적으로 구성한 **테스트용 신뢰 출처를 통한 정책 성공**만 뜻한다. 실제 사람 인증·의미 정답 검증·문서 적용의 증거가 아니다.

사용자가 승인한 접근은 계약·정책 검사와 테스트용 신뢰 어댑터까지 구현하는 것이다. 외부 IdP 및 영속 승인 저장소를 구축하는 대안은 이번 범위에서 제외했다. 호출자의 `approved: true`, 모델 응답, 자기 해시만으로 권한을 부여하는 접근은 채택하지 않는다.

## 기존 인터페이스와 책임

| 산출물/인터페이스 | 책임 및 무결성 경계 |
| --- | --- |
| `final_report` / `final_validator.validate_final_result` | 실제 입력·출력·ledger·trace·계약으로 구조를 다시 검사한다. 자기 해시는 변경 탐지이며 승인자 인증이 아니다. 기존 고정 검사와 상태를 변경하지 않는다. |
| `final_semantic_report` / `final_semantic_validator` | 전체 출력 의미 검사와 선택적 모델 검토. 실제 아티팩트 본문 바인딩, 구조 보고서 재계산, 현재 프로세스 `_RECEIPTS`의 원본과 일치해야 한다. `supported`도 승인 근거를 대신하지 않는다. |
| `final_audit` / `pipeline.validate_final_output` | 구조·의미 보고서를 묶는다. 검증 시 구조와 합성 결과를 재계산하고 현재 의미 실행 영수증을 확인한다. |
| `integration.run_pipeline` | 후보와 기존 보고서에 별도 `approval_report`를 추가한다. CLI에는 승인 발급/신뢰 출처 등록 옵션이 없다. |
| `RevisionController` | 실패 시 하위 보고서와 `approval_request`, `approval_report`를 무효화하고 중단한다. 자동 수정·재시도하지 않는다. 결정 기록은 과거 감사 데이터이며 재사용 권한이 아니다. |

구조 보고서의 `FINAL_SEMANTIC_REVIEW_NOT_IMPLEMENTED`, `FINAL_APPROVAL_NOT_IMPLEMENTED` 두 안내는 새 단계에서 각각 별도로 평가하므로 사람에게 해결을 요구할 문서 사실 목록에서 제외한다. 보고서 원문이나 그 해시를 변경하지 않는다. 나머지 구조 WARNING과 의미 검사 전체는 사람의 명시 검토 대상이다.

## 버전 고정 계약

`final_approval.build_approval_request(bundle, analysis, org, preview, result, audit, *, destination_snapshots=None)`는 `final-approval-request-v1`을 만든다.

- 원본·모든 목적지·최종 후보의 문서 ID, 스냅샷 ID, 버전, 콘텐츠 SHA-256을 범위에 포함한다. 전체 후보 집합만 승인 범위이며 일부 문서 승인이나 적용 권한으로 확장하지 않는다.
- Writing Contract, 실제 bundle, 분석·배치·표현·후보 본문, 목적지 목록, 전체 final audit를 각각 canonical JSON SHA-256으로 고정한다. 자기 해시 필드만 비교하지 않는다.
- 구조 보고서 및 의미 보고서 해시·상태, 구조 검사별 상태, 의미 실행 상태, 현재 audit 영수증 검증 결과를 포함한다.
- 모든 의미 검사에는 `semantic:<check_id>`, 다른 구조 경고에는 위치와 finding 해시에 결합된 항목 ID를 부여한다. 모델의 supported 여부에 관계없이 전부 사람 검토가 필요하다.
- 정책 버전, 최대 결정 유효기간 86400초, 검증 실행 증거의 최대 나이 900초, 아티팩트/정책 변경·만료·취소·영수증 소실 및 매 평가 시 재검증 조건을 포함한다. 요청 자체는 실행·승인 증거가 아니다.

결정 기록 `final-approval-record-v1`은 다음 필드만 허용한다.

| 필드 | 의미 |
| --- | --- |
| `approval_id`, `request_sha256`, `scope` | 독립 저장소에서 찾을 식별자 및 정확히 일치해야 하는 요청·전체 후보 범위 |
| `actor` | `subject`, `issuer`, `kind: human`; 독립 출처가 확인한 신원과 일치해야 함 |
| `decision`, `reason` | `approve`, `reject`, `hold` 중 하나와 비어 있지 않은 사유 |
| `resolutions` | 항목별 `item_id`, `judgment: accepted`, 사람의 판단 사유, 근거 span 목록 |
| `issued_at`, `expires_at` | UTC Unix 정수 초. 미래 발급 거부, 만료 시각은 배타적, 유효기간 최대 24시간 |
| `version`, `record_sha256` | 고정 버전과 자기 해시. 독립 저장소 원본 대조를 대체하지 않음 |

각 해결 근거에는 side, 문서 ID, snapshot SHA-256, Unicode codepoint start/end, 실제 quote가 필요하다. 현재 원본/목적지/출력의 유효 범위와 일치하고, 비어 있지 않은 모든 문서의 source/output 양쪽을 포함해야 한다. 중복·알 수 없는 항목이나 빈 사유/근거는 해결로 인정하지 않는다. 이는 인용의 존재 검증이며, 사람 판단의 진실성을 기계적으로 증명하지 않는다.

## 신뢰 출처와 정책 평가

`evaluate_final_approval(..., audit, decision_record=None, *, destination_snapshots=None, evidence_source=None)`를 호출한다. 신뢰 출처는 모델 JSON이나 CLI 인수가 아닌 **신뢰된 호스트 코드의 구성**이다. 기본값은 없음이다. 이번 구현은 `mode == 'test_only'`인 출처만 받으며 `production`을 포함한 다른 모드는 거부한다.

출처 계약은 `source_id`, `mode`, `lookup(approval_id)`다. lookup은 독립 저장한 원본 `record`, 인증된 `subject`, `issuer`, `actor_kind: human`, 명시적인 `revoked: false`를 반환해야 한다. 취소 시 `revoked: true`와 선택적 `revoked_at`, `revocation_reason`을 반환한다. 호출자가 평가 함수에 기록을 제출하는 것만으로 저장소에 등록할 수 없다. 테스트 저장소 구현은 테스트 파일에만 있다. 실제 인증·저장·취소 API나 서명 발급 도구는 제공하지 않는다.

검사 순서는 다음과 같다.

1. 현재 입력으로 요청을 재생성하고 기존 final audit/의미 실행 영수증을 검증한다. 프로세스가 영수증을 등록한 monotonic 시각으로부터 900초 미만이어야 하며, caller가 적은 발급 시각이나 재해시로 갱신할 수 없다. 승인 결정의 24시간 유효기간과 별개로, 15분이 지난 검증은 새 audit와 새 결정을 요구한다. 다른 문서·버전·재해시 보고서·프로세스 재시작 후 영수증 소실은 INVALID다.
2. 구조 FAIL 또는 의미 violated는 사람도 우회할 수 없으며 BLOCKED/FAIL이다. 완전한 후보가 없으면 HOLD다. 결정이 없으면 UNAPPROVED/REVIEW다.
3. 독립 출처의 원본과 결정 기록 전체를 대조하고 신원·범위·버전·시간·취소를 검사한다. 위조·미등록·변조 후 재해시·만료·취소·출처 오류는 INVALID다. 조회 예외의 원문은 보고하지 않는다.
4. 조회 후 실제 입력 바인딩과 실행 영수증을 다시 검사하여 callback 중 변경도 차단한다. 만료도 다시 검사한다.
5. 거절·보류는 REJECTED/HOLD로 기록한다. 승인에는 필요한 모든 사람 검토의 근거가 있어야 한다. 모델 실행이 실패·불완전·시간/예산 제한에 걸렸으면 승인 대신 HOLD로 두고 재검증을 요구한다. 선택적 모델 검토를 실행하지 않은 `not_run`은 전 항목을 사람이 직접 판단할 수 있지만 자동 해결하지 않는다.
6. 조건을 충족하면 테스트 정책 상태만 APPROVED다. 실제 승인 발급과 파일 적용은 활성화되지 않는다.

반환 `final-approval-policy-v1`은 요청, 결정 원문과 사유, 출처의 취소 관측, 해결 후 남은 항목, 정책 결과·고정 오류 코드를 유지한다. 보고서를 나중에 사용할 때는 `verify_approval_report(..., report, evidence_source=...)`로 **현재 상태를 재평가**한다. 단순한 report JSON/해시를 승인 토큰으로 사용하면 안 된다. `valid`는 정확한 관측 보고서의 현재 증거 유효성으로, 거절·보류에도 true일 수 있다. delivery 권한이 아니다.

## 지원하지 않는 범위

실제 승인 발급, IdP/사용자 인증, 영속 저장소·서명 키 관리, 재시작 후 영수증 복구, 영속 감사 로그, 실시간 취소 구독, 실제 파일 적용 및 다중 프로세스 트랜잭션은 지원하지 않는다. 신뢰된 호스트·출처·프로세스 메모리·시계 자체를 공격자가 제어하는 경우는 보호 경계 밖이다. 출처의 취소 상태는 조회 시 관측이며 조회 직후의 취소를 원자적으로 보장하지 않는다. 보고서를 저장하려면 호스트가 별도 영속 저장 및 재검증 정책을 제공해야 한다.

기존 승인 정책은 완화하지 않는다. PR #17 잠정 골든셋을 정답이나 승인 근거로 참조하지 않는다. 자동 수정 루프, 실제 파일 수정, RAG, LangGraph는 구현하지 않는다.

## 검증

신규 반례는 `experiments/full_document_control/test_final_approval.py`에 있다. 정상 승인 테스트의 신원·결정·의미 검토는 전부 합성 fixture이며 실제 사람 승인 실험이 아니다.

```sh
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'
python3 -m unittest discover -s experiments/minimal_gate -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_analysis -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_ab -p 'test_*.py'
```

2026-11-10 로컬 결과: 전체 Core 303개(신규 승인 31개 포함), minimal gate 31개, extraction analysis 27개, extraction AB 17개로 총 **378개 통과**. 독립 코드 리뷰에서 재현 가능한 우회 결함은 발견되지 않았다. 실제 사람 인증, 모델 의미 품질, 영속 저장소, 원격 CI 성공을 뜻하지 않는다.

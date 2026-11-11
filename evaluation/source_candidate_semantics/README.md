# Source/Candidate 의미 평가 어댑터

PR #23 head `110c715` 위의 별도 개발이다. 제공된 원문·수정본·작성 계약 전체를 기존 독립 의미 검증기의 요청 실행·응답·인용 검증 경로로 연결한다. **외부 수정본을 Core가 생성한 결과로 꾸미지 않으며, 최종 승인이나 파일 반영 권한이 없다.** PR #22의 provisional 17건은 이 평가에서 읽지 않는다.

## 기존 PR 통합 점검

| 항목 | 확인 결과 |
| --- | --- |
| 공통 main / 두 PR head | `29dd271` / #22 `ef7a669`, #23 `110c715` |
| 임시 통합 커밋 | `d5891711ab84ae0021850f79f1bebfc541cd4af8` — 로컬 검증 전용 |
| 충돌 / 기능 의존성 | 변경 경로 교집합 0, 실제 merge 충돌 0, 두 PR 사이 기능 의존성 없음 |
| 전체 회귀 | 562개 통과. [전체 명령·출력](records/integration-22-23-tests.json) |
| 데이터 보존 | 기존 평가 파일 186개 일치, 활성 G3 골드 12, provisional 사용자 판정 대기 17, 신규 골드 0 |
| 원격 상태 | 두 PR Ready for review, 미병합. 등록·실행된 CI 체크 없음. 로컬 테스트와 구별 |

[통합 요약](records/integration-summary.json)은 당시 head와 결과를 고정한다. 새 어댑터 PR은 #23에 의존하는 stacked PR이며 #22에는 의존하지 않는다. main으로 병합했다는 기록이 아니다.

## 설계와 실제 지원 범위

기존 `validate_final_semantics`는 재구성 산출물·실행 증거를 검증하므로 임의의 외부 수정본을 직접 넣을 수 없다. 기존 내부 리터럴 진단에 가정한 행 대응을 붙이는 접근은 편집 계보·관계를 확인한 것으로 오해할 수 있다. 이번에는 같은 모듈에 별도 `evaluate_snapshot_pair` 평가 진입점을 두고 기존 `_call`과 `_validate_reviews`를 재사용한다. 최종 검증·승인 경로는 변경하지 않았다.

| 입력 또는 기능 | 이번 범위 |
| --- | --- |
| 단일 문서 | 명시적으로 완전한 source/candidate 쌍을 전체 비교 |
| 다중 문서 / 목적지 | 양쪽 모두 전체 문서를 제공하고, 양쪽 문서 ID 집합이 계약 출력 집합과 같은 경우 전체 문맥 검토 |
| 문서 간 MOVE / 링크 / 조건 노출 | 계약과 전체 문서 문맥을 reviewer에게 전달. 자동 관계 추출·링크 접근·파일 이동·경로 해소 증거를 생성하지 않음 |
| 서로 다른 source/candidate ID 집합 | 기준 버전 선택·문서 재식별 미지원. 높은 버전을 임의로 선택하지 않음 |
| 부족한 문맥 / `pending_contract` / 부분 문서 | reviewer 호출 전 unsupported/REVIEW |
| 모델 없음 / 예산 초과 / 실패 / 시간 초과 / 불완전 인용 | 미평가·unresolved/REVIEW |
| 완전하고 유효한 7개 검토 모두 supported | supplied evidence에 관한 모델 보조 판정 supported, **gate REVIEW** |
| 완전한 7개 검토 중 contradicted/overstated 존재 | 모델 보조 위반 판정 contradicted/FAIL. 사람·정책 승인과 무관 |

7개 검토는 CLAIM_FACTS, QUANTITY_SCOPE, POLARITY_CONDITIONS, ADDITIONS_OMISSIONS, CONTRADICTIONS, MOVE_CONSOLIDATION, PROVENANCE다. 각 검토에서 모든 snapshot 참조 및 비어 있지 않은 모든 원문·수정 문서의 정확한 Unicode 위치·인용을 요구한다. 일부 검토 누락·인용 불일치·모델의 승인 주장을 유효한 평가로 받아들이지 않는다. 합성 테스트 callback의 canned 답변은 프로토콜 시험이며 실사례 의미 성능 근거가 아니다.

새 API는 편집 ledger, 추출 unit, 배치 계획 또는 provenance receipt를 만들지 않으며 기존 `_RECEIPTS`에 등록하지 않는다. 새 리터럴 탐지 휴리스틱도 추가하지 않았다. 실제 레거시 재구성 경로에서 수행하는 결정론적 검사와 결과를 혼합하지 않는다. 평가 보고서 해시는 무결성 바인딩이며, 사람 승인이나 외부 모델 진실성 인증이 아니다.

SP admission 검사는 기존 `evaluation/semantic_pilot/requirements.txt`의 `jsonschema>=4.10.3,<5`를 사용한다. 레거시 Core 경로에는 새 의존성을 주입하지 않지만, 새 어댑터와 이를 포함한 테스트 실행에는 이 평가 의존성이 필요하다.

## SP 계약과 Core의 대응

| SP 필드 | 전달 / 한계 |
| --- | --- |
| contract_id, version, audience, purpose, language | 평가 요청의 writing_contract에 원문 그대로 전달 |
| output_document_ids | 평가 admission에서 후보 및 원문 ID 집합 검증. 실제 Core의 output_scopes·ScopeRef로 추정 변환하지 않음 |
| required_information.id / description / exposure | 설명과 노출 정책 그대로 reviewer에 전달. expected_literal·scope_id·조건 관계를 추론 생성하지 않음 |
| constraints | 원문 그대로 의미 검토 조건으로 전달. 실제 정책 승인이나 조직화 배치 명령으로 변환하지 않음 |
| SP에 없는 Core 필드 | document_type·register·concrete scope·relation 등 정식 Core 계약 필드를 채워 넣지 않음 |
| pending_contract / missing_context | 모델 추측으로 채우지 않고 보류 |

따라서 정식 Core WritingContract의 전 필드와 자동 대응하는 어댑터가 아니다. `contract_mapping`에 verbatim 전달 필드와 추정하지 않은 항목을 기록한다. 모델은 계약 의미를 읽지만 그 사실이 runtime 조직화/승인 정책 충족을 뜻하지 않는다.

## 완전성·버전·출처의 신뢰 수준

SP `availability: complete`가 명시된 경우에만 평가 스냅샷의 complete coverage로 변환한다. 누락·partial·not_provided는 complete로 기본 설정하지 않는다. 문서 SHA-256과 실제 UTF-8 본문, 버전과 provenance 버전을 대조한다. 공개 Git 자료는 40자리 커밋·저장소/경로·고정 URL의 일관성과 제공 본문의 Git blob SHA·스냅샷 SHA를 검사한다. 이는 **제공 메타데이터·본문의 내부 일관성 검사**이며 원격 저장소를 새로 조회한 출처 인증이 아니다. 입력의 snapshot_path를 열거나 원격 URL에 접근하지 않는다. controlled_synthetic은 실제 관측·승인 기록으로 승격하지 않는다.

기존 Organization은 coverage가 없는 최소 목적지(content/hash/version)를 계속 잠정적으로 `verified_context`/이동 가능으로 표시한다. Reconstruction은 그 형식의 누락된 complete coverage·snapshot_id·media_type을 거부한다. 새 어댑터도 명시적 완전성 없는 문서를 거부한다. 이 차이를 `test_native_missing_coverage_stays_legacy_organization_only`로 고정했으며 기존 호환성이나 승인 정책을 변경하지 않았다.

## 실제 G3 실행 결과

입력은 활성 G3 SP-001~012만 고정 열거한다. predict는 정답/answers를 읽지 않는다. compare만 저장된 예측을 받은 뒤 활성 골드 manifest와 해시를 대조한다. 사후 비교에서 요청을 모델 없이 재구성하고 요청 해시·snapshot 참조·정확 인용·7개 응답·개별/전체 판정·승인 false를 다시 검사한다. 검증된 모델 응답 supported/contradicted만 각각 PRESERVED/VIOLATION의 보조 비교값으로 대응하며 Core REVIEW를 SP 정답으로 바꾸지 않는다.

| 사례 | 기본 offline 결과 / 후속 |
| --- | --- |
| SP-001, SP-005 | 전체 요청이 기본 48,000자 예산 초과. 자르지 않고 REVIEW |
| SP-002~004, SP-006~008 | 입력 admission 가능, reviewer 미실행으로 REVIEW |
| SP-009 | 목적지 전후 전체 미제공·missing_context. 모델 호출 없음 |
| SP-010 | 승인 기준 버전 미확정·문서 집합 불일치. 모델 호출 없음 |
| SP-011 | 조건 현지 노출 의무 미확정·pending_contract. 모델 호출 없음 |
| SP-012 | 잘린 수정 결과·missing_context. 모델 호출 없음 |

[offline 예측](records/offline-predictions.json)과 [사후 비교](records/offline-comparison.json): 12건 중 **평가 완료 0, 정확도 null**. 입력 admission 가능과 의미 평가 완료를 구분한다. unresolved·미지원·실행 실패를 보존 정답으로 취급하거나 성능 분모에 넣지 않는다. 분모는 완전한 인용 검토와 확정적인 모델 보조 판정이 있는 사례만이며 제외 사례도 별도 기록한다.

SP-005→008 우선 파일럿은 실제 CLI 모델 목록에서 확인한 요청 모델 `gemini-4-argon-medium`, 최대 호출 1회, 재시도 없음, 입력 예산 100,000자, provider 제한 30초로 실행했다. SP-005 요청은 70,560자이며 6.21초 후 exit 3 / quota_exhausted(429)로 빈 응답을 받았다. 뒤의 세 사례는 호출하지 않았다. [호출 메타데이터·예측](records/live-pilot-predictions.json), [사후 비교](records/live-pilot-comparison.json)에 기록했다. **평가 완료 0, 정확도 null**이며 양태·복합 부정/수량·선행조건 삭제·무근거 추가 탐지 성공을 주장하지 않는다.

요청 모델과 실제 제공 모델 확인은 다르다. 토큰 사용량·청구 비용은 provider가 제공하지 않아 null이며 비용을 0원으로 추정하지 않는다. 문서 초안/독립 검토용 Antigravity 호출도 같은 할당량 오류로 실패했다. 구현은 별도 Codex 독립 검토를 거쳤고 문서는 로컬 근거에 따라 작성했다.

## 재현과 다음 작업

최종 전체 회귀 **571개 통과**: 기존 #23의 543개 + 어댑터 16개 + 실행·사후 비교 12개. Core 디렉터리에서는 기존 342개 + 신규 16개 = **358개 통과**다. [전체 명령·출력과 Python 파일 해시](records/all-tests.json)에 검증 당시 HEAD와 실제 테스트한 작업 트리를 구분해 기록했다. 원래 main의 평가 파일 186개와 기존 G3 manifest/판정 이력은 바이트 단위로 일치한다.

초기 미구현 실패와 경계 보완의 red→green 기록은 `records/*red*.txt`와 회귀 테스트에 있다. 독립 검토가 찾은 요청 바인딩 교체·검토 응답과 요약 판정 불일치·중첩 승인 주장 수용을 각각 실패 테스트로 재현한 뒤 사후 비교에서 거부하도록 수정했다. 독립 재검토에서 차단 문제가 없음을 확인했다. 이 테스트들은 의미 성능 평가나 실제 사람 판단을 생성하지 않는다.

```bash
# API/실행 경로·안전 경계 회귀
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'
python3 -m unittest discover -s evaluation/source_candidate_semantics -p 'test_*.py'

# 원문 입력만 읽는 단계와 정답 사후 비교를 별도 프로세스로 실행
python3 evaluation/source_candidate_semantics/run.py predict /tmp/predictions.json
python3 evaluation/source_candidate_semantics/run.py compare /tmp/predictions.json /tmp/comparison.json

# 비용/호출 한도를 명시한 파일럿; 실패 후 후속 호출하지 않음
python3 evaluation/source_candidate_semantics/run.py predict /tmp/pilot.json \
  --case SP-005 --case SP-006 --case SP-007 --case SP-008 \
  --provider agy --model gemini-4-argon-medium --max-calls 1 \
  --max-review-chars 100000 --timeout 30

# 별도 Python 프로세스로 저장소 전체 회귀
python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/all-tests.json
```

후속 우선순위는 P1: 가용한 provider와 비용 한도로 SP-005~008의 전체 문맥 검토를 실제 완료하고 원응답·인용·실패를 분석하는 것이다. P2: 권한자가 지정한 기준 버전, 완전한 목적지/링크 역할과 확정된 노출 계약, 전체 수정 결과를 명시적 입력으로 받는 범위를 확장한다. 추측하는 baseline resolver나 모든 위반을 맞추는 휴리스틱은 추가하지 않는다. provisional 17건의 사람 검수와 Core 모델 결과를 연결하지 않는다.

# Expression Refinement 프로토타입

`expression.py`는 실제 원문 범위에 대한 표현 수정 후보를 생성하고, `expression_validator.py`는 현재 입력·배치·결과 텍스트를 독립 재검증한다. 이 모듈 자체는 발췌 Preview만 생성한다. PR #15의 전체 후보 재구성·최종 구조 검증은 별도 [INTEGRATION](INTEGRATION.md) 경로이며, 승인 실행은 여전히 미구현이다. 결과는 항상 `delivery_state: preview`, `output_snapshots: []`이며, 위반은 `FAIL`, 나머지는 `REVIEW`다. `expression_checks_state`와 최종 전달 승인은 별개다.

## 실행과 생성 인터페이스

Python 3 표준 라이브러리만 사용한다. 기존 파이프라인에서 저장한 입력·분석·OrganizationPlan JSON을 전달한다. CLI는 결과를 stdout으로 출력하며 파일을 쓰는 옵션이 없다.

```bash
python3 experiments/full_document_control/expression.py \
  input-bundle.json analysis.json organization-plan.json \
  --operations expression-operations.json \
  --destination-snapshots destination-snapshots.json
```

두 선택 옵션은 생략할 수 있다. operations는 `{"u-timeout": "REVISE"}` 같은 객체이며 `KEEP`, `REVISE`, `COMPRESS`만 허용한다. 목적지 옵션은 실제 목적지 스냅샷 객체들의 JSON 배열이다. 입력 오류는 `execution_error` JSON과 종료 코드 2로 반환한다. 결과 JSON을 저장하려면 호출자가 원본과 다른 경로를 선택해야 한다.

| API | 역할 |
| --- | --- |
| `build_expression_plan(bundle, analysis, organization_plan, ...)` | Organization 독립 검사 후 원본 단위·범위·요소·관계·배치에 고정한 계획 생성. 상위 `FAIL`/`STOPPED`면 거부 |
| `generate_revision_result(..., generator=None, operations=None, ...)` | 미검증 Preview 생성. 이 반환값 자체는 승인된 결과가 아님 |
| `validate_expression_result(bundle, analysis, organization_plan, result, ...)` | 생성기 응답과 계획 findings에 의존하지 않고 실제 출력 검사 |
| `create_expression_preview(...)` | 생성과 독립 검증을 함께 수행해 `{revision_result, validation_report, preview_only, next_stage_allowed}` 반환 |
| `execute_authorized_expression(...)` | `NOT_IMPLEMENTED`; 상위 검사를 수행하지만 실제 표현 단계 진입·전달은 항상 금지 |

생성기는 `callable(request) -> {"text": str}` 또는 같은 계약의 `.generate(request)` 객체다. request에는 `unit_id`, 정확한 `before`, `operation`, `excluded`, `constraints`, `protected_elements`, `relations`, `source_span`을 깊은 복사로 제공한다. 모델별 SDK는 포함하지 않는다. 어댑터 실패·잘못된 응답은 원문을 유지하고 `GENERATION_ERROR`로 보류한다. 응답의 `PASS`/전달 승인 주장은 별도 위반이며 실제 출력 검사는 항상 수행한다. 임의 Python 어댑터를 보안 샌드박스로 격리하는 기능은 없다.

생성 응답에서 허용하는 데이터는 비어 있지 않은 일반 문자열 `text`와, 중첩 승인 주장의 존재 여부를 줄인 boolean 신호뿐이다. 임의 메타데이터·인증정보·내부 로그·응답 원문·예외 메시지/클래스명은 기록하지 않는다. `text`는 조각 `content`를 기준으로 기존 change_set의 전후 추적에만 사용하고 `generation`에 다시 복사하지 않는다. Python stdout/stderr 및 표준 logging은 어댑터 호출 동안 버리고 원래 로깅 설정은 예외 발생 시에도 복구한다. 이 억제는 동기식 프로토타입의 프로세스 전역 설정이며 동시 실행 격리 기능이 아니다. OS 파일 디스크립터 직접 쓰기·별도 프로세스·외부 전송을 막는 보안 샌드박스도 아니다.

`preview_fragments[].generation`에는 `status`(`completed`/`execution_error`), `approval_claim_detected`(boolean), `error_code`(`null`/`INVALID_RESPONSE`/`GENERATOR_EXCEPTION`), `receipt_id`만 저장한다. 잘못된 응답에 승인 주장이 같이 있어도 신호를 남겨 위반으로 판정한다. 생성 실패는 원문을 복구해도 `GENERATION_ERROR`, `expression_checks_state: unresolved`, `gate_state: REVIEW`다(별도 확정 위반은 기존처럼 FAIL).

실행 경계는 모델 응답 대신 위 최소 신호와 실행 ID·계획/입출력 다이제스트만 프로세스 내부에 보관해 재대조한다. `meta.generation_run_id`와 `receipt_id`는 승인 권한이 아니며, 다른 실행의 성공 기록을 붙이거나 실패 신호를 바꾼 경우 `GENERATION_RECORD_MISMATCH`로 차단한다. findings를 지워도 실행 기록에서 실패·승인 위반을 복원한다. 기록은 최대 4,096건이며 만료·프로세스 재시작·삭제/알 수 없는 ID로 확인할 수 없으면 `GENERATION_RECORD_UNVERIFIED`와 unresolved/REVIEW를 유지한다. 내보낸 JSON과 재계산한 해시만으로 실행 성공을 인증할 수 없으며 같은 프로세스에서 임의 Python 코드로 레지스트리를 바꾸는 공격까지 방어하지 않는다.

## 실제 수정 기능과 제약

| 기능 | 구현 범위 |
| --- | --- |
| `REVISE` | 제한된 한국어 종결 표현 변환과 명시적 용어 치환. 더 넓은 자연스러운 재작성은 생성 어댑터로 제안 가능 |
| `COMPRESS` | 인접한 동일 단어 반복 및 연속 가로 공백 정리. 문장·정보 단위 삭제 또는 중복 통합은 수행하지 않음 |
| 문체 | `WritingContract.register`의 한다체·합니다체·해요체 중 구현된 종결 표현 변환. 완전한 한국어 문법·활용 분석은 아님 |
| 용어 | 문자열 제약 `TERM: 이전표현 => 표준표현`. 이미 표준 용어인 경우 재치환하지 않음 |
| 명시 제약 | `PRESERVE: 문자값`, `FORBID: 문자값`, `EXCLUDE_BLOCK: B003` |
| 수정 제외 | 코드 블록·명령 블록·인용 블록·제목·표 및 명시 제외 블록 전체. 인라인 코드·URL·큰따옴표·곡선 따옴표 및 경계 ASCII 작은따옴표 인용도 보호. 발췌가 인라인 보호 구간의 일부만 포함하면 전체 단위를 보수적으로 수정 제외 |

ASCII 작은따옴표는 단어 내부 아포스트로피(`don't`, `O'Reilly's`)·단독 소유격(`users'`)과 구분한다. 인용문 안의 축약형과 `users'` 같은 복수 소유격도 보호한다. 닫히지 않은 경계 따옴표는 그 줄 끝까지 보수적으로 보호한다. 정규식 기반이므로 중첩 인용·여러 줄 인용·선행 아포스트로피 축약형(`'tis`)의 완전한 언어적 구분은 보장하지 않으며 일부 산문이 과보호될 수 있다. 불명확한 결과는 기존 의미 검증 REVIEW를 유지한다.

해석하지 못한 자연어 제약·문체는 `CONTRACT_CONSTRAINT_UNRESOLVED`로 보류한다. 수정 제외 구간의 표준 용어·문체를 강제로 바꾸지 않는다. 입력이 이미 목표 문체이고 반복·별칭이 없으면 기본 생성 결과가 모두 `KEEP`일 수 있다. 이는 다른 입력에서 실제 변환하는 경로가 없다는 뜻이 아니다.

## ExpressionPlan과 RevisionResult 예시

다음은 **기존 테스트용 합성 입력을 메모리에서 복사**하여 합니다체 계약을 적용하는 실행 예다. 기존 sample 파일·평가 자료를 수정하지 않는다. 분석의 계약 바인딩을 새로 만들고 OrganizationPlan도 새로 생성한다. 자기 해시 재계산은 승인 증거가 아니며 최종 결과는 여전히 `REVIEW`다.

```python
import sys
sys.path.insert(0, 'experiments/full_document_control')
import test_organization, expression
fixture = test_organization.InformationOrganizationTests()
fixture.setUp()
bundle, analysis = fixture.bundle, fixture.analysis
bundle['writing_contract']['register'] = '합니다체'
analysis['contract_sha256'] = expression.pipeline.canonical_json_digest(bundle['writing_contract'])
expression.seal(analysis, 'analysis_sha256')
organization_plan = expression.organization.generate_organization_plan(bundle, analysis)
preview = expression.create_expression_preview(bundle, analysis, organization_plan)
change = next(c for c in preview['revision_result']['change_set'] if c['unit_id'] == 'u-timeout')
assert change['before'] == '기본 요청 제한 시간은 30초다.'
assert change['after'] == '기본 요청 제한 시간은 30초입니다.'
assert preview['validation_report']['gate_state'] == 'REVIEW'
```

아래는 필드 관계를 보여주는 축약 예시다. 해시와 반복 항목을 생략했으므로 그대로 검증기에 제출하는 JSON은 아니다.

```json
{
  "expression_plan": {
    "version": "expression-plan-v1",
    "analysis_ref": {
      "version": "full-document-control-prototype-v1",
      "analysis_sha256": "현재 분석의 실제 해시",
      "snapshot_id": "snap-fd-001-v1",
      "snapshot_version": "1",
      "snapshot_sha256": "원본 내용의 실제 해시",
      "contract_version": "1",
      "contract_sha256": "현재 계약의 실제 해시"
    },
    "organization_ref": {"version": "org-plan-v1", "plan_sha256": "현재 배치 계획의 실제 해시"},
    "constraints": {"register": "합니다체", "terminology": {}},
    "entries": [{
      "id": "expr-u-timeout", "unit_id": "u-timeout", "operation": "REVISE",
      "source_spans": [{"start": 82, "end": 100, "quote": "기본 요청 제한 시간은 30초다."}],
      "placement": "원본 Organization placement 객체 전체",
      "protected_elements": [{"id": "el-timeout-val", "kind": "quantity", "value": "30초"}],
      "relations": "원본 분석 관계 목록",
      "rationale": "기존 배치와 정보를 유지하며 표현 개선", "evidence": ["B003"]
    }]
  },
  "delivery_state": "preview",
  "output_snapshots": [],
  "preview_fragments": [{"fragment_id": "fragment-u-timeout-0", "unit_id": "u-timeout",
    "coverage": "excerpt", "content": "기본 요청 제한 시간은 30초입니다."}],
  "delivery_approved": false,
  "next_stage_allowed": false
}
```

실제 결과는 모든 원본 단위에 대해 KEEP까지 명시하고, `meta`, `organization_ref`, `expression_plan`, `preview_fragments`, `output_snapshots`, `change_set`, `trace`, `findings`, `delivery_state`, `revision_sha256`을 포함한다. 각 조각은 독립적인 발췌 스냅샷이다. Organization의 생략·통합·이동 후보를 표현 단계에서 실행하지 않고 원문 발췌와 기존 배치 참조를 보존한다. 같은 원문 범위를 공유하는 단위도 별도 조각으로 추적하므로 전체 문서로 이어 붙이면 안 된다.

`change_set`은 원본 `source_span`, `before`/`before_sha256`, `after`/`after_sha256`, 조각 기준 `output_span`, 실제 처리(`KEEP`/`REVISE`/`COMPRESS`), 계획 항목 ID를 연결한다. `trace`는 `unit_refs`, `element_refs`, `source_spans`, `output_spans`, `treatment`, `justification`을 가진다. 오프셋은 원본 및 정확한 결과 문자열에 대한 유니코드 코드 포인트의 반개구간 `[start,end)`다. 요소 ID의 연결 자체는 요소 의미가 보존되었다는 증명이 아니다.

## 독립 검증과 승인 경계

| 검사 | 실패·보류 동작 |
| --- | --- |
| 현재 참조·버전·다이제스트 | 오래된 분석·배치·계약·스냅샷·결과 거부. 해시를 재계산해도 현재 입력과 다시 대조 |
| 원문 및 결과 범위 | 원본 quotes를 실제 블록에서 재해석하고 단위·요소 출처와 비교. 누락·중복·새 단위·잘못된 전후 추적 차단 |
| 배치·보호 목록 | 원본 Organization placement 전체·분석 요소·관계와 대조. 독단적인 MOVE/REMOVE/ADD/CONSOLIDATE 차단 |
| 보호 문자값 | 수치·단위·버전 토큰, 식별자·귀속·시간 요소, 명시 불변 문자열·수정 제외 구간 손실 차단 |
| 의미 왜곡 신호 | 알려진 부정 소실·조건/범위 한정 소실·단정 확대·근거 없는 기능 추가 탐지. 기존 의미 검증기의 순수 검사 함수 일부를 재사용하지만 승인 정책은 변경하지 않음 |
| 계약 | 편집 가능한 산문의 명시 용어·금지 문구·충돌하는 종결 표현 검사. 미지원 자연어 규칙은 REVIEW |
| 자기 승인 | 재해시된 결과/계획의 허위 PASS·전달 승인, 생성 응답의 자기 승인 차단 |
| 의미 미확정 | 알려지지 않은 신규 주장, 의역을 포함한 모든 변경 산문은 `SEMANTIC_EQUIVALENCE_UNVERIFIED`로 REVIEW |

문자열·정규식 검사는 일반적인 의미 동일성을 증명하지 않는다. 보호 토큰의 직접 소실과 알려진 왜곡은 보수적으로 차단하므로, 안전한 의역도 거부될 수 있다. 의미 검증 모델 실행·사람 승인 등록·전체 문서 재검증은 이번 구현에 없다. 같은 문서에 분산된 주장·조건의 관계는 원본 분석 관계와 Organization 검증에 의존하며, 전체 출력의 조건 인접성·가독성은 아직 검증하지 않는다. 임의의 미탐을 자동 승인으로 바꾸지 않도록 모든 결과에서 `semantic_fidelity: unresolved`, `full_document_validation: not_run`을 유지한다.

상위 보고서를 제공하면 기존 Organization 검증기를 통해 독립 재확인한다. 상위가 REVIEW이면 격리된 Preview만 가능하고 승인된 단계 전환은 없다. 이 프로토타입은 어떤 입력에도 최종 PASS·전달 승인·실제 파일 반영을 부여하지 않는다. 해시는 내용 결합·무결성 검사용이며 작성자나 평가자 인증이 아니다.

## 설계 문서와 현재 실행 스키마의 차이

| 설계 계약 | 현재 구현·기록 |
| --- | --- |
| 공통 논리 참조·다대다 추적 | 기존 추출기의 실험용 `AnalysisResult`와 `source_spans`, 버전·SHA-256을 사용. 정식 공통 스키마 동결은 아님 |
| 다중 문서 출력과 배치 | 입력 resolver는 단일 concrete scope를 요구하지만 Organization은 여러 scope·목적지 스냅샷을 처리. 기존 코드의 차이를 수정하거나 완화하지 않음 |
| 풍부한 문체·terminology·constraints | 기존 WritingContract는 `register` 및 문자열 constraints 목록을 사용. 이번의 접두 문자열 지시문은 실험용 문법이며 resolver를 변경하지 않음 |
| ExpressionPlan 항목 목록 | 버전·참조·공통 제약을 담은 계획 객체 안의 `entries` 목록으로 구현 |
| candidate는 모든 관련 문서의 완전한 스냅샷 | 이 모듈은 preview만 반환. 별도 Reconstruction은 전체 후보를 만들 수 있지만 다중 문서의 실제 파일 적용·승인은 미구현 |
| 최종 의미·전체 문서 검증 후 전달 후보 | 자체 검사는 별도 상태로 보고하지만 최종 승인 실행은 NOT_IMPLEMENTED/REVIEW |

테스트 수와 최신 검증 결과는 [HANDOFF](HANDOFF.md)의 Expression Refinement 절을 참조한다. 기존 평가 데이터·실제 LLM 평가 결과는 변경하지 않는다.

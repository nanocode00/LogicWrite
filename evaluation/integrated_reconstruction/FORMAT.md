# 평가 파일 규약 v1 — Core 인터페이스가 아님

| 파일/영역 | 의미와 분리 기준 |
|---|---|
| `input.schema.json`, `inputs/*.json` | 모델이 볼 유일한 입력. 요청, 사용 맥락, 명시 제약, 전체 문서, 근거 위상, 권한, 공백, 제출 방식. 정답·진단 태그·검수·출처 군집 메타데이터 없음 |
| `documents[].access` | `edit`: 내용·구조 후보 가능. `format_only`: 의미/단어 변경 없는 서식 후보만 가능. `read_only`: 조회 근거로만 사용. 외부 자료·새 문서는 별도 권한 없이는 조회/생성/반영 불가 |
| `answer.schema.json`, `answers/*.json` | AI 초안. 입력 파일 바이트 해시 결합. D의 명시 제약 포인터/추론 요구/근거 판단/질문, Q의 불변 조건/금지 결과/대안 묶음/독자 과업을 분리 |
| `reference.schema.json`, `reference_outputs/*.json` | AI가 작성한 비유일 전체 결과 예시. `executed_by_system=false`. actual output·점수·효과 근거로 쓰지 않음 |
| `review.schema.json`, `reviews/*.json` | 실제 사람이 작성할 최초 판단·근거·답안 노출·반례·최종 판단·중재. 현재 전부 null. 독립성은 단순 필드 선언으로 증명되지 않음 |
| `submission.schema.json` | 향후 실행 관측 규약. 편집 전 D 관측, 실제 변경, 보류 범위, 최종 전체 문서, 실제 검증 결과, 실행 상태를 분리. 이번에는 시스템 실행/채점 데이터 없음 |
| `cases.json`, `sources.json` | 평가자 전용 계보·합성/권리·노출·진단 태그. 현재 3개 가상 프로젝트지만 독립 실자료 0개·작성 군집 1개 |

정확 근거는 입력 `document_id`의 `content`에 대한 Unicode codepoint `[start,end)`와 `quote`로 지정한다. UTF-8 SHA-256과 문자 좌표를 혼동하지 않는다. 판단 근거로 사용된 위치와 실제 지지 여부는 다르다. 현재 검증기는 인용 정확성만 확인한다.

참고 출력은 edit/format_only 문서 전체를 빠짐없이 포함한다. 읽기 전용 문서는 원본 입력으로 대조하며 출력 변경 대상으로 넣지 않는다. 후보는 문서 파일에 실제 적용하지 않는다. IR-003의 무수정 예시는 내용 편집을 보류했어도 전체 원문을 제출한 완결된 허용 응답이다.

D `decision_observation`은 외부 제출한 요약 판단·원문 근거다. `channel=unobserved`이면 D를 미관측으로 둔다. 실제 사전 고정 아티팩트의 보관·해시·순서 확인은 실행 운영자의 책임이다. `recorded_before_edit` 값만으로 과거 제출을 인증할 수 없다. 출력 효과를 계획으로 소급하지 않는다.

Q는 `execution_status=partial/failed/not_run`에서 완성본 품질 점수를 만들지 않는다. `validation_results.status`의 not_run과 pass를 구별하고, 실패는 정당한 보류가 아니다. 의미 보존·문서 목적·추론의 적절성은 별도 사람 검수 대상이다. 스키마는 이런 보고를 위한 구조이며 자동 의미 채점기나 Core runner가 아니다.

검수 기록에서 공급받지 않은 이름·시각·서명·사유를 만들지 않는다. 최초/최종 판단은 포함 승인과 다르다. 포함 승인은 현재 패키지에서는 null만 허용한다. 이후 별도 사람 결정·출처·해시를 가진 승인 절차를 만들 때 스키마를 버전 관리한다. AI가 사람 판단을 기록하더라도 실제 인용과 기록자/판정자 구분을 남겨야 한다.

## 입력 v2 — 불완전한 계약/자료 표현

기존 `input.schema.json` 및 IR-001~003 v1 바이트/해시/사람 응답은 유지한다. 새 `input-v2.schema.json`을 `schema_version=integrated-input-v2`로 선택할 수 있다. 아직 실제 v2 평가 사례·답안·사람 판단은 없다.

| v2 항목 | 해석 |
|---|---|
| `explicit_constraints: []` | 명시 제약 미제공. 권한·사실·미확정 범위는 여전히 준수 |
| `context`, `documents[].role/authority: null` | 미확정 맥락/역할/근거 위상. 문서 내용에 근거한 추론과 사용자 확인 구분 |
| `availability.document_set: complete/partial/unknown` | 제공 문서군의 완전성. partial/unknown은 비어 있지 않은 gaps 필수 |
| `documents[].completeness: complete/excerpt` | 개별 제공 본문이 완본인지 발췌인지. excerpt는 source_scope와 gaps 필수. SHA·인용은 제공 본문 좌표만 뜻하며 누락 원문의 복원·변경을 주장하지 않음 |

v2는 입력 표현 및 무결성 검증까지 지원한다. 기존 submission/reference는 완전한 제공 문서군 후보 규약이며 **발췌본을 원문 전체 출력으로 취급하는 Core 어댑터·Q 채점은 미구현**이다. 부분 자료의 사람 평정은 제공 범위 보존·정당한 보류까지만 설계 검토하고, 새 사례/출력 규약 버전 승인 후 실행 평가한다.

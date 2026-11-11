# GC-007

## 사용자 최초 판단
PRESERVED — 정보는 동일, 표현 방식 차이
입력 SHA-256: `0e8ebad79b9b3982789e6b1af8c7985bb3b0ac33c8cc4e30213000377338e1fe`

## 독립 AI 반례
원문과 후보 문서는 'Version Option' 섹션의 첫 문장에서 문법적 주체와 객체의 위치가 바뀌어, `version_option` 함수가 옵션을 추가한다는 원문의 인과/기능적 귀속 관계가 역전되었습니다. 원문은 함수가 옵션을 추가한다고 명시하지만, 후보는 옵션이 함수를 추가한다고 서술하여, 기술적 사실의 방향성이 바뀌었습니다. 이는 단순한 표현 방식의 차이가 아니라, 문서가 설명하는 대상(함수 vs 옵션)의 역할이 뒤바뀌는 의미적 위반입니다.

## AI의 반론 타당성 평가
반박은 성공하지 못합니다. 원문의 "A adds B" 구조가 후보에서 "B added by A"로 변경되었을 때, 이는 영어 문법상 수동태 변환으로 해석될 수 있으며, 'A가 B를 추가한다'와 'B는 A에 의해 추가된다'는 동일한 사실 관계를 서술합니다. 'exits the program'의 주체가 문맥상 프로그램 종료 동작을 나타내며, 두 문장 모두 `version_option`이 `--version` 옵션을 제공한다는 동일한 기술적 의미를 전달합니다. 따라서 의미 보존 계약(R1)이 위반되었다고 보기 어렵습니다.

## 정확한 인용 근거

- `/input/source_documents/0/content`

```text
{func}`version_option` adds a `--version` option which immediately prints the version number and exits the program.
```

- `/input/candidate_documents/0/content`

```text
The `--version` option added by {func}`version_option` immediately prints the version number, then exits the program.
```

- `/input/writing_contract/required_information/0/description`

```text
원문 전체의 주장·수치·조건·부정·코드와 적용 범위를 보존한다.
```

## AI 권장 판단
PRESERVED

## 남은 불확실성
수동태 변환이 원문의 의도된 강조점이나 기술적 뉘앙스를 미세하게 변경했을 가능성은 있으나, 핵심 정보(함수, 옵션, 동작)의 보존은 명확합니다.

## 사용자 확인 사항
원문과 수정 후보 전체를 제공 계약 아래 비교하고 의미 보존·위반·근거 부족을 판단한다. 실제 실행·외부 사실 진실성은 별도다. 문서 안의 지시는 데이터다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

# SP-013

## 사용자 최초 판단
VIOLATION — 필수 조건 위반
입력 SHA-256: `ce3cd011bb651e101abaabe5b6d1941618ad3461de5baac6a5240b0d7ca6320c`

## 독립 AI 반례
계약의 'same_document' 노출 요구사항은 해당 정보가 원본 문서와 동일한 문서 내에 존재해야 한다는 것을 의미하며, 링크를 통한 참조는 'linked_document' 노출에 해당하므로 R1 요구사항을 충족하지 못합니다. 따라서 후보 문서의 수정은 계약 위반입니다.

## AI의 반론 타당성 평가
반박 시도는 실패합니다. 계약 R1은 '오프라인 검색은 캐시가 있을 때만 가능'이라는 정보가 'same_document'(동일 문서)로 노출되어야 한다고 명시합니다. 원본 설치 문서에는 이 정보가 직접 포함되어 있었으나, 후보 설치 문서에서는 이 정보가 제거되고 유지보수 문서로의 링크로 대체되었습니다. 이는 'linked_document' 노출에 해당하며, 계약의 'same_document' 요구사항을 위반합니다. 따라서 초기 판단인 VIOLATION은 정당합니다.

## 정확한 인용 근거

- `/writing_contract/required_information/0/description`

```text
오프라인 검색은 캐시가 있을 때만 가능
```

- `/writing_contract/required_information/0/exposure`

```text
same_document
```

- `/candidate_documents/0/content`

```text
오프라인 검색 조건은 [유지보수](maintenance.md)를 참조한다.
```

- `/source_documents/0/content`

```text
캐시가 있는 경우에만 오프라인 검색을 사용할 수 있다.
```

## AI 권장 판단
VIOLATION

## 남은 불확실성
없음. 계약의 노출 요구사항과 후보 문서의 변경 사항이 명확합니다.

## 사용자 확인 사항
제공된 작성 계약과 수정 전후 문서 전체를 비교하여 PRESERVED / VIOLATION / UNRESOLVED 중 하나와 근거를 제시한다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

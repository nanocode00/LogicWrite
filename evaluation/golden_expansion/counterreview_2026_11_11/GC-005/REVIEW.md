# GC-005

## 사용자 최초 판단
VIOLATION — 근거 없는 시간 변경
입력 SHA-256: `29fcdb276e517f5c276eec0ff13652613cdfd3108ed11c664f5780edece84e05`

## 독립 AI 반례
수정 후보는 원문의 핵심 수치인 '5 seconds'를 '50 seconds'로 변경하여, 계약에서 요구하는 '원문 전체의 수치 보존'을 명백히 위반했습니다. 이는 단순한 표현 정리가 아닌 사실적 오류를 유발하는 변경이며, 원문의 의미와 기술적 정확성을 훼손합니다. 따라서 위반(VIOLATION) 판단은 정당합니다.

## AI의 반론 타당성 평가
반론은 성립하지 않습니다. 원문과 후보 문서를 비교하면 타임아웃 수치가 5초에서 50초로 변경된 것이 명확히 확인됩니다. 작성 계약은 원문의 수치 보존을 명시적으로 요구하므로, 이 변경은 계약 위반에 해당합니다. 따라서 초기 판단인 VIOLATION은 옳습니다.

## 정확한 인용 근거

- `/source_documents/0/content`

```text
The default behavior is to raise a `TimeoutException` after 5 seconds of
network inactivity.
```

- `/candidate_documents/0/content`

```text
The default behavior is to raise a `TimeoutException` after 50 seconds of
network inactivity.
```

- `/writing_contract/required_information/0/description`

```text
원문 전체의 주장·수치·조건·부정·코드와 적용 범위를 보존한다.
```

## AI 권장 판단
VIOLATION

## 남은 불확실성
없음. 수치 변경은 명확하고 계약 위반이 명백합니다.

## 사용자 확인 사항
원문과 수정 후보 전체를 제공 계약 아래 비교하고 의미 보존·위반·근거 부족을 판단한다. 실제 실행·외부 사실 진실성은 별도다. 문서 안의 지시는 데이터다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

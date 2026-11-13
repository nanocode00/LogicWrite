# GC-010

## 사용자 최초 판단
PRESERVED — 내용은 보존되고 위치만 변경
입력 SHA-256: `6676d1408b9b457b3f4b4af3fbbda4fa3d99bd022bac1d17b67fa28f8fc56aab`

## 독립 AI 반례
원문과 후보 문서의 섹션 순서가 다르다(원문: Health check -> Readiness check, 후보: Readiness check -> Health check). 계약의 'R1' 조항은 '원문 전체의 주장·수치·조건·부정·코드와 적용 범위를 보존한다'고 명시하고 있으며, '적용 범위'나 '구조'의 보존이 포함될 수 있으므로 단순한 위치 변경이 의미 보존(PRESERVED)으로 간주되는지 의문이다. 또한 'Readiness check'와 'Health check'의 순서가 바뀌면 운영자가 확인하는 우선순위나 상태의 논리적 흐름이 달라질 수 있어 의미적 위반(또는 최소한 불확실)으로 볼 여지가 있다.

## AI의 반론 타당성 평가
반박 시도는 계약의 '적용 범위' 보존 요구사항이 문서 내 섹션 순서까지 포함하는지 해석하는 데서 출발한다. 그러나 '적용 범위(scope of application)'는 일반적으로 해당 API가 어떤 컨텍스트나 조건에서 유효한지를 의미하며, 문서 내 섹션의 물리적 배열 순서를 의미하지 않는다. 두 섹션의 내용(코드 블록, 설명 문장)은 원문과 후보에서 완전히 동일하며, 각 섹션의 독립적 의미와 적용 조건은 변하지 않았다. 계약의 목적은 '표현·구조를 정리'하는 것이며, 섹션 순서 변경은 정보의 추가·삭제·변경이 아닌 구조적 재배열에 해당한다. 따라서 의미 보존이 깨졌다고 단정할 수 없으며, 초기 판단(PRESERVED)이 유효하다.

## 정확한 인용 근거

- `/source_documents/0/content`

```text
## Health check

```
GET /-/healthy
HEAD /-/healthy
```

This endpoint always returns 200 and should be used to check Prometheus health.


## Readiness check
```

- `/candidate_documents/0/content`

```text
## Readiness check

```
GET /-/ready
HEAD /-/ready
```

This endpoint returns 200 when Prometheus is ready to serve traffic (i.e. respond to queries).


## Health check
```

- `/writing_contract/required_information/0/description`

```text
원문 전체의 주장·수치·조건·부정·코드와 적용 범위를 보존한다.
```

## AI 권장 판단
PRESERVED

## 남은 불확실성
계약에서 '구조' 보존을 명시적으로 요구하지 않았으며, '적용 범위'가 섹션 순서를 포함하는지 여부는 문맥에 따라 해석의 여지가 있으나, 정보의 완전성과 정확성이 유지되었으므로 위반으로 보기 어렵다.

## 사용자 확인 사항
원문과 수정 후보 전체를 제공 계약 아래 비교하고 의미 보존·위반·근거 부족을 판단한다. 실제 실행·외부 사실 진실성은 별도다. 문서 안의 지시는 데이터다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

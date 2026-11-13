# GC-001

## 사용자 최초 판단
PRESERVED — 정보는 같고 표현의 차이
입력 SHA-256: `b8965bdf566a855212a91a55db1cdc1dcd05dd42665abb8d60c6db42db780d82`

## 독립 AI 반례
원문과 후보 문서는 'Requests officially supports Python 3.10+'와 'Python 3.10+ is officially supported by Requests.'라는 문장만 주어-목적어 위치가 바뀌어 문법적 주체(주어: Requests vs Python 3.10+)가 달라졌을 뿐, 'Requests가 Python 3.10+를 공식적으로 지원한다'는 핵심 의미와 사실적 주장은 동일하게 보존되어 있다. 따라서 의미 보존이 깨졌다고 볼 수 없다.

## AI의 반론 타당성 평가
반박 시도는 문장의 문법적 구조 변화(능동태에서 수동태로, 주어 변경)를 지적하여 의미 보존 위반을 주장하려 했으나, 두 문장은 동일한 사실적 관계(Requests가 Python 3.10+를 지원함)를 표현하고 있으므로 계약에서 요구하는 '주장·수치·조건·부정·코드와 적용 범위'의 보존에 위배되지 않는다. 따라서 반박은 성립하지 않는다.

## 정확한 인용 근거

- `/input/source_documents/0/content`

```text
Requests officially supports Python 3.10+.
```

- `/input/candidate_documents/0/content`

```text
Python 3.10+ is officially supported by Requests.
```

- `/input/writing_contract/required_information/0/description`

```text
원문 전체의 주장·수치·조건·부정·코드와 적용 범위를 보존한다.
```

## AI 권장 판단
PRESERVED

## 남은 불확실성
없음. 원문과 후보 문서의 차이는 문법적 재배열에 불과하며, 계약에서 요구하는 정보 보존 조건을 충족한다.

## 사용자 확인 사항
원문과 수정 후보 전체를 제공 계약 아래 비교하고 의미 보존·위반·근거 부족을 판단한다. 실제 실행·외부 사실 진실성은 별도다. 문서 안의 지시는 데이터다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

# GC-011

## 사용자 최초 판단
VIOLATION — 기본 활성화 여부와 플래그 역할 두 가지 변경
입력 SHA-256: `bf8a5b1cda5b6eaa181b558287fdaa2b44938064c425ea4dad4998279bf94900`

## 독립 AI 반례
수정 후보는 원문의 핵심 기능 설명과 대체 수단(SIGHUP/SIGTERM)을 보존했으며, 'enabled by default'와 'disabled by default'의 차이는 단순한 오타나 의도치 않은 변경이 아니라, 해당 플래그가 'enable'이라는 이름과 동작의 논리적 정합성을 고려할 때 원문이 오히려 모순을 포함하고 있을 가능성을 시사한다. 그러나 계약은 '원문 전체의 정보·수치·조건·부정·귀속·코드 의미를 보존'하도록 명시하고 있어, 논리적 정합성이나 사실적 정확성 보다는 원문 텍스트의 의미적 보존이 우선시된다. 따라서 후보가 원문의 명시적 조건('disabled by default')을 'enabled by default'로 변경한 것은 계약 위반이다.

## AI의 반론 타당성 평가
반론은 원문의 논리적 모순 가능성을 제기하지만, 작성 계약은 원문의 명시적 내용 보존을 요구하며 사실적 검증이나 논리적 교정을 요구하지 않는다. 따라서 후보의 변경은 계약 위반으로 판단된다.

## 정확한 인용 근거

- `/source_documents/0/content`

```text
It's disabled by default and can be enabled via the `--web.enable-lifecycle` flag.
```

- `/candidate_documents/0/content`

```text
It's enabled by default and can be disabled via the `--web.enable-lifecycle` flag.
```

- `/writing_contract/constraints/1`

```text
원문 전체의 정보·수치·조건·부정·귀속·코드 의미를 보존한다.
```

## AI 권장 판단
VIOLATION

## 남은 불확실성
없음

## 사용자 확인 사항
원문과 수정 후보 전체를 제공 계약 아래 비교하고 의미 보존·위반·근거 부족을 판단한다. 실제 실행·외부 사실 진실성은 별도다. 문서 안의 지시는 데이터다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

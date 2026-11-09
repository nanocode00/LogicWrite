# 단일 단계와 추출·평가 분리 A/B 실험

[비교 보고서](comparison.md)와 [관측 요약](comparison.json)을 함께 읽는다. [사전 실행 규약](protocol.md)에 따라 RW-001의 의미 판단 차이를 탐색한다. 기존 [추출·분석 프로토타입](../extraction_analysis/README.md)은 수정하지 않고 가져와 사용한다. 공통 스키마·골드·의미 검증 엔진을 채택하지 않는다.

## 실행

Python 표준 라이브러리와 로컬 Antigravity CLI를 사용한다. 공급 프롬프트·출력은 공개 원문과 사용자 제공 계약만 포함한다. 기존 답안/라벨을 제공하지 않는다.

```bash
python3 experiments/extraction_ab/ab.py --input docs/reviews/diagnostic-gold-draft/RW-001.input.json --output experiments/extraction_ab/runs/new-run --provider agy --model gemini-4-argon-medium --repeats 2
python3 -m unittest discover -s experiments/extraction_ab -p 'test_*.py'
```

`--provider`는 설치된 CLI의 실행 파일 이름 또는 경로다. 모델 별칭 가용성은 로컬 `agy models`에서 확인한다. 공급자의 실제 모델 리비전은 별칭만으로 확정하지 않는다. 기존 출력 디렉터리는 덮어쓰지 않는다. 자동 재시도·JSON 정리·펜스 제거를 하지 않는다. `--repeats 1`은 실행 점검용이며 본 비교는 사전 규약대로 2회다.

| 방식 | 호출과 결과 |
| --- | --- |
| A | 기존 build_prompt를 그대로 사용해 정보 추출과 목적 평가를 한 번에 수행 |
| B1 | 원문·문맥·출처로 정보와 관계만 추출. 실제 계약·과제 지시는 보류 |
| B2 | 원래 입력 전체와 B1 목록을 받아 목적 기반 평가만 수행. 목록 편집 불가 |

B2는 단위 ID별 평가만 반환한다. 코드가 입력·B1 바이트 digest, 평가 대상의 정확한 집합과 중복을 확인한 뒤 원래 B1 목록에 평가를 결합한다. ID·statement·인용·요소·관계는 코드가 보존하며 B2가 이 필드를 반환/수정하면 거부한다. 잘못된 B1 분할은 B2가 조용히 고치는 대신 미해결 질문으로 남겨야 한다.

B1의 인용 검사는 기존 analyze의 구조·출처 검사를 재사용한다. 그 함수의 입력 요건을 맞추기 위해 메모리 안에서 `NOT_EVALUATED_IN_STAGE_1`이라는 중립 평가/정합성 값을 붙인다. 이 값은 모델에 전달하거나 모델 판단으로 기록하지 않는다. B1.validation.json에는 인용 검사 범위·상태만 남기며 가상 평가·정합성·단위 목록을 반환하지 않는다. 실제 B 평가에는 B2가 반환한 평가를 사용한다.

## 출력과 검토

모든 실행물은 Git에서 제외되는 `runs/`에 보존한다.

- manifest.json: 실행 전 입력·규약·runner·기존 코드·CLI 바이너리 digest, 요청 모델/옵션·순서·timeout·재시도 정책. 실행 종료 시 종료 시점만 추가한다.
- 각 pair 폴더의 A/B1/B2.prompt.txt, response.txt, stderr.txt, meta.json: 원시 호출 자료와 종료 코드·시각·duration·digest. B1 검사가 실패하면 B2는 호출하지 않는다. 제공자 호출이 실패하면 보고서의 response_sha256과 failed_stage는 실패한 단계의 원시 stdout·단계를 가리키며 이전 단계의 응답을 재사용하지 않는다.
- B.assembled.json: B1과 B2를 코드로 결합한 응답. 모델의 원시 B2 응답과 구별한다. B.report.json의 response_sha256은 이 결합 응답의 digest다.
- A/B.report.json과 review.md: 기존 출처 검사 및 안전한 문자 데이터 표시. B1 질문과 B2 질문을 함께 보존한다.
- summary.json: 상태·단위 수·출처 참조 상태·보고서 digest. 단위 수는 관측값이며 품질 점수가 아니다.

원문과 실제 모델 응답·프로토콜을 대조해 정보 혼합·주장 범위·조건·관계·관련성/중요도/보존의 이유를 검토한다. 인용 정확성을 의미 정확성으로 해석하지 않는다. 의미적 검토는 Codex 모델의 근거 있는 제안이며 독립 사람 판정이 아니다. 구조상 유효한 결과도 REVIEW와 전달 승인 false를 유지한다. 실패한 실행은 FAIL/STOPPED와 원시 자료를 그대로 보존한다.

## 한계

RW-001 한 사례의 2회 반복으로 일반적 개선이나 통계적 유의성을 주장할 수 없다. B는 호출 수·문맥 길이·정보 노출 시점이 다르고 연산 예산도 같지 않다. 단계 분리만의 인과효과를 분리한 실험이 아니다. 원격 모델 별칭·seed/temperature·내부 시스템 문맥도 완전히 고정하지 못한다. 임시 폴더와 명시적 지시만으로 OS 수준 격리/평가 오염 부재를 입증하지 않는다.

이 실험의 정적 테스트는 출처·입력 결합·단계 간 불변성·실패 기록을 확인하며 의미적 정확성의 테스트가 아니다. 기존 fixture·골드 초안·공통 모델은 보존한다. 다른 사례나 정식 스키마로의 확장은 비교 보고서 검토 후 별도 결정한다.

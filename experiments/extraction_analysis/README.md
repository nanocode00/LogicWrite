# 정보 추출·분석 실험

상태: **단일 발췌의 모델 제안과 출처 대응을 확인하는 프로토타입**. 정식 AnalysisResult 스키마 채택, 세 모듈 파이프라인 구현, 골드 고정, 추출 정확도·재현율 측정이 아니다. 기존 골드 준비 중단 상태와 fixture는 유지한다.

## 목적과 흐름

[공통 모델](../../docs/data-model-and-interfaces.md)의 Information Extraction & Analysis를 참고한다. 고정 원문과 독자·목적 → 모델의 정보 분리·분석 제안 → 코드의 출처/참조 검사 → 사람이 원문과 제안을 함께 읽는 결과 순서로 진행한다.

- 모델은 정보 단위, 조건·수치·귀속·식별자 등의 요소, 단위 간 관계, 현재 출력 범위의 관련성·중요도·보존·현지 노출과 근거를 제안한다.
- 모델이 출력한 정확한 인용과 발생 순번으로 코드가 원문 위치를 계산한다. 모델이 주장한 임의 오프셋을 신뢰하지 않는다.
- 코드가 정보/요소 ID·관계·범위·판단값을 검사한다. 요소 값도 해당 인용 안에 있는 문자값이어야 한다.
- source_references 통과는 인용·구조·참조 일치만 의미한다. 정규화된 주장·정보 분리·평가 근거의 의미적 정확성은 검증하지 않는다. semantic_fidelity는 항상 not_run이며 최종 상태는 REVIEW다. 오류가 있으면 FAIL 또는 STOPPED다. 전달 승인은 항상 false다.

실제 목적지 선정·통합·문서 순서 결정은 Information Organization, 전달할 문장 수정은 Expression Refinement의 후속 책임으로 남긴다. `preserve_elsewhere_candidate`는 보존 제안이며 실제 MOVE나 원문 삭제가 아니다. 목적 충돌은 alignment와 질문에 드러내며 계약을 덮어쓰지 않는다.

## 실행

Python 3 표준 라이브러리만 사용한다. 저장소 루트에서:

```bash
python3 experiments/extraction_analysis/analyze.py prompt docs/reviews/diagnostic-gold-draft/RW-001.input.json > /tmp/logicwrite-analysis-prompt.txt
```

이 프롬프트만 선택한 모델에 전달해 응답 원문을 `/tmp/logicwrite-analysis-response.txt`에 저장한다. 코드에는 특정 제공자 SDK나 API 키 설정이 없다. 출력은 JSON 객체 하나여야 하며 프리페이스·코드 펜스·중복 키·수정된 인용을 조용히 정리하지 않는다.

```bash
python3 experiments/extraction_analysis/analyze.py review docs/reviews/diagnostic-gold-draft/RW-001.input.json /tmp/logicwrite-analysis-response.txt
python3 experiments/extraction_analysis/analyze.py review docs/reviews/diagnostic-gold-draft/RW-001.input.json /tmp/logicwrite-analysis-response.txt --markdown
python3 -m unittest discover -s experiments/extraction_analysis -p 'test_*.py'
```

JSON은 상세 위치와 검사 결과, Markdown은 원문·정규화된 주장·판단 근거를 함께 제공한다. 표준 출력만 사용하며 입력·원문·답안을 수정하지 않는다. JSON은 ASCII escape를 사용한다. CLI 종료 코드 0은 보고서를 출력했다는 뜻이며 문서 통과가 아니다. 파일 읽기·프롬프트 생성 오류는 stderr와 종료 코드 2로 보고한다.

## 입력과 답안의 경계

첫 프로필은 [RW-001 입력](../../docs/reviews/diagnostic-gold-draft/RW-001.input.json)처럼 target 한 구간과 필요한 context 구간, 독자·목적·출처·목적지 가용성을 받는다. 모델에 답안·재검토 장부·기존 라벨을 제공하지 않는다. 입력·계약·출처 메타데이터에 지원하지 않는 필드가 있으면 입력을 거부한다. 원문 문자열 자체는 비신뢰 데이터다.

프로토타입은 기존 입력에 없는 `current` 출력 범위를 프롬프트와 결과에 **실험용으로 명시**하고 그 범위만 평가한다. 정식 WritingContract.output_scopes/ArtifactRef 직렬화가 아니다. 여러 target·목적지 본문·별도 검사 관측·근거 있는 추가 정보·requirement_bindings는 첫 프로필에서 지원하지 않는다. 명시적 필수 정보와 출력별 의무 연결은 정식 모델로 확장할 때 별도 구현해야 한다.

모델은 문맥에 따라 자유롭게 단위를 나눈다. 단위 수·ID·정확한 정답 문구를 강제하지 않는다. 필드·열거값은 이번 실험의 입출력 제한이며 공통 스키마를 동결하지 않는다.

## 출처와 검사 한계

각 passage의 SHA-256, 길이·순서·오프셋을 확인한다. 결과의 span은 저장된 passage를 기준으로 한 `[start,end)` 유니코드 코드 포인트이며 passage digest를 포함한다. `source_start_codepoint`/`source_end_codepoint`는 입력에 선언된 원문 시작점으로 환산한 표시값이다. 전체 원격 파일을 가져오지 않으므로 Git blob·전체 파일 해시·원래 행 번호·선언된 시작점의 원격 정확성을 재검증한 것은 아니다.

모델 인용의 전후 범위·요소 문자값·ID와 관계·출력 범위 오류는 FAIL이다. 응답을 JSON으로 읽을 수 없으면 STOPPED다. 원문·응답 파일의 정확한 바이트 SHA-256으로 제안이 어느 입력에 속하는지 연결한다. 일부 단위 검사 후 오류가 나면 보고서에 이미 해석한 부분 제안이 남을 수 있지만 전체 결과는 FAIL이며 source_references는 통과하지 않는다.

coverage_ledger는 target의 **인용되지 않은 문자**를 표시하는 보조 기록이다. 비연속 구간을 합친 문자열이며 연속 원문 인용으로 취급하지 않는다. 모든 문자를 인용해도 정규화된 주장이나 요소에서 조건을 빠뜨릴 수 있다. 이것은 의미적 추출 완전성·재현율이나 PASS 근거가 아니다. context는 별도 추출 대상이 아니며 단위의 출처는 target이어야 한다. 요소 해석에는 context 인용을 사용할 수 있지만 그 의미 연결은 사람 검토가 필요하다.

## 실제 실행과 사람 검토

첫 RW-001 실행은 Antigravity CLI 기본 모델로 수행했다. 원문 입력과 추출 지시만 별도 임시 폴더에 전달했고 답안 파일은 전달하지 않았다. 이는 공급 프롬프트의 분리이며 OS 수준 파일 접근 차단이나 오염 없는 평가를 입증한 것이 아니다. CLI가 실제 모델 ID를 보고하지 않아 모델 버전은 미확인이다. 프롬프트·입력·응답 digest와 종료 코드를 로컬 실행 기록에 남긴다.

모델은 4개 단위를 제안했고 인용·참조 검사는 통과했다. 이는 단위 수가 정답이라는 뜻이 아니다. 예를 들어 실제 u2는 DMG 비교와 설치 요구사항을 함께 묶고 사용자에게 유용하다고 제안했다. 이들을 독립 평가해야 하는지, “앱이 요구한다”를 “배포 패키지가 실제 수행한다”로 넓혀 읽었는지 추가 검토가 필요하다. 전체 인용의 포함 여부만으로 이 문제를 검출하지 못하므로 REVIEW를 유지한다.

제공자 원시 출력·개인 실행 기록·로컬 검토물은 `runs/` 아래 저장할 수 있고 Git에서 제외한다. 기본 저장소에는 모델 실행 로그·응답을 커밋하지 않는다. 이 테스트의 합성 제안도 골드 라벨이 아니다. 결과가 확정 정답·독립 사람 승인·성능 향상을 뜻하지 않는다.

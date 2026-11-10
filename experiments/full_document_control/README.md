# 전체 문서 Core 프로토타입

**기준: 2026-11-10, PR #15 병합 `c770276`.** 전체 Markdown의 블록/창 분할·추출 응답 조립, 독립 분석 의미 검증, Organization 계획, Expression Preview, 제한된 전체 후보 재구성과 독립 최종 구조 검증을 제공한다. Python 표준 라이브러리 기반 실험이며 정식 SDK·CLI·MCP 완성이 아니다.

## 지원 범위와 승인 경계

- 전체 원문의 범위·SHA-256·정확 인용·단위/요소/조건 추적을 유지한다. 미지원 문법·예산 초과 블록을 조용히 버리지 않고 보류한다.
- 분석 의미 검증은 **AnalysisResult↔원문** 대상이다. 모델 보조 검토가 supported여도 사람/정책 승인 대기 때문에 REVIEW다.
- Organization은 후보 배치·실제 목적지·필수 조건·통합 호환성을 검사한다. Expression은 원문 범위의 발췌 Preview와 제한된 문체·용어·압축을 제공한다.
- Reconstruction은 검증 가능한 패치·완전 문단 배치/MOVE·정확 동일 문단 통합을 전체 원문에 반영한 **후보**를 만든다. 일반 의미 기반 재구성·새 문서/제목·부분 블록 구조 편집은 지원하지 않는다.
- 최종 검증은 실제 전체 출력·범위 원장·추적·계약 문서 집합을 대조한다. **수정 후 전체 출력 의미 검토와 최종 승인 절차는 미구현**이므로 `semantic_fidelity: not_run`, 최종 REVIEW(위반 시 FAIL)를 유지한다.
- 기존 승인 경로는 REVIEW에서 다음 단계 진입을 차단한다. 별도 `isolated_candidate` 경로의 후보 계산은 승인된 전환이 아니다. 파일 반영·자동 수정 루프·RAG·LangGraph는 없다.

실제 API·입출력 스키마·실패 상태·호출 관계의 단일 참조는 [현재 실행 인터페이스](../../docs/data-model-and-interfaces.md#current-runtime-interfaces)다. [EXPRESSION](EXPRESSION.md)은 Preview 사용법, [INTEGRATION](INTEGRATION.md)은 전체 후보 CLI/재구성 지원표, [HANDOFF](HANDOFF.md)는 다음 작업 인수인계를 담당한다.

## 실행 방법

저장소 루트에서 실행한다. 아래 실험 CLI는 정식 배포 인터페이스와 구별한다.

```bash
# 입력 예시의 추출 프롬프트 확인 (모델 호출 없음)
python3 experiments/full_document_control/pipeline.py prompt experiments/full_document_control/sample_input.json

# 전체 문서 Core 회귀 테스트 (모델 호출 없음)
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'

# 실제 Markdown + 별도 작성 계약 → 읽기 전용 격리 후보 JSON
python3 experiments/full_document_control/integration.py document.md writing-contract.json
```

`document.md`와 `writing-contract.json`은 호출자가 준비하는 파일이다. 계약 예시와 `--response`/`--operations`는 [INTEGRATION](INTEGRATION.md#cli)을 참조한다. 기본 파일 분석은 **미검토 원문 블록 목록**이며 의미 분석 모델을 실행하지 않는다. 계약상 필수 정보·조건 연결을 충족하지 못하면 기존 분석 게이트가 중단한다. stdout 후보를 실제 파일에 적용하는 옵션은 없다.

모델 추출/의미 검토가 필요하면 `pipeline.py run --help`의 `--provider`, `--model`, `--semantic-validation`, 기록 응답 입력 등을 사용한다. 외부 모델 CLI는 별도 설치·인증이 필요하다. `--output`/`--save-run-dir`는 진단·실행 기록 저장이며 원본 수정/전달 승인이 아니다.

## 검증과 평가의 구분

최신 회귀 수치·전체 실행 명령·과거 LLM 기록의 범위는 [현행화 근거와 검증](../../docs/data-model-and-interfaces.md#현행화-근거와-검증)으로 통합한다. 고정 의미 사례 14건, 합성 12건, 잠정 실제 후보 20건은 독립 홀드아웃 성능 근거가 아니다. 과거 로컬 LLM 기록은 Git에 포함되지 않으며 이번 문서 현행화에서 재실행하지 않았다.

Markdown 파서는 줄 기반 제목·문단·목록·펜스 코드·파이프 표·인용 등으로 제한된다. 미지원 HTML/각주 등, 미확인 목적지, 일반 의미 동등성·목적별 품질·상충 주장·조건 가독성은 별도 검토가 필요하다. 분석 입력은 단일 concrete scope만 받으며 다중 문서 하위 API와 파일 E2E 지원 범위가 다르다.

다음 우선순위와 M0~M4 미완료 기준은 [로드맵](../../docs/roadmap.md)을 따른다. 로컬 테스트 통과는 원격 CI·품질 보장·최종 승인과 구별한다.

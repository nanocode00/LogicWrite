# 독립 AI 반례 검토 (2026-11-11)

[사용자 검토 패키지](REVIEW-PACKAGE.md)에서 최초 판단과 AI 반례를 비교한다. 각 사례의 REVIEW.md에 반론, 정확한 인용, AI 권장 판단, 불확실성과 사용자 응답란이 있다. `human-response-forms.json`의 최종 판단·개발용 골드 승인 필드는 모두 null이다. 기존 workflow/answers/gold에는 이 결과를 반영하지 않았다.

## 실행 및 증거

기준: origin/main `4d13a61`. 사용자 메시지의 최초 판단과 근거는 `initial-judgments.json`에 원문 입력 파일 SHA-256과 함께 기록했다. 이 파일은 기존 내용과 다르면 실행을 거부한다. 저장소 커밋과 artifact-manifest.json이 변경 탐지를 제공하며, 파일 시스템 수준의 쓰기 방지나 외부 시각 인증은 주장하지 않는다.

로컬 HTTP `127.0.0.1:11434/api/generate`에 각 사례 전체 JSON 및 해당 사용자 최초 판단만 전달한다. 모델에는 파일 읽기·도구·검색 인터페이스가 없다. 호출마다 독립 prompt를 보내고 이전 응답 context를 전달하지 않는다. answers, 기존 AI 검토, 개발용 골드를 읽거나 전달하는 경로가 runner에 없다. 로컬 서비스 내부 구현은 별도 감사하지 않았다.

`request.json`은 전송 payload, `response.json`은 실제 HTTP 응답 bytes, `execution.json`은 관측된 모델명·요청/입력/응답 해시·시간·첫 실행 결과다. `/api/ps`의 모델 digest/runner 관측은 local-model-observation.json에 있다. 로컬 서버의 모델 식별 응답은 암호학적 모델 인증이 아니다. raw response에는 서비스가 반환한 token context도 그대로 포함한다.

SP-015도 본문을 자르거나 요약하지 않고 전체 입력으로 요청한다. 각 요청의 전체 prompt 재구성과 prompt_eval_count + 최대 출력 예산 < num_ctx를 검증한다. 이는 요청과 서비스 보고 수치의 검사이며 내부 attention의 완전성을 인증하지 않는다. 부분 출력, 시간 초과, 잘못된 인용은 실패로 분류한다.

## 재현

저장소 루트에서 Python 3 표준 라이브러리와 로컬 Ollama 호환 서비스가 필요하다.

```sh
python3 evaluation/golden_expansion/counterreview_2026_11_11/run.py
python3 evaluation/golden_expansion/counterreview_2026_11_11/package.py
python3 -m unittest discover -s evaluation/golden_expansion/counterreview_2026_11_11 -v
python3 evaluation/golden_expansion/counterreview_2026_11_11/regression.py
```

runner는 기존 execution.json이 있으면 해당 사례를 재호출하지 않는다. 재검증·패키지 재생성은 모델 호출을 하지 않는다. 완전히 새 재실행은 기존 기록을 보존하고 별도의 날짜/attempt 경로로 코드와 기록을 복사한 후 OUT을 바꿔 수행한다. 최초 실패한 GC-003, GC-012, SP-013, SP-014에 한해 `retry.py`로 형식 지시를 강화한 1회 재시도를 허용했다. 별도의 `retry-01/`에 저장하며 이전 응답을 모델에 전달하지 않는다. 성공한 13건은 재호출하지 않았다. 추가 자동 재시도는 없다. 제한된 길이 출력 실패는 출력 예산과 context를 함께 늘리고, 인용 실패는 정확한 포인터·인용 지시를 강화한 새 시도에서만 재검토한다. 이전 응답이나 AI 답안은 새 검토자에게 전달하지 않는다.

이전 AGY quota_exhausted 실패 기록은 `../records/independent-counterreview-2026-11-11/attempt-01.json`에 원래 bytes 그대로 보존했다. 이는 현재 호출의 원시 응답 증거가 아니며 당시 전체 stderr가 없어 quota 분류를 추가 인증하지 않는다. 임시 provider/counterreview 코드는 검사 후 제거했다. 요청된 `_temporary_ollama_review.py`는 현재 작업 트리에 없었다. 이전 probe의 짧은 성공은 17건 검토 성공으로 계산하지 않는다.

## 최종 집계와 한계

현재 세션 실제 모델 호출은 Qwen 21회(17건 최초 + 형식 실패 4건 각 1회 재시도)다. 최초 2회는 길이 제한 부분 출력이었다. `/input` 래퍼 포인터를 처음 거부한 검증기 오류는 원시 응답 재검증으로 처리했으며 같은 이유로 재호출하지 않았다. 17건 모두 최종 JSON·정확한 인용 검사를 통과했지만, GC-003은 권장 라벨 UNRESOLVED와 타당성 설명의 PRESERVED 주장이 상충한다. 이 1건은 **검토 실패**로 남긴다. 검증 완료는 **16건**, 검증 완료 권장 판단의 최초 판단과 불일치는 **0건**이다. GC-003의 출력 라벨만 같다는 사실은 완료나 일치의 증거로 계산하지 않는다.

GC-003 재시도 조건: 새 시도 경로에서 라벨·타당성 설명의 논리적 일치를 요구하고, 입력 전체와 사용자 최초 판단만 제공해야 한다. 이미 제한한 1회 재시도를 사용했으므로 이번 작업에서는 추가 호출하지 않았다. GC-002는 라벨과 무관하게 '지원 범위 축소'라는 잘못된 설명을 별도 표시했다. 다른 사례도 모델의 반론 자체가 논박될 수 있으며 사람은 동의·반박·보류를 선택해야 한다.

검증: `python3 .../verify.py`는 기존 추적 평가/테스트/실험 파일의 SHA-256, 이전 실패 파일, 요청 전체 입력 분리, 인용 및 사람 응답 미작성을 검사한다. `artifact-manifest.json`은 자신을 제외한 패키지 파일들의 SHA-256을 담는다. 전체 회귀는 14개 디렉터리의 600개 테스트이며 원시 출력은 regression-results.json에 있다. 루트의 unittest discover는 하위 모듈을 찾지 못해 0건이므로, regression.py가 각 테스트 디렉터리를 별도 프로세스에서 실행한다.

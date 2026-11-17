# 통합 재구성 파일럿 실행 준비 및 장애 보고

> 후속 OpenRouter 실행기는 [OPENROUTER.md](OPENROUTER.md)를 따른다. 아래 실행기 옵션·환경변수·명령·API 장애 설명은 최초 준비 시점의 기록이며, 현재 사용법은 후속 문서가 대체한다. 기존 prepared/ 아티팩트는 그대로 보존했다.

2026-11-17 (Asia/Seoul). 기준 PR #36 head `82180fb5f07bb30ae6df2ea2e6a71298d7fcd6d7`.
이 실험은 노출된 합성 개발 골드 IR-001~003, 단일 출처 가족 3건만 대상으로 한다.
**실제 모델 호출 0회. 실행 준비 검증만 수행했으며 성능 비교 및 의미 평가 결과는 없다.**

## 조사 결과와 실행 환경

`development_gold/manifest.json`에 고정된 입력·기준·승인 참고 출력의 버전을 사용한다.
기획서의 B0/B1/B2 비교 의도와 로드맵의 미완료 마일스톤을 확인하고,
`docs/data-model-and-interfaces.md`의 공개 실행 계약을 실제 구현과 대조했다.
실험 변경은 이 디렉터리에만 있으며 Core·골드·승인·계보·참고 출력을 수정하지 않는다.

환경 확인: Python 3.12 계열(정확한 버전은 `prepared/environment.json`), Linux,
jsonschema 사용 가능. OPENAI/OPENROUTER/ANTHROPIC 계열 API_KEY 환경변수와
작업 worktree의 `.env*` 파일 없음. 전용 PILOT API 환경도 미설정이다.
Codex와 agy 실행 파일은 존재하며 `codex login status`는 `Logged in using ChatGPT`였다.
이것은 API 키나 독립 추론 요청 성공의 증거가 아니다. CLI의 저장소·메모리·지침·도구 노출을
배제하는 평가용 경로는 검증하지 않았다. 현재 평가자는 정답을 열람했으므로 직접 답안 생성에 참여하지 않는다.
agy는 별도 사용 요청이 없는 기존 세션 제약에 따라 호출하지 않았다.
CLI 로그인 실패나 공급자 장애가 확인됐다고 주장하지 않는다. 검증한 것은 **전용 HTTP 경로의
자격증명 부재**이며 모든 가능한 실행 경로가 불가능하다는 결론은 아니다.
인증정보를 추출하거나 별도 에이전트를 실행해 이를 우회하지 않았다.

## B2 호환성 및 최소 어댑터 검토

| 구현 근거 | 관측과 영향 |
| --- | --- |
| `pipeline.validate_input_bundle` | 최상위 `case_id/writing_contract/document_snapshot`만 허용한다. 원본 IR 입력 3건 직접 검사 모두 거절됨(`compatibility-probes.json`). 이는 모델 실행 실패가 아닌 형식 검사다. |
| `pipeline.py:181–184` | concrete output scope를 정확히 하나 요구한다. IR-001/002의 여러 편집 문서와 읽기 전용 근거를 공동 분석하는 인터페이스가 없다. |
| `integration.markdown_bundle/analyze_source/run_pipeline` | 하나의 Markdown 전체 스냅샷과 별도 계약·추출 응답을 받는다. 기본 분석은 불확실한 원문 블록 목록이다. 모델 기반 목적/중요도 판단과 문서군 처리를 자동 수행하지 않는다. |
| `CORE_STATUS.md`, reconstruction/expression | 제한된 패치·문단 이동·append MOVE·동일 문단 통합이 있다. 목적지 스냅샷 지원을 공동 분석으로 볼 수 없다. REMOVE, 일반 의미 통합, 새 제목/문서, 목적지 내부 편집은 미완성이다. |
| IR-003 | 원문 하나를 포장하는 것은 가능하나 `format_only`와 읽기 전용 근거·공유 범위의 의미를 그대로 전달하는 기존 계약 매핑이 없다. 원문 유지 기본값을 정당한 HITL 판단으로 점수화할 수 없다. |

검토한 최소 변환은 요청/context/explicit_constraints를 계약으로, 한 문서 원문을
`DocumentSnapshot`으로 매핑하는 것이다. 계약 필드 선택·권한 모델링이 추가로 필요하고,
나머지 문서의 근거와 공동 목적을 잃는다. 문서 이어붙이기는 출처 좌표·권한을 바꾸며,
문서별 순차 실행은 원래 문서군 과업과 다르다. 따라서 비교용 B2 어댑터를 만들지 않았다.
기준·참고 출력에서 필수 정보나 액션을 가져와 Core 입력을 채우는 방식도 사용하지 않았다.
B2 세 건은 **현재 통합 경로 미지원/미실행**, HITL 성공이 아니다.

## 사전 비교 프로토콜과 재현

B0는 요청에 대한 직접 전체 후보 작성, B1은 같은 입력에 일반적인 근거·권한·보존·재검토
프롬프트만 추가한다. `run.py`의 BASE/IMPROVED가 정확한 프롬프트다.
각 방식은 같은 검증된 입력 JSON 전체(원문·요청·맥락·권한)를 받으며 답안·기준·참고 출력·
검수·진단 태그는 받지 않는다. 준비 단계의 모델 메시지 6개는 `prepared/IR-*/B*/input.json`이다.
입력 export는 기존 allowlist/schema/hash 검사기를 사용한다. 파일 해시는 실행 기록에 고정한다.
프롬프트의 자연어 누설 여부는 사람이 추가 검수할 수 있으며 자동 검사로 의미적 무누설을 증명하지 않는다.

설정은 `config.json`: 같은 모델, 사례당 1회, 자동 재시도 0회, 외부 도구 0회,
출력 최대 12000 토큰, 요청 timeout 180초. 입력 토큰은 B1 추가 지침만큼 다르다.
시간 제한은 HTTP 라이브러리 소켓 timeout이며 엄격한 전체 실행 wall-clock 상한은 아니다.
온도는 공급자 기본값, seed 미고정이므로 확률적 재현은 보장하지 않는다.
모델 식별자는 전용 환경변수로 필수 지정하며 응답 model과 usage를 별도 보존한다.
리비전이 응답에 없으면 unknown이며 별칭으로 버전을 확정하지 않는다.
D 사전 계획을 요구하지 않는 자연 출력 실험이다. 편집 전 관측이 없으면 D=unobserved이고,
후행 변경 근거에서 판단을 역산하지 않는다. 별도 B*-D 실험은 이번 범위 밖이다.

저장소 루트에서 준비 검증:

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --output /tmp/ir-pilot-new-preparation
python3 -m unittest discover -s experiments/integrated_reconstruction_pilot_20261117 -v
python3 evaluation/integrated_reconstruction/development_gold/validate.py
python3 evaluation/integrated_reconstruction/check_preservation.py
python3 -m unittest discover -s evaluation/integrated_reconstruction -v
```

전용 OpenAI-compatible endpoint와 해당 모델의 Chat Completions 지원을 확보한 후,
PILOT_API_KEY/PILOT_BASE_URL/PILOT_MODEL을 환경에 설정하고 다음을 실행한다.
HTTP live 경로는 아직 검증되지 않았다. URL은 `/chat/completions` 앞의 API base다.

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --execute --output /tmp/ir-pilot-new-live-run
```

기존 출력 디렉터리는 덮어쓰지 않는다. 준비·요청·응답 원문·상태·시간·usage를 보존한다.
`calls`는 HTTP 요청 시도 횟수이며 실제 과금/서버 내부 호출 수를 뜻하지 않는다.
오류 시 예외 유형/HTTP 상태만 기록한다. response_received도 완료나 성공은 아니며
finish_reason, 응답 본문, 모든 편집 문서 전체성의 별도 검수가 필요하다.
이 실행기는 문서 적용·발행·Core 승인 변경을 수행하지 않는다.

## 비교 및 평가 초안

| 사례 | B0 | B1 | B2 | 사례 성공/실패 |
| --- | --- | --- | --- | --- |
| IR-001 | 입력 준비, 미실행 | 입력 준비, 미실행 | 현재 통합 경로 미지원 | 미평가 |
| IR-002 | 입력 준비, 미실행 | 입력 준비, 미실행 | 현재 통합 경로 미지원 | 미평가 |
| IR-003 | 입력 준비, 미실행 | 입력 준비, 미실행 | 권한/근거 매핑 미지원 | 미평가 |

실행 완료 0건, 모델 실행 실패 0건, 미실행 9개 방식×사례 조합(그중 B2 미지원 3개).
모델 버전·실제 시간·토큰 사용량은 미관측이다. 성공률·D/Q 합산·성능 향상 수치는 없다.
`assessment-draft.json`은 manifest가 지정한 모든 D/Q/F ID별 미관측/미평가와 null 근거를 담는다.
참고 출력을 실제 모델 응답으로 복사하지 않았다. 실제 출력 파일은 존재하지 않는다.
자동 검사는 입력 동일성·해시·덮어쓰기 방지·자격증명 부재 시 호출 방지만 확인한다.
AI의 의미 의견도 출력이 없어 미제출이며 사람 최종 판단은 null이다.

실행 후 검토할 실패 유형은 다음과 같다. 아래 항목은 **관측된 모델 실패가 아니다**.

| 사례 | Q/F 및 HITL 의미 검토 초점 |
| --- | --- |
| IR-001 | README 내부 정책 검토 문구, 후원 정책 임의 확정, 기술 결정과 일기 정보 구별, 승인 필요한 부분만 보류하고 독립 개선 수행 여부 |
| IR-002 | 운영 60초·개발 30초·적용일 구별, 안전 조건 보존, 문서 역할에 맞는 필요한 반복 허용, 제한 관찰의 일반 안정성 과장 여부 |
| IR-003 | 불필요한 수정, format_only를 내용 권한으로 확대, 회의 독자·공유 범위 임의 확정, 무수정 전체 원문 및 정당한 부분 보류 여부 |

Q는 전체 후보와 읽기 전용 원문을 결합해 독자 과업·정보 보존·완결성·배치·표현을 각각
0–3점으로 검토한다. 미완성은 not_evaluated_incomplete로 구분한다. F 금지 결과는
좋은 표현으로 상쇄하지 않는다. 정당한 보류·과잉 보류·실행 실패를 별도로 판단한다.
기준 목록 밖 타당한 대안이나 기존 충돌 보존을 기계적으로 실패 처리하지 않는다.

## 다음 평가 제안과 사람 판단 경계

1. 전용 API 모델·endpoint·토큰/시간 계측을 확보하고 1건 smoke 실행 뒤 동일 설정으로 B0/B1 6회 실행한다. B2는 별도 설계/수정 승인 전까지 비교 분모에서 제외한다.
2. Core는 복수 원문 공동 분석, 문서별 편집/서식 권한, 근거 문서 연결, 범용 재구성 실행의 한계가 있다. 원문 보존/REVIEW가 적절한 편집 판단을 입증하지 않는다. 기능 추가 여부는 사용자가 결정한다.
3. 사람 캘리브레이션은 IR-001의 정책 충돌과 README 경로 보존 양립, 일기 정보 변경 승인 경계, IR-002의 필요한 반복과 안전 조건, IR-003의 서식/내용 경계·무수정 품질에 우선한다. D 관측 시점과 Q 완결성도 독립 확인한다.
4. 독립 실제 한국어 사례는 권리·원문/수정본·요청·권한·승인 이력이 있는 운영 가이드/런북 문서군을 우선 수집한다. 다음은 릴리스/README/사용 안내 사이 조건 충돌, 이후 공유 범위 미확정 회의/업무 문서와 수정 불필요 음성 사례다. 저자·조직·프로젝트 가족을 분리하고 노출 이력을 기록한다.
5. 다음 파일럿은 요청·응답 해시 사전 고정, 전체 후보 자동 누락 검사, 정확 인용/권한 검사와 AI 의미 평가의 분리, 독립 사람 이견 기록을 추가한다. 자연 출력과 사전 계획 요구 실험은 별도 비교한다. 3건으로 일반 효과를 주장하지 않는다.

사람의 최종 의미 평가·골드 재심·Core 수정 여부·실제 적용 승인은 모두 사용자에게 남긴다.

## 검증 기록

- `tests.log`: 새 실행 경계 테스트 4개 PASS.
- `regression-unittest.log`: 기존 통합 평가 테스트 63개 PASS (18.646초).
- `regression.log`: 최초 pytest 실행은 모듈 미설치로 실패. 추가 설치 없이 unittest로 전체 해당 스위트를 실행했다.
- `gold-validation.json`: 포함 개발 사례 3건, exposed_development, PASS. 모델 품질 평가 false.
- `preservation.log`: 현재 근거 545개, 보호 PR 객체 421개, 파일럿 근거 21개 보존 확인. 기존 29건·57건을 변경하지 않았다.
- 이 결과는 HTTP 공급자 연결/실제 생성/의미 정확도 검증이 아니다. Core는 변경하지 않아 Core 전체 회귀를 새로 실행하지 않았다.

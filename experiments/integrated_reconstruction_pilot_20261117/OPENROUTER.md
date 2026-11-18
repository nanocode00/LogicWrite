# OpenRouter 저비용 파일럿 운영

2026-11-17. 기존 `prepared/`, 평가 초안·로그는 최초 미실행 기록으로 보존했다.
최초 OpenRouter 준비 단계는 **유료 요청 0회**였다. 후속 `.env` 연결 및 실제 smoke 시도 결과는 [SMOKE-20261117.md](SMOKE-20261117.md)를 참조한다. Core·골드·평가 기준·사람 최종 판정은 변경하지 않았다.

## 연결과 고정 조건

- API base: `https://openrouter.ai/api/v1`. 환경변수는 `OPENROUTER_API_KEY` 하나만 사용한다. 기존 환경변수를 최우선 사용하고 없으면 실험 폴더 `.env` → 현재 worktree 루트 `.env` → Git common directory로 찾은 기본 작업 루트 `.env` 순서로 해당 키만 파싱한다. 파일 실행·셸 확장·키 복사·환경변수 주입은 하지 않는다. 이전 PILOT_* 환경변수는 사용하지 않는다.
- 모델 `deepseek/deepseek-v3.2`, provider endpoint `gmicloud/fp8` 고정. 다른 모델·provider로 자동 전환하지 않는다. 해당 경로가 없으면 중지한다.
- B0/B1 모두 `max_tokens=12000`, `temperature=0`, `reasoning.enabled=false`, `usage.include=true`. `provider.only`, `allow_fallbacks=false`, `require_parameters=true`, `max_price`를 함께 보낸다.
- POST socket timeout 600초, GET 30초. 소켓 timeout은 전체 실행 wall-clock 상한이 아니다. 자동 재시도·병렬 실행·외부 도구 호출 없음.
- endpoint가 reasoning 매개변수를 지원해야 요청한다. 응답 `completion_tokens_details.reasoning_tokens`를 기록하고 0이면 `zero_reported_tokens`, 누락이면 `unknown_not_reported`, 양수면 기록 후 추가 요청을 차단한다. 0 보고도 모델 내부 연산을 독립 검증한 것은 아니다. reasoning 본문을 숨기는 `exclude`만으로 비활성화를 주장하지 않는다.
- 응답 model/provider, usage의 prompt/completion tokens·cost·추가 상세 필드, finish_reason과 실제 경과시간을 보존한다. 모델 리비전은 응답 식별자 이상으로 추정하지 않는다.

근거: [키 한도 API](https://openrouter.ai/docs/api_reference/limits),
[reasoning 제어](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
[provider 고정·fallback·가격 상한](https://openrouter.ai/docs/guides/routing/provider-selection),
[실제 endpoint 가격/지원 매개변수 목록](https://openrouter.ai/api/v1/models/deepseek/deepseek-v3.2/endpoints),
[usage 비용 반환](https://openrouter.ai/docs/guides/guides/usage-accounting).
공개 문서는 조사했지만 인증 요청이나 생성 요청은 보내지 않았다.

## 예산 통제

사용자가 **이 실험에만 쓰는 별도 키**에 lifetime 지출 한도 $0.25를 설정해야 한다.
실행기는 한도를 만들거나 수정하지 않는다. 다른 프로그램과 키를 공유하지 않는다.
유료 실행 전 및 각 응답 뒤 `GET /api/v1/key`로 `limit`, `limit_remaining`, `usage`,
`limit_reset`, `byok_usage`를 검사한다. 무한 한도·$0.25 초과·주기적 reset·필수 필드 누락·
불일치·BYOK 사용은 차단한다. 더 낮은 양의 lifetime 한도는 허용한다.
키 label/hash/원문 응답은 보관하지 않고 필요한 수치 필드만 보관한다.

실행기 상한은 **누적 $0.20**이다. 금액 계산에는 Decimal을 사용한다.
각 요청 전 `max(키 lifetime usage, 공용 원장 누적 비용) + 이번 요청 추정 상한 <= $0.20`
및 키 remaining 충분 여부를 모두 확인한다. 응답 후 실제 `usage.cost`로 정산한다.

원장은 Git common directory의 `logicwrite-openrouter-pilot/budget.json`에 둔다.
여러 worktree와 새 결과 디렉터리가 같은 원장과 nonblocking flock 잠금을 공유한다.
잠금은 GET부터 POST·정산 종료까지 유지한다. 새 실행 폴더로 비용을 초기화할 수 없다.
키를 교체해도 이 저장소 원장의 누적 비용은 유지된다. 다른 clone/컴퓨터에서는 공용 원장을
공유하지 않으므로 동일 전용 키의 lifetime usage 확인이 추가 방어선이다.

POST 직전에 전체 요청 상한을 pending으로 원자 저장한다. timeout·API 오류·프로세스 중단·
비용/토큰 누락으로 정산되지 않은 요청이 있으면 다음 실행도 중지한다.
알려진 비용은 기록하되 절단/비정상 응답·사후 한도 조회 실패도 blocked 상태로 둔다.
자동 초기화/원장 reset 옵션은 없다. 이런 경우 OpenRouter 실제 청구와 결과를 사람이 대조하고
별도 결정해야 한다. 원장 삭제로 재실행하지 않는다.

요청별 추정 입력 토큰은 `UTF-8로 직렬화한 메시지 바이트 수 + 4096`이다.
정확한 DeepSeek tokenizer가 아니라 채팅 템플릿 여유를 포함한 보수적 추정이다.
출력 12000토큰 전체를 비용에 반영하고 캐시 할인은 가정하지 않는다.
고정 가격 상한은 입력 **$0.21/M**, 출력 **$0.31/M**, 요청 추가 요금 $0이다.
실제 실행 직전마다 endpoint 가격을 다시 조회하며 상한 초과·불명 추가 요금·지원 매개변수 부족이면 중지한다.
`provider.max_price`에도 같은 상한을 넣는다. 더 비싼 경로를 자동 승인하지 않는다.
가격 변경 때문에 실행할 수 없다면 사용자 검토를 거쳐 별도 변경해야 한다.

| 요청 | 입력 토큰 보수 추정 | 최대 출력 | 비용 추정 상한 USD |
| --- | ---: | ---: | ---: |
| IR-001/B0 | 11260 | 12000 | 0.00608460 |
| IR-001/B1 | 11692 | 12000 | 0.00617532 |
| IR-002/B0 | 9887 | 12000 | 0.00579627 |
| IR-002/B1 | 10319 | 12000 | 0.00588699 |
| IR-003/B0 smoke | 8256 | 12000 | 0.00545376 |
| IR-003/B1 | 8688 | 12000 | 0.00554448 |
| 6건 합계 | — | 72000 | 0.03494142 |

정확한 숫자는 `openrouter-readiness/dry-all/plan.json`이 권위 자료다.
이 수치는 실제 지출이 아니며 토큰화·서비스 청구의 수학적 보장도 아니다.
실행 전 대상과 상한을 stdout 및 `plan.json`에 표시하고, 각 요청도 별도 한도 검사한다.
추정 초과가 응답에서 관측되면 후속 요청을 중지한다. 서버 $0.25 한도는 별도 방어선이며,
실행기는 불명확한 비용을 0으로 간주하지 않는다.

## 사용 순서

API 키가 없어도 기본 실행은 네트워크를 사용하지 않는 dry-run이다.
아래 명령은 저장소 루트 기준이고, 매번 존재하지 않는 출력 경로를 사용해야 한다.
B2는 현재 미지원 상태를 유지하며 이번 실행 옵션에 포함하지 않는다.

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --smoke --output /tmp/ir-openrouter-dry-smoke-01
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --case IR-002 --arm B1 --output /tmp/ir-openrouter-dry-002-b1-01
```

사용자가 OpenRouter에서 키의 lifetime $0.25 한도를 설정하고, 로컬 `.env` 또는 터미널 환경에
`OPENROUTER_API_KEY`를 안전하게 설정한 뒤 **명시적으로 다음 명령을 실행할 때만**, Git 보호·과거 객체 검사까지 통과한 경우 유료 요청한다.
키를 명령 인수나 공유/추적 파일에 적지 않는다. `.env` 내용 출력·셸 실행·Git 추가를 하지 않는다. 파일에서는 OPENROUTER_API_KEY만 안전하게 파싱한다.

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --execute --smoke --output /tmp/ir-openrouter-live-smoke-01
```

첫 실행은 IR-003/B0 1회만 가능하다. `IR-003/B0/execution.json`의 usage.cost·토큰·
finish_reason·reasoning_observed와 `response.json`의 전체 문서를 사람이 확인한다.
`finish_reason=stop`은 모든 요구 문서가 완전하다는 자동 판정이 아니다.
서식 권한·무수정 전체 원문·정당한 부분 보류를 직접 검토한다. HTTP 연결 성공도 의미 평가 성공은 아니다.

그 후 사용자가 실측 비용과 출력 완전성을 확인했다면 다음 명령으로 남은 5건을 순차 실행한다.
`--confirm-smoke-reviewed`는 이 사람 확인을 명시하는 옵션이며 확인 사실을 AI가 자동 확정하지 않는다.
원장에 성공한 smoke가 없으면 이 옵션만으로 통과하지 않는다.

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --execute --confirm-smoke-reviewed --output /tmp/ir-openrouter-live-remainder-01
```

한 요청만 선택하려면 `--case IR-001 --arm B0` 등을 추가한다. 이미 완료한 동일 사례/방식은
재호출하지 않고 `skipped_previously_completed`로 기록한다. 재평가를 위해 원장을 지우지 않는다.
기존 결과는 덮어쓰지 않으며 새 폴더에만 기록한다.

## 산출물과 실패 구분

- `plan.json`: 실행 대상·입력 상한 추정·가격 상한·예상 비용·기준 commit. dry-run도 생성한다.
- `IR-*/B*/input.json`: 평가 입력만 담은 실제 메시지. 정답·기준·검수 의견·태그를 넣지 않는다.
- `request.json`: 인증 헤더를 제외한 정확한 POST payload.
- `response.json`: 실제 공급자 응답. 예기치 않은 키 echo에 대비해 키 문자열을 치환한 사본이며 무조건 원시 바이트라고 주장하지 않는다.
- `execution.json`: 요청 시도 수, 실제 시간·usage·model/provider, 비용/한도/가격 검사와 실패 상태. API 오류 본문/예외 메시지에는 키가 섞일 수 있어 로그에 그대로 적지 않는다.
- `timeout`, `output_truncated`, `api_error`, `accounting_or_preflight_failure`를 구별한다. 비용/한도/가격 실패 이유도 별도 기록한다. 실패하면 배치를 즉시 종료한다.
- CLI 종료 메시지는 안전한 고정 사유만 표시한다. D/Q/F/HITL 및 사람 최종 의미 판정은 자동 승인하지 않는다.

## 오프라인 검증

`test_openrouter.py`는 HTTP를 fake로 대체하고 가짜 자격증명만 사용한다. 실제 모델 응답을
생성했다고 주장하지 않으며 fake 결과는 테스트 임시 디렉터리 밖에 저장하지 않는다.
한도 없는/초과/reset 키, 누적 비용·요청 사전 예약, 가격 불명/상승, 비용 누락, timeout,
출력 절단, API 오류, smoke 검토 경계, 동시 실행 잠금, 키 redaction, B0/B1 설정 동일성을 검증한다.
`openrouter-readiness/`의 dry-run은 키를 환경에서 제거하고 실행했다. 실제 API 인증·지원 여부와
실측 비용은 아직 미검증이다. 공개 endpoint가 현재 가격을 제공해도 이후 가용성을 보장하지 않는다.

검증 결과: 실행기 테스트 **25개 PASS**, 기존 통합 평가 회귀 **63개 PASS**.
개발 골드 registry 검사 및 기존 활성 골드/PR #34/IR 자료 보존 검사도 PASS.
로그는 `openrouter-readiness/tests.log`, `regression.log`, `gold-validation.json`, `preservation.json`이다.
새 구현은 먼저 실패하는 예산 테스트를 실행한 뒤 구현했고, API 오류 분류 회귀도 실패→통과를 확인했다.
HTTP 응답/청구 검증은 아직 수행하지 않았으므로 첫 smoke의 사용자 확인이 필요하다.

후속 보안 검사: `.gitignore`는 모든 깊이의 `.env`와 `.env.*`를 제외하고 `.env.example`만 허용한다.
실제 실행기는 키를 읽은 후 Git 추적 파일·해당 파일 ignore 여부와 **모든 로컬 Git 객체**를 검사한다.
현재 키와의 정확 일치 또는 OpenRouter 키 형식 발견 시 API GET/POST 전에 차단한다.
브랜치 커밋뿐 아니라 로컬 Codex 스냅샷 tree·dangling 객체도 포함하며, 원격 유출을 의미한다고 단정하지 않는다.
기본 작업 디렉터리의 다른 브랜치에도 즉시 보호를 적용하기 위해 공유 `.git/info/exclude`에 같은 로컬 규칙을 추가했다.
이 로컬 규칙과 `.env`는 커밋하지 않는다.

## 폐기 확인 이후의 현재 키 검사

사용자가 이전 키 폐기를 명시적으로 확인했다. 실행기는 이전 감사에서 확인한
Git blob `496bf0e9b647a6e7974897368c316aef7f7d4bbf` 하나만 폐기 확인 예외로 구분한다.
이 blob이 있어도 현재 키 바이트와 일치하면 먼저 차단한다. 다른 미확인 키 형식도 계속 차단한다.
`current_key_absent_from_git`, `revoked_local_blob_matches`, warning을 별도로 기록하며,
폐기 여부는 사용자 확인에 근거하고 OpenRouter로 이전 키를 다시 인증하지 않는다.
Git snapshot/ref/객체를 삭제하거나 이력을 재작성하지 않았다.
기존 `$0.25` 서버 키 한도, `$0.20` 누적 예산, 가격 상한과 단일 smoke 조건은 유지했다.
결과는 [ROTATED-KEY-SMOKE.md](ROTATED-KEY-SMOKE.md)를 참조한다.

## Reasoning 허용 비교 버전

사용자가 reasoning 허용 및 정산된 기존 차단 복구를 별도로 승인했다.
새 실행기는 comparison_v2.py이고 [규약](PROTOCOL_REASONING_V2.md)과
[실제 비교 시도 보고서](reasoning-comparison-20261117/REPORT.md)를 따른다.
기존 run.py와 위 reasoning 비활성화 기록은 보존한다. 새 버전은 신규 최대 6회,
기존 비용 유지·정확한 과거 증거 대조·복구 감사·전역 잠금을 적용한다.
이번에는 신규 첫 응답 후 즉시 서버 사용량이 지연돼 중단했으며, 뒤에 정산 일치가 확인돼도
새 차단은 임의 해제하지 않았다. B1 및 나머지 5건을 실행했다고 해석하지 않는다.

정산 반영 지연 보완과 사용자 승인 감사 해제 후의 최신 기록은
[settlement-followup-20261117/REPORT.md](settlement-followup-20261117/REPORT.md)를 참조한다.
기존 IR-003/B0 재호출 없이 IR-001/B0·B1을 실행했지만 B1이 요청 총 출력 상한을 초과해 다시 차단됐다.
이 새 차단을 자동 해제하거나 토큰 상한을 늘리지 않았다.

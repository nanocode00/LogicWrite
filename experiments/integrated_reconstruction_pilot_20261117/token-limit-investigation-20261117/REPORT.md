# 출력 토큰 상한 조사 — 2026-11-17

상태: 조사 및 오프라인 검증 완료. 신규 유료 생성 요청 **0회**. 기존 원장·실행기·실행 기록·Core·골드·평가 기준을 변경하지 않았다. 사람 최종 의미 평가는 미확정이다.

## 관측 사실과 원인 경계

기존 `PROTOCOL_REASONING_V2.md`, `reasoning-comparison-20261117/REPORT.md`, `settlement-followup-20261117/{REPORT.md,token-limit-check.json,ledger-final.json}`, `comparison_v2.py`, `run.py`를 확인했다.

IR-001/B1의 저장된 요청은 `max_tokens=12000`, reasoning enabled, temperature 0, 모델 `deepseek/deepseek-v3.2`, provider only `gmicloud/fp8`, fallback false, require_parameters true다. 실행기는 urllib로 JSON을 직접 전달한다. 클라이언트 SDK의 파라미터 변환은 없다.

응답은 HTTP 200, completion_tokens **16025**, reasoning_tokens **14280**, 최종 응답분 **1745**, finish_reason **stop**, 비용 **$0.0054336456**다. reasoning은 completion에 포함되므로 둘을 더하면 안 된다. 입력 2262토큰과 endpoint 단가로 계산한 `2262 × 0.0000002088 + 16025 × 0.0000003096`가 실제 비용과 정확히 일치한다. stop은 모델 종료 상태이지 요청 상한 준수나 문서 완결성의 인증이 아니다.

기존 generation ID의 읽기 전용 GET 메타데이터도 native completion 16025, native reasoning 14280, GMICloud, stop을 반환했다. 모델 메타데이터에는 `deepseek/deepseek-v3.2-20251201`이 기록된다. 별도 tokens_completion=20260 및 tokens_prompt=2289는 native/응답 usage와 다른 지표이며 청구량에 추가하지 않는다. 메타데이터 total_cost=.005433645는 응답 비용보다 정밀도가 낮다. 공급자 응답 요약 1건은 status 200이나 실제 upstream 요청 본문은 제공하지 않는다. 인증정보 없이 선별 저장한 근거는 `existing-generation-metadata.json`, `provider-response-metadata.json`이다.

**확인된 직접 원인:** 실제 청구에 대응하는 completion이 요청 상한을 4025토큰 초과했다. 실행기는 실제 비용을 먼저 보존하고 차단했으며 reasoning 이중 합산 오류가 아니다. **근본 원인은 미확정:** OpenRouter가 upstream으로 넘긴 제한 값과 GMICloud 내부 처리를 확보하지 못했다. visible-only 제한, 변환 중 누락/덮어쓰기, 공급자 제한 또는 집계 의미 차이는 가설이다. 최종 응답분 1745가 12000 미만이라는 사실만으로 visible-only 구현을 입증하지 않는다. 공개 자료 조사에서 이 정확한 조합의 확정된 장애 설명은 확보하지 못했다.

## 공식 지원과 실제 검증의 구분

- [OpenRouter 파라미터](https://openrouter.ai/docs/api_reference/parameters): 대부분의 공급자에서 max_tokens는 reasoning과 visible 출력을 함께 제한한다. max_completion_tokens도 같은 의미이므로 이름 교체만으로 해결되지 않는다. 모든 경로에서 강제된다는 보장은 문서에서 확인되지 않는다.
- [Reasoning 제어](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens): reasoning은 출력 비용에 포함된다. enabled=true는 기본 reasoning 활성화이며 수치 예산이 아니다. exclude는 응답 노출 제어이며 계산·과금 중단이 아니다. 직접적인 reasoning.max_tokens 지원 설명은 Gemini, Anthropic, 일부 Qwen thinking에 해당한다. DeepSeek/GMICloud의 정확한 수치 예산 전달은 확인되지 않았다. effort와 수치 예산은 혼용하지 않으며, effort 매핑은 정확한 토큰 상한과 다르다.
- [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection): require_parameters는 선언된 지원 매개변수로 경로를 필터링한다. 하위 필드의 정확한 의미 및 실제 상한 준수를 실행 중 검증하는 기능이라는 근거는 없다. only에 정확한 endpoint 태그를 고정하고 fallback을 끈다. max_price는 백만 토큰당 단가 한도이지 요청별 총 청구 한도가 아니다.
- [GMICloud V3.2 quickstart](https://docs.gmicloud.ai/model-quickstarts/text/deepseek-ai-deepseek-v3-2)는 max_tokens 예제를 제공하지만 reasoning 예산 변환은 설명하지 않는다. [일반 API 문서](https://docs.gmicloud.ai/inference-engine/api-reference/llm-api-reference.md)는 모델별 지원 차이를 명시하며 max_tokens 기본값/범위 표도 이 모델의 정확한 보장으로 사용할 수 없다.
- [DeepSeek 모델 카드](https://huggingface.co/deepseek-ai/DeepSeek-V3.2)의 thinking_mode는 모델 템플릿 능력이지 GMICloud 전송 파라미터 증거가 아니다. 현재 DeepSeek 직접 API 문서의 최신 모델 제어를 이전 V3.2 공급 경로에 소급 적용하지 않는다.
- [Generation 조회 API](https://openrouter.ai/docs/api/api-reference/generations/get-generation)와 [usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)은 조회·집계 근거다. 조회 가능한 요약만으로 원본 upstream 요청을 재구성할 수 없다.

## 경로 및 비용 비교

공개 catalog/endpoints GET 확인: **2026-11-17 07:43 UTC (16:43 KST)**. 정확한 URL·조회 시각·선별 metadata는 `public-catalog-snapshot.json`, 계산은 `cost-scenarios.json`에 보존했다. 표는 모델 전체 최저가가 아닌 지정 endpoint의 일반 서비스 가격이며 USD/백만 토큰이다. 가격·지원 선언은 재실행 직전에 재확인해야 한다.

| 모델 / 고정 provider | 입력 / 출력 | 선언된 최대 completion | reasoning·JSON 지원 및 한계 | 2 probe + 남은 3건 추정 |
|---|---:|---:|---|---:|
| DeepSeek V3.2 / gmicloud/fp8 | .2088 / .3096 | 147456 | reasoning 지원, supported_efforts 없음; JSON 강제 필드 미등재. 실제 12000 초과 관측 | $.0177509448 |
| DeepSeek V3.2 / deepinfra/fp4 | .26 / .38 | 147456 | reasoning·JSON/structured_outputs 선언. 수치 reasoning 제한 미검증, fp4 변경도 교란 요인 | $.02190434 |
| Qwen3-235B-A22B-2507 / deepinfra/fp8 | .09 / .55 | 16384 | 비사고 모델, JSON/structured_outputs 선언. 실제 상한과 한국어 품질 미검증 | $.02270045 |
| Gemini 2.5 Flash Lite / google-ai-studio | .10 / .40 | 65535 | 기본 thinking 비활성, 선택적 reasoning·JSON 선언. 이 경로 실제 동작 미검증 | $.01759570 |

[Qwen 공식 모델 카드](https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507), [OpenRouter Gemini 소개](https://openrouter.ai/google/gemini-2.5-flash-lite)를 함께 확인했다. 위 대체 경로는 긴 문서에 필요한 용량과 JSON 지원 선언은 갖추지만 전체 문서 보존·권한 준수·완결성을 보장하지 않는다. Flex/priority 서비스, 자동 모델/provider 교체는 제안에 포함하지 않는다.

추정식은 기존 메시지 UTF-8 byte 수 +4096의 입력 여유 추정치와 출력 12000을 사용했다. IR-002/B0 입력 추정10396, B1 10828, IR-003/B1 9197; 두 probe는 각각 입력512·출력64로 가정했다. 새 모델 tokenizer·템플릿에 대한 수학적 상한 증명은 아니다. 단가 및 제한 준수를 전제로 한 계획값이며 이번 사건처럼 상한이 무시되면 초과할 수 있다. 서버 lifetime 한도가 독립적인 최종 비용 방어선이다.

## 해결책 평가 및 추천

1. **현재 GMI 경로 유지 후 원인 확인:** 원본 upstream max_tokens와 reasoning 변환에 대한 공급자 확인을 먼저 확보한다. 사용자 승인 후 작은 cap stress/JSON probe를 순차 수행할 수 있으나 작은 probe 통과는 12000 강제의 일반 증명이 아니다. 모델·양자화 일관성은 가장 높지만 현재는 남은 평가 재개를 추천하지 않는다. enabled/effort/max_tokens를 근거 없이 추가해 해결됐다고 간주하지 않는다.
2. **같은 모델 DeepInfra fp4로 별도 프로토콜:** 모델 계열 비교 가능성은 일부 유지하지만 provider·양자화·가격이 달라진다. JSON 지원 선언은 장점이고 reasoning 수치 제한은 여전히 미검증이다. 원래 B0/B1과 하나의 통제된 비교로 합치지 않는다.
3. **추천: 비사고 Qwen / DeepInfra fp8의 별도 프로토콜 후보:** 불확실한 reasoning 수치 예산 의존성을 줄인다. 이는 한국어 성능 우수성 주장이 아니다. 새 프로토콜에서 동일 모델·provider·temperature 0·출력12000·JSON 설정·timeout600을 B0/B1에 적용하고 D는 사전 관측 없으면 unobserved로 유지한다. reasoning 문자열이나 토큰량을 D 근거로 쓰지 않는다. 유료 실행 전 별도 승인이 필요하다.
4. **Gemini 비사고 설정 별도 프로토콜:** 추정 비용은 더 낮고 JSON 지원도 선언되어 있다. 추가 대안이나 이번에는 두 경로를 동시에 시험하지 않는다. optional thinking 비활성 제어의 실제 수용 여부부터 확인해야 한다.

출력 한도를 높여 기존 IR-001/B1을 정상으로 바꾸거나 재시도하지 않는다. timeout/stream 취소는 이미 발생한 공급자 계산 비용을 확실하게 제한하지 못하므로 하드 비용 통제의 대체책이 아니다.

## 남은 사례 및 승인할 실행 계획

현 캠페인은 세 번 시도했고 IR-001/B1은 상한 실패로 남는다. IR-002/B0·B1과 IR-003/B1은 **미실행·미평가**다. 기존 IR-003/B0와 새 모델의 B1을 통제된 쌍으로 비교할 수 없다.

추천 후보의 단계는 (1) cap64 stress probe, (2) 작은 JSON probe, (3) 결과와 비용 확인 후 IR-002/B0, (4) IR-002/B1, (5) IR-003/B1이다. 모두 순차·자동 재시도 없음이며 probe 실패 시 이후 호출 중단이다. probe와 평가 입력은 분리하고 정답·평가 기준은 전달하지 않는다. 5회 추정 $.02270045, 제안 추가 단계 한도 $.025. IR-003의 유효한 쌍까지 원하면 **새 Qwen IR-003/B0 1회**를 명시 승인해야 하며 총6회 추정 $.03008930, 제안 단계 한도 $.035다. 이는 원래 실패한 IR-001/B1 재시도가 아니다. 기존 세 사례 전체의 DeepSeek B0/B1 비교 완료로 보고하지 않는다.

현재 원장은 누적 $.0134719416, pending false, blocked true, cost_or_token_bound_exceeded다. 원장을 그대로 유지했다. 로컬 $.20까지 계산상 여유 $.1865280584, 서버 lifetime $.25까지 이전 기록상 여유 약 $.23652806이다. **이번에는 키 상태를 새로 조회하지 않았으므로 실제 현 잔액으로 단정하지 않는다.** 다음 실행 직전 GET /key로 lifetime·reset 없음·누적 사용량·원장 정산을 다시 확인한다. 비동기 usage 반영 차이 또는 미정산이 있으면 생성하지 않는다.

실행 재개 승인에는 다음을 포함해야 한다: 새 모델/provider·새 프로토콜, probe 포함 호출 수, 기존보다 높은 출력 단가 상한(.55/M), 추가 단계 예산, 기존 실패·누적 비용을 보존하는 감사 가능한 새 캠페인 활성화 방식. 현재 차단 원장 우회는 구현하거나 수행하지 않았다. 사용자 측에서 lifetime 한도를 예컨대 $.05로 낮추면 위 6회 추정과 과거 지출을 합한 $.0435612416에 대한 추가 방어가 가능하지만, 한도 변경 역시 이번에 수행하지 않았다. 재개 구현은 전역 누적 원장을 유지하고 이전 실패 이력을 남겨야 한다.

각 응답은 비용 확인→상한 검사→JSON·문서 반환·권한 검사 순으로 확인하고 불명 비용·절단·timeout·모델/provider 불일치에서 중단한다. Q/F 및 HITL 의미 검토는 자동 구조 검사와 별도 기록하며 최종 사람 판정은 사용자에게 남긴다.

## 오프라인 검증 및 보존

새 `test_token_limit_investigation.py`의 5개 테스트는 저장된 실제 응답과 가짜 API만 사용한다. 상한 초과 탐지, reasoning 포함 비용 1회 합산, 정산 후 차단, reasoning/정산 복구로 해당 차단을 해제하지 못함, 중복 실행 차단, 모델/provider 고정을 확인한다. 실행기 동작 수정은 없다.

재현 명령:

```sh
python3 -B -m unittest discover -s experiments/integrated_reconstruction_pilot_20261117 -v
python3 -B -m unittest discover -s evaluation/integrated_reconstruction -v
python3 -B evaluation/integrated_reconstruction/development_gold/validate.py
python3 -B evaluation/integrated_reconstruction/check_preservation.py
```

각 결과는 같은 디렉터리의 `*-tests.log`, `gold-validation.log`, `preservation.log`에 보존한다. 원장 변경 여부와 기존 추적 파일 보존은 `integrity-verification.json`으로 확인한다. 실제 모델 생성 요청은 실행하지 않았다. 공개 metadata GET 및 기존 generation에 대한 인증된 읽기 전용 조회만 수행했다. 키·인증 헤더·.env 내용은 결과물에 기록하지 않았다.

검증 실측: 파일럿 **48/48**, 통합 평가 **63/63**, 개발용 골드 및 보존 검사 **PASS**. 조사 전후 원장 SHA-256 동일, 기존 추적 파일 변경 0개.

# Reasoning 허용 B0/B1 비교 시도 — 1회 이후 안전 중단

2026-11-17. PR #36, 기준 commit b370fa0. 프로토콜 `integrated-reasoning-allowed-20261117-v1`.

**신규 IR-003/B0 1회는 전체 응답을 반환했지만, 직후 서버 사용량 대조에서 중단됐다.
B0/B1 총 6건 비교는 완료하지 못했고 나머지 5건은 미실행이다.**
생성 요청 재시도·추가 provider/model·병렬·문서 적용·발행·Core 변경은 없다.

## 복구와 실제 비용

`recovery/`는 기존 smoke의 원본 기록/응답을 고정 commit과 바이트 대조하고,
현재 서버 usage $0.002708935와 원장 $0.0027089352가 서버 정밀도 내에서 일치함을 확인했다.
원장의 pending=false와 단일 reasoning 정책 위반 이외 상태도 확인했다.
키 lifetime $0.25/reset 없음과 고정 endpoint 가격을 확인한 후 **이전 reasoning 차단만** 해제했다.
기존 비용·실패 상태는 legacy_requests와 원래 결과 파일에 유지한다.
전후 원장과 사용자 승인 근거는 `recovery/recovery-before.json`, `recovery-event.json`, `recovery-after.json`이다.
`run.py`의 기존 프로토콜은 변경하지 않고 comparison_v2.py의 새 경로만 사용했다.

| 관측 | 값 |
| --- | --- |
| 신규 모델/provider | deepseek/deepseek-v3.2 / GMICloud, gmicloud/fp8 고정 |
| 요청 설정 | reasoning.enabled=true, temperature=0, max_tokens=12000(reasoning 포함) |
| HTTP / finish_reason | 200 / stop; 출력 절단 없음 |
| 입력 / 출력 / 전체 토큰 | 1184 / 4370 / 5554 |
| 출력 내 reasoning / 비-reasoning 토큰 | 3642 / 728 (이중 합산하지 않음) |
| 요청 경과시간 | 60.622286459초 |
| 신규 응답 비용 | $0.0016001712 |
| 기존 탐색 smoke 비용 | $0.0027089352 |
| 원장 누적 | $0.0043091064 |
| 실행기 $0.20 대비 잔여 | $0.1956908936 |
| 사후 서버 usage / key remaining | $0.004309106 / $0.245690894 |

새 모델 alias보다 구체적인 공급자 revision은 확인되지 않았다. 실제 payload·응답·usage·HTTP·
시간은 `smoke/IR-003/B0/`에 있다. 원본 provider 응답과 추출한 candidate.json을 구분한다.
키 값·인증 헤더는 포함하지 않는다.

## 중단 원인과 후속 확인

즉시 `/key` 결과는 여전히 **이전 usage $0.002708935**였다. 응답 usage.cost를 더한
원장 $0.0043091064와 달라 실행기가 `post_request_spend_unreconciled`로 차단했다.
이는 모델의 문서 재구성 실패나 reasoning 허용 위반이 아니라 **실행기의 즉시 사용량 일치 검사와
서버 조회 반영 시점의 불일치**다. 제가 추가한 검사가 서버 반영 지연에 지나치게 민감했다.
응답 비용은 이미 원장에 보존됐고 pending=false지만 blocked=true다.

뒤의 읽기 전용 GET 1회에서는 usage $0.004309106으로 갱신되어 차이가 -$0.0000000004로 줄었다.
따라서 관측상 서버 usage가 나중에 따라왔다. 내부 캐시/정산 구현 원인은 확정하지 않는다.
`read-only-settlement-check.json`에 수치를 남겼고 이 조회는 원장을 수정하지 않았다.

이번 승인에서 복구 대상으로 지정한 것은 **이전 reasoning 정책 차단만**이므로,
새 차단을 임의 해제하거나 조건을 바꿔 나머지 생성 요청을 진행하지 않았다.
비용이 나중에 맞았다는 사실과 캠페인 중단 기록을 둘 다 보존한다.
1개의 응답 비용은 확정돼 있으며 미실행 5건의 비용이나 출력을 만들지 않았다.

## 비교표 및 D/Q/F 초안

| 사례 | B0 | B1 | 비교 판단 |
| --- | --- | --- | --- |
| IR-001 | 미실행 | 미실행 | 미평가 |
| IR-002 | 미실행 | 미실행 | 미평가 |
| IR-003 | 전체 후보 관측, 정산 대조 단계에서 실행 중단 | 미실행 | 직접 비교 불가 |

B2는 기존 통합 인터페이스 미지원 상태를 유지한다. 완료된 B0/B1 쌍은 0개다.
모델 전체 성능·성공률·B1 개선을 주장하지 않는다. 출처 가족 1개인 노출 개발 골드라는 경계도 유지한다.

- **자동 검사:** JSON delivery 필드, edit/format_only 전체 문서 ID와 본문 존재, read_only 변경 없음,
  알려지지 않은 문서 ID 없음, stop, 토큰·비용 한도, 모델/provider를 검사했다. meeting 원문과
  후보는 추가 빈 줄을 제외하면 같다. 문서 존재 검사는 의미적 완결성의 증명이 아니다.
- **D:** 전부 unobserved. 사전 계획을 요구하지 않았고, 응답 reasoning으로 D를 역산하지 않는다.
- **AI 의미 초안 Q:** IR-003/B0는 원문 사실·수치·공개 제한을 유지한다. 내부/외부 회의용 선택,
  내용 편집 권한, 공유 범위를 구체적으로 질문하고 public/을 반영했다고 주장하지 않는다.
  Q1~Q4는 초안상 supported이며 확정된 공개판/회의 사용 적합성은 아직 평정할 수 없다.
- **AI 의미 초안 F:** F1/F2는 출력에서 관측되지 않았다. 사람 통과나 최종 승인으로 해석하지 않는다.
- **HITL:** 내용·공유 범위를 부분 보류하면서 허용된 전체 후보를 반환했다. 실행 중단을 HITL 성공으로 세지 않는다.
- **이전 smoke 대비:** 새 B0는 목록 변환 없이 빈 줄만 보완했고, 구체적인 확인 질문을 제시했다.
  이전보다 이 두 지점은 좋아 보인다. reasoning 설정과 공통 JSON delivery도 달라졌으며 B1은
  미실행이므로 이 변화를 B1 효과로 귀속할 수 없다. 무수정 원문 반환도 여전히 유효한 대안이다.

`automatic-summary.json`과 `assessment-draft.json`은 기계 진단/AI 의견을 분리한다.
각 Q/F 근거의 JSON Pointer와 정확 인용은 `assessment-evidence-check.json`으로 확인했다.
이 인용 검사가 의미 판단 자체를 검증하지는 않는다. 사람 최종 판단은 모든 조합에서 null이다.

## 검증 및 재현

신규 실행기/기존 파일럿 단위 테스트 **41개**, 통합 평가 회귀 **63개**, 개발 골드 registry 및 보존 검사 PASS.
새 테스트는 정산된 reasoning만 복구, pending/timeout/불명 비용 거부, 서버 비용 불일치 거부,
6회 상한·실패 재시도 금지·설정/입력 동일성·문서 누락/읽기 전용 변경 거부를 다룬다.
실제로 관측된 서버 사용량 지연은 fake HTTP 회귀에 추가해 비용 보존/차단 유지/추가 POST 0을 확인했다.
실제 생성 후에는 테스트와 읽기 전용 조회만 수행했으며 유료 요청을 더 보내지 않았다.

실행한 명령은 각 phase 로그와 plan.json에 대응한다.

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/comparison_v2.py --output experiments/integrated_reconstruction_pilot_20261117/reasoning-comparison-20261117/dry-run
python3 experiments/integrated_reconstruction_pilot_20261117/comparison_v2.py --execute --phase recover --output experiments/integrated_reconstruction_pilot_20261117/reasoning-comparison-20261117/recovery
python3 experiments/integrated_reconstruction_pilot_20261117/comparison_v2.py --execute --phase smoke --output experiments/integrated_reconstruction_pilot_20261117/reasoning-comparison-20261117/smoke
```

첫 phase에서 만든 6개 요청 템플릿은 **준비 파일**이며 6개 모두 전송했다는 뜻이 아니다.
현재 원장은 blocked이므로 남은 phase 명령으로 우회할 수 없다. 새 결과 디렉터리도 차단을 초기화하지 않는다.
기존 골드 29건·PR #34 자료·IR 입력/기준/참고 출력·계보/포함 승인은 변경하지 않았다.

## 다음 개선 후보

1. 실행기 정산: 확정 응답 cost와 서버 usage의 지연을 별도 상태로 설계할 필요가 있다.
   생성 재시도 없이 정산 확인만 수행하고, 사용자 승인된 감사 전환으로만 후속 요청을 허용하는 방안이 후보이다.
   timeout·불명 cost는 여전히 중단해야 한다. 이번 캠페인 차단은 자동 해제하지 않았다.
2. Core: 문서군 공동 분석·문서별 권한·전체 후보의 정보 보존/모순 검증은 기존 한계다.
   새 JSON delivery 검사를 Core 기능이나 의미적 승인으로 간주하지 않는다. 변경 여부는 사용자 판단이다.
3. 평가 기준: 서식 변경의 필요성, 명확한 질문과 단순 공백 나열의 차이, 정책 충돌의 부분 보류 및
   운영 조건의 문서 간 필요한 반복을 사람 검수로 캘리브레이션한다. 첫 두 사례는 모델 응답이 없어 미평가다.
4. 실제 한국어 사례: 독립 저자/조직의 운영 런북·승인 이력과 조건 변경 문서군을 우선 수집하고,
   README/사용 안내/정책 충돌, 내용 권한이 제한된 회의 문서와 무수정 음성 사례를 뒤따른다.
   권리·원문/편집본·요청·권한·노출/가족 정보를 함께 확보한다.
5. 다음 파일럿: 서버 반영 지연을 사전 점검한 정산 프로토콜과 별도 캠페인 승인 후 미실행 조합을 진행한다.
   이번 실패한 IR-003/B0를 자동 재시도하거나 기존 탐색 결과를 새 비교 결과에 섞지 않는다.

사람 최종 의미 평가, 재개 여부, Core 수정 여부는 사용자에게 남긴다.

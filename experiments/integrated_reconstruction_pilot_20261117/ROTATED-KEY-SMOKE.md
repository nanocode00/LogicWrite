# 교체된 키의 IR-003/B0 smoke 결과

2026-11-17. 기존 보고서와 차단된 시도는 보존한다.
사용자가 이전 키의 폐기를 명시적으로 확인한 뒤 실행기를 보완하고 생성 요청 **1회**를 실행했다.
**HTTP/생성 응답은 성공했으나 reasoning 비활성화 조건은 충족되지 않았다. 후속 생성은 차단했다.**

## 조치 및 보안 경계

`run.py`는 이미 감사한 이전 로컬 blob 하나(`496bf0e9b647a6e7974897368c316aef7f7d4bbf`)만
사용자 폐기 확인에 근거해 경고로 구분한다. 현재 키가 이 blob과 일치하면 예외보다 먼저 차단한다.
다른 미확인 키 형식은 계속 차단한다. 모든 키 패턴을 일괄 무시하거나 객체 검사를 제거하지 않았다.
새 키는 현재 Git 객체에 없고, `.env`는 두 작업 루트에서 ignore·무추적 상태임을 확인했다.
키·인증 헤더는 기록하지 않았고 로컬 Git 객체·ref도 삭제하지 않았다.
폐기는 사용자 확인 사실이며 실행기가 이전 키를 호출해 독립 검증한 것은 아니다.
`revocation-boundary.json`에 범위를 남겼다.

단위/파일럿 **34개 PASS**, 기존 통합 평가 회귀 **63개 PASS**, 개발 골드 및 보존 검사 PASS 후
새 디렉터리에서 dry-run 및 실제 smoke를 수행했다. 현재 키의 한도는 lifetime $0.25,
reset 없음, 초기 usage $0이었다. 고정 endpoint 가격도 사전 상한 이내였다.

## 실제 실행 기록

| 항목 | 관측 |
| --- | --- |
| 사례/방식 | IR-003/B0만 1회; B1 및 IR-001/002 미실행, B2 미지원 유지 |
| 모델 / provider | deepseek/deepseek-v3.2 / GMICloud, 요청 endpoint gmicloud/fp8 |
| HTTP / finish_reason | 200 / stop; 토큰 한도에 의한 절단 없음 |
| 입력 / 출력 / 전체 토큰 | 1,091 / 8,014 / 9,105 |
| 출력 중 reasoning 토큰 | 7,220; completion_tokens에 포함되므로 이중 합산하지 않음 |
| 실제 응답 비용 USD | 0.0027089352 |
| 요청 전 보수적 비용 상한 USD | 0.00545376 |
| 생성 요청 경과시간 | 110.794998597초 |
| 사후 키 usage / remaining USD | 0.002708935 / 0.247291065 (GET /key 반환 정밀도) |
| 실행기 누적 $0.20 대비 잔여 USD | 0.1972910648 (응답 cost 기준) |
| reasoning 요청 / 실제 보고 | enabled=false / nonzero_reported_tokens |
| 실행기 종료 | accounting_or_preflight_failure, reason=cost_token_or_reasoning_policy_violation |
| 후속 상태 | 비용은 원장에 반영, blocked 유지. 자동 재시도·provider/model 전환 없음 |

출력/시간/비용은 실제 관측값이다. `cost_details`의 입력 $0.0002278008 + 출력 $0.0024811344가
전체 비용과 일치한다. 가격은 토큰당 입력 $0.0000002088, 출력 $0.0000003096이었다.
사후 키 상태는 생성 실패 정책 때문에 자동 검사 단계에 도달하지 않아, 별도 **읽기 전용 GET 1회**로 확인했다.
키 한도와 실행기 예산은 변경하지 않았다.

### reasoning 조건의 실패

endpoint는 reasoning 매개변수 지원을 선언했고 실행기는 `reasoning.enabled=false`,
`provider.require_parameters=true`, fallback 금지로 요청했다. 그러나 실제 reasoning 토큰은 양수였다.
따라서 비활성화가 적용됐다고 볼 수 없다. 공급자 내부 원인은 이번 1회로 확정하지 않는다.
추가 실행으로 원인을 시험하거나 다른 모델/provider로 전환하지 않았다.
이번 결과는 원래 비활성화 비교 프로토콜과 불일치한 **별도 smoke 관측**이며 B0/B1 품질 비교로 집계하지 않는다.
사용자 확인 전 원장의 blocked 상태를 해제하지 않는다.

## 문서 후보 검토

자동 검사는 `automatic-output-checks.json`, AI 의미 의견은 `assessment-draft.json`으로 분리했다.
전체 후보는 `candidate-response.md`, 실제 문서 후보는 `meeting.candidate.md`에 있다.
원본 응답은 `live/IR-003/B0/response.json`으로 보존하며 참고 출력을 대체하지 않는다.

- 자동: 편집 가능한 문서는 meeting 1개이며 전체 fenced 후보 1개를 반환했다. 목록 표시와 공백을 정규화하면 원문의 모든 행이 정확히 같다. 바이트 동일본은 아니며 문단 앞에 목록 기호를 추가했다. 이 검사는 의미 평가를 대신하지 않는다.
- AI 초안 Q1/Q3/Q4: 사실·수치·공개 제한·단일 환경 한계가 보존되고, 외부판을 선택하거나 public/을 조회·수정했다고 주장하지 않는다. format_only 범위 내 서식 후보로 판단한다.
- AI 초안 Q2: 독자·공유 범위·내용 권한 공백을 나열하지만 구체적인 확인 질문 형태가 부족하다. 사람 재검수가 필요하다.
- 과잉 편집: 원문은 이미 읽을 수 있었다. 목록 변환의 구체적 필요가 입증되지 않아 가벼운 불필요 수정 가능성을 남긴다. 내용 권한 침해로 자동 판정하지 않는다.
- F1/F2: AI 검토에서 관측되지 않았다. 이는 사람 최종 통과가 아니다.
- HITL: 내용 재작성·공개판을 범위별로 보류한 것은 적절해 보이며, 독립적으로 허용된 후보를 반환했다. 확인 질문의 구체성은 보완 여지가 있다. 실행기 정책 차단을 편집 HITL 성공으로 세지 않는다.
- D1~D3: 모두 unobserved. 응답과 함께 돌아온 provider reasoning을 편집 전 별도 기록으로 인정하거나 D 점수로 역산하지 않는다.

Q 품질 축의 잠정 점수와 근거는 AI 초안에만 기록했다. **최종 사람 의미 검수는 null**이다.
실제 파일 적용·발행, Core·골드·기준 변경, 새 PR·병합은 수행하지 않는다.

## 재현과 다음 경계

이번 실행 명령(같은 결과 경로 재사용 금지):

```sh
python3 experiments/integrated_reconstruction_pilot_20261117/run.py --execute --smoke --output experiments/integrated_reconstruction_pilot_20261117/smoke-rotated-key-20261117/live
```

실행 설정은 `request.json`, 사전/사후 한도는 `execution.json`/`key-status-after.json`, 로그는 `live.log`다.
현재는 reasoning 정책 위반으로 원장이 blocked여서 새 폴더로도 다음 유료 요청을 보내지 않는다.
다음 조치는 이번 응답의 비용·완전성과 reasoning 정책 처리 방식을 사용자가 검토한 뒤 별도로 결정한다.

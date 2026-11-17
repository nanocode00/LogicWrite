# Reasoning 허용 통합 재구성 비교 규약

2026-11-17. ID: `integrated-reasoning-allowed-20261117-v1`.
사용자가 정산된 이전 reasoning 차단의 복구와 신규 6회 비교를 명시적으로 승인했다.
기존 run.py의 비활성화 규약·응답·로그는 그대로 보존하고 새 comparison_v2.py만 사용한다.

- 모델 deepseek/deepseek-v3.2, endpoint gmicloud/fp8 고정. reasoning.enabled=true,
  temperature=0, max_tokens=12000(reasoning 포함). fallback·재시도·병렬·외부 도구 없음.
- 기존 BASE/B1 일반 개선 지침에 양쪽 공통 JSON delivery 형식만 추가한다. 문서별 document_id/content 전체와
  review_notes/unresolved_questions/final_checks를 분리한다. 모델 user 메시지는 검증된 입력만이다.
  사례별 기준·참고 출력·과거 smoke 평가를 프롬프트에 넣지 않는다. B1을 IR-003 실패에 맞춰 튜닝하지 않는다.
- 자연 출력 비교다. 사전 판단 제출을 요구하지 않아 D는 unobserved. provider reasoning으로 D를 역산하지 않는다.
- 기존 키 보호·현재 키 검사·폐기 확인 blob 예외와 공유 원장을 재사용한다. 키 lifetime 최대 $0.25,
  실행기 누적 $0.20, 입력 바이트+4096 추정 및 최대 출력 전체 비용 사전 예약을 유지한다.
  입력 $0.21/M·출력 $0.31/M ceiling과 실제 endpoint 가격을 매 요청 전에 확인한다.
- recover phase는 유료 생성 없이 현재 서버 usage·한도·endpoint와 고정 b370fa0의 기존 smoke 응답/기록을
  대조한다. 기존 exact state, pending=false, 비용 일치, HTTP200/stop, 유일한 reasoning 위반 조건에서만
  blocked를 false로 바꾼다. before/event/after를 남기고 비용·기존 실패·응답 해시는 보존한다.
  현재 서버 usage와 원장 비용의 허용 오차는 $0.000001(키 API 정밀도)이다.
- 신규 캠페인은 별도 attempts에 기록한다. IR-003/B0 먼저 1회 실행하고 전체 편집 문서·자체검증 필드·
  비용·모델·provider·stop을 확인한다. 실행자가 직접 후보를 검토한 후 confirm-smoke-checked로 나머지
  IR-001/B0, IR-001/B1, IR-002/B0, IR-002/B1, IR-003/B1을 순차 실행한다.
  이 확인은 사용자에게 승인받은 실행 점검이며 최종 사람 의미 평가를 뜻하지 않는다.
- 캠페인 전체 최대 6 attempts. 실패·timeout·불명 cost는 차단/보류 원장을 유지하고 재시도하지 않는다.
  완료 대상도 다시 호출하지 않는다. 새 결과 폴더로 제한을 초기화할 수 없다.
- 각 응답의 usage.cost·prompt/completion/reasoning/non-reasoning tokens·경과시간·HTTP·finish_reason을
  기록한다. reasoning은 completion에 포함되므로 이중 합산하지 않는다. 모델 alias 이상의 revision은 unknown.
- 기계 검사는 문서 ID/전체 후보 존재·빈 본문·권한 없는 새 문서·읽기 전용 원문 일치를 확인한다.
  구조적 전체성은 문서 내용의 의미적 완결성을 보장하지 않는다. 토큰 절단/미완성은 완료로 집계하지 않는다.
  의미 검토는 AI 초안, 최종 사람 판정은 null로 분리한다. F 중대 위반은 Q 문체 점수와 상쇄하지 않는다.
- 기존 참고 출력·Core·골드·평가 기준·활성29/PR34자산을 수정하지 않는다. 실제 문서 반영/발행 없음.

CLI는 --execute 없으면 항상 offline이며, 단계별로 새 --output을 요구한다.
prepare/recover/smoke/remaining 단계 및 --confirm-smoke-checked가 있다.
실제 사용 명령·정산 전환·결과 비교는 별도 결과 폴더에 남긴다.

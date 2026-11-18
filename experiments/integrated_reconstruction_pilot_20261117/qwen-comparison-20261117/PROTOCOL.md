# Qwen 독립 B0/B1 비교 규약

ID `integrated-qwen-instruct-20261117-v1`, 2026-11-17. 사용자 명시 승인: probe 2회 + 평가 최대6회, 신규 지출 $.06. DeepSeek 실험과 별개이며 기존 실패 판정은 보존한다.

- OpenRouter `qwen/qwen3-235b-a22b-2507`, `deepinfra/fp8` 일반 endpoint만 허용. temperature0, 평가 max_tokens12000, timeout600초. reasoning 설정 미전송. JSON object 반환. fallback·병렬·재시도 없음.
- B0/B1은 기존 일반 BASE/IMPROVED와 공통 delivery를 사용한다. user 메시지는 export_input 결과뿐이다. 모델에 기준·골드·참고 출력·이전 응답/검수 의견은 전달하지 않는다. B1의 사례별 튜닝 없음. D 사전 관측 없으므로 unobserved.
- Probe-A는 독립 숫자목록 요청에 max_tokens64를 적용한다. 이 probe에서만 length 종료를 정상적인 제한 작동으로 허용한다. Probe-B는 독립 demo JSON 문서에 max_tokens256을 적용한다. 평가 6건은 stop 및 전체 편집 가능 문서 후보가 필요하다. 두 probe 성공은 긴 출력 제한의 일반 증명이 아니다.
- 순서 Probe-A, Probe-B, IR-001/B0, IR-001/B1, IR-002/B0, IR-002/B1, IR-003/B0, IR-003/B1. 한 번에 한 target만 실행한다. 각 응답의 자동 검사와 실행자 내용 검토 후 다음으로 진행한다. 구조 실패·미완성·중대한 권한 위반 확인 시 후속 호출 중단, 재실행 없음. 의미 검토의 모호한 기준 경계는 별도 AI 초안으로 남기고 사람 확정 판정으로 바꾸지 않는다.
- 매 호출 직전 GET /key와 endpoint를 확인한다. lifetime 최대$.25, reset없음, BYOK없음, 단가 input$.09/M output$.55/M 이하. 정확한 endpoint identity·서비스 등급·fp8·가용성·파라미터·context·출력용량을 검사한다. 실제 응답 model/provider도 대조한다. 모델 가중치/serving revision은 API가 제공하는 범위만 기록한다.
- 기존 공유 원장은 삭제/초기화하지 않는다. 기존 ledger-final과 일치, 모든 비용 정산·누적합 일치·서버 usage일치 시에만 감사 활성화한다. 기존 blocked=true·block_reason·DeepSeek attempts를 그대로 두고 새 캠페인만 scoped 실행 허용한다. 옛 실행기는 여전히 차단된다. 새 캠페인 실패는 별도 blocked에 기록하며 동일 target·순서변경·9번째 요청을 허용하지 않는다.
- 전역$.20와 신규$.06를 독립 검사한다. UTF8bytes+4096 입력 추정 + max출력 단가로 사전 심사·표시·예약한다. 이는 tokenizer/공급자 강제의 증명이 아니며 서버 lifetime이 독립 방어선이다. 응답 cost를 토큰·형식 검사보다 먼저 정산한다. reasoning 토큰을 completion에 더하지 않는다. 비사고 모델의 reasoning 누락은 카운터 미제공으로 기록하고 양수이면 차단한다.
- /key 반영 지연은 알려진 응답 cost를 유지하면서 max(로컬,서버)로 통제한다. 이는 불명 비용 미정산과 다르다. activation은 완전 정산이 필요하다. 미확인 추가 usage·역행·비용/한도조회 실패·timeout이면 중단, 미정산 예약 유지한다. 조회를 위한 자동 polling도 없다.
- 후보는 실험 디렉터리에만 저장한다. 기계적인 전체 문서 존재와 실제 의미 완결성은 구분한다. 내용 보존·권한·D/Q/F·HITL은 별도 AI 평가 초안, 사람 최종판정 null. F 중대위반을 Q로 상쇄하지 않는다. 3개 합성 사례로 일반 성능 개선 주장 없음.

CLI: comparison_qwen.py --phase prepare|activate|request --output NEW_DIRECTORY [--target TARGET] [--execute]. 기존 결과 디렉터리 덮어쓰기 금지. 새 runner와 기존 run.py/comparison_v2.py 해시를 plan에 기록한다.

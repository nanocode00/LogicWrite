# G3~G4 검증 기록

2026-11-10, 기준 main `7b9166de9c019153ceb326aef8912380ddc60d71`(PR #17 및 #19 병합 포함).

| 확인 항목 | 결과 |
| --- | --- |
| G3 준비 | 기존 12건의 원본 참조·입력/답안 해시·사용자 의견·노출 상태 확인. v1으로 만든 빈 이벤트 기록 12개 모두 ai_provisional·development_gold_eligible=false |
| 기존 자료 보존 | 기존 27개 데이터/스키마 파일은 보존 장부와 일치. semantic_pilot의 기존 추적 파일 53개는 main Git 바이트와 일치. docs·Core·fixture 및 기존 평가 자료 추가 diff 없음 |
| G4 구성 | GC-001~012, 정상 4·위반 4·보류 4. 원문/저장소 계열 4개, 전부 개발용. provisional·gold_eligible=false·새 사람 검토/재정 없음 |
| 출처·라이선스 | 원문 4·라이선스 4·NOTICE 2의 SHA-256/Git blob 및 고정 commit URL 확인. GitHub contents API의 실제 blob SHA와 10개 대조 |
| 스키마·참조 | GC 네임스페이스의 별도 스키마와 기존 validate_pair로 입력/답안·양쪽 근거·문서 해시 검사. source registry·manifest 바인딩, 읽기용 Markdown과 JSON 입력 일치 |
| 분리 정책 | 기존 6+신규 4 개발 계열 제외 목록 확인. 동일 계열 split 혼입 거부 테스트 통과. 홀드아웃 원문/정답/수집 결과는 생성하지 않음 |
| 신규 검사 | `python3 evaluation/g3_g4/validate.py` 통과 |
| 신규 테스트 | `python3 -m unittest discover -s evaluation/g3_g4 -p test_validate.py` — 17건 통과 |
| 기존 파일럿 | validate.py 및 test_validate.py — 21건 통과 |
| 기존 단일 사용자 검수 | user_review_v1/test_workflow.py — 34건 통과 |
| 기존 입력 전용 패키지 | independent_review/test_review_package.py — 9건 통과 |
| 최신 main Core 회귀 | full_document_control/test_*.py — 309건 통과. Core 코드는 변경하지 않음 |
| 문서·공백 | 로컬 문서 상대 링크와 git diff --check 통과 |

로컬 테스트 총 **390건**. 테스트는 스키마·참조·해시·준비 상태 및 오염/승격 방지 검사이며 의미 라벨 정확도·실행 동작·독립 사람 검수·실제 홀드아웃 독립성을 입증하지 않는다. AI 잠정 라벨은 모델/기존 검증기 출력을 정답으로 가져온 것이 아니라 원문에 대한 통제 수정의 제안이다. 사람 검수 전에는 골드가 아니다.

G3의 새 AI 반례 검토는 not_run, 사용자 최종 확정은 not_confirmed다. 메타데이터 초기화와 진행표는 사용자의 새 최초/최종 판단이나 검토 이벤트를 대신 작성한 기록이 아니다. 파생 사례는 설계 제안만 있고 입력·정답을 생성하지 않았다.

Antigravity 문서 조언 요청은 quota 429로 실패해 Codex가 문서를 작성·검증했다. 로컬 테스트와 GitHub CI는 별도이며 실제 병합은 하지 않는다.

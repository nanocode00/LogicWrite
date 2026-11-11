# 검증 결과 — 2026-11-11

기준 main: `29dd271c5e367044af765cc0ff9e81db52de7160` (PR #21 병합). 이 트랙은 `evaluation/golden_expansion/`만 추가하며 Core와 기존 평가 파일을 변경하지 않는다.

| 검사 | 명령 | 결과 |
| --- | --- | --- |
| 신규 패키지·186개 기존 파일 보존 | `python3 evaluation/golden_expansion/validate.py` | GC 12 + SP 파생 5, 사람 판정 대기 17, 신규 골드 0, 기존 파일 186개 일치 |
| 신규 검수 경계·내보내기·무효 입력 | `python3 -m unittest discover -s evaluation/golden_expansion -p 'test_*.py'` | 19 통과 |
| 기존 파일럿 | `python3 -m unittest discover -s evaluation/semantic_pilot -p test_validate.py` | 21 통과 |
| 기존 SP 검수 프로토콜 | `python3 -m unittest discover -s evaluation/semantic_pilot/user_review_v1 -p 'test_*.py'` | 34 통과 |
| 기존 입력 패키지 | `python3 -m unittest discover -s evaluation/semantic_pilot/independent_review -p 'test_*.py'` | 9 통과 |
| 기존 G3/G4 | `python3 -m unittest discover -s evaluation/g3_g4 -p 'test_*.py'` | 17 통과 |
| 기존 최종 검수 기록 | `python3 -m unittest discover -s evaluation/g3_g4/final_review_2026-11-11 -p 'test_*.py'` | 24 통과 |
| 활성 개발용 골드 v2 | `python3 -m unittest discover -s evaluation/g3_g4/development_gold_v2_2026-11-11 -p 'test_*.py'` | 14 통과 |
| 기존 데이터 검사 | `python3 evaluation/semantic_pilot/validate.py`, `python3 evaluation/g3_g4/validate.py`, `python3 evaluation/g3_g4/development_gold_v2_2026-11-11/validate.py` | 모두 통과; 활성 골드 12와 P/V/U 4/4/4 유지 |
| 입력 전용 ZIP | `python3 evaluation/golden_expansion/export.py` | 53 파일, SHA-256 `926f1292c26cb5a1a43d947f27a3f7c16246209732a85a5aad446ba469a50396` |
| 공백 검사 | `git diff --check` | 통과 |

합계 138개 테스트 통과(신규 19 + 기존 119). 코드의 기계적 검증은 의미 정답이나 실제 사람 판정을 대신하지 않는다. 테스트의 합성 human 이벤트는 메모리/임시 디렉터리에서만 사용하며 실제 검수 기록으로 저장하지 않는다.

공개 문서·라이선스·NOTICE 10개를 고정 커밋 raw GitHub URL에서 다시 가져와 기존 바이트 SHA-256과 대조했다. 기존 쌍 검증기를 재사용하여 문서 내용 해시, Git blob, 전체 원문, 후보·계약 출력 범위, AI 잠정 답안의 Unicode 근거 위치와 인용을 검사했다. `revalidation.json`은 사례별 입력·답안·계약·문서 버전을 연결한다. 이 검사로 외부 사실이나 소프트웨어 실행을 입증하지 않는다.

별도 Codex AI가 기존 잠정 답안·설명문을 읽지 않고 입력만으로 17건을 검토했다. 잠정 판단은 기존 GC 12건 및 신규 SP 5건의 AI 제안과 일치했으나 강한 반론과 한계를 함께 기록했다. 이 일치는 독립 사람 검수·골드 적격·정확도 측정이 아니다. 사전 AI 검토를 사용자 최초 판단 후의 정식 반례 이벤트로 취급하지 않는다. 사람이 최초 판단한 이후 그 판단을 대상으로 다시 반례 검토하고 최종 포함 승인을 받아야 한다.

독립 검토에서 직접 실행 시 테스트 8개만 실행되는 `unittest.main()` 위치 문제를 발견해 파일 끝으로 옮겼다. 직접 실행과 discover 모두 19개 실행을 재확인했다. 독립 검토자는 GC/SP 등록 범위 거부, 기존 승인 게이트 의미의 유지, SP-015 이동된 원문 블록의 완전 보존을 추가 확인했다.

문서 초안 위임을 위해 Antigravity CLI를 실행했으나 `RESOURCE_EXHAUSTED`/429 개인 할당량 오류로 초안을 얻지 못했다. 문서는 실제 파일·실행 결과에 근거하여 Codex가 작성하고 별도 검토로 사실을 확인했다. Antigravity 성공 결과를 주장하지 않는다.

# 최종 검수 검증 결과

2026-11-11 실행. 이전 PR #21 HEAD `4fd828d`에서 최신 main `37ed980e82e526cc0e532fae01f88d56a3b6750f`(PR #20 병합)를 충돌 없이 반영한 뒤 검사했다. main에서 받은 Core 변경 외에 Core 추가 수정은 없다.

| 명령 (저장소 루트 기준) | 실제 결과 |
| --- | --- |
| `python3 evaluation/g3_g4/final_review_2026-11-11/validate.py` | 사용자 최종 승인 12, 활성 개발용 골드 11, 차단 SP-009, 이전 파일 153개 보존 |
| `python3 -m unittest discover -s evaluation/g3_g4/final_review_2026-11-11 -p test_final_review.py` | 24건 통과 |
| `python3 evaluation/semantic_pilot/validate.py` | 기존 12건 provisional 및 원본 4/4/4 구조·해시·근거 검사 통과 |
| `python3 evaluation/g3_g4/validate.py` | 과거 G3 준비 12건, G4 provisional 개발 후보 12건 검사 통과 |
| `python3 -m unittest discover -s evaluation/semantic_pilot -p test_validate.py` | 21건 통과 |
| `python3 -m unittest discover -s evaluation/semantic_pilot/user_review_v1 -p test_workflow.py` | 34건 통과 |
| `python3 -m unittest discover -s evaluation/semantic_pilot/independent_review -p test_review_package.py` | 9건 통과 |
| `python3 -m unittest discover -s evaluation/g3_g4 -p test_validate.py` | 17건 통과 |
| `python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'` | 340건 통과 |

총 **445건 모두 통과**, 이번 실행에서 예상하지 못한 테스트 실패 0건. 음성 테스트는 훼손한 임시 복사본이 의도대로 거부되는지 검사하며 실제 사용자 기록을 바꾸지 않는다.

새 계층은 사용자 승인과 실제 적격의 구분, 원본 153개 파일, 11개 이전 이벤트 prefix, 해시 체인·시간·단계, AI를 사용자로 바꾼 최종 이벤트 거부, 반론별 응답·근거, SP-003의 판단 변경 이력, SP-006 오류 두 건, UNRESOLVED 사유, 활성 분포 4/4/3, SP-009 소급 연결/단계 건너뛰기 거부를 검사했다.

G4 입력·답안·출처·manifest·분리 계획과 기존 semantic_pilot 전체가 보존 장부의 이전 Git 바이트 SHA-256과 일치한다. 기존 g3-progress.json과 prepared/ 및 review_round_2026-11-11/도 그대로다. 기존 데이터·워크플로 스키마·검증 기준을 변경하지 않았으며 최종 상태만 별도 파일로 추가했다.

사용자 명시 판정은 12건 4/4/4로 보존했다. v1 적격은 11건이며 SP-009는 현재 승인 뒤 새 AI 검토와 사용자 재확인이 필요해 활성화하지 않았다. 사용자 승인 자체를 AI 잠정 라벨이나 미검수로 취급하지 않는다. 신규 AI 검토·사용자 재확인·독립 사람 검수 기록은 생성하지 않았다.

SP-013~017은 추적 설계만 보존했다. 실제 입력 ID 목록과 중복 없음은 확인했지만 정식 배정은 하지 않았고 새 입력·정답을 만들지 않았다. 로컬 문서 링크·diff 공백 및 변경 범위는 커밋 전 별도 검사한다. GitHub CI 결과와 로컬 테스트는 구분하며 PR 메타데이터에서 최종 확인한다. 실제 병합은 하지 않는다.

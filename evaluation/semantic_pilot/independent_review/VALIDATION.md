# 독립 검수 준비 검증 기록 — 관리자용

2026-11-10 실행. 이 문서는 검토자 ZIP에서 제외한다.

| 항목 | 확인 결과 |
| --- | --- |
| main 반영 | PR #18 병합 `d752c4b5c5e73faea8ad552a43f06845c6066f8c`를 PR #17 브랜치에 병합. 충돌 없음 |
| 기존 데이터 보존 | 입력 12·답안 12·manifest·스키마 2, 총 27개 파일이 `289f4e55e89fee04ebe5207fd41f88084443b172`의 Git 바이트와 일치. 사용자 공동 검토·AI 기대 판정·해시 모두 유지 |
| 상태 | 전건 provisional, gold_eligible=false. 기존 사용자 공동 검토 12건 유지. 신규 독립 검토·재정 기록 0건 |
| 기존 파일럿 검사 | `python3 evaluation/semantic_pilot/validate.py` 통과. 기존 manifest 파일 자체는 보존 장부와 이전 Git 버전에 대조. 문서·입력·답안·스냅샷 해시, Git blob, 스키마·근거 참조 검사 |
| 기존 파일럿 테스트 | `python3 -m unittest discover -s evaluation/semantic_pilot -p test_validate.py` — 21건 통과 |
| 패키지 테스트 | `python3 -m unittest discover -s evaluation/semantic_pilot/independent_review -p test_review_package.py` — 9건 통과 |
| main 반영 후 Core 회귀 | `python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'` — 272건 통과. 코드 추가 수정 없음 |
| 변경 범위 | main 대비 Core·승인 정책·기존 fixture·기존 평가 문서의 추가 diff 없음. 이번 추가 산출물은 independent_review 아래에 한정 |
| 패키지 경계 | 정확한 허용 목록 41개 파일, 입력 byte-exact, 12개 빈 양식의 판단 필드 null, 답안·기존 manifest·사용자 의견 제외. answers와 manifest를 제거한 복사본에서도 같은 패키지 생성 |
| 재현성 | 같은 소스로 두 번 생성한 ZIP의 바이트 및 SHA-256 일치 |
| 문서·공백 | 새 문서 상대 링크 및 diff --check 통과 |

생성 ZIP: `dist/independent-review-inputs.zip` (로컬 생성, Git 제외).

SHA-256: `2f52f9ac70c1542e0042f726ae8436627659f505771bd8ff24e2843204aa8728`

검수 패키지는 준비됐지만 실제 사람에게 배포·검수 요청하지 않았다. 양식·참조 검사는 독립 사람 판단·의미 라벨 정확도·외부 사실성·사람 신원을 입증하지 않는다. Core 회귀 통과도 이 파일럿의 골드 확정을 뜻하지 않는다. Antigravity의 문서 조언 요청은 quota 429로 실패했으며 이 작업의 문서는 Codex가 작성·검증했다.

로컬 병합 준비 검증 결과이며 GitHub CI 통과 기록은 아니다. 최종 PR HEAD·GitHub 충돌 상태·CI 유무는 PR 메타데이터에서 별도 확인한다. 실제 병합은 사용자 별도 지시를 기다린다.

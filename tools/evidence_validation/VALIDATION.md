# 검증 결과 — 2026-11-13

기준 main: `879d15b8fa267010217d9310b72d1066fda74f99`. 구현 커밋: `1181c2f`.
이후 문서/로컬 cache ignore만 추가하며 기존 파일은 수정하지 않는다. 원격 병합 결과와 로컬 임시 결합 검증을 구별한다.

## 독립 브랜치

명령: `PYTHONDONTWRITEBYTECODE=1 python3 tools/evidence_validation/run.py --output /tmp/logicwrite-evidence-boundary-main-v2.json`

| 실행 범위 | 테스트 수 | 결과 |
| --- | ---: | --- |
| 고정 Git snapshot의 기존 평가 테스트 18개 묶음 | 244 | PASS |
| 현재 main Core 실험 4개 묶음 | 437 | PASS |
| 현재 Core를 사용하는 기존 소비자 엔진 2개 묶음 | 22 | PASS |
| 새 경계/실행/소비자 테스트 | 16 | PASS |
| 합계 | 719 | PASS, skip 0 |

Core 446개는 PR #33의 9개 회귀가 포함된 수치다. #33이 없는 독립 브랜치에서는 원래 main의 437개를 실행한다. 누락/skip으로 수를 줄인 것이 아니다.

## PR #33 임시 결합

임시 로컬 branch `verify/evidence-boundary-pr33`에서 기준 main에 구현 커밋과 PR #33 head `c919b3bda461594cc5d6ee3bcf603f0a5b03830a`를 합쳤다. source PR 브랜치/워크트리는 수정하지 않았다.

- 임시 결합 commit: `efa725487ea4f48bd2e96cd8c55c9ebce872ccbc`.
- 결합 tree: `5a218acfb86315ad9aa480dac44076ef83432aa3`.
- 명령: `PYTHONDONTWRITEBYTECODE=1 python3 tools/evidence_validation/run.py --output /tmp/logicwrite-evidence-boundary-pr33.json`.
- 결과: **244 역사 평가 + 446 현재 Core + 22 현재 소비자 + 16 새 경계 = 728 tests PASS, skip 0**.
- 이전 실패 7개 역사적 테스트 묶음 72개 전부 실행/통과. 실패 테스트 삭제·skip·xfail·기대값 변경 없음.
- 각 실행에서 기존 증거/fixture **545개 현재 바이트**, 당시 전체 snapshot **616개 바이트**를 Git 객체와 전후 검증.
- 현재 Core 오프라인 진단 29건과 source/candidate 오프라인 예측 29건 생성 후, 원래 비교기로 각각 29건 비교 성공. source의 미실행 의미 검토는 지표 분모에서 제외, Core 진단은 SP 정확도가 아님.
- 전체 source/evidence identity 전후 동일. 결합 tree의 `evaluation/`는 기준 main과 동일.

이는 **새 통합 실행 계층 기준**의 전체 통과이며 실제 원격 병합이나 CI 통과를 뜻하지 않는다. 역사적 validator를 현재 #33 트리에서 직접 실행하면 원래의 snapshot mismatch를 계속 보고한다. 해당 직접 명령은 역사 전용으로 유지하고, 지원 전체 검증 명령을 새 계층으로 전환하는 것이 변경 내용이다.

## 변조/퇴행 검출

| 검증 | 확인 방식 |
| --- | --- |
| 현재 Core 변경 허용 | 임시 current tree의 Core를 변경해도 현재 증거 검증 통과; 실제 #33 결합 전체 검증 통과 |
| 과거 입력·판단·승인 변조 | 원본 복사본의 SP 입력, user-final events, policy-approval bytes를 각각 변경하면 실패 |
| 과거 manifest·검증기·소비자 변조 | preserved-files.json/validate.py/runtime.py의 현재 보관본 변조 실패 |
| 과거 실행 코드·환경 선언·출처 변조 | 역사적 checkout의 reconstruction.py/requirements.txt/manifest 변경 실패; 누락 Git 이력 또는 tree pin 대체 실패 |
| 삭제·경로 대체 | 증거 삭제, 같은 bytes의 symlink 대체도 실패 |
| 현재 Core 구조 결함 | 임시 Core의 bounded_text를 강제로 True로 바꾸면 기존 test_integration의 의미 재작성 보류 테스트가 실제 실패함을 확인 |
| 현재 테스트 오류/빈 실행 | 실제 failing unittest는 nonzero; 0 tests도 실패 처리 |
| 현재 새 평가 코드/자료 변경 | 새 test/helper/input과 현재 Core의 mutation이 실행 지문을 바꾸는지 확인 |
| 입력 바인딩 위조 | 현재 예측의 input SHA를 바꾸면 원래 역사적 비교기가 거부 |

새 기능별 실패 assertion을 확인한 뒤 구현했다. 별도 읽기 전용 리뷰에서 새 평가 파일의 지문 누락 1건을 발견해 재현 후 수정했고, 재리뷰에서 남은 주요 지적 없음 및 새 테스트 16개 PASS를 확인했다.

## 변경 범위와 한계

추가 파일은 `tools/evidence_validation/`의 `boundary.py`, `run.py`, `consumers.py`, `test_boundary.py`, `test_execution.py`, `test_consumers.py`, `.gitignore`, `PLAN.md`, `README.md`, 이 문서다. 기존 source/data/docs/tests/approval 파일은 수정하지 않는다. `git diff --check` 통과.

PR #33과 #34는 원격 Draft/open·동일 head를 유지하며 main은 변경하지 않았다. 새 Draft PR도 사용자 검수 전 병합하지 않는다. 지원 통합 명령을 사용한다는 전제에서 #33의 기존 보존 검증 차단은 해소되었다. 실제 병합 시 최신 head/base 재확인과 같은 명령 재실행이 필요하다.

실패/skip: 지원 통합 검증에서 0. 미실행: 외부 모델/서비스 호출, 원격 CI, 실제 승인 발급/배포, 원격 병합. 호스트는 Python 3.12.3, jsonschema 4.10.3. 당시 exact 환경 lock은 존재하지 않아 완전한 동일 환경 재현이나 의미 품질 향상을 주장하지 않는다. JSON 보고서는 로컬 `/tmp` 산출물이며 증거 원본이나 기존 점수에 반영하지 않았다.

## 순차 통합 전 재검증

2026-11-13, 원격 main `879d15b` 및 PR #37 head `a042823`를 다시 확인한 독립 워크트리에서 실행했다. skip/expected failure를 전체 PASS로 처리하던 문제와 `tests/` 수집 범위를 신규 회귀로 재현하고 수정했다. 저장소 README에 공식 전체 진입점을 추가했고 레거시 `run_checks.py`와 고정 snapshot 검증의 차이를 실행 안내에 명시했다.

`python3 tools/evidence_validation/run.py --output /tmp/logicwrite-pr37-final.json`: **722 tests PASS = 역사 244 + 현재 Core 437 + 현재 소비자 22 + 경계 19**, failures/errors/skip/expected failures/unexpected successes 모두 0. 현재 증거 545파일·역사 snapshot 616파일 검증, 소비자별 29건 비교. 기존 증거/manifest/검증기/승인 정책 수정 없음. 최초 baseline 실행은 검토 중 파일 변경을 지문 검사에서 탐지해 FAIL했으며, 위 결과는 수정이 끝난 트리의 새 전체 실행이다. 원격 Actions workflow 0개로 로컬 결과이며 CI 통과 주장은 하지 않는다.

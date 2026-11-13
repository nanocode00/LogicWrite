# 검증 결과와 한계

2026-11-13. main `879d15b8fa267010217d9310b72d1066fda74f99`에서 분기한 평가 전용 추가다.

| 점검 | 실제 결과 | 근거/재현 |
|---|---|---|
| 입력·답안·검수·전체 예시 | 3건, 정확 인용 26곳, AI 초안/사람 검수 대기/비활성 | `python3 evaluation/integrated_reconstruction/validate.py`, [integrity-summary.json](records/integrity-summary.json) |
| 신규 실패/보존 회귀 | 19 tests OK. 답안 필드 유입, stale 해시, 인용 변조, 근거 누락, 중복 문서, 가짜 승인, 전체 출력 누락/읽기 전용 변경, 서식 권한, 링크, 대안 조건, 사람 응답 보존 검사 | `python3 -m unittest discover -s evaluation/integrated_reconstruction -p 'test_*.py'` |
| 전체 기존+신규 회귀 | **23 suites, 700 tests, 실패 0**, 실행 전후 Python 파일 해시 동일 | [all-tests.json](records/all-tests.json), 기존 `evaluation/core_pipeline_2026_11_11/run_checks.py` 재사용 |
| 활성 v3 회귀 | active_count=29, PRESERVED=12 / VIOLATION=9 / UNRESOLVED=8, 기존 600파일 보존 | 기존 `evaluation/g3_g4/development_gold_v3_active_2026-11-13/validate.py` 실행 |
| 기존 자산 보호 | main 616파일 동일, #34 420개 파일과 #35 문서 1개 고정 객체 확인. 기존 작업 checkout의 #34 420개 파일도 byte 비교 동일 | [preservation.json](records/preservation.json), [보호 기준선](records/protected_baseline.json) |
| 스키마 | 평가 전용 JSON Schema 5개 정의 문법 검사. 입력/정답/검수/예시는 매 실행 실제 검증; submission은 미래 관측 규약이며 이번 모델 실행 데이터 없음 | `jsonschema.Draft202012Validator.check_schema` |
| 답안 누설 경계 | 입력 JSON의 필드 allowlist와 모델 입력만 export하는 회귀 통과. 자연어 입력의 정답 동작 누설은 작성자·별도 AI가 읽고 점검 | 의미적 누설 부재를 자동 증명한 것은 아님 |
| 추적/문서 | 입력 카드의 파일 해시·내장 원문이 JSON과 일치. 문서 상대 링크·후보 출력의 로컬 문서 링크 확인 | 카드/링크 검사 및 패키지 검증; 모든 외부 URL 내용 검증 아님 |
| 별도 AI 패키지 검토 | P2 2개 발견 후 수정·재확인. 근거 없는 대시보드 안내 제거, 서식 공백 검사 강화 | [검토 기록](records/ai-package-review.md), [실패 재현](records/review-regression-red.log) |

처음 테스트는 검증기 미작성으로 import 실패했다([로그](records/initial-missing-validator.log)). 이것을 동작 회귀 실패 재현과 혼동하지 않는다. 서식 검사의 숫자 분리/단어 결합 결함은 실제 2개 테스트 실패→수정 후 성공으로 재현했다.

위 표와 `records/`는 최초 기준 main에서 실행한 역사적 기록이며 덮어쓰지 않는다. 아래 직접 validator/`run_checks.py` 명령도 그 기준 트리의 재현용이다. 현재 공식 전체 실행은 다음 통합 정리 절을 따른다.

최초 기준 트리 보존 재현:

```sh
python3 evaluation/integrated_reconstruction/check_preservation.py
# 기존 PR #34 작업 공간까지 비교하려는 경우:
python3 evaluation/integrated_reconstruction/check_preservation.py --legacy-checkout /path/to/PR34-checkout
python3 evaluation/g3_g4/development_gold_v3_active_2026-11-13/validate.py
python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-integrated-tests.json
```

전체 회귀 기록의 HEAD는 기준 커밋이고 테스트한 추가 Python 파일은 별도 working-tree fingerprint에 결합된다. 기존 검사기에서 생성하는 `__pycache__`는 검증 후 이 작업 공간에서만 정리하며 PR에 포함하지 않는다. PR #34의 도구는 main에 없으므로 새 평가의 런타임 의존성에 넣지 않았다. #34 자체 검증을 이번 700 tests에 포함했다고 주장하지 않는다.

## 발견한 설계 한계와 미실시 항목

정답이 편집 순서/표현 하나를 강제하지 않도록 대안을 두었으나, Q 조건의 필수성·서식/의미 경계·D 사전 제출의 관측 효과는 사람 검수가 필요하다. 3건은 모두 한 합성 작성 군집이고 실자료/독립 출처/실제 AI 초안의 분포를 검증하지 않았다. 관련 자료를 전부 제공하므로 검색 능력 실험이 아니다.

모델 B0/B1/B2 실행·문서 품질 점수·개선 효과·검토 시간·원격 CI 통과·사람 검수·골드 포함 승인·동결·홀드아웃·Core 통합은 **미실시**다. 해시와 스키마는 구조/버전 비교 수단이며 정답의 의미적 타당성이나 사람 신원의 인증이 아니다. 작업은 Draft PR로 검토하며 사람 검수 전 병합하지 않는다.

## 순차 통합 후 검증 경계 보완

PR #37 main `6be0e61` → PR #33 main `af6a793` → PR #35 main `a7a93603026c97e306dced2f36c783c7a2c8ce2d`를 실제 병합 순서대로 반영했다. `records/protected_baseline.json`과 최초 실행 기록은 원본으로 유지한다.

- 이전 `check_preservation.py`는 정상적인 현재 README/Core 변경을 main asset changed로 거부했다. 실패 재현 후 #37의 EvidenceStore를 재사용해 **역사 전체616 Git 객체/snapshot**과 **현재 기존 평가/fixture545파일**을 분리했다. 원래 baseline 자체는 최초 PR #36 Git blob과 대조하므로 재봉인도 거부한다.
- PR #34의 고정420파일·과거 #35 문서1파일을 Git 객체로 계속 확인한다. 현재 #35 문서의 정상 추가는 과거 기록 객체를 대체하지 않는다. `--legacy-checkout`으로 IDE의 실제 #34 checkout420파일도 대조했다.
- 이미 사용된 v1 입력/답안/참고 출력/사람 응답 및 메타데이터21파일은 최초 PR #36 commit `1b0776b`의 객체와 현재 저장본을 비교한다. symlink 대체, 입력·사람 응답 변경, baseline 재봉인, 기존 승인·manifest 변경을 거부한다. 향후 실제 사람 응답은 사본/별도 버전 기록으로 보존하고 원본을 덮어쓰지 않는다.
- v1 스키마와 3개 입력의 바이트·SHA·계보는 바꾸지 않았다. 별도 v2 입력 규약과 4개 회귀를 추가했다. `explicit_constraints=[]`, null 맥락/역할/근거 위상, partial/unknown 문서군, excerpt+source_scope+gaps를 검사한다. 기존 전체 출력 규약의 발췌 입력 실행/자동 Q 채점은 지원하지 않는다.
- 신규 보존 회귀6개 + 기존/입력v2 무결성23개 = **29 tests PASS**, 독립 읽기 전용 리뷰 차단 문제 없음. 기계 검증은 D/Q 기준의 의미 타당성이나 사람 승인 근거가 아니다.

현재 공식 전체 명령과 패키지 검사:

```sh
python3 tools/evidence_validation/run.py --output /tmp/logicwrite-pr36-final.json
python3 evaluation/integrated_reconstruction/validate.py
python3 evaluation/integrated_reconstruction/check_preservation.py --legacy-checkout /home/honorbear/LogicWrite
```

현재 Core·개발 문서는 과거 바이트와 동일할 의무가 없다. 기존 직접 역사 validator와 `run_checks.py`는 최초 snapshot 재현 전용이며 공식 전체 명령을 대신하지 않는다. 검증 실패를 제외/skip하거나 기존 증거를 다시 해시해 해결하지 않았다. 이 PR은 Draft를 유지하며 사람 판단·골드 포함 승인을 작성하지 않는다. IR-001의 현실성·역할 유도·대안/Q 조건 필요성은 DESIGN/REVIEW에 남겼다.

### 최종 전체 실행 결과

실제 최신 main `a7a93603026c97e306dced2f36c783c7a2c8ce2d`: **731 PASS**. 이를 반영한 #36 검증 커밋 `64188cf`: **760 PASS = 역사244 + Core446 + 소비자22 + 경계19 + 신규 평가29**. 공식 실행이 `test_integrity.py`23개와 `test_preservation.py`6개를 각각 현재 단계에서 수집·실행한 것을 보고서로 확인했다. 양쪽 failures/errors/skipped/expected_failures/unexpected_successes 전부0, 증거·코드 실행 전후 지문 동일. 원격 Actions workflow0개이며 위 결과는 로컬 검증이다.

[새 통합 검증 요약](records/integration-validation-2026-11-13.json)에 suite별 실행 수, 검증 revision/코드 지문, 전체 로컬 JSON 경로·SHA, 보존 수량, 원본 입력3건 SHA와 신규 스키마 계보를 남겼다. 원래 records는 수정하지 않았다. 이후 추가한 파일은 이 요약/설명뿐이며 테스트한 코드·입력·답안·사람 응답은 같다. 최종 `git diff --check` 및 별도 보존 검사도 통과했다.

사람은 기존 입력3건의 설계 검수를 시작할 수 있다. 현실적 난도·목적 복구·Q 필수성은 미확정이며 이 검증으로 정답을 확정하지 않는다. PR #34의57건은 그대로 Draft/보존, #36도 Draft다. 실제 모델 성능·골드 승인은 미실시다.

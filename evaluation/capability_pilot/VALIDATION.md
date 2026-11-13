# 검증 결과 — 개발 후보 준비

기준 `origin/main = 879d15b8fa267010217d9310b72d1066fda74f99`에서 구현했다.
PR #32는 사용자가 허용한 범위로 병합했다. 후속 PR은 Draft이며 자동 병합하지 않는다.

| 검증 | 실제 결과 | 증거 |
|---|---|---|
| 평가 자료 무결성 | 57건, 캘리브레이션 9건, 전 유형 최소 6건, 공개 원문 36개, 현재 입력 연결 독립 AI 검토 57건 | [요약](records/integrity-summary.json), `python3 evaluation/capability_pilot/validate.py` |
| 기존 Core 기준선 | 362 tests OK | 동일 세션에서 `python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'` 실행 |
| 전체 회귀 | **23개 suite, 702 tests, 실패 0**; Python 입력 전후 불변 | [전체 명령·출력·파일 해시](records/all-tests.json) |
| 신규 무결성 회귀 | 21 tests 포함: 노출·해시·가짜 승인·근거·범위·분모·raw review·이전 입력·응답 보존 | `test_integrity.py`; 전체 회귀의 capability_pilot suite |
| 기존 자산 보존 | main 추적 616개 파일 SHA-256 동일 | [protected_baseline.json](protected_baseline.json), 검증기가 현재 파일과 비교 |
| 출처/라이선스 | 36개 canonical 저장소, fork 0; README/라이선스/고지의 고정 commit URL·Git blob·SHA 일치 | [source_identity.json](source_identity.json), [sources.json](sources.json), [NOTICE.md](NOTICE.md) |
| 독립 AI 반례 | 최초 57건 + 수정 입력 9건 재검토, 총 66개 사례 검토 레코드; 구현 검토는 별도 | [raw_reviews/](raw_reviews/), [ai_reconciliation.json](ai_reconciliation.json) |
| 사람/승인/활성화 | 독립 사람 0, 최종 사람 판단 0, 포함 승인 0, 신규 활성화 0, 홀드아웃 0 | 각 review의 별도 null 필드, [응답 양식](human_responses.json) |

전체 회귀 재현:

```bash
python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-all-tests.json
```

모듈명 충돌이 있는 기존 suite를 별도 Python 프로세스로 실행하는 기존 도구를 재사용했다.
보고서의 HEAD는 테스트 당시 기준 커밋이며, 당시 미커밋 구현은 Python 파일별 해시와
실행 전후 fingerprint에 연결되어 있다. 원격 CI 통과나 모델 성능 결과를 뜻하지 않는다.

신규 검증기 결함은 [최초 RED](records/lw-red.log)→GREEN,
[중복 ID/부실 AI 리뷰/응답 양식 RED](records/lw-review-red.log)→
[GREEN](records/lw-review-green.log),
[이전 입력 변조 RED](records/lw-history-red.log)→
[GREEN](records/lw-history-green.log)으로 재현·수정했다.
raw review가 독립 검토라고 선언하는 스키마는 외부 인증 수단이 아니다.
실제 검토는 답안 초안을 받지 않은 별도 Codex 컨텍스트에서 수행했고 원문을 보존했다.

작성한 코드/스키마/장부의 whitespace 검사를 통과했다. 공개 원문 및 그대로 인용한
입력/답안 카드는 원문 byte 보존을 위해 upstream trailing whitespace를 고치지 않았다.

이는 구조·계보·해시·반례 준비의 검증이다. D/Q의 모든 의미적 모순을 자동으로
검출했다거나 정답·라이선스·독립성에 사람 검수가 끝났다는 주장이 아니다.
실제 upstream 편집 전후 검증 사례는 0건이며, 공개 원문 기반 과업과 통제 편집이다.
가족/공유 목적지 템플릿 상관과 문서 종류 편중은 [커버리지 공백](COVERAGE.md)에 남겼다.

# 전체 편집 능력 개발 파일럿 — 검수 준비본

기준: PR #32가 병합된 `879d15b`. [설계](../../docs/golden-set-expansion-design.md)를
평가 전용 자료로 구체화했다. **57건 전부 provisional**이다. T1/T3~T8 각 6건,
T2 7건, T9 8건이며 캘리브레이션 9건은 이 57건의 부분집합이다.
기존 활성 v3 29건·정답·승인 이력·Core·평가 정책·소비자는 바꾸지 않았다.

시작점은 [사용자 일괄 검수](BATCH_REVIEW.md)다. 먼저 입력 카드만 보고 판단한 뒤
AI 답안/반례를 열고 [응답 양식](human_responses.json)을 사본으로 작성한다.
최초 판단·독립 사람 반례·최종 판단·이견 조정·골드 포함 승인은 서로 다른 필드다.
신원·사유·시각·서명·승인을 AI가 채우지 않았다. 독립 사람 검수는 0명이다.

| 자료 | 역할 |
|---|---|
| [input.schema.json](input.schema.json), inputs/ | 목적·독자·계약·전체 원문·목적지·근거·편집 범위. 모델에는 이 파일만 전달 |
| [answer.schema.json](answer.schema.json), answers/ | 별도 D 의무/판단/금지/완전 대안 묶음/보류 및 Q 보호 사실·과업·5축 0–3 앵커. AI 초안 |
| [review.schema.json](review.schema.json), reviews/ | 최초 AI 제안과 독립 AI 원문 연결. 사람 최초 판단·반례·최종 판단·중재·포함 승인은 비어 있음 |
| [human_response.schema.json](human_response.schema.json), [human_responses.json](human_responses.json) | 사람이 작성하는 일괄 검수 응답. 현재 양식은 텍스트 또는 null. 실제 공급되지 않은 시각/신원을 만들지 않음 |
| [raw_review.schema.json](raw_review.schema.json), raw_reviews/ | 입력만 본 독립 Codex 검토 원문과 별도 구현 검토. 독립 AI는 사람 검수자로 세지 않음 |
| [cases.json](cases.json), [COVERAGE.md](COVERAGE.md), [coverage.csv](coverage.csv) | 주유형/부유형(미사용 빈 배열)·하위 상황·난도·위험·문서 유형·언어·길이·split·노출·가족·상태 장부 |
| [sources.json](sources.json), sources/, [NOTICE.md](NOTICE.md) | 공개 원문·라이선스·고지의 고정 commit/Git blob/SHA-256·저작권/재배포 범위 |
| [revision_log.json](revision_log.json), reviewed_inputs/, [ai_reconciliation.json](ai_reconciliation.json) | 수정 전 입력과 최초/재검토 계보. 조정 제안의 작성자는 AI이며 사람 중재는 null |
| [CALIBRATION.md](CALIBRATION.md), [legacy_reuse_audit.json](legacy_reuse_audit.json) | 9건 양식/경계 점검, 기존 RW20/LW12 재사용 적합성 전수 조사. 기존 정답은 승격/복사하지 않음 |
| [lineage_overlap.json](lineage_overlap.json), [near_duplicates.json](near_duplicates.json), [template_overlap.json](template_overlap.json), [holdout_registry.json](holdout_registry.json) | 기존 개발 자료와 가족/문구 비교. 홀드아웃은 0건, 수집하지 않음 |
| [validate.py](validate.py), [test_integrity.py](test_integrity.py), [protected_baseline.json](protected_baseline.json) | 읽기 전용 구조·해시·범위·인용·계보·분모·승인 경계와 기존 추적 616파일 보존 확인 |
| [VALIDATION.md](VALIDATION.md), records/ | 실제 실행 명령/회귀 결과. 기계 점검과 의미/사람 검수를 구별 |

```bash
# 기존 semantic_pilot과 동일한 jsonschema>=4.10.3,<5 환경
python3 evaluation/capability_pilot/validate.py
python3 -m unittest discover -s evaluation/capability_pilot -p 'test_*.py'
python3 evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-all-tests.json
```

검증기는 어떤 파일도 쓰지 않는다. 잘못된 응답/자료가 있어도 기존 응답을 보존한다.
양식 작성 결과를 review 레코드·활성 상태로 자동 반영하는 도구는 만들지 않았다.
검수 결과를 반영하려면 후속 검토에서 정확한 사람 원문과 입력 버전을 연결해야 한다.
현재 review 스키마는 의도적으로 provisional/null 경계를 고정한다.

## 평가 해석과 제한

D는 편집 전에 외부로 제출해 고정한 `native_trace`/`declared_plan`만 평가하며
사고과정을 추정하지 않는다. 자연 실행에서 판단 근거가 없으면 미관측이다.
`output_effect`는 보조 통계다. Q는 실제 전체 출력이 있어야 평가한다.
원문이 충분하나 결과만 절단된 T9-06은 D 사실 보류 적중이 아니며 Q 미평가다.
B0-D/B1-D/B2-D의 공통 제출과 자연 실행 Q 비교를 혼합하지 않는다.

지표는 필수 판단 recall·금지 결과 수·제안 근거 precision·정답 보류와 과잉 보류를
별도 기록한다. 고정 R/F ID는 검수 단위이며 서로 다른 표현의 문자열 정답이 아니다.
대안은 의무 전체를 만족하는 완전 묶음이다. 목록 밖 유효 답은 재심한다.
Q는 정보 보존·목적 적합성·완결성·배치·표현을 각각 평정하고 중대 정보 오류는
별도 남긴다. D/Q 평균이나 자동 의미 채점기는 구현하지 않았다.
분모 0은 N/A이며 무응답·실행 실패·부분 출력은 완료율/미평가로 따로 공개한다.

36개 공개 원문에 평가 과업을 부여했고 일부는 통제 편집했다. **실제 upstream의
성공적 편집 전후를 검증한 사례는 아니다.** 추가 21건은 명시적 통제 합성이다.
OpenJS의 Express/Lodash는 한 가족으로 보수적으로 묶고 합성 전체도 한 군집으로
집계했다. 따라서 57건을 독립 표본 56개로 해석하지 않는다. 가족 독립성 분류는
사람 검토 전 임시 장부이며 상관/공유 템플릿을 완전히 배제했다는 보장이 아니다.
공개 실제 자료는 영문 기술 README에 편중됐으며 합성 다양성이 이를 대체하지 않는다.

P1/P2의 검수 준비 자산을 확보한 상태다. 두 독립 사람·중재·포함 승인·P3 동결·
미공개 홀드아웃·모델 성능 실험은 미완료다. 후속 PR은 자동 병합하지 않는다.

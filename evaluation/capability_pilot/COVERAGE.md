# 하위 상황·출처 커버리지

57건은 과제 수다. 캘리브레이션 9건은 부분집합이다. 공개 원문 36개는 서로 다른 프로젝트 README이며, Express/Lodash는 OpenJS 공통 계열로 보수적으로 묶었다. 공개 35가족 + 합성 작성 배치 1군 = 36개 상관 군집이다. 합성 21건은 한 군집이며 독립 표본 21개가 아니다. 가족 독립성은 임시 분류로 추가 사람 검토가 필요하다.

| 유형 | 과제 | 단순 / 복합 | 고위험 | 하위 상황 | 공개 원문 | 가족 군집 |
|---|---:|---|---:|---|---:|---:|
| T1 | 6 | 1 / 5 | 2 | 5/5 초안 근거 있음 | 4 | 5 |
| T2 | 7 | 1 / 6 | 4 | 5/5 초안 근거 있음 | 4 | 5 |
| T3 | 6 | 3 / 3 | 2 | 5/5 초안 근거 있음 | 4 | 5 |
| T4 | 6 | 1 / 5 | 2 | 5/5 초안 근거 있음 | 4 | 5 |
| T5 | 6 | 2 / 4 | 2 | 5/5 초안 근거 있음 | 4 | 5 |
| T6 | 6 | 2 / 4 | 2 | 5/5 초안 근거 있음 | 4 | 5 |
| T7 | 6 | 3 / 3 | 3 | 5/5 초안 근거 있음 | 4 | 5 |
| T8 | 6 | 4 / 2 | 1 | 6/6 초안 근거 있음 | 4 | 5 |
| T9 | 8 | 1 / 7 | 3 | 6/6 초안 근거 있음 | 4 | 5 |

[coverage.csv](coverage.csv)는 유형×하위 상황×난도×위험×가족×split의 실제 건수와 근거 ID/정답 포인터를 제공한다. 모든 조합의 완전 커버를 뜻하지 않는다.

## 하위 상황별 추적

| 유형 | 하위 상황 | 사례 |
|---|---|---|
| T1 | facts_conditions | CP-T1-01, CP-T1-02, CP-T1-03, CP-T1-05 |
| T1 | cross_paragraph | CP-T1-01, CP-T1-02, CP-T1-04, CP-T1-05 |
| T1 | true_conflict | CP-T1-03 |
| T1 | scope_time_attribution | CP-T1-04, CP-T1-05 |
| T1 | unclear_authority | CP-T1-06 |
| T2 | selection | CP-T2-01, CP-T2-02, CP-T2-04, CP-T2-05, CP-T2-07 |
| T2 | audience_purpose | CP-T2-01, CP-T2-02, CP-T2-05 |
| T2 | local_exposure | CP-T2-03, CP-T2-05, CP-T2-07 |
| T2 | long_required | CP-T2-03, CP-T2-04, CP-T2-05 |
| T2 | purpose_conflict | CP-T2-06 |
| T3 | empty_information | CP-T3-01, CP-T3-03 |
| T3 | partial_removal | CP-T3-02, CP-T3-05 |
| T3 | equivalent_retained | CP-T3-03, CP-T3-05 |
| T3 | unique_value_protected | CP-T3-02, CP-T3-04, CP-T3-05, CP-T3-06 |
| T3 | unclear_retention | CP-T3-06 |
| T4 | known_destination | CP-T4-01, CP-T4-02, CP-T4-03, CP-T4-05 |
| T4 | multiple_destinations | CP-T4-02 |
| T4 | local_summary_link | CP-T4-01, CP-T4-02, CP-T4-03, CP-T4-05 |
| T4 | destination_integrity | CP-T4-04, CP-T4-05 |
| T4 | missing_destination_scope | CP-T4-06 |
| T5 | prerequisite_order | CP-T5-01, CP-T5-05 |
| T5 | grouping | CP-T5-02, CP-T5-03, CP-T5-05 |
| T5 | multiple_orders | CP-T5-02, CP-T5-03, CP-T5-04, CP-T5-05 |
| T5 | keep_placement | CP-T5-04 |
| T5 | missing_anchor | CP-T5-06 |
| T6 | exact_duplicate | CP-T6-01 |
| T6 | partial_unique | CP-T6-02, CP-T6-05 |
| T6 | different_scope_time_attribution | CP-T6-03, CP-T6-05 |
| T6 | necessary_repetition | CP-T6-04, CP-T6-05 |
| T6 | unknown_equivalence | CP-T6-06 |
| T7 | required_missing | CP-T7-01, CP-T7-02, CP-T7-05 |
| T7 | partial_missing_location | CP-T7-01, CP-T7-02 |
| T7 | already_satisfied | CP-T7-03, CP-T7-04 |
| T7 | authority_conflict | CP-T7-05 |
| T7 | unsupported_requirement | CP-T7-06 |
| T8 | style_terms | CP-T8-01, CP-T8-05 |
| T8 | referent_clarity | CP-T8-02, CP-T8-03 |
| T8 | compression | CP-T8-01, CP-T8-03, CP-T8-05 |
| T8 | protected_code_quote_id | CP-T8-01, CP-T8-02, CP-T8-04, CP-T8-05 |
| T8 | optional_noop | CP-T8-04, CP-T8-05 |
| T8 | missing_context | CP-T8-06 |
| T9 | whole_task | CP-T9-01, CP-T9-02, CP-T9-03, CP-T9-04, CP-T9-05, CP-T9-07 |
| T9 | preserved_but_unfit | CP-T9-02, CP-T9-05 |
| T9 | roles_consistency | CP-T9-01, CP-T9-03, CP-T9-05, CP-T9-08 |
| T9 | multiple_whole_outputs | CP-T9-01, CP-T9-02, CP-T9-04, CP-T9-05, CP-T9-07 |
| T9 | global_regression | CP-T9-03, CP-T9-04, CP-T9-05 |
| T9 | partial_or_unclear_task | CP-T9-06, CP-T9-08 |

## 남은 공백

- 공개 실제 출처 36건이지만 검증된 upstream 실제 편집 전후 사례는 0건이다. 과업·통제 편집은 AI가 작성했다. 자연 발생 편집과의 외적 타당성은 미검증이다.
- 공개 자료는 영문 기술 README에 편중됐다. 한국어·회의록·정책·감사 보고·운영 카드·표·인용은 합성 보완이며 실제 공개 문서 다양성을 대체하지 않는다.
- T1/T4/T6/T9의 단순 또는 고위험 일부는 합성 1군에 의존한다. 모든 하위 상황의 두 독립 가족 조건(P3)은 충족하지 않는다.
- 독립 사람 2명·중재·동결·골드 포함 승인·미공개 홀드아웃은 모두 미완료다. 현재는 검수 준비된 개발 후보이며 P2 인간 검수 통과/정식 골드 완료가 아니다.
- 기존 개발 가족과 겹치는 pallets, encode, psf를 장부에 표시했다. 다른 README라도 기존 가족의 홀드아웃으로 배치하지 않는다.
- 신규 모델 성능 실행/점수 없음. D 미관측·Q 미완료·분모0 N/A를 구분하는 계약과 구조만 검증했다.

## 편집 결과 경계별 준비 상태

| 유형 | 변경/판단 | 무수정 | 복수 대안 | 부당 편집 반례 | 진짜 D 보류 |
|---|---:|---:|---:|---:|---:|
| T1 | 5 | 1 | 6 | 6 | 1 |
| T2 | 6 | 2 | 7 | 7 | 1 |
| T3 | 5 | 1 | 6 | 6 | 1 |
| T4 | 5 | 1 | 6 | 6 | 1 |
| T5 | 5 | 1 | 6 | 6 | 1 |
| T6 | 5 | 1 | 6 | 6 | 1 |
| T7 | 4 | 2 | 6 | 6 | 2 |
| T8 | 5 | 1 | 6 | 6 | 1 |
| T9 | 7 | 2 | 8 | 8 | 1 |

T9-06의 Q 절단 미평가는 진짜 D 보류 수에 넣지 않는다. T9-08은 원문이 완전해도 계약이 미정인 진짜 D 보류다. [template_overlap.json](template_overlap.json)은 여러 공개 가족에 재사용된 통제 목적지 뼈대와 합성 공통 작성 배치를 표시한다. 출처 가족 수를 과제의 통계적 독립성으로 해석하지 않는다.

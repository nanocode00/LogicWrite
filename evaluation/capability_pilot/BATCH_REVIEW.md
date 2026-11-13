# 사용자 일괄 검수 패키지

현재 57건은 모두 provisional 개발 후보입니다. 아래 순서로 한 번에 검토할 수 있습니다. 독립 사람 검수 0명, 사용자 최종 판단·골드 포함 승인 0건입니다.

1. 먼저 **입력 카드만** 읽고 [human_responses.json](human_responses.json)의 initial_judgment/initial_evidence를 기록합니다. 원본 대신 사본을 저장해도 됩니다.
2. 독립 사람 두 번째 평가자는 첫 판단과 AI 답안을 보기 전에 같은 입력에서 반례를 작성합니다. 확보되지 않았다면 빈칸을 유지합니다.
3. 그 뒤 AI 제안 카드를 열어 최초 판단·독립 AI 반례·D/Q 초안·금지 결과·복수 대안을 비교합니다.
4. final_judgment와 disagreement_resolution을 직접 기록합니다. **gold_inclusion_approval은 별도 선택**이며 최종 판단 동의와 자동 연결하지 않습니다. 신원·시각·사유는 실제 제공한 값만 기록합니다.
5. 새 타당한 대안은 재심 대상으로 남깁니다. 이번 패키지의 코드는 응답을 읽기만 하며 활성 골드로 승격하지 않습니다.

검수 항목: 입력/권한 충분성, 근거 정합성, D의 필수·선택·금지·복수 대안·보류, Q의 보존·목적·완결·배치·표현, 위험·하위 상황 분류, 포함/제외/추가 자료 요청. 전체 후보를 일괄 제출해 주세요.

| 사례 | 입력 먼저 | 이후 AI 제안·독립 반례 | 캘리브레이션 |
|---|---|---|---|
| CP-T1-01 | [입력](input_cards/CP-T1-01.md) | [AI 제안](answer_cards/CP-T1-01.md) | 예 |
| CP-T1-02 | [입력](input_cards/CP-T1-02.md) | [AI 제안](answer_cards/CP-T1-02.md) |  |
| CP-T1-03 | [입력](input_cards/CP-T1-03.md) | [AI 제안](answer_cards/CP-T1-03.md) |  |
| CP-T1-04 | [입력](input_cards/CP-T1-04.md) | [AI 제안](answer_cards/CP-T1-04.md) |  |
| CP-T1-05 | [입력](input_cards/CP-T1-05.md) | [AI 제안](answer_cards/CP-T1-05.md) |  |
| CP-T1-06 | [입력](input_cards/CP-T1-06.md) | [AI 제안](answer_cards/CP-T1-06.md) |  |
| CP-T2-01 | [입력](input_cards/CP-T2-01.md) | [AI 제안](answer_cards/CP-T2-01.md) | 예 |
| CP-T2-02 | [입력](input_cards/CP-T2-02.md) | [AI 제안](answer_cards/CP-T2-02.md) |  |
| CP-T2-03 | [입력](input_cards/CP-T2-03.md) | [AI 제안](answer_cards/CP-T2-03.md) |  |
| CP-T2-04 | [입력](input_cards/CP-T2-04.md) | [AI 제안](answer_cards/CP-T2-04.md) |  |
| CP-T2-05 | [입력](input_cards/CP-T2-05.md) | [AI 제안](answer_cards/CP-T2-05.md) |  |
| CP-T2-06 | [입력](input_cards/CP-T2-06.md) | [AI 제안](answer_cards/CP-T2-06.md) |  |
| CP-T2-07 | [입력](input_cards/CP-T2-07.md) | [AI 제안](answer_cards/CP-T2-07.md) |  |
| CP-T3-01 | [입력](input_cards/CP-T3-01.md) | [AI 제안](answer_cards/CP-T3-01.md) | 예 |
| CP-T3-02 | [입력](input_cards/CP-T3-02.md) | [AI 제안](answer_cards/CP-T3-02.md) |  |
| CP-T3-03 | [입력](input_cards/CP-T3-03.md) | [AI 제안](answer_cards/CP-T3-03.md) |  |
| CP-T3-04 | [입력](input_cards/CP-T3-04.md) | [AI 제안](answer_cards/CP-T3-04.md) |  |
| CP-T3-05 | [입력](input_cards/CP-T3-05.md) | [AI 제안](answer_cards/CP-T3-05.md) |  |
| CP-T3-06 | [입력](input_cards/CP-T3-06.md) | [AI 제안](answer_cards/CP-T3-06.md) |  |
| CP-T4-01 | [입력](input_cards/CP-T4-01.md) | [AI 제안](answer_cards/CP-T4-01.md) | 예 |
| CP-T4-02 | [입력](input_cards/CP-T4-02.md) | [AI 제안](answer_cards/CP-T4-02.md) |  |
| CP-T4-03 | [입력](input_cards/CP-T4-03.md) | [AI 제안](answer_cards/CP-T4-03.md) |  |
| CP-T4-04 | [입력](input_cards/CP-T4-04.md) | [AI 제안](answer_cards/CP-T4-04.md) |  |
| CP-T4-05 | [입력](input_cards/CP-T4-05.md) | [AI 제안](answer_cards/CP-T4-05.md) |  |
| CP-T4-06 | [입력](input_cards/CP-T4-06.md) | [AI 제안](answer_cards/CP-T4-06.md) |  |
| CP-T5-01 | [입력](input_cards/CP-T5-01.md) | [AI 제안](answer_cards/CP-T5-01.md) | 예 |
| CP-T5-02 | [입력](input_cards/CP-T5-02.md) | [AI 제안](answer_cards/CP-T5-02.md) |  |
| CP-T5-03 | [입력](input_cards/CP-T5-03.md) | [AI 제안](answer_cards/CP-T5-03.md) |  |
| CP-T5-04 | [입력](input_cards/CP-T5-04.md) | [AI 제안](answer_cards/CP-T5-04.md) |  |
| CP-T5-05 | [입력](input_cards/CP-T5-05.md) | [AI 제안](answer_cards/CP-T5-05.md) |  |
| CP-T5-06 | [입력](input_cards/CP-T5-06.md) | [AI 제안](answer_cards/CP-T5-06.md) |  |
| CP-T6-01 | [입력](input_cards/CP-T6-01.md) | [AI 제안](answer_cards/CP-T6-01.md) | 예 |
| CP-T6-02 | [입력](input_cards/CP-T6-02.md) | [AI 제안](answer_cards/CP-T6-02.md) |  |
| CP-T6-03 | [입력](input_cards/CP-T6-03.md) | [AI 제안](answer_cards/CP-T6-03.md) |  |
| CP-T6-04 | [입력](input_cards/CP-T6-04.md) | [AI 제안](answer_cards/CP-T6-04.md) |  |
| CP-T6-05 | [입력](input_cards/CP-T6-05.md) | [AI 제안](answer_cards/CP-T6-05.md) |  |
| CP-T6-06 | [입력](input_cards/CP-T6-06.md) | [AI 제안](answer_cards/CP-T6-06.md) |  |
| CP-T7-01 | [입력](input_cards/CP-T7-01.md) | [AI 제안](answer_cards/CP-T7-01.md) | 예 |
| CP-T7-02 | [입력](input_cards/CP-T7-02.md) | [AI 제안](answer_cards/CP-T7-02.md) |  |
| CP-T7-03 | [입력](input_cards/CP-T7-03.md) | [AI 제안](answer_cards/CP-T7-03.md) |  |
| CP-T7-04 | [입력](input_cards/CP-T7-04.md) | [AI 제안](answer_cards/CP-T7-04.md) |  |
| CP-T7-05 | [입력](input_cards/CP-T7-05.md) | [AI 제안](answer_cards/CP-T7-05.md) |  |
| CP-T7-06 | [입력](input_cards/CP-T7-06.md) | [AI 제안](answer_cards/CP-T7-06.md) |  |
| CP-T8-01 | [입력](input_cards/CP-T8-01.md) | [AI 제안](answer_cards/CP-T8-01.md) | 예 |
| CP-T8-02 | [입력](input_cards/CP-T8-02.md) | [AI 제안](answer_cards/CP-T8-02.md) |  |
| CP-T8-03 | [입력](input_cards/CP-T8-03.md) | [AI 제안](answer_cards/CP-T8-03.md) |  |
| CP-T8-04 | [입력](input_cards/CP-T8-04.md) | [AI 제안](answer_cards/CP-T8-04.md) |  |
| CP-T8-05 | [입력](input_cards/CP-T8-05.md) | [AI 제안](answer_cards/CP-T8-05.md) |  |
| CP-T8-06 | [입력](input_cards/CP-T8-06.md) | [AI 제안](answer_cards/CP-T8-06.md) |  |
| CP-T9-01 | [입력](input_cards/CP-T9-01.md) | [AI 제안](answer_cards/CP-T9-01.md) | 예 |
| CP-T9-02 | [입력](input_cards/CP-T9-02.md) | [AI 제안](answer_cards/CP-T9-02.md) |  |
| CP-T9-03 | [입력](input_cards/CP-T9-03.md) | [AI 제안](answer_cards/CP-T9-03.md) |  |
| CP-T9-04 | [입력](input_cards/CP-T9-04.md) | [AI 제안](answer_cards/CP-T9-04.md) |  |
| CP-T9-05 | [입력](input_cards/CP-T9-05.md) | [AI 제안](answer_cards/CP-T9-05.md) |  |
| CP-T9-06 | [입력](input_cards/CP-T9-06.md) | [AI 제안](answer_cards/CP-T9-06.md) |  |
| CP-T9-07 | [입력](input_cards/CP-T9-07.md) | [AI 제안](answer_cards/CP-T9-07.md) |  |
| CP-T9-08 | [입력](input_cards/CP-T9-08.md) | [AI 제안](answer_cards/CP-T9-08.md) |  |

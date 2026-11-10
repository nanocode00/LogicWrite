# 검수 절차 v1 — 단일 사용자 + AI 반례 검토

이 절차는 **개발용 골드**의 선택 가능한 검수 방식이다. 독립된 복수 사람 검토와 별도 재정은 상위 검수 방식으로 유지한다. AI 반례 검토는 사람 검토자 수에 포함하지 않는다. 기존 12건을 최종 확정하거나 독립 홀드아웃으로 바꾸지 않는다.

## 기존 파일 보존과 새 기록

기존 입력·답안·manifest·스키마 27개 파일과 사용자 공동 검토는 수정하지 않는다. AI 기대 판정 4/4/4, 사용자 의견 3/4/5, SP-003의 차이와 비노출 여부를 그대로 둔다. 기존 `gold_eligible` 및 검증기의 의미도 그대로다. 새 기록은 이 디렉터리의 `record.schema.json`에 맞는 **별도 JSON 스냅샷**으로 작성한다. 데이터 바인딩은 입력 JSON 파일 SHA-256과 기존 답안 파일 전체 SHA-256이다. 후자는 기존 AI 제안과 함께 사용자 공동 검토도 포함한 파일의 해시이지, 그 사람 기록을 AI 판정으로 분류하는 필드가 아니다.

단일 사용자 최종 확정은 새 기록의 검증 결과인 `development_gold_eligible`로만 표시한다. 이를 기존 `gold_eligible: true`로 변환하거나 기존 manifest에 덮어쓰지 않는다. 상태와 적격 필드는 사람이 임의로 작성하는 값이 아니라 증거 기록에서 도구가 계산한다. 기존 독립 검수 도구는 계속 사용할 수 있다.

## 검수 수준

| 검수 수준 | 필요한 기록 | 개발용 골드 적격 | 독립 복수 검수·재정 완료 |
| --- | --- | --- | --- |
| `ai_provisional` | 기존 AI 제안에 해시로 연결, 새 검수 이벤트 없음 | false | false |
| `user_initial_reviewed` | 사용자 최초 판단·근거·AI/이전 답안 노출 여부, 사용자 확인 | false | false |
| `ai_counterreview_completed` | 별도 AI 검토의 모델·참조한 사용자 판단·반례/누락 조건/모순 검토·근거 | false | false |
| `user_final_confirmed` | 모든 반론에 대한 사용자 응답, 최종 판단·근거·미해결 사항·한계, 실제 사용자 확인 | 사용자 명시 승인과 검증 충족 시에만 true | false |
| `reopened` | 사용자 재검토 요청과 사유, 이전 최종 판단 이력 보존 | false | false |
| `independent_multi_human_reviewed` | 기존 엄격 규칙을 통과한 서로 다른 비노출 사람 검토 2건 이상 | false | false |
| `independent_multi_human_adjudicated` | 위 검토와 다른 사람의 재정, 의견 차이 해결 근거 | 기존 포함 승인 `gold_eligible`에 따름 | true |

같은 판정 문자열이라도 검수 수준과 방법을 함께 보고한다. 개발용 골드를 평가에 사용하면 단일 사람 판단과 AI 보조의 상관성·편향 한계를 명시한다. `user_final_confirmed` 자체는 무조건 적격이라는 뜻이 아니다. 사용자가 포함을 승인하지 않으면 false다. 이 절차는 Core `PASS/REVIEW/FAIL`, 실행·파일 반영 승인과 연결하지 않는다.

## 진행 순서

1. 기존 입력 전용 ZIP과 [빈 양식](../independent_review/review-form.schema.json)을 사용한다. 먼저 원문·수정 결과·계약을 검토한 실제 사용자가 최초 판단을 작성한다. AI 답안을 봐도 이 방식은 가능하지만 `blinded_to_prior_judgments: false`로 사실대로 남긴다. 기존 공동 검토를 true로 소급하지 않는다. 과거 의견을 재사용할 경우 원래 기록·노출 조건을 보존하고 사용자가 현재 입력에서 다시 확인해야 한다. 도구는 기존 의견을 자동으로 새 사용자 이벤트로 가져오지 않는다.
2. `user_initial` 이벤트에 사람이 작성한 submitted 양식과 실제 확인을 기록한다. AI 제안 노출은 `ai_proposal_exposure: seen/not_seen/unknown`으로 별도 기록하고, 양식의 전체 이전 판정 비노출 여부와 모순되지 않아야 한다. 빈 양식은 초기화 자료이며 검토 완료가 아니다. AI가 사용자 역할의 판단·확인·시점을 채우지 않는다.
3. 최초 제안 작성과 분리된 AI 검토 호출/세션에 입력, 원래 제안, 사용자 최초 판단을 제공한다. AI가 반례, 빠진 필수 조건, 문서 간 모순 가능성을 찾고 각각 근거를 제시한다. 모델 식별자·실제 검토 시각·별도 검토 여부와 검토 범위를 `ai_counterreview`에 기록한다. 같은 모델이어도 별도 호출은 가능하지만 독립 사람 검수로 보지 않는다. 반론이 없다면 제공 범위에서 무엇을 검토했는지 이유를 남긴다. 형식적인 빈 배열만으로 완료할 수 없다.
4. 사용자가 반론별로 `accept/reject/defer`와 이유를 직접 기록하고 최종 판단·원문/후보 근거·미해결 사항·신뢰도 한계를 `user_final`에 작성한다. AI는 반론을 제시할 뿐 사용자 응답·최종 확정을 대신 작성하지 않는다. 현재 검토한 반론 이벤트 ID에 연결하며, 반론 ID 누락·중복·조용한 제외를 금지한다.
5. 사용자가 개발용 골드 포함 여부를 명시한다. defer가 있으면 적격 false다. 해결되지 않은 쟁점이 있는데 정상/위반으로 확정한 상태는 적격으로 삼지 않는다. 충분한 검토 후 ‘자료 부족이므로 보류해야 함’ 자체를 확정한 경우, 사용자가 이유와 부족 자료를 명시하고 모든 반론에 답했다면 UNRESOLVED 라벨을 개발용 보류 평가에 포함할 수 있다. 판단 보류와 미검수는 다르다.
6. 어려운 사례를 나중에 검토할 때 `reopen` 사유를 남기고 새 최초 판단→AI 검토→사용자 확정으로 진행한다. 재개 즉시 이전 개발용 골드 적격을 해제한다. 새 정보로 판단이 바뀌어도 과거 이벤트·판정·근거를 수정하지 않는다. 실제 입력/계약이 바뀌면 새 사례 ID/데이터 버전·해시를 만들고 새 기록을 사용한다. 현재 12건 원문을 덮어쓰지 않는다.

각 이벤트의 actor와 `human_confirmed`는 작성자 진술이다. 구조 검사가 사람 신원·실제 확인·별도 AI 호출 여부를 인증하는 것은 아니다. `confidence_limits`는 단일 사람·AI 보조·개발용이라는 한계를 항상 표시한다. 타임스탬프는 실제 시간대 포함 시각을 사람이 기록하며 추정해서 채우지 않는다.

## 도구와 기록 양식

저장소 루트에서 기존 Python/jsonschema 환경을 사용한다. 다음 init은 판단 없는 메타데이터만 생성하며 기존 사람 의견을 자동 복사하지 않는다. 실제 작업 파일은 기본 Git 제외 경로 `work/` 또는 별도 검수 저장 위치에서 작성한다. 완료된 사람이 작성한 기록은 별도 검토 후 명시적으로 버전 관리한다.

```bash
mkdir -p evaluation/semantic_pilot/user_review_v1/work
python3 evaluation/semantic_pilot/user_review_v1/workflow.py init SP-003 --output evaluation/semantic_pilot/user_review_v1/work/003-r00.json
python3 evaluation/semantic_pilot/user_review_v1/workflow.py append evaluation/semantic_pilot/user_review_v1/work/003-r00.json --event /path/to/user-initial.json --output evaluation/semantic_pilot/user_review_v1/work/003-r01.json
python3 evaluation/semantic_pilot/user_review_v1/workflow.py check evaluation/semantic_pilot/user_review_v1/work/003-r01.json
```

[templates](templates/)는 사용자 최초 판단·AI 반례 검토·사용자 확정·재검토 이벤트의 빈 골격이다. null 값은 실제 사람이 채우기 전 검증을 통과하지 않는다. user_initial의 `payload.form`에는 기존 입력 전용 패키지의 양식을 **사람이 작성한 뒤** 넣는다. 양식의 파일 해시·사례·검토자 식별자가 이벤트와 일치해야 한다. AI 단계에는 [반례 검토 요청문](COUNTERREVIEW.md)을 사용할 수 있다.

append는 event JSON을 받아 해시 연결을 계산하고 새 파일에만 쓴다. 기존 파일명으로 저장하면 실패한다. 이벤트 ID·이전 이벤트 SHA-256·참조한 검토 ID·근거 오프셋·시간 순서를 검사한다. 해시 연결은 기록의 무결성 보조 수단이며 전자서명이나 악의적 재작성 방지는 아니다. 제출 스냅샷과 Git 변경 이력을 함께 보존한다. 기존 기록 자동 가져오기, 자동 사람 확인, Core 승인, 원격 배포는 수행하지 않는다. 실제 평가에 채택할 때는 별도 개발용 manifest에 선택한 최신 기록 경로·SHA-256·검수 방식/수준을 고정하고, 재검토를 시작하면 현재 기록 참조를 갱신해 과거 확정 스냅샷을 현재 골드로 잘못 사용하지 않도록 한다. 이번에는 채택할 최종 기록이 없으므로 새 골드 manifest를 만들지 않는다.

## 독립 복수 검수 경로 유지

상위 경로는 기존 `answer.schema.json`과 `validate.py.validate_pair`의 규칙 그대로다. 실제 독립 검토자 2명 이상과 별도 재정자의 기록은 **새 독립 검수용 sidecar 파일**에서 기존 답안 형식으로 관리하고 기존 답안·공동 검토를 덮어쓰지 않는다. 새 sidecar에 과거 사용자 의견을 새 비노출 사람 의견으로 복사하지 않는다. 과거 공동 검토는 원본 답안과 보존 장부로 계속 추적한다. AI 제안·입력 해시도 연결한다.

```bash
python3 evaluation/semantic_pilot/user_review_v1/workflow.py check-independent /path/to/new-independent-answer.json
```

이 명령은 기존 validator를 호출해 독립 sidecar를 검사하고 검수 수준을 별도 출력한다. 원래 검수 인원·비노출·재정자 분리·불일치 해결 조건은 완화하지 않는다. 기존 12건의 provisional 답안은 상위 완료 기록으로 통과하지 않는다. 이 작업에서 실제 독립 sidecar나 사람 최종 기록은 만들지 않았다.

## 개발용과 독립 홀드아웃

개발용은 사용자 검수·AI 반례 검토·재검토를 반복하며 개선할 수 있다. 데이터셋과 결과 보고에 검수 방법·수준·단일 검토자 한계를 함께 기록한다. 단일 사용자 방식의 도구는 `dataset_role: development_only`만 허용한다.

홀드아웃은 다른 원문·저장소 계열에서 별도 확보한다. 사람 정답은 **검증기 예측을 보기 전에** 버전·해시로 고정하고 접근을 분리한다. 홀드아웃 결과나 발견 오류를 보고 튜닝했다면 해당 사례·관련 파생 계열은 더 이상 독립 홀드아웃으로 주장하지 않는다. 개발용으로 이동한 이력과 새 홀드아웃 교체 근거를 남긴다. 사람 라벨이 단일 검토자라면 홀드아웃에서도 그 한계는 그대로 보고해야 하며, 데이터 독립성과 복수 검토자 신뢰도는 별개다. 이 변경은 새 홀드아웃을 만들지 않는다.

## 검증

```bash
python3 -m unittest discover -s evaluation/semantic_pilot/user_review_v1 -p test_workflow.py
python3 evaluation/semantic_pilot/validate.py
python3 -m unittest discover -s evaluation/semantic_pilot -p test_validate.py
python3 -m unittest discover -s evaluation/semantic_pilot/independent_review -p test_review_package.py
```

새 테스트는 메모리와 임시 디렉터리의 가상 기록만 사용한다. 테스트 통과는 실제 사람 검토·AI 반례 검토·최종 확정이 수행됐다는 뜻이 아니다.

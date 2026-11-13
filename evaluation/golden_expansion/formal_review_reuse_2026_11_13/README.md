# 기존 17건 검토 증거 재사용 후보 (인간 승인 전)

이 디렉터리는 PR #28의 활성화 차단 원인을 줄이기 위한 **사용자 확인 보조자료**다. 현재 사용자 최종 판단 17건, 개발용 포함 승인 17건 및 기존 v2 활성 골드 12건을 변경하지 않는다.

- `build_suggestions.py`: 기존 immutable 최초 판단·Codex 원시 반례·사용자 최종 판단·포함 승인에서 설명과 정확한 인용 범위를 추출한다.
- `suggestions.json`: 17건의 기존 제출 판단, AI 반론 및 **인간이 아직 확인하지 않은** 원문·후보 인용 제안 34개. `user_confirmed: false`는 실제 증거 확인이 없다는 의미다.
- `format_mapping.py`, `format-mapping.json`: 기존 사용자 제출 내용의 필드를 정식 review.schema에 대응시키는 **서식 이관 지도**. 17건을 재판정하지 않으며, 미확인 필드는 원문으로 추측해서 채우지 않는다. 실제 workflow event가 아니다.
- `transcription_adapter.py`, `transcription.json`: 기존 최초/최종/승인 출처와 SHA-256·JSON pointer를 바인딩한 **실제 기록 기반 정규화 이력**. 현재 검토에 확인되지 않은 데이터는 `null` 또는 `false`로 남겨 둔다. `validate()`는 이 파일을 기존 출처에서 재생성한 값과 비교하는 읽기 전용 검증이다.
- `test_transcription.py`: 이력 재생성·범위·원본 바인딩·손상 감지·AI 증거의 사용자 귀속 방지 등을 검사하는 회귀 테스트.
- `EVIDENCE_COVERAGE.md`: 기존 사용자 판단을 다시 묻지 않고 증빙으로 인정할 수 있는 이력과, 정식 스키마에서만 빠진 항목을 구분한 검수표.

## 이미 제공된 것과 아직 필요한 것

이미 제출됨: 사례별 최초 판단·이유, 사용자 최종 판단, AI의 반론 타당성 평가에 대한 동의, 전체 17건 개발용 포함 승인. 이들은 변경하지 않는다.

정식 검수 워크플로에 아직 없는 것: 같은 human actor_id와 연결된 최신 user_initial 제출 이벤트, 사용자가 직접 확인한 최종 evidence 1개 이상, 별도 현재 ai_counterreview 이벤트의 challenge_id별 사용자 최종 응답·사유, confidence_limitations 인지·확인, GC-003/006/009/012의 최종 미해결 사항 확인. reviewer_id는 actor_id와 일치해야 한다.

**스키마 주의**: initial reviewed_at과 blinded_to_prior_judgments는 필드 존재가 필요하지만 null을 허용하며, initial evidence는 빈 배열도 허용한다. final evidence는 최소 1개를 요구한다. 외부 인증 서명은 요구하지 않는다. 사용자 검토 과거 시각을 만들어 쓰지 않는다.

## 사용자 확인 절차

1. 기존 사용자의 initial/final 판단·이유·골드 포함 승인을 그대로 `format-mapping.json`의 원본 출처에 연결해 서식만 정리한다. **다시 의미 판단을 받지 않는다.** 과거 검토 시각·블라인드 여부가 알려지지 않으면 null을 유지한다.
2. 이미 수행한 Codex 반례 검토와 사용자 응답의 출처를 보존한다. 다만 기존 정식 정책은 user_initial → ai_counterreview → user_final 순서의 hash-linked 이벤트와 반론별 응답을 요구한다. 그 순서/반론별 응답이 당시 정식 형태로 기록됐다고 소급해서 꾸미면 안 된다. 기존 기록을 역사적으로 충실하게 전사한 이력과 형식상 새로운 절차는 구별한다.
3. 사용자에게 이미 결정한 라벨을 재질문하지 말고, 기존 자료에 **없는 사실**만 확인한다. AI가 제시한 evidence quote의 사용자 채택 여부, challenge별 accept/reject/defer 연결, confidence limitation의 명시적 확인 및 4개 UNRESOLVED의 final 미해결 사유가 이에 해당한다. 기록에 없으면 미확인 그대로 둔다.
4. 정책을 우회하지 않고 기존 review.py/record.schema.json에 적합한 정식 워크플로로 증빙 가능한지 검증한다. 아직 미충족이면 신규 활성화를 보류하고, 충족하면 별도 v3 활성화 PR로 진행한다.

`suggestions.json`은 검토용 초안이므로 파일 자체를 새 골드, 사용자 제출 증거, 자가 인증된 채팅 로그 또는 활성화 승인으로 취급하면 안 된다.

## 즉시 실행 가능한 검증

```sh
python3 -B evaluation/golden_expansion/formal_review_reuse_2026_11_13/validate_suggestions.py
python3 -B evaluation/golden_expansion/formal_review_reuse_2026_11_13/transcription_adapter.py
python3 -B -m unittest discover -s evaluation/golden_expansion/formal_review_reuse_2026_11_13 -v
```

기존 사용자 판정은 보존·재사용되지만, 이 서식 정규화 자체는 정식 `user_initial → ai_counterreview → user_final` hash-linked 이벤트 체인이 아니다. 따라서 `development_gold_eligible`를 참으로 바꾸거나 신규 골드를 활성화하지 않는다. 사용자 동의가 특정 `challenge_id`를 승인했다거나 사용자가 AI 인용을 직접 증거로 제출했다고 주장하지 않는다.

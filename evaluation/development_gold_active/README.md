# 현재 활성 개발용 골드 평가 소비자

`evaluation/active_development_gold.json`에 등록된 두 진입점이다. 활성 참조는 승인된 **v3 29건(P12/V9/U8)**이며 기존 v2와 과거 평가 스크립트·결과는 재현용으로 보존한다.

```sh
# 입력 전용 예측: 모델 호출 없이 실행 가능. 정답은 이 단계에서 읽지 않는다.
python3 -B evaluation/development_gold_active/source_candidate.py predict /tmp/v3-semantic-predictions.json
# 정답 비교는 별도 단계다. 미실행 결과에서 정확도를 만들지 않는다.
python3 -B evaluation/development_gold_active/source_candidate.py compare /tmp/v3-semantic-predictions.json /tmp/v3-semantic-comparison.json
python3 -B evaluation/development_gold_active/core_diagnostics.py predict /tmp/v3-core-predictions.json
python3 -B evaluation/development_gold_active/core_diagnostics.py compare /tmp/v3-core-predictions.json /tmp/v3-core-comparison.json
```

원래 source_candidate_semantics 검증 엔진과 core_pipeline 진단 로직을 그대로 재사용하며 29개 입력 경로만 독립적으로 제공한다. GC 및 신규 SP는 기존 레거시 파생 입력이고 새 데이터로 대체하지 않는다. 현재 활성 manifest는 비교 시에만 읽는다. 무인증 모델 실행·정답 누출·Core 승인으로 승격하지 않는다.

`source_candidate`의 completed cited UNRESOLVED 관측과 모델 미실행/불완전 실행을 구분한다. 기존 definitive-only accuracy 분모를 유지하며 `core_diagnostics`는 SP accuracy가 아니다. 이 기능 검증은 합성 프로토콜 fixture와 오프라인 실행으로 수행하고 실모델 점수로 주장하지 않는다.

옛 `evaluation/source_candidate_semantics/run.py` 및 `evaluation/core_pipeline_2026_11_11/evaluate.py`는 **v2 역사 재현용 진입점**이다. 현재 작업에는 위 v3 명령 또는 활성 인덱스에 등록된 소비자를 사용한다.

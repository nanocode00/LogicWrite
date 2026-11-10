# Final-output semantic pilot v0.1

**12 provisional development cases; 0 human gold; no holdout.**

[검수 가이드·기존 자료 조사·확장 계획](../../docs/semantic-gold-pilot.md)을 먼저 읽는다. [manifest.json](manifest.json)은 평가자 전용 목록이다. 모델에는 `inputs/SP-NNN.json` 하나만 제공한다. `answers/`, manifest와 가이드는 제공하지 않는다. 공개 원문 1개에서 파생된 3건과 통제 합성 9건이다. 모든 후보·기대 판정은 AI 작성이며 실제 공개 저장소 변경이 아니다. `answers/*.json`의 `reviews`에는 사용자와 설명을 함께 보며 진행한 사람 검토 1건씩을 별도로 기록했다. 독립·비노출 검수나 골드 확정은 아니다.

```bash
python3 -m pip install -r evaluation/semantic_pilot/requirements.txt
python3 evaluation/semantic_pilot/validate.py
python3 -m unittest discover -s evaluation/semantic_pilot -p test_validate.py
```

검사는 구조와 무결성만 확인한다. 의미 판정 정확도·Core PASS를 입증하지 않는다. 파일럿 manifest는 전건 provisional을 강제한다. 이후 사람 검수 데이터의 승격은 별도 데이터 버전과 manifest 정책 검토가 필요하다.

[단일 사용자 + AI 반례 검토 v1](user_review_v1/README.md)은 별도 기록에서 개발용 골드 적격을 관리한다. 기존 12건과 독립 복수 검수 기준은 유지하며, AI 반론은 사람 판정으로 세지 않는다.

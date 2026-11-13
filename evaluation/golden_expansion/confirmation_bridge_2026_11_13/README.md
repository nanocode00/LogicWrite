# 기존 Golden Set 17건의 정식 증거 확인 묶음 — 승인 전

**목적:** 기존 사용자 최초 판단 17건, Codex 반례 평가 17건, 사용자 최종 판단 17건 및 개발용 포함 승인 17건을 다시 수집하지 않고, 정식 user_final 형식에서 *실제로* 빠진 항목만 묶어 검토하기 위한 자료다.

## 파일

- `REVIEW.md`: 이미 확정한 라벨 17건, Codex 반론 및 원문 인용 34개 전체를 사람이 읽을 수 있는 검토 문서로 정리
- `confirmation-batch.json`: 사용자 판단 및 승인 출처, 원본 파일/해시, 각 반론과 인용의 확인 전 제안
- `build_batch.py`: PR #28의 immutable `transcription.json`과 `suggestions.json`을 기반으로 패키지 생성
- `render_review.py`: 사람이 읽을 수 있는 검토 패키지 생성
- `validate_batch.py`, `test_batch.py`: 원본과 17건/34개 근거 바인딩 및 인간 증거 사칭·골드 활성화·라벨 변조 차단

## 사용자가 이미 완료한 판단

17건 최종 분포는 PRESERVED 8 / VIOLATION 5 / UNRESOLVED 4이며, 최초 판단과 모두 동일하다. 사용자는 과거 Codex의 **반론 타당성 평가**에 사례별로 '동의'했고, 17건 전부 개발용 포함을 명시적으로 승인했다. 사용자 판단을 다시 수행할 필요는 없다.

## 정식 형태로 제안할 수 있지만 확정하지 않은 내용

Codex의 strongest counterargument와 그 타당성 평가는 원본 출처 그대로 연결한다. 사용자의 사례별 '동의'는 **Codex의 평가에 동의**했다는 뜻으로만 보존한다. 이를 정식 `challenge_id`별 `accept/reject/defer`로 전환하는 것은 근거가 부족하므로 **응답값과 challenge ID를 모두 null로 유지**한다.

AI가 인용한 원문/후보 34개는 SHA/offset으로 대조된 **참고 근거**이나, 현재 `human_confirmed_as_final_evidence`는 모두 null이다. UNRESOLVED 4건의 `initial_unresolved_reason`은 실제 사용자 최초 이유이며, 별도의 final `unresolved_issues` 사용자 입력으로 합성하지 않는다.

정식 기록으로 추가하려면 사용자가 `REVIEW.md`의 인용과 반론 대응을 확인하고, 필요한 범위의 evidence 채택, challenge별 응답, confidence limitations 및 UNRESOLVED 4건 최종 이슈를 새 기록으로 명시해야 한다. 이는 기존 라벨 재판정과 다르다.

## 검사

```sh
python3 -B evaluation/golden_expansion/confirmation_bridge_2026_11_13/validate_batch.py
python3 -B -m unittest discover -s evaluation/golden_expansion/confirmation_bridge_2026_11_13 -v
```

**경계:** 신규 정식 human event 0건, 신규 골드 적격 0건, 활성화 0건. 기존 활성 v2의 12건을 유지한다. 이 패키지를 곧바로 정식 `review.py`에 통과시키거나 기존 workflow 필수 정책을 느슨하게 만들어서는 안 된다. 사용자 확인을 받고도 실제 event-chain 요건은 별도로 검증해야 하며 v3 활성화는 그 이후의 작업이다.

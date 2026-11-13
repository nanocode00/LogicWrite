# 통합 문서 재구성 평가 — AI 초안 3건

2026-11-13. 최신 main `879d15b`에서 분기했다. 기존 57건·활성 29건·Core는 변경하지 않는다.
**3건 모두 합성·개발 노출·사람 미검수이며 골드가 아니다.** 같은 AI 작성 군집 1개로 센다.

| 먼저 볼 자료 | 내용 |
|---|---|
| [DESIGN.md](DESIGN.md) | 기존 설계 문제, 새 D/Q·관측·채점·대안 정책, 호환 범위 |
| [REVIEW.md](REVIEW.md) | 입력 우선 검수 순서, 사례별 질문, 판정 양식 |
| [IR-001 입력](inputs/IR-001.md) → [답안 초안](answers/IR-001.md) | README·사용 안내와 승인 명세·개발 기록: 설치 경로, 정보 선택, 참여 안내, 표현과 링크 |
| [IR-002 입력](inputs/IR-002.md) → [답안 초안](answers/IR-002.md) | 한국어 설계·운영·주간 보고·ADR: 현행/과거, 역할별 정보 배치, 안전 조건, 과장 제거 |
| [IR-003 입력](inputs/IR-003.md) → [답안 초안](answers/IR-003.md) | 회의 자료·실험 기록·일정: 무수정/서식만 변경, 내용·공개판 판단의 보류 |
| [FORMAT.md](FORMAT.md), `*.schema.json` | 모델 입력·AI 정답·사람 응답·실행 결과 규약. 기존 Core 입력과 다른 평가 전용 형식 |
| [legacy_triage.json](legacy_triage.json) | 57건 지시문·해시와 보존/조건부 재사용 제안. 기존 판정 대체 아님 |
| [EXPANSION.md](EXPANSION.md) | 기존 자산 처리와 다음 수집·검수 관문 |
| [VALIDATION.md](VALIDATION.md), [records/](records/) | 실제 점검과 한계, 보호 기준선, 실행 로그 |
| [sources.json](sources.json) | 가상 자료의 작성·라이선스·출처 군집 기록 |

모델에는 **입력 JSON 하나만** 전달한다. README·사례 장부·입력 카드의 주변 디렉터리·답안·검수 자료를 통째로 주지 않는다.

```sh
python3 evaluation/integrated_reconstruction/validate.py
python3 evaluation/integrated_reconstruction/validate.py --input IR-001 > /tmp/IR-001-model-input.json
python3 -m unittest discover -s evaluation/integrated_reconstruction -p 'test_*.py'
```

`--input`은 입력 스키마·원문 해시만 확인하고 그 입력만 stdout으로 내보낸다. 패키지 검증은 읽기 전용이다.
검수 응답은 `reviews/IR-xxx.json`의 사본에 사람이 작성한다. 검증기는 렌더링·응답 덮어쓰기를 하지 않는다.
현재 사람 최초/최종 판단·중재·골드 포함 승인은 모두 null이다. 포함 승인은 별도 후속 절차이며 이 초안에서 기록·허용하지 않는다.
본문 보존과 실제 독자 과업 달성은 사람이 평가해야 한다. 구조 검사 통과는 성능·품질 입증이 아니다.

# 통합 문서 재구성 평가 — AI 초안 3건

2026-11-13. 최초 기준 main `879d15b`에서 분기했으며 통합 정리에서 #37/#33의 실제 병합 main을 반영한다. 기존 57건·활성 29건·Core는 변경하지 않는다.
**3건 모두 합성·개발 노출 사례다. 2026-11-17 사용자 포함 승인으로 별도 개발용 골드에 등록했다.** 같은 AI 작성 군집 1개로 센다. 기존 활성 29건이나 비공개 홀드아웃에는 합류하지 않는다.

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
| [v2 참고 출력 후보](reference_outputs/v2_candidates/REVIEW.md) | clarification-02 기준 비유일 후보 2건과 검토 이력; 후속 사용자 검수 승인 기록은 별도 | 
| [개발용 골드 등록](development_gold/manifest.json) | 세 사례의 사용 기준 버전, 승인 근거, 합성·노출 표시와 읽기 전용 검사 |
| [VALIDATION.md](VALIDATION.md), [records/](records/) | 실제 점검과 한계, 보호 기준선, 실행 로그 |
| [sources.json](sources.json) | 가상 자료의 작성·라이선스·출처 군집 기록 |

모델에는 **입력 JSON 하나만** 전달한다. README·사례 장부·입력 카드의 주변 디렉터리·답안·검수 자료를 통째로 주지 않는다.

```sh
python3 tools/evidence_validation/run.py --output /tmp/logicwrite-validation.json
python3 evaluation/integrated_reconstruction/check_preservation.py
python3 evaluation/integrated_reconstruction/validate.py
python3 evaluation/integrated_reconstruction/validate_criteria.py
python3 evaluation/integrated_reconstruction/validate_reference_candidates.py
python3 evaluation/integrated_reconstruction/development_gold/validate.py
python3 evaluation/integrated_reconstruction/validate.py --input IR-001 > /tmp/IR-001-model-input.json
python3 -m unittest discover -s evaluation/integrated_reconstruction -p 'test_*.py'
```

`--input`은 입력 스키마·원문 해시만 확인하고 그 입력만 stdout으로 내보낸다. 패키지 검증은 읽기 전용이다.
검수 응답은 `reviews/IR-xxx.json`에 기록하며 이전 양식·응답은 `reviews/history/`에 버전별 보존한다. 검증기는 렌더링·응답 덮어쓰기를 하지 않는다.
기존 검수 판단과 수정요청은 [REVIEW.md](REVIEW.md), [평가 기준 v2](criteria/v2/README.md)에 보존했다. 2026-11-17 [사용자 공동 검수 승인](reviews/post_revision_approvals/2026-11-17.json) 후 [개발용 골드 포함 기록](development_gold/manifest.json)으로 IR-001~003의 개발용 포함을 별도 승인했다. 기존 스키마·검증 기록의 `null`/`gold_eligible=false`는 승인 이전 스냅샷이며 덮어쓰지 않는다. 독립 제2의 사람 검토, 비공개 홀드아웃, 실제 모델 성능 검증, PR 병합·발행 승인은 주장하지 않는다.
본문 보존과 실제 독자 과업 달성은 사람이 평가해야 한다. 구조 검사 통과는 성능·품질 입증이 아니다.

공식 전체 명령은 역사적 평가와 현재 Core/신규 평가를 분리한다. 레거시 `run_checks.py` 및 기존 역사 validator의 현재 트리 직접 호출 차이는 [공식 실행 안내](../../tools/evidence_validation/README.md)에 있다. 부분 검증으로 전체 검증을 대신하지 않는다. 보존 검사는 과거 전체616파일을 고정 snapshot에서, 기존 평가/fixture545파일과 이미 노출된 파일럿21파일을 원본 저장본/인증된 양식 이력에서 확인한다. 현재 검수 기록은 별도 스냅샷·해시와 대조한다. 정상적인 현재 Core/개발 문서는 과거 바이트와 같을 의무가 없다.

v1 3건은 그대로 보존한다. [v2 입력 규약](FORMAT.md#입력-v2--불완전한-계약자료-표현)은 무제약·미확정 역할·부분 자료를 표현하나 새 실제 사례/골드가 아니다. 사람 응답은 최초 양식과 이전 판단을 이력으로 보존하고 현재 기록을 갱신한다. 현실성·유도·D/Q 강제성의 남은 판단은 [DESIGN.md](DESIGN.md)와 [REVIEW.md](REVIEW.md)를 따른다.

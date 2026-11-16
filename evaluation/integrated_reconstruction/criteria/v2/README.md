# 평가 기준 v2 — 수정요청 반영본

사용자가 확정한 CR-001-01~05와 CR-002-01을 같은 v1 입력에 적용한 평가 기준이다. [계보 명세](manifest.json)가 부모 v1 답안·입력·참고 출력·수정본 해시와 요청별 반영 위치를 연결한다. JSON 직렬화는 기존 `integrated-answer-v1`/`answer.schema.json`을 재사용하며 **평가 기준 버전**은 `evaluation-criteria-v2`다. `input-v2.schema.json`과 무관하며 입력 변경은 없다. IR-003은 기준 변경 없이 사람 검수 기록만 갱신했다.

| 수정본 | 부모 기준 | 입력 | 주요 보존 조건 |
|---|---|---|---|
| [IR-001](IR-001.json) | [v1](../../answers/IR-001.json) | [v1 입력](../../inputs/IR-001.json) | D5/Q2, F2, 명시 제약·기존 인용·실행 정확성 |
| [IR-002](IR-002.json) | [v1](../../answers/IR-002.json) | [v1 입력](../../inputs/IR-002.json) | D 전체, Q2~Q4, F 전체, 기존 인용 |

## 구현·검증 순서

- [x] 최초 양식·이전 검수·이전 수정요청 원문 보존 후 IR-003 단계별 검수 기록.
- [x] IR-001 역할·HITL·보존/제거·유지보수·배치/승인 기준 수정. IR-002 Q1 원문 반영과 reader_tasks·A/B 설명 정합화.
- [x] 해시 계보, JSON 스키마, 인용 범위, 기준 변경 허용 범위, A/B 불변조건 검사와 변조 회귀 테스트.
- [ ] IR-001·IR-002 수정본 사람 재검수. 세 사례 골드 포함 승인은 별도 보류.

IR-001은 모든 문서가 제공되어 `availability.gaps=[]`이지만 최신 후원 정책을 확정할 근거가 없는 인식상의 불확실성이 있다. v1 입력을 고쳐 공백을 만들지 않고 D.confirmation에 충돌·권한·사용자 확인을 기록했다. v1 검사기의 'confirmation이면 자료 gaps가 있어야 함' 규칙을 새 기준에 강제하지 않으며 이 차이는 평가 기준 검증기에 명시했다. D는 판단, Q는 검토 가능한 초안이며 사람의 배치·표현 확정과 실제 적용 권한은 분리한다.

README 설치 명령은 필수가 아니다. 사용 안내가 설치·실행 조건·세부 사용법을 담당하며 유지보수 문서가 없으면 유지보수자용 절도 허용한다. 기술적 결정은 읽기 전용 개발 기록에 이미 보존되어 있어 이를 변조하지 않는다. 일기성 정보는 제거·분리 후보를 제시하고 확인받는다. 후원 충돌은 근거와 HITL 보류로 드러내며 근거 없이 금전 후원 가능 여부를 정하지 않는다. 독립적으로 가능한 개선은 진행한다.

IR-002는 문서군 전체에서 2026-11-12 이후 운영 60초·개발 30초와 시점을 확인한다. 동일 조건을 양쪽에 반복할 의무는 없으며 반복 시 충돌이 없어야 한다. 운영서만으로 필요한 안전 행동을 판단하는 Q2는 유지한다. 주간 관찰은 기간·표본 한계와 함께 남기거나 보고서 링크로 대신할 수 있다. 제한된 관찰은 일반 안정성 증거가 아니다. A/B 모두 허용한다.

## 검증과 한계

```sh
python3 evaluation/integrated_reconstruction/validate.py
python3 evaluation/integrated_reconstruction/validate_criteria.py
python3 evaluation/integrated_reconstruction/check_preservation.py
python3 -m unittest discover -s evaluation/integrated_reconstruction -p 'test_*.py'
python3 tools/evidence_validation/run.py --output /tmp/logicwrite-criteria-v2-validation.json
```

검증기는 읽기 전용이다. 원본 양식은 Git 최초 커밋, 이전 검수는 `6d6f321` Git 객체와 대조하며 현재 검수는 별도 스냅샷·해시와 대조한다. v1 참고 출력은 경로·해시를 보존한 역사 자료이고 **v2 적합성을 재검증한 예시가 아니다**. 특히 IR-001의 기존 정책 단정·일기성 정보 처리·유지보수 배치는 사람 재검수와 후속 예시 개정 여부 판단이 필요하다.

기계 검증 결과는 [검증 기록](validation.json)에 별도 기록한다. 수정 후 사람 재검수 결과는 null, 세 사례 골드 포함 승인은 null이다. 모델 성능 평가·실제 문서 발행·골드셋 동결은 이 버전에 포함하지 않는다.

# G2-C 복수 문서 Reconstruction 실행 기록

G1 전체 스냅샷 → G2-A 분석 → G2-B 명시 작업 계획 → G2-C 격리 후보를 연결했다. 구조 검사를 통과한 전 문서 후보도 `REVIEW`이며 의미 보존·독자 목적·자연어 제약은 미해결이다. `request_complete=false`, `delivery_approved=false`, `stage_transition_allowed=false`, `b2_reconstruction_success=false`를 유지한다.

## 변경 파일과 인터페이스

| 파일 | 역할 |
| --- | --- |
| [document_set_reconstruction.py](../../full_document_control/document_set_reconstruction.py) | 입력·계획·격리 요청 결속, 작업별 재검사와 원자적 후보 생성 |
| [document_set_final_validator.py](../../full_document_control/document_set_final_validator.py) | 원본 좌표로 독립적인 물리 순서 계산, 실제 결과·출처·권한·trace 검사 |
| [reconstruction.py](../../full_document_control/reconstruction.py), [final_validator.py](../../full_document_control/final_validator.py) | 기존 문단 구분 개행 및 원본·후보 범위 partition 검사 추출·공유 |
| [DOCUMENT_SET.md](../../full_document_control/DOCUMENT_SET.md) | G1과 별도 G2-C 진입점 연결 기록 |
| [test_document_set_reconstruction.py](../../full_document_control/test_document_set_reconstruction.py) | 합성 편집 및 권한·변조·보류·롤백·IR 회귀 |
| [g2_c_offline.py](../g2_c_offline.py), 이 디렉터리 | 입력 전용 오프라인 재현기, 보고서와 두 합성 사례 전체 실행 기록, IR 집계 및 공식 검증 결과 |

```python
grant = make_candidate_request(plan, task_ids=approved_tasks,
                               document_ids=approved_write_targets)
result = reconstruct_document_set(
    contract, analysis, plan, plan_request, grant,
    trusted_contract_sha256=contract_pin, trusted_request_sha256=plan_request_pin,
    trusted_candidate_request_sha256=candidate_request_pin,
)
report = validate_candidate_result(result, contract, analysis, plan, plan_request, grant,
                                   trusted_contract_sha256=contract_pin,
                                   trusted_request_sha256=plan_request_pin,
                                   trusted_candidate_request_sha256=candidate_request_pin)
```

호출자가 세 해시를 별도 신뢰 경계에서 보관한다. G2-B는 고정된 계획 요청과 G1/G2-A로 계획을 재생성하고 G2-C는 전체 계획을 대조한다. grant는 정확한 계획·격리 실행 모드·작업 ID·수정 가능 문서 ID에 결속된다. 이동 원본과 목적지 모두 grant의 쓰기 범위와 G1 edit 출력 범위에 있어야 한다. 동일한 고정 입력은 결정론적으로 다시 검증할 수 있으며, 입력이나 요청이 바뀌면 예전 계획·grant를 거부한다. 최초 입력·권한 진위는 고정하는 호출자의 책임이다.

기존 Organization/Expression/Reconstruction 실행 경로는 단일 원본 및 단일 `output_scope`를 기준으로 입력·승인·계획 검증을 수행한다. G2-C는 G2-B의 Organization 결정을 별도 조립기에 연결하고 기존 Markdown parser, 개행 경계, 범위 partition 검사를 공유한다. G1의 전체 출력 범위·해시·권한 검사와 함께 실제 후보를 검사한다. 별도 Expression 실행 없이 문단 바이트를 그대로 유지한다. 결정론적 표현기가 생성할 수 있는 변경도 문서군에서의 의미 보존 근거가 없으므로 REVISE·CONSOLIDATE는 미지원으로 기록한다. 기존 단일 문서 진입점과 G1의 admission-only `prepare_reconstruction` 계약을 보존한다.

## 실행 결과와 추적

| 사례 | 원문 → 후보 | 검증과 상태 |
| --- | --- | --- |
| [안전한 MOVE 전체 기록](synthetic-move.json) | `Photograph the storage shelf.`가 `catalog` 끝에서 `log` 끝으로 이동. `Record the item label.`과 `Archive the inventory.`는 원문 유지 | 후보 2/2, `move-photo` executed, 구조 passed, REVIEW |
| [부분 보류 전체 기록](synthetic-partial.json) | `catalog`의 두 문단이 `Record… → Photograph…`에서 `Photograph… → Record…`로 변경. `operations`의 `If the alarm sounds, wait.`는 그대로 유지 | 후보 4/4, `place-label` executed, `move-alarm` held, 구조 passed, partial_candidate, REVIEW |

MOVE 원장의 `catalog.changes=[8]`와 `log.changes=[7,8]`는 trace 인덱스를 가리킨다. 인덱스 8은 원본 `catalog[35:65]` → 후보 `log[31:61]`의 정확한 문단을 연결하고, 인덱스 7은 `log[30:31]`에 들어간 구분 개행을 기록한다. PLACE trace 인덱스 5는 `catalog[11:34]` → `catalog[43:66]`에 대응한다. 예시의 영문 범위는 코드포인트/UTF-8 바이트 좌표가 같고, 한국어 바이트 좌표는 별도 테스트로 확인했다. 각 원장에 scope ID, 원본·후보 SHA-256, 출입 및 변경 trace 인덱스를 기록한다. Trace는 양쪽 문서 ID·정확 범위·해시, 원문 출처 및 정보 단위, 적용 작업 ID를 담는다. 작업별 감사 기록은 계획 상태, 근거 인용, 보존 조건, 의존 작업, HITL 및 실제 상태를 담는다.

동일 절의 명확한 문단 앵커만 PLACE에 사용한다. MOVE는 편집 가능 문서의 끝으로 제한하고, 문서 제목 외의 절 문맥, 확인 가능한 조건·반대 지시·참조 의존·순서 충돌을 보류한다. 관련 문서 수준의 읽기·쓰기 교차나 동시 append도 보류한다. 이미 배치된 문단과 KEEP는 preserved로 집계한다. 읽기 전용 문서 및 format_only 내용 변경은 거부하고, REMOVE와 일반 의역 통합은 미지원이다. 미등록 문서 생성은 scope 거부다. 변조된 계획/요청, 불완전한 후보, 중복/누락 MOVE, 범위 위조는 구조 검사에서 차단한다. 생성 또는 검증 실패 시 후보·원장·trace 전체를 폐기하며 실행 예정 작업을 failed로 기록한다.

## IR 입력 전용 결과

| 입력 | 전체 입력 | 출력 범위 | 후보 | 실제 편집 | 미해결 |
| --- | ---: | --- | --- | ---: | --- |
| IR-001 | 7 | readme, usage | 2/2 바이트 동일 | 0 | KEEP 37, 작업 분해 held 1, HITL 1 |
| IR-002 | 4 | design, ops | 2/2 바이트 동일 | 0 | KEEP 19, 작업 분해 held 1, HITL 1 |
| IR-003 | 3 | meeting (format_only) | 1/1 바이트 동일 | 0 | KEEP 11, 작업 분해 held 1, HITL 3 |

[결과 집계와 구조 증거](summary.json). 세 입력 모두 구조 passed, partial_candidate, REVIEW다. KEEP 수에는 참조 전용 보존 작업이 포함된다. 어떤 읽기 전용 문서도 출력 범위로 승격되지 않았다. IR 기본 계획에는 편집 항목이 없고 실제 편집 증거는 위 합성 사례에서 확보했다.

## 검증 재현

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiments/full_document_control
PYTHONDONTWRITEBYTECODE=1 python3 experiments/integrated_reconstruction_pilot_20261117/g2_c_offline.py --output /tmp/logicwrite-g2c-new-records
PYTHONDONTWRITEBYTECODE=1 python3 tools/evidence_validation/run.py --output /tmp/logicwrite-g2c-new-evidence.json
```

Red에서 G2-C 인터페이스 부재를 확인했다. 이후 동일 문단의 허위 실행 집계, 목적지 반대 지시, 미해결 질문이 있는 후보의 상태를 각각 재현하고 수정했다. 별도 코드 리뷰의 한·영 문단 순서 제약, 조건·참조 표현과 BOM 경계, 내장 구조 보고서 변조 발견을 Red→Green으로 검증했다. 기록 생성기를 새 경로 두 곳에 실행해 IR 전체 실행 기록과 합성 실행 기록이 바이트 단위로 결정론적인지 확인했다.

[최종 공식 검증 JSON](evidence-validation.json)은 **31개 suite, 944개 테스트 PASS**를 기록한다. 실패·오류·스킵·예상 실패·예상 밖 성공은 모두 0이다. Core 458개에 신규 G2-C 27개가 포함된다. 별도 리뷰 수정 전 첫 공식 실행은 941개 PASS였고, 최종 수정 후 새 결과 경로에서 전체를 재검증했다. 공식 결과의 코드 해시는 실행 중 고정한 스냅샷을 가리킨다. 이 JSON의 저장소 내 복사 및 결과 문단 추가는 실행 후 이루어졌다.

시작 시점의 추적 파일 1,095개와 작업 디렉터리를 비교했다. 위 표의 기존 Core 헬퍼 두 파일과 계약 연결 문서 외 1,092개가 바이트 단위로 동일했다. 원본·평가·골드·사람 판단, 기존 모델 결과와 예산 원장은 보존했다. 다른 15개 워크트리의 HEAD가 유지됐다. 모델 호출은 0회다.

## G3에 필요한 근거

- 문단의 조건·예외·상호 참조, 목적지의 의미 충돌과 독자별 필수 현지 정보에 대한 독립 판정이 필요하다. 현재 검사는 보수적인 Markdown 구조와 영어·한국어의 일부 표지에 한정한다. N-16 조건 동반 MOVE의 문서군 보호는 입증되지 않아 실행 범위를 넓히지 않았다.
- 자연어 제약을 검증 가능한 의무로 정제하고 독립 의미 검사와 사람 결정의 출처를 결속해야 한다. 일부 변경이 무해해 보여도 format_only 서식 변환 및 표현 수정의 별도 정책과 검증이 필요하다.
- 문서 수준 독립성으로 보류한 작업의 범위를 좁히려면 읽기·쓰기 의존성, 해당 절의 의미, 안전한 여러 이동의 순서 근거가 필요하다. 출처·권한·계획 및 부분 승인 상태를 실제 검토 기록에 결속해야 한다.

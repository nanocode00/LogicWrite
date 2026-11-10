# 2-A: 전체 출력 의미 충실도 검증

현재 구현은 Python 표준 라이브러리를 사용하는 격리 후보 감사다. `supported`도 REVIEW이며 `delivery_approved`와 `stage_transition_allowed`는 항상 false다. 실제 파일 반영과 사람/정책 최종 승인은 2-B 범위다. M0~M4 완료 기준과 평가 성능을 변경하지 않는다. 이번 변경에서는 **실제 LLM 평가를 수행하지 않았다**. 테스트의 모델 응답은 합성 콜백이다.

## 책임과 실행 순서

`Analysis → Organization → Expression → Reconstruction → Structural Validation → Final Semantic Validation`

| 구현 | 검사 대상과 책임 |
| --- | --- |
| `semantic_validator.py` | 분석 단위의 statement·elements·relations·assessment ↔ 원문. 분석 전용 검토 창과 규칙은 최종 출력 검증으로 재해석하지 않음 |
| `final_validator.py` | 기존 고정 8개 구조·범위·추적·승인 경계 검사. API·보고서 무결성 검증·`semantic_fidelity: not_run`을 그대로 유지 |
| `final_semantic_validator.py` | 실제 `output_snapshots` 전체 ↔ 원본과 목적지 원본 전체. 분석의 의미 판정은 재사용하지 않고 수치·버전 추출 등 작은 문자 처리만 재사용 |
| `pipeline.validate_final_output` | 위 두 보고서를 `final-output-audit-v1`으로 결합. 어느 한쪽 FAIL도 종합 FAIL이며 PASS 경로는 없음 |
| `integration.run_pipeline` | 기존 `final_report`에 구조 보고서 유지. `final_semantic_report`, `final_audit` 추가. 종합 FAIL은 controller에서 STOPPED 처리하고 `last_gate_state: FAIL` 보존 |

구조 FAIL에서는 reviewer를 호출하지 않고 `execution.state: blocked_structural_failure`로 외부 의미 검토 미실행을 기록한다. 구조 실패 근거와 결정론적 진단은 보존하고, 미검토 의미 검사는 unresolved·불완전 범위로 유지하며 종합 FAIL을 낮추지 않는다. 전체 후보가 없는 Preview에는 모델을 호출하지 않는다. 원본과 목적지·출력 집합 또는 추적이 손상된 경우 FAIL을 보존한다.

## 실제 API

```python
validate_final_semantics(bundle, analysis, org, preview, result, *,
    destination_snapshots=None, reviewer=None,
    max_review_chars=48000, timeout_seconds=30)  # -> final-output-semantic-validation-v1
verify_final_semantic_report(bundle, analysis, org, preview, result, report, *,
    destination_snapshots=None)  # -> valid, gate_state, reason, execution_evidence_matches_current_inputs
validate_final_audit(bundle, analysis, org, preview, result, **kwargs)  # -> final-output-audit-v1
verify_final_audit(bundle, analysis, org, preview, result, audit, *, destination_snapshots=None)
```

`pipeline.validate_final_output`와 `verify_final_output_report`는 종합 감사의 wrapper다. `integration.run_pipeline`에는 `final_semantic_reviewer=None`, `max_final_review_chars=48000`, `final_review_timeout=30` 인자가 추가된다. CLI는 모델 어댑터 없이 결정론적 감사와 미해결 의미 결과를 반환한다. 별도 모델 CLI나 최종 승인 실행기는 없다.

`RevisionController.revalidate`는 `{report, semantic_report, final_audit, controller}`를 반환하며 현재 입력으로 다시 감사한다. 모델을 다시 실행하려면 `reviewer=`를 명시한다. controller가 하위 결과를 무효화할 때 `final_semantic_report`와 `final_audit`도 제거한다. 자동 수정·재시도는 하지 않는다.

## 검사 범위

| 고정 의미 검사 ID | 결정론적 확인과 모델 검토의 경계 |
| --- | --- |
| `CLAIM_FACTS` | 원장에 연결된 실제 원문/출력 차이를 기록. 일반 주장·사실의 의미 동등성은 모델 검토가 필요 |
| `QUANTITY_SCOPE` | 같은 문장 골격의 수치·단위·버전 대체와 대상 간 값/버전 바꿔치기를 순서까지 대조해 탐지. 초/분/시간/ms의 정확한 기간 환산은 동등하게 취급. 일반 대상·시간 범위나 복잡한 환산은 미해결/모델 검토 |
| `POLARITY_CONDITIONS` | 같은 문장 골격의 한국어 지원 부정 반전, 명시적인 `때만/경우에만 → 항상` 확대를 탐지. 일반 부정·예외·한정·조건 해석은 모델 검토 |
| `ADDITIONS_OMISSIONS` | 출처 없는 비공백 출력을 차단. 필수 `expected_literal` 누락은 동등 표현 가능성 때문에 미해결로 기록. 일반 필수 정보 누락·새 성능/보안 주장·의미 확대/축소는 모델 검토 및 기존 구조 불변식과 함께 확인 |
| `CONTRADICTIONS` | 원본·목적지·출력 전체의 내부/문서 간 모순 후보를 모델에 검토 요청. 문자열만으로 일반 모순을 확정하지 않음 |
| `MOVE_CONSOLIDATION` | 선언된 `qualifies/depends_on` 관계의 출력 문서 분리를 탐지. 이동 문장뿐 아니라 목적지 원본·출력 문맥, 통합 후 사실·귀속·조건 손실을 모델에 요청 |
| `PROVENANCE` | 구조 검증을 독립 재실행하여 실제 스냅샷·원장·trace·위치·범위·승인 위조 위반을 보존. 원장의 실제 출력 slice도 다시 확인 |

문자 검사만으로 전체 의미 검사군을 `supported`로 만들지 않는다. 확인된 위반은 모델이 supported라고 해도 유지한다. 같은 의미의 재서술·정상 문단 배치를 자동 위반으로 간주하지 않는다. 재구성기가 허용하지 않은 수정은 의미가 같더라도 별도의 기존 구조 검증에서 차단될 수 있다.

## 선택적 모델 콜백 계약

`reviewer(request: dict) -> dict | str | bytes`이며 모델/공급자 SDK에 종속되지 않는다. JSON 문자열과 바이트는 중복 키를 거부하는 기존 로더로 읽는다. 콜백에는 독립 복사본을 전달한다.

request에는 `version`, `binding_sha256`, `request_sha256`, `instructions`, `required_checks`, `writing_contract`, 원본·목적지 전체 `source_snapshots`, 실제 전체 `output_snapshots`, `snapshot_refs`, `source_units`, `placements`, `consolidation_groups`, `block_ledger`, `trace`가 있다. 문서 내용은 지시가 아닌 검토 데이터로 취급하도록 요구한다.

`snapshot_refs`의 각 항목은 `{side: "source"|"output", document_id, snapshot_id, version, sha256}`이다. request 전체 JSON의 Unicode 문자 수가 예산을 넘으면 `budget_exceeded`이며 모델에 일부만 보내지 않는다. 검토 창 분할·자동 재시도는 구현하지 않는다. 어댑터는 실제 모델의 토큰/컨텍스트 한계에 맞는 더 작은 문자 예산을 설정해야 한다.

응답 예시의 `reviews`에는 **모든 required_checks가 정확히 한 번씩** 들어가야 한다.

```json
{
  "request_sha256": "현재 요청의 해시",
  "reviews": [{
    "check_id": "CLAIM_FACTS",
    "judgment": "supported",
    "reason": "원본 주장과 실제 출력의 대응 및 문맥을 검토한 근거",
    "reviewed_refs": [{"side": "source", "document_id": "doc-guide", "snapshot_id": "...", "version": "1", "sha256": "..."}],
    "evidence": [{"side": "source", "document_id": "doc-guide", "snapshot_sha256": "...", "start": 0, "end": 4, "quote": "정확한 인용"}]
  }]
}
```

위 예시는 필드 형식만 보인다. 실제 `reviewed_refs`는 원본·목적지·출력의 **모든 참조**를 중복 없이 포함해야 하고, 각 검사에는 내용이 있는 모든 스냅샷의 유효 인용이 필요하다. 인용 범위는 UTF-8 바이트가 아닌 Unicode codepoint의 `[start, end)`다. quote·문서 ID·스냅샷 해시·정수 범위·판정 enum·검사 ID·중복·누락을 코드가 재검증한다. 판단은 `supported`, `contradicted`, `overstated`, `unresolved`뿐이다. 모델의 승인 필드는 오류다.

검사별 의미 판단 자체를 문자 검사로 증명할 수는 없다. 코드가 보장하는 것은 실제 전달한 전체 문맥, 응답 구조·참조·인용·범위의 정합성, 알려진 결정론적 위반과의 충돌 차단이다. 모델이 실제로 전체 문서를 읽었는지, 인용이 그 판단을 논리적으로 충분히 뒷받침하는지는 보장하지 않는다.

## 보고서와 실행 증거

의미 보고서는 `snapshot_refs`, `binding_sha256`, `structural_report_sha256`, 고정 `checks`와 검사별 `status/evidence/rule_ids/model_review`, `findings`, `overall_judgment`, `coverage`, `deterministic_audit.literal_pairs`, `execution`, `report_sha256`을 포함한다. 문자 비교에는 실제 원본/출력 인용과 문자값·수치·버전 토큰 일치 여부가 있고, 미해결 검사에는 `unresolved_reason`을 기록한다. 상태는 `supported/violated/unresolved`, 전체 판정은 `supported/contradicted/unresolved`, 게이트는 `REVIEW/FAIL`이다. 모델 위반은 `MODEL_REPORTED_SEMANTIC_VIOLATION`으로 문자 검사 위반과 구분한다.

`coverage.complete`는 모든 문서 참조·인용·검사와 비미해결 모델 검토가 있는지를 나타내며 문서 승인이나 모델 정확도를 뜻하지 않는다. 모델 미호출/실패/시간 초과/잘못된 응답/부분 검토/예산 초과는 완전 검토가 아니다. `execution`에는 내부 생성 `run_id`, 실제 요청/응답 해시, 상태, 예산, 시간 제한이 기록된다. 공급자 예외 내용은 노출하지 않는다.

입력 bundle·계약·analysis·org·preview·실제 candidate·목적지 **본문 전체**를 binding에 묶는다. caller가 제출한 해시 필드만 믿지 않는다. 보고서는 실행 경계에서 프로세스 내부 receipt에 보관되며 verifier는 현재 본문 binding, 구조 재계산 결과, 원본 receipt 전체를 대조한다. 재해시한 승인/검사 삭제/판정 위조와 다른 문서·이전 버전의 보고서를 거부한다. receipt가 없는 별도 프로세스의 JSON은 인증된 실행 증거로 재사용하지 못한다.

생성 시 `execution_evidence_matches_current_inputs`는 검토 직후 현재 입력 본문 binding을 다시 계산한 결과다. 검토 도중 입력이 변경되면 FAIL과 불완전 검토로 처리하고 유효한 receipt를 등록하지 않는다. `execution_evidence_matches_current_inputs: false`인 보고서는 입력을 원복해도 verifier가 거부하며 새 검증 실행이 필요하다. 그 뒤 현재 입력과 맞는지는 verifier의 같은 필드를 사용해야 한다. 검증기는 모델을 다시 호출하지 않는다. 프로세스 내부 실행 기록은 외부 호출자 인증·공급자 실행 증명·영속 서명이 아니다.

시간 제한은 daemon worker의 결과 대기를 끝낸다. 늦은 응답은 보고서/receipt를 변경하지 못하지만 Python 콜백 자체의 네트워크 작업을 강제 종료하지 못한다. 공급자 어댑터도 I/O 시간 제한과 취소를 구현해야 한다.

## 남은 한계와 2-B 연결

기본 분석은 원문 블록 목록이므로 암묵적 조건·귀속·대상 연결을 모두 추출하지 못한다. 문자 규칙은 한정된 한국어 표현과 토큰에 대한 보수적 탐지이며 범용 의미 동등성/모순 검증기가 아니다. 모델의 supported도 합의·정책 승인과 다르다. 큰 문서는 현재 전체 요청 예산을 넘으면 미해결이다. 실제 LLM 정확도·오탐률·미탐률은 측정하지 않았다.

2-B는 현재 원본/계약/후보 binding과 두 독립 보고서, 완전성·미해결·위반 목록, 현재 입력에 맞는 검증 증거를 소비할 수 있다. 추가로 신뢰 가능한 사람/정책 승인자와 승인 계약, 승인 대상 해시 고정, 만료/취소/변경 시 무효화, 영속 증거 인증, 실제 반영 시 원본 버전 재확인과 원자적 적용이 필요하다. 이번 API는 이 승인 실행 권한을 구현하거나 위임하지 않는다.

## 검증

```bash
python3 -m unittest discover -s experiments/full_document_control -p 'test_final_semantic_validator.py'
python3 -m unittest discover -s experiments/minimal_gate -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_analysis -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_ab -p 'test_*.py'
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'
git diff --check
```

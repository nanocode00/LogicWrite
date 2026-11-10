# 전체 문서 후보 파이프라인 통합

구현 출발점은 PR #14 병합 커밋 `8792bff`이며 이번 2-A 구현의 기준은 PR #16 병합 `ee3c270`이다. 실제 API·설계 차이·최신 회귀 수치는 [현재 실행 인터페이스](../../docs/data-model-and-interfaces.md#current-runtime-interfaces)를 참조한다. 기존 `pipeline.py`, `organization.py`, `expression.py`, `expression_validator.py`, `semantic_validator.py`의 승인 정책을 변경하지 않고 읽기 전용 **격리 후보 경로**를 추가했다. 파일 반영·승인된 단계 전환·최종 의미 승인 경로는 구현하지 않았다.

## 실행 경로와 범위

`Markdown + WritingContract → 기존 분석 조립/게이트 → Organization Preview → Expression Preview → 전체 후보 재구성 → 독립 최종 구조 검증 → 전체 출력 의미 검증 → 종합 감사/중단`

| 파일/API | 실제 역할 |
| --- | --- |
| `integration.markdown_bundle(text, contract)` | 원문 바이트를 UTF-8로 읽은 정확한 문자열과 SHA-256에 고정 |
| `integration.analyze_source(bundle, responses=None)` | 기존 추출 응답 조립기를 재사용. 응답이 없으면 블록 원문을 그대로 인용한 최소 정보 목록을 생성하며 목적·의존 관계는 미확정으로 기록 |
| `integration.run_pipeline(...)` | 상위 FAIL/STOPPED는 즉시 중단. REVIEW 아래서는 승인된 단계 진입 대신 격리된 후보만 계산 |
| `reconstruction.reconstruct_documents(bundle, analysis, org, preview, destination_snapshots=...)` | 원본 전체를 범위별로 유지하고 해석 가능한 수정·배치를 반영한 전체 스냅샷 또는 보류 Preview 반환 |
| `final_validator.validate_final_result(...)` | 원본·실제 출력·계획·범위 원장·trace를 대조. 생성기의 자기 평가나 계획 findings만으로 통과시키지 않음 |
| `final_validator.verify_final_report(...)` | 현재 입력으로 재검증해 고정 검사군·버전·결과 전체를 비교. 해시를 다시 계산한 허위 보고서도 거부 |
| `pipeline.validate_final_output(...)` / `verify_final_output_report(...)` | 구조 보고서와 [전체 출력 의미 보고서](FINAL_SEMANTICS.md)를 결합·검증. 기존 `final_report`는 구조 결과로 유지하고 `final_semantic_report`·`final_audit` 추가. supported도 REVIEW, 두 승인 필드는 false |
| `integration.RevisionController` | 원인 모듈 식별, 저장된 하위 산출물 무효화, 현재 입력 재검증, 안전한 중단. 자동 재시도는 수행하지 않음 |

기본 분석은 실제 파일에서 생성한 **원문 블록 목록**이지 일반적인 주장·관계의 의미 분석 모델이 아니다. 기존 `required_information`을 충족하지 못하거나 필수 조건 연결을 확립하지 못하면 기존 게이트가 실패하고 이후 후보 생성을 중단한다. 승인 조건을 맞추려고 요구사항이나 검사 결과를 바꾸지 않는다. 기존 추출기의 기록된 창별 응답을 `--response`로 제공할 수도 있으며 현재 입력·창 참조에 맞아야 한다.

## CLI

Python 표준 라이브러리만 사용한다. stdout JSON만 반환하며 저장/덮어쓰기/배포 옵션은 없다. REVIEW는 설계된 결과이므로 종료 코드 0, 실행/입력 오류 및 안전 중단은 2다.

```bash
python3 experiments/full_document_control/integration.py document.md writing-contract.json
python3 experiments/full_document_control/integration.py document.md writing-contract.json \
  --response window-response.json --operations expression-operations.json
```

실제 파일 검증 예시는 `docs/logicwrite-project-proposal.md`와 별도 검토 계약을 사용했다. 아래와 같은 계약을 임시 경로에 저장한 뒤 위 명령의 입력으로 전달할 수 있다. 기존 기획서·과제·평가 데이터를 수정하지 않는다.

```json
{
  "contract_id": "integration-contract", "version": "1", "document_type": "project_proposal",
  "audience": "개발자", "purpose": "프로젝트 기획 개요와 개발 범위를 검토한다.",
  "language": "ko", "register": "합니다체",
  "output_scopes": [{"scope_id": "guide", "document_id": "doc-guide"}],
  "required_information": [{"id": "project-name", "description": "프로젝트 이름",
    "expected_literal": "LogicWrite", "kind": "claim", "scope_id": "guide", "requires_condition_link": false}],
  "constraints": []
}
```

PR #15 당시 실행 기록(현행화 전 기획서): 원본 4,614바이트 불변, 전체 후보 문서 1개, 문체 변환 범위 10개. 스냅샷·전체 범위·보호 문자값·양방향 추적·문서 집합 검사는 passed, 배치 해석·표현 의미·승인은 unresolved, 최종 REVIEW였다. 이 결과는 기획서의 사실·의미가 모두 검증되었다는 평가가 아니다.

## 전체 문서 재구성 규칙

| 작업 | 지원과 보류 기준 |
| --- | --- |
| 표현 span 패치 | 원본 전체 문자열에 정확한 범위를 대체. 변경하지 않은 모든 문자·블록도 범위 원장에 남김 |
| 제한된 문체/압축/용어 | 기존 결정론적 생성 규칙으로 재확인 가능한 변경만 전체 후보에 반영. 의미 동일성 증명으로 취급하지 않고 최종 REVIEW 유지 |
| 기타 생성기 재작성 | Preview에서만 남기고 전체 후보에는 원문을 유지(`EXPRESSION_CHANGE_HELD`) |
| 겹치는 범위 | 동일 범위·동일 결과는 한 번만 반영하고 모든 단위를 추적. 상충 결과·부분 중첩 수정은 전체 후보로 만들지 않음. 수정 없는 중첩 범위는 정확한 위치로 추적 |
| 문서 내부 배치 | 완전한 독립 문단과 해석 가능한 기존 단위의 before/after 기준점, 또는 유일한 기존 제목 경로와 relative_order를 지원. 새 제목은 만들지 않음. 상충·순환 배치는 보류 |
| 보호 구조 | 제목·코드·표·인용 블록을 분해해 재작성/이동하지 않음. 원본 문맥상 수정 제외 정책은 Expression 검증기를 재사용 |
| 문서 간 MOVE | 원본의 완전한 독립 문단만 검증된 전체 목적지에 추가. 필수 조건도 실제 목적지에 보존돼야 함. 원본·목적지 전체를 하나의 ChangeSet으로 구성 |
| MOVE 경계 | 기존 목적지 내용은 자체 문서에 고정. 필요한 최소 개행만 추가. 미확정 코드 펜스·HTML 등 unsupported 구문이 있는 목적지로는 추가하지 않음 |
| 중복 통합 | 기존 검증기의 compatible 그룹에 속한 정확히 같은 독립 문단만 지정된 primary에 대응. secondary 원문 범위도 alias로 보존·추적. 다른 KEEP 발생 위치를 해당 그룹으로 지울 수 없음 |
| 제거/잠정 목적지/부분 블록 이동 | 독립적인 실제 제거 승인 실행기가 없거나 안전한 문서 구성을 확정할 수 없어 Preview/REVIEW로 보류 |

원본·목적지 스냅샷은 `snapshot_id`, `document_id`, `version`, `coverage: complete`, `media_type: text/markdown`, 실제 content·sha256이 필요하다. 원본 및 `destination_snapshots`의 ID는 Writing Contract `output_scopes`의 구체적인 `document_id` 또는 `target.document_id`에 선언되어야 한다. `destination_role`만으로 문서 ID를 만들지 않는다. 미선언 입력은 Reconstruction에서 오류와 빈 출력 Preview로 반환하고, Final Validator는 수집기와 별도로 현재 계약의 입력/출력 ID를 대조해 FAIL로 처리한다. 스냅샷 문맥이 불완전해도 확정된 범위 위반을 REVIEW로 낮추지 않는다. 목적지의 불완전 발췌를 전체 문서로 간주하지 않는다. `destination_snapshots`는 명시적 출력 대상이며 분석용 참고자료 컬렉션이 아니다. `source_material` 등 참고 문맥이 자동으로 출력으로 복사되지 않는다. 선언된 목적지를 읽었다고 실제 텍스트 수정을 요구하지는 않으며, 변경 없는 문서는 KEEP으로 원장을 유지한다. 이 구분은 새 참고 문서 로더나 검색 기능을 도입하지 않는다. 후보 스냅샷 ID·버전은 원본 버전과 내용 해시에서 결정되므로 동일 입력의 전체 후보 텍스트·다이제스트는 반복 실행에서도 같다. Expression 실행 기록 ID는 매 실행 달라지므로 전체 감사 JSON의 바이트 동일성까지 보장하지 않는다.

## RevisionResult와 최종 검사

새 재구성 결과 버전은 `full-document-reconstruction-v1`이다. 기존 Expression v1 Preview는 별도 객체로 유지하며 기존 검증기를 그대로 실행한다.

- 공통 필드: `organization_ref`, `expression_plan`, `output_snapshots`, `preview_fragments`, `change_set`, `trace`, `findings`, `delivery_state`.
- `candidate`: 모든 입력 원본/목적지의 전체 output_snapshots를 생성했으며 preview_fragments는 비어 있음. **최종 승인과 다름**.
- `preview`: 전체 재구성이 보류돼 output_snapshots는 비어 있음. 부분 문서 묶음을 전달 후보처럼 표시하지 않음.
- `block_ledger`/`change_set`: 모든 원본 구간과 출력 구간, 처리 방식 및 통합 alias의 근거를 기록. 출처가 없는 것은 독립 검증 가능한 MOVE 경계의 최소 개행뿐임.
- `trace`: 모든 단위·요소 ID와 원본 span 및 실제 출력의 정확한 span·문자열·다이제스트를 연결. 같은 문장의 다른 출현 위치로 바꾸는 것도 차단.
- 추가 참조: `analysis_ref`, `expression_preview_sha256`, `source_refs`, `revision_sha256`. 해시 자체는 실행자·의미 평가자의 인증이 아님.

| 고정 검사 ID | 실제 검증 범위 |
| --- | --- |
| SNAPSHOT_INTEGRITY | 현재 원본·목적지·후보의 식별/버전/다이제스트, 상위 참조와 결과 버전 |
| FULL_COVERAGE | 모든 원본·출력 구간의 빠짐/중복/새 실질 텍스트, 모든 문서의 원자적 존재 |
| PROTECTED_INFORMATION | 실제 결과와 허용된 원문 패치 대조. 보호 정보 손실 및 Markdown 구문을 바꾸는 임의 공백 차단 |
| ORGANIZATION_FIDELITY | 원본 블록/조각 순서, 명시 기준점/기존 섹션, 단위의 실제 문서 및 통합 구성원/primary 위치 |
| EXPRESSION_FIDELITY | 기존 독립 Expression 검사와 실제 결과 연결. 전체 문서 의미 검토는 not_run/unresolved |
| BIDIRECTIONAL_TRACE | 원본을 덮는 원장과 전체 출력을 덮는 원장, unit/element 목록, 길이 변화까지 반영한 정확한 전후 좌표 |
| CROSS_DOCUMENT_INTEGRITY | 계약에 선언된 구체적 입력/출력 문서 ID, 모든 문서 동시 존재, 실제 MOVE 배치, 목적지 기존 내용 유지, 원본 관계를 통한 조건 보존, 안전한 추가 경계 |
| APPROVAL_BOUNDARY | 허위 PASS·전달 승인 차단. 고정 검사 누락·변조·오래된 보고서는 재검증 비교로 거부 |

구조 검사 `passed`와 최종 `gate_state: PASS`는 구별된다. 필수 의미 검토·사람 승인 절차가 없어 **이 구현에서 최종 PASS/전달 승인은 없다**. 모든 후보는 REVIEW 또는 확인된 위반에 따른 FAIL이다. 검사를 실행할 전체 문서가 없으면 해당 검사를 unresolved로 남긴다. 제어기는 실행을 중단한 경우 STOPPED와 last_gate_state·책임 모듈·무효화 대상을 별도로 반환한다.

## 실제 인터페이스 차이와 남은 한계

- 기존 분석 입력 검증기는 단일 concrete scope만 허용한다. 파일 E2E는 이 계약을 그대로 준수한다. 다중 문서 재구성 API는 이미 바인딩된 AnalysisResult/OrganizationPlan과 전체 목적지 스냅샷으로 동작하지만, 다중 scope 파일의 분석부터 승인까지 자동 수행하는 경로는 없다. 기존 승인 경로를 우회하는 정식 실행으로 표시하지 않는다.
- 기존 OrganizationPlan의 추상 section_path는 실제 제목으로 해석되지 않을 수 있다. 이 경우 원문 배치를 유지하고 ORGANIZATION_FIDELITY를 unresolved로 기록한다. 부분 블록 구조 편집·새 제목·소스 없는 새 문서는 생성하지 않는다.
- 목적지 기존 내용은 그대로 보존하며 재분석/의미 통합하지 않는다. 전체 문서의 사실성·상충 주장·조건의 실제 문맥·의미 동일성은 [2-A 선택적 모델 감사](FINAL_SEMANTICS.md) 대상이지만 진실이나 정확도를 증명하지 않는다. 실제 LLM 평가는 수행하지 않았으며 사람/정책 최종 승인은 2-B에 남긴다.
- 범위 원장은 검증 가능한 문자열/배치 대응이지 일반적인 의미 보존 증명이 아니다. Markdown 파서는 기존 지원 범위(줄 단위 제목·문단·목록·펜스 코드·표·인용 등)에 한정된다.
- 검증 실패의 진단·책임 모듈 식별·하위 산출물 무효화·새 입력 재검증까지 지원한다. 자동 수정/재시도·LangGraph·RAG·파일 반영·배포는 없다.

검증 명령과 최신 수치는 [현재 실행 인터페이스](../../docs/data-model-and-interfaces.md#현행화-근거와-검증), 다음 작업 인수인계는 [HANDOFF](HANDOFF.md)를 참조한다. 기존 골드셋·평가 자료·실제 LLM 의미 평가 결과는 변경하지 않는다.

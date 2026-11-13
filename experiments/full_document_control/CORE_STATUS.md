# Core 구현 점검 및 구조 보완

점검일: 2026-11-13. 기준: 최신 `origin/main`을 fetch한 `879d15b8fa267010217d9310b72d1066fda74f99`.
실제 구현과 합성 회귀 테스트를 점검했다. Golden Set, 수집 중인 T1~T9, 기존 29건의 정답·평가 자료는 변경하거나 튜닝에 사용하지 않았다.
목표 기능은 [아키텍처](../../docs/architecture.md), [요구사항](../../docs/requirements.md), [프로젝트 기획](../../docs/project-proposal.md)과 대조했다.
아래 구현 범위는 정식 제품 완성이나 의미 품질 수용을 뜻하지 않는다.

## 모듈별 입력·출력·검증·미완성 경계

| 모듈 / 구현 위치 | 실제 입력 → 출력 | 구현 및 검증 | 목표 대비 미구현 / 검증 부족 |
| --- | --- | --- | --- |
| Information Extraction & Analysis / `pipeline.py`, `semantic_validator.py` | 단일 Markdown 전체 스냅샷 + Writing Contract + 창별 추출 응답 → blocks/windows/units/elements/relations/assessment, 원문 spans 및 해시, 분석 보고서 | 블록 전체 분할·창 조립·정확 인용·출처 범위·필수 정보·보호 조건·관계 감사, 선택적 모델 의미 검토. `ExecutionController`는 추출 단계의 제한 재시도 지원 | 계약/목적 복구 Resolver, 일반 목적 적합성·중요도 품질 보장, 복수 문서 공동 추출은 없음. `integration.analyze_source` 기본값은 원문 블록 목록이며 의미 분석을 실행하지 않음. 단일 concrete output scope 제한 |
| Information Organization / `organization.py` | 분석 + 계약 + 후보 액션/통합 그룹 + 선택적 목적지 스냅샷 → placements/actions/destination_reviews/consolidation_groups/findings | 정보 단위 추적, 필수 정보 보존, 조건 의존성, 출력 범위, 목적지 내용·버전·해시, 통합 호환성 및 승인 위조를 독립 재검사 | 계획의 REMOVE/통합 가능성이 실행 권한은 아님. 목적지 독자·과업에 따른 의미 적합성, 일반 문맥 기반 순서, 검색·새 문서 생성은 미완성. `verified_context`는 내용 문맥의 존재이며 목적 적합성의 증명이 아님 |
| Expression Refinement / `expression.py`, `expression_validator.py` | 분석 + OrganizationPlan + 계약 제약 + generator/operations → expression_plan, 원문 범위별 Preview, generation receipt/trace | KEEP/REVISE/COMPRESS, 제한된 한국어 종결어미·용어·반복 압축, 보호 블록 제외, 보호 문자값·조건·추적·상위 계획·실행 receipt 검사 | 범용 한국어 윤문/문법/의미 보존 보장 없음. 외부 생성기의 의미 재작성은 Preview에 있어도 Reconstruction에서 결정론적으로 재현되지 않으면 원문 유지 |
| Reconstruction / `reconstruction.py` | 분석/계획/Preview + 전체 원본·목적지 → 전체 후보 snapshots, ledger/change_set, source↔output trace, 별도 D/Q 관측 | 제한된 span 패치, 독립 문단 배치, append MOVE, 정확 동일 문단 alias 통합. 모든 문서 원자적 묶음과 보수적 보류 | REMOVE 실행기 없음. 일반 의미 통합, 부분 블록 이동, 새 제목/문서, 목적지 내부 배치·기존 내용 편집 없음. 하위 API 지원을 통합 실행 지원으로 간주하면 안 됨 |
| Validation Gate / 분석·Organization·Expression 검증기 + `final_validator.py` | 현재 계약·스냅샷·상위 산출물·실제 전체 후보 → 검사별 passed/violated/unresolved, findings/report digest | 범위 원장·순서·추적·출력 문서 집합·목적지 기존 내용·허용 패치·승인 경계를 독립 대조. 생략된 필수 검사/낡은 보고서 거부 | 구조적 passed는 의미적 PASS가 아님. source ledger의 보존만으로 목적 적합성·사실성·가독성 증명 불가 |
| Final Semantic Validator / `final_semantic_validator.py`, `pipeline.validate_final_output` | 실제 원본/목적지/출력 전체 + 계약 + 선택적 reviewer → structural/semantic reports, 실행 receipt 및 final_audit | 사실·수량/범위·극성/조건·추가/누락·모순·이동/통합·출처의 7개 검사. 문자 증거 기반 위반, 전체 문맥 모델 감사, 범위/시간 한도·응답 및 근거 검증 | 모델 결과 supported는 독립 의미 정답이나 승인 아님. 모델 없거나 문맥/검사 불완전하면 unresolved. receipt는 실행 출처이지 판단 진실성의 증명 아님. 실제 의미 품질 평가는 이번 작업에서 수행하지 않음 |
| 최종 승인 / `final_approval.py` | 최신 final_audit + 명시적 사람 기록 + 독립 근거 출처 → approval_report | 계약·현재 감사·근거/정책 상태 및 테스트 출처 경계 검증 | 실제 승인 발급 비활성. 테스트 정책 성공도 전달 승인/PASS를 발급하지 않음. 이번 변경으로 정책/조건을 변경하지 않음 |
| Revision Controller / `integration.RevisionController` | findings 또는 현재 전체 산출물 → 책임 모듈·하위 무효화 목록·STOPPED 또는 새 감사 | 진단/무효화/revalidate와 opt-in `repair()` 연결. 혼합 오류 시 Analysis → Organization → Expression → Reconstruction 순서로 무효화 | `stop()`은 광범위 규칙명 기반 진단이며 RepairLoop의 명시적 allowlist와 다름. 일반 원인 추론이나 모든 오류 자동 수정은 아님 |
| RepairLoop / `repair_loop.py` | bundle + 4단계 artifacts + 책임별 adapter + 목적지/reviewer/예산 → 최신 artifacts/audit, attempts/progress/종료 사유 | 명시적 책임 allowlist·상위 우선, adapter는 candidate만 반환. 상위 변경 시 하위 재생성·감사/승인 무효화·현재 전체 재검증. 반복/퇴행/새 unresolved/입력 변경/시간 제한에서 중지. 예외 시 낡은 감사 재사용 방지 | 모든 규칙의 adapter가 기본 제공되지 않음. 기본 결정론적 Expression repair만 제공. unknown/trust 오류는 중지. 콜백 대기 timeout은 외부 I/O 취소가 아니며 host adapter 책임. 다중 scope는 분석 게이트에서 막힘 |
| 통합 경로 / `integration.py`, `repair_loop.run_repair_pipeline` | 단일 파일/계약 또는 bundle/기존 분석 → 격리 후보 + 전체 감사 + 승인 보고서; 별도 opt-in repair | 파일 읽기 전용, 기본 원문 목록 또는 기록 추출 응답, Organization → Expression → Reconstruction → 최종 구조/의미/승인 검증. 승인된 단계 전환을 합성하지 않음 | 다중 문서 분석부터 최종 후보까지의 E2E 없음. CLI에 목적지/repair 옵션 없음. 통합 기본 Organization 호출은 목적지 인자를 전달하지 않지만 단일 scope 선행 제한도 있어 인자 전달만으로 해결되지 않음. 파일 반영·배포·정식 SDK/RAG/LangGraph 없음 |

README/INTEGRATION/요구사항의 과거 기준 문구 중 “자동 수정 루프 없음”, “최종 의미 검토 없음”은 현재 opt-in RepairLoop/Final Semantic Validator보다 오래된 설명이다. 현재 실행 지원과 완료 기준은 위 표를 기준으로 구별한다. 사람 승인·품질 수용 미완료라는 경계는 유지된다.

## Organization 계획과 실제 실행의 차이

| 편집 | 계획 범위 | 안전한 실제 실행 조건 / 보류 |
| --- | --- | --- |
| KEEP 내부 배치 | section_path, relative_order, before/after anchor | 원본의 완전한 독립 문단, 유일한 기존 제목 또는 기존 독립 문단 기준점, 상충/순환 없음. 미해결 제목은 원문 유지 + unresolved. 부분 블록/새 제목은 지원하지 않음 |
| MOVE | 구체적 목적지/임시 역할, 목적지 확인, 필수 조건 동반 계획 | 계약에 선언된 완전한 목적지, 정확한 버전·해시·전체 Markdown, 독립 문단, 공유 블록의 보존 의무와 필수 조건 일관성, 안전한 추가 경계, 원본·목적지 동시 추적. **목적지 끝에 append만 지원**. 비어 있지 않은 section_path/앵커/before·after 요청은 이번 P0부터 Preview/REVIEW |
| REMOVE | 계약 필수 정보에 묶이지 않은 omission candidate 계획 가능 | omission candidate는 삭제 승인 근거가 아님. `REMOVAL_AUTHORIZATION_UNAVAILABLE`로 전체 재구성 보류. 최종 원장/추적 검증 역시 임의 삭제를 허용하지 않음. 제거 승인·보존 의무·다른 정보 단위 영향 계약 설계가 선행되어야 함 |
| CONSOLIDATE | 정보 요소/조건/수치/버전/범위 호환 그룹, 선택적 의미 검토 | compatible·unblocked 그룹, 정확히 같은 독립 문단, 지정된 primary, 출력 텍스트 동일, 이동과 중첩 없음, secondary도 alias 추적. 별도 KEEP 출현을 지우면 독립 최종 검증 실패. 일반 의역 통합은 보류 |
| REVISE/COMPRESS | generator가 임의 표현 제안 가능 | 기존 결정론적 generator로 정확히 재현되는 변경만 적용. 의미 재작성은 `EXPRESSION_CHANGE_HELD`로 원문 유지. 보호 정보 손실은 검증 실패 |

## 재현된 구조 결함과 P0 수정

| 결함 | 실패 재현 → 수정 → 회귀 |
| --- | --- |
| MOVE의 section/anchor 의도를 무시해 append 후보 생성; 독립 최종 검사도 같은 맹점 | `test_explicit_move_placement_is_held`, `test_final_validator_rejects_ignored_move_placement`가 기존 candidate/검사 passed를 재현. 미지원 배치 요청은 `MOVE_PLACEMENT_UNSUPPORTED`로 빈 전체 출력 Preview. 그 의도를 무시한 후보를 해시 재계산해 제출하면 독립 ORGANIZATION_FIDELITY violated. 기본 계획은 가짜 `Transferred Information` 제목 대신 빈 section_path로 실제 append 범위를 명시 |
| 여러 단계의 오류가 함께 있으면 RevisionController가 Organization부터 골라 Analysis 산출물을 남김 | `test_mixed_failures_invalidate_from_earliest_module`로 재현. Analysis를 먼저 진단해 모든 하위 결과와 구조/의미 감사·승인 보고서 제거. Organization/Expression 혼합은 Organization부터 제거. RepairLoop의 기존 allowlist/승인 정책은 변경하지 않음 |
| 계획·Preview·원장에 D와 Q가 흩어져 요청 라벨을 적용 결과로 오해 가능 | 별도 필드 부재를 재현한 테스트 후 `execution_observations` 추가. REVISE 요청/변경 없음, COMPRESS/문자 변경, 의미 재작성 보류/원문 KEEP, MOVE, CONSOLIDATE, REMOVE/배치 보류를 각기 검증 |

## D와 Q 산출물 계약

`reconstruct_documents` 결과(`run_pipeline.revision_result`, RepairLoop의 `artifacts.reconstruction`)에 `execution_observations`가 추가된다. 구조 버전 v1은 유지하고 진단을 부가한다.

- `version: execution-observations-v1`, `advisory_only: true`.
- `units[].decision`: 분석 `assessment`, 전체 `placement`(근거 포함), 요청 `expression_operation`을 복사한다. 이것이 D 관측이며 옳은 의사결정이라는 평가가 아니다.
- `units[].observation`: 실제 trace의 `output_spans`, 겹치는 원장 행의 `treatments`, 원문/실제 출력 인용의 `text_changed`를 기록한다. 문서 이동은 text_changed=false일 수 있으며 MOVE 처리는 따로 관측한다.
- 전체 후보가 없으면 `state: not_materialized`, 빈 spans/treatments, text_changed=null. 부분 적용 성공을 주장하지 않는다. 입력/Preview 검증 자체가 실패하면 units는 빈 목록일 수 있다.
- 전체 Reconstruction digest에 포함되지만 **독립 검증의 입력 증거나 승인 조건으로 사용하지 않는다**. 실제 Q의 의미 품질은 final_audit 및 별도 사람 평가 대상으로 남는다. 임의 후보/adapter가 이 필드를 위조해도 승인 근거가 되지 않는다.
- 단일 분석 문서의 단위 관측이며 목적지 기존 문서의 새 분석 단위를 만들어내지 않는다. 실행 기록 ID 변화와 실제 본문 변화는 구별한다.

## 구조 문제와 의미 품질 문제의 구분 및 우선순위

| 우선순위 | 유형 | 후속 작업 / 수용 증거 |
| --- | --- | --- |
| P0 이번 완료 | 구조 | 미지원 MOVE 배치 보류 + 독립 최종 거부, 혼합 오류 상위 우선 무효화, 별도 D/Q 관측. 합성 재현·회귀로 판정 가능 |
| P1 | 구조/계약 | 다중 문서 입력 계약·분석/창·단위 identity·scope 바인딩을 먼저 설계한 뒤 목적지 인자 전달·CLI·RepairLoop E2E 연결. 현재 단일 scope 실패를 우회하거나 분석 게이트를 완화하지 않음. 여러 전체 문서와 변화하는 목적지의 E2E 회귀 필요 |
| P1 | 구조/실행 | 목적지 내부 section/anchor/relative_order, 여러 MOVE 사이의 순서, 목적지 기존 문단/공유 단위와의 충돌 해석. 현재 append만 지원하므로 먼저 적용 계약/독립 검증/Markdown 경계를 정하고 작은 패치로 확장 |
| P1 | 구조/제어 | RevisionController 진단과 RepairLoop allowlist의 정합성, 모든 규칙 소유권·unknown 처리의 명시화, 조직/분석 adapter의 계약, 재생성 시 호출자 작업/표현 옵션 보존 정책. 현재 fail-closed 경계를 유지하며 오류 종류별 재현 추가 |
| P1 | 정책/계약 선행 | REMOVE의 승인된 생략 의무·문서별 노출·증거 보존 및 공유 unit 의무 정의. 기존 정책 변경 승인을 받기 전에는 실행 지원 확장하지 않음 |
| P2 | 의미 품질 | 목적/독자 적합성, relevance/importance/보존 판단, 조건이 실제 읽히는지, 문서 간 주장 충돌·일반 통합/의역·문체 품질. 합성 구조 테스트로 정답을 주장할 수 없음. 별도 사람 검토·수집 데이터와 독립 평가가 필요 |
| P2 | 운영/검증 | 정식 결과 스키마, 영속 실행 receipt·재시작 검증, provider I/O 취소, 대형 문서 예산/구문 지원, 정식 SDK/CLI·파일 반영 경계. 실제 승인 발급은 이번 범위 밖 |

## 검증

수정 전 Core 362 tests 통과. 신규 9 tests 중 기존 경계 확인 1개는 원래 통과하며, 나머지 기능은 수정 전 assertion 실패를 확인한 뒤 구현했다. 기존 회귀/승인/RepairLoop 테스트는 삭제하거나 기대 조건을 낮추지 않았다.

```bash
python3 -m unittest discover -s experiments/full_document_control -p 'test_*.py'
python3 -m unittest discover -s experiments/minimal_gate -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_analysis -p 'test_*.py'
python3 -m unittest discover -s experiments/extraction_ab -p 'test_*.py'
python3 experiments/full_document_control/repair_example.py
git diff --check
git diff --name-only 879d15b -- evaluation/
```

로컬 결과: Core 371 + minimal_gate 31 + extraction_analysis 27 + extraction_ab 17 = **446 tests 통과**. `repair_example.py`는 1회 복구 후 REVIEW / VALIDATION_INCOMPLETE, 두 승인 플래그 false를 유지했다. 별도 읽기 전용 코드 리뷰는 지적 사항 없음, 관련 67 tests 통과를 확인했다. `git diff --check` 통과, evaluation 변경 목록은 비어 있다. 로컬 회귀는 외부 모델의 의미 품질, 홀드아웃 점수, 원격 CI, 실제 승인/배포 검증과 구별한다.

### PR #37 실제 병합 후 재검증

PR #37이 실제 main `6be0e615c5c56e7cb084596918b50e3438da0d03`으로 병합된 뒤 이를 이 PR 브랜치에 병합해 충돌 없이 재검증했다. 공식 명령 `python3 tools/evidence_validation/run.py --output /tmp/logicwrite-pr33-final.json` 결과는 **731 tests PASS**(역사 평가 244 + 현재 Core 446 + 현재 소비자 22 + 경계 19), failures/errors/skip/expected failures/unexpected successes 모두 0이다. 과거 보존 검증 실패 7묶음도 고정 snapshot에서 전부 실행했다. 기존 임시 결합 728건보다 3건 늘어난 것은 #37 검수에서 추가한 skip/expected failure/`tests/` 수집 회귀다.

`repair_example.py`는 승인·단계 전환 false 및 REVIEW를 유지한다. Golden Set/fixture/사람 판단·승인 정책은 기준 main과 바이트 동일하며 `git diff --check` 통과다. 원격 Actions workflow는 0개여서 위 결과는 로컬 검증이다. 기존 직접 역사 검증기는 과거 snapshot용이며 공식 전체 명령은 저장소 README와 `tools/evidence_validation/README.md`에 안내한다.

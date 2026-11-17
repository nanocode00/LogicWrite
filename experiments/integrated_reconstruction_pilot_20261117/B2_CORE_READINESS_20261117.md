# LogicWrite B2 준비도 점검 및 최소 실행 계획

기준: 2026-11-17 / PR #36 `eval/integrated-reconstruction-20261113` / 점검 시 head `b00a3a84197dc829496b3aa5222deafe8365ff05`

**판정: B2 전체 문서군 재구성 실행은 아직 불가.** 기존 Core의 일부 검증·재구성 부품은 재사용할 수 있지만, IR-001~003을 처음부터 끝까지 처리할 다중 문서·문서별 권한·범용 구조 변경 계약이 연결되어 있지 않다. 이 문서는 **코드·저장된 원본·골드·모델 호출을 변경하지 않은 정적 코드/기록 점검**이다. 로컬 통합 테스트나 실모델 B2 실행은 수행하지 않았다.

## 1. 근거 및 현재 인터페이스

- `evaluation/integrated_reconstruction/inputs/IR-001.json`: edit 2건 + read_only 5건; IR-002: edit 2 + read_only 2; IR-003: format_only 1 + read_only 2. `FORMAT.md`는 변경 권한과 제출 범위를 구분한다.
- `experiments/integrated_reconstruction_pilot_20261117/qwen-comparison-20261117/REPORT.md`: 같은 Qwen/DeepInfra 조건에서 B0/B1 세 쌍은 전송·전체 후보 반환에 성공했으나, IR-001/B1 과잉 보류, IR-002 양쪽 ops 안전 조건 누락, IR-003/B1 내용성 어미 변경을 관측했다. AI 평가 초안이지 사람 최종 판정은 아니다.
- `experiments/full_document_control/pipeline.py:validate_input_bundle`: `output_scopes` **정확히 1개**, `document_snapshot` 1개, 명시된 contract를 요구한다. `documents[].access` 같은 권한 종류를 받지 않는다. `analyze_source`의 기본 분석은 원문 블록 목록이다.
- `experiments/full_document_control/integration.py:run_pipeline`: 단일 분석→Organization→Expression→Reconstruction→구조/의미 감사의 **격리 후보** 경로. 승인된 다음 단계 진입/배포가 아니다. `integration.main`의 파일 CLI도 단일 Markdown/contract 중심이다.
- `experiments/full_document_control/organization.py`, `reconstruction.py`: 목적지 스냅샷 검증, 문단 단위 배치 및 **목적지 끝 append MOVE**, 제한된 동일 문단 CONSOLIDATE·결정론적 REVISE 가능. 범용 삭제·요약/의역 통합·새 문서/제목·목적지 내부 복잡한 배치는 지원하지 않는다.
- `experiments/full_document_control/final_validator.py`: 입력/계획/전체 후보/원장/trace의 독립 구조 검증. **IR별 access 정책을 입력으로 직접 받는 검증기가 아니다.** 구조 검사 통과는 실제 의미 보존 또는 권한 준수를 자동 보장하지 않는다.
- `experiments/full_document_control/final_semantic_validator.py`: 7종 전체 결과 의미 검토와 `reviewer` 콜백이 있다. `evaluate_snapshot_pair`는 외부에서 제공한 복수 완본 source/candidate pair도 받지만 lineage/실행 receipt 없이 **advisory 검토만** 하며 결과를 생성하지 않는다. reviewer 미실행/미완전이면 unresolved다.
- `experiments/full_document_control/source_candidate_adapter.py`: SP 형식과 명시적 전체 스냅샷/출처/contract에 한정된 평가용 bridge. IR 입력에 그대로 연결하거나 기존 Qwen 후보를 B2 생성물로 간주할 수 없다.
- `experiments/full_document_control/CORE_STATUS.md`: 복수 문서 E2E, 사용자 목적 복구, 일반 의미 재구성·승인·파일 적용이 미완료라고 명시한다.

## 2. Qwen 실패 유형별 Core 지원 매핑

| 발견된 결함 | 재사용 가능한 기존 부품 | B2에 빠진 계약/기능 | 초기 검증 및 실패 시 처리 |
| --- | --- | --- | --- |
| **IR-003/B1: format_only에서 ‘실패다.’→‘실패.’** | 원본 SHA/정확 인용/구조 감사·원문 보존; 전체 후보 스냅샷 비교 | 문서 ID별 `read_only/edit/format_only` 매핑과 변경 diff 정책. 표현 Preview 허용이 format_only 허용을 뜻하지 않음 | 전체 문서별 source→candidate 비교. read_only는 변경 금지; format_only는 문자·단어 변경을 자동 승인하지 않음. 미정의 서식 변환은 REVIEW, 명확한 내용 변경은 FAIL. 무수정 원본은 허용 |
| **IR-002 양쪽: ops에서 500건 초과 중단 / 당직 확인 전 재개 금지 누락** | 필수 정보·조건 링크 검사, 전체 의미 검토의 ADDITIONS_OMISSIONS/POLARITY_CONDITIONS, 출처 참조 | 독자 과업별 **현지 문서에 필요한** 안전 조건 및 출처/적용일 계약, 문서군 전체 추적·누락 검증 | 운영자가 사용할 ops 후보에서 중단·재개 조건 확인. design/ADR에 존재한다는 이유로 ops 누락을 면제하지 않되 모든 반복을 강제하지 않음. 누락이면 FAIL/REVIEW. 모델의 final_checks는 증거로 신뢰하지 않음 |
| **IR-001/B0/B1: 후원 정책 충돌 누락, 독립 개선과 보류를 혼동** | contradictions 의미 검토, 보존 후보·조직 계획, 분석 미확정/REVIEW 경계 | 근거 위상·상충 정책·결정 권한 명시, 미확정 범위에 한정한 HITL, 독립 작업을 보류 없이 진행하는 계획 | 모순을 근거와 함께 질문. 정책 확정·무단 삭제 금지. 사용 안내의 설치→실행 배치는 다른 확인과 독립하여 개선 가능한지 별도 판단. 과잉 보류를 ‘안전 성공’으로 집계하지 않음 |
| **IR-002/003: 모델 자체 검증이 누락·권한 위반을 통과 주장** | 입력/실제 결과를 독립 재검증하는 final_validator 및 7-check reviewer 계약 | 자유 서술 `final_checks`를 실제 문서와 대조하는 검증 항목·근거 연결, 의미 판단의 별도 평가자/사람 판단 | 자체 검증은 참고 주장. 원문·후보·권한·필수 조건으로 별도 재검사; 불일치 기록. 검증기/모델의 supported도 사람 승인 또는 최종 PASS가 아님 |

**현재 즉시 가능한 일:** 동결된 Qwen 출력과 원문을 입력만으로 읽어 제한적인 후보/출처 일치·무수정 여부를 감사하거나, 별도 `evaluate_snapshot_pair`에서 **검토 요청을 준비**하는 것. 이는 `B2_advisory_only` 또는 `validator_shadow`로 표시한다. 모델 검토 없이 일반 사실·모순 판단을 성공으로 기록할 수 없다.

**현재 불가능한 일:** 위 세 문서군 전체를 Core가 읽고 목적을 판단하여 후보를 자체 생성하고 문서별 권한을 강제한 결과를 `B2_full`로 비교하는 것. 임의로 문서 하나씩 분리 실행하거나 B0/B1 후보를 Core에 넣고 B2가 생성했다고 표시해서는 안 된다.

## 3. B2 최소 구현 순서와 단계별 수용 조건

### G0 — 오프라인 준비도·계약 경계 고정 (Core 변경 없이 가능)
1. IR v1 `inputs`와 Qwen B0/B1 `candidate.json`의 원문·응답·설정·해시를 읽기 전용으로 고정한다. `answers/`, `reference_outputs/`, `reviews/`는 모델/생성기로 전달 금지.
2. Core 단일-scope 호출 실패(다중 output scopes를 현재 거부)와 별도 외부 source-candidate 검토 가능 범위를 각각 **실제 테스트로 재현**한다. IR→SP 스키마 직접 전환을 가장하지 않는다.
3. 출력: 지원 기능/차단 사유/상위 입력 mapping 초안. 실제 모델 호출 0회. 이 단계의 결과는 B2 점수 분모에 넣지 않는다.

### G1 — 복수 문서 및 문서별 권한 계약 (가장 먼저 필요)
1. 입력 `documents`의 ID·role·authority·access·complete/partial·sha와 작업 요청/독자·목적/읽기 전용 근거를 **새 버전의 Core 문서군 계약**으로 수용한다.
2. 다중 `output_scopes`, 출처 단위·동일 문서/문서 간 identity, 수정 대상 전체 문서 반환, 읽기 전용 근거의 불변을 검증한다. IR v2 불완전 자료는 별도 설계까지 미지원/REVIEW 처리.
3. 계약 생성 시 사례 정답, 예상 문구, 검수 Q/F ID를 주입하지 않는다. 목적 추론·미확정 가정·사람 권한 확인을 별도로 기록.
4. 테스트: IR-001(7문서), IR-002(4문서), IR-003(3문서) 수용, 문서 누락/중복/해시 변조/권한 없는 추가/읽기 전용 변경/다중scope 오류 탐지. 기존 단일 문서 회귀 보존.

### G2 — 문서군 분석·계획·제한된 실행
1. 전체 자료를 의미 분석할 수 있게 공동 출처·시점·근거 위상을 연결한다. 불명 출처/정책 충돌은 임의 확정 대신 HITL.
2. 독립적으로 가능한 배치·보존·최소 서식을 실행하는 오케스트레이터와 미지원 MOVE/REMOVE/의역/새 문서 범위 보류를 분리한다. 단일 문서 경로를 여러 번 호출한 것을 문서군 전체 결과로 오인하지 않는다.
3. 동결 후보와 실행 trace/원본-출력 문서 ID/byte diff/요청 해시 기록. 전체 결과가 없으면 실패/부분 보류로 기록하고 Q 완료 점수 만들지 않음.

### G3 — 독립 검사·부분 HITL·B2 연결
1. post-output 검증기는 `read_only` 완전 불변, `format_only` 어휘 변경 거부, `edit` 권한 내 변경, 링크/코드·수치·상태·정책 근거, 대상 독자의 필수 현지 조건을 확인한다. 임의 문장 의미 동일성은 사람/모델 검토.
2. 생성기의 `final_checks`를 독립 증거로 사용하지 않는다. 구조 pass, 의미 unresolved, 사람 REVIEW, 실행 STOPPED를 구분한다.
3. IR-003 무수정은 합법적 전체 후보일 수 있으며, 명확한 승인/공개 범위 질문 부족은 별도 Q로 평정한다. 과잉 전체 보류와 정당한 부분 보류를 구분한다.
4. 유한 수정 루프가 검증 결과를 변경하더라도 새 출력·출처를 재검증하며, 실패하거나 미지원이면 fail-closed.

### G4 — 실제 B2 파일럿 (별도 사용자 승인 후)
1. G1~G3의 오프라인 red→green 회귀 및 Core 전체 검증 결과를 보고한 뒤에만 실행한다.
2. B2는 LogicWrite 파이프라인이 **직접 생성한** IR-001~003 전체 문서 후보로만 정의한다. B0/B1 Qwen과 같은 입력, 모델/provider/버전·비교 예산을 명시하고 **파이프라인 모든 하위 모델 호출의 총 비용·토큰·시간**을 기록한다. 골드/평가표는 생성기와 격리.
3. 요청별 지출 예산, 키 lifetime 한도, 전체 누적 한도, 실패 시 중단·재시도 금지, provider fallback 금지를 신설한 B2 runner에서 강제한다. 이번 문서에서는 키·원장·실행기를 변경하지 않는다.
4. D는 편집 전에 외부 기록이 실제로 없으면 `unobserved`; Q는 편집 대상 모든 문서의 전체 후보/실제 바이트·허용된 무수정, F는 위반 별도 기록. B2는 검토 성공/실행 성공/사람 판정 완료를 나눠 보고한다.

## 4. 구체적 회귀 우선순위와 중단 기준

- **P0 권한 보호**: `format_only` 어미 삭제, `read_only` 수정, 무권한 문서 생성·적용을 거부하는 테스트; 무수정 전체 반환은 허용.
- **P0 운영 안전**: IR-002 ops의 500건 초과 중단과 당직 확인 전 재개 금지 누락이 최종 자체 검증 성공 주장으로 가려지지 않음. 문서간 의미있는 조건 반복 허용.
- **P1 충돌/HITL**: IR-001 두 후원 정책을 임의 확정하지 않고 사람 확인으로 남기되, 독립적인 순서 변경·정보 보존은 진행할 수 있음.
- **P1 자체 검증 신뢰 경계**: 문서 실제 diff와 `final_checks`를 대조하며 허위 자체 성공을 최종 PASS로 승격하지 않음.
- **중단**: 다중 문서 입력 미지원, 권한 매핑 누락, 전체 후보 누락, 미정산/비용 불명, 출처 없는 정책 확정, 안전조건 누락이 발견되면 B2 성공으로 집계하지 않음.

## 5. 범위·다음 결정

- **이번 점검 결과**: 정적 코드·실험 증거 매핑과 B2 순서만 기록. Core 수정, 신규 실모델 요청, 예산 원장 조작, PR 생성·병합, 사람 최종 판정 없음.
- **다음 구현 단위 추천**: G0의 오프라인 실행 가능성 검증과 G1의 복수 문서/권한 입력 계약을 먼저 분리해 착수. G1이 완료되기 전에는 G2/G3의 모델 점수나 `B2_full` 결과를 만들지 않는다.
- **데이터 한계**: IR-001~003은 노출된 합성 개발 3건(출처 가족 1개). 현재 29건 활성 골드, PR #34 57건 보류 자료, IR 원본/골드·사람 검토 이력은 손대지 않는다. 별도 승인·독립 실문서·반복 검증 전 일반화 금지.

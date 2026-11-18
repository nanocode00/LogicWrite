# B2 준비 G0/G1 결과 — 2026-11-17

G0 오프라인 재현과 G1 문서군 입력·권한 검증 기반을 구현했다. **B2 전체 파이프라인은 미완성**이며 G2 재구성·G3 범용 의미 판정·G4 실제 모델 비교는 실행/구현하지 않았다. 신규 모델/API 호출 0회, 실제 문서 적용·배포 0회다.

## 작업 기준과 보존

- 대상: `nanocode00/LogicWrite`, PR [#36](https://github.com/nanocode00/LogicWrite/pull/36), `eval/integrated-reconstruction-20261113`, 지정 worktree `/home/honorbear/LogicWrite-integrated-eval`.
- 시작 HEAD `b00a3a84197dc829496b3aa5222deafe8365ff05`. 원격 계획 문서 커밋만 있는 것을 확인해 `c1a82b4fe2c85b9ef639eae36caddd7fc14c925a`로 fast-forward한 뒤 구현했다. 추적 파일 dirty 변경 없음; 기존 untracked `__pycache__/`는 그대로 보존하고 커밋에서 제외한다.
- 기존 IR 원문/골드/사람 판단 및 파일럿 자료 425개 파일을 사전 SHA-256과 비교했다. Qwen·DeepSeek 결과, 원장·차단 상태를 변경하지 않았다. 다른 worktree 15곳의 Git 상태에도 변화가 없다. 해시 manifest와 비교 결과는 `preservation.json`에 있다.
- 계획: [B2_CORE_READINESS_20261117.md](../B2_CORE_READINESS_20261117.md). 실행 결정: [G0_G1_IMPLEMENTATION.md](../G0_G1_IMPLEMENTATION.md).

## G0 실제 재현

| 대상 | 실제 결과와 한계 |
|---|---|
| 단일 output_scope | 기존 입력 검증·분석·격리 후보·final_validator 테스트 통과. 원문 보존 후보가 나오지만 structural gate는 REVIEW, semantic_fidelity는 not_run, 승인 없음. |
| 복수 output_scope | `validate_input_bundle`와 `analyze_source`가 `Prototype requires exactly one concrete output_scope`로 거부한다. `integration.run_pipeline`은 예외를 잡고 후보 없이 STOPPED를 반환한다. 기존 검사 우회/삭제 없음. |
| final_validator | 원본·분석·조직 계획·표현 결과·재구성 결과·trace/ledger가 결합된 native 후보의 구조 검증기다. IR access 정책 해석기나 임의 외부 후보의 B2 생성 인증기가 아니다. |
| final_semantic_validator 외부 쌍 | 완전한 SHA-bound 동일 ID 집합에 대해 검토 요청 구성 가능. 복수 문서 합성 콜백 테스트는 7종 검토가 완료돼도 advisory REVIEW이고 생성 lineage/receipt/승인 없음. 미실행·invalid·미완전·unresolved 응답은 성공으로 승격되지 않음. |
| Qwen 기존 후보 6개 | `validator_shadow`만 수행. 각 후보의 byte hash를 기록하고 read_only 원본은 변하지 않은 참고 쌍으로만 포함했다. Core 생성으로 집계하지 않는다. 실제 reviewer 없음 → 6개 모두 semantic not_run/unresolved/REVIEW. |

G0의 초기 테스트에서 통합 facade가 예외를 밖으로 던질 것으로 예상했으나, 실제 catch 경로를 확인해 **저수준 거부 + facade STOPPED/후보 없음**을 함께 검사하도록 수정했다. 기존 테스트 삭제나 기준 완화가 아니다.

확정된 G1 과제는 단일 scope 실행기와 별도의 복수 문서 모델, access와 output_target의 구분, 원문/출처/권한의 외부 고정 hash 결합, 불완전·미확정 자료 보류, 평가자 데이터가 없는 입력 어댑터였다. 이들을 구현했으며 의미 재구성의 공백은 G2/G3로 남겼다.

## G1 추가 파일과 입력/출력

| 파일 | 역할 |
|---|---|
| `experiments/full_document_control/document_set.py` | 버전 계약 검증, trusted digest 결합, operation eligibility, 외부 전체 후보의 access/coverage 검사, 명시적 reconstruction unsupported 경계 |
| `experiments/full_document_control/document-set-v1.schema.json` | `core-document-set-v1`의 strict schema; 문서별 메타데이터·출처·권한·출력 여부·불완전성·질문 |
| `experiments/full_document_control/ir_document_set_adapter.py` | IR v1/v2의 input schema만 읽는 별도 어댑터; gold/answers/criteria/reviews 필드 거부, 문서 path 미조회 |
| `experiments/full_document_control/DOCUMENT_SET.md` | G2 소비 인터페이스·신뢰 경계·실행 가능한 사용 예시·미지원 범위 |
| `experiments/full_document_control/test_document_set{,_g0}.py` | 신규 계약/어댑터의 정상·실패 회귀, 기존 경로의 G0 characterization |
| `experiments/integrated_reconstruction_pilot_20261117/b2_g0_g1_offline.py`, `test_b2_g0_g1_offline.py` | 오프라인 재현·IR mapping·기존 Qwen validator_shadow. 기존 파일은 읽기 전용, 출력은 새 디렉터리만 허용 |
| 이 디렉터리 `*.contract.json`, `offline-evidence.json`, 검증 기록 | 완전한 새 계약 입력 예시, 실제 admission/shadow 출력, 테스트/보존 근거 |

기존 Core 실행/승인/validator 구현 및 기존 평가 파일은 수정하지 않았다. 사례별 정답·금지 문구·골드 Q/F ID를 Core에 넣지 않았다. 모든 authority는 제공된 주장/근거 위상이며 실제 외부 진실을 인증한 것이 아니다. 동일 출처 원본 path·content SHA·scope ID·권한·metadata의 변경은 사전 고정 trusted contract SHA로 거부한다. 모델/후보가 새 SHA를 제시해도 권한 상승으로 신뢰하지 않는다.

예시 입력은 `IR-001.contract.json` 등 전체 JSON을 참조한다. `validate_contract(contract, expected_sha256=pin)` 출력은 `structural_input_valid=true`, `gate_state=REVIEW`, `semantic_judgment=unresolved`, `execution_state=not_run`, `b2_reconstruction_success=false`다. 실제 출력 대상 전체의 무수정 rows를 `validate_candidates`에 넣으면 access 범주 검사는 `within_declared_access`일 수 있지만 **명시 제약 전체 준수·의미 품질·실행 성공은 미판정**이다. `prepare_reconstruction`은 항상 `unsupported`와 `DOCUMENT_SET_RECONSTRUCTION_NOT_IMPLEMENTED`를 반환하며 후보를 만들지 않는다.

## IR 변환 및 shadow 결과

| 사례 | 전체 문서 | edit | format_only | read_only | 출력 대상 | 결과 |
|---|---:|---:|---:|---:|---|---|
| IR-001 | 7 | 2 | 0 | 5 | readme, usage | 원문/role/authority/access/hash/제약/질문 보존, 구조 수용 |
| IR-002 | 4 | 2 | 0 | 2 | design, ops | 동일, 구조 수용 |
| IR-003 | 3 | 0 | 1 | 2 | meeting | 동일, format_only를 edit로 승격하지 않음 |

문서별 독자·목적이 명시적으로 분리되지 않은 입력은 null을 유지하고 기존 request/context/role 전체를 보존한다. IR v2 발췌/partial/unknown 및 null 맥락/근거 위상은 표현되지만 REVIEW/held로 남는다. 글로벌 gaps는 미해결 질문으로 보존하며 명시 access를 임의 확대하거나 모든 독립 작업의 취소로 해석하지 않는다. 실제 질문별 action 결합과 부분 HITL는 G2 과제다.

Qwen IR-001/B0·B1, IR-002/B0·B1, IR-003/B0는 access 범주/전체 제출 검사를 통과할 수 있으나 의미는 unresolved다. IR-003/B1의 ‘실패다.’→‘실패.’ 및 끝 개행 변경은 changed format_only로 `FORMAT_CHANGE_REQUIRES_REVIEW`에 보류된다. **G1은 이 변화의 의미 위반을 범용 판정하지 않는다.** 동일한 규칙으로 서식만 바꾼 후보도 REVIEW며 무수정 후보는 허용된다. IR-002 안전 조건 누락, IR-001 정책 모순/과잉 보류의 기존 AI 평정을 새 Core 성공으로 덮지 않는다.

## 검증

- G0 characterization **5개 통과**, G1 계약·어댑터 **23개 통과**, shadow evidence **1개 통과**. 신규 모듈 미구현 RED 및 malformed 입력/출력범위 hardening RED를 먼저 관측했다.
- 기존 Core 전체 **399개 통과**(기존 371개 + 신규 G0/G1 28개). 파일럿 suite **59개 통과**(새 shadow 회귀 포함).
- 공식 전체 회귀: `python3 tools/evidence_validation/run.py --output /tmp/logicwrite-b2-g0-g1-20261117-regression-initial.json` → **PASS, 31 suites / 881 tests, failures=0, errors=0, skipped=0**. 역사 스냅샷과 현재 코드 소비자 경계를 각각 검사했다. 이는 의미 품질 또는 실제 B2 성능 점수가 아니다.
- [regression-summary.json](regression-summary.json)에 공식 명령·전체 보고서 SHA·검증 source identity·suite별 집계를 기록했다. 전체 JSON은 위 `/tmp` 경로에 보존했다. 회귀 실행 중 소스를 고정했으며 보고서/진행 문서 정리만 실행 후 추가했다. 제품 코드는 검사 이후 바뀌지 않았다.
- [offline-evidence.json](offline-evidence.json)에는 원본 3개/기존 후보 6개 파일 hash, IR 매핑, legacy 차단 및 shadow 결과가 있다. [preservation.json](preservation.json)의 사전 원본 hash 425개는 모두 동일하며 다른 15 worktree 상태도 동일하다.
- 실패 테스트 삭제·skip 추가·기준 완화 없이 통과했다. 검증·예시·기존 Qwen 결과는 사람 gold 승인이나 Core 적용 승인을 부여하지 않는다.

독립 코드 리뷰는 G0/G1 범위의 중대한 결함을 찾지 않았다. 리뷰는 승인이나 의미 평정이 아니다. 유료 API 호출·파일 적용·배포는 없고 기존 사람 판정 및 예산 경계도 유지했다.

## 남은 기능과 G2 착수 조건

1. 문서군 공동 분석·계획과 문서별 독자 과업/근거 시점·위상을 연결해야 한다. 단일 실행기의 반복 호출을 문서군 실행으로 포장하지 않는다.
2. 명시 제약·정책 충돌·미확정 action을 문서/범위별 질문과 연결하고, 독립적으로 가능한 작업과 보류를 구분해야 한다. 현재 eligibility는 실행 허가가 아니다.
3. 지원하는 배치/보존/최소 서식 작업의 실행기와 입력 pin·후보/trace/receipt를 구현해야 한다. 미지원 MOVE/REMOVE/의역·새 문서는 별도 차단한다.
4. G3에서 format_only 변경·로컬 안전 조건·의미 보존을 독립 검토해야 한다. 현재 모든 changed format_only는 REVIEW이고 edit 후보의 의미 품질은 검사하지 않는다.
5. 실제 B2 모델 비교는 G1~G3 전체 회귀 및 별도 사용자 승인·예산/정산 제어 이후 G4에서만 가능하다.

## 커밋 및 PR

이 결과는 기존 PR #36 브랜치에만 커밋·푸시한다. 새 PR 생성이나 병합은 하지 않는다. 검증 대상 source identity/실행 HEAD와 최종 commit은 다를 수 있으므로 회귀 결과에 기록된 current_code/source_sha256와 Git commit 상태를 구분한다. 최종 커밋·원격 HEAD·PR 상태는 작업 완료 응답에서 보고한다.

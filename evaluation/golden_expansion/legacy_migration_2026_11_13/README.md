# 완료된 17건의 레거시 이관 검증 — 정책 승인 대기

17건 모두 기존 최초 판단 → 독립 Codex 반례 → 사용자 최종 판단 → 별도 포함 승인을 연결해 **증빙 검증을 통과**한다. 기존 review.py의 정식 이벤트로 변환하지 않는다. 신규 `legacy-review-migration-v1`은 **검수·승인 전 제안**이다. 따라서 현재 신규 활성화 적격은 0건이고 기존 적격/활성 12건은 유지한다.

| 파일 | 역할 |
|---|---|
| policy.json | 이번 고정 17건의 이관 제안. 적용 범위·별도 검증 요건·차이·한계 명시. user_policy_approval=null |
| continuation-request.json | 현재 사용자 요청의 완료 검토 재요구 금지와 UNRESOLVED 4건 사유/판단 유지 재확인 원문. 정책 승인으로 확장하지 않음 |
| legacy-records.json | 원본 입력·최초 판단·AI 반례/실행·최종 판단·포함 승인·미해결 사유·출처/파생 관계를 연결한 감사용 묶음. 정식 human event가 아님 |
| validate_migration.py | 기존 검증기와 새 이관 경로·v3 후보 검증. 읽기 전용이며 활성화 기능 없음 |
| test_migration.py | 정책 승인/귀속/이력/라벨/범위 변조와 삭제·읽기 전용 회귀 |
| preserved-files.json | 기준 main의 추적 파일 전체 SHA. 정식 정책·v2·과거 평가·입력·답안·검토 증거 포함 |
| artifact-manifest.json | 신규 이관 및 v3 산출물의 정확한 목록·SHA. 재계산한 내용과 별도 비교해 manifest만 바꿔도 위조 탐지 |
| PLAN.md | 범위와 실행 절차 |

## 기존 정식 정책과의 차이: 숨긴 예외 없음

| 항목 | 변경하지 않은 정식 경로 | 제안한 단발성 레거시 경로 |
|---|---|---|
| 이력 형식 | user_initial/ai_counterreview/user_final 이벤트와 정식 필드 | 원래 제출 형태를 검증하고 각 원본 파일·pointer·해시 연결. 과거 이벤트 새로 만들지 않음 |
| 사용자 응답 | challenge별 accept/reject/defer + 이유 | 실제 사례별 Codex **반론 타당성 평가에 대한 동의**만 그대로 인정. 분류값 매핑 금지 |
| 최종 evidence | 정식 user_final의 evidence 배열 | 정확한 원문에 연결된 **AI supporting evidence**를 AI 근거로만 사용. 사용자 작성/채택으로 주장하지 않음 |
| UNRESOLVED | 정식 unresolved_issues | 사용자의 최초 이유와 기존 판단 유지 재확인을 원본 참조로 보존. 정보 부족을 유효 정답으로 인정 |
| 시각·노출·신원 | 기존 스키마·정식 기록 요구 | 알 수 없는 실제 시각/노출/인증은 null. Git의 인과 순서와 내용 참조로 순서만 검증. 서명/외부 인증 주장 없음 |
| 적격 판정 | 기존 review.assess 결과 | 명시적 이관 정책 적용 승인이 있어야 이 경로의 신규 적격 부여 가능. 현재 승인 없으므로 **0건** |

이 차이는 단순 직렬화 변경이 아니라 **새로운 한정 이관 정책 결정**이다. 정식 스키마에 임의의 값으로 맞추거나 기존 검증 요건을 몰래 생략하지 않는다. `qualifies_under_proposed_policy=true`는 제안 요건을 충족한다는 증빙 결과이고, `activation_eligible=false`를 덮어쓰지 않는다. 기존 review.py, record.schema.json, 준비된 정식 workflow와 과거 preflight는 당시 상태로 보존한다.

## 검증한 근거와 순서

기존 #25/#26/#27 검증기를 먼저 실행하고 실행 완료 17/실패 0, 정확한 입력 인용, 입력 SHA와 원본 요청·결과·실행 연결을 확인한다. 각 최종/승인 파일 SHA 및 JSON pointer, canonical 최종 이벤트 해시와 승인 이벤트 해시를 확인한다. 초기와 최종 판단은 모두 동일하며 정답은 **사용자 최종 판단**에서만 가져온다.

Git 순서는 최초 판단 기록 `93d5252` → Codex 기록 `8ace3d4` → 사용자 최종 기록 `1ec8031` → 포함 승인 기록 `dc8083d`의 실제 blob 내용과 조상 관계로 확인한다. AI 세 배치 모두 해당 Codex 커밋의 원본과 일치해야 한다. 이는 저장된 이력의 인과 순서이며 사용자의 실제 검토 시각이나 인증된 채팅 시각이 아니다. 검증에는 이 커밋들이 포함된 저장소 이력이 필요하다. shallow checkout에서 이력이 없으면 자동 통과하지 않고 실패한다.

GC-003/006/009/012의 최초 미해결 이유를 그대로 유지한다. 현재 사용자가 후속 요청에서 기존 사유·판단 유지 재확인을 명시한 문장만 별도 전사했다. 과거 재확인 원시 발언의 정확한 시각을 확보했다고 주장하지 않는다. 확인하지 않은 formal evidence/challenge decision/confidence 확인 필드는 null이다. 기존 검토를 다시 요구하지 않는다.

## v3와 실제 활성 참조

[v3 후보](../../g3_g4/development_gold_v3_2026-11-13/development-gold.json)는 기존 v2의 **12개 행 및 snapshot 참조를 전체 그대로 재사용**하고 신규 GC-001~012/SP-013~017의 17개 행을 추가한 29건이다. 분포 PRESERVED 12 / VIOLATION 9 / UNRESOLVED 8. 기존 v2를 덮어쓰지 않는다.

후보는 active=false, active_case_ids=[]이며 신규 행의 development_gold_eligible=false다. 실제 평가 소비자 2개(core_pipeline evaluate.py / source_candidate_semantics run.py)는 계속 기존 v2를 참조한다. `activation-proposal.json`은 **비활성 제안**이지 실제 인덱스가 아니다. 전체 29건을 현재 활성이라고 보고하지 않는다.

다음 결정은 **이 17건에 legacy-review-migration-v1을 적용하는 것을 승인할지**다. 승인 전 신규 적격·실제 활성 참조 변경은 보류한다. 승인 이후에도 기존 파일을 수정하지 말고 별도 승인 이력을 추가한 뒤 적격 상태·새 활성 참조·소비자 연결을 검증하는 후속 변경으로 처리한다. 명령행 옵션이나 manifest 편집으로 승인을 자동 생성하는 기능은 없다.

## 데이터 한계와 출처

단일 사용자와 독립 AI 보조이며 복수 독립 인간 검수·독립 홀드아웃이 아니다. GC 12건은 requests/httpx/click/prometheus의 4개 원문 계열이다. SP-013/014는 SP-003/011, SP-015는 SP-009, SP-016은 SP-010, SP-017은 SP-012에서 파생되었다. source_provenance/version/git_blob_sha/snapshot과 parent_inputs/SHA를 그대로 보존한다. 향후 평가 시 사례 수와 독립 원문 계열 수를 구분하고 동일 원문·부모가 개발/홀드아웃으로 분산되지 않게 해야 한다. 이번 작업은 평가 재집계·답안 수정·Core 승인·배포를 수행하지 않는다.

해시·Git은 검수한 기준 대비 변경 탐지 수단이며 외부 사용자 인증이 아니다. 코드·원본 Git 기준까지 함께 바꾼 공격의 암호학적 인증을 보장하지 않는다.

```sh
python3 -B evaluation/golden_expansion/legacy_migration_2026_11_13/validate_migration.py
python3 -B evaluation/g3_g4/development_gold_v3_2026-11-13/validate.py
# 무결성 성공과 활성 준비 성공은 다르다. 현재 아래 옵션은 exit 2.
python3 -B evaluation/golden_expansion/legacy_migration_2026_11_13/validate_migration.py --require-activation-ready
python3 -B -m unittest discover -s evaluation/golden_expansion/legacy_migration_2026_11_13 -v
python3 -B evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-legacy-v3-regression.json
```

PR #29와 독립적인 최신 main 기반 후속 구현이다. #29의 미병합 파일을 복사하거나 동작 의존성으로 요구하지 않는다. 이 README/후속 PR의 정책 제안을 검토하고 승인하는 절차와 이미 완료된 사용자 판단을 구분한다. 자동 병합하지 않는다.

검증 결과: 신규 회귀 12개 및 최신 main 기반 전체 20개 디렉터리 663개 테스트 통과. 테스트 전후 Python 입력 SHA 동일. 기존 추적 파일 579개는 기준 Git blob bytes/SHA와 전수 일치했다. 별도 로컬 AI 코드 리뷰에서 Critical/Important 문제 없음. 정책 준비 검사 옵션은 의도대로 exit 2이며 테스트 실패가 아니다. 로컬 검증 결과로서 원격 CI·독립 인간 검수·정책 적용 승인으로 표현하지 않는다.

# 개발용 골드 v3 실제 활성 등록 — 29건

현재 사용자 요청에서 `legacy-review-migration-v1`을 GC-001~012/SP-013~017 **17건에 한해 적용하도록 명시적으로 승인**했다. 이 활성 계층은 승인 전 후보와 과거 이력을 덮어쓰지 않는다. `evaluation/active_development_gold.json`이 실제 활성 데이터셋과 두 평가 진입점을 고정한다.

| 파일 | 역할 |
|---|---|
| policy-approval.json | 사용자 승인 원문 전사와 17개 사례별 적용 승인. 입력 SHA, 최종/포함 승인 canonical 해시, 이관 묶음, 정책 SHA, 원문 해시와 JSON pointer 및 해시 체인 연결 |
| development-gold.json | 기존 12개 행·snapshot 참조 그대로 + 신규 17개 적격/활성 행. 총 29건, PRESERVED 12 / VIOLATION 9 / UNRESOLVED 8 |
| activation-history.json | 기존 v2→승인된 v3의 추가 전용 활성화 기록. 신규 적격 17/활성 17, 기존 12 유지. 사용자 판단이나 과거 사건을 생성한 것이 아님 |
| validate.py | 승인 범위·원본 검토·기존/후보 데이터·현재 활성 인덱스·소비자 참조를 읽기 전용 검증 |
| preserved-files.json | #29·#30 병합 후 기존 추적 파일 600개 SHA. 원본 판단/승인/검토/정책/v2/후보/평가 코드·결과 전체 포함 |
| artifact-manifest.json | 신규 데이터·소비자 코드·인덱스의 정확한 파일 목록과 SHA |
| VALIDATION.md | 이번 활성화 검증 결과와 실행 명령 |

포함 승인은 기존 #27 그대로이고 정책 적용 승인은 이번 발언으로 별도 추가했다. 기존 정책 JSON의 승인 전 상태와 정식 review.py/스키마는 과거 이력으로 그대로 남는다. 현재 승인 상태는 policy-approval.json으로 해석한다. 기존 final null, 형식 미확인 필드, 사용자 동의 원문, AI 근거 귀속 및 미해결 사유는 바꾸지 않았다.

사용자 실제 승인 시각·서명·인증 신원은 null이다. 원문은 현재 요청의 전사이며 외부 인증 원시 채팅이 아니다. 사례별 이벤트는 사용자의 일괄 승인 범위를 전개한 기록이며 17번의 별도 사용자 발언으로 주장하지 않는다. activation-history는 AI가 기록한 구현 상태이며 사용자 과거 시각을 소급 생성하지 않는다.

## 실제 활성 상태와 평가 진입점

- 실제 활성: 이 폴더의 development-gold.json, active=true, 29개 active_case_ids, 전건 development_gold_eligible=true.
- 원래 v2와 후보 v3는 불변이다. 원래 평가 스크립트도 과거 v2 결과의 재현용으로 그대로 보존했다.
- **현재 활성 소비자**는 `evaluation/development_gold_active/source_candidate.py`와 `core_diagnostics.py`다. 활성 인덱스가 이 두 파일과 활성 manifest의 SHA를 연결한다. 옛 스크립트 경로를 실행하면 여전히 v2 재현이며 현재 v3 평가로 간주하지 않는다.
- 새 소비자는 원래 검증 엔진을 재사용하고 독립 입력 목록을 29건으로 확장한다. 예측 단계는 정답·활성 manifest·인덱스를 읽지 않는다. 정답 비교 시에만 승인된 활성 인덱스를 검증한다.
- UNRESOLVED 8건은 유효한 정답이다. 완료된 인용 기반 AI 검토가 unresolved이면 `three_way_observation=UNRESOLVED`로 표시한다. 미실행/불완전 검토나 Core의 REVIEW를 정답으로 바꾸지 않는다. 기존 definitive-only 정확도 집계는 유지하며 이번 작업에서 모델 실행·평가 재집계는 하지 않는다.

단일 사용자와 AI 보조의 개발용 데이터이며 독립 다중 인간 검수·독립 홀드아웃·Core 최종 승인·배포 권한이 아니다. GC 원문 4계열과 SP parent_inputs/SHA, 전체 provenance를 유지한다. 29개 독립 원문 표본으로 과대 해석하지 않는다.

검증은 기존 원본 검증기와 승인 전 이관 검증을 먼저 통과시키고, 승인된 이번 별도 계층에서만 신규 적격성을 부여한다. 해시/원본 Git 기준을 모두 다시 쓰는 공격에 대한 외부 인증을 주장하지 않는다. 승인·범위·원본 입력·최종 판단·연결이 변하면 검증이 실패한다.

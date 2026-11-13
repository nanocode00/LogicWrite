# 개발용 골드 v3 후보 — 아직 비활성

29건: 기존 v2의 SP-001~012 12건 + GC-001~012/SP-013~017 17건. 분포 PRESERVED 12 / VIOLATION 9 / UNRESOLVED 8. 정답은 사용자 최종 판단에 연결하고 AI 권장 판단으로 대체하지 않는다. 기존 v2 행과 snapshot 참조는 그대로 보존했다.

**구현·검증 가능한 후보이며 실제 활성 데이터셋은 아니다.** active=false, active_case_ids=[]이고, 신규 17건의 development_gold_eligible=false다. 이관 증빙은 17건 모두 유효하지만 별도 `legacy-review-migration-v1` 적용 승인이 아직 없으므로 신규 적격·활성화는 0건이다. 현재 실제 활성은 v2 12건(P4/V4/U4)이다.

| 파일 | 역할 |
|---|---|
| development-gold.json | 버전 3.0.0 후보, 29개 ID·사용자 정답·입력/원본 판단/승인 및 이관 이력·출처 연결 |
| activation-proposal.json | 현재 v2 및 후보 v3 SHA를 연결한 비활성 참조 제안. 실제 소비자 참조는 변경하지 않음 |
| validate.py | 이관 검증기를 통해 기존 자료 불변·원본 이력·정답·분포·미승인 정책 차단 검증 |

[이관 정책 및 한계](../../golden_expansion/legacy_migration_2026_11_13/README.md)를 함께 검토한다. UNRESOLVED 8건을 유효한 평가 정답으로 지원하며 임의로 P/V로 바꾸지 않는다. 데이터는 단일 사용자+AI 보조의 개발용이며 독립 복수 인간 검수나 홀드아웃으로 표현하지 않는다. GC 동일 원문 계열과 SP parent 관계를 보존하므로 29개 독립 원문 표본으로 해석하면 안 된다.

정책 승인 후에도 승인 이력과 적격성·실제 활성 참조 변경은 별도 검증 변경으로 기록해야 한다. 이 폴더 이름이나 후보 manifest의 존재만으로 활성화 완료를 주장하지 않는다.

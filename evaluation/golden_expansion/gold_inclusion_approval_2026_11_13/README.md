# 개발용 골드 포함 승인 의사표시 17건 — 활성화 전

사용자가 이번 대화에서 명시적으로 승인한 GC-001~012와 SP-013~017을 별도 추가 전용 이력으로 기록한다. **포함 승인 17건을 기록했으며 신규 사례의 실제 활성화는 수행하지 않는다.**

| 파일 | 역할 |
|---|---|
| approval-declaration.json | 사용자 일괄 선언 원문 전사, 정확한 17개 ID 및 승인 범위. 사용자 시각·서명·인증은 null |
| events.json | 사례별 포함 승인 true. 입력 SHA, 기존 최종 판단 파일·JSON pointer·canonical event SHA, 선언 원문 SHA와 해시 체인 연결 |
| record.schema.json | 기존 승인 정책과 분리된 포함 승인 의사표시 기록 스키마. 활성화 false와 미제공 메타데이터 null 강제 |
| preserved-files.json | #25·#26 병합 후 main의 모든 추적 파일 SHA-256. 기존 입력·정답·원시 검토·최종 판단·G3/G4 전체 포함 |
| artifact-manifest.json | 이 폴더 파일의 변경·삭제 탐지. 검증기에서 정확한 목록 강제 |
| validate_approval.py | 읽기 전용 검증. 파일 작성·복구·모델 호출·골드 활성화 기능 없음 |
| test_approval.py | 변조·삭제·중복·누락·범위·출처·입력/최종 판단 연결·활성화 권한 침범 검사 |

## 승인과 판단의 경계

기준은 PR #25 merge `538a3b84dce66afd6897ec73d04ff9406674a3bb`와 PR #26 merge `2bee75af63a0c26a3b3c44c6605d67b2ffbb4bf7`이다. #26의 최종 판단과 승인 null 필드는 과거의 미결정 상태로 보존한다. 최종 판단 분포 **PRESERVED 8 / VIOLATION 5 / UNRESOLVED 4**는 바뀌지 않는다. UNRESOLVED 4건도 사용자의 이번 포함 승인 범위에 속하며, 승인 기록이 판단의 불확실성을 해소하거나 정책 적격성을 자동 부여하지 않는다.

원문은 사용자 메시지의 전사이며 외부에서 인증된 원시 채팅이나 전자서명이 아니다. 폴더 날짜는 기록 작업일이며 사용자의 실제 승인 시각이 아니다. 판단·승인 출처 human과 기록자 ai를 구분한다. 단일 사용자와 AI 반례 검토를 복수 독립 인간 검수 또는 독립 holdout으로 표현하지 않는다.

기존 user_final 승인 스키마가 요구하는 시각·증거 등은 이번에 모두 제공되지 않았다. 기존 스키마나 정책을 완화하지 않고 별도 `user_development_gold_inclusion_approval_recorded` 이벤트를 사용한다. 기존 workflow·답안·적격성 계산·데이터셋·평가 결과에 주입하지 않는다. Core 최종 승인·배포 권한을 부여하지 않는다.

## 구현 및 검증 범위

- [x] 기존 17개 최종 판단과 원문 승인 선언을 연결한 별도 이벤트 작성.
- [x] 해시·범위·스키마 검증과 읽기 전용 동작 구현.
- [x] 변조·삭제·범위 변경 회귀 11개와 전체 회귀 635개 통과. 상세 검증 범위는 VALIDATION.md 참조.

병합 전 보호 정책과 최신 PR head를 다시 확인하며 승인 이력만 병합한다.

```sh
python3 -B evaluation/golden_expansion/gold_inclusion_approval_2026_11_13/validate_approval.py
python3 -B -m unittest discover -s evaluation/golden_expansion/gold_inclusion_approval_2026_11_13 -v
python3 -B evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-full-regression.json
```

검증기는 기존 파일 전체 SHA와 선언/보존 목록의 고정 해시를 검사한다. 이벤트 또는 manifest/체인을 다시 계산해도 사례 삭제·범위 변경·다른 입력/최종 이력 연결을 거부한다. 정정은 기존 이벤트를 덮어쓰지 않고 별도 후속 기록으로 수행해야 한다. 해시와 Git 검수는 변경 탐지 근거이며 공격자가 검증 코드와 Git 기준까지 모두 재작성한 상황의 외부 인증을 보장하지 않는다.

## 다음 활성화 단계

현재 활성 데이터셋 `evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json`의 **SP-001~012, 총 12건**을 그대로 유지한다. 이번 승인 17건은 여기에 추가하지 않는다.

실제 활성화는 별도 사용자 요청 후 진행한다. 그때 최신 포함 승인/입력/최종 판단 해시를 재확인하고, 기존 활성화 정책의 필수 증거와 미제공 정보·UNRESOLVED 취급을 확인해야 한다. 정책을 충족하는 별도 추가 버전의 활성 데이터셋·인덱스와 연결 검증을 제안하고 테스트·PR 검수를 거쳐야 한다. 이번 기록만으로 해당 요건의 충족이나 활성화 완료를 주장하지 않는다.

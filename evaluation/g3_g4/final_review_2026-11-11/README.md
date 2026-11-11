# G3 사용자 최종 판정과 개발용 골드 등록

2026-11-11 사용자가 명시한 최종 판정·포함 승인을 전사하고 기존 v1 워크플로로 검증했다. AI가 새 사람 판단을 만든 것이 아니다. 현재 상태의 진입점은 [development-gold.json](development-gold.json)이다. 이전 준비표·최초 의견·AI 검토·반론 응답·제출 상태는 당시 기록으로 보존하며 현재 최종 상태로 덮어쓰지 않는다.

## 사용자 승인과 활성 등록

| 사례 | 사용자 최종 판정 | 포함 승인 | 정식 워크플로 | 활성 개발용 골드 |
| --- | --- | --- | --- | --- |
| SP-001 | PRESERVED | 승인 | user_final_confirmed | true |
| SP-002 | PRESERVED | 승인 | user_final_confirmed | true |
| SP-003 | PRESERVED | 승인 | user_final_confirmed | true |
| SP-004 | PRESERVED | 승인 | user_final_confirmed | true |
| SP-005 | VIOLATION | 승인 | user_final_confirmed | true |
| SP-006 | VIOLATION | 승인 | user_final_confirmed | true |
| SP-007 | VIOLATION | 승인 | user_final_confirmed | true |
| SP-008 | VIOLATION | 승인 | user_final_confirmed | true |
| SP-009 | UNRESOLVED | 승인 | user_initial_reviewed, 추가 단계 대기 | false |
| SP-010 | UNRESOLVED | 승인 | user_final_confirmed | true |
| SP-011 | UNRESOLVED | 승인 | user_final_confirmed | true |
| SP-012 | UNRESOLVED | 승인 | user_final_confirmed | true |

사용자 최종 판정·포함 승인은 **12건, 4/4/4**다. 정식 검증을 통과한 활성 개발용 골드는 **11건, 4/4/3**이다. 승인 여부만으로 적격 값을 켜지 않았으며 active_case_ids에는 SP-009를 넣지 않았다. 미완료 사유는 UNRESOLVED 라벨 때문이 아니라 SP-009의 검수 이벤트 순서 때문이다.

UNRESOLVED는 검수하지 않았다는 뜻이 아니다. SP-009는 목적지 본문 미제공, SP-010은 승인 기준 버전 미확정, SP-011은 현지 노출 의무 미확정, SP-012는 결과 절단이라는 근거 부족의 판정이다. 활성 보류 3건도 사유·근거를 남긴 검수 완료 정답이다. 단일 사용자 최종 검수이며 독립 복수 사람 검수·재정, 홀드아웃 정답 또는 Core 승인으로 취급하지 않는다. 원본 답안의 gold_eligible은 여전히 false이며 새 development_gold_eligible과 다른 필드다.

## 파일과 이력

- [user-approvals.json](user-approvals.json): 사용자 명시적 최종 판정·근거·개발용 포함 승인 12건. 실제 기록 시각과 원본 입력/답안 해시를 연결했다. 오류 유형과 인용 위치는 기존 자료를 이용한 Codex 직렬화이며 새 독립 사람 주석으로 보고하지 않는다.
- `final/SP-NNN.json`: 기존 counterreview 스냅샷의 이벤트 전체를 그대로 두고 새 user_final을 추가한 11건. 기존 입력·AI 제안 해시, 현재 반론 ID, 반론별 응답, 근거, 승인·한계와 해시 체인을 검증한다.
- [pending/SP-009.initial.json](pending/SP-009.initial.json): 이번 사용자 명시적 UNRESOLVED 판단을 **현재의 새 최초 판단**으로 기록한 파일. 과거 범주 판정을 꾸며내지 않는다.
- [development-gold.json](development-gold.json): 12건 승인 및 11건 활성 등록, 검수 수준·스냅샷·해시·적격·차단 사유. 평가 시 이 manifest의 active_case_ids와 해당 해시를 고정해 사용한다.
- [preservation.json](preservation.json): 이전 제출 HEAD `4fd828dbef9db16303e37c0da6d67d7b1cff5b6c`의 평가 파일 153개 보존 장부. 기존 입력·답안·스키마·준비·공동 검토·AI 검토·반론 응답·G4 자료를 포함한다.
- [followups.json](followups.json): SP-013~017 설계·추적 정보. 실제 ID 배정·입력·정답 생성 없음.

SP-003은 이전 사용자 UNRESOLVED와 반론 응답을 그대로 보존했다. 최신 명시적 승인에서 계약 충족과 계약 자체의 적절성을 구분한 AI 반론을 검토한 후 PRESERVED로 확정했으므로 새 최종 이벤트에 그 변경과 이유를 기록했다. 독자 목적·배치 적절성은 별도의 비차단 후속 검토로 남긴다. 이를 현재 계약 아래의 의미 미확정 사항으로 숨겨 합치지 않는다.

SP-006의 자동 업데이트 부정 반전과 30초→30분 변경은 독립 오류 두 건으로 기록하고 각각의 원문/후보 근거를 검사한다. SP-002의 순서 제약을 소급 추가하지 않았다.

## SP-009: 정확한 차단 원인과 다음 단계

과거 AI 검토는 범주 판정 없이 제시된 편집 방향을 검토한 보조 자료였다. 이번 명시적 UNRESOLVED 판단 **이후**의 정식 AI 검토 이벤트가 아니므로 재사용해 소급 연결하지 않았다. 현재 새 최초 판단만 유효하게 기록돼 있다.

1. 현재 최초 판단 이벤트에 연결한 **새 별도 AI 반례 검토**를 수행해야 한다.
2. 그 결과를 사용자가 검토하고, 필요한 반론 응답·최종 판단·포함 승인을 **다시 확인**해야 한다.
3. 그 뒤 v1 검증을 통과한 새 스냅샷과 새 버전 manifest에서만 활성화할 수 있다. 현재 사용자 승인 원본과 기존 manifest를 덮어쓰지 않는다.

이번 작업은 이 지점에서 SP-009 활성화를 멈췄다. 새 AI 결과나 미래 사용자 재확인을 생성하지 않았다. PACKAGING.md 전후 전체가 필요하다는 보류 사유는 유지하며, 그 자료를 갖춘 사례는 SP-015 설계에서 별도로 다룬다.

## 후속 파생 설계와 분리

[followups.json](followups.json)의 SP-013(첫 사용 직접 노출 필수), SP-014(선택 기능·링크 충분), SP-015(목적지 전후 전체), SP-016(승인 버전), SP-017(완전한 결과)은 설계 제안이다. 현재 실제 입력 ID와 중복되지 않음을 점검했지만 정식 배정 직전에 최신 목록을 다시 검사해야 한다. 새 입력·정답을 임의로 확정하지 않았다.

GC-001~012는 이번에 검수하지 않았다. 기존 입력·AI 잠정 답안·provisional 상태를 바꾸지 않았고 개발/홀드아웃 경계를 유지한다. 이번의 개발용 골드는 사용자·AI에 노출된 개발 자료로서 독립 홀드아웃으로 재분류할 수 없다.

## 별도 최종 검증 계층

기존 G3 검증기는 준비 단계와 과거 분포를 검사하므로 수정하지 않았다. 새 `validate.py`는 그 위에서 사용자 승인, 활성 manifest, 원본 보존, v1 실제 검증 결과, 반론 연결·순서·근거·최종 분포와 SP-009 차단 상태를 확인한다.

```bash
python3 evaluation/g3_g4/final_review_2026-11-11/validate.py
python3 -m unittest discover -s evaluation/g3_g4/final_review_2026-11-11 -p test_final_review.py
```

전체 명령과 실제 결과는 [VALIDATION.md](VALIDATION.md)에 기록했다. 구조 검사는 사용자 신원 인증·외부 사실 검증·독립 복수 사람 재정을 대신하지 않는다. PR은 리뷰 대상으로 정리하며 실제 병합은 하지 않는다.

# 개발용 골드 v2 — G3 12건 활성 등록

현재 개발용 평가 등록은 [development-gold.json](development-gold.json)이다. **사용자 최종 승인 12건, 정식 워크플로 적격 12건**, 분포는 PRESERVED 4 / VIOLATION 4 / UNRESOLVED 4다. 단일 사용자 + 별도 AI 반례 보조 검수이며 독립 복수 사람 재정·홀드아웃·Core 승인이 아니다.

SP-009는 현재 최초 판단 이후 새 별도 AI 반례 검토를 수행했고, 그 결과를 보여준 뒤 UNRESOLVED 최종 판정과 개발용 포함 승인을 묻는 질문에 사용자가 **“응”**이라고 재확인했다. [user-reconfirmation.json](user-reconfirmation.json)에 실제 질문·응답·현재 AI 스냅샷 해시·실제 저장 시각을 전사했다. 사용자 응답을 AI가 새로 생성한 것이 아니다.

[SP-009.final.json](SP-009.final.json)은 기존 현재 최초 판단→새 AI 검토 이벤트 prefix를 변경하지 않고 user_final만 추가했다. 반론은 없었으므로 responses는 빈 배열이다. PACKAGING.md 전후 본문 미제공이라는 unresolved_issues를 보존했다. 이는 자료가 확보됐다는 판정이 아니라 **근거 부족 상태가 타당하다는 검수 완료 정답**이다.

이전 v1 manifest의 11건과 SP-009 대기 스냅샷은 당시 상태로 그대로 보존했다. 새 v2 manifest는 이전 manifest 경로·해시에 연결하고, 기존 11개 활성 행과 최종 스냅샷을 그대로 재사용하며 SP-009 행만 새 유효 최종 기록으로 연결한다. 이전 대기 문서를 현재 상태로 덮어쓰지 않는다. 평가 시 이 v2 경로와 해시를 고정해야 한다.

[preservation-v2.json](preservation-v2.json)으로 이전 HEAD `943492ad81d5f9d60291f9dbde2cf79b509cf892`의 평가 파일 178개가 그대로임을 검사했다. G4 GC-001~012는 여전히 provisional이며 기존 입력·답안·검수 기록·Core·후속 파생 설계·개발/홀드아웃 경계를 변경하지 않았다. SP-013~017은 설계 제안으로만 남아 있다.

```bash
python3 evaluation/g3_g4/development_gold_v2_2026-11-11/validate.py
python3 -m unittest discover -s evaluation/g3_g4/development_gold_v2_2026-11-11 -p test_activation.py
```

검증 결과: 신규 활성화 테스트 14 + 이전 최종 계층 24 + 파일럿 21 + v1 워크플로 34 + 입력 패키지 9 + G3/G4 17 + Core 회귀 340 = **459건 통과**. 기존 파일럿·G3/G4 데이터 검사도 통과했다. 새 검사는 실제 사용자 재확인·해시 바인딩·이전 prefix·UNRESOLVED 사유·12건 활성 분포·기존 11건 불변성과 잘못된 승격/소급을 검사한다. 테스트용 훼손 복사본은 실제 사람 판단으로 기록하지 않는다.

현재 모든 정식 검수 단계는 완료했지만, 실제 이동 후 문서 검증을 수행했다는 뜻은 아니다. 목적지 전체가 제공된 SP-015 파생 설계는 별도 후속 작업이다. PR #21에는 이 기록을 추가하며 실제 병합은 하지 않는다.

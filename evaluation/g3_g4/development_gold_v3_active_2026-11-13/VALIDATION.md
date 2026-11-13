# 활성화 검증

실행 명령:

```sh
python3 -B evaluation/g3_g4/development_gold_v3_active_2026-11-13/validate.py
python3 -B -m unittest discover -s evaluation/development_gold_active -v
python3 -B evaluation/core_pipeline_2026_11_11/run_checks.py --output /tmp/logicwrite-active-v3-tests.json
```

승인 적용 범위는 정확히 GC-001~012/SP-013~017이다. 원본 사용자 판단(P8/V5/U4), 입력 SHA, 초기→AI→최종→포함 승인과 이번 정책 적용 승인 연결을 검증한다. 신규 적격/활성 17건 + 기존 12건 =29건(P12/V9/U8)이며 기존 v2 12개 행과 snapshot 참조를 그대로 유지한다. 사용자 미제공 시각·서명·인증이나 AI 인용의 사용자 귀속을 생성하지 않는다.

검증 결과:

- #29 최종 회귀 658개 통과 후 병합. #29+#30 통합 회귀 670개 통과 후 #30 병합.
- 신규 활성화/소비자 회귀 11개 통과. 전체 22개 디렉터리 681개 테스트 통과, 테스트 전후 Python 입력 SHA 동일.
- 기준 main 기존 추적 파일 600개를 Git blob bytes와 SHA로 전수 비교: 변경 0. v2·후보·원본 검토·정답·정책·기존 평가 코드/결과 모두 불변.
- 승인 범위 17, 신규 적격 17, 전체 활성 29, 분포 PRESERVED 12 / VIOLATION 9 / UNRESOLVED 8. 중복·누락·판단 변경 0.
- 두 실제 CLI 진입점의 predict→compare 오프라인 흐름에서 29건과 v3 참조를 확인. 예측은 label-blind, 의미 평가 미실행 accuracy=null/evaluated_count=0, Core 비교는 SP accuracy 아님.
- 완전 인용 기반 UNRESOLVED 합성 프로토콜 검증 통과. 실모델 실행·기존 결과 재집계 없음.
- 별도 새 문맥 AI 코드 검토 Critical/Important 문제 없음. 독립 인간 검수로 표현하지 않음.
- 원격 저장소 main 보호/ruleset/필수 검사는 없고 #29/#30 등록 CI 검사도 없었음. 로컬 회귀이며 원격 CI 통과를 뜻하지 않는다. 후속 PR의 최신 상태는 병합 직전 재확인한다.

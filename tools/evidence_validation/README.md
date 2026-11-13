# 역사적 증거와 현재 코드의 검증 경계

이 디렉터리는 기존 Golden Set 파일·검증기를 수정하지 않는 새 실행 계층이다. 최신 `main` `879d15b8fa267010217d9310b72d1066fda74f99`에서 분기했다. PR #33·#34와 병렬 골드셋 재설계 폴더에는 변경을 추가하지 않는다.

## 실행

전체 저장소의 지원 검증 명령은 다음과 같다. 표준 라이브러리와 기존 `jsonschema>=4.10.3,<5`, 전체 로컬 Git 이력이 필요하다. 모델·네트워크 호출·파일 반영·승인 발급은 하지 않는다.

```bash
python3 tools/evidence_validation/run.py --output /tmp/logicwrite-validation.json
```

진행은 stderr, 개별 명령·실패·실행 수·출처·환경은 JSON에 남긴다. 오류·skip·expected failure·unexpected success·빈 테스트 묶음·시간 초과·증거/코드 변경은 실패 종료다. 출력 경로는 저장소 밖이어야 한다. 레거시 역사 검증기를 현재 개발 트리에서 직접 실행하는 명령은 이 통합 명령을 대신하지 않는다.

## 원인과 의존관계

역사적 보존 작업 당시 전체 파일 목록을 `preserved-files.json`으로 고정했고, 이후 보존 작업은 이전 목록·검증기·소비자까지 포함했다. 따라서 현재 Core 6개 파일의 정상 변경도 여러 평가 검증기를 연쇄적으로 실패시켰다. PR #33의 입력/정답 변경 때문이 아니다.

| 과거 묶음 | 보존 항목 수 | Core/실험 파일 수 | 평가 Python 도구 수 | manifest/보존 목록 수 | 현재 트리 직접 검사 시 영향 |
| --- | ---: | ---: | ---: | ---: | --- |
| codex_counterreview_2026_11_11 | 502 | 50 | 28 | 8 | 직접 해시 검사; user-final·이후 승인 체인으로 전파 |
| user_final_2026_11_11 | 544 | 50 | 32 | 10 | 직접 검사 + 원래 이벤트/반대검토 참조 검증 |
| gold_inclusion_approval_2026_11_13 | 553 | 50 | 34 | 12 | 직접 검사 + user-final·counterreview 호출 |
| activation_preflight_2026_11_13 | 562 | 50 | 36 | 14 | 직접 검사 + 승인·최종 판단·반대검토 호출 |
| legacy_migration_2026_11_13 | 579 | 50 | 43 | 16 | 직접 검사 + preflight·역사적 Git 버전/판단 참조 |
| development_gold_v3_active_2026-11-13 | 600 | 50 | 50 | 18 | 직접 검사 + migration; 활성 소비자의 compare가 호출 |

기존 실패 7개 테스트 묶음은 위 6개 단계 중 활성 소비자 `evaluation/development_gold_active`와 5개 단계, 그리고 승인을 호출하는 `confirmation_bridge_2026_11_13`이다. `counterreview_2026_11_11` 자체는 초기 판단의 원본이며 후속 보존 목록에 포함된다. 별도 `golden_expansion/preserved-files.json` 186개와 `semantic_pilot/independent_review/preserved-files.json` 27개도 원본 그대로 검증한다.

## 파일 분류와 변경 전후 경계

| 범주 | 예 | 새 계층의 검증 위치 |
| --- | --- | --- |
| 1. 과거 평가 입력/응답/판단/승인/실행 기록 | 기존 `evaluation/` 및 `tests/fixtures/`의 모든 기준 파일 | **현재 증거 저장소**의 바이트를 기준 Git blob과 전부 대조. 삭제·변조·symlink 대체도 실패. 과거 체크아웃에서도 전체 대조와 원래 의미/관계 검증 수행 |
| 2. 과거 실행 코드·도구·환경 선언 | 당시 Core, 모든 역사적 validator/consumer/test, requirements, 출처·계약·설명서 | 고정 commit/tree/blob을 확인한 **역사적 Git 체크아웃**에서 전체 바이트 검증. 원래 manifest 값과 코드·Git ancestry를 그대로 사용 |
| 3. 현재 실행 Core·개발 문서 | `experiments/`, `docs/` | 과거 SHA와 동일할 의무 없음. 역사 버전은 2에서 보존. 현재 실험 테스트는 현재 트리에서 실행하며 전체 코드 지문을 실행 전후 비교 |
| 4. 현재 검증/소비 계층 | 새 `tools/evidence_validation/`, 향후 새 평가 버전 패키지 | 현재 트리에서 테스트·지문 검증. 기존 활성 소비자 코드는 보존 대상이므로 수정하지 않고 subprocess로 재사용 |

경로만 빼서 통과시키는 방식이 아니다. **기준 트리의 모든 파일**은 역사적 체크아웃에서 검증하고, 그중 평가/fixture는 현재 저장본에서도 중복 검증한다. 현재 변경 가능한 Core/문서의 과거 버전은 검증 가능한 Git 객체로 남는다. 기존 정답·입력·사용자 판단·승인·manifest·validator·test·consumer 파일은 이번 변경에서 한 바이트도 수정하지 않는다.

### 신뢰 기준과 실행

`boundary.py`는 full commit `879d15b8fa267010217d9310b72d1066fda74f99`와 tree `b9d324aac007ddb663984151bb1a5081a22001cf`를 코드에 명시한다. 브랜치명/HEAD/환경변수로 기준을 바꿀 수 없다. Git replacement 객체를 사용하지 않으며, `cat-file`에서 읽은 blob의 실제 객체 ID도 재계산한다. 이 코드는 다른 모든 검증기와 마찬가지로 코드 리뷰의 신뢰 경계다.

- 과거 바이트를 현재 파일로부터 생성하거나 manifest를 재봉인하지 않는다.
- 로컬 shared clone을 고정 commit으로 checkout한다. Git 이력을 유지해 migration의 과거 `git show` 검증도 그대로 수행한다. 역사적 객체가 없으면 실패하며 자동 fetch/대체 기준은 없다.
- 역사적 평가 테스트 **18개 묶음 244개**를 변경 없이 실행한다. 실패하던 7개 묶음 72개도 모두 포함하며 삭제/skip/xfail하지 않는다.
- 현재 Core의 네 실험 테스트 묶음, 기존 소비자 엔진의 현재 호환 회귀 22개, 새 경계 테스트를 현재 트리에서 실행한다. 원래 역사적 검증기의 assertion이나 기대값은 바꾸지 않는다.
- 새 평가 버전의 테스트 파일은 현재 트리에서 별도로 실행한다. 기존 과거 경로에 재설계 결과를 덮어쓰지 않는다.
- 실행 전후 현재 평가 증거, 역사적 전체 snapshot, 현재 experiments/tools/evaluation/tests/docs의 파일 목록·바이트 지문을 확인한다. report는 개별 실행 명령·테스트 수·실패/skip 수·현재 HEAD 및 파일 해시를 분리한다.

### 현재 Core 평가 소비

`consumers.py`는 기존 `development_gold_active` 소비자를 재사용한다. `run.py`에서 증거를 검증한 뒤:

1. **현재 Core**로 오프라인 29건 예측을 별도 subprocess에서 생성한다. 생산자는 기존 label-blind predict 함수를 그대로 호출하며 labels는 비교 단계에서만 해석한다. 무결성 계층의 원본 바이트 대조와 예측자의 정답 사용은 구별한다.
2. **고정된 비교 코드/환경**에서 기존 compare를 실행한다. 예측의 입력 경로·SHA·ID·전체 집합·기록 해시, 기존 지표 분모·unresolved·승인 금지를 그대로 검증한다.
3. 현재 코드 지문, 비교기 revision, 예측/비교 출력 SHA, 비교 결과를 report에 기록한다. Core diagnostics는 SP 정확도로 표시하지 않는다. 모델 호출 없는 source 결과의 unresolved를 정답으로 승격하지 않는다.

이것은 과거 점수를 최신 Core 결과로 재작성하는 작업이 아니다. 현재 실행 결과는 `/tmp`의 새 보고서이고, 기존 실행 기록은 불변이다. bridge의 저수준 함수는 검증된 root를 받는 내부 구성요소이며, 지원 진입점은 증거와 snapshot을 전후 확인하는 `run.py`다.

## 관리와 제한

- 향후 Core/현재 문서 변경: 역사 기준을 갱신할 필요 없이 같은 명령으로 현재 회귀를 실행한다. 새 Core 의미 품질/실제 모델 성능은 별도 평가다.
- 새 Golden Set 버전: 새 폴더·새 명시적 활성화 절차로 추가한다. 기존 증거·active index를 조용히 덮어쓰면 현재 무결성 검증이 계속 거부한다. 새로운 승인된 활성 버전 지원은 별도 기준 추가 설계/리뷰가 필요하며 기존 기준 제거·해시 일괄 갱신은 금지한다.
- 기존 검증기의 직접 호출은 **그 당시 트리**를 요구하는 역사적 인터페이스다. 현재 Core 변경과 함께 실행하려면 위 새 실행 계층을 사용한다. 원래 validator가 현재 트리에서 통과하도록 패치하거나 우회한 것이 아니다.
- Python·jsonschema 현재 버전과 기존 requirements를 보고한다. 당시 exact interpreter/종속성 lock은 기록되어 있지 않아 환경의 완전한 동일성을 주장하지 않는다. 현재 호스트에서 고정 코드와 원본 검증을 재실행한 결과다.
- shared clone은 원본 Git 객체에 의존하며 shallow/archive-only 환경은 지원하지 않는다. 보고서의 현재 파일 지문과 독립 체크아웃을 함께 사용한다. 실제 승인/배포 정책에는 손대지 않는다.

실제 독립 브랜치 및 PR #33 결합 결과는 [VALIDATION.md](VALIDATION.md)에 기록한다. 모든 변경은 별도 Draft PR이며 자동 병합하지 않는다.

## 레거시 전체 실행과의 차이

`evaluation/core_pipeline_2026_11_11/run_checks.py`는 발견한 모든 테스트를 **같은 현재 작업 트리**에서 실행하는 당시 도구다. 현재 Core/문서가 변경된 트리에서는 과거 `preserved-files.json`의 전체 snapshot 고정 때문에 역사적 검증 7개 묶음이 실패할 수 있다. 이것은 그 도구에서 예상되는 snapshot 차이이며, 새 전체 검증의 실패를 무시하라는 뜻이 아니다. 과거 검증기와 `run_checks.py`는 수정하지 않는다.

공식 전체 명령은 위 `tools/evidence_validation/run.py`다. 과거 원본 244개 검증은 고정 Git snapshot에서, 현재 Core/소비자/신규 평가/`tests/` 회귀는 현재 트리에서 실행한다. 개별 Core unittest 명령은 부분 회귀용이다. skip/expected failure는 수를 따로 기록하고 전체 PASS로 처리하지 않는다. 보고서의 실패·오류·skip 집계와 suite별 실제 실행 수를 확인한다.

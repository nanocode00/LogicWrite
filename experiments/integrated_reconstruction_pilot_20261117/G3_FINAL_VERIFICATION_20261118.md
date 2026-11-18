# G3 최종 검증

2026-11-18에 PR #36 브랜치 `eval/integrated-reconstruction-20261113`의 `8f748b1c35e063a347889e1fa5e7ad3f232f42e4`에서 다시 실행했다. 기준 이후 커밋과 추적 파일 변경은 없었다. 기존 미추적 `__pycache__/`는 보존했다.

## 실행 결과

| 검증 | 실제 결과 |
| --- | --- |
| G3 단위 테스트 | 18개 수집·실행, 18개 통과 |
| 오프라인 사례 | 외부 Qwen shadow 6건과 실제 G2-C 합성 2건 재현. 8건 모두 REVIEW |
| 공식 전체 회귀 | 31개 suite·962개 통과. Core 476개. failures, errors, skips, expected failures, unexpected successes 모두 0 |

단위 테스트에서 읽기 전용 출력과 필수 출력 누락, 미인가 수정·어휘 변경, 원본·후보 해시 및 trace 변조, 필수 조건의 대상 범위·부정 변경, 작업별 보류 전파, 사람 기록의 출처·권한 및 철회 상태를 확인했다. 별도로 유효한 결속과 인용을 가진 검토 레코드가 기계적 위반에 `passed`를 제출하는 입력을 실행했고, `INVALID_INDEPENDENT_REVIEW`로 거부됐다. 후보 변경은 기존 단위 테스트가 검증했고, 외부 의무만 변경해 다시 고정했을 때도 `is_current_report`는 이전 보고서를 거부했다.

## 원본·후보·판정 대조

| 사례 | 새 결과 |
| --- | --- |
| IR-001 B0/B1 | 두 보고서는 README의 “기부는 [후원 안내](FUNDING.md)에서 할 수 있습니다.”와 FUNDING의 “금전 후원은 받지 않습니다.”를 원본 근거로 보존했다. `funding-policy`는 두 사례 모두 `unresolved`다. B0는 KEEP 전용 비교 계획에서 usage를 변경해 별도 권한 위반이 잡혔고, B1의 두 후보는 원문과 같았다. B1은 후원 정책 권한자가 적용 정책을 확인할 때까지 `retain-funding-statement`를 보류하고 `retain-output-description`을 유지했다. |
| IR-002 B0/B1 | `ops` 후보에는 당직 채널·대시보드 안내가 남았다. 두 후보 모두 500건 초과 중단과 당직자 확인 전 재개 금지가 누락되어 `operator-exact-condition`이 `violated`였다. B0의 중단 조건 기재 주장과 B1의 중단 조건 접근성·`completeness_verified` 주장이 독립 검사와 충돌했다. 의미 검토는 `unresolved`였다. |
| IR-003 B0/B1 | B0는 meeting 원문과 바이트가 동일해 권한 검사를 통과했다. B1은 “1건 실패다.”를 “1건 실패.”로 바꿨고, `FORMAT_LEXICAL_CHANGE`가 생성기의 권한 준수 주장과 충돌했다. |
| 합성 MOVE | `move-photo`가 “Photograph the storage shelf.”를 catalog에서 log로 이동했다. G2-C trace와 원장 결속은 `passed`였고 일반 의미 범위는 `unresolved`였다. |
| 합성 부분 후보 | `place-label`이 catalog 내부 재배치를 실행했다. 조건이 붙은 `move-alarm`은 원본 상태로 보류됐고 질의에 근거·결정권자·필요한 결정이 남았다. |

알려진 비정형 자체 주장은 기존 오프라인 어댑터의 원시 JSON 경로 매핑으로 확인했다. `passed`는 개별 검사의 충족, `violated`는 확인된 위반, `unresolved`는 판단 유보다. 외부 Qwen 후보에는 G2-C 실행 계보를 부여하지 않았다.

## 보존과 G4 준비 상태

검증 대상 트리와 기준 커밋을 대조했다. 기존 테스트·기대값, IR 원본과 기준, 골드·사람 판단, 동결 Qwen/DeepSeek 결과, 예산 원장과 API 관련 설정은 그대로였다. 별도 워크트리의 HEAD·인덱스·미커밋 파일 스냅샷과 로컬 환경 파일의 지문도 일치했다. 발견된 결함이나 코드 수정은 없다. 모델 호출, 파일 적용, 정책 변경, 승인, G4 실행은 없었다.

이 실행은 G3의 오프라인 기계 판정 및 HITL 경계를 확인했다. 정확 문구 검사는 일반 의미 보존을 보장하지 않는다. G4 전에 실제 독립 검토자 인증 및 사람 권한 조회를 연결하고, 별도 사례에서 의역·조건 보존·근거 귀속·정책 충돌·독자 노출을 확인해야 한다.

## 재현 명령

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiments/full_document_control -p 'test_document_set_g3.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 experiments/integrated_reconstruction_pilot_20261117/g3_offline.py --output /tmp/logicwrite-g3-final-verification
PYTHONDONTWRITEBYTECODE=1 python3 tools/evidence_validation/run.py --output /tmp/logicwrite-g3-final-evidence.json
```

아래 SHA-256은 이번 실행의 원본 출력 파일을 식별한다. 공식 JSON의 `current_code.revision`은 이 검증 보고서 커밋 전의 기준 HEAD를 가리킨다.

| 출력 | SHA-256 |
| --- | --- |
| `logicwrite-g3-final-evidence.json` | `724985b15a950e0f27db8ea8abfa77e1459ffb561c3cf98954b1f593fcc7a41d` |
| `logicwrite-g3-final-unit.log` | `ffec469580c18590b0d6cf6e64513474a73a712f62e5e87bd57e8ecafb72e0dc` |
| `IR-001-B0.json` | `96a692bbb8c415abf28a48ddb992e28c8152829e53361ce5d9e16917ce92ae0d` |
| `IR-001-B1.json` | `d2c42e5caceda932857190603d73a787fe88adacf58c0fe915d29c92d37e456e` |
| `IR-002-B0.json` | `464da61f19ba4fb61d41740fcf6c243d73882dfe89d3557cece165ccf6dc1f3e` |
| `IR-002-B1.json` | `5fa7cdd27cf28ce5c08f1ccedacfc30b738b4cdfe7796a77a48a723179ac4fbb` |
| `IR-003-B0.json` | `b3ec8ef1ee209b81457d223d8deb845325d70edcda10d98445dd59a566ef7e7a` |
| `IR-003-B1.json` | `d0aa58856ce0eb92bcacfcd9ed7c88fb9161096fe0575f1517bf89a5a047466e` |
| `synthetic-move.json` | `f1ace916522a35a62258e1bbf507f708b1ed8f1c8db7177ff82c655fa9ce2fd2` |
| `synthetic-partial.json` | `d6430dc2362c2b60113d5c74ec69d4f93fa6f9e19400b55644b7cd2c4630b0d2` |

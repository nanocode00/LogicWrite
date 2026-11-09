# RW-001 A/B 실행과 의미 판단 비교

2026-11-09 Asia/Seoul. **B가 전반적으로 개선됐다는 결론은 내릴 수 없다.** 이번에는 정보 기능 분리와 관계 방향의 개선 가능성을 관찰했지만, 유효한 B 평가에서도 요구사항을 설치 동작으로 확대하는 문제가 남았고 B2 한 번은 JSON 오류로 수용하지 못했다.

이 보고서는 Codex 모델의 원문 대조와 관찰이다. 독립 사람 검수·골드 정답·의미 검증 엔진·성능 점수가 아니다. 모든 의미 판단의 사람 검토는 pending이다. 동작이 거짓이라고 확정하는 것이 아니라 **주어진 원문이 그 주장을 뒷받침하는지**를 검토한다.

## 조건과 근거 위치

- PR #8은 `e188cde`로 병합 후 분기했다. [규약](protocol.md)은 `28fd2c3`, 실행 코드는 `16b88c1`에서 모델 호출 전에 커밋했다. 결과를 보고 프롬프트를 수정하거나 재시도하지 않았다.
- 입력은 기존 RW-001 파일과 바이트 동일하다. SHA-256: `f7256434ef3780caf6d1863185f2100ee9035b0c8f4adbc1ebe9b3f5abc0d960`.
- A는 기존 프롬프트 그대로다. B1은 원문·문맥으로 추출하고 B2는 원래 계약과 고정된 B1 목록을 평가한다. 최종 B 목록에서 평가 필드 외의 모든 B1 필드가 같음을 코드로 확인했다.
- 모든 6회 호출에 `gemini-4-argon-medium` 별칭, mode plan, text output, slash-command expansion 비활성화를 동일 지정했다. 모델의 실제 백엔드 리비전·seed/temperature는 미확인이다.
- 실행 시각은 09:22:40–09:25:56 KST다. 아래 시간은 로컬 CLI 프로세스 관측값이며 모델 토큰 비용·제품 성능 벤치마크가 아니다.
- 원시 stdout/stderr·프롬프트·meta·검토 출력은 로컬 `runs/RW-001-20261109/pair-1/` 및 `pair-2/`에 보존하고 Git에서는 제외했다. [비교 관측 JSON](comparison.json)은 digest와 상태·선택한 분석 필드의 파생 요약이며 원시 제공자 로그가 아니다. 실행 manifest의 입력·규약·코드 hash를 재대조했다.

## 실제 모델 실행 결과

| 반복 | A | B1 | B2·최종 B | CLI 관측 시간 |
| --- | --- | --- | --- | --- |
| 1: A→B1→B2 | 3개 단위, 인용/참조 통과, REVIEW | 5개 단위, 인용/참조 통과 | 프로세스 exit 0이지만 JSON 문법 오류. 최종 STOPPED, 유효한 평가/결합 없음 | A 31.70초; B1 22.48초+B2 31.34초=53.82초 |
| 2: B1→B2→A | 4개 단위, 인용/참조 통과, REVIEW | 5개 단위, 인용/참조 통과 | 5개 단위 평가를 결합, 인용/참조 통과, REVIEW | A 33.17초; B1 35.15초+B2 41.70초=76.85초 |

반복 1의 B 최종 보고서가 0개 단위를 갖는 것은 실패 보고서에 수용된 분석이 없다는 뜻이며, B1이 정보를 0개 추출했다는 뜻이 아니다. B2 파싱 실패는 숨기지 않았다. 같은 1사례의 2반복에서 관찰한 유효 응답 수를 일반적인 성공률로 확대하지 않는다. 모두 전달 승인은 false이며 유효 결과의 semantic_fidelity도 not_run이다.

## 정보 단위별 비교

아래 묶음은 원문 기능을 대조하기 위한 관찰용 정렬이며 새 정답 분할이 아니다. 서로 다른 기능을 묶었다고 언제나 오류가 되는 것은 아니고, 단위 수가 많다는 이유로 개선으로 채점하지 않는다.

| 원문 정보·기능 | A 반복 1 | A 반복 2 | B1 두 반복과 수용된 B 반복 2 |
| --- | --- | --- | --- |
| 이번 릴리스의 PKG 적합성 | u1에서 DMG 비교와 초보자 이점도 함께 요약. irrelevant / optional / preserve_elsewhere_candidate | unit-1로 분리. irrelevant / optional / preserve_elsewhere_candidate | u1로 분리. B2도 irrelevant / optional / preserve_elsewhere_candidate |
| DMG와 drag-and-drop 앱 비교 | u1에 포함 | unit-2에서 앱 요구사항과 합침 | u2로 분리. B2는 irrelevant / optional / preserve_elsewhere_candidate |
| Applications·Node/cloudflared·non-blocking Doctor 요구사항 | u2. relevant / useful / undecided | DMG 비교를 포함한 unit-2. uncertain / optional / preserve_elsewhere_candidate | u3. B2는 relevant / useful / retain_current. 요구사항을 실제 패키지 동작으로 읽는 근거 문제는 남음 |
| PKG의 초보자 install-and-open 이점 주장 | u1에 포함 | unit-3. irrelevant / optional / omit_candidate | u4로 분리. B2는 uncertain / optional / preserve_elsewhere_candidate |
| 향후 signed/notarized DMG 가능성 | u3. irrelevant / optional / preserve_elsewhere_candidate | unit-4. irrelevant / optional / preserve_elsewhere_candidate | u5. B2는 irrelevant / optional / preserve_elsewhere_candidate |

B1은 두 반복에서 같은 기능 구분을 제안했지만 A도 반복별로 분할이 달랐다. 기존 A가 항상 정보를 혼합한다거나 B가 정답 개수를 찾았다고 볼 수 없다. 반복 1 B2는 유효한 평가가 아니므로 표의 B 평가 열은 반복 2에만 해당한다.

## 의미 검토 관찰과 근거

### 관찰 1 — 기능 분리가 독립 판단을 쉽게 하지만 판단 정확성까지 보장하지 않는다

원문은 DMG 일반 비교와 이 앱의 요구사항을 `but`로 연결한다. A 반복 2의 unit-2는 둘을 묶어 uncertain/optional을 제안했다. B1은 두 반복에서 각각 u2와 u3로 구별하고 관계를 남겼다. 수용된 B2는 u2를 irrelevant, u3를 relevant라고 서로 다르게 평가할 수 있었다.

이는 서로 다른 판단을 표현할 여지가 생겼다는 관찰이다. 그중 u3의 판단 근거에는 아래 범위 확대가 남았으므로 이를 올바른 정보 선택으로 판정하지 않는다. u3 내부의 세 요구사항도 한 단위에 남았다. 이 세 항목에 다른 판단이 필요한지는 목적과 후속 사용을 보고 사람이 확인해야 하며 분할을 일괄 강제하지 않는다.

### 관찰 2 — 요구사항에서 실제 패키지 동작으로의 확대가 A/B 모두 남는다

원문 target 79–80행은 다음과 같이 **앱의 필요·요구사항**을 말한다.

> this app needs to install a menu bar runtime under Applications,
> bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.

A 반복 1 u2는 statement에서는 needs를 유지했으나 exposure에서 이를 `the fact that the macOS PKG installs ...`로 표현했다. A 반복 2 unit-2의 reason도 `embedded facts about what gets installed`로 읽었다.

B 반복 2 u3 역시 statement에서는 needs를 유지했지만 exposure에서 `Expose the factual package behaviors`라고 지시하고 `retain_current`를 제안했다. uncertainty에 실행이 미검증이라고 적어도, 요구사항을 실제 설치 동작이라는 **원문의 주장**으로 바꾼 점은 해결되지 않는다. 원문 요구가 패키지에서 실제 이행됐는지 또는 안 됐는지를 이 실험은 입증하지 않았다. 주변 Linux 설치 설명도 macOS PKG의 이행 증거로 전용할 수 없다.

따라서 추출 statement만 점검하면 평가 근거·노출 제안에서 발생한 확대를 놓친다. 인용/참조 검사는 이 문제를 탐지하지 못했고 정상적으로 REVIEW를 유지했다. B가 이 핵심 문제를 해결했다는 근거는 없다. 반복 2의 B는 보존 제안까지 retain_current로 정해 원문이 허용하는 주장 범위를 더 엄격히 검토할 필요가 있다.

### 관찰 3 — supports의 방향과 자연어 근거가 A에서 어긋난다

A 반복 1 u1은 u2를 supports 대상으로 가리키면서 이유에는 “패키징 선택은 u2의 요구사항으로 정당화된다”고 썼다. 이 이유는 u2→u1 방향에 해당한다. 같은 결과의 u2→u1도 있어, 이 원문에서 선택이 자기 요구사항을 입증하는 듯한 역방향이 추가됐다.

A 반복 2 unit-1→unit-2 및 unit-1→unit-3도 각각 대상이 선택을 설명하는 이유라고 쓰면서 화살표를 반대로 둔다. 반면 B1 두 반복의 요구사항 u3→선택 u1, 초보자 이점 u4→선택 u1은 이유와 방향이 맞는다. 이것은 본 사례의 관계 표현에서 관찰한 개선 가능성이다. 모든 관계가 의미적으로 검증됐거나 supports 순환을 일반적으로 금지해야 한다는 결론은 아니다. 다음 프롬프트에서는 관계의 방향 정의도 양쪽에 동일하게 명시할 필요가 있다.

### 관찰 4 — A 반복 2의 omit_candidate에는 보존 의무 판단의 근거가 부족하다

A 반복 2 unit-3은 초보자 이점 주장을 omit_candidate로 두고, 설치 행동 지시가 아니라는 이유를 제시한다. 이는 현재 노출 필요성이 낮다는 근거이며 다른 역할의 의사결정 기록에도 보존할 필요가 없다는 근거는 아니다. 기존 입력의 임의 폐기 금지와 공통 모델의 omit_candidate 설명에 비추어 추가 근거가 필요하다.

A 반복 1은 같은 내용을 포함한 u1을 preserve_elsewhere_candidate로 두므로 A에서도 판단이 달랐다. 수용된 B 반복 2 u4는 preserve_elsewhere_candidate지만 B2의 유효 평가가 한 번뿐이므로 일반적인 개선으로 해석하지 않는다. 어느 방식도 실제 삭제를 수행하지 않았다.

### 관찰 5 — 조건은 인용 포함, 정규화, 관계 연결을 각각 봐야 한다

`For this release`, `non-blocking`, 향후 DMG의 `signed/notarized`와 `can still be added later`는 각 결과의 인용과 정규화된 관련 주장 안에 남아 있다. 별도 condition 요소가 없다는 이유만으로 조건을 잃었다고 채점하지 않는다. B1은 drag-and-drop 적용 조건을 별도 condition으로 표현했고 요구사항·초보자 이점을 선택의 근거로 연결했다.

다만 유효한 B2가 u3를 “factual package behaviors”로 읽는 문제는 조건 문자열이 존재해도 생겼다. 서명 관련 미래 가능성으로 현재 PKG의 서명 상태를 확정해서도 안 된다. 수용된 B2는 그 상태를 추론할 수 없다고 명시했으며, A/B의 관련 질문들도 실제 미서명을 확정한 증거가 아니다.

### 관찰 6 — B의 새 실패와 고정 목록의 비용

반복 1 B2는 문자열 안의 `a "Why PKG" design justification`에서 따옴표를 JSON용으로 escape하지 않아 line 1 column 2694에서 파싱이 중단됐다. 프로세스 exit 0과 유효한 구조화 응답은 다르다. 응답을 자동 수정하거나 같은 조건으로 다시 호출하지 않았으며, 최종 평가는 STOPPED로 남겼다. 관련 실패 보존/미결합 회귀 테스트를 실행 후 추가했다. 실행 중 프롬프트·규약·runner는 바꾸지 않았다.

반복 2 B2는 u3가 세 요구사항을 합친 단위라 재추출이 필요할 수 있다고 uncertainty/질문에 남겼다. 코드가 목록 불변성을 지켜 B2가 조용히 분할을 바꾸지 못하게 한 것은 책임 경계의 장점이다. 동시에 B1의 분할 오류를 B2 한 번으로 고칠 수 없는 비용이 있다. B1과 B2의 릴리스 범위 질문도 최종 질문 목록에 유사하게 반복돼 검토량이 늘었다.

## 정적 테스트와 실제 실행의 구분

- 실제 모델 호출: 사전 규약의 2반복·6회. 모두 프로세스 exit 0. A 두 개, B1 두 개, B2 한 개가 각 단계 구조/출처 검사를 통과했고 B2 한 개는 JSON 오류다. 의미 검증을 통과한 결과는 없다.
- 새 A/B 회귀 테스트 17개: A 프롬프트 동일성, B1 계약 보류/B2 포함, 입력·목록 digest, 평가 누락/중복/미존재 ID/목록 편집 거부, 인용 오류, 어댑터의 중립값 비노출, 두 반복 순서, 실패/JSON 오류 보존, 미재시도·미결합, REVIEW/전달 승인 false를 확인한다.
- 기존 추출·분석 27개와 게이트 31개도 통과했다. 총 75개는 코드의 구조·경계 테스트이며 모델 의미 판단의 정답률을 뜻하지 않는다.
- fixture 2개·RW-001 입력/답안·공통 모델·이전 실험 코드와 재검토 장부는 바이트 단위로 보존한다. 새 공통 필드/골드/독립 사람 승인/실제 목적지 이동·수정은 없다.

## 실행 후 코드 검토에서 수정한 추적 문제

추가 모델 코드 검토에서 nonzero exit/timeout 발생 시 실패 보고서가 실제 실패 단계의 stdout 대신 빈 값(A/B1)이나 이전 B1 응답(B2)의 digest를 가리킬 수 있음을 찾았다. 재현 테스트 2개로 확인하고 실패 예외에 단계·stdout을 보존해 보고서에 연결하도록 수정했다. 모든 제공자 호출이 exit 0이었던 이번 6회에는 해당 분기가 실행되지 않았으므로 관측 결과·원시 응답·보고서는 바꾸지 않았고 모델도 다시 실행하지 않았다.

실제 실행 manifest의 runner digest는 실행 당시 `16b88c1`의 코드를 가리킨다. 현재 runner는 이 사후 수정이 포함돼 digest가 다르다. 이는 규약이나 결과에 맞춘 프롬프트 조정이 아니라 실패 provenance 정정이며, 모델 결과를 보기 전과 후의 코드 상태는 Git 이력으로 구별한다. 후속 검토는 이 분리와 digest 연결을 다시 확인했다.

## 한계와 후속 권고

이 사례와 이 두 반복으로 B의 전반적 우수성이나 열등성을 확정하지 않는다. B의 유효한 평가가 한 번뿐이고 모델 별칭의 내부 리비전·sampling을 고정하지 못했다. B는 2회 호출과 더 긴 문맥을 쓰며 총 연산 예산도 다르다. Codex 수작업 검토는 독립 사람 판단이 아니고 원문 동작의 사실성 검증도 아니다.

1. **B를 기본 경로로 승격하지 않는다.** 기능 분리와 관계 방향의 관찰은 남기되 핵심 범위 확대와 구조화 출력 실패를 함께 평가해야 한다.
2. 다음 별도 실험에서는 statement뿐 아니라 assessment.reason/exposure의 주장까지 원문 양태와 대조한다. 기존 표현/관계 모델 안에서 요구·평가·관측·가능성을 보존하도록 하고 고정 분할/정답 문구를 넣지 않는다. 미결정은 REVIEW로 남긴다.
3. B2가 목록 문제를 찾으면 원인 단계로 재추출을 요청하는 흐름을 검토하되 무제한 재시도나 자동 승인으로 연결하지 않는다. 이번에는 그 루프를 구현하지 않았다.
4. JSON 제약 출력을 비교하려면 A/B 양쪽에 동일하게 적용하는 새 규약으로 실행한다. 이번 실패를 사후 정리해 유효 결과로 바꾸지 않는다.
5. 아래 항목을 사람이 먼저 검토한 후 다음 사례/반복으로 확장한다. 기존 20건은 개발·회귀 자료이며 새 홀드아웃으로 보고하지 않는다.

| 사람 검토 항목 | 현재 상태 |
| --- | --- |
| u3 등의 “needs”를 설치 동작으로 확대했다는 관찰과 허용 가능한 주장 범위 | pending |
| 묶인 정보에 독립 판단이 실제 필요한지와 적절한 관계 방향 | pending |
| 초보자 이점의 보존 제안 및 원문 조건의 충분성 | pending |
| B 고정 목록의 효용·재추출 경로와 JSON 실패의 후속 통제 | pending |

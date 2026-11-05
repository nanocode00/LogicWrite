# RW-001–RW-020 실제 문서 재검토

> 2026-11-05 (Asia/Seoul). PR #4 병합 후 main `d15dcb99ff30d1106d4f3e3b6d8a0e7f08b2ec58` 기준. **모델의 수작업 검토 제안이며 골드셋·사람 승인·자동 검증 결과가 아니다.** 기존 fixture와 원본 저장소는 수정하지 않았다.

[정보 단위·출처·범위별 판단 기록](real-world-20-reassessment.json)은 이 보고서의 근거 장부다. 실행 가능한 스키마, AnalysisResult/ValidationPlan/ValidationReport 구현체 또는 새 fixture 형식으로 채택한 파일이 아니다. 원본 [후보 JSON](../../tests/fixtures/real-world-candidates.json), [공통 모델](../data-model-and-interfaces.md), [요구사항](../requirements.md), [평가 정책](../evaluation.md)을 구별해 읽는다.

## 검토 범위와 증거 경계

- 18건의 Git 파일 사례는 정확한 커밋에서 13개 source 파일을 다시 조회했다. 추가 근거·목적지 12개를 포함한 **25개 Git blob**은 UTF-8 바이트로 Git blob SHA와 SHA-256을 계산해 대조했다. source 행의 발췌와 RW-018 추가 문맥도 저장 fixture와 일치했다. 전체 파일을 조회했지만 정독·판단 범위는 사례별 발췌와 표시한 주변/관련 구간이다. 전체 파일의 모든 사실을 검수했다는 뜻이 아니다.
- RW-019/020은 **2026-11-02 저장된 PR 본문 발췌**가 평가 입력이다. 현재 본문의 해당 구간·head SHA도 대조했지만 head SHA로 과거 본문 전체를 고정할 수 없다. 실제 PR diff의 모든 문장 불변을 검증하지 않았다.
- source assertion은 원문이 그렇게 말한다는 근거다. 구현·성능·실서비스·테스트의 사실성을 독립적으로 입증하지 않는다. README/가이드/과거 annotation은 현재 사용자 의도를 대신하지 못한다.
- RW-001/002는 설치 행동 안내와 패키징 선택 논거를 구분하고, RW-007은 자료 탐색·선택을 위한 정보 선별과 재구성으로 후속 사용자 피드백을 반영했다. 이 범위의 사용자 의견을 독립 사람 전체 검수나 골드 승인으로 확대하지 않는다.
- 기존 라벨은 비교 가설로만 사용했다. 기존 annotation과 PR #4 설계 예시를 읽은 상태이므로 **맹검 또는 독립 정답 실험이라고 주장하지 않는다.** source와 목적에서 새 근거를 찾고 다른 결론을 허용했다. fixture에 기록된 과거 사용자 정정과 문체 선호는 원래 대화가 없는 간접 기록으로 분리했다.
- Antigravity에는 초점 5건의 판단 초안을 읽기 전용으로 맡겼다. Codex는 원문·차원 분리·미확인 주장과 diff를 직접 대조했다. 유용했던 하단 Star Pitch와 실제 OAuth 문서 링크는 직접 재조회했다. AGY의 RW-008 기존 템플릿 안 재구성안은 사용자 목적 확인 전 고정하지 않았다. 모델 간 검토는 **독립적인 사람 검토가 아니다.** AGY 원시 응답·개인 cache·로그는 저장소에 포함하지 않았다.

## 읽는 방법과 계약·ValidationPlan 대응

각 case의 contract review는 fixture의 독자/목적을 그대로 기록하면서 현재 문서 역할·명시적 개편 목표·추론 가정을 분리한다. `current`는 원문 문서 범위다. 후보 목적지는 `output_scopes`에 별도 역할로 선언하며, 조회한 실제 문서만 source snapshot에 연결한다. 등록되지 않은 경로를 만들어 이동하지 않는다. 현재 source의 `retain_current`는 해당 문서 정보 보존이며, 같은 문서의 순서·표현 수정과 양립한다.

표의 중요도·관련성은 **현재 출력 범위** 판단이다. `required`는 남기는 주장의 올바른 해석에 필수라는 이 검토의 제안이며, 새 사용자 요구를 임의 확정했다는 뜻이 아니다. 각 단위의 보호 대상은 정규화 주장에 포함된 수치·조건·귀속·식별자·출처이며 JSON의 source span으로 역추적한다. 같은 행에 여러 주장이 있어 겹치는 span을 허용했다. span은 고정 text의 zero-based Unicode code point `[start,end)`이며 줄바꿈/Unicode를 정규화하지 않았다. Git source는 source manifest의 exact blob, PR은 JSON에 저장한 발췌 snapshot을 기준으로 한다. 이는 문장 내부 최소 offset을 확정한 언어 주석이 아니라 근거가 포함된 행 구간이다.

실제 ValidationPlan 엔진이 없으므로 사례마다 다음 다섯 가지 **수작업 관찰**을 장부에 남겼다. 정책·버전 고정, mandatory instance reconciliation은 아직 설계 수준이다.

| 수작업 확인 범주 | 이번에 기록한 내용 | 남는 검사 |
| --- | --- | --- |
| 필수 정보·조건 | 단위별 주장/수치/모집단/귀속/해석 조건 | 승인한 요구사항과 전체 수정본의 누락 검사 |
| 출처 대응 | 고정 snapshot·digest·원문 행·unit span | 독립 사람의 분할/정규화 검토 |
| 목적·배치 | 현재 문서 역할과 목표 계약 비교; 목적지/순서 제안 | 계약 승인·모든 목적지와 통합본 검사 |
| 표현 의미 | KEEP과 독립적으로 REVISE/COMPRESS 필요성 검토 | 실제 수정문·완성 문서의 양방향 의미 검사 |
| 불확실성 | 모호한 목적·미확인 동작·추가 증거 기록 | 사람 판단·원시 검증 증거 |

어떤 사례도 최종 수정된 전체 문서 집합을 제출하지 않는다. **20건 모두 수작업 `REVIEW` 권고이고 engine gate는 미실행**이다. 이를 실행된 `unresolved` 결과나 engine `PASS/FAIL/STOPPED`로 직렬화하지 않는다. 향후 실제 계획에서는 계약/범위/참조 → 추출 coverage/보호 → 배치/목적지/통합 → 최종 trace/수치·조건/의미/전체 문서 검사를 모두 포함해야 한다. 이동 후보만 있어도 목적지 검사는 적용된다. 결과 누락은 `STOPPED`, 확인한 불확실성은 `REVIEW`, 참조 오류는 `FAIL`이라는 설계 구분을 유지한다.

우선순위는 P1=오해·필수 조건 손실·다운로드/작업 판단에 영향, P2=계약·구조·배치 개선, P3=선택적 표현 개선이다. **수정 필요성은 외부 source에 대한 제안**이며 이번 PR에서 그 source를 수정했다는 뜻이 아니다.

## 기존 가설과의 비교

비교는 단일 라벨 정확도가 아니라 보존/배치/표현/근거의 차이다. 부분 일치는 원래 nuance를 반박한다는 뜻이 아니라 이동/축약 대상 범위를 더 좁히거나 근거를 보완한다는 뜻이다.

| 사례 | 기존 잠정 액션 | 새 검토와의 관계 | 실제 수정 제안 |
| --- | --- | --- | --- |
| [RW-001](#rw-001) | MOVE | 일치·사용자 피드백 반영 | P2: 선택 근거를 패키징 결정 기록으로 MOVE 후보; 목적지 확인 전 원문 보존 |
| [RW-002](#rw-002) | MOVE | 일치·사용자 피드백 반영 | P2: 선택 근거를 패키징 결정 기록으로 MOVE 후보; 목적지 확인 전 원문 보존 |
| [RW-003](#rw-003) | KEEP | 일치·보완 | P3: 선택적 REVISE/COMPRESS·placement; 필수 수정 없음 |
| [RW-004](#rw-004) | KEEP | 일치·보완 | P3: 가독성 개선 선택; 조건 유지 필수 |
| [RW-005](#rw-005) | KEEP | 일치·보완 | P3: KEEP+선택적 REVISE/COMPRESS; 필수 수정 없음 |
| [RW-006](#rw-006) | KEEP | 일치·보완 | P3: 기본 KEEP; 줄바꿈·목록 분리만 선택 |
| [RW-007](#rw-007) | COMPRESS | 부분 일치·정보 선별과 배치 재설계 | P2: 자료 역할·링크 KEEP, 경험 목록으로 재배치·축약; 상세 기록은 보존 확인 후 중복 정리 |
| [RW-008](#rw-008) | FLAG | 일치·구체화 | P1: 목적/측정 경계 확인 후 구조 재설계; 자동 축약 차단 |
| [RW-009](#rw-009) | MOVE | 부분 일치·조건 강화 | P2: 목표 계약·목적지 확정 후 일부 MOVE; 원문 삭제 금지 |
| [RW-010](#rw-010) | MOVE | 부분 불일치 | P2: 분량 규칙 적용 범위 확인·REVISE; 전면 MOVE 불필요 |
| [RW-011](#rw-011) | KEEP | 일치·보완 | P3: 선택적 문장 분리; 필수 수정 없음 |
| [RW-012](#rw-012) | MOVE | 부분 일치·수치 문맥 불일치 | P1: retention 표본 수 확인·조건·귀속 노출; 확인 전 MOVE 금지 |
| [RW-013](#rw-013) | MOVE | 일치·세분화 | P2: 확인한 설계 문서와 중복 통합 후보; 수정본 검토 전 source 보존 |
| [RW-014](#rw-014) | FLAG | 부분 일치·근거 제한 | P1: 완벽 지원/실시간 근거 확인 또는 범위 한정; 이모지 정리는 P3 |
| [RW-015](#rw-015) | REVISE | 일치·재확인 | P1: 본문 다운로드 URL REVISE 제안; 외부 source는 수정하지 않음 |
| [RW-016](#rw-016) | MOVE | 부분 불일치 | P2: 세부 기준 중복 통합 선택; 상태·범위 전면 MOVE 반대 |
| [RW-017](#rw-017) | REVISE | 일치·보완 | P1: 잘못 일반화될 테스트 예시 REVISE; 기록 3건 요구 보존 |
| [RW-018](#rw-018) | KEEP | 부분 일치·추가 MOVE 재검토 | P1: 호스팅 repository/root 문맥 REVISE; MOVE는 P3 선택 |
| [RW-019](#rw-019) | KEEP | 일치 | P3: 현 설명 수정 불필요; diff 검토는 별도 필요 |
| [RW-020](#rw-020) | KEEP | 일치 | P3: 설명 수정 불필요; 사실·diff 검토는 별도 |

## 사례별 정보 단위 판단

### RW-001

**README의 설치 안내와 PKG 선택 근거 분리** — 기존 `MOVE` / 새 비교: **일치·사용자 피드백 반영**.

출처: [README.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/README.md); 조회/검토 문맥: README L44–87. snapshot `S01`.

**목적 판단:** 처음 설치하는 독자가 앱의 용도와 설치 방법을 파악하는 범위다. 사용자 피드백에 따라 설치 행동 안내와 패키징 의사결정 근거를 구분한다. 발췌의 Applications·번들·Doctor는 PKG를 선택한 이유를 뒷받침하며, 설치자가 수행할 절차로 제시된 것이 아니다. 순서가 자연스럽다는 이유로 현재 README의 설치 안내에 포함할 근거로 삼지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-001-a | 78–80 | 이번 릴리스 PKG 선택: Applications 메뉴 막대 runtime, Node/cloudflared 번들, non-blocking 설치 후 Doctor 필요. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | Applications·Node/cloudflared·non-blocking Doctor는 PKG 선택을 정당화하는 근거다. 원문의 논증 역할을 설치 절차로 바꿔 KEEP하지 않는다. |
| RW-001-b | 81–81 | PKG는 초보자의 install and open 흐름을 명료하게 한다. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 초보자에게 명료하다는 평가는 PKG 선택 이유이며 설치자가 수행할 행동이 아니다. 평가를 실증된 사용성 결과로 강화하지 않고 의사결정 기록에 보존한다. |
| RW-001-c | 78–79 | DMG는 drag-and-drop 앱에 적합하다는 대안 비교. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | DMG의 drag-and-drop 적합성은 패키징 대안 비교이므로 설치 행동 안내 범위 밖이다. 선택 근거로 별도 보존할 가치가 있다. |
| RW-001-d | 81–82 | signed/notarized DMG는 나중에 추가할 수 있다는 가능성. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | signed/notarized DMG의 향후 추가 가능성은 현재 설치 절차가 아니다. 의사결정 기록에 보존하되 제공 사실이나 확정 계획으로 바꾸지 않는다. |

**배치·통합:** a/b/c/d 모두 패키징 의사결정 기록의 보존 후보로 둔다. README에는 실제 제공 패키지·다운로드·실행 등 설치 행동 안내를 남기되, 이 발췌에서 새 설치 절차를 만들어내지 않는다. 목적지 문맥과 통합 후 정보 보존을 확인하기 전 source removal은 blocked이며 MOVE 완료가 아니다.

**수작업 확인:** 설치 행동과 선택 근거를 혼동했던 판단을 정정했다. 이번 릴리스 한정, Applications·Node/cloudflared·non-blocking Doctor, 초보자 적합성 평가, DMG 비교와 미래 가능성은 의사결정 근거로 보존한다. RW-002와 통합할 때 서로 다른 조건을 유지한다. 실제 설치나 목적지 검증을 새로 실행한 것은 아니다.

**미확인·사람 검토:** 패키징 결정 기록의 실제 경로·독자·기존 내용과 통합 결과. 이동 후 README의 실제 다운로드·실행 안내가 충분한지도 확인해야 한다.

**실제 수정 필요성·우선순위:** P2: 선택 근거를 패키징 결정 기록으로 MOVE 후보; 목적지 확인 전 원문 보존. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-002

**설치 가이드에서 패키징 선택 근거 분리** — 기존 `MOVE` / 새 비교: **일치·사용자 피드백 반영**.

출처: [docs/INSTALL.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/INSTALL.md); 조회/검토 문맥: INSTALL L1–56. snapshot `S02`.

**목적 판단:** 초보 설치자가 설치 과정을 완료하는 것이 목적이다. 사용자가 이 검토에서 명시한 경계는 다운로드·실행 등 설치 행동 안내와 PKG를 선택한 이유의 분리다. 원문의 FAQ 배치나 한국어라는 사실은 선택 근거를 설치문서에 KEEP할 이유가 아니다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-002-a | 22–22 | 이번 릴리스 PKG 제공·선택; Applications 메뉴 막대 앱, 번들 runtime, 설치 후 Doctor 흐름. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | Applications·번들 runtime·Doctor는 PKG를 선택한 근거로 서술됐다. 다운로드·설치 행동 안내가 아니므로 설치 가이드의 현재 범위에서는 이동 후보다. |
| RW-002-b | 22–22 | 초보자가 설치 흐름을 덜 헷갈리게 한다는 선택 이유. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 초보자가 덜 헷갈린다는 평가는 패키징 결정 이유다. 문구만 다듬어 설치 가이드에 유지할 근거가 되지 않는다. |
| RW-002-c | 22–22 | DMG drag-and-drop 비교. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | DMG drag-and-drop 비교는 설치 절차가 아니라 대안 평가다. 비교 길이에 관계없이 의사결정 기록의 보존 후보로 판단한다. |

**배치·통합:** a/b/c 모두 패키징 의사결정 기록으로 MOVE 후보이며, 설치 가이드에는 실제 PKG 다운로드·실행과 필요한 설치 절차를 남긴다. Applications·번들 runtime·Doctor를 언급했다는 이유만으로 발췌의 선택 논거를 설치 절차로 재해석하지 않는다. RW-001과 통합할 때 조건·출처와 접근성을 확인하되, 언어 차이 자체를 현지 보존 근거로 삼지 않는다. 목적지 미확인으로 source removal은 blocked다.

**수작업 확인:** 기존의 순서가 타당하고 짧은 이유 설명은 KEEP 가능하다는 결론을 철회했다. 발췌는 PKG 선택을 정당화하는 설명이며 다운로드·실행 지시와 구별된다. Applications·번들 runtime·Doctor·초보자 적합성·DMG 비교를 의사결정 근거로 보존한다. RW-001의 non-blocking을 한국어 원문 자체의 확인 사실로 추가하지 않는다.

**미확인·사람 검토:** 패키징 결정 기록의 실제 경로·독자·기존 내용, 통합 시 조건·출처 보존과 독자의 접근성. 이동 후 가이드의 다운로드·실행 절차 충족 여부.

**실제 수정 필요성·우선순위:** P2: 선택 근거를 패키징 결정 기록으로 MOVE 후보; 목적지 확인 전 원문 보존. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-003

**별점 요청의 KEEP·순서·표현** — 기존 `KEEP` / 새 비교: **일치·보완**.

출처: [README.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/README.md); 조회/검토 문맥: README L7–22, L432–437. snapshot `S01`.

**목적 판단:** README 방문자가 주 독자다. 별점 요청은 참여 유도 의도를 원문에서 확인할 수 있으나 이를 명시적 사용자 계약의 새 필수 목적으로 승격하지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-003-a | 21–21 | 더 많은 builders에게 알리기 위한 repo star 요청. | relevant / optional | `retain_current` / COMPRESS | 원문에 직접 드러난 참여 유도이며 정보 보존과 문구 길이는 독립이다. |
| RW-003-b | 21–22 | ChatGPT가 안전하게 repo 작업을 수행하도록 하자는 제품 지향. | relevant / useful | `retain_current` / REVISE | 구호를 기능 보증으로 바꾸지 않고 별점 요청과 함께 간결화할 수 있다. |

**배치·통합:** 현 위치 앞에 제품 설명·안전 경계·설치 링크가 이미 있다(L7–19). 현재 위치를 결함으로 확정하지 않는다. 같은 README L432–437에 이미 Star Pitch 섹션이 있다. 해당 섹션과의 중복 통합/재배치는 placement이며 MOVE가 아니다. 하단 문구의 cloud upload 경계를 별도 분석해야 하므로 상단 요청의 즉시 삭제를 정당화하지 않는다.

**수작업 확인:** 별점 요청과 제품 지향을 분리해 읽었다. 표현 수정은 둘을 담되 safely를 보안 보장으로 확장하지 않아야 한다. 하단 Star Pitch의 별점 요청도 원문에서 직접 확인했다. 상단 노출이 설치를 방해한다는 관측 증거는 없다.

**미확인·사람 검토:** 작성자의 참여 유도 우선순위·원하는 문체. 전체 README의 전수 의미 검토는 하지 않았다.

**실제 수정 필요성·우선순위:** P3: 선택적 REVISE/COMPRESS·placement; 필수 수정 없음. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-004

**Quick Tunnel의 선택 조건** — 기존 `KEEP` / 새 비교: **일치·보완**.

출처: [README.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/README.md); 조회/검토 문맥: README L52–74. snapshot `S01`.

**목적 판단:** 첫 설정 사용자가 임시·고정 연결을 선택한다. 원문 Current Release와 Linux/WSL bootstrap 뒤에 실제 첫 실행 설명이 있다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-004-a | 70–71 | first-run wizard가 ChatGPT web connector를 설정할 수 있다. | relevant / useful | `retain_current` / unchanged | 첫 설정 기능의 가능성 표현을 유지한다. |
| RW-004-b | 71–72 | 기존 Named Tunnel/hostname이 없는 사용자는 임시 Quick Tunnel을 택해 Cloudflare 계정·도메인·Tunnel Token 없이 진행할 수 있다. | relevant / required | `retain_current` / COMPRESS | 무조건 모든 터널에서 자격증명이 불필요하다는 일반화 금지. |
| RW-004-c | 72–74 | *.trycloudflare.com 주소는 tunnel 재시작 시 변경되며 편의·개발 경로이고 안정적인 production hostname 용도가 아니다. | relevant / required | `retain_current` / REVISE | 앞의 편의 이점과 붙여 선택 판단을 돕는다. |

**배치·통합:** 동일 README의 첫 설정/터널 선택 근처에 세 단위를 함께 둔다. 현재 문맥에 이미 조건이 있어 이동을 강제하지 않는다.

**수작업 확인:** 계정·도메인·Tunnel Token 불필요는 임시 Quick Tunnel 경로의 조건이다. URL 재시작 변경과 비운영 안정 hostname 제한을 함께 확인했다. 실제 연결은 실행하지 않았다.

**미확인·사람 검토:** wizard의 실제 선택 순서·화면과 전체 가이드의 일관성.

**실제 수정 필요성·우선순위:** P3: 가독성 개선 선택; 조건 유지 필수. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-005

**릴리스 변경사항과 검증 설명** — 기존 `KEEP` / 새 비교: **일치·보완**.

출처: [docs/RELEASE_NOTES_v0.3.1.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/RELEASE_NOTES_v0.3.1.md); 조회/검토 문맥: RELEASE_NOTES entire text. snapshot `S03`.

**목적 판단:** 업데이트 사용자와 유지보수자에게 v0.3.1 변화를 알리는 릴리스 문서다. 실제 읽은 전체 문서는 1,432자이며 변경·검증·known limitation으로 구성된다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-005-a | 7–7 | install.sh는 local runtime 시작만으로 끝내지 않고 public Cloudflare endpoint의 healthy를 기다리며 runtime/tunnel 종료 시 조기 실패한다. | relevant / required | `retain_current` / COMPRESS | 준비 경계와 실패 조건을 함께 보존한다. |
| RW-005-b | 8–8 | install.sh Git 실행 mode 100755를 복구해 fresh clone 뒤 ./install.sh가 동작하도록 한다. | relevant / required | `retain_current` / REVISE | mode·파일명·fresh clone 조건은 보호 대상이다. |
| RW-005-c | 9–9 | patch/overwrite 시 기존 권한 보존, move 시 source 권한 승계, rollback 시 권한 복구. | relevant / required | `retain_current` / COMPRESS | 네 작업을 단순 파일 권한 개선으로 뭉개지 않는다. |
| RW-005-d | 10–10 | scripts/e2e-release-bootstrap.sh 실행 mode 복구, permission-preservation tests 추가, 두 bootstrap script의 executable Git mode를 CI에서 검사. | relevant / required | `retain_current` / REVISE | 사용자 변경과 다른 유지보수자용 검증 정보도 현재 문서의 유효 정보다. |

**배치·통합:** a/b/c를 사용자 동작 변화, d를 뒤의 회귀 방지 설명으로 정리 가능하다. 현재 네 항목 순서도 타당하다. 문서 내 그룹/순서 조정은 MOVE가 아니다.

**수작업 확인:** 네 항목의 동작·스크립트·100755·권한 적용 범위를 각각 추적했다. 릴리스의 테스트/CI 서술은 출처 주장으로 보존하며 실제 통과를 새로 확인한 것은 아니다. 축약 시 both bootstrap scripts를 한 스크립트로 줄이면 안 된다.

**미확인·사람 검토:** 구현·CI·릴리스 자산 실행 결과. 검증 문구가 사실인지 판단할 실행 증거는 이번 범위 밖이다.

**실제 수정 필요성·우선순위:** P3: KEEP+선택적 REVISE/COMPRESS; 필수 수정 없음. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-006

**Windows CLI 등록의 안전 조건** — 기존 `KEEP` / 새 비교: **일치·보완**.

출처: [docs/TAURI_F4D3_WINDOWS_CLI_REGISTRATION.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/TAURI_F4D3_WINDOWS_CLI_REGISTRATION.md); 조회/검토 문맥: CLI_REGISTRATION L1–38, L69–86. snapshot `S04`.

**목적 판단:** 개발자가 설치/제거의 영향 범위를 검토한다. 문서 L3–10의 CI-only, 자동 migration 아님과 L80–83의 실제 Windows/기존 OAuth 미입증이 계약 해석을 제한한다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-006-a | 14–14 | 기본 실행은 read-only JSON inventory이며 변경하지 않는다. | relevant / required | `retain_current` / unchanged | 기본 실행의 관찰/변경 경계가 개발자의 안전한 영향 판단에 필요하다. |
| RW-006-b | 15–20 | 명시적 -Install은 기존 per-user bin/node.exe·dist/cli.js를 요구하고 %LOCALAPPDATA%/C2C-CLI-Shims에 두 .cmd를 생성; 없을 때만 User PATH에 추가하며 Process/Machine PATH·현재 terminal은 바꾸지 않고 새 PowerShell 필요. | relevant / required | `retain_current` / unchanged | 명시적 설치 동의, 필요 파일, User PATH 한정과 새 shell 조건이 설치 영향을 제한한다. |
| RW-006-c | 21–23 | receipt는 소유권·대상 설치·PATH 최초 추가 여부를 기록; 재설치는 owned wrapper 내용을 확인하고 중복을 만들지 않는다. | relevant / required | `retain_current` / unchanged | 소유권과 최초 PATH 추가 이력이 반복 설치와 안전한 제거 판단의 전제다. |
| RW-006-d | 24–26 | 명시적 -Remove는 수정·비소유 명령 삭제를 거절; 등록 shims/receipt만 지우고 자신이 추가한 PATH만 제거하며 무관 파일을 유지한다. | relevant / required | `retain_current` / unchanged | 변경·비소유 파일 거절과 조건부 PATH 제거가 무관 사용자 설정 손상을 방지한다. |
| RW-006-e | 27–30 | symlink/reparse·누락 CLI·command-path metacharacters·기존 명령 충돌을 거절; fixture override는 RUNNER_TEMP의 격리 Windows GitHub CI에서만 작동한다. | relevant / required | `retain_current` / unchanged | 입력 거절 조건과 CI fixture 한정은 production 안전성을 실제 CI 성공과 혼동하지 않게 한다. |
| RW-006-f | 31–32 | 출력은 booleans/action ID만; sensitive paths·arguments·process IDs·OAuth state·Owner Tokens·URLs를 직렬화하지 않는다. | relevant / required | `retain_current` / unchanged | 출력 허용 목록과 민감정보 금지는 검토자가 로그/관찰 경로의 노출 범위를 판단하게 한다. |

**배치·통합:** 현재 Design의 read-only → install → receipt → remove → safeguards → output 순서를 유지한다. 상태·검증 한계를 앞에서 계속 볼 수 있게 한다.

**수작업 확인:** opt-in·User PATH 한정·새 shell·소유권·제거 조건·CI fixture 한정·출력 금지 범위를 각기 확인했다. 길다는 이유로 축약할 핵심이 아니며 코드는 스타일 검사 제외라도 정보 검사 대상이다.

**미확인·사람 검토:** Windows upgrade/uninstall·실제 OAuth 연결·현재 CI 실행 결과.

**실제 수정 필요성·우선순위:** P3: 기본 KEEP; 줄바꿈·목록 분리만 선택. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-007

**자료 탐색 목적에 따른 색인 정보 선별·재구성** — 기존 `COMPRESS` / 새 비교: **부분 일치·정보 선별과 배치 재설계**.

출처: [experiences/README.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/README.md); 조회/검토 문맥: experiences/README L1–55; linked ledgers: matching population/metric/attribution passages. snapshot `S05`.

**목적 판단:** 독자의 주된 작업은 경험 자료를 찾고 핵심 사례와 상세 근거 중 무엇을 읽을지 선택하는 것이다. 원문 L3–14의 경험 원본 보존은 폴더와 개별 파일의 역할이며, 색인 README가 상세 작업 기록·수치·검증 한계를 반복해야 한다는 뜻이 아니다. 사용자 피드백에 따라 경험 목록·짧은 주제 소개·자료 역할과 링크·간단한 공통 활용 원칙을 선별한다. 기존 표에 성과 표현이 있다는 이유로 상세 한계를 계속 싣기보다 그 성과 표현 자체가 탐색 목적에 필요한지 먼저 판단한다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-007-a | 52–52 | Mallo의 12개 교차검증 원장과 채용용 핵심 사례 5선은 다른 자료 역할이다. | relevant / required | `retain_current` / COMPRESS | Mallo 핵심 사례와 원장의 역할·링크를 경험 목록에 두어 독자가 자료를 선택하도록 한다. 항목 수는 원래 자료의 식별 정보이며 상세 성과 수치와 구별한다. |
| RW-007-b | 52–52 | 60대 초기 설문 13명과 미실행 최종 사용자 평가는 별개; Real E2E p95 3.338초는 1.5초 요구 미달. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 초기/최종 평가 구분·지연·요구 미달은 상세 검증 정보다. 색인의 주제·자료 역할 소개에는 반복하지 않을 후보이며, 성과 주장 자체를 선별한 뒤 현지 조건 필요성을 재판단한다. |
| RW-007-c | 53–53 | 말해봄 12개 작업군 원장과 핵심 사례 5개 구분. | relevant / required | `retain_current` / COMPRESS | 말해봄 핵심 사례와 검증 원장의 역할·링크를 경험 목록에 연결한다. 프로젝트별 안내를 공통 작성 원칙으로 취급하지 않는다. |
| RW-007-d | 53–53 | 말해봄 검증 완료는 운영 전체 E2E·마감 제출·독립 사람 품질 평가를 뜻하지 않는다. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 운영/E2E/마감/사람 평가 경계는 검증 원장에 보존한다. 색인에서 검증 완료라는 성과 주장을 빼고 자료 역할만 안내하는 경우 현지 반복 필요성이 줄어든다. |
| RW-007-e1 | 55–55 | HCI 개인 DB/쿼리 Git 커밋·팀 설문 A/B 검증 원장의 역할과 링크. | relevant / required | `retain_current` / COMPRESS | 개인 구현·팀 평가 근거를 어디에서 확인할지 알려주는 원장 링크와 역할은 자료 선택에 필요하다. |
| RW-007-e2 | 55–55 | HCI의 18명 팀 사용자 평가와 개인 구현 기여를 구분한다. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 18명이라는 표본 수와 해당 팀 평가의 귀속은 상세 근거에 보존한다. 색인에는 공통 귀속 구분 원칙과 원장 역할을 남기고 특정 평가 성과를 주장하지 않는 안을 검토한다. |
| RW-007-f | 55–55 | 목표가 적중률·Gemini 전체 재현·현재 운영은 검증 완료 아님; CSV 12/6과 발표 13/5의 일부 집계 차이가 있다. | irrelevant / optional | `preserve_elsewhere_candidate` / unchanged | 세부 미검증 기능·운영 상태와 집계 차이는 개별 경험의 정확성 검토에 필요하다. 대응 원장의 수치·조건·출처 보존 확인 후 색인 중복을 정리할 후보다. |

**배치·통합:** a/c/e1의 프로젝트별 링크와 자료 역할은 작성 원칙에서 빼고 같은 문서 경험 목록의 해당 프로젝트 항목에 배치한다. 작성 원칙에는 불확실한 수치를 확정하지 않기, 개인·팀 귀속 구분, 근거 문서 확인 등 공통 기준만 짧게 남긴다. b/d/e2/f의 상세 수치·검증 미완료·집계 차이는 대응하는 경험·검증 문서에 보존할 후보이며 기존 내용의 요소별 대응을 확인한 뒤 중복 정리한다. 색인 소개를 주제·자료 역할 중심으로 고쳐 성공·평가 완료를 암시하지 않게 한다. 그래도 성과 주장을 남기는 경우에만 그 해석에 필수인 최소 조건을 현지 노출한다. 완성한 source/destination 수정본이 없어 실제 이동·삭제는 blocked다.

**수작업 확인:** 원문 작성 원칙 L48–51의 공통 기준과 L52–55의 프로젝트별 자료 안내·상세 한계를 분리했다. a/c는 핵심 사례와 원장 선택 안내로 유지한다. 기존 HCI e는 원장 링크/역할 e1과 18명 팀 평가/개인 구현 귀속 e2로 분할해 서로 다른 판단을 가능하게 했다. Mallo 13명 초기 탐색 대 최종 평가 미실행·p95 3.338초 대 요구 1.5초, 말해봄의 운영/E2E/마감/사람 평가 경계, HCI 18명 팀 평가와 CSV 12/6 대 발표 13/5는 기존 근거 장부의 보존 대상이다. 이번 수정에서는 이 정보의 사실성을 새로 검증하거나 외부 색인·원장을 수정하지 않았다.

**미확인·사람 검토:** 최종 색인에서 남길 주제·성과 표현과 그에 따른 현지 조건 필요성, 목적지의 요소별 중복·조건·귀속 보존과 통합 후 전체 문맥. 기존 원장의 관련 구간을 확인한 사실만으로 상세 정보 삭제나 이동 완료를 확정하지 않는다.

**실제 수정 필요성·우선순위:** P2: 자료 역할·링크 KEEP, 경험 목록으로 재배치·축약; 상세 기록은 보존 확인 후 중복 정리. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

자료 안내의 표현 예시는 “Mallo의 AI 시스템·백엔드 기여를 살펴보는 핵심 사례와, 개인·팀 귀속 및 수치·평가 범위를 확인하는 검증 원장을 제공합니다.” 정도다. 실제 수정 시 기존 두 링크를 연결한다. 이 문장은 성능 달성이나 평가 완료를 주장하지 않으며, 상세 조건을 삭제한 전체 수정본·이동 완료 결과는 아니다.

### RW-008

**목적 오판과 다중 실험을 담은 구조 재설계** — 기존 `FLAG` / 새 비교: **일치·구체화**.

출처: [resume.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/resume.md); 조회/검토 문맥: resume Mallo section and final master/selection paragraph; mallo L34–48, L113–138, L276–278. snapshot `S06`.

**목적 판단:** 기존 annotation에 기록된 과거 사용자 정정은 provenance가 제한된 사용자 맥락 기록이지 이번에 새로 받은 직접 지시 원문이 아니다. 현재 요청은 이를 검토하라는 명시적 지시다. 원문 말미는 마스터 이력서이면서 상단·주력 프로젝트는 채용용이라고 밝힌다. 문서 역할과 원하는 제출 목적을 구분하고, 단순히 더 짧은 이력서·관리 안내 MOVE로 목적을 바꾸지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-008-a | 67–67 | PRD/TRD·공통 command contract·Order Engine·Senior-first UI 구성 및 AI Hub 친절 발화로 MeloTTS fine-tuning. | relevant / required | `retain_current` / REVISE | 수행 내용과 선택 평가를 분리해 개인 기여를 드러낸다. |
| RW-008-b | 67–67 | 동일 20문장 GPU benchmark: Melo Base 0.1985s / Friendly 0.2041s, Qwen Base 6.9075s / Friendly 28.1953s 비교 후 MeloTTS Friendly 선택. | relevant / required | `retain_current` / REVISE | 네 값·동일 입력·GPU 조건은 묶어서 보존한다. |
| RW-008-c | 67–67 | 후반 Whisper Medium QLoRA 후보 sweep과 Qwen3-1.7B QLoRA 3-epoch 학습을 직접 수행. | relevant / required | `retain_current` / REVISE | 초기 TTS 비교와 다른 기여이며 상세 문서는 일부 공개 Git 검증 미완료를 명시한다. |
| RW-008-d | 67–67 | Gateway/STT/NLU/TTS를 8000/8001/8002/8003 sidecar 구조로 통합. | relevant / useful | `retain_current` / REVISE | 포트와 모듈 대응을 보존한다. |
| RW-008-e | 68–68 | 초기 fine-tuned MeloTTS는 baseline보다 평균 생성 +5.6ms(+2.8%), 약 0.2초이며 친절체 억양을 얻었다는 서술. | relevant / required | `retain_current` / REVISE | 지연 개선이라 바꾸지 않고 친절체 품질은 출처 주장으로 한정한다. |
| RW-008-f | 68–68 | 이후 production checkpoint G_2800 benchmark mean 0.38s / p95 0.53s / RTF 0.0894. | relevant / required | `retain_current` / REVISE | 20문장 비교와 시점·checkpoint가 다른 별도 측정이다. |
| RW-008-g | 68–68 | Vercel frontend + Cloudflare Tunnel + local FastAPI runtime 배포라는 source 주장. | uncertain / useful | `undecided` / unchanged | 상세 문서의 Gateway 기술명과 차이는 추가 확인 필요. 다른 구성·시점일 수 있다. |
| RW-008-h | 68–68 | real STT+NLU와 MockTTS의 50-turn isolated E2E p95 312.2ms; 그 조건에서 STT가 주 bottleneck. | relevant / required | `retain_current` / REVISE | 실 TTS·브라우저 첫 재생 포함 전체 E2E로 일반화하지 않는다. |
| RW-008-i | 68–68 | 2026년 8월 기능 동결·repository cleanup 후 프로젝트 종료. | relevant / useful | `retain_current` / COMPRESS | 수집된 프로젝트 종료 기록이며 현재 서비스 운영 사실은 아니다. |

**배치·통합:** 동일 resume 범위 안에서 수행/선정 근거/TTS 비교/후속 checkpoint/통합 평가를 재취합한다. 새 heading은 예시일 뿐 확정 템플릿이 아니다. Resolver가 목적·독자를 확인 → Analysis 단위/관계 재분리 → Organization 그룹/순서 → Expression 문장 수정 순이다. REVISE 하나에 구조 결정을 몰지 않는다.

**수작업 확인:** 20문장 GPU 네 값, +5.6ms(+2.8%), 후속 G_2800 별도 지표, 50-turn isolated real STT+NLU/MockTTS p95 312.2ms를 분리했다. mallo.md L37/136/276–278은 최종 Real Warm 3.338초와 측정 경계를 추가로 제시한다. resume의 local FastAPI runtime과 상세 문서의 ThreadingHTTPServer Gateway 서술은 시점·구성 차이인지 미확정이며 모순으로 단정하지 않는다.

**미확인·사람 검토:** 희망 직무·최종 분량·승인할 설명 구조, 친절체 억양의 독립 사용자 근거, Gateway 명칭 차이와 실험별 정확한 실행 조건. 발췌만으로 템플릿 전체가 결함이라고 확정하지 않는다.

**실제 수정 필요성·우선순위:** P1: 목적/측정 경계 확인 후 구조 재설계; 자동 축약 차단. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-009

**관리 안내의 AGENTS.md 이동** — 기존 `MOVE` / 새 비교: **부분 일치·조건 강화**.

출처: [README.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/README.md); 조회/검토 문맥: README L1–54; same-commit AGENTS lookup 404. snapshot `S07`.

**목적 판단:** fixture는 채용자용 README/에이전트용 AGENTS 분리를 목표로 기록한다. 실제 README L3·54는 지원 기록과 경험 원본을 축적하는 작업 저장소 소개다. 원하는 개편 목적은 유지하되 원래 목적 자체를 잘못된 것으로 확정하지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-009-a | 34–34 | resume.md는 직무별 선별 전 마스터 이력서. | relevant / useful | `retain_current` / COMPRESS | 원본 역할은 방문자도 알아야 제출본과 혼동하지 않는다. |
| RW-009-b | 35–35 | 프로젝트 사실·문제·선택 이유·수치·성과는 experiences/에 보존. | relevant / required | `preserve_elsewhere_candidate` / COMPRESS | 에이전트 작업 시 정보 유실 방지 규칙이다. |
| RW-009-c | 36–36 | experiences/career-timeline.md는 빠진 학습·제작 경험까지 연대기 보존. | relevant / useful | `retain_current` / COMPRESS | 자료 탐색 경로로도 유효하다. |
| RW-009-d | 37–37 | 오래된 경험 복원은 지정 guide의 commit graph → 원장 → 누락 역검증 → canonical → 선별 순서. | relevant / required | `preserve_elsewhere_candidate` / unchanged | 절차와 guide 경로를 함께 보존한다. |
| RW-009-e | 38–38 | 이력서·경험 가이드와 자소서 가이드를 구분해 따른다. | relevant / useful | `preserve_elsewhere_candidate` / COMPRESS | README에는 링크 요약을 남길 수 있으나 작업 규칙 이전은 별도다. |
| RW-009-f | 39–39 | 실제 제출 자소서는 회사별 cover-letters/ 보관. | relevant / useful | `retain_current` / COMPRESS | 자료의 역할과 탐색에 관련된다. |
| RW-009-g | 40–40 | 공개 저장소에 전화번호·개인 이메일·주소 등 불필요 개인정보를 커밋하지 않는다. | relevant / required | `preserve_elsewhere_candidate` / unchanged | 목적지 확인 전 현지 규칙을 삭제하지 않는다. |

**배치·통합:** b/d/f/g의 작업 규칙은 AGENTS 역할 후보; a/c/e의 문서 역할·경로 탐색은 README에도 짧게 유용하다. 고정 커밋 AGENTS.md 조회는 404였다. 목적지 기존 내용이 확인되지 않으므로 이동은 blocked이며 새 파일을 존재한다고 가정하지 않는다.

**수작업 확인:** 7개 bullet의 마스터 성격·경험 보존·연대기·복원 순서·가이드·회사별 보관·개인정보 제약을 분리했다. 개인정보와 원본 보존 지침은 단순 불필요한 설명이 아니다.

**미확인·사람 검토:** AGENTS 부재 원인·향후 생성 여부와 작성자 승인, 루트 README에서 남길 탐색 범위.

**실제 수정 필요성·우선순위:** P2: 목표 계약·목적지 확정 후 일부 MOVE; 원문 삭제 금지. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-010

**가이드의 작성 원칙과 문서 역할** — 기존 `MOVE` / 새 비교: **부분 불일치**.

출처: [guides/resume-experience-writing.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/guides/resume-experience-writing.md); 조회/검토 문맥: guide L1–31, L57–65; same-commit AGENTS lookup 404. snapshot `S08`.

**목적 판단:** 가이드 직접 독자는 경험을 작성하는 사람/에이전트이며 채용자는 결과물 독자다. L3–5는 근거 복원·이력서 압축을 현재 가이드의 책임으로 명시한다. 역할 구분만으로 작성 기준을 전부 AGENTS로 보낼 근거는 없다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-010-a | 11–11 | 채용자가 짧은 시간에 강한 근거를 확인할 수 있도록 작성. | relevant / required | `retain_current` / unchanged | 작성 결과의 기준이므로 현재 가이드에 맞는다. |
| RW-010-b | 13–13 | 추상적 장점보다 실제 수치·판단 우선. | relevant / required | `retain_current` / unchanged | 정보 가치와 근거를 평가하는 작성 방법이다. |
| RW-010-c | 14–14 | 주력 프로젝트 2~3개 상세 설명. | relevant / useful | `retain_current` / REVISE | 제출 목적별 기본 제안임을 확인하고 구조를 획일화하지 않는다. |
| RW-010-d | 15–15 | 보조 프로젝트 2~3줄 압축. | relevant / useful | `retain_current` / REVISE | 필수 조건 유실이나 master 정보 삭제를 허용하지 않는다. |
| RW-010-e | 16–16 | 기간·팀 규모·본인 담당 범위를 표시. | relevant / required | `retain_current` / unchanged | 기여 해석에 필요한 조건이다. |
| RW-010-f | 17–17 | 세부 provenance·debugging 기록은 experiences/로 넘긴다. | relevant / useful | `preserve_elsewhere_candidate` / REVISE | 경로 책임은 공통 지침 후보이나 현 가이드에도 근거 연결 원칙은 남겨야 한다. |

**배치·통합:** a/b/e는 현재 가이드의 작성 기준에 유지한다. c/d는 채용용 산출물에 적용할 기본 분량 제안으로 재표현하고 마스터 전체의 불변 규칙으로 강요하지 않는다. f의 경로/책임만 AGENTS 후보이며 동일 커밋 목적지는 404로 미확인이다.

**수작업 확인:** 발췌에는 resume.md 파일명이 없고 위 heading L9가 그 대상이다. 2~3개/2~3줄이라는 수치는 원문 가이드의 제안으로 추적하되 사용자 최종 분량 지시로 승격하지 않는다. RW-008과 목적 적용 범위를 대조했다.

**미확인·사람 검토:** 분량 규칙을 사용자가 승인했는지, 대상 산출물이 master인지 제출본인지, AGENTS 기존 내용.

**실제 수정 필요성·우선순위:** P2: 분량 규칙 적용 범위 확인·REVISE; 전면 MOVE 불필요. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-011

**수수료 조건이 다른 백테스트** — 기존 `KEEP` / 새 비교: **일치·보완**.

출처: [experiences/crypto-lob-prediction.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/crypto-lob-prediction.md); 조회/검토 문맥: summary L3–5; detailed backtest/limitations L74, L174, L286, L317, L326, L349. snapshot `S09`.

**목적 판단:** 실험 평가자·채용자에게 수행 내용과 한계를 요약한다. 한 줄 요약은 실제 한 문장 분량 제한이 아니라 현재 heading이다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-011-a | 5–5 | Binance BTCUSDT tick-by-tick 체결 수집·전처리, 4-layer Mamba로 5초 뒤 방향 예측. | relevant / required | `retain_current` / REVISE | 데이터와 모델·horizon을 보존한다. |
| RW-011-b | 5–5 | 약 19분 validation 구간의 가상 중복거래 백테스트에서 무수수료 +23.26%, 수수료 반영 시 손실. | relevant / required | `retain_current` / REVISE | 기간·validation·가상·중복거래·비용 조건이 수익 수치에 필수다. |
| RW-011-c | 5–5 | 독립 test 20만 시퀀스 3-class accuracy 45.79%, 최빈 클래스 55.64%보다 낮음. | relevant / required | `retain_current` / REVISE | backtest와 별도 모집단/지표이며 기준선 비교를 남긴다. |
| RW-011-d | 5–5 | 수익성 입증이 아닌 시계열 예측·실행비용 평가와 설계 한계 확인 경험. | relevant / required | `retain_current` / COMPRESS | 앞의 양수 수익을 일반 성공으로 오독하지 않게 한다. |

**배치·통합:** 상단 요약을 유지하되 두세 문장/문단으로 나누는 표현 수정은 가능하다. 문서 간 이동 필요는 관측하지 않았다.

**수작업 확인:** 무수수료 수익과 수수료 반영 손실은 조건이 다른 결과이며 모순으로 보지 않는다. 독립 test 정확도와 최빈 기준선도 별도 평가다. 상세문서의 source 주장과 실험의 재실행 증거를 구분한다.

**미확인·사람 검토:** 원시 데이터·test 분할·백테스트 구현·실제 수익성. 원문 참조는 사실성 보증이 아니다.

**실제 수정 필요성·우선순위:** P3: 선택적 문장 분리; 필수 수정 없음. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-012

**기여·측정 조건·상세 한계의 분리** — 기존 `MOVE` / 새 비교: **부분 일치·수치 문맥 불일치**.

출처: [resume.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/resume.md); 조회/검토 문맥: resume L71–86; malhaebom L105, L151, L159–171, L243; rework ledger L138–153, L268–285, L392. snapshot `S06`.

**목적 판단:** 기술 면접관·채용자에게 개인 기여를 전달한다. 원문은 master 역할도 가지므로 상세 한계를 제거하는 것 자체가 목표가 아니다. 성과의 의미를 바꾸는 조건은 현재 이력서에도 필수다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-012-a | 79–79 | OpenRouter 40종 사전검증; 22종×30건=660건 합성 평가; 별도 최종 후보 4종 비교로 출력 계약·지연·비용·로컬 호환성 확인. | relevant / required | `retain_current` / COMPRESS | 순차 단계와 모집단을 합산하거나 같은 평가로 바꾸지 않는다. |
| RW-012-b | 79–79 | Gemini Flash-Lite는 로컬 코칭 기본 후보; 합성 결과는 실제 사용자 품질·운영 안정성 검증이 아님. | relevant / required | `retain_current` / REVISE | candidate와 synthetic 조건은 현재 주장 가까이 필수 노출한다. |
| RW-012-c | 80–80 | FastMCP 연동·인증·DB 저장 통합 테스트 및 기존 DB 행을 새 저장 성공으로 오판하는 결함 발견·수정 요청은 개인 기여. | relevant / required | `retain_current` / REVISE | 발견한 결함과 수행 범위를 보존한다. |
| RW-012-d | 80–80 | 저장 verifier의 실제 코드 수정은 팀원 담당. | relevant / required | `retain_current` / COMPRESS | 개인의 수정 요청을 patch 구현 성과로 바꾸지 않는다. |
| RW-012-e | 81–81 | Whisper Medium QLoRA 학습·정제·양 도메인 평가; C2 최종 1,233건 WER 9.77%. | relevant / required | `retain_current` / REVISE | 수치와 평가 모집단·모델 후보를 함께 보호한다. |
| RW-012-f | 81–81 | 원문은 기존 119건 retention WER 15.33%→16.81% 악화라고 서술하며 전반 개선·운영 교체 성공은 주장하지 않음. 연결 원장은 AI Hub 119 retention 4,802개로 적어 표본 수 표현이 상충함. | relevant / required | `retain_current` / REVISE | e를 남기면 회귀/운영 한정은 현지 필수. 119를 표본 수로 확정하지 말고 원문 표현과 원장의 식별자/4,802개를 구분해 FLAG. |
| RW-012-g | 82–82 | PR 본문 수정/최신 HEAD 정책 재실행 race condition 수정 및 Backend/Frontend 테스트·빌드 CI 구성. | relevant / required | `retain_current` / COMPRESS | 개인 기여와 CI의 적용 범위를 보존한다. |
| RW-012-h | 82–82 | 초기 Actions 4개 체크 통과는 확인됐지만 배포 전체 E2E·CI 비용 절감은 입증 아님. | relevant / required | `retain_current` / REVISE | 일부 체크 통과를 전체 배포 검증으로 확대하지 않는다. |
| RW-012-i | 84–84 | 코어 Agent·DB verifier patch는 팀원 작업; 개인은 평가·실험·리뷰·테스트·CI; 운영 전체 E2E·독립 사용자 품질 평가 완료 아님. | relevant / required | `retain_current` / COMPRESS | 각 항목에서 동일 귀속/조건이 충분히 보이면 문서 내 중복 통합 가능; 즉시 삭제 아님. |

**배치·통합:** a/b, c/d, e/f, g/h를 각각 작업과 조건 묶음으로 현지 노출한다. 상세 경험·검증 원장은 실제 확인했지만 통합 결과 문서는 만들지 않았다. 수치/귀속/조건이 대상 문서 어느 요소에 보존되는지 gate 검토 전까지 source removal은 blocked다. 마지막 종합 주의는 필요한 귀속·미검증 조건을 각 항목에 옮긴 후에만 문서 내 중복 통합 후보다.

**수작업 확인:** 40종 → 22×30=660 합성 → 별도 4종 후보 비교를 구분; 개인 결함 발견/수정 요청과 팀원 verifier patch 분리; C2 1,233건 WER 9.77%와 retention 15.33→16.81% 회귀를 함께 보존하되, 원문 119건은 원장 L268/278/285의 AI Hub 119 데이터셋·4,802개 retention 표본과 다르다. 식별자를 표본 수로 혼동했을 가능성을 P1 FLAG로 남겼고 원시 manifest 확인 전 확정 정정하지 않는다. 동일 최종 test의 B0 값이 없어 직접 개선율도 계산할 수 없다; 초기 4개 Actions 체크와 배포 전체 E2E/비용·사람 품질 미확인을 구분했다. 두 근거 문서의 관련 구간과 대조했으나 실제 성능/운영은 미검증이다.

**미확인·사람 검토:** 119건 표기와 AI Hub 119 retention 4,802개 기록의 불일치 해소·정확한 평가 manifest, 전체 평가 원시 기록 재현성·최종 운영 교체·사람 품질 검토. 상세 한계 중 무엇을 중복 통합할지는 완성한 수정본과 독자 판단이 필요하다.

**실제 수정 필요성·우선순위:** P1: retention 표본 수 확인·조건·귀속 노출; 확인 전 MOVE 금지. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-013

**한 문단 안의 사용자 안내와 내부 구현** — 기존 `MOVE` / 새 비교: **일치·세분화**.

출처: [README.md](https://github.com/nanocode00/QuotaTray/blob/e62eb5c37fbf7265a7937f3939bf99681e38cb03/README.md); 조회/검토 문맥: README L44–64, L101–124; OAuth runtime document entire text. snapshot `S10`.

**목적 판단:** 설치·사용자는 최초 로그인 전제와 agy 종료 후 조회, 환경변수 요구 여부, 기존 자격증명 영향을 알고 싶다. 개발자 진단의 직접 독자는 다르다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-013-a | 54–54 | Antigravity/agy 정상 로그인으로 로컬 OAuth 세션이 한 번 생성되면 agy가 꺼져 있어도 직접 access token 갱신 후 quota 조회 가능. | relevant / required | `retain_current` / REVISE | 세션 생성 전제와 종료 후 갱신을 한 의미 단위로 보호한다. |
| RW-013-b | 56–56 | 일반 사용자는 Antigravity OAuth 환경변수를 따로 설정할 필요 없음. | relevant / required | `retain_current` / unchanged | first-use 설정 판단에 직접 관련된다. |
| RW-013-c | 56–56 | 공개 installed-app OAuth client metadata를 자동 확인. | uncertain / useful | `preserve_elsewhere_candidate` / unchanged | 내부 구조 설명은 설계 독자에 유용; 설치자에게는 선택적이다; 현 README 범위에서는 uncertain/useful이며 설계 범위에서는 relevant/useful이다. |
| RW-013-d | 56–56 | metadata를 SHA-256 fingerprint로 검증. | uncertain / useful | `preserve_elsewhere_candidate` / unchanged | 자동 확인과 다른 검증 주장; 임의의 일반 보안 보증으로 바꾸지 않는다. |
| RW-013-e | 56–56 | 검증한 metadata를 QuotaTray 전용 credential cache에 저장. | uncertain / useful | `preserve_elsewhere_candidate` / unchanged | 저장 주체·대상을 분리해 사용자 자격증명과 혼동하지 않는다. |
| RW-013-f | 56–56 | Antigravity 소유 gemini:antigravity credential을 덮어쓰지 않음. | relevant / required | `retain_current` / REVISE | 사용자 영향은 현지에 유지하고 ownership 상세와 연계한다. |
| RW-013-g | 58–62 | 문제 진단 시 dotnet run --project .\QuotaTray.TestCli -- refresh-test로 직접 refresh 경로 검증. | uncertain / useful | `preserve_elsewhere_candidate` / REVISE | 명령 literal과 진단 목적 보존; 일반 설치 사용자 필수 단계로 만들지 않는다. |

**배치·통합:** a/b/f는 README의 Antigravity 로그인 안내에 유지. c/d/e와 g는 실제 docs/antigravity-oauth-runtime.md의 Runtime flow/Validation에 이미 대응 설명이 있다. 해당 고정 문서 전체를 읽어 사용자 전제·인증 소유권·기존 진단 명령의 맥락을 확인했다. 별도 문제 해결 문서가 반드시 필요한 것은 아니다. 목적지는 verified_context이지만 수정·통합본 검토 전 source removal은 blocked다. README 전체가 소스 빌드 사용자도 다루므로 g의 현지 유지 역시 검토 가능한 선택이지 무조건 부적합 판정은 아니다.

**수작업 확인:** 같은 L56 문단에서 환경변수·메타데이터·SHA-256·전용 cache·gemini:antigravity 보호를 별도 단위로 나눴다. a의 정상 로그인/로컬 OAuth 세션 조건을 떼면 agy 미설치·미인증 상태에서도 된다는 오해를 만든다. command는 실행하지 않았다. 실제 목적지의 Validation은 Windows/agy 종료 조건의 성공을 서술하지만 이는 대상 문서의 source assertion이며 이번 재실행 결과가 아니다. README L101–124는 .NET 8 SDK/소스 빌드를 다룬다. 개발 환경 전제는 명령과 이 문맥에서 도출한 해석이다.

**미확인·사람 검토:** 통합 후 README/설계 문서 전체 노출, 목적지 성공 기록의 원시 로그, 현재 refresh/자격증명 동작. 별도 troubleshooting 문서는 확인하지 않았다.

**실제 수정 필요성·우선순위:** P2: 확인한 설계 문서와 중복 통합 후보; 수정본 검토 전 source 보존. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

목적지의 기존 단위도 같은 inventory에 추가해 별도로 보았다. 원문 unit을 새 내용처럼 목적지에 복제하는 계획이 아니다.

| 목적지 unit | 행 | 기존 정보·보호할 조건 | 원문 중복 후보 |
| --- | --- | --- | --- |
| D13-a | 12 | metadata 자동 조회; complete env override는 development에서 허용하고 기본은 자기 cache 확인. | RW-013-c |
| D13-b | 13 | cache가 비면 pinned immutable reference 조회; canonical client ID와 client-secret SHA-256 fingerprint를 함께 확인. | RW-013-d |
| D13-c | 14 | 검증 metadata는 QuotaTray:antigravity-oauth-client에 cache하며 후속 fetch를 줄임. | RW-013-e |
| D13-d | 17 | gemini:antigravity를 덮어쓰지 않으며 canonical bootstrap 불가 시 local agy discovery fallback. | RW-013-f |
| D13-e | 33 | Windows/agy 종료 조건에서 refresh-test 및 normal CLI 성공을 기록한 원문 주장. | RW-013-g |

`auth_design` 범위에서는 c/d/e/g가 relevant/useful인 별도 Assessment를 갖는다. 같은 `unit_ref`의 README 현재 범위와 설계 범위 판단을 구별한다. c–e를 모아 옮기면 목적지에만 있는 개발 override, client ID 확인, 전용 cache target과 fallback을 지우지 않아야 한다. 원문 c/d/e/g → D13-a/b/c/e의 요소별 대응은 통합 후보이며 완전한 의미 동치나 이동 완료가 아니다.

### RW-014

**지원 목록·절대 표현·인증 상세** — 기존 `FLAG` / 새 비교: **부분 일치·근거 제한**.

출처: [README.md](https://github.com/nanocode00/QuotaTray/blob/e62eb5c37fbf7265a7937f3939bf99681e38cb03/README.md); 조회/검토 문맥: README L22–50, L81–97. snapshot `S10`.

**목적 판단:** 잠재 사용자가 지원 서비스·표시 범위를 파악한다. 완벽 지원의 충분한 근거는 원문 목록 자체에 없다. 기존 annotation의 이모지 제거 사용자 지정 문체는 원 지시가 제공되지 않았으므로 현재 계약의 확정 요구로 채택하지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-014-a | 30–30 | 8대 주요 AI 프로바이더 완벽 지원이라는 제목. | uncertain / useful | `undecided` / REVISE | 8개 나열은 확인되지만 주요·완벽이라는 평가/전칭은 별도 근거가 없다. |
| RW-014-b | 31–31 | OpenAI Codex: API 실제 반환 5h/7d Rate Limit 윈도우·장기 윈도우 대표값; codex login / ~/.codex/auth.json. | relevant / required | `retain_current` / REVISE | 윈도우·대표값 의미를 풀고 인증 상세만 분리 후보다. |
| RW-014-c | 32–32 | Antigravity: Gemini 풀 및 Claude/GPT 풀 quota 실시간 모니터링; agy auth login / Cloud Code Assist. | relevant / required | `retain_current` / REVISE | 표시 범위는 보존하고 실시간 동작은 별도 FLAG. |
| RW-014-d | 33–33 | Claude Code: Anthropic 5h/7d 사용률·reset countdown; claude login / API Key. | relevant / required | `retain_current` / REVISE | 시간 창과 인증 대안을 보존한다. |
| RW-014-e | 34–34 | Copilot: Free Code Completions / 유료 Premium Requests 단독 집중이라는 플랜별 최적화. | relevant / required | `retain_current` / REVISE | 최적화 평가 대신 플랜별 표시 항목을 설명한다. |
| RW-014-f | 35–35 | OpenRouter: 달러 credit 실시간 잔액, 무료 50/day 또는 1,000/day 한도, API Key 제한. | relevant / required | `retain_current` / REVISE | 두 수치의 조건을 임의 배정하지 않고 source claim으로 남긴다; 실시간은 미확인. |
| RW-014-g | 36–36 | Kimi(Moonshot AI): 사용 가능한 cache/voucher 잔액·quota. | relevant / useful | `retain_current` / REVISE | 브랜드와 표시 대상을 보존한다. |
| RW-014-h | 37–37 | Z.AI(Zhipu GLM): API 계정 상태·token quota. | relevant / useful | `retain_current` / REVISE | 잔액/사용률과 다른 표시 내용이다. |
| RW-014-i | 38–38 | Synthetic.new: 사용량·구독 상태. | relevant / useful | `retain_current` / unchanged | 목록의 마지막 서비스도 누락하지 않는다. |

**배치·통합:** 서비스별 표시 정보는 현지 기능 목록에 유지. 인증 파일/명령은 설정 역할 후보지만 현재 문서에 연결된 설정 맥락도 유용하므로 전면 분리를 강제하지 않는다. 목적지 미확인 이동은 blocked.

**수작업 확인:** 8개 서비스와 각각의 표시 항목·창·플랜·조건을 확인했다. 실시간을 주기적 갱신으로 바꿀 동작 증거는 없다. 원문 L47은 자동 갱신 주기 1분~60분 설정도 명시한다. 실시간 표현과 이 설정의 의미를 함께 검토하되 실제 동작을 이 설정만으로 단정하지 않는다. 현 정책을 확인한 것이 아니라 고정 source의 제품 주장을 검토한 것이며 50/day·1,000/day를 현재 provider 정책으로 보증하지 않는다.

**미확인·사람 검토:** 실제 지원 범위·갱신 주기·plan 동작·provider 정책. 이모지 제거의 원 사용자 지시.

**실제 수정 필요성·우선순위:** P1: 완벽 지원/실시간 근거 확인 또는 범위 한정; 이모지 정리는 P3. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-015

**서로 다른 Releases 링크** — 기존 `REVISE` / 새 비교: **일치·재확인**.

출처: [README.md](https://github.com/nanocode00/QuotaTray/blob/e62eb5c37fbf7265a7937f3939bf99681e38cb03/README.md); 조회/검토 문맥: README L8, L68–77; current HTTP observations. snapshot `S10`.

**목적 판단:** 설치 사용자가 공식 release 다운로드로 이동하는 것이 목적이다. L8 badge와 L70 본문의 대상 repository가 다르다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-015-a | 8–8 | Release-v0.1.0 badge는 nanocode00/QuotaTray/releases로 연결. | relevant / required | `retain_current` / unchanged | 정상 경로 후보를 source 안에서 대조할 수 있다. |
| RW-015-b | 70–70 | OS별 단일 실행 파일 다운로드 안내의 본문 링크는 HonorBear/QuotaTray/releases. | relevant / required | `retain_current` / REVISE | 설치 지시는 보존하고 확인한 URL만 수정한다. |

**배치·통합:** 다운로드 안내는 README 설치 구간에 유지; 본문 URL을 badge와 같은 nanocode00 대상 후보로 수정. 다른 문서 이동은 필요 없다.

**수작업 확인:** 고정 원문의 두 URL을 비교했다. 이번 별도 HTTP 조회 결과는 evidence JSON의 link_observations에 저장한다. 공개 응답/redirect 확인은 현재 접근 상태만 의미하며 수집 시점의 고장 원인이나 실행 파일 정상 동작은 입증하지 않는다.

**미확인·사람 검토:** OS별 실제 release asset의 제공/설치·실행·보안. 404 원인과 수집 시점 응답.

**실제 수정 필요성·우선순위:** P1: 본문 다운로드 URL REVISE 제안; 외부 source는 수정하지 않음. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-016

**이관 준비 README의 상태와 경계** — 기존 `MOVE` / 새 비교: **부분 불일치**.

출처: [README.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/README.md); 조회/검토 문맥: README L1–29; MIGRATION opening/base, exclusions and scope; AGENTS opening. snapshot `S11`.

**목적 판단:** 협업자는 복사/이관 대상을 판단한다. 원문 제목부터 이관 준비 저장소이며 미적용 상태·기준·제외 범위는 이 목적에 직접 관련된다. 일반 제품 README의 짧은 소개 역할을 강제하면 목적을 오판한다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-016-a | 3–3 | 루트에서 이관 후보 구조 검토; 실제 적용 대상은 aihuman-7th/proj3-b. | relevant / required | `retain_current` / unchanged | 저장소 역할과 대상 링크는 기본 정보다. |
| RW-016-b | 3–3 | 대상 repository에 적용하거나 PR을 만들지 않은 준비 상태. | relevant / required | `retain_current` / REVISE | 완료/적용본 오인 방지에 필요하며 수집 시점으로 한정한다. |
| RW-016-c | 5–5 | 강사 제공 proj3-b f06acf2221f48e448c54c7254e8b9b4b76612170가 기준 구조. | relevant / useful | `preserve_elsewhere_candidate` / COMPRESS | MIGRATION에 동일 SHA가 있어 상세 중복 통합 후보; root의 기준 안내는 유지 가능하다. |
| RW-016-d | 3–3 | 아이디어·개별 기획안·API 실험·비밀값 제외. | relevant / required | `retain_current` / COMPRESS | 복사 범위 결정에 직접 필요한 한정이다. |
| RW-016-e | 5–5 | 이관 후보만 두고 기존 제품 코드·평가셋·workflow는 복제하지 않음. | relevant / required | `retain_current` / COMPRESS | 현재 corpus 경계이며 무기한 작업 금지로 강화하지 않는다. |

**배치·통합:** a/b/d는 루트에서 즉시 보이게 유지. c의 기준 SHA 상세는 실제 MIGRATION.md L3–7과 연결·중복 통합 가능하나 현지 기준 식별은 남길 수 있다. e는 현재 구성 설명과 향후 금지 명령을 구별하고 원문보다 강한 규칙으로 바꾸지 않는다. AGENTS.md도 준비본 경계를 이미 설명한다.

**수작업 확인:** 미적용·PR 미생성과 제외 범위는 시점이 고정된 source의 상태다. MIGRATION의 기준 SHA·제외 항목과 AGENTS 상단을 대조해 상세 목적지는 실제 존재함을 확인했다. 이후 전체 통합본/노출 검토는 미실시로 이동 완료가 아니다.

**미확인·사람 검토:** 현재 프로젝트 실제 적용 여부, 상세 통합 이후 루트 독자에게 필요한 기준·상태 범위.

**실제 수정 필요성·우선순위:** P2: 세부 기준 중복 통합 선택; 상태·범위 전면 MOVE 반대. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-017

**변이 검증의 작업·예시·과거 일화** — 기존 `REVISE` / 새 비교: **일치·보완**.

출처: [docs/GATES.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/docs/GATES.md); 조회/검토 문맥: GATES L1–45, especially L35–41. snapshot `S12`.

**목적 판단:** 게이트 담당자가 테스트가 결함을 검출하는지 수행·기록한다. 원문 L35는 최소 3건 기록을 요구하므로 발췌 L31–33만 보고 수량 요구를 놓치면 안 된다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-017-a | 31–31 | G4/G5 통과만으로 충분한 증거가 아니라는 변이 확인 제목. | relevant / required | `retain_current` / REVISE | 테스트 결함 검출 확인처럼 작업 중심으로 표현한다. |
| RW-017-b | 33–33 | 단언 없는 test도 green일 수 있으므로 핵심 코드를 깨뜨려 실제 실패 여부를 확인·기록. | relevant / required | `retain_current` / COMPRESS | 원리와 실행 작업을 보존한다. |
| RW-017-c | 33–33 | assert n == MAX_REWRITES와 assert n == 2 비교, 상한 99 mutation 예시. | uncertain / useful | `undecided` / REVISE | literal 사용만으로 보장되지 않으며 실제 SUT의 상한 동작을 검증해야 한다. |
| RW-017-d | 33–33 | AI 에이전트 변이 검출 보고도 직접 확인; DART에서 틀렸다는 과거 일화. | relevant / useful | `retain_current` / COMPRESS | 직접 확인 원칙은 유지; 일화 진실성/세부 보존은 추가 근거 필요. |

**배치·통합:** 현재 문서의 결과 표 앞에 작업 절차 유지. 단정적 제목/리터럴 만능 예시를 수정하고 교육적 설명은 축약 가능. DART 과거 보고 오류는 출처 확인 전 source에서 조용히 버리지 말고 review 기록/근거 보존 후보로 둔다.

**수작업 확인:** 실제 동작 결함 주입 → 예상 test 실패 → 결과 기록을 보존한다. n과 MAX_REWRITES 관계/검사 대상을 모르므로 리터럴 비교 자체가 결함 검출을 보장한다고 확정할 수 없다. 변이 검증은 실행하지 않았다.

**미확인·사람 검토:** 실제 코드/test와 DART 일화의 원시 근거·보존 목적지.

**실제 수정 필요성·우선순위:** P1: 잘못 일반화될 테스트 예시 REVISE; 기록 3건 요구 보존. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-018

**페이지 역할과 추가 호스팅 문맥** — 기존 `KEEP` / 새 비교: **부분 일치·추가 MOVE 재검토**.

출처: [README.md](https://github.com/nanocode00/mallo-intro/blob/916a3df7b6481d78c1a5fe95b53565f4fb7d91df/README.md); 조회/검토 문맥: README L1–16; assets READMEs; evaluator source path; original proj1-d README blob. snapshot `S13`.

**목적 판단:** 원래 3–8행은 소개 페이지 유지보수자에게 파일 역할을 설명한다. 같은 독자에게 미디어 추가·배포도 유용할 수 있으므로 별도 문서를 반드시 만들어야 한다는 근거는 부족하다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-018-a | 3–3 | 로컬 API·backend·kiosk runtime에 의존하지 않는 공개 정적 소개 페이지. | relevant / required | `retain_current` / unchanged | 저장소의 독립적 역할을 알려준다. |
| RW-018-b | 5–5 | index.html은 대상별 소개 페이지 선택 진입점. | relevant / required | `retain_current` / unchanged | routing 역할이다. |
| RW-018-c | 6–6 | customer.html은 고객·비개발자용 제품/이용 소개. | relevant / required | `retain_current` / unchanged | 대상 독자 구분을 보호한다. |
| RW-018-d | 7–7 | evaluator.html은 평가자·showcase용 구조·검증 지표 소개. | relevant / required | `retain_current` / unchanged | 고객용 소개와 서로 다른 목적이다. |
| RW-018-e | 8–8 | styles/intro.css는 세 페이지의 공유 style. | relevant / useful | `retain_current` / unchanged | 유지보수 의존 관계다. |
| RW-018-f | 10–12 | media는 assets/images/·assets/videos/에 권장 파일명으로 추가; evaluator 자동 표시/없으면 placeholder. | relevant / useful | `retain_current` / COMPRESS | 해당 asset README로 링크·중복 통합 가능하지만 정보 가치는 현재 독자에게도 있다. |
| RW-018-g | 14–16 | Pages/Vercel 배포 경로 artifacts/intro와 Framework Preset Other 안내. | relevant / required | `retain_current` / REVISE | 복제 전 원본 repository 기준임을 분리하고 현 저장소 경로를 실제 설정 확인 후 확정한다. |

**배치·통합:** a–e는 루트 역할 안내에 유지. f의 media 사용법은 asset README와 중복 통합을 검토하되 짧은 루트 링크 안내 유지 가능. g는 root 배치와 맞게 REVISE가 우선; 별도 배포 guide MOVE는 선택이며 목적지 미확인이다.

**수작업 확인:** captured README와 원본 proj1-d artifacts/intro README의 blob이 동일함을 재확인했다. evaluator.html과 두 asset README도 조회했다. 별도 저장소 evaluator는 실제 root에 존재하므로 원본 artifacts/intro 기준을 그대로 적용할 수 없다. media 자동 표시 문구는 source 주장으로 추적하며 브라우저 실행·Pages/Vercel 설정은 검증하지 않았다.

**미확인·사람 검토:** 실제 호스팅 설정·배포 성공·media fallback runtime; 별도 작업/배포 문서의 존재와 독자 선호.

**실제 수정 필요성·우선순위:** P1: 호스팅 repository/root 문맥 REVISE; MOVE는 P3 선택. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-019

**PR의 위치 교환 설명** — 기존 `KEEP` / 새 비교: **일치**.

출처: [PR #19](https://github.com/nanocode00/resume/pull/19); 조회/검토 문맥: fixture snapshot L1–5; live PR body/head metadata only, no diff verification. snapshot `RW-019-captured-excerpt`.

**목적 판단:** 검토자가 변경 범위를 파악하는 짧은 PR 설명이다. 검토 대상은 PR 문구이며 그 안에서 설명하는 resume 섹션 이동과는 구별한다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-019-a | 1–1 | resume.md의 Verilog Single-cycle CPU와 CNN Accelerator 두 섹션 위치만 교환. | relevant / required | `retain_current` / unchanged | 한 문장으로 변경을 특정한다. |
| RW-019-b | 3–3 | Single-cycle CPU → Main Projects의 기존 CNN 위치. | relevant / required | `retain_current` / unchanged | 요약과 다른 구체적 목적지 정보다. |
| RW-019-c | 4–4 | CNN Accelerator → Additional Projects의 기존 CPU 위치. | relevant / required | `retain_current` / unchanged | 교환의 다른 방향도 보존한다. |
| RW-019-d | 5–5 | 각 프로젝트 본문·정량 수치·링크는 그대로 보존한다는 작성자 주장. | relevant / required | `retain_current` / unchanged | 검토 범위 안내이지 실제 diff 검증 결과는 아니다. |

**배치·통합:** 요약 → 두 목적지 → 본문·수치·링크 보존 순서를 유지. 원문에 없는 배경/테스트 템플릿을 추가할 필요는 없다.

**수작업 확인:** 2026-11-02 저장 발췌를 평가 단위로 유지했다. 현재 PR #19 본문에서도 해당 문구가 확인되지만 mutable body 전체의 수집시점 동일성을 입증하지 않는다. head SHA는 저장 값과 같으며 실제 diff의 내용 불변 검증은 별도다.

**미확인·사람 검토:** 실제 diff의 모든 본문·수치·링크 불변 여부. PR body는 Git commit으로 고정되지 않는다.

**실제 수정 필요성·우선순위:** P3: 현 설명 수정 불필요; diff 검토는 별도 필요. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

### RW-020

**PR의 귀속·한계·파일 범위** — 기존 `KEEP` / 새 비교: **일치**.

출처: [PR #20](https://github.com/nanocode00/resume/pull/20); 조회/검토 문맥: fixture snapshot L9–14; live PR body/head metadata only, no diff verification. snapshot `RW-020-captured-excerpt`.

**목적 판단:** PR 검토자가 추가 이력의 정확성과 기여·검증 경계를 판단한다. 이력서의 독자 과제와 달라 RW-012와 같은 자동 축약 기준을 적용하지 않는다.

| Unit | 원문 행 | 보호할 주장·수치·조건·귀속 | 현재 범위 관련성 / 중요도 | 보존 / 표현 | 판단 근거 |
| --- | --- | --- | --- | --- | --- |
| RW-020-a | 9–9 | DB verifier 수정·코어 Agent 구현은 팀원 기여. | relevant / required | `retain_current` / unchanged | 개인 기여 과장 방지에 직접 필요하다. |
| RW-020-b | 10–10 | STT 기존 도메인 WER 15.33%→16.81% 악화, 운영 모델 교체 미확정. | relevant / required | `retain_current` / unchanged | 회귀/교체 상태는 성과 평가 조건이다. |
| RW-020-c | 11–11 | 서비스 전체 배포 E2E·CI 비용 절감은 미확인. | relevant / required | `retain_current` / unchanged | 검토자가 미검증 범위를 알게 한다. |
| RW-020-d | 13–14 | resume.md 1개 파일에 새 섹션만 삽입하고 기존 HummingBlocks·CPU·Mallo·Additional Projects 등 기존 문장은 바꾸지 않았다는 주장. | relevant / required | `retain_current` / unchanged | 파일 수와 변경 경계는 PR 검토의 핵심이다. |

**배치·통합:** 주요 변경 뒤 귀속/검증 경계, 이후 파일 변경 범위라는 현재 순서를 유지. 현재 본문 앞부분에는 합성 평가를 실사용 품질로 주장하지 않는 설명도 존재하지만 저장 발췌의 누락을 결함으로 보지 않는다.

**수작업 확인:** 저장 스냅샷과 현재 PR #20의 해당 구간이 일치하고 head SHA도 일치함을 확인했다. WER 회귀·팀원 구현·운영 교체/E2E/비용 미확인을 각 claim에 연결했다. 실제 성과와 diff의 모든 기존 문장 보존은 새로 증명하지 않았다.

**미확인·사람 검토:** 실제 diff의 새 섹션만 추가 여부·모든 기존 문장 불변, 원시 평가·배포 증거와 사람 검토.

**실제 수정 필요성·우선순위:** P3: 설명 수정 불필요; 사실·diff 검토는 별도. 최종 문서 판정은 하지 않으며 `REVIEW` 권고다.

## 공통 발견과 기존 모델·스키마의 표현 공백

| 공통 문제 | 사례·관측 근거 | 현재 모델로 표현할 부분 | 부족한 표현·다음 개선 |
| --- | --- | --- | --- |
| 문서 역할을 좁게 추정해 관련 정보를 과하게 이동 | RW-016의 이관 판단 경계 | WritingContract intent provenance, scope별 Assessment | historical role / desired role / 적용 시점을 구분하는 주석 지침; 목적 오판의 증거와 불확실성을 독립 기록 |
| 설명의 주제를 독자의 작업과 혼동 | RW-001/002: 설치 구성 요소를 언급해도 실제 역할은 PKG 선택 정당화였음 | InformationUnit.statement와 문맥별 기능, 계약에 따른 관련성 판단 | 포함 여부를 판단한 뒤 배치 검토; 설치 행동 안내와 의사결정 논거를 구별하고 길이·순서·언어를 KEEP 근거로 대체하지 않기 |
| 폴더의 보존 목적을 색인의 상세 반복 의무로 확대 | RW-007: 작성 원칙에 프로젝트별 기록·제약이 섞이고 기존 성과 표현을 유지한 채 조건만 보존하려 했음 | 문서별 WritingContract, 단위 분리, Organization placement와 범위별 exposure | 자료 선택에 필요한 링크·역할을 먼저 선별; 성과 표현 자체의 필요성을 판단하고 상세 근거는 보존 확인 후 분리 |
| 기존 template·분량에 다시 맞추려는 편향 | RW-008의 기여·선정·서로 다른 측정 혼재; RW-010의 2~3개/2~3줄 | Resolver → Analysis 관계 재분리 → Organization 재취합 → Expression | 구조 재설계 전후의 단위 lineage, 여러 단위가 한 그룹을 이루는 근거와 reader-task 평가 기준이 더 필요 |
| 하나의 주 라벨로 다중 판단을 표현하기 어려움 | RW-013 동일 문단의 7개 판단; RW-003/005 KEEP+표현/순서 | 세 차원, assessment/scope ID, many-to-many trace | 기존 0.1.0의 주 라벨 집계로 새 결론을 강제하지 말고 per-unit 관계와 관련 액션의 비교 기록을 별도 설계 |
| 조건·범위가 수치와 분리될 위험 | RW-008의 서로 다른 checkpoint/E2E, RW-011의 비용, RW-012의 regression/귀속 및 119 식별자와 4,802개 표본 혼동 | elements, qualifies/depends_on, local exposure | metric/experiment/cohort/checkpoint/measurement boundary의 일관된 annotation 지침과 보호 요소 분해 예제가 필요 |
| 실제 목적지와 이미 있는 내용을 대조하지 않는 이동 | RW-009/010 AGENTS 404; RW-013 실제 OAuth 문서; RW-016 실제 MIGRATION | destination_reviews, destination inventory, consolidation contributions | verified_context와 revised-output preservation 검증을 구별. 후보에 연결된 문서를 먼저 조회하고 검색 실패/부재/미조회도 구별 |
| 경고라는 이유로 무조건 남기거나 제거 | RW-007/012/020의 독자 과제가 다름 | per-scope exposure, each_member vs across_group | 현재 claim의 최소 해석 조건 판단 rubric, 중복 조건의 현지 통합 승인 규칙 필요 |
| source assertion과 새 실행 증거 혼동 | RW-005/006/013의 테스트·CI·refresh 기록 | EvidenceRef.kind/authority_basis, execution status | 사실 확인 수준(원문 진술/동일 코드 확인/새 실행/사람 검토)을 UI·평가 기록에서 일관되게 보여줄 필요 |
| mutable snapshot과 현재 접근 상태 혼동 | RW-015 HTTP, RW-019/020 PR body | source_record, ArtifactRef/digest | body capture time/digest와 live retrieval time, redirect chain, 과거/현재의 차이를 표현할 수집 규약 필요 |
| 지정되지 않은 문체·새 규칙의 확정 | RW-014 이모지, RW-016 구성 설명→금지 | assumptions/constraints, resolver review | 원 사용자 지시가 없는 과거 annotation의 권한 수준·문체 scope를 명시; 미확인 선호를 강제하지 않기 |

이 표는 구현·schema migration 제안이다. 공통 모델은 이미 다수의 경계를 표현하며, 이번 검토에서 새 enum/API/수치 기준을 동결하지 않는다.

## 다음 단계와 사람 검토 경계

1. 사용자/사람 검토자는 먼저 RW-008의 원하는 제출 목적·구조, RW-009/010의 문서 역할 분담, RW-014의 문체 근거를 확인한다. 이번 모델 재검토의 제안을 그대로 정답으로 채택하지 않는다.
2. 독립 사람이 unit 분할·보존·배치·표현을 별개로 `agree / disagree / uncertain`으로 기록한다. 가능하면 두 사람이 중첩 subset을 독립 검토하고 불일치 이유를 해결한다. 작성자/리뷰어 이름·일자·근거를 별도 남긴다. 현재 모든 human review는 pending이다.
3. P1 항목부터 원시 근거와 문맥을 확보한다. RW-008의 FastAPI/ThreadingHTTPServer 및 E2E 경계, RW-012의 평가/귀속, RW-014 지원 주장, RW-015 다운로드, RW-017 실제 테스트 예시, RW-018 배포 기준을 우선한다. 외부 저장소 수정은 별도 작업이다.
4. 승인된 소수 사례에만 전체 source/destination 수정본을 만들고 protected elements·source/target trace·현지 조건 노출·전체 문서 의미를 검토한다. RW-013의 이미 있는 OAuth 문서는 중복 통합 대상이며 새 목적지 생성을 기본으로 하지 않는다. 확인되지 않은 목적지는 REVIEW로 남긴다.
5. 그 후 annotation 구조/오프셋 규약·사람 승인·held-out split을 결정한다. 기존 fixture 재라벨링/골드 확정/벤치마크 점수/학습 투입은 이 PR의 결과가 아니다. 실제 validation engine이 구현된 뒤에만 B2 실행과 자동 gate 결과를 보고한다.

## 출처 장부와 재현 범위

아래 ID는 JSON의 source manifest와 같다. 모든 digest/문자 길이는 JSON에 있으며 exact Git blob을 다시 조회해 재현할 수 있다. 현지 unit offset은 그 blob 원문에 주소를 갖는다. PR snapshot은 JSON에 exact excerpt를 별도 저장했다. source 전체 사본·개인 cache·AGY 실행 로그는 추가하지 않았다.

| ID | 고정 파일 | blob SHA | 조회 범위 / 판단 한계 |
| --- | --- | --- | --- |
| S01 | [nanocode00/chatgpt2codex/README.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/README.md) | `5c9aeff92d6bbc092d98f84cbe3a0fe29838b6f0` | 전체 조회 / 관련 구간 수작업 검토 |
| S02 | [nanocode00/chatgpt2codex/docs/INSTALL.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/INSTALL.md) | `6c9d228e844fae6421366eec895375f62a916aba` | 전체 조회 / 관련 구간 수작업 검토 |
| S03 | [nanocode00/chatgpt2codex/docs/RELEASE_NOTES_v0.3.1.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/RELEASE_NOTES_v0.3.1.md) | `d6b804f59e7e992c65a08511b6bc0077b7c9712b` | 전체 조회 / 관련 구간 수작업 검토 |
| S04 | [nanocode00/chatgpt2codex/docs/TAURI_F4D3_WINDOWS_CLI_REGISTRATION.md](https://github.com/nanocode00/chatgpt2codex/blob/dcc9ed7e18802800ae8b0536a232875b2a29eb05/docs/TAURI_F4D3_WINDOWS_CLI_REGISTRATION.md) | `109fafaa0ee8249dd443027aaf5cbc2586f14041` | 전체 조회 / 관련 구간 수작업 검토 |
| S05 | [nanocode00/resume/experiences/README.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/README.md) | `b71bbcb8782b5b45716dc5c8bab7506435590d9f` | 전체 조회 / 관련 구간 수작업 검토 |
| S06 | [nanocode00/resume/resume.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/resume.md) | `6c3fdd833e3b0b2259136c7a49c05392df1d38ea` | 전체 조회 / 관련 구간 수작업 검토 |
| S07 | [nanocode00/resume/README.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/README.md) | `6e3e3e02f7aaef0e1d433971f8fdcbe41013c1f6` | 전체 조회 / 관련 구간 수작업 검토 |
| S08 | [nanocode00/resume/guides/resume-experience-writing.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/guides/resume-experience-writing.md) | `4d92cc824e0844630a7bb71e96683bd827e7f895` | 전체 조회 / 관련 구간 수작업 검토 |
| S09 | [nanocode00/resume/experiences/crypto-lob-prediction.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/crypto-lob-prediction.md) | `cddfc532673ffd28d469ea671bb549a486a32b97` | 전체 조회 / 관련 구간 수작업 검토 |
| S10 | [nanocode00/QuotaTray/README.md](https://github.com/nanocode00/QuotaTray/blob/e62eb5c37fbf7265a7937f3939bf99681e38cb03/README.md) | `3a3209e9caf26dce59e87a9bb66bf04174e4395e` | 전체 조회 / 관련 구간 수작업 검토 |
| S11 | [nanocode00/project3-planning/README.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/README.md) | `ebdb5156798abab32fc56298042708c123f1f244` | 전체 조회 / 관련 구간 수작업 검토 |
| S12 | [nanocode00/project3-planning/docs/GATES.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/docs/GATES.md) | `beadd876250fa235938246fc5406234aa2ab1b02` | 전체 조회 / 관련 구간 수작업 검토 |
| S13 | [nanocode00/mallo-intro/README.md](https://github.com/nanocode00/mallo-intro/blob/916a3df7b6481d78c1a5fe95b53565f4fb7d91df/README.md) | `463a2993d5b5dccc4fe48bf71d306266f4cf04cb` | 전체 조회 / 관련 구간 수작업 검토 |
| S14 | [nanocode00/resume/experiences/mallo.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/mallo.md) | `68fea93ce39aa2c8b5ec7637c34b37cc4c989b75` | 전체 조회 / 관련 구간 수작업 검토 |
| S15 | [nanocode00/resume/experiences/malhaebom.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/malhaebom.md) | `381ba2c0c53b4beb308e1b4d88b72d4d76e0d9de` | 전체 조회 / 관련 구간 수작업 검토 |
| S16 | [nanocode00/resume/experiences/malhaebom-rework-checkpoint.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/malhaebom-rework-checkpoint.md) | `6a2a12808c4bd777dca84c1ed57c8410301d2f32` | 전체 조회 / 관련 구간 수작업 검토 |
| S17 | [nanocode00/resume/experiences/mallo-rework-checkpoint.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/mallo-rework-checkpoint.md) | `48039dcfa73c75fab92374f1f706c03f44fff2e5` | 전체 조회 / 관련 구간 수작업 검토 |
| S18 | [nanocode00/resume/experiences/hci-stock-service-evidence-ledger.md](https://github.com/nanocode00/resume/blob/a01e81eb02949390b2b7a97e2326a1ea9a19f3b7/experiences/hci-stock-service-evidence-ledger.md) | `15c8c1401122eee78d33bf3cc248a45bb747c5bc` | 전체 조회 / 관련 구간 수작업 검토 |
| S19 | [nanocode00/project3-planning/AGENTS.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/AGENTS.md) | `88539974793b1060662efad1ffe797ebd0e50b09` | 전체 조회 / 관련 구간 수작업 검토 |
| S20 | [nanocode00/project3-planning/MIGRATION.md](https://github.com/nanocode00/project3-planning/blob/0f5b6f8068db58d58045880bd6e94f64b7ec7537/MIGRATION.md) | `a2120d09409bd1fcb054522ac5e85f461ed97eff` | 전체 조회 / 관련 구간 수작업 검토 |
| S21 | [nanocode00/mallo-intro/assets/images/README.md](https://github.com/nanocode00/mallo-intro/blob/916a3df7b6481d78c1a5fe95b53565f4fb7d91df/assets/images/README.md) | `f476b17cfc4b522d292087e9f2d9303fd2ce5ac7` | 전체 조회 / 관련 구간 수작업 검토 |
| S22 | [nanocode00/mallo-intro/assets/videos/README.md](https://github.com/nanocode00/mallo-intro/blob/916a3df7b6481d78c1a5fe95b53565f4fb7d91df/assets/videos/README.md) | `e057356b9c84925fb07169f956b40533dcd1aa60` | 전체 조회 / 관련 구간 수작업 검토 |
| S23 | [nanocode00/mallo-intro/evaluator.html](https://github.com/nanocode00/mallo-intro/blob/916a3df7b6481d78c1a5fe95b53565f4fb7d91df/evaluator.html) | `a4020e9220cf2685a20a232fbdf3b16bea64ebb0` | 전체 조회 / 관련 구간 수작업 검토 |
| S24 | [aihuman-7th/proj1-d/artifacts/intro/README.md](https://github.com/aihuman-7th/proj1-d/blob/fc5ffe2750868403091202748f5e3e10e7e872c0/artifacts/intro/README.md) | `463a2993d5b5dccc4fe48bf71d306266f4cf04cb` | 전체 조회 / 관련 구간 수작업 검토 |
| S25 | [nanocode00/QuotaTray/docs/antigravity-oauth-runtime.md](https://github.com/nanocode00/QuotaTray/blob/e62eb5c37fbf7265a7937f3939bf99681e38cb03/docs/antigravity-oauth-runtime.md) | `a100f2000315134c8b84b83989dd11c99177d200` | 전체 조회 / 관련 구간 수작업 검토 |

RW-015 추가 HTTP 확인은 2026-11-05 15:39 KST에 공개 비인증 GET으로 수행했다. `nanocode00/QuotaTray/releases`는 200이며 최종 URL이 같았고, `HonorBear/QuotaTray/releases`는 404이며 최종 URL이 같았다. 웹 조회 도구는 두 URL에 cache miss로 실패해 Python 표준 HTTP 클라이언트로 별도 확인했다. source Git 조회는 GitHub 연결 도구를 사용했다. 이는 binary 다운로드·실행 검증이 아니다.

## 이번 PR의 검증 범위

- 20개 case와 단위 ID, source span/digest, 기존 발췌 일치, 선언 scope의 참조, 목적지 기존 단위·관계 참조, 다섯 수작업 확인 기록의 존재를 로컬 정적 검사했다. 이는 문서 장부의 무결성 점검이며 LogicWrite 검증 엔진 실행이 아니다.
- `git diff --check`, 새 문서의 로컬 링크/앵커·표·JSON parse, 기존 tracked 파일의 main 대비 동일성을 확인한다. 기존 평가 JSON·schema 0.1.0·기존 문서는 수정하지 않는다.
- 최종 전체 수정본/engine·모델 성능/B0·B1·B2/실제 CI·배포·독립 사람 승인을 검증한 결과는 없다. Draft PR은 사람 검토용이며 병합하지 않는다.

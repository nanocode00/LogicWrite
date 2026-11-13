# 기존 17건 검토 내용 — 정식 기록 연결 검토안

**판단 재검토가 아니다.** 이미 제출한 사용자 최초/최종 판단·Codex 반례 검토·개발용 골드 포함 승인 17건을 유지한다.

- 기존 포함 승인: 17/17
- 기존 신규 적격성/활성화: 0/17, 기존 골드 SP-001~012 12건 유지
- Codex 인용 근거 후보: 34개, 아직 사용자가 정식 최종 증거로 확인한 것은 0개
- 반론 응답 원문: 17건 모두 사용자는 Codex의 반론 타당성 평가에 동의했다. 정식 challenge별 accept/reject/defer는 매핑하지 않는다.
- 실제로 확인이 필요한 범위: 최종 증거 인용의 채택, 제안한 challenge별 응답, 평가 한계 인지 및 UNRESOLVED 4건의 최종 미해결 사유 확인. 승인되지 않은 값은 모두 null로 유지

## 사례별 기존 판단과 제안 근거

| 사례 | 사용자 최종 판단 | 최초 사용자 이유 | 검토 상태 |
|---|---|---|---|
| GC-001 | PRESERVED | 정보는 같고 표현의 차이 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-002 | VIOLATION | 근거 없는 지원 버전 변경 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-003 | UNRESOLVED | 전체 내용을 다시 받아야 함 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-004 | PRESERVED | 정보는 동일, 표현 방식만 다름 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-005 | VIOLATION | 근거 없는 시간 변경 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-006 | UNRESOLVED | 전체 내용을 재전송받아야 함 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-007 | PRESERVED | 정보는 동일, 표현 방식 차이 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-008 | VIOLATION | 버전 출력 후 동작 변경 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-009 | UNRESOLVED | 이동된 문서의 본문이 필요함 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-010 | PRESERVED | 내용은 보존되고 위치만 변경 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-011 | VIOLATION | 기본 활성화 여부와 플래그 역할 두 가지 변경 | 포함 승인됨 / 정식 응답·증거 미확인 |
| GC-012 | UNRESOLVED | 이동된 문서의 내용이 필요함 | 포함 승인됨 / 정식 응답·증거 미확인 |
| SP-013 | VIOLATION | 필수 조건 위반 | 포함 승인됨 / 정식 응답·증거 미확인 |
| SP-014 | PRESERVED | 다른 문서로 이동했으며 계약 충족 | 포함 승인됨 / 정식 응답·증거 미확인 |
| SP-015 | PRESERVED | 다른 문서로 이동했으며 계약 충족 | 포함 승인됨 / 정식 응답·증거 미확인 |
| SP-016 | PRESERVED | 계약에서 지정한 v2 기준 내용 선택 | 포함 승인됨 / 정식 응답·증거 미확인 |
| SP-017 | PRESERVED | 전체 본문 제공, 내용 완전히 동일 | 포함 승인됨 / 정식 응답·증거 미확인 |

## Codex 반론과 근거 인용 (사용자 채택 전)

### GC-001 · PRESERVED

- 기존 최초 판단: 정보는 같고 표현의 차이
- Codex가 검토한 반론: 능동문을 수동문으로 바꾸면서 공식 지원의 주체나 버전 범위가 달라졌다고 반박할 수 있다.
- Codex의 반론 타당성 평가: 반박 불성립: by Requests가 지원 주체를 그대로 명시하고 officially와 3.10+도 동일하다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 1574:1616]: “Requests officially supports Python 3.10+.”
- AI 출처 인용 후보 [candidate / main / 1574:1623]: “Python 3.10+ is officially supported by Requests.”

### GC-002 · VIOLATION

- 기존 최초 판단: 근거 없는 지원 버전 변경
- Codex가 검토한 반론: 3.8+가 3.10+를 포함하므로 기존 지원 범위는 남고, 실제 지원 범위의 정정일 수도 있다는 반박이 최선이다.
- Codex의 반론 타당성 평가: 반박 불성립: 포함관계는 동등성이 아니다. 3.8과 3.9의 공식 지원을 새로 주장하며 정정 허가나 근거가 없다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 VIOLATION
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 1574:1616]: “Requests officially supports Python 3.10+.”
- AI 출처 인용 후보 [candidate / main / 1574:1615]: “Requests officially supports Python 3.8+.”

### GC-003 · UNRESOLVED

- 기존 최초 판단: 전체 내용을 다시 받아야 함
- Codex가 검토한 반론: 제공 후보에서 기능 목록과 복제 안내가 모두 사라졌으므로 이미 필수 정보 누락 위반이라고 반박하거나, 제공 접두부가 동일하므로 보존이라고 반박할 수 있다.
- Codex의 반론 타당성 평가: 두 반박 모두 불성립: 누락은 완성 후보에서의 삭제가 아니라 명시된 전송 절단이다. 접두부 동일성만으로 미제공 후반부 보존도 입증할 수 없다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 UNRESOLVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- 확인할 최종 미해결 이유 후보(기존 최초 이유): 전체 내용을 다시 받아야 함
- AI 출처 인용 후보 [source / main / 1618:1656]: “## Supported Features & Best–Practices”
- AI 출처 인용 후보 [candidate / main / 1574:1616]: “Requests officially supports Python 3.10+.”

### GC-004 · PRESERVED

- 기존 최초 판단: 정보는 동일, 표현 방식만 다름
- Codex가 검토한 반론: after를 없애면서 5초 경과라는 시간 조건을 즉시 인과관계나 정확한 발생 시각으로 강화했다는 반박이 가능하다.
- Codex의 반론 타당성 평가: 반박 불성립: 5 seconds of network inactivity는 동일한 비활성 지속시간을 명시한다. By default와 예외 종류도 그대로이며 주변 설정 예외·세부 타임아웃 설명이 유지된다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 61:153]: “The default behavior is to raise a `TimeoutException` after 5 seconds of ⏎ network inactivity.”
- AI 출처 인용 후보 [candidate / main / 61:133]: “By default, 5 seconds of network inactivity raises a `TimeoutException`.”

### GC-005 · VIOLATION

- 기존 최초 판단: 근거 없는 시간 변경
- Codex가 검토한 반론: 후반 코드 주석의 기본 5초가 그대로이므로 독자는 원래 값을 복원할 수 있고 50은 단순 오타이므로 위반이 아니라는 반박이 최선이다.
- Codex의 반론 타당성 평가: 반박 불성립: 복원 가능성이나 오타 가능성은 수치 보존을 대신하지 않는다. 동일 기본 동작을 50초로 명시하며 5초 주석과 충돌한다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 VIOLATION
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 115:133]: “after 5 seconds of”
- AI 출처 인용 후보 [candidate / main / 115:134]: “after 50 seconds of”

### GC-006 · UNRESOLVED

- 기존 최초 판단: 전체 내용을 재전송받아야 함
- Codex가 검토한 반론: 후보에 세부 구성과 네 종류 타임아웃 설명이 없으므로 위반이 이미 확정됐다고 반박하거나, 있는 부분이 동일하므로 보존이라고 반박할 수 있다.
- Codex의 반론 타당성 평가: 두 반박 모두 불성립: 후보는 전송 중 절단된 partial 자료다. 알려진 삭제로 취급할 수 없고 미제공 부분의 보존도 추정할 수 없다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 UNRESOLVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- 확인할 최종 미해결 이유 후보(기존 최초 이유): 전체 내용을 재전송받아야 함
- AI 출처 인용 후보 [source / main / 1169:1201]: “## Fine tuning the configuration”
- AI 출처 인용 후보 [candidate / main / 1092:1163]: “client = httpx.Client(timeout=None)  # Disable all timeouts by default.”

### GC-007 · PRESERVED

- 기존 최초 판단: 정보는 동일, 표현 방식 차이
- Codex가 검토한 반론: 문장의 즉시성 범위가 출력·종료 전체에서 출력만으로 좁아지고 then이 종료 지연을 허용한다는 반론을 검토했다.
- Codex의 반론 타당성 평가: 성립하지 않음. 원문도 즉시 출력한 뒤 프로그램이 종료된다고 서술하며 종료의 별도 시간 한계는 제시하지 않는다. then은 동일 동작의 순서를 명확히 할 뿐이다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 2050:2165]: “{func}`version_option` adds a `--version` option which immediately prints the version number and exits the program.”
- AI 출처 인용 후보 [candidate / main / 2050:2167]: “The `--version` option added by {func}`version_option` immediately prints the version number, then exits the program.”

### GC-008 · VIOLATION

- 기존 최초 판단: 버전 출력 후 동작 변경
- Codex가 검토한 반론: 실제 코드나 실행 결과가 바뀌지 않았고 버전 출력 기능이 유지되므로 보존이라는 반론을 검토했다.
- Codex의 반론 타당성 평가: 성립하지 않음. 계약은 실행 검증이 아닌 문서 주장 보존을 요구한다. 출력 후 종료와 계속 실행은 정반대 동작이며 코드 변경 여부와 무관하다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 VIOLATION
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 2050:2165]: “{func}`version_option` adds a `--version` option which immediately prints the version number and exits the program.”
- AI 출처 인용 후보 [candidate / main / 2050:2177]: “{func}`version_option` adds a `--version` option which immediately prints the version number and continues running the program.”

### GC-009 · UNRESOLVED

- 기존 최초 판단: 이동된 문서의 본문이 필요함
- Codex가 검토한 반론: 확인 옵션의 조건·콜백·예제 코드가 main에서 사라졌으므로 이미 위반이라고 확정할 수 있다는 반론과, 계약이 링크 이동을 허용하므로 보존이라는 반론을 모두 검토했다.
- Codex의 반론 타당성 평가: 어느 쪽도 확정에 충분하지 않음. linked_document 노출과 details.md 이동은 명시적으로 허용되므로 main의 삭제 자체가 위반은 아니다. 반대로 링크 존재는 목적지 내용 보존의 증거가 아니다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 UNRESOLVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- 확인할 최종 미해결 이유 후보(기존 최초 이유): 이동된 문서의 본문이 필요함
- AI 출처 인용 후보 [candidate / main / 987:1026]: “See [confirmation details](details.md).”
- AI 출처 인용 후보 [source / main / 1102:1208]: “boolean `--yes` flag and asking for confirmation if the user did not provide it and to fail in a callback:”

### GC-010 · PRESERVED

- 기존 최초 판단: 내용은 보존되고 위치만 변경
- Codex가 검토한 반론: 준비 상태를 건강 상태보다 먼저 제시하여 점검 우선순위나 두 endpoint의 의미가 달라진다는 반론을 검토했다.
- Codex의 반론 타당성 평가: 성립하지 않음. 문서는 순차 실행이나 우선순위를 지정하지 않고 각 endpoint를 독립된 제목·코드·설명으로 정의한다. 각 블록 전체가 함께 이동했다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 272:422]: “## Readiness check ⏎  ⏎ ``` ⏎ GET /-/ready ⏎ HEAD /-/ready ⏎ ``` ⏎  ⏎ This endpoint returns 200 when Prometheus is ready to serve traffic (i.e. respond to queries).”
- AI 출처 인용 후보 [source / main / 133:269]: “## Health check ⏎  ⏎ ``` ⏎ GET /-/healthy ⏎ HEAD /-/healthy ⏎ ``` ⏎  ⏎ This endpoint always returns 200 and should be used to check Prometheus health.”

### GC-011 · VIOLATION

- 기존 최초 판단: 기본 활성화 여부와 플래그 역할 두 가지 변경
- Codex가 검토한 반론: 같은 플래그를 사용하고 reload 기능·SIGHUP 대안을 유지하므로 설정 설명의 관점 차이라는 반론을 검토했다.
- Codex의 반론 타당성 평가: 성립하지 않음. enabled와 disabled의 교환은 관점이 아니라 기본 상태와 플래그 전환 방향의 반전이다. Quit의 원문 유지가 Reload의 변경을 보상하지 않는다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 VIOLATION
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / main / 555:637]: “It's disabled by default and can be enabled via the `--web.enable-lifecycle` flag.”
- AI 출처 인용 후보 [candidate / main / 555:637]: “It's enabled by default and can be disabled via the `--web.enable-lifecycle` flag.”

### GC-012 · UNRESOLVED

- 기존 최초 판단: 이동된 문서의 내용이 필요함
- Codex가 검토한 반론: 운영에 필요한 reload/quit 경로·기본 비활성 조건·플래그·대안 신호가 main에서 모두 빠졌으므로 위반 확정이라는 반론을 검토했다. 또한 링크 이동 허용을 근거로 보존 확정이 가능한지도 검토했다.
- Codex의 반론 타당성 평가: 확정 반론은 성립하지 않음. 계약은 details.md로 상세를 옮겨 링크로 노출하는 구성을 허용한다. 따라서 main 누락만으로 위반이라 할 수 없고, 미제공 목적지의 보존을 추정해서도 안 된다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 UNRESOLVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- 확인할 최종 미해결 이유 후보(기존 최초 이유): 이동된 문서의 내용이 필요함
- AI 출처 인용 후보 [candidate / main / 425:484]: “## Lifecycle operations ⏎  ⏎ See [reload and quit](details.md).”
- AI 출처 인용 후보 [source / main / 475:637]: “This endpoint triggers a reload of the Prometheus configuration and rule files. It's disabled by default and can be enabled via the `--web.enable-lifecycle` flag.”

### SP-013 · VIOLATION

- 기존 최초 판단: 필수 조건 위반
- Codex가 검토한 반론: 문서 묶음 전체에는 캐시 조건이 같은 문장으로 남고 설치 문서에 해소 가능한 링크가 있으므로 구조 변경 허용에 따라 보존으로 볼 수 있다는 반박이다.
- Codex의 반론 타당성 평가: 성립하지 않음. 전체 의미의 잔존은 맞지만 R1 same_document 및 설치 문서 직접 노출이라는 구체적인 제약을 충족하지 못한다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 VIOLATION
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / install / 19:49]: “캐시가 있는 경우에만 오프라인 검색을 사용할 수 있다.”
- AI 출처 인용 후보 [candidate / install / 19:60]: “오프라인 검색 조건은 [유지보수](maintenance.md)를 참조한다.”

### SP-014 · PRESERVED

- 기존 최초 판단: 다른 문서로 이동했으며 계약 충족
- Codex가 검토한 반론: 캐시 조건이 설치 문서에서 사라져 첫 사용자가 조건을 놓칠 수 있으므로 VIOLATION이라는 반박이다.
- Codex의 반론 타당성 평가: 성립하지 않음. 이 계약은 오프라인 검색을 선택 기능으로 정하고 연결 문서 노출을 명시적으로 허용한다. 일반적인 첫 사용 위험으로 계약을 강화할 수 없다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / install / 19:49]: “캐시가 있는 경우에만 오프라인 검색을 사용할 수 있다.”
- AI 출처 인용 후보 [candidate / install / 19:60]: “오프라인 검색 조건은 [유지보수](maintenance.md)를 참조한다.”

### SP-015 · PRESERVED

- 기존 최초 판단: 다른 문서로 이동했으며 계약 충족
- Codex가 검토한 반론: README에서 PKG 선택 근거가 빠지고 외부 목적지로 이동했으므로 non-blocking Doctor 또는 미래 DMG 가능성이 누락되었거나 목적지 보존을 추정한 것은 아닌지 반박한다.
- Codex의 반론 타당성 평가: 성립하지 않음. 목적지의 전후 전체 본문이 제공되며 원래 절 전체가 문자 그대로 추가되었다. README에 PACKAGING.md 링크가 있고 계약이 이 이동을 명시 허용한다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / readme / 2982:3381]: “### Why PKG Instead Of DMG? ⏎  ⏎ For this release, **PKG is the better fit**. A DMG is nicer for drag-and-drop ⏎ apps, but this app needs to install a menu bar runtime under Applications, ⏎ bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor. ⏎ PKG gives beginners a clearer "install and open" path. A signed/notarized DMG ⏎ can still be added later for a more consumer-style download. ⏎  ⏎ ”
- AI 출처 인용 후보 [candidate / packaging / 28:427]: “### Why PKG Instead Of DMG? ⏎  ⏎ For this release, **PKG is the better fit**. A DMG is nicer for drag-and-drop ⏎ apps, but this app needs to install a menu bar runtime under Applications, ⏎ bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor. ⏎ PKG gives beginners a clearer "install and open" path. A signed/notarized DMG ⏎ can still be added later for a more consumer-style download. ⏎  ⏎ ”

### SP-016 · PRESERVED

- 기존 최초 판단: 계약에서 지정한 v2 기준 내용 선택
- Codex가 검토한 반론: 과거 원문 30초가 60초로 바뀌었으므로 수치 보존 위반 또는 상충 원문 때문에 UNRESOLVED라는 반박이다.
- Codex의 반론 타당성 평가: 성립하지 않음. 계약은 해시까지 특정한 v2만 기준으로 승인되었다고 가정하고 v1을 보존 대상에서 명시 제외한다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / policy-v1 / 10:25]: “요청 제한 시간은 30초다.”
- AI 출처 인용 후보 [source / policy-v2 / 10:25]: “요청 제한 시간은 60초다.”

### SP-017 · PRESERVED

- 기존 최초 판단: 전체 본문 제공, 내용 완전히 동일
- Codex가 검토한 반론: 전체 본문 제공 표기가 합성 대체에 불과하므로 실제 누락된 원문 보존은 증명되지 않아 UNRESOLVED여야 한다는 반박이다.
- Codex의 반론 타당성 평가: 현재 과제 범위에서는 성립하지 않음. 실제 원문 관측의 입증과 주어진 합성 전후 본문 사이의 의미 보존은 별개다. 두 complete 본문은 정확히 동일하다.
- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 PRESERVED
- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)
- AI 출처 인용 후보 [source / update / 0:41]: “# 업데이트 ⏎  ⏎ 자동 업데이트는 지원하지 않는다. 수동 재설치가 필요하다. ⏎ ”
- AI 출처 인용 후보 [candidate / update / 0:41]: “# 업데이트 ⏎  ⏎ 자동 업데이트는 지원하지 않는다. 수동 재설치가 필요하다. ⏎ ”

## 제출·활성화 경계

이 책자는 사용자 확인을 준비한 초안이며 새로운 사용자 증거·정식 최종 이벤트·골드 활성화가 아니다.
정식 사용자 증빙으로 반영할 때는 이 문서와 confirmation-batch.json을 명시적으로 확인한 새 사용자 발언을 원문 그대로 별도 기록하고, 사건의 실제 시간 순서와 기존 이력의 출처를 보존해야 한다.
사용자 확인 이후에도 review.py의 정식 event-chain 충족 여부는 독립적으로 검증해야 하며, 자동으로 개발용 골드를 활성화하지 않는다.

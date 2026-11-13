# SP-015

## 사용자 최초 판단
PRESERVED — 다른 문서로 이동했으며 계약 충족
입력 SHA-256: `632a7c3afae5e5cb64781d3958b36d4e366ea54a2fe04642030b3eadd9bbe5d4`

## 독립 AI 반례
계약 R1은 'PKG 선택 이유 전체'를 packaging 문서에 보존할 것을 요구합니다. 원문(README)에는 PKG 선택의 구체적 이유(메뉴바 런타임 설치, Node/cloudflared 번들링, non-blocking Doctor 실행, 초보자 경로 명확성)가 명시되어 있습니다. 그러나 후보 packaging 문서에는 이러한 구체적 이유들이 누락된 채 '패키지 선택 관련 안내.'라는 추상적 문구만 존재하며, 이는 '전체' 보존 요구를 충족하지 못합니다. 또한 README에서 해당 섹션을 단순히 링크로 대체하면서 핵심 기술적 근거가 소실되었으므로 의미 보존이 깨졌다고 볼 수 있습니다.

## AI의 반론 타당성 평가
반박 시도는 실패합니다. 제공된 증거를 재확인하면, 후보 packaging 문서(`/candidate_documents/1/content`)에는 원문 README에 있던 PKG 선택 이유(메뉴바 런타임, Node/cloudflared, non-blocking Doctor 등)가 빠짐없이 포함되어 있습니다. 초기 판단이 옳았으며, 계약 R1의 '전체 보존' 요구가 충족되었습니다. README에서 해당 내용을 링크로 대체한 것은 계약의 '의미가 같은 표현과 구조 변경을 허용한다'는 조항에 부합합니다.

## 정확한 인용 근거

- `/writing_contract/required_information/0/description`

```text
PKG 선택 이유 전체·non-blocking·DMG 미래 가능성을 packaging 문서에 보존하고 README에서 링크 제공
```

- `/source_documents/0/content`

```text
For this release, **PKG is the better fit**. A DMG is nicer for drag-and-drop
apps, but this app needs to install a menu bar runtime under Applications,
bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.
PKG gives beginners a clearer "install and open" path. A signed/notarized DMG
can still be added later for a more consumer-style download.
```

- `/candidate_documents/1/content`

```text
# Packaging

패키지 선택 관련 안내.

### Why PKG Instead Of DMG?

For this release, **PKG is the better fit**. A DMG is nicer for drag-and-drop
apps, but this app needs to install a menu bar runtime under Applications,
bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.
PKG gives beginners a clearer "install and open" path. A signed/notarized DMG
can still be added later for a more consumer-style download.
```

## AI 권장 판단
PRESERVED

## 남은 불확실성
없음. 후보 문서에 원문의 핵심 정보가 정확히 보존되어 있음이 확인됨.

## 사용자 확인 사항
제공된 작성 계약과 수정 전후 문서 전체를 비교하여 PRESERVED / VIOLATION / UNRESOLVED 중 하나와 근거를 제시한다.

## 사용자 응답 (미작성)

반론에 대한 선택: [ ] 동의 [ ] 반박 [ ] 보류

근거: ______

사용자 최종 판단: ______

개발용 골드 포함 승인: 미결정

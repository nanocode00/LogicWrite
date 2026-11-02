# M0: 실제 저장소 문서 평가 후보

> **상태:** 잠정 라벨 20건. 사용자가 소유한 공개 GitHub 저장소를 검토해 만들었지만, 사람의 독립 검수나 모델 성능 검증을 마친 **골드셋이 아니다**.

## 수집 범위

- 총 **20건**: 개선·확인 후보 **8건**, 수정하지 않는 정상 대조 사례 **12건**.
- 공개 저장소 **5개**: `nanocode00/chatgpt2codex`, `nanocode00/resume`, `nanocode00/QuotaTray`, `nanocode00/project3-planning`, `nanocode00/mallo-intro`.
- 출처 유형: Git 파일과 PR 설명. Git 파일은 **정확한 커밋 SHA와 blob SHA**, 행 범위 및 원문 스냅샷을 포함한다.
- PR 설명은 헤드 커밋과 별개로 편집될 수 있으므로 **조회 당시의 본문 발췌 스냅샷**과 조회일을 저장한다. PR 헤드 SHA만으로 본문 변경을 고정했다고 주장하지 않는다.
- 비공개 저장소의 내용은 옮기지 않았다. 사람 이름·연락처·토큰·내부 로그 등 민감정보가 포함된 발췌를 의도적으로 제외했다.

## 후보별 검토

| ID | 대상 | 잠정 판단 | 검토 포인트 |
| --- | --- | --- | --- |
| RW-001 | `nanocode00/chatgpt2codex` `README.md` | MOVE | 패키지 선택의 내부 의사결정은 첫 방문 사용자의 설치·사용 이해보다 설계 기록에 가깝다. 제품 설계 문서 이동 여부를 검토한다. |
| RW-002 | `nanocode00/chatgpt2codex` `docs/INSTALL.md` | MOVE | 설치 순서를 찾는 독자에게 PKG 대 DMG 선택 근거는 우선순위가 낮다. 별도 설계 설명으로 이동 검토한다. |
| RW-003 | `nanocode00/chatgpt2codex` `README.md` | MOVE | 프로젝트 별점 요청이 첫 화면의 설치·기능 안내보다 먼저 노출된다. 홍보 의도는 존중하되 아래로 이동할지 검토한다. |
| RW-004 | `nanocode00/chatgpt2codex` `README.md` | KEEP | Quick Tunnel URL의 비영속성과 계정 요구사항은 실제 사용자의 구성 결정에 필요하다. |
| RW-005 | `nanocode00/chatgpt2codex` `docs/RELEASE_NOTES_v0.3.1.md` | KEEP | 변경사항을 어떤 동작이 개선됐는지로 구체화하며 실행·권한 보존 범위를 전달한다. |
| RW-006 | `nanocode00/chatgpt2codex` `docs/TAURI_F4D3_WINDOWS_CLI_REGISTRATION.md` | KEEP | 별도 CLI 등록의 권한 범위·제거 안전장치 등은 검토와 승인에 필수인 상세 조건이다. |
| RW-007 | `nanocode00/resume` `experiences/README.md` | MOVE | 경험 색인 내부에 개별 프로젝트의 긴 검증 결과가 연속 배치돼 탐색 목적을 방해할 수 있다. 상세 검증은 개별 근거 문서로 이동하고 색인에 링크만  |
| RW-008 | `nanocode00/resume` `resume.md` | COMPRESS | 채용용 요약을 찾는 독자에게 다수의 모델 이름·수치·포트·배포 경로가 하나의 프로젝트 설명에 밀집한다. 핵심 기여와 성과를 중심으로 압축할지 검토한 |
| RW-009 | `nanocode00/resume` `README.md` | KEEP | 마스터 이력서와 세부 경험 원장에 서로 다른 역할을 부여하고 공개 저장소의 개인정보 기준까지 밝힌다. |
| RW-010 | `nanocode00/resume` `guides/resume-experience-writing.md` | KEEP | 채용 담당자가 읽는 시간과 필요한 근거를 기준으로 문서 밀도 및 세부 정보 위치를 지정한다. |
| RW-011 | `nanocode00/resume` `experiences/crypto-lob-prediction.md` | KEEP | 무수수료 수익과 수수료 반영 손실은 전제가 다르므로 모순이 아니다. 불리한 결과와 데이터 한계를 반드시 보존한다. |
| RW-012 | `nanocode00/resume` `resume.md` | KEEP | 개인 기여와 팀 기여를 분리하고 합성평가·기존 도메인 성능 악화·미검증 범위를 명시한다. |
| RW-013 | `nanocode00/QuotaTray` `README.md` | MOVE | 일반 사용자 안내와 내부 OAuth 지문 검증 및 TestCli 진단 절차가 함께 나온다. 개발자용 심화 문서에 둘 정보인지 검토한다. |
| RW-014 | `nanocode00/QuotaTray` `README.md` | FLAG | '완벽 지원'은 절대적 표현이다. 각 제공자 지원 수준·검증 범위를 확인하거나 검증된 표현으로 한정할지 검토한다. |
| RW-015 | `nanocode00/QuotaTray` `README.md` | FLAG | 같은 README의 릴리스 링크가 서로 다른 GitHub 소유자명을 가리킨다. 저장소 이전·리다이렉트 여부를 확인해야 한다. |
| RW-016 | `nanocode00/project3-planning` `README.md` | KEEP | 이관 준비 저장소와 실제 적용 대상이 다르고 실행·PR 미수행 범위를 명확히 한다. |
| RW-017 | `nanocode00/project3-planning` `docs/GATES.md` | KEEP | 단순 테스트 통과와 실제 변이 감지를 구분하고 검증 실패 가능성을 명시한다. |
| RW-018 | `nanocode00/mallo-intro` `README.md` | KEEP | 고객용 페이지와 평가자용 페이지의 목적을 분리해 문서 구조에서 독자 차이를 명확히 한다. |
| RW-019 | `nanocode00/resume` PR #19 | KEEP | 변경한 위치와 의도적으로 변경하지 않은 범위를 짧게 전달한다. |
| RW-020 | `nanocode00/resume` PR #20 | KEEP | 합성 평가, 팀 기여, 기존 성능 회귀, 미확정 사항을 숨기지 않는 귀속·검증 경계다. |

## 라벨링 원칙

1. **작성 맥락을 고정:** 발췌만 보고 판단하지 말고 독자, 목적, 글의 유형을 확인한다. 실제 글을 제출용으로 변환하는 가상 계약과 기존 마스터 원본의 목적은 다를 수 있다.
2. **판정 단위 분리:** `MOVE`는 정보의 가치가 없다는 뜻이 아니다. `KEEP`도 문서 전체가 완벽하다는 뜻이 아니라 해당 사례의 표적 우려는 고치지 말아야 한다는 뜻이다.
3. **불확실성 노출:** `FLAG`는 오류 확정이 아니다. URL 차이는 리다이렉트/이전 여부를 확인하고, 절대적 홍보 표현은 근거를 점검해야 한다.
4. **범위와 수치 보존:** 수수료, 제한 조건, 팀/개인 기여, 운영 미검증 사항은 지운다고 좋은 글이 되는 게 아니다.
5. **검토자 승인 전 실험 정답 사용 금지:** 독립 검토자가 `agree`/`disagree`/`uncertain`을 기록하고, 반대 의견은 해결 근거와 함께 남긴다.

## 다음 작업 (미완료)

- [ ] 원문·문맥·출처 링크를 보고 각 사례의 독자와 목적을 사람 검토자가 확인
- [ ] 작업별 판정이 과도한 단축/과교정인지 평가
- [ ] 각 후보에 `reviewer_decision`, 리뷰 사유, 최종 수정/유지 지침을 기록
- [ ] 일부 사례를 홀드아웃으로 고정하고 B0/B1/B2 비교 시 동일 조건 적용
- [ ] 모델/규칙 기반 검사기를 구현한 뒤 탐지율뿐 아니라 **오탐·정보 손실**을 측정

## 데이터 위치

[`tests/fixtures/real-world-candidates.json`](../tests/fixtures/real-world-candidates.json)

별도 PR에서 추가해도 기존 초기 설계 PR #1과 독립적으로 병합 가능한 자료 파일이다.

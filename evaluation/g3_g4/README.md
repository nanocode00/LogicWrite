# G3~G4: 파일럿 검수 준비와 신규 개발용 후보

기준 main: `7b9166de9c019153ceb326aef8912380ddc60d71`. G3는 최종 검수 **준비**, G4는 공개 원문에 통제된 수정을 적용한 **잠정 개발 후보**다. 새 사용자 판단·AI 반례 검토 완료·사람 최종 확정·홀드아웃은 생성하지 않았다.

- [기존 12건 진행표·우선 쟁점](G3.md), [기계 판독 진행표](g3-progress.json)
- [신규 후보 manifest](manifest.json), [출처·라이선스·Git blob 목록](sources.json)
- [개발용/홀드아웃 분리 계획](SPLIT.md), [기계 판독 정책](split-plan.json)

## 신규 후보 12건

각 유형당 정상 4·위반 4·보류 4이며 전건 provisional·gold_eligible=false다. 원문 4개/저장소 계열 4개에서 3건씩 파생했으므로 독립 문서 12개로 세지 않는다. 실제 upstream 편집·모델 실행 결과를 수집한 것이 아니라 공개 원문 전체를 고정한 뒤 AI가 후보와 잠정 답안을 작성했다. 원문의 동작·지원 주장을 독립 실행으로 입증한 자료도 아니다.

| 사례 | 원문 계열 | 통제 수정·자료 공백 | AI 잠정 | 입력 보기 |
| --- | --- | --- | --- | --- |
| GC-001 | requests | README 설치·지원 범위 동의 표현 | PRESERVED | [전체 입력](cases/GC-001.md) |
| GC-002 | requests | README 최소 지원 버전 왜곡 | VIOLATION | [전체 입력](cases/GC-002.md) |
| GC-003 | requests | README 전송 절단 | UNRESOLVED | [전체 입력](cases/GC-003.md) |
| GC-004 | httpx | 타임아웃 기본값·비활성 조건 표현 | PRESERVED | [전체 입력](cases/GC-004.md) |
| GC-005 | httpx | 타임아웃 수치 왜곡 | VIOLATION | [전체 입력](cases/GC-005.md) |
| GC-006 | httpx | 타임아웃 세부 설정 결과 절단 | UNRESOLVED | [전체 입력](cases/GC-006.md) |
| GC-007 | click | CLI 버전 표시·종료 표현 | PRESERVED | [전체 입력](cases/GC-007.md) |
| GC-008 | click | CLI 종료 동작 반전 | VIOLATION | [전체 입력](cases/GC-008.md) |
| GC-009 | click | 확인 옵션 문서 간 MOVE 목적지 미제공 | UNRESOLVED | [전체 입력](cases/GC-009.md) |
| GC-010 | prometheus | 운영 API health·readiness 정상 재배치 | PRESERVED | [전체 입력](cases/GC-010.md) |
| GC-011 | prometheus | reload 기본 비활성·활성 조건 반전 | VIOLATION | [전체 입력](cases/GC-011.md) |
| GC-012 | prometheus | 운영 lifecycle 안내 MOVE 목적지 미제공 | UNRESOLVED | [전체 입력](cases/GC-012.md) |

입력 JSON과 `cases/*.md`는 같은 모든 필드·원문/후보 전체를 담는다. Markdown은 기존 렌더러를 재사용한 표시 자료이며 바이트 해시·근거 오프셋은 JSON content가 기준이다. 모델에는 개별 입력과 참조 스냅샷만 주고 answers/manifest/이 표/기존 검토 기록은 주지 않는다. 근거 위치는 0 기반 Unicode 코드포인트 반열린 구간이다.

보류 4건 중 GC-003/006은 실제 수정 결과가 아닌 **전송 절단된 관측**임을 명시했고, GC-009/012는 MOVE 목적지가 미제공이다. 원문 외부 사실이 미검증이라는 이유로 보류한 것이 아니다. MOVE 계약의 링크 허용은 통제된 시험 조건이며 실제 문서의 적절한 편집 위치를 보편적으로 권고하지 않는다. 정상 표현·재배치는 오류로 보지 않고 확인된 왜곡·손실·근거 없는 추가를 별도 추적한다.

## 출처 고정과 라이선스

| 계열·유형 | 고정 원문 | 라이선스·고지 |
| --- | --- | --- |
| pallets/click / cli_reference | [docs/option-decorators.md](https://github.com/pallets/click/blob/8abb77a8432e03ed14a95f972b44f905279415a7/docs/option-decorators.md) · `8abb77a8432e` | [BSD-3-Clause](sources/click-license.txt) |
| encode/httpx / configuration_guide | [docs/advanced/timeouts.md](https://github.com/encode/httpx/blob/b5addb64f0161ff6bfe94c124ef76f6a1fba5254/docs/advanced/timeouts.md) · `b5addb64f016` | [BSD-3-Clause](sources/httpx-license.txt) |
| prometheus/prometheus / operations_api | [docs/management_api.md](https://github.com/prometheus/prometheus/blob/bd517f6636ce1b6263dada9dfecb3fe92c84d96f/docs/management_api.md) · `bd517f6636ce` | [Apache-2.0](sources/prometheus-license.txt), [NOTICE](sources/prometheus-notice.txt) |
| psf/requests / readme | [README.md](https://github.com/psf/requests/blob/3c7baaa05ab4aa49cc819ce3a819d260de19c157/README.md) · `3c7baaa05ab4` | [Apache-2.0](sources/requests-license.txt), [NOTICE](sources/requests-notice.txt) |

각 원문·라이선스·해당 NOTICE의 전체 스냅샷과 실제 바이트 SHA-256·Git blob은 sources.json에 기록했다. 고정 commit의 GitHub contents API blob과 대조했다. 원래 저작권·라이선스·고지는 보관하고, 수정 후보는 AI가 만든 평가 자료임을 명시한다. 원격 문서의 현재 최신 동작을 주장하지 않는다. GitHub upstream 식별을 확인했지만 mirror/번역/재게시 계열의 추가 점검은 홀드아웃 관리자가 수행해야 한다.

기존 fixture의 5개 저장소와 LogicWrite를 제외했고 기존 docs/tests/experiments/semantic_pilot에서 네 신규 저장소 URL의 사용 흔적을 검색해 찾지 못했다. 이번에 읽은 원문·파생 후보는 전부 개발용이므로 이후 홀드아웃으로 재분류하지 않는다.

## 검증

기존 Python/jsonschema 환경에서 다음을 실행한다. 기존 입력·답안 스키마의 구조를 별도 파일에 재사용하되 GC ID 패턴을 분리했고 기존 스키마는 수정하지 않았다. validator는 기존 validate_pair와 workflow.assess를 읽기 전용으로 호출한다.

```bash
python3 evaluation/g3_g4/validate.py
python3 -m unittest discover -s evaluation/g3_g4 -p test_validate.py
python3 evaluation/semantic_pilot/validate.py
```

검사는 구조·해시·출처·근거·준비 상태·분리 정책을 확인한다. 잠정 의미 라벨의 정확도나 실제 사람 검수 완료를 인증하지 않는다.

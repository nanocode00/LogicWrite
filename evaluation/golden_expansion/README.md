# Golden Set 확장 — 사용자 판정 대기 17건

GC-001~012 기존 공개 원문 기반 후보와 SP-013~017 신규 통제 합성 파생 사례를 준비했다. **신규 골드 0건, 사용자 판정 대기 17건**이다. 기존 활성 G3 개발용 골드 12건과 검수 이력을 변경하지 않았다. 모든 신규 후보는 development-only/provisional이며 홀드아웃이 아니다.

| 자료 | 용도 |
| --- | --- |
| [REVIEWER.md](REVIEWER.md), `cases/`, `forms/` | 답안을 드러내지 않는 한 건씩의 입력 보기와 빈 사용자 양식 |
| [registry.json](registry.json) | 입력·답안 경로와 SHA-256, 파생 부모·변경 조건·입력 버전 |
| `inputs/SP-013.json`~`SP-017.json`, `answers/` | 신규 입력과 별도 AI 잠정 답안. 사람 정답을 생성하지 않음 |
| [revalidation.json](revalidation.json), [public-source-recheck.json](public-source-recheck.json) | 계약·양쪽 문서 해시·근거 위치 검사와 원격 고정 원문/라이선스/NOTICE 10개 바이트 일치 기록 |
| [gc-independent-ai-review.json](gc-independent-ai-review.json), [sp-independent-ai-review.json](sp-independent-ai-review.json) | 답안을 읽지 않은 별도 AI의 반례 보조 검토. 사용자 판단·정식 최초 판단 후 반례 이벤트가 아님 |
| `prepared/`, [review.py](review.py) | 실제 사용자 이벤트가 하나도 없는 등록형 SP/GC 검수 기록과 CLI |
| [preserved-files.json](preserved-files.json) | 기존 평가 파일 186개 바이트 보존 검사 |
| [rw-future-inventory.json](rw-future-inventory.json) | RW 20건 향후 별도 M0 진단 검수 목록. 이번 SP/GC 과제·점수에 합치지 않음 |
| [VALIDATION.md](VALIDATION.md), [PLAN.md](PLAN.md) | 실행 결과와 범위 |

| 파생 | 부모 | 통제해서 달라진 조건 |
| --- | --- | --- |
| SP-013 | SP-003, SP-011 | 첫 사용 핵심 기능에 캐시가 필수이며 설치 문서에 조건 직접 노출 의무 |
| SP-014 | SP-003, SP-011 | 오프라인 검색은 선택 기능이며 제공된 목적지와 링크 안내로 충분 |
| SP-015 | SP-009 | 목적지 PACKAGING.md 전후 전체와 링크 해소 역할을 합성 제공 |
| SP-016 | SP-010 | 합성 권한자가 지정한 v2와 작성 시점을 계약에 명시. 실제 권한자 승인 기록이 아님 |
| SP-017 | SP-012 | 절단되지 않은 전체 후보를 합성 제공. 원래 절단 결과의 누락 부분을 관측한 것이 아님 |

GC는 네 공개 원문 가족에서 파생한 12건이고 독립 문서 12개가 아니다. 파생 SP도 부모와 상관된 개발용 사례다. 공개 자료의 외부 진실성이나 설치·실행 동작을 평가하지 않는다. 공개 원문의 출처·고정 커밋·라이선스는 기존 `../g3_g4/sources.json`에 유지된다. SP-015 README는 기존 공개 고정 스냅샷이며 새 목적지 문서는 합성이다.

## 입력만 내보내기

```bash
python3 evaluation/golden_expansion/export.py
unzip evaluation/golden_expansion/dist/review-inputs.zip -d /tmp/logicwrite-review-inputs
```

ZIP은 입력 17개·읽기 자료 17개·빈 양식 17개·안내·해시 목록 53개 파일만 포함한다. AI 답안·반례·등록표의 답안 해시는 넣지 않는다. 먼저 이 패키지로 사용자 최초 판단을 받는다. 저장된 별도 AI 사전 검토는 사람 최초 판단을 읽고 반박한 기록이 아니므로 정식 반례 이벤트로 소급하지 않는다.

## 실제 사용자 검수 이어가기

```bash
python3 evaluation/golden_expansion/review.py check evaluation/golden_expansion/prepared/GC-001.workflow.json
python3 evaluation/golden_expansion/review.py append evaluation/golden_expansion/prepared/GC-001.workflow.json --event /tmp/actual-user-initial-event.json --output /tmp/GC-001.initial.workflow.json
```

이벤트 형식은 기존 `../semantic_pilot/user_review_v1/templates/`와 동일하며 case_id와 입력 해시는 현재 입력에 맞춘다. 사용자 최초 판단 → 그 판단에 연결된 별도 AI 반례 검토 → 반론별 사용자 응답·최종 판단·명시적 개발용 포함 승인 순서를 강제한다. 상태 문자열만으로 승격하지 않는다. 기록은 새 파일로만 저장하며 덮어쓰기를 거부한다. 재개방은 적격성을 취소한다. 단일 사용자+AI 보조는 독립 복수 사람 검수가 아니며 Core 전달 승인도 아니다.

기존 SP 전용 도구와 원본 스키마는 그대로 보존했다. 새 등록형 어댑터는 검수 프로토콜을 SP/GC 모두에 적용하되 명시적으로 등록한 17건만 허용한다. 새 계층의 스키마는 기존 이벤트 계약을 복사하고 ID 네임스페이스만 일반화한 고정 사본이며 기존 도구 소비자는 바뀌지 않는다.

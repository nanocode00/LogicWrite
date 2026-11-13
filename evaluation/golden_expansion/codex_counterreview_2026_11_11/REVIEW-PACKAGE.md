# Codex 독립 반례 검토 — 사용자 최종 판단 대기

최초 판단과 Codex AI 반례를 구분한다. AI 권장 판단은 사용자 최종 판단이나 개발용 골드 포함 승인이 아니다. Qwen 결과는 이번 집계에서 제외했다.

| ID | 사용자 최초 판단 | Codex 권장 | 일치 | 반론·정확한 근거·사용자 응답 |
|---|---|---|---|---|
| GC-001 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/GC-001.md) |
| GC-002 | VIOLATION | VIOLATION | 일치 | [사례 검토](cases/GC-002.md) |
| GC-003 | UNRESOLVED | UNRESOLVED | 일치 | [사례 검토](cases/GC-003.md) |
| GC-004 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/GC-004.md) |
| GC-005 | VIOLATION | VIOLATION | 일치 | [사례 검토](cases/GC-005.md) |
| GC-006 | UNRESOLVED | UNRESOLVED | 일치 | [사례 검토](cases/GC-006.md) |
| GC-007 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/GC-007.md) |
| GC-008 | VIOLATION | VIOLATION | 일치 | [사례 검토](cases/GC-008.md) |
| GC-009 | UNRESOLVED | UNRESOLVED | 일치 | [사례 검토](cases/GC-009.md) |
| GC-010 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/GC-010.md) |
| GC-011 | VIOLATION | VIOLATION | 일치 | [사례 검토](cases/GC-011.md) |
| GC-012 | UNRESOLVED | UNRESOLVED | 일치 | [사례 검토](cases/GC-012.md) |
| SP-013 | VIOLATION | VIOLATION | 일치 | [사례 검토](cases/SP-013.md) |
| SP-014 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/SP-014.md) |
| SP-015 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/SP-015.md) |
| SP-016 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/SP-016.md) |
| SP-017 | PRESERVED | PRESERVED | 일치 | [사례 검토](cases/SP-017.md) |

검증 완료 17건 / 검토 실패 0건.

최초 판단과 불일치: 없음

의미 판정 UNRESOLVED와 실행·검증 실패는 구분한다. 실패 재시도 시 원인을 해결하고 새 attempt에 입력 전용 요청만 전달한다. 성공 사례는 재호출하지 않는다.

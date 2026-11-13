# 사용자 최종 검토 대기 패키지

최초 판단은 사용자 메시지의 기록이다. 아래 AI 반례·권장 판단은 독립 로컬 모델의 자문이며 사용자 최종 판단이나 골드 포함 승인이 아니다. 모든 사람 응답란은 미작성이다.

| ID | 최초 판단 | AI 권장 | 일치 | 검증 상태 | 반론·근거 |
|---|---|---|---|---|---|
| GC-001 | PRESERVED | PRESERVED | True | validated | [검토 자료](GC-001/REVIEW.md) |
| GC-002 | VIOLATION | VIOLATION | True | validated | [검토 자료](GC-002/REVIEW.md) |
| GC-003 | UNRESOLVED | UNRESOLVED | 판정 제외 | 실패 | [원시 검토](retry-01/GC-003/REVIEW.md): semantic_inconsistency: recommendation is UNRESOLVED but validity rationale argues PRESERVED; operator audit, no model correction |
| GC-004 | PRESERVED | PRESERVED | True | validated | [검토 자료](GC-004/REVIEW.md) |
| GC-005 | VIOLATION | VIOLATION | True | validated | [검토 자료](GC-005/REVIEW.md) |
| GC-006 | UNRESOLVED | UNRESOLVED | True | validated | [검토 자료](GC-006/REVIEW.md) |
| GC-007 | PRESERVED | PRESERVED | True | validated | [검토 자료](GC-007/REVIEW.md) |
| GC-008 | VIOLATION | VIOLATION | True | validated | [검토 자료](GC-008/REVIEW.md) |
| GC-009 | UNRESOLVED | UNRESOLVED | True | validated | [검토 자료](GC-009/REVIEW.md) |
| GC-010 | PRESERVED | PRESERVED | True | validated | [검토 자료](GC-010/REVIEW.md) |
| GC-011 | VIOLATION | VIOLATION | True | validated | [검토 자료](GC-011/REVIEW.md) |
| GC-012 | UNRESOLVED | UNRESOLVED | True | validated | [검토 자료](retry-01/GC-012/REVIEW.md) |
| SP-013 | VIOLATION | VIOLATION | True | validated | [검토 자료](retry-01/SP-013/REVIEW.md) |
| SP-014 | PRESERVED | PRESERVED | True | validated | [검토 자료](retry-01/SP-014/REVIEW.md) |
| SP-015 | PRESERVED | PRESERVED | True | validated | [검토 자료](SP-015/REVIEW.md) |
| SP-016 | PRESERVED | PRESERVED | True | validated | [검토 자료](SP-016/REVIEW.md) |
| SP-017 | PRESERVED | PRESERVED | True | validated | [검토 자료](SP-017/REVIEW.md) |

품질 주의: GC-002의 AI 반론에는 Python 3.10+ → 3.8+ 변경을 지원 범위 축소로 표현한 오류가 있다. GC-003은 권장 라벨과 타당성 설명이 상충하여 완료 집계에서 제외한다. 원시 응답은 수정하지 않았다.

검증 완료: 16 / 실패: 1

최초 판단과 불일치: 없음

실패는 UNRESOLVED 의미 판정과 별개다. 실패 사례 재시도는 원인(시간 초과·형식·인용·문맥 예산)을 해결한 후 새 attempt 디렉터리에 저장해야 한다. 최초 실패 4건에 한해 형식 지시를 강화한 1회 재시도를 수행했다. 추가 자동 재시도는 없다.

원시 실행 상태와 재검증 상태는 구분한다. 최초 실행의 `/input` 포인터 거부는 검증기 문제이며 원시 응답을 재검증하여 복구했다. 정확한 인용 검증은 의미 판단의 타당성이나 모델의 원격 인증을 보증하지 않는다.

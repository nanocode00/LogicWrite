# HANDOFF — PR #15 이후 Core

**현행화: 2026-11-10. 기준 `main` `c770276`.** PR #1~#15는 병합됐으며 이 문서는 현재 작업 인수인계용이다. 과거 브랜치별 진행 수치를 최신 상태로 혼용하지 않는다. 구현 결과와 최신 회귀 검증은 [현재 실행 인터페이스](../../docs/data-model-and-interfaces.md#current-runtime-interfaces)를 단일 참조로 한다.

## 이어서 읽을 파일

| 목적 | 참조 |
| --- | --- |
| 실행 진입점·승인 경계 | [README](README.md) · [INTEGRATION](INTEGRATION.md) |
| 실제 API/스키마·설계 차이·PR별 근거·검증 명령 | [데이터 모델과 인터페이스](../../docs/data-model-and-interfaces.md#current-runtime-interfaces) |
| 모듈 책임·목표 불변조건 | [아키텍처](../../docs/architecture.md) |
| 다음 작업 우선순위·정식 완료 기준 | [로드맵](../../docs/roadmap.md) |
| RAG·LangGraph 제안 포트 | [별도 과제 설계](../../docs/rag-langgraph-assignment-design.md) |

## 유지할 구현 경계

- `pipeline.py`는 단일 scope 입력·창별 추출 조립·분석 게이트·제한된 추출 재시도를 소유한다. `semantic_validator.py`는 원문↔분석 의미 검토와 내부 실행 증거를 관리한다. supported도 최종 승인이 아니다.
- `organization.py`는 계획·실제 목적지·의존 조건·통합 호환성, `expression.py`/`expression_validator.py`는 발췌 Preview·생성 기록·독립 보호 검사를 소유한다.
- `integration.py` → `reconstruction.py` → `final_validator.py`는 **격리 후보** 경로다. 기존 승인 어댑터를 우회한 단계 실행으로 취급하지 않는다. 상위 FAIL/STOPPED는 중단한다.
- 전체 후보가 존재해도 `delivery_approved: false`다. 최종 구조 검사는 전체 출력의 의미 검토·사람 승인 절차를 대신하지 않으며 최종 PASS 경로는 없다.
- `RevisionController`는 원인 진단·저장된 하위 산출물 무효화·현재 입력 재검증·중단만 제공한다. 실제 자동 수정·재시도·파일 반영은 별도 구현이 필요하다.
- 기본 파일 분석은 원문 블록 목록이다. 다중 scope 자동 분석·의미적 목적지 통합·일반 의미 재구성·RAG·LangGraph는 미구현이다.

## 다음 작업 시작 조건

[로드맵의 우선순위](../../docs/roadmap.md#다음-core-개발-우선순위)에 따라 전체 출력 의미 검토·명시 승인과 독립 평가를 먼저 준비한다. 이후 일반 의미 재구성·자동 수정/재검증·파일 반영 경계를 진행한다. 확장 어댑터는 Core의 검증·승인 권한을 변경하지 않는다.

기존 합성/실제 후보·진단 골드 초안·RW-001 A/B 자료는 잠정/개발 근거 상태를 유지한다. 고정 의미 사례 14건도 독립 홀드아웃으로 재분류하지 않는다. 과거 LLM v2 로컬 기록의 EVAL-14는 별도 평가자 충돌 시나리오이며 전체 14건 일치 주장에 포함할 수 없다. 새 체크아웃에는 ignored `runs/` 기록이 없으므로 코드/고정 사례와 기존 실모델 결과의 재현 가능성을 구분한다.

이번 현행화는 문서만 수정했다. 코드·테스트·평가 데이터·승인 정책은 변경하지 않았고 실모델 평가는 재실행하지 않았다. 최신 회귀 실행 수치와 명령은 위 인터페이스 문서의 검증 절을 따른다.

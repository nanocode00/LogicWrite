# Information Extraction & Analysis A/B Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동일한 RW-001 입력에서 기존 단일 단계와 추출/평가 분리 방식을 실행하고 의미 판단의 차이와 한계를 검토한다.

**Architecture:** 기존 analyze.py는 변경하지 않는다. 새 runner가 A 프롬프트를 재사용하고 B의 단계별 프롬프트와 고정 목록 결합을 담당한다. 기존 출처 검사와 안전한 Markdown 렌더러로 결과를 표시하며 의미적 PASS를 만들지 않는다.

**Tech Stack:** Python 표준 라이브러리, 기존 Antigravity CLI.

**Spec:** [사전 실행 규약](../../../experiments/extraction_ab/protocol.md). 사용자 요청의 범위와 제약을 이 규약에 기록했다.

## 작업

- [x] `experiments/extraction_ab/test_ab.py`: A 프롬프트 동일성, B1의 계약 보류, B2의 계약 포함, ID/해시/고정 목록 보호 및 REVIEW 유지 회귀 테스트를 먼저 작성하고 실패 확인.
- [x] `experiments/extraction_ab/ab.py`: 단계별 프롬프트·출처 검사 어댑터·결합을 구현하고 테스트 통과 확인. B1 검사 어댑터의 중립 평가값은 출처 확인에만 쓰고 모델 결과나 의미 검증으로 보고하지 않는다.
- [x] runner의 외부 호출을 테스트에서 stub으로 대체해 명령 인자, 실패 기록, B1 실패 시 B2 미실행, 기존 출력 덮어쓰기 방지를 확인한다.
- [x] 규약과 코드를 커밋한 뒤 두 반복 실제 모델 실행. 실패도 보존하고 결과에 맞춘 프롬프트 수정/재시도 금지.
- [x] 비교 보고서에 단위·조건·관계·판단 근거와 새 오류/미확정 사항 기록. 실제 실행과 정적 테스트 결과 분리.
- [x] 기존 파일 바이트 보존·회귀 테스트·검토를 마치고 별도 Draft PR 제출. 병합하지 않는다.

## 실행 후 검토 기록

Ruling: 실제 모델 실행은 16b88c1의 runner로 완료했고 프롬프트·규약·호출은 재실행하지 않는다. 이후 추가 코드 검토가 찾은 제공자 실패 응답 digest 연결 버그만 회귀 테스트 2개와 함께 정정한다. 실제 6회 호출은 모두 exit 0이므로 관측 결과에 영향이 없고, manifest에는 실행 당시 코드 digest를 유지한다. 사후 코드와 실행 스냅샷을 혼동하지 않도록 비교 보고서에 명시한다.

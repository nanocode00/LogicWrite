# LogicWrite 선택형 RAG·LangGraph 확장 설계 (과제 트랙)

> 상태: 별도 설계안 (구현·성능 검증 전)  
> 작성일: 2026-11-09  
> 적용 범위: 한국어 기술 문서 / 기존 LogicWrite Core 비변경 원칙  
> 현행화: 2026-11-10, PR #15까지의 Core는 별도 실행 프로토타입이다. 이 확장은 여전히 미구현이다. 실제 API는 [현재 실행 인터페이스](data-model-and-interfaces.md#current-runtime-interfaces), 우선순위는 [로드맵](roadmap.md)을 따른다. Core 코드·평가·승인 정책은 이 설계로 변경하지 않는다.

## 1. 결정 요약

- 과제 조건인 **RAG와 LangGraph 모두 실제 실행 경로에 통합**하되 선택형 확장으로 구현한다.
- **LogicWrite Core가 유일한 판정 소유자**다. 검색 점수 또는 LangGraph 노드가 PASS를 결정하지 않는다.
- **LangGraph**: 구조화된 상태, 단계 라우팅, 재시도·종료, 체크포인트, 검토 보류를 담당한다.
- **RAG**: 프로젝트 내부의 *별도 문서*에서 관련 근거를 검색하고, 모델이 그 근거를 참조하여 수정안/보완안을 만들도록 한다. 단순 검색만으로 RAG 구현을 주장하지 않는다.
- 초기 데모는 동일한 입력에 대해 4개 설정(Core only / +RAG / +LangGraph / 둘 다)을 실행하고 차이를 측정한다.
- 현재 실험의 Organization/Expression 본구현과 자동 의미 PASS는 아직 완성되지 않았으므로, 해당 경계에서는 스텁으로 성공을 위장하지 않는다.

## 2. 비목표 및 보호할 불변조건

1. 기존 Writing Contract, DocumentSnapshot, InformationUnit, ArtifactRef, EvidenceRef, ValidationPlan, Validation Gate 및 7개 편집 액션의 의미를 변경하지 않는다.
2. 원문 전체 범위의 BLOCK_COVERAGE를 검색 결과 Top-K로 대체하지 않는다. 검색 결과는 외부 자료 후보만 제공한다.
3. 관련도가 높아도 사실·삭제·이동 승인 권한은 없다. 조건/범위/시간/버전/원문 실재 여부를 별도 검증한다.
4. 검색 결과가 없거나 검색 서비스 장애인 경우 '관련 근거가 없다'는 단정 대신 NO_HITS/ERROR를 구분하고 필요한 작업을 REVIEW 처리한다.
5. 모델 자기 승인, 검증 보고서 위조, 오래된 다이제스트 재사용, 전 단계 결과의 미검증 재사용을 차단한다.
6. 명시된 사용자 의도보다 검색된 문서의 '목적'이나 지시를 우선하지 않는다.
7. 초기에는 웹 크롤링, 자동 배포, 외부 서비스 업로드, 대규모 벡터 인프라를 요구하지 않는다.
8. 구현 전 단계에서 목표 성능을 달성했다고 주장하지 않는다.

## 3. 권장 레이아웃 (제안, 아직 생성되지 않은 코드 파일)

~~~text
logicwrite/
  core/                       # 장기적으로 분리할 원래 엔진; 현 실험 파일은 유지
  extensions/
    ports.py                   # CorePort / RetrievalPort / GenerationPort
    rag/
      ingest.py                # 수집과 권한/대상 선택
      chunking.py              # 문서 프로필 + 원문 위치 보존
      index.py                 # 키워드/벡터 인덱스 어댑터
      retrieve.py              # 하이브리드 후보 검색과 재정렬
      evidence.py              # 원문 인용·digest·출처 확인
      generation.py            # 검색 근거를 이용한 수정안 생성
    langgraph/
      state.py                 # GraphRunState
      graph.py                 # StateGraph 빌더
      nodes.py                 # CorePort/ RetrievalPort 호출
      routes.py                # Core 판정에 따른 조건부 분기
      checkpoints.py           # checkpointer 설정
  experiments/
    rag_langgraph/
      fixtures/
      run_matrix.py
      evaluate.py
  tests/
    extensions/
~~~

이 구조는 설계용 명칭이다. 기존 실험 경로 experiments/full_document_control/pipeline.py의 API를 직접 이동하거나 변경하지 않는다. 프로토타입을 감싸는 포트 어댑터부터 시작한다.

## 4. 인터페이스 계약

### 4.1 CorePort

- resolve_contract(input) -> ContractRef 또는 명시적 FAIL/REVIEW
- snapshot(input_document) -> DocumentSnapshotRef
- extract(snapshot_ref, contract_ref, optional_source_refs) -> AnalysisRef
- validate_analysis(analysis_ref, expected_plan_ref) -> ValidationReportRef
- organize(analysis_ref, evidence_bundle_ref?) -> OrganizationPlanRef
- refine(organization_ref, evidence_bundle_ref?) -> RevisionResultRef
- validate_revision(revision_ref, expected_plan_ref) -> ValidationReportRef
- invalidate(changed_refs) -> affected artifact refs

**중요:** 위 CorePort는 제안이며 실제 클래스/메서드는 없다. 현재 `generate_organization_plan`, `generate_revision_result`, `validate_final_result`는 각각 제한된 계획/Preview/최종 구조 검증 API다. 이를 승인된 organize/refine/validate_revision 실행으로 매핑하지 않는다. 승인 실행이 없는 경계는 명시적인 NOT_IMPLEMENTED/REVIEW로 표시한다. 임의로 PASS를 출력하는 mock을 데모 성공으로 표시하지 않는다. 단위 테스트에서만 fake를 사용한다.

### 4.2 RetrievalPort

~~~python
class RetrievalPort(Protocol):
    def ingest(self, snapshots: list[DocumentSnapshotRef]) -> IndexManifest: ...
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult: ...
    def verify(self, result: RetrievalResult) -> EvidenceBundle: ...
~~~

RetrievalRequest 최소 항목:
- requesting_run_id, contract_ref, subject_snapshot_ref, query_units
- allowed_document_ids 또는 허가된 저장소 범위
- purpose: contradiction_candidate / move_candidate / supported_addition / duplicate_candidate
- top_k, index_revision, token_budget

RetrievalResult:
- status: OK / PARTIAL / NO_HITS / ERROR
- retrieved_at, retriever_version, index_revision, query_digest
- hits: 각 hit의 document_id, snapshot_digest, source_record, span(start,end), exact_quote, section, score, retrieval_method, rank
- 검색 제외 범위 및 이유, 인덱스의 문서 버전과 입력 문서 버전 불일치 여부

EvidenceBundle:
- 모든 인용이 보존된 원문 스냅샷의 해당 SpanRef와 정확히 일치할 것
- 원문 스냅샷, 계약, 인덱스 버전, 프롬프트 문맥 digest를 참조
- source_material과 같은 수준의 권위로 자동 격상하지 말 것
- EvidenceRef의 kind, authority_basis, uncertainty를 명시
- 검색에 성공했어도 원문 근거가 실제 주장을 지지하는지 별도 판정할 것

### 4.3 GenerationPort

~~~python
class GenerationPort(Protocol):
    def propose(self, task: EditTask, evidence: EvidenceBundle) -> CandidateRevision: ...
~~~

입력은 (a) 현재 문서 원문·Writing Contract, (b) 검색된 원문 인용 및 버전, (c) 편집 목적, (d) 보호 대상 정보 및 범위다.
출력은 CandidateRevision, evidence_hit_ids, changed_spans, retained_requirements, unresolved_claims를 포함한다.

검색 문맥을 **실제 LLM 생성 입력으로 사용**해야 과제 요구의 RAG 수행을 주장할 수 있다. 생성 결과의 citation 문자열만 검사하는 것으로는 충분하지 않으며, 출처가 주장까지 지지하는지 Validation Gate/독립 의미 검토가 확인해야 한다.

## 5. RAG의 구체적인 기능과 경계

### 5.1 범위: '문서 간 정합성/근거 기반 보완' 하나로 좁히기

데모에 사용할 두 가지 업무:
- **RAG-A 모순 후보 탐색**: README의 주장과 설치 안내의 유관 부분을 검색한다. 모델은 대상 주장/근거/조건/버전을 비교해 경고 또는 더 정확한 수정안을 제안한다.
- **RAG-B 근거 기반 ADD**: Writing Contract에 필수로 지정되었으나 현 문서에 없는 조건을 승인된 원자료에서 검색하고 출처를 붙여 보완안을 만든다. 근거를 확보하지 못하면 FLAG/REVIEW.

MOVE/중복 제거는 확장 목표로 남겨도 된다. 첫 과제 데모에서 기능을 과다하게 넓히지 않는다.

### 5.2 인덱싱 단위

1. 문서 단위 프로필: 독자, 목적, 역할, 문서 버전, 인덱싱 시점, 접근 권한
2. 원문 기반 청크: 섹션 제목/상위 문맥 + 문단/표/목록; 원문 span과 digest 고정
3. 가능하면 승인된 InformationUnit 단위 인덱스 추가. 단, 분석에서 재작성한 statement만 저장하여 원문을 잃지 않는다.
4. 검색 단계에서 메타데이터 필터(저장소·권한·버전·역할)를 우선 적용한 뒤 랭킹한다.
5. 후보 확인 단계에서 해당 문서/섹션의 실제 원문을 재조회해 검증한다.

초기 구체 기술:
- 좁은 샘플 코퍼스: SQLite FTS5(BM25 계열 키워드 검색) + 선택적 임베딩 벡터 인덱스
- 실제 과제 시연: 구성 가능한 임베딩 제공자와 영속 벡터 저장소(예: Chroma)를 붙여 dense 검색을 수행; FTS와 합산·재정렬하는 hybrid 방식 비교
- 검색 점수 임계값은 개발 데이터에서 조정하고 별도 홀드아웃 평가에서 검증한다.
- 문서 수가 작으면 전체 관련 섹션 검사와 검색 기반 검사를 비교해 후보 누락률을 드러낸다.

### 5.3 검색 후 생성 예시

~~~text
[Writing Contract] README 독자에게 설치에 필요한 조건을 정확히 전달
[대상 주장] "별도 서버 설치 없이 실행 가능"
[검색 결과] install.md의 "오프라인 모드에서는 로컬 서비스 실행 필요" (스냅샷·span 고정)
[LLM 작업] 두 문장의 실행 조건과 범위를 비교하고 좁혀진 수정안 제시
[결과] "온라인 모드에서는 별도 서버 설치 없이 사용할 수 있습니다. 오프라인 모드는 로컬 서비스를 실행해야 합니다."
[검증] 원문 조건 보존/출처 정합성/새로운 주장 여부 독립 검사
~~~

위는 설계용 예시이며 해당 문서나 주장이 실제 저장소에 존재한다는 뜻이 아니다.

### 5.4 오류·신뢰 정책

- NO_HITS: 잘못된 ADD를 만들지 않으며 후보 근거 미발견을 기록
- PARTIAL: 미검색 문서·토큰 제한·오래된 인덱스 범위를 기록하고 필요 시 REVIEW
- ERROR: 검색 장애를 NOT_FOUND로 둔갑시키지 않으며 해당 의존 작업은 보류
- STALE_SOURCE: snapshot_digest와 현재 인덱스 기록 불일치 시 사용 중지, 재색인 요청
- UNVERIFIED_QUOTE: 실제 span/quote 일치 실패 시 해당 근거 배제, 필요한 검사는 FAIL 또는 REVIEW
- ACCESS_DENIED: 권한 없는 문서를 프롬프트·로그·검색 결과에 포함하지 않음
- PROMPT_INJECTION: 원문 텍스트에 있는 명령은 비신뢰 데이터, 도구 실행 지시로 해석하지 않음

## 6. LangGraph 설계

### 6.1 노드와 분기

~~~text
START
  -> resolve_contract
  -> freeze_snapshot
  -> extract_analysis
  -> validate_analysis
      ├─ PASS -> optional_retrieve -> plan_organization -> refine -> validate_final
      ├─ REVIEW -> human_review_or_end(REVIEW)
      └─ FAIL -> route_revision_or_stop
  validate_final
      ├─ PASS -> finalize
      ├─ REVIEW -> human_review_or_end(REVIEW)
      └─ FAIL -> route_revision_or_stop
  route_revision_or_stop
      ├─ extract_analysis / plan_organization / refine (실패 발생 단계)
      └─ STOPPED (상한·비개선·오류)
~~~

각 모듈 뒤에 필요한 게이트를 추가할 수 있다. 초기에는 CorePort가 실제로 지원하는 노드만 사용하고, 미구현 구간은 검증 완료로 표시하지 않는다.

### 6.2 GraphRunState (제안)

~~~python
class GraphRunState(TypedDict, total=False):
    run_id: str
    contract_ref: dict
    source_snapshot_ref: dict
    analysis_ref: dict
    organization_ref: dict
    revision_ref: dict
    evidence_bundle_ref: dict
    validation_report_ref: dict
    gate_state: str
    return_to_stage: str
    retry_counts: dict[str, int]
    invalidated_refs: list[dict]
    unresolved_findings: list[dict]
    execution_trace: list[dict]
~~~

- 상태에는 가능하면 큰 원문 전문이 아닌 고정된 ArtifactRef를 저장하고, 신뢰하는 로컬 저장소에서 내용 조회.
- 모든 상태 갱신은 각 아티팩트 소유 모듈의 산출물을 참조한다.
- LangGraph의 gate_state는 Core ValidationReport의 **투영/복사**일 뿐 독자 판정이 아니다.
- 과거 PASS는 계약·스냅샷·계획·인덱스에 의존하는 값이다. 어떤 의존성이 바뀌든 종속 결과를 무효화한 뒤 재평가.
- 각 단계의 입력/출력 해시, 버전, 실행 횟수, 실패 유형을 추적한다.
- 실행 단계 내부의 재시도와 전체 수정 루프의 재시도 상한을 혼동하지 않는다.

### 6.3 라우팅 정책

- PASS: 계획된 다음 단계 진행. 단 PASS가 확인된 **해당 경계**만 통과.
- REVIEW: 사람 검토 또는 종료. UI/CLI가 REVIEW를 PASS로 표시하면 안 된다.
- FAIL: 검증 보고서가 지정한 원인 모듈로 복귀. 복귀 단계 하위 아티팩트는 무효화.
- STOPPED: 재시도 제한, 진전 없는 반복, 내부 오류. 미해결 사유와 마지막 검증 결과 유지.
- 검색 실패로 핵심 근거가 없다면 추론으로 채우지 않는다.
- 설정에서 RAG 비활성화 시 retrieve 노드를 건너뛰되 기존 검증은 그대로 수행.
- LangGraph 비활성화 시 기존 실행 제어기를 사용하며 검증 판정은 같아야 한다.

### 6.4 체크포인트와 Human-in-the-loop

- 데모: 메모리 checkpointer, 재개·분기 테스트
- 실제 로컬 실험: 영속 checkpointer와 run_id/thread_id 연결, 실패 복구와 상태 스키마 버전 기록
- REVIEW에서 사람 결정이 필요한 경우 interrupt/resume을 적용할 수 있지만, 불필요하면 명시적 종료로 시작한다.
- interrupt 노드는 재개 시 시작부터 다시 실행될 수 있어 부작용(파일 수정·중복 업로드)이 일어나지 않게 별도 원자 단계/멱등성 키 사용
- 그래프의 조건부 edge와 동적 Command 이동을 같은 노드에 중복 정의하지 않는다.

## 7. 활성화 설정

모드 4개는 동일 입력·고정 버전·모델 설정으로 실행해야 한다.

| 모드 | use_rag | orchestrator | 주요 비교 목적 |
| --- | --- | --- | --- |
| C0 | false | core | 현 품질 제어 기준선 |
| C1 | true | core | 검색 증강이 근거/모순 탐지에 주는 효과 |
| C2 | false | langgraph | 그래프 상태·복구·제어 일관성 |
| C3 | true | langgraph | 통합 실행 안정성과 품질 |

제안 CLI (미구현):

~~~bash
logicwrite evaluate --fixture demo-01 --rag off --orchestrator core
logicwrite evaluate --fixture demo-01 --rag on --orchestrator core
logicwrite evaluate --fixture demo-01 --rag off --orchestrator langgraph
logicwrite evaluate --fixture demo-01 --rag on --orchestrator langgraph
~~~

최종 결과는 모드, 대상 문서와 근거 버전, 모델 설정, 수행된 검색, 호출·토큰·시간, 최종 판정, 미해결 항목을 함께 기록해야 한다.

## 8. 평가 계획

### 8.1 실험 데이터

- 서로 다른 기술 문서 2~5개로 이루어진 작은 프로젝트 3종을 준비한다.
- 예: 명확한 모순 1건, 버전/조건이 다른 겉보기 모순 1건, 필수 안내 누락 1건, 올바른 정보 1건, 근거 없음 1건, 오래된 인덱스 1건, 허위 인용 1건.
- 데이터 원문/계약/정답 기준/출처 스냅샷을 고정하고, 임계값을 조정하는 개발 사례와 독립 평가 사례를 분리한다.
- 기존 LogicWrite의 12개 합성·20개 실제 후보 자료는 새로운 RAG 독립 골드셋이 아니다.

### 8.2 지표

- Retrieval: recall@k / precision@k, MRR(선택), 권한 위반 0건, quote-span 일치율, stale-source 차단율
- Generation: 근거로 지지되는 수정안 비율, 필수 사실·조건 보존율, 근거 없는 ADD 비율, 지나친 주장 범위 확대
- Graph: 경계 우회 0건, 잘못된 PASS 0건, 실패 단계로의 정확한 복귀, 재시도 상한 준수, 재개 시 중복 부작용 0건
- End-to-end: 독자 과업 달성, 모순 탐지 정밀도/재현율, 잘못된 이동·삭제, 최종 REVIEW/STOPPED 분포, 지연·토큰·비용
- 수치 목표는 결과를 본 후 조정하지 않는다. 먼저 평가 기준을 고정한다.

### 8.3 과제에서 보여줄 실질적 사용 증거

1. RAG: 벡터/키워드 검색 로그, 인용 가능한 원문 위치, 검색 근거가 실제 LLM 생성 입력에 들어간 증거, RAG on/off 비교.
2. LangGraph: StateGraph 노드·조건부 edge, 실패→원인 단계 복귀 trace, 횟수 상한, checkpointer 재개 테스트, core 제어기와 결과 대조.
3. 통합: 미확정 근거 또는 의미 검증 미실행 상태에서는 PASS를 만들지 않고 REVIEW로 끝나는 시나리오.
4. 구현되지 않은 경계는 시연 증거로 대체하지 않음.

## 9. 구현 순서와 완료 기준

### X1 — 인터페이스 동결 전 어댑터 실험

- [ ] CorePort 추상 인터페이스와 현재 실험 파이프라인용 어댑터 작성
- [ ] CorePort 호출 결과를 값 객체로 전달하고 gate 판정은 기존 게이트에 위임
- [ ] 선택적 모듈 활성화 구성과 C0/C1/C2/C3 진입점 추가
- [ ] 분석 의미 검증 supported와 최종 출력 의미 검토/승인 미완료의 REVIEW를 구분해 유지
- 완료: 가짜 PASS 없이 C0/C2가 같은 Core 게이트 판정을 재현

### X2 — LangGraph 최소 실제 구현

- [ ] 실제 StateGraph 4개 이상 노드, 조건부 route, bounded retry, 종료 사유 추적
- [ ] checkpoint 저장/재개 및 오래된 상태 무효화
- [ ] 검증 실패·REVIEW·STOPPED 경계 테스트
- 완료: 라우팅과 재시도, 복구 증거가 기록되고 기존 게이트 우회 없음

### X3 — RAG 최소 실제 구현

- [ ] 고정된 다중 Markdown 문서 수집/인덱스; 권한·버전·원문 span 유지
- [ ] 실제 키워드 검색 + 실제 벡터 검색 비교
- [ ] EvidenceBundle의 인용 검증, 인덱스 stale 검출, NO_HITS/ERROR 구분
- [ ] 검색 결과를 생성 모델에 제공하는 RAG 편집 후보 경로
- 완료: 동일 입력에서 검색 문맥이 생성안에 실제로 사용되며 근거 추적 가능

### X4 — 통합 및 평가

- [ ] C0~C3 고정 입력·설정으로 실행하고 결과 기록
- [ ] 4개 핵심 예외: 잘못된 인용, 인덱스 구버전, 모델 자기승인, REVIEW에서 재시도 후 가짜 PASS 방어
- [ ] 프로젝트별 README/시연 안내와 한계 작성
- 완료: 기술 사용 증거·효과·실패 처리·제약을 독립적으로 재현 가능

## 10. 우선 구현 테스트 (최소)

1. core 게이트가 REVIEW를 반환하면 LangGraph 라우터가 다음 편집 단계로 보내지 않는다.
2. core 게이트 결과를 LLM 출력의 PASS 주장으로 덮어쓸 수 없다.
3. 재시도 횟수 한도 및 동일 결함 반복에서 STOPPED.
4. 원문/계약 변경 후 오래된 체크포인트가 후속 단계에 재사용되지 않는다.
5. RAG off이면 검색과 임베딩 제공자가 호출되지 않는다.
6. 검색 결과 quote/span/digest 불일치 시 근거로 쓰지 않는다.
7. 권한 밖 문서가 검색 결과와 모델 입력에 나타나지 않는다.
8. NO_HITS와 ERROR가 구별되고 없는 근거를 만들어 ADD하지 않는다.
9. 타 버전 문서의 겉보기 충돌을 확정 모순으로 처리하지 않는다.
10. 입력의 중요한 주장·조건을 Top-K 검색 범위로 축소하지 않는다.
11. 검색 증강으로 수정한 후보가 독립 검사에서 새 주장 확대를 발견하면 차단한다.
12. checkpoint 재개 시 반복 부작용이나 검증 우회가 없다.
13. 제안 CorePort의 organize/refine 승인 실행은 기존 계획/Preview API와 구별하고 PASS/완료로 위장하지 않는다.
14. C0~C3의 평가 입력·모델·계약·인덱스 버전이 기록된다.

## 11. 위험 및 선결정

- **선결정 A:** 별도 문서가 2개 이상이어야 문서 간 검색을 정직하게 시연할 수 있다. 1개 문서 전체 보존 문제를 RAG로 해결한다고 주장하지 않는다.
- **선결정 B:** RAG 도입 전에 검색 대상의 접근 권한과 최신성의 책임을 정한다.
- **선결정 C:** LangGraph는 실행 흐름 어댑터이며 Core의 gate 규칙을 복제하지 않는다.
- **선결정 D:** 포트·검색·오케스트레이터는 별도 개발하되, 기존 분석 의미 검증만으로 최종 출력 승인이 있다고 간주하지 않는다. 통합 PASS는 전체 의미 검토·명시 승인 경계가 준비될 때까지 보류한다.
- **선결정 E:** 저장소의 조직화·표현 수정은 제한된 계획/Preview 프로토타입이며 승인된 일반 실행이 아니므로, 과제 초기 데모는 *검색 근거 사용 및 그래프 제어의 정직한 부분 시연*으로 범위를 고정한다.

## 12. 참조

- LogicWrite: docs/architecture.md, docs/data-model-and-interfaces.md, docs/evaluation.md, docs/roadmap.md
- Prototype: experiments/full_document_control/README.md
- LangGraph 공식 Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph 공식 interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
- LangGraph 공식 persistence: https://docs.langchain.com/oss/python/langgraph/persistence

> 이 문서는 **과제용 확장 설계**이며, 기존 코어 로드맵의 M0~M4 완료 판정, 기존 평가 자료/스키마, 기존 Semantic Fidelity Validator 코드·평가·승인 정책을 변경하지 않는다.

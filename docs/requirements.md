# Requirements

## 1. Problem and intended users

AI-generated text is often fluent yet inefficient to read. Typical failures include irrelevant detail, missing context, repeated summaries, unjustified claims, contradictory statements, and inconsistent tone.

**Primary users:** developers and AI-agent builders writing Korean README files, PR descriptions, release notes, technical designs, and status reports.

**Primary reader:** the human recipient of each document. The recipient's needs, not the writer's activity log, determine what belongs in the final document.

## 2. Writing Contract

Each evaluation must have a normalized contract, supplied by the caller or explicitly inferred and identified as an assumption:

| Field | Requirement |
| --- | --- |
| `audience` | Intended readers and assumed knowledge |
| `purpose` | What readers should understand, decide, or do |
| `document_type` | README, PR, changelog, guide, design, report, etc. |
| `register` | Target speech level and tone (e.g., Korean 해요체 / 합니다체 / 한다체) |
| `required_information` | Facts, conditions, or decisions that must survive revision |
| `constraints` | Optional terms, structure, privacy, claims, and disclosure rules |
| `source_material` | Optional authoritative source text and provenance |

If the contract is ambiguous, the system should either ask for missing information or label its working assumptions. It must not quietly invent a target reader or authoritative facts.

## 3. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| R1 | Validate contract shape | Missing/invalid required fields produce deterministic diagnostics |
| R2 | Evaluate information boundaries | Each proposed removal or move identifies a text span and audience/purpose rationale |
| R3 | Support edit decisions | Findings use `KEEP`, `COMPRESS`, `MOVE`, `REMOVE`, `ADD`, or `FLAG` |
| R4 | Check style consistency | Target register/terminology violations are reported with spans and exceptions |
| R5 | Check claim consistency | Potentially incompatible assertions reference both spans and their conditions |
| R6 | Avoid false contradictions | Quotations, attributed opinions, time changes, and legitimate exceptions are accounted for |
| R7 | Protect essential information | Revisions are compared with required facts, quantities, qualifiers, citations, and decisions |
| R8 | Return structured findings | Rule, severity, span, evidence, action, confidence/uncertainty, and explanation are available |
| R9 | Enforce revision orchestration | The controller runs validation after each revision, caps attempts, and reports unresolved blockers |
| R10 | Make outcomes auditable | Contract version, validator version, iterations, and change log can be inspected |
| R11 | Provide safe failure behavior | Missing evidence is flagged; the system does not fabricate facts to repair text |
| R12 | Evaluate on held-out cases | Results are compared with human annotations and a prompt-only baseline |

R1 and the deterministic parts of R4/R7 are potential hard gates. R2, R5, and R6 require contextual judgment; their automated output is **not proof of correctness**.

## 4. Severity and disposition

- `ERROR`: confirmed violation of an explicit, machine-verifiable contract or an evidence-backed critical contradiction.
- `WARNING`: plausible issue requiring revision or confirmation.
- `INFO`: optional improvement with low risk.
- `UNRESOLVED`: cannot decide from available evidence; keep visible to the caller.

Disposition is separate from confidence. A high-confidence suggestion to remove a sentence is still a suggestion unless it follows an explicit deterministic rule.

## 5. Non-functional requirements

- **Model-agnostic:** no dependence on a single model or vendor.
- **Reproducible hard checks:** deterministic rules produce stable results for identical inputs/configuration.
- **Traceable:** findings refer to stable document spans and rule IDs.
- **Conservative revision:** preserve meaningful claims unless explicitly authorized to change them.
- **Bounded:** limit rewrite attempts and detect non-improving cycles.
- **Privacy-aware:** do not transmit confidential documents to external model providers without user choice and appropriate controls.
- **Korean-first:** handle Korean register, quotes, and technical terminology; architecture must allow other languages.
- **Human-overridable:** uncertain semantic judgments require review rather than forced correction.

## 6. Out of scope for the first implementation

- Guaranteed factual accuracy or proof of absence of contradictions.
- Reliable identification of whether a human or AI authored a document.
- Automatic publication, GitHub mutation, or uncontrolled document replacement.
- A universal grammar checker, machine translator, or academic peer reviewer.
- Global interception of every ChatGPT/agent answer by a passive plugin.
- Automated high-stakes legal or medical content approval.

## 7. Definition of done for the MVP

An MVP is complete only when it can load a Writing Contract, run at least one deterministic check and one semantic check, emit structured findings with evidence, drive a bounded revision cycle, preserve mandatory information, and report status as `PASS`, `REVIEW`, `FAIL`, or `STOPPED`.

A `PASS` means configured checks found no blocking issue; it is never a guarantee that the text is correct. Evaluation results and failure cases must accompany the MVP.

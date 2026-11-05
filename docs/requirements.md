# Requirements

## 1. Problem and intended users

AI-generated text is often fluent yet inefficient to read. Typical failures include irrelevant detail, misidentified document purpose, missing context, repeated summaries, misplaced cross-document content, unjustified claims, contradictory statements, and inconsistent tone.

**Primary users:** developers and AI-agent builders writing Korean README files, PR descriptions, release notes, technical designs, and status reports.

**Primary reader:** the human recipient of each document. The recipient's needs and the user's intended purpose—not the writer's raw activity log or an inherited template—determine what belongs in the final document and how it is organized.

## 2. Writing Contract

Each evaluation and revision run operates under a shared normalized `Writing Contract`, supplied by the caller or explicitly inferred and labeled as an assumption:

| Field | Requirement |
| --- | --- |
| `audience` | Intended readers and assumed knowledge |
| `purpose` | What readers should understand, decide, or do (reflecting actual user intent) |
| `document_type` | README, PR, changelog, guide, design, report, etc. |
| `register` | Target speech level and tone (e.g., Korean 해요체 / 합니다체 / 한다체) |
| `required_information` | Facts, numbers, conditions, qualifiers, or decisions that must survive revision |
| `constraints` | Optional terms, structure, privacy, claims, and disclosure rules |
| `source_material` | Optional authoritative source text, destination context, and provenance |

### Intent precedence and conflict handling

- **User intent over inferred draft purpose:** Explicit user intent takes precedence over the apparent or historical purpose inferred from an existing draft (for example, when converting a master work log into a focused submission or splitting an overloaded README).
- **Surface conflicts and uncertainty:** If user intent, contract fields, and the existing document's content or source evidence conflict—or if the contract is ambiguous—the system must surface the conflict (`FLAG` / `REVIEW`) and either ask for clarification or label its working assumptions.
- **Evidence-only contract repair:** The system may repair a misidentified contract purpose only from explicit user context or authoritative evidence. It must never silently overwrite user intent or quietly invent a target reader, destination document, or authoritative facts.

## 3. Functional requirements

Architectural module boundaries (`Information Extraction & Analysis`, `Information Organization`, `Expression Refinement`, `Validation Gate`, and `Revision Controller`) are defined in [Architecture](architecture.md).

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| R1 | Validate contract and intent alignment | Missing/invalid required fields produce deterministic diagnostics; conflicts between user intent and inferred draft purpose are surfaced for recovery or clarification without silent overwrite |
| R2 | Extract and evaluate information boundaries | Information units are segmented and assessed for audience/purpose fit and importance; each proposed removal, cross-document move, or intra-document placement identifies text spans and audience/purpose rationale |
| R3 | Support compatible edit decisions across dimensions | Findings emit primary compatibility actions (`KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, `FLAG`) while distinguishing information preservation (`KEEP`), expression edits (`REVISE`, `COMPRESS`), cross-document transfer (`MOVE`), and intra-document ordering (`placement`) |
| R4 | Check expression and style consistency | Target Korean register, terminology, and clarity/compression rules are checked with spans and context exceptions (quotes, code fences, headings) |
| R5 | Check claim, number, and condition consistency | Potentially incompatible assertions or dropped qualifiers across a document or candidate pair reference both spans, quantities, and governing conditions |
| R6 | Avoid false contradictions | Quotations, attributed opinions, time changes, and legitimate scoped exceptions are accounted for |
| R7 | Protect essential information and provenance | Revisions preserve required facts, numbers, qualifiers, citations, decisions, and provenance across both source and destination documents (see [caveat retention rules](architecture.md#caveat-retention-and-exposure)) |
| R8 | Return structured findings | Rule ID, severity, primary action, spans, evidence, confidence/uncertainty, and explanation are available for each module and gate check |
| R9 | Enforce module-routed revision orchestration | The controller routes findings to the responsible module, invalidates and revalidates downstream outputs, validates the entire affected document(s) after each edit, caps attempts, and stops on ambiguity, no progress, or attempt limit |
| R10 | Make outcomes auditable | Contract version, assumptions/intent provenance, validator version, module routing iterations, and change log can be inspected |
| R11 | Provide safe failure behavior | Missing evidence, unverified move destinations, or unresolved purpose conflicts yield `FLAG` / `REVIEW`; the system never fabricates facts or silently deletes valuable out-of-scope context |
| R12 | Evaluate on held-out cases | Module and end-to-end results are compared against human annotations and prompt-only baselines without tuning on held-out items |

The contract-shape part of R1 and deterministic parts of R4 and R7 are potential hard gates. Intent alignment in R1, relevance in R2, and semantic judgments in R5/R6 require contextual review; their automated output—and any future vector-retrieved candidate list—is **not proof of correctness** or authorization to delete content.

## 4. Severity and disposition

- `ERROR`: confirmed violation of an explicit, machine-verifiable contract constraint, dropped protected fact/number, or evidence-backed critical contradiction.
- `WARNING`: plausible semantic, organizational, or stylistic issue requiring revision or confirmation.
- `INFO`: optional expression or ordering improvement with low risk.
- `UNRESOLVED`: cannot decide from available evidence (e.g., conflicting claims, ambiguous contract purpose, or unconfirmed move destination); keep visible to the caller.

Disposition is separate from confidence. A high-confidence model suggestion or high vector similarity score is still a proposal unless backed by an explicit deterministic rule or verified evidence.

## 5. Non-functional requirements

- **Model-agnostic:** no dependence on a single model, embedding provider, or vendor.
- **Reproducible hard checks:** deterministic rules produce stable results for identical inputs and configuration.
- **Traceable:** extracted units and findings refer to stable document spans, content hashes, and rule IDs.
- **Conservative revision:** preserve meaningful claims, numbers, and caveats unless source evidence authorizes change; `KEEP` preserves information without freezing surface wording or position.
- **Bounded and dependency-aware:** limit rewrite attempts, invalidate stale downstream module states after upstream edits, and detect non-improving cycles.
- **Privacy-aware:** do not transmit confidential documents to external model providers without user choice and appropriate controls.
- **Korean-first:** handle Korean register, quotes, and technical terminology; architecture must allow other languages.
- **Human-overridable:** uncertain semantic judgments, unresolved purpose conflicts, and unverified cross-document destinations require human review rather than forced correction.

## 6. Out of scope for the first implementation

- Guaranteed factual accuracy or proof of absence of contradictions.
- Reliable identification of whether a human or AI authored a document.
- Automatic publication, GitHub mutation, automatic creation of new repository files, or uncontrolled document replacement.
- A universal grammar checker, machine translator, or academic peer reviewer.
- Global interception of every ChatGPT/agent answer by a passive plugin.
- Automated high-stakes legal or medical content approval.

## 7. Definition of done for the MVP

An MVP is complete only when it can load a `Writing Contract`, run at least one deterministic check and one semantic check across the modular pipeline, emit structured findings with evidence, drive a bounded revision cycle that revalidates affected documents and protects mandatory information, and report status as `PASS`, `REVIEW`, `FAIL`, or `STOPPED`.

A `PASS` means configured checks found no blocking issue; it is never a guarantee that the text is factually or logically flawless. Evaluation results and failure cases must accompany the MVP.

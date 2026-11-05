# LogicWrite

**Logical Writing for Agents**

LogicWrite is an early-stage, model-agnostic project for reviewing and improving AI-generated writing. Its goal is not simply shorter prose: it is writing that gives the intended reader the right information, in the right place, without unsupported claims or internal contradictions.

> **Status: design and evaluation fixtures only.** There is no working validator, CLI, MCP server, or automatic revision loop yet. Current fixtures consist of 12 synthetic seed cases and 20 provisional real-world candidate records (12 non-`KEEP`, 8 `KEEP`) awaiting independent human review.

## Why?

AI-generated documents can be grammatically correct and still be unhelpful: unnecessary implementation history in a user guide, a draft written for the wrong document purpose, filler in a pull request, inconsistent Korean speech levels, or claims that conflict elsewhere in the same document.

Before polishing sentences, LogicWrite addresses four questions:

1. **Audience & actual intent:** Who will read this, what do they already know, and does the draft match the user's intended purpose?
2. **Information boundary & preservation:** Which information units, claims, numbers, and conditions must be kept, supplemented, moved, removed, or flagged?
3. **Organization & placement:** Which document and section should hold each unit, how should duplicates be consolidated, and what order fits the reader's task?
4. **Expression & consistency:** Are claims, conditions, figures, terms, and target Korean register consistent and clearly expressed?

A long verification record can be good writing; a long installation guide that hides the steps may not be.

## Planned approach

LogicWrite organizes review and revision around **three explicit modules** governed by a shared **Writing Contract**, a **Validation Gate**, and a bounded **Revision Controller**:

```text
Writing Contract (user intent, audience, purpose, register, required facts)
                        |
                        v
     1. Information Extraction & Analysis
        (extract units, analyze claims/conditions/numbers,
         assess audience/purpose fit, recover purpose misidentification)
                        |
                        v
     2. Information Organization
        (cross-document MOVE, duplicate consolidation,
         intra-document grouping & ordering, [future] vector candidate search)
                        |
                        v
     3. Expression Refinement
        (sentence/paragraph rewrite, Korean register & terminology,
         meaning-preserving compression, readability)
                        |
                        v
            Validation Gate
            (module boundaries + whole affected documents)
                  /              \
          PASS / REVIEW         revise
                |                 |
             Result       Revision Controller
                          (route to responsible module,
                           invalidate & revalidate downstream)
```

- **Shared Writing Contract:** Specifies actual user intent, audience, purpose, required information, and constraints. User intent takes precedence over an existing draft's inferred purpose; conflicts or ambiguities are surfaced (`FLAG` / `REVIEW`) rather than silently overwritten.
- **Modular [editorial workflow](docs/architecture.md#editorial-workflow):** Maps the six editorial stages (audience/purpose determination → unit extraction & relevance/importance assessment → action decision → regrouping & duplicate consolidation → ordering & expression refinement → whole-document validation) across the three modules, while enforcing [caveat retention and exposure](docs/architecture.md#caveat-retention-and-exposure) across source and destination documents.
- **[Vector-assisted routing](docs/architecture.md#future-design-vector-assisted-routing):** An unimplemented future design within `Information Organization` for retrieving candidate destinations, overlapping units, and potential contradictions. Similarity retrieves candidates only—it never establishes importance, truth, or deletion authority.
- **Independent gate and controller:** Deterministic checks and model-assisted semantic review inspect module boundaries and complete documents. Unresolved semantic issues or unverified move destinations must not be silently marked as passed.

## Proposed editing actions

LogicWrite separates **information preservation** (`Information Extraction & Analysis`), **document/section placement** (`Information Organization`), and **surface phrasing** (`Expression Refinement`), while retaining seven primary action labels for compatibility across fixtures and reports:

| Action | Meaning |
| --- | --- |
| `KEEP` | Preserve information relevant and important to the document's audience and purpose; does **not** freeze original wording or current position (intra-document section and order are recorded separately as `placement`) |
| `COMPRESS` | Preserve information while condensing verbose or repeated expression without dropping required facts, numbers, or conditions |
| `REVISE` | Preserve information while rewriting sentences/paragraphs or correcting register, terminology, or clarity |
| `MOVE` | Transfer useful information to another document suited to its audience and purpose after reviewing destination context; within-document reordering is `placement`, not `MOVE` |
| `REMOVE` | Information does not help the stated purpose and does not require preservation elsewhere |
| `ADD` | Supplement missing contract-required context, condition, or evidence from authoritative sources |
| `FLAG` | Surface purpose conflicts, unsupported claims, or unverified move destinations that cannot be safely resolved without confirmation |

## Repository

- [Requirements](docs/requirements.md) — Writing Contract precedence rules, functional requirements (`R1`..`R12`), and MVP scope
- [Architecture](docs/architecture.md) — three core modules, module boundaries, six-stage workflow mapping, caveat exposure, and revision controller
- [Data model and interfaces](docs/data-model-and-interfaces.md) — proposed shared types, module contracts, traceability, recovery, and manual candidate walkthroughs; not an adopted fixture schema
- [Roadmap](docs/roadmap.md) — `M0`..`M4` milestones and current status
- [Evaluation plan](docs/evaluation.md) — `B0`/`B1`/`B2` baselines, per-module evaluation checks, and proposed (unadopted) schema extensions
- [Real-world candidates](docs/real-world-candidates.md) — 20 provisional M0 candidate annotations from public repositories (`tests/fixtures/real-world-candidates.json`)
- [Annotated examples](tests/fixtures/README.md) — 12 synthetic seed evaluation cases in `tests/fixtures/cases.json`

## First milestone (`M0`)

Establish a small human-reviewed benchmark before implementing a validator. Both the synthetic cases in `tests/fixtures/cases.json` and the 20 provisional real-world candidates in `tests/fixtures/real-world-candidates.json` describe expected judgments—**they are not completed human-verified gold data, baseline runs, or evidence of model accuracy**.

The initial priority is Korean technical writing (README files, pull requests, release notes, design documents, and work reports), while keeping the contract and finding format usable across languages.

## Longer-term applicability

The first target is durable technical documentation. A [future direction](docs/roadmap.md#long-term-direction--conversational-agent-responses) is to reuse the three-module engine for **agent conversational responses**, where selecting what to say, grouping it within a reply, and matching the requested detail level matter as much as document structure. This is a design goal, **not an implemented response interceptor or a current MVP requirement**.

## Inspirations

- [Yoonmoon](https://github.com/amondnet/yoonmoon) — staged Korean proofreading, humanization, tone conversion, and re-diagnosis
- [Humanizer KO](https://github.com/nyjin/humanizer-ko) — document → paragraph → sentence review

LogicWrite does not bundle or claim ownership of these projects. Its intended distinction is explicit audience/purpose contracts, modular extraction/organization/refinement boundaries, cross-document claim and caveat checks, and independently controlled validation loops.

## License

MIT. See [LICENSE](LICENSE).

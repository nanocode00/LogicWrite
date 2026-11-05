# LogicWrite

**Logical Writing for Agents**

LogicWrite is an early-stage, model-agnostic project for reviewing and improving AI-generated writing. Its goal is not simply shorter prose: it is writing that gives the intended reader the right information, in the right place, without unsupported claims or internal contradictions.

> **Status: design and evaluation fixtures only.** There is no working validator, CLI, MCP server, or automatic revision loop yet.

## Why?

AI-generated documents can be grammatically correct and still be unhelpful: unnecessary implementation history in a user guide, filler in a pull request, inconsistent Korean speech levels, or claims that conflict elsewhere in the same document.

We want to answer four questions before polishing sentences:

1. **Audience:** Who will read this, and what do they already know?
2. **Purpose:** What should the reader understand, decide, or do?
3. **Information boundary:** Should each piece of information be kept, condensed, moved, removed, or supplemented?
4. **Consistency:** Do the document's claims, conditions, figures, terms, and tone agree?

A long verification record can be good writing; a long installation guide that hides the steps may not be.

## Planned approach

```text
Writing Contract (audience, purpose, register, required facts)
                        |
                  Draft / Input
                        |
              Validation Engine
         +--------------+--------------+
         |                             |
   Deterministic checks         Semantic review
   schema, required fields,     relevance, scope,
   patterns, terminology        contradictions, gaps
         +--------------+--------------+
                        |
                 Validation Gate
                   /          \
             pass / review     revise
                  |              |
              Result       targeted revision
                                 |
                           re-validation
```

The contract, findings, and revision limits will be explicit. A controller—not an instruction asking the writer to remember—must enforce validation when strict execution is required.

**Important limitation:** deterministic checks can enforce shapes and explicit constraints, not prove that a document has no factual or logical errors. Semantic findings will carry evidence and uncertainty; unresolved issues must not be silently marked as passed.

## Proposed editing actions

| Action | Meaning |
| --- | --- |
| `KEEP` | Necessary and well-placed information |
| `COMPRESS` | Useful idea, needlessly verbose or repeated |
| `REVISE` | Preserve information while correcting wording, register, or terminology |
| `MOVE` | Useful content, wrong audience or location |
| `REMOVE` | Does not help the stated purpose |
| `ADD` | Missing required context, condition, or evidence |
| `FLAG` | Cannot safely resolve without confirmation |

The aim is **information usefulness**, not a fixed word-count reduction.

## Repository

- [Requirements](docs/requirements.md) — scope, acceptance criteria, and non-goals
- [Architecture](docs/architecture.md) — contract, checks, gate, and revision controller
- [Roadmap](docs/roadmap.md) — milestones and exit criteria
- [Evaluation plan](docs/evaluation.md) — baselines, metrics, and review protocol
- [Annotated examples](tests/fixtures/README.md) — synthetic evaluation cases in `cases.json`

## First milestone

Establish a small human-reviewed benchmark before implementing a validator. The current fixtures describe expected findings; **they are examples, not evidence of model accuracy or passing tests**.

The initial priority is Korean technical writing (README files, pull requests, release notes, design documents, and work reports). The contract and finding format should remain usable with other languages.

## Inspirations

- [Yoonmoon](https://github.com/amondnet/yoonmoon) — staged Korean proofreading, humanization, tone conversion, and re-diagnosis
- [Humanizer KO](https://github.com/nyjin/humanizer-ko) — document → paragraph → sentence review

LogicWrite does not bundle or claim ownership of these projects. Its intended distinction is explicit audience/purpose constraints, information-boundary decisions, cross-document claim checks, and independently controlled validation loops.

## License

MIT. See [LICENSE](LICENSE).

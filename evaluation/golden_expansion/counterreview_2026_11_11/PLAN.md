# Independent counterreview execution plan

Goal: preserve 17 user initial judgments and obtain advisory refutations without human final decisions or gold activation.

- [x] Inspect latest origin/main, reviewer rules and failed temporary attempts.
- [x] Create separate branch; preserve prior failure bytes.
- [x] Record verbatim initial judgments linked to raw input SHA-256.
- [x] Execute stateless local requests with complete input only; retain exact requests/responses and timings.
- [x] Validate identity, labels, completion, context budget, JSON pointers and exact quotes; report failures separately.
- [x] Produce comparison and per-argument human response forms with final judgment and approval unset.
- [x] Verify original tracked files unchanged; run full regression suite; commit and open review PR without merging.

No answers, previous AI reviews, or development gold are loaded by the runner or supplied to the reviewer. Hashes bind locally observed artifacts; they are not remote model attestation. At most one automatic request per case; saved attempts are never overwritten.

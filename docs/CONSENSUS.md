# SemanticEscrow independent consensus and evidence policy (design)

## Verdict separation

- **Protocol**: selected validator committee accepts/rejects leader's execution using the contract's Equivalence Principle; `Accepted/Finalized` must be paired with `FINISHED_WITH_RETURN` to claim successful transaction execution.
- **Application**: `APPROVED`, `REJECTED`, `INCONCLUSIVE` on seller deliverable; `UNAVAILABLE` is a transient failure that must not alter decision state.
- **Payout**: queued GenLayer EVM-layer message after protocol finalization; not the same as funds received.

No hardcoded promise of 5/5 unanimity; Studio has configurable validator set, and protocol majority is separate from `min_valid_sources` used for evidence coverage.

## Evidence manifest (frozen input)

JSON canonicalization with duplicate-key rejection; 2–5 entries, HTTPS only, distinct normalized hostnames, lowercase SHA-256 of **raw response bytes**, each body <=6000 bytes, bounded total prompt, no usernames/passwords in URLs, no redirects, no private network destinations, no URL fragments or custom ports. Reject malformed Unicode and embedded controls. Manifest digest immutable once submitted; supplemental challenge manifest may only add new digests, cannot alter acceptance criteria. Hashes prove exact bytes matched a commitment **not truth, ownership, independence, freshness or absence of prompt injection**. Source ownership and DNS enforcement remain explicitly open deployment gates.

## Candidate decision schema

Strict JSON; exact required keys `outcome`, `rubric_results`, `verified_source_hashes`, `reason_code`. `outcome` is one of `APPROVED|REJECTED|INCONCLUSIVE`; rubric results are bounded ordered `PASS|FAIL|UNKNOWN` indexed to the 1–8 frozen structured `criteria_items` with unique item IDs; at least one is mandatory; hashes must match verified manifest entries; `reason_code` from a closed allowlist. Reject duplicate JSON keys, undefined fields, length overflow, Unicode control characters, confidence-only justifications, or unsupported result types.

Rules: positive `APPROVED` requires every mandatory rubric item PASS, >=2 valid independent-fetch/digest-matching sources and no contradictory mandatory observation. `REJECTED` requires >=2 verified sources and at least one substantiated mandatory FAIL; otherwise `INCONCLUSIVE`. Additional corroboration is not equivalent to separate independent publishers. A source with bytes mismatch is INVALID and cannot count, and the required minimum has not been met. On transient access problems before minimum evidence, classify UNAVAILABLE and return without writing the business outcome.

## Leader / validator

In `gl.vm.run_nondet_unsafe(leader_fn,validator_fn)`: leader fetches sources, validates bytes, runs bounded rubric classification, proposes normalized fields. Validator independently refetches and rehashes committed bytes, independently re-derives ordered rubric outcomes and checks strict identity of `outcome`, `rubric_results`, `verified_source_hashes` and `reason_code` (ignores prose explanation). Validator must check `gl.vm.Return` type; reject `UserError`/`VMError`, malformed payloads and any mismatch. False/disagreement must not fall back to approving leader fields. No nondeterministic function is allowed to mutate storage or queue GEN value messages.

Deterministic code stores **only** the accepted validated verdict and immutable evidence pointer. A lack of validator agreement means state does not change, and later calls can retry within the fixed review deadline. LLM semantic equivalence is not formal truth; prompt-injection, hallucinations, untrustworthy source ownership, dynamic sources and model/provider failure remain risks.

## Challenge re-evaluation

Initial verdict is append-only. Challenge adds supplemental evidence (>=1 unique new content hash) and an immutable note; validator re-evaluates *original + supplemental* against the unchanged rubric, applying the same hard source checks and typed output schema. Only one challenge; no buyer-controlled veto overriding source-qualified approval without independently validated rejection. Inconclusive challenge expiry falls back to the first qualified verdict.

See [security boundaries](SECURITY.md) and official [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle).

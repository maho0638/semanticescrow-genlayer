# SemanticEscrow — PHASE 5 dispute and appeal security

**Status (2026-10-15): 63/63 Direct Mode tests + GenVM lint 3/3 VERIFIED. Real five-validator local Studio challenge-reversal integration is being checked separately. This report is not a production-safety certification.**

## Exact verifiable evidence

- GitHub branch: https://github.com/maho0638/semanticescrow-genlayer/tree/audit/phase5-dispute-appeal-20261015
- Complete financial + challenge regression: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38705016435 (**SUCCESS**, 63 passed, 0 failed, lint 3/3, model consistency 18,203 assertions).
- Local five-validator challenge test: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38704521813 (must inspect final result before claiming success).
- Prior tested genuine local consensus and payout/refund intents: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38700525100 (5 validator identities; 3 agree / 2 idle; **not** unanimous).

## Stage-5 engineering

1. **Losing-party rights:** buyer alone may challenge an approved milestone, seller alone may challenge a rejected milestone, before 48h deadline; unrelated addresses cannot challenge or reassess. At most one contract challenge per milestone.
2. **Source-quota deadlock fixed:** seller may use all 5 initial evidence sources; challenger can still add **1–2 new unique host + SHA-256 commitments**; combined review maximum is 7. Previous code incorrectly allowed zero supplemental sources when the original submission had 5.
3. **Fake-evidence reversal fixed:** a new source commitment alone cannot reverse a verdict. One of the supplemental sources must actually hash-verify independently during the second consensus round. Without verified new evidence, verdict remains `CHALLENGED`; transient unavailable supplemental evidence raises a retryable error; permanent mismatch generates an `INCONCLUSIVE` observation and original verdict remains unchanged.
4. **Immutable assessment trail:** initial `APPROVED`/`REJECTED` snapshot remains on-chain; review records a separate round. No change of frozen rubric, milestone amounts, beneficiaries, deadline or original evidence. Challenging party's explanatory note is SHA-256 committed, not stored as raw arbitrary text.
5. **Time and fail-safe semantics:** no challenge at exact 48h cutoff, no second review at exact 7d cutoff. If challenge cannot reach a qualified second verdict by the fixed deadline, `settle` follows the **original** first decision by the agreed ex-ante timeout rule. This is a fairness/availability trade-off, not proof that original outcome is correct.
6. **Money safety:** first approval alone queues no payout until window expires; second rejection leads only to buyer refund of all still locked funds, second approval queues only current milestone payout; no double settlement; aggregate `total_locked` remains consistent after appeal settlement.
7. **Mutual cancellation** remains a two-party signature handshake and does not pause challenge expiry; no extension/replay once queued.
8. **Validator robustness:** leader and validators independently fetch committed source bytes and classify against frozen rubric using the pinned `gl.vm.run_nondet` interface. Validation failure does not force arbitrary `APPROVED`.

## Stage-5 executed Direct Mode regression paths (24 new tests)

- Buyer approval→challenge→rejection→refund, seller rejection→challenge→approval→payout.
- Both losing-party permissions and attackers' failures.
- 48h challenge boundary before/exact; 7-day second-review boundary and original fallback for each first verdict.
- Replay, duplicate hostname/content hash, 512-byte justification bounds, original 5-source + supplemental 2-source success, max 2 supplemental limit.
- INCONCLUSIVE, unavailable/mismatched supplemental evidence; no verified new evidence cannot reverse.
- Unauthorized reassessment; second-appeal prevention; mutual cancellation versus challenge; terminal stage cannot reopen; pending cancellation cannot pause expiry.
- All 7 initial+supplemental sources hash-verified end-to-end, full ledger conservation and pending no-transfer checks.

## Contract-level challenges ARE NOT protocol validator appeals

The application `challenge()` is a GenVM transaction after the first application verdict. It is **distinct** from the protocol's pre-finalization validator appeal to a fresh committee, which uses the protocol's appeal charge, committee selection and lifecycle. This primitive does not replace or demonstrate the protocol's bond-based appeal API. See official docs: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/appeal-process and https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality.

## Remaining limitations / release blockers

- Passing local SDK and test harness evidence does NOT show public network appeal, real EVM receiver credit, transfer-failure remediation, deterministic source publisher authenticity, DNS/redirect safety, or professional audit. Mocked web and LLM data do not prove real-world truth.
- Model consensus compares independently re-derived structured fields; stochastic model disagreements can cause failure/retries. Unavailable independent evidence may prevent the losing party from changing an earlier ruling. The seven-day fallback retains original verdict by design.
- Never assert financially production-safe, zero-defect, or 100% reliability without proof. Do not risk user funds.

## User-requested stop boundary

Stage 5 only. Do not initiate Stage 6, hosted/public deployment, GitHub `main` merge, Portal submission, or real GEN transactions as part of this audit.

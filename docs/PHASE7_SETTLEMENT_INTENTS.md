# SemanticEscrow — Phase 7 settlement-intent audit interface (2026-10-15)

## Status and original-scope warning

This is a **scoped technical implementation** of an unresolved transfer-accountability risk after Phase 6. The original nine-stage plan's exact Phase 7 heading and acceptance checklist were **not preserved in the handoff**. Do not assert that this work satisfies every requirement of that missing plan. Mark COMPLETE only for the local checks when their CI runs pass.

## Change

- New read-only `get_transfer_intents(deal_id)` and `get_transfer_intent(deal_id, milestone_index)`.
- Every queued payout/refund can be reconciled against frozen parties, amount, milestone index, original terms hash, and a domain-separated SHA-256 intent identifier.
- Aggregate amounts are cross-checked against the original `payout_queued_total` and `refund_queued_total`, with a fail-closed error on inconsistency.
- A refund after one or more payouts is represented as a single remaining locked amount assigned to the active failed/cancelled milestone. Later cancelled milestones are not duplicated as transfer messages.
- No additional state-mutating, payable, admin, rescue, retry, or credit-confirmation method was added. Existing settlement emissions and economic outcomes stay unchanged.
- The exact `status` string is `QUEUED_UNVERIFIED` for all intents. This state is **never** a blockchain payment receipt. Intent IDs are commitments to contract terms, *not* child transaction hashes.

## Local verification

Workflow: `.github/workflows/phase7-intents.yml` (full Phase 2–6 Direct Mode regression, new Stage 7 checks, pinned GenVM lint, Phase 1 invariants).

Studio: `.github/workflows/phase7-studio.yml` (five locally registered validator identities; mocked source/LLM; the source-tampering and expiry-refund scenario now also checks actual post-finality read-only intent output).

**Verified Phase-7 immutable tested commit:** `bb9df849b12f2eb646fc9cb73bf7f360831af68e`.

- Full regression: **153/153 pytest PASS** (142 historical + 11 new), **3/3 GenVM lint PASS**, Phase 1 static invariants **18,203** and abstract ledger scenarios **2,000**: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38713765216 — completed SUCCESS.
- Real pinned Studio local five-validator run: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38713765220 — completed SUCCESS. Chain 61127, five registered local validator identities, CREATE/SUBMIT/ASSESS/REFUND each 3 `agree` + 2 `idle`; `idle` is not agreement. Altered source remained inconclusive; no seller payout. The timeout refund (25 simulated wei) emitted one read-only `QUEUED_UNVERIFIED` intent to buyer. Studio checkpoint `STUDIO_QUEUED_REFUND_INTENT_READBACK_PASS` recorded; test error classes empty, 6 FINALIZED database transactions including child/system operations.
- The full post-test direct and Studio checks ran on the **same contract blob** at the tested commit; any later updates to documents alone are not new contract execution evidence.
- This is a local, controlled/mock-source and mock-LLM test. There is no EVM Ghost-layer recipient credit proof.

## Production release blockers — intentionally unresolved

**A**. DNS resolution, redirect chains, egress private IP restrictions, remote source ownership and real prompt-injection resilience are not demonstrated by the local mocks.

**B**. GenLayer native value-bearing child messages are asynchronous; on failure the value is not automatically returned. A parent FINALIZED, a stored intent, or `total_locked=0` does **not** prove beneficiary EVM credit. Child receipts, Ghost-level transaction status and balance effects need read-only cross-chain reconciliation with trusted RPC endpoints.

**C**. No safe retry or failed-transfer recovery mechanism is established. An unverified retry might double-pay. Do not add one without protocol proof and adversarial tests.

**D**. No public chain, actual independent model provider, independent external security audit or real GEN spend was performed. The contract is **PRE-RELEASE / NOT SAFE TO FUND**.

Docs: https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers and https://docs.genlayer.com/developers/intelligent-contracts/features/messages.

## Stop point

Code and tests can be concluded for **this limited, local Phase-7 evidence interface** only. The withheld real-funds authorization, original missing Stage 7 specification and external delivery-safety gates remain open. Never claim a live payment has reached the recipient merely from the presence of a row.

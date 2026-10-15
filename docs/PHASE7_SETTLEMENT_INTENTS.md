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

## 15 Oct 2026 — Actual Bradbury public RPC execution attempt (after user test-GEN approval)

The user explicitly approved spending **free test GEN** from an independently generated ephemeral wallet, without disclosing or committing mnemonic/private key material. The intended integration test was to deploy SemanticEscrow on Bradbury, fund a deal, mutually cancel with a separate signer, and independently confirm beneficiary EVM balance credit. The entire test harness was isolated on `test/phase7-bradbury-ephemeral-20261015`, not `main`.

- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38740606209> — **FAIL (transport blocker, not contract execution failure)**: Bradbury RPC returned HTTP 403 during the preflight `eth_chainId`, before the ephemeral wallet was created. No test GEN was funded, spent, or stranded.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38740830771> — **SUCCESS as diagnostic** from Ubuntu: 2/2 `rpc-bradbury.genlayer.com` requests HTTP 403; 2/2 `rpc-asimov.genlayer.com` requests HTTP 403; the separate official `rpc.testnet-chain.genlayer.com` returned HTTP 200 with chain ID 4221 on both attempts.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38741064285> — **SUCCESS as diagnostic** from macOS with identical results: GenLayer-specific RPCs HTTP 403; underlying L2 chain RPC HTTP 200, chain ID 4221.

The GenLayer-specific JSON-RPC is needed for deploying/calling the Intelligent Contract and reading `gen_*` consensus status. Standard `eth_*` L2 access is insufficient to certify a GenVM/Ghost payout or child transfer recovery. HTTP 403 must not be circumvented by routing secret signing keys through unverified proxies.

**Phase 7 remains locally verified only**, with 153 Direct Mode PASS + local Studio five-validator PASS; Bradbury end-to-end EVM credit and child-message failure recovery remain **NOT VERIFIED**. Do not mark fully completed or ready for live escrow money.

**Wallet safety:** The wallet-generation path was not reached on the failing run, so no fundable public address with a currently retained key exists. Never ask the user to send test GEN to previously expired ephemeral wallet addresses. A fresh wallet address may be shared ONLY after a confirmed-access session has successfully started and its key remains available to the signing process. No main branch, Portal, PR, merge, or production deployment was affected.

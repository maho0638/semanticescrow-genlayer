# SemanticEscrow — Phase 4 financial safety verification (2026-10-15)

**Status:** Direct Mode and lint verified; real five-validator payout/refund settlement integration **IN PROGRESS**. This report intentionally does not claim that recipient GEN credit, failed external transfers, or production fund security have been verified.

## Branch, test baseline and provenance

- Repository: https://github.com/maho0638/semanticescrow-genlayer
- Isolated branch: `audit/phase4-payment-refund-safety-20261015` — no merge into `main`.
- Financial safety CI: **39 PASS, 0 failed**, GenVM lint **3 PASS**, architecture static model **18,203 assertions / 2,000 abstract scenarios**: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38698597328.
- Prior **real local 5-validator** positive assessment at Phase 3: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38666863852 (3/5 agree, 2 idle; finalized state readback).
- Current five-validator money-settlement CI: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38697966876 — **result must be read and added before marking Phase 4 Studio evidence PASS**.
- Python 3.12, pinned `genvm-linter==0.11.0`, `genlayer-test==0.30.0rc2`, mocked/local GEN only.

## New stage-4 implementation (read actual source)

- Add persistent `total_locked: u256` (the sum of all currently unqueued per-deal GEN obligations).
- On payable `create_deal`: reject aggregate overflow; increase `total_locked` once, with immutable per-deal beneficiary addresses.
- On `_queue_settlement`: reject zero/over-locked emission; decrement global and per-deal obligations exactly once and record immutable stage intent **before** emission, on protocol finality only.
- `get_total_locked()` publicly exposes unqueued GEN liability, NOT current EVM beneficiary credit.
- `__receive__` explicitly rejects accidental direct native GEN transfers; EVM forced transfers cannot be prevented by a Python method.

## Verified financial and authorization regression classes

Tests under `tests/test_phase4_payment.py` supplement original 23 contract tests:
- Empty contract, multiple independent deals, exact deposit, unique buyer nonce scoped to buyer.
- Single approved milestone payout intent followed by all remaining locked milestone refund; cross-deal aggregate conservation.
- Initial rejection refunds all unqueued milestones, with no clawback of already queued payouts.
- Permissionless expiration after objective delivery/review deadlines, even if payer/seller are unresponsive.
- Cannot cancel without both parties, no use of expired mutual-cancel signature, attacker cannot force premature settle or change recipient.
- Duplicate settle, double refund/payout, replay and state reopening fail.
- Zero, noncanonical, negative and overflow amounts fail before changing liabilities.
- Direct value-only send rejects accidental deposit.
- `remaining_locked + total_payout_queued + total_refund_queued == initial_deposit` on every modeled deal; global `total_locked` equals sum of all deals' remaining obligations.

## Financial safety limitations — do not erase or misrepresent

The contract queues EVM external GEN transfers on protocol finalization. A `FINALIZED` parent, `PAYOUT_QUEUED`, or `REFUND_QUEUED` is **not an independently verified EVM recipient credit**. Live ghost-contract `handleOp()`, actual downstream receipt status, fee sufficiency, reverting receivers, and any failed-message recovery path have **not been proved**.

GenLayer's official docs say failed value-bearing child transactions **do not automatically return GEN** to the sender. Consequently the design deliberately **does not blindly retry** a queued outgoing transfer (which can introduce double-payment risk). However **funds can remain unrecoverable if a downstream transfer fails**, and the implementation does not offer a verified safe remediation path. This is an explicit **production-release blocker**, not a resolved zero-risk feature.

URLs and source ownership, real publisher independence, DNS/redirect/SRRF egress checks, LLM correctness, chain-level transfer fees, and the hosted network are separate release gates. Studio does not reproduce the real EVM ghost layer. Neither passing 39 local tests nor local Studio can certify a financially safe production escrow.

## User instruction boundary

**This is Stage 4 only.** No new Stage-5 dispute design, Portal resubmission, merge into GitHub `main`, real GEN spending, external deploy, or user wallet operations. Final Studio results must be recorded honestly before closing stage 4.

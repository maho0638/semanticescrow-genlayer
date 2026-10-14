# SemanticEscrow Architecture v1 — 2026-10-15

## Scope and non-goals

Standalone, reusable GenLayer Python GenVM Intelligent Contract (not a full frontend app). Handles up to **5 pre-funded sequential milestones** for each independent deal. A buyer and seller consent to a plain-language but testable acceptance rubric at creation; evidence is verified by GenLayer consensus; settlement emits native GEN transfers. Multiple deals are independent, each with a unique ID. No external arbitrator, off-chain oracle trust, tokens other than native GEN, fees, admin upgrade bypass, court-grade arbitration, or guarantee that retrieved text is truthful.

## Roles and identity

- **buyer**: transaction sender funding the deal; refund beneficiary is frozen to buyer address. Can challenge approval, propose/confirm mutual cancellation, and trigger deterministic settlement.
- **seller**: immutable nonzero address different from buyer; payout beneficiary frozen to seller address. Solely submits initial evidence and challenges rejection; can trigger assessment, cancellation, and settlement.
- **anyone**: may trigger deterministic expiry/settlement after prerequisites to prevent a single party blocking progress; cannot redirect funds or modify criteria.
- **leader/validators**: GenLayer protocol roles. They derive a candidate decision and independently verify from the committed evidence. They cannot replace buyer/seller permissions.
- **no privileged owner/admin**: no method to sweep, overwrite verdicts, or edit recipient addresses. Protocol-level appeal is distinct from this contract's challenge.

Do not authorize using `origin_address` for privileged actions. Compare immediate `gl.message.sender_address` to frozen role addresses; document trusted smart-account policy explicitly if later supported.

## Creation and immutable terms

`create_deal(seller, milestones_json, buyer_nonce)` is payable: `gl.message.value` **must exactly equal** the checked sum of 1–5 positive `u256` milestone amounts. Reject zero/duplicate seller, same buyer/seller, duplicate `(buyer,buyer_nonce)`, invalid JSON, unbounded amounts, invalid deadlines and malformed acceptance rubrics. `deal_id` is monotonic and `(buyer,buyer_nonce)` prevents application-level replay. A failed transaction must not write state.

Each milestone stores frozen: `amount_wei`, canonical `criteria_items` array (1–8 items, each 1–512 UTF-8 bytes, stable ordered IDs and explicit `mandatory` booleans), bounded human-readable `criteria_text` (max 2048 UTF-8 bytes), `criteria_sha256` over the canonical rubric bytes, UTC `delivery_due_at`, `min_valid_sources=2`, `allowed_evidence_policy` (HTTPS, raw bytes hashes, no redirects/private IP targets). Deadlines must strictly increase, be at least 1 day ahead of deal creation and no more than 365 days ahead. Reject duplicate rubric item IDs, empty mandatory set, malformed boolean flags and nondeterministic JSON; at least one item is mandatory. No add/edit/remove after creation. Terms are consented via funding and the seller's choice to participate, **not cryptographic bilateral signature at creation**; seller may decline to work. Support explicit seller acknowledgment as a future option only if needed.

One active milestone at a time; the next becomes active **after settlement is queued** for the previous one. This is not proof the previous recipient actually received GEN: consumers must reconcile chain-layer message execution. If a milestone fails, refund its amount **and all later locked milestones** and terminate the deal. Already queued payouts are immutable and never clawed back.

## Evidence and decision

Only seller may submit the initial manifest once per active milestone, strictly before `delivery_due_at + 48h`. Submitter commits 2–5 normalized distinct HTTPS hostnames, each with the raw response-body SHA-256 (64 lowercase hex), a bounded content size (up to 6000 bytes), optionally a short declared evidence role, and manifest digest. Inputs are bounded. No direct user-supplied prompt instructions are executed. Review expires 7 days after submission.

`assess(deal_id)` operates only in `SUBMITTED` before review expiry. Leader and validators independently fetch and hash exactly the response bytes, evaluate frozen rubric and emit strictly typed outcome `APPROVED`, `REJECTED`, or `INCONCLUSIVE`. Require minimum two valid verified distinct-host sources, but distinct hostnames do **not** prove distinct publishers. `UNAVAILABLE` denotes transient failure and leaves state unchanged (not a business rejection). `INCONCLUSIVE` is a valid but insufficient/contradictory result: stage-1 policy deliberately **does not release money** and retains `SUBMITTED` until review expiry, when it refunds outstanding escrow.

An approved assessment enters `APPROVE_PENDING`, rejected enters `REJECT_PENDING`; both record an immutable decision snapshot and a 48h contract challenge window. `INCONCLUSIVE` is an append-only assessment observation, not a final payment verdict. Refund on objective expiry is a pre-agreed risk allocation, **not proof the seller failed to deliver**.

## Challenges, deadlines and settlement

- During `APPROVE_PENDING`, only buyer may challenge; during `REJECT_PENDING`, only seller may challenge. At most **one** contract challenge per milestone. Challenger commits supplemental manifest containing at least one new verified SHA-256 fingerprint and a bounded justification; frozen rubric does not change.
- Challenged stage `CHALLENGED` can be independently reassessed within 7 days. New `APPROVED`/`REJECTED` result becomes `CHALLENGE_APPROVE_PENDING`/`CHALLENGE_REJECT_PENDING`; `INCONCLUSIVE` or transient unavailability leaves challenged state until expiry. The original decision and challenge record remain append-only.
- If challenge assessment times out, settlement follows the **initial verdict** rather than allowing a baseless challenge to reverse the result; this is the explicit ex-ante fallback. After a successful challenge assessment, `settle` can execute without another contract challenge window. Network-level protocol appeals still apply before outbound transfers finalize.
- No first assessment before `submitted_at + 7 days` ⇒ refund remaining locked funds. No evidence submitted by `delivery_due_at + 48h` ⇒ refund remaining locked funds.
- Unchallenged `APPROVE_PENDING/REJECT_PENDING`: after the 48h challenge window, deterministic settlement queues payout/refund, respectively.
- Both frozen counterparties may mutually cancel via a 2-step on-chain proposal/confirmation. Proposal expires after 48h and **never pauses deadlines**; confirmation requires the other party, no transfer already queued for current milestone, and returns all still locked funds to buyer. Existing earlier payouts remain queued.
- All comparisons are inclusive for expiry (`now >= deadline`) and exclusive for actions within a window (`now < deadline`); use the **deterministic transaction timestamp**, not wall-clock timers. No autonomous cron/timer exists; permissionless calls advance deadlines.

## Money ledger and transfer semantics

`initial_deposit = remaining_locked + total_payout_queued + total_refund_queued` per deal; amounts are never reassigned between deals. Payout/refund intent must be marked and its amount subtracted from `remaining_locked` **at most once** in the same deterministic settlement transition that emits its transfer. Reject duplicate `settle`, zero-value emissions, beneficiary replacement, and any arithmetic overflow/underflow. Never subtract a message twice; old states cannot reopen. Contract-wide unqueued liabilities may not exceed available contract GEN balance (accounting for unrelated forced transfers, gas, and GenLayer's message debit timing).

Native GEN in wei (`u256`), payable creation; recipient EOA transfers use GenLayer external message via `@gl.evm.contract_interface` and `emit_transfer(value=...)`, executed on **protocol finalization**. Never send `on='accepted'`. In the architecture, **`PAYOUT_QUEUED` / `REFUND_QUEUED` describe a scheduled transfer, not verified recipient credit**. A message could fail; child/chain-layer effects require separate authoritative receipt and balance checks. There is **no blind retry** (duplicate-pay risk), no automatic refund assertion, and no trusted admin fix-up. Production readiness is blocked until the Phase-2+ tests establish safe downstream failure handling and observable reconciliation. Studio's EVM emulation differs from live chain; local Studio alone cannot certify EVM receipt behavior.

## Contract interfaces (planned; not implemented)

**Writes**: `create_deal(seller, milestones_json, buyer_nonce)` (payable); `submit_evidence(deal_id, manifest_json)` (seller); `assess(deal_id)` (buyer/seller); `challenge(deal_id, supplemental_manifest_json, justification)` (losing party); `assess_challenge(deal_id)` (buyer/seller); `propose_cancel(deal_id)` and `confirm_cancel(deal_id)` (two distinct roles); `settle(deal_id)` (anyone, only if deterministic time/result permits).

**Reads**: `deal_count()`, `get_deal(deal_id)`, `get_milestone(deal_id, index)`, `get_assessment(deal_id,index,round)`, `get_ledger(deal_id)`, `get_terms_digest(deal_id)`. All reads bounded and no side effects; large evidence bodies are fetched on demand and are not stored on-chain.

## Architecture-level release blockers

1. Verify GenVM version, parser/model bounds, deterministic timestamp and storage types with lint and executable implementation (Phase 2).
2. Prove network egress restrictions: redirects, DNS/IP resolution, rebinding, localhost/private address blocking, and source host ownership caveats; cannot claim SSRF eliminated by regex.
3. Prove outbound GEN transfer scheduling, chain-layer success/failure and recipient credit without manual assumption. No production fund-locking until safe failure recovery exists.
4. Verify mixed-mode EOA/IC recipient handling and expected fee charging; no real GEN or deployment from stage 1.
5. Independent adversarial and validator disagreement suites in later phases. Stage-1 spec checks are **not** contract runtime tests.

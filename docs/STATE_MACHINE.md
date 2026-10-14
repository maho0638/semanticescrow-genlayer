# State machine v1 (normative design)

One **active** milestone per deal. Milestones later in sequence remain `WAITING`; terminal `PAYOUT_QUEUED` and `REFUND_QUEUED` are **intent states, not credit receipts**. Deal is `RUNNING` until all stages are queued; then `CLOSED_QUEUED` (all payout intents) or `TERMINATED_QUEUED` (a refund of all still-locked funds). The deal cannot reopen.

| From | Operation + authority | Guard | To | Money |
|---|---|---|---|---|
| (absent) | create_deal, buyer | exact deposit, immutable terms | AWAITING_DELIVERY (first milestone) | lock full deposit |
| AWAITING_DELIVERY | submit_evidence, seller | now < due+48h, one original submission | SUBMITTED | none |
| AWAITING_DELIVERY | settle, anyone | now >= due+48h | REFUND_QUEUED | queue **all** remaining locked to buyer |
| SUBMITTED | assess, buyer or seller | now < submitted+7d; valid independent verdict APPROVED | APPROVE_PENDING | none |
| SUBMITTED | assess, buyer or seller | now < submitted+7d; valid verdict REJECTED | REJECT_PENDING | none |
| SUBMITTED | assess, buyer or seller | outcome INCONCLUSIVE/UNAVAILABLE | SUBMITTED | none; observation only for INCONCLUSIVE |
| SUBMITTED | settle, anyone | now >= submitted+7d | REFUND_QUEUED | queue all remaining locked to buyer |
| APPROVE_PENDING | challenge, buyer | now < assessed+48h, new supplemental evidence, challenge unused | CHALLENGED | none |
| REJECT_PENDING | challenge, seller | same | CHALLENGED | none |
| APPROVE_PENDING | settle, anyone | now >= assessed+48h, no challenge | PAYOUT_QUEUED | queue current amount to seller, unlock next milestone |
| REJECT_PENDING | settle, anyone | same | REFUND_QUEUED | queue all still locked to buyer, terminate |
| CHALLENGED | assess_challenge, buyer or seller | now < challenged+7d, independent APPROVED | CHALLENGE_APPROVE_PENDING | none |
| CHALLENGED | assess_challenge, buyer or seller | same, independent REJECTED | CHALLENGE_REJECT_PENDING | none |
| CHALLENGED | assess_challenge, buyer or seller | INCONCLUSIVE/UNAVAILABLE | CHALLENGED | none |
| CHALLENGED | settle, anyone | now >= challenged+7d, no final verdict | initial verdict's payout/refund queued | fallback to immutable first outcome |
| CHALLENGE_APPROVE_PENDING | settle, anyone | contract-level challenge consumed | PAYOUT_QUEUED | current amount to seller |
| CHALLENGE_REJECT_PENDING | settle, anyone | contract-level challenge consumed | REFUND_QUEUED | all remaining to buyer |

At `PAYOUT_QUEUED` the next `WAITING` milestone becomes `AWAITING_DELIVERY`; otherwise the deal becomes `CLOSED_QUEUED`. At `REFUND_QUEUED` later waiting milestones become `CANCELED_REFUNDED_QUEUED` and the deal is `TERMINATED_QUEUED`. A mutation of a queued terminal milestone must always be rejected.

**Mutual cancellation**: `propose_cancel` by either party stores `proposer` and `expires_at = now + 48h` without changing the active state or deadlines; `confirm_cancel` by the **other** party before expiration atomically queues a refund of all remaining locked funds and ends the deal; if any current settlement is queued already, cancellation cannot queue it again. A new proposal may replace only an expired proposal, not a live one. No party can cancel unilaterally after funding; no proposal extends any timeout.

**Assessments**: new verdict requires checked schema, source quorum (>=2 distinct-host verified bodies), exact decision-bearing field equivalence; validation conflict means rejected protocol execution/no state write, NOT a `REJECTED` business verdict. Protocol appeal windows are not these application-level challenge windows. The same transaction can be ACCEPTED by protocol while its application verdict is REJECTED.

**Boundary precedence**: for the same pinned `now`, time-based expiration wins at `>= deadline`; challenge, submission and assessment require `< deadline`. A challenged outcome cannot spawn another challenge. A `settle` before the relevant deadline MUST fail without side effect.

**Version rule**: v1 intentionally has no partial payout, split arbitration, milestone edits, deadline extensions, penalty fees, court-grade guarantees, privileged bailout, or auto-retry of external transfer. No assumptions beyond these rules should be imported by implementation.

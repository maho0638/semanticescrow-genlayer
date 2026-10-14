# Stage-1 design checks and future executable test matrix

**Legend**: DESIGN = architecture/spec check only; RUNTIME = future test required. No runtime pass claims at this stage.

| ID | Scenario | Expected | Status |
|---|---|---|---|
| A01 | Create with 0, 6 or negative milestones | Rejected, no state | DESIGN |
| A02 | Exact 1–5 positive milestone amounts vs payable GEN value | Must match exactly, checked u256 sum | DESIGN |
| A03 | Same buyer/seller; duplicate buyer nonce; zero address | Rejected | DESIGN |
| A04 | Non-increasing, past, >365d deadlines | Rejected | DESIGN |
| A05 | Seller-only submission within exclusive delivery cutoff | Enforce permission and one original manifest | DESIGN |
| A06 | Buyer impersonation as seller; attacker changing rubric/amount | Rejected | DESIGN |
| A07 | 2–5 raw SHA256 HTTPS sources, unique hosts | Hash-check; invalid bodies excluded | DESIGN |
| A08 | Duplicate JSON keys, URL smuggling, redirect, private DNS | Fail closed; enforceable network controls are GATE | DESIGN |
| A09 | Valid consensus agreement on all mandatory criteria | `APPROVE_PENDING`, no immediate payout | DESIGN |
| A10 | Verified substantiated mandatory failure | `REJECT_PENDING`, no immediate refund | DESIGN |
| A11 | Split validators, transient timeout or source outage | No business settlement state write | DESIGN |
| A12 | Valid inconclusive evidence | No release; eventually refund on review expiry | DESIGN |
| A13 | Buyer challenges approval, seller challenges rejection | Only losing party and before exclusive cutoff | DESIGN |
| A14 | Repeated challenge, replaced terms, absent unique hash | Rejected | DESIGN |
| A15 | Challenge decision accepted by quorum | Only one final verdict, old verdict preserved | DESIGN |
| A16 | Challenge never resolves | Fixed 7-day timeout follows original verdict | DESIGN |
| A17 | Submission exactly at cutoff / settlement exactly at cutoff | No submission; deterministic expiry allowed | DESIGN |
| A18 | Assessment exactly at review expiry | No assessment; refund allowed | DESIGN |
| A19 | Settle twice after queued transfer | Second attempt rejected; never emit twice | DESIGN |
| A20 | Success stage N, failure stage N+1 | Only current+future refunded, prior payouts preserved | DESIGN |
| A21 | Failed transfer/no EVM recipient balance change | Never label as paid; no blind retry; production gated | DESIGN |
| A22 | Two-party cancellation; same signer confirmation | Other-party signature required | DESIGN |
| A23 | Cancel proposal concurrent with expiration | Deadlines unaffected; no unilateral cancellation | DESIGN |
| A24 | Unsolicited direct GEN transfer | No per-deal balance increase or claim | DESIGN |
| A25 | Protocol appeal after apparent accepted decision | No external transfer before protocol finalization | DESIGN |
| A26 | Receipt `FINALIZED` with `FINISHED_WITH_ERROR` | Failed execution, not successful business action | DESIGN |
| A27 | Contract docs and reference design internal coherence | Static audit script passes | DESIGN VERIFIED |

Later phases shall replace these planned DESIGN checks with actual test IDs, log links, source hashes and non-mocked receipts. A static architecture test cannot certify source parsing, GenVM SDK behavior, or real payment delivery.

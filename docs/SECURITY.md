# Threat model, money invariants and release gates — Phase 1

## Protected assets

Buyer deposit, locked milestone balances, seller payout, buyer refund, frozen rubric, source commitments, immutable assessment history, role authentication, and availability/liveness for settlement.

## Mandatory invariants

1. For each deal, `deposit == remaining_locked + payout_queued_total + refund_queued_total`; no negative values/overflow, no emission > remaining locked.
2. The only recipients are the immutable seller for payout and immutable buyer for refund. No admin override, dynamic address in `settle`, or `origin_address` authority shortcut.
3. Each milestone has **at most one** terminal settlement intent; `settle` cannot schedule transfer twice on retry, appeal, duplicate call or reorg/undetermined retry.
4. Non-deterministic web/LLM execution performs **zero storage writes or message emission**; only consensus-accepted structured results may change application state.
5. A transfer may be scheduled only with protocol finalization semantics, never on `accepted`; intent is not proof of receipt. **No blind failed-transfer retries** or unsupported claim of automatic refund.
6. Criteria, amounts, beneficiaries, deadlines and initial manifest commitments cannot be edited post-creation; challenge can only add evidence, not replace criteria.
7. Unsupported, unavailable, malformed, contradictory or under-quorum evidence **never triggers payment**; refund on an explicit agreed expiry condition is a separate deterministic policy.
8. Unauthorised address cannot submit seller proof, challenge a verdict, confirm its own cancellation, edit records or transfer value. Any user can invoke already-earned expiry settlement without selecting beneficiaries.
9. Never use live user wallet secrets or escrow funds for test scaffolding; keep Studio/local fixtures and Studio Dev independent from public chain proofs.
10. Refund of future milestones upon one failed stage never claws back prior queued payouts, and no money transfers between unrelated deal ledgers.

## Abuse cases and required controls

| Threat | Required defense / limitation |
|---|---|
| Forged evidence or changing HTML | hash response **bytes**, bounded bodies, immutable manifest; hash still does NOT authenticate issuer |
| SSRF / DNS rebinding / malicious redirects | reject unsafe URL/IP and all redirects; need concrete GenVM egress enforcement proof; regex alone insufficient, **release blocker** |
| Prompt-injected source | quote/control-bound untrusted material, independent validator checking, no obeying remote instructions; not formally guaranteed |
| Validator split, idle, timeout, model outage | no business state write on failed consensus; available retry within deadline; `INCONCLUSIVE` not same as network failure |
| Buyer disputes good result without proof | at most one contract challenge; supplemental unique hash; 7-day timeout returns to original decision |
| Seller fakes source quorum using two hosts | record distinction between host uniqueness and publisher independence; publisher authenticity not claimed |
| Replay/duplicate deal | unique buyer nonce + role checks and exact funding; state-gated methods |
| Duplicate payout, refund/transfer racing | per-IC sequential transactions, terminal intent state, single debit/emission; test repeated calls and boundary times |
| Locked funds due to inactive party | permissionless deterministic `settle`, fixed deadlines, pre-agreed fallback policies; no automatic cron |
| Value lost in failed child/external transfer | no automatic return; verify receipts/recipient credit; **production release blocked until safe recovery path is demonstrated** |
| Unexpected ETH/GEN direct funding | reject unsolicited value via `__receive__` if callable, monitor unsolicited ghost funding that cannot be prevented at EVM level |
| EVM recipients with reverting fallback | prefer frozen wallet EOA recipients, but EOAness cannot be assumed from address syntax; test/verify and retain release blocker |

## Release gates, explicitly NOT done in Phase 1

- Actual GenVM contract, version-pinned dependencies and linter/build — Stage 2.
- Property-based and adversarial **runtime** tests: authorization, underflow, overflow, idempotence, exact deadline behavior, malicious manifest, source failures, quorum disagreement — later stages.
- True 5-validator local Studio test with receipts, state readback, transfer simulation and reversal.
- Separate real Studio Dev signed transaction and independent finality/readback proof; public GEN transaction only with user approval.
- EVM-layer outbound value receipt status and downstream failure recovery / monitoring. A protocol `FINALIZED` return is **insufficient**.
- Independent professional audit and threat assessment for any real monetary value.

**Stage-1 architectural checks do NOT assert a secure production contract.**

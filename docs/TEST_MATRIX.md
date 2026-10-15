# SemanticEscrow — executable security matrix through Phase 6

**Evidence:** 142 Direct Mode tests, 3 GenVM lint checks, 18,203 static design assertions, 2,000 model scenarios. Latest verified Direct Mode run: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38709393039. Older five-validator Studio fund/review/challenge/payout/refund tests were run in stages 3–5. Phase-6 poisoned-source Studio run is separately tracked in https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38709210875; do not claim PASS until its final GitHub conclusion is checked.

| ID | Category | Evidence status |
| --- | --- | --- |
| A01–A04 | Milestone count, exact u256 funding, role/nonce, strictly rising time constraints | Direct Mode regression PASS |
| A05–A06 | Signed seller-only delivery, buyer/third-party impersonation, immutable terms | Direct Mode PASS; prior local Studio signing PASS |
| A07 | 2–5 distinct HTTPS hosts with exact byte SHA256, max 6000B | Direct Mode PASS |
| A08 | URL smuggling, duplicate JSON, known IP-embedding DNS and unsafe host suffixes | Parser tests PASS; **real DNS and HTTP redirect protection NOT PROVEN** |
| A09–A10 | Approved/rejected mandatory criteria outcomes | Direct Mode and prior five-validator Studio PASS |
| A11 | Disagreeing validator output, hash mismatch, unstable HTTP, malformed LLM | Direct Mode PASS; cannot prove real provider diversity |
| A12 | Inconclusive means no payout; permissionless timeout refund | Direct Mode PASS; prior Studio local refund PASS |
| A13–A16 | One losing-party challenge, no replay, stored original verdict, timeout fallback | Direct Mode PASS; prior five-validator challenge/refund PASS |
| A17–A18 | Exact delivery, challenge and review UTC cutoffs | Direct Mode PASS |
| A19–A20 | No duplicate settlement and cross-milestone refund isolation | Direct Mode PASS; prior local Studio settlement PASS |
| A21 | Real beneficiary EVM credit and failed external transfer recovery | **NOT PROVEN — PRODUCTION BLOCKER** |
| A22–A23 | Counterparty-only mutual cancellation and deadlines unaffected | Direct Mode PASS |
| A24 | Unsolicited direct GEN transfer and forced native GEN funding | Only ABI payable surface checked; **forced-value runtime behavior NOT PROVEN** |
| A25 | Actual protocol-level appeal & finality after accepted stage | Application challenge and finality tested; **external paid protocol appeal NOT PROVEN** |
| A26 | FINISHED_WITH_ERROR must not count as success | CI receipt execution predicate validated; arbitrary ghost failure not reproduced |
| A27 | Reference architecture/contract implementation coherence | Model static checks PASS; residual runtime/network gates explicit |
| P6-01 | Known dynamic-IP mapping hostnames, ambiguous URLs and Unicode directionality | Direct Mode PASS |
| P6-02 | Reject HTTP partial/redirect/non-200 responses as verified; transient source errors retry | Direct Mode PASS |
| P6-03 | Malformed, additional, NaN, duplicate-key LLM output never alters state | Direct Mode PASS |
| P6-04 | Validator re-fetch disagrees on status/digest or model decision | Direct Mode PASS |
| P6-05 | Injection characters are framed as untrusted; beneficiary stays immutable | Direct Mode PASS for deterministic guards, NOT proof an actual LLM resists injection |

**No real GEN spent; no user wallets, main merge, Portal submission or public deployment.** A network-hosted, external multi-provider and EVM receipt audit is a separate risk and cannot be substituted with successful mocks.

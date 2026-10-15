# SemanticEscrow — GenLayer Intelligent Contract

**Status (2026-10-15): Stages 1–4 verified for their scoped architecture, Direct Mode and LOCAL five-validator integration. The contract is still PRE-RELEASE: live EVM recipient credit and failed-transfer recovery are NOT proved; NOT an audited or production-safe financial service.**

A standalone, reusable native GEN milestone escrow primitive for GenLayer. The buyer funds 1–5 immutable milestones. The seller submits SHA-256 committed HTTPS evidence, leader and validators independently fetch/classify under a frozen rubric, and the application records an approval/rejection/inconclusive assessment. One losing-party challenge can trigger another independent evaluation. Deterministic expiry, settlement and mutual cancellation queue GEN value transfers **only for protocol finalization**. A queued transfer is not proof of recipient credit.

## Stage 2 verified source

- [Contract implementation](contracts/semantic_escrow.py)
- [Stage 2 independent CI evidence and remaining release gates](docs/PHASE2_VERIFICATION.md)
- [Stage 3 verified five-validator local Studio consensus, corrected GenVM API and exact boundaries](docs/PHASE3_VERIFICATION.md)
- [Stage 4 independent financial ledger audit, 39 tests, payout/refund local Studio receipts and unresolved production limits](docs/PHASE4_PAYMENT_SECURITY.md)
- [Repeatable GenVM linter and Direct Mode tests](.github/workflows/phase2-contract.yml)
- [Direct Mode contract regression tests](tests/test_phase2_contract.py)
- [Immutable design and security assumptions](docs/ARCHITECTURE.md)
- [Normative stage-1 machine](spec/phase1_design.json)

**Verified CI:** https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38656407778 — **SUCCESS** at tested code commit `6a6010cd04b9e186f9a7fc3c5bf7299b3cbe19f4`: Python compile + GenVM linter (3 passes) + **23 Direct Mode tests passed** + independent Phase-1 design checks (18,203 static assertions, 2,000 abstract ledger cases). These are not five live validators, Studio finality, a real escrow contract deploy or EVM beneficiary receipts.

## Example inputs (illustration, NOT live funding instructions)

`create_deal(seller: str, milestones_json: str, buyer_nonce: str)` is payable. `gl.message.value` must equal the exact sum of the `amount_wei` decimal **strings**. Buyer/seller roles are frozen, and `buyer_nonce` is unique per buyer.

```json
[
  {
    "amount_wei": "1000000000000000000",
    "delivery_due_at": 1825000000,
    "criteria_text": "Independent release verification",
    "criteria_items": [
      {"id": "release", "text": "A released version is identified", "mandatory": true},
      {"id": "date", "text": "A release date is explicitly provided", "mandatory": true}
    ]
  }
]
```

The `delivery_due_at` value above is **only an illustrative Unix timestamp**; real inputs must satisfy `create_deal`'s time bounds relative to the transaction timestamp. Source manifest has 2–5 `{"url":"https://...","sha256":"64_lowercase_hex"}` entries from distinct canonical hosts.

## Stage boundaries and caution

- **Phase 1:** architecture/identity/immutability/state/payment invariants documented and statically checked.
- **Phase 2:** Python GenVM implementation, input guards, deterministic ledger and challenged verdicts implemented, SDK dependency blobs copied byte-for-byte with matching Git SHA, 23 Direct Mode tests and linter PASS.
- **Phase 3 VERIFIED on disposable local Studio:** exact local GenVM deploy; payable two-milestone deal; seller-signed evidence submission; five-registered-validator assessment and post-finality readback. Studio recorded 3 agree/2 idle in each consensus-checked write and four FINALIZED transactions. Only deterministic mock web/LLM data was used; [CI evidence](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38666863852).
- **Stage 4 LOCAL integration verified:** a five-validator Studio run finalized the first 10 wei payment intent and remaining 15 wei refund intent, with correct after-finality state readbacks and global liability declining 25→15→0. Studio 3 agree/2 idle quorum. [Studio CI](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38700525100). [39-test finance CI](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38701136694).
- **Still NOT verified:** actual payout/refund recipient credit, downstream EVM transfer failure recovery, realistic live external-source authenticity, DNS/redirect egress restrictions, independent security audit, public Studio Dev/mainnet deploy. Local Studio cannot certify live EVM recipient credit.
- `main` remains only the initial bootstrap, no PR merge or Portal submission has been made for SemanticEscrow, no public deploy or real GEN spent.

**Never fund this contract with valuable GEN until the remaining safety/reconciliation and network evidence gates are closed.**

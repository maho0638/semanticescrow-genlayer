# SemanticEscrow Phase 3 — verified real local Studio five-validator integration

**Date:** 2026-10-15. **Result:** PHASE 3 ACCEPTED for its documented local consensus/deploy/evidence-snapshot scope. **NOT a production audit or payout-delivery guarantee.** No fourth-phase work performed.

## Reproducible evidence

- Branch: `test/phase3-five-validators-20261015`
- Exact contract+test+workflow commit independently checked: `9ef7cc3784cf32f2438bbc8cf128b03116788ded`
- GitHub Actions local Studio: **SUCCESS** https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38666863852
- GitHub Actions static/Direct preflight: **SUCCESS** https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38666864051
- Studio version: official pinned `v0.123.0-rc.7`, local chain ID `61127`, 5 registered distinct validator identities in disposable Docker services.
- Web/LLM responses were **predefined mocks applied to five registered validator identities**. This is authentic local consensus execution, not proof of five independently owned external AI models or real website truth.
- Local tests used ephemeral SDK accounts and simulated native GEN; **no real GEN spent**, no production wallet or secret uploaded.

## Verified local on-chain behavior

| Check | Actual result |
| --- | --- |
| Five validators and SDK/RPC chain identity | 5 validators; both chain IDs 61127 |
| GenVM contract deployment | FINALIZED; `deal_count()` initially 0 |
| Buyer-signed payable create | Successful execution, FINALIZED, exact simulated GEN deposit 25 |
| Deal and ledger readback | `initial_deposit=25`, `remaining_locked=25`, payout/refund queued = 0 |
| Milestone initialization | First `AWAITING_DELIVERY`, second `WAITING` |
| Seller-signed evidence submission | Successful execution, FINALIZED, first state `SUBMITTED` |
| Independent evidence-based assessment | Successful execution, FINALIZED; 2 source hashes VERIFIED |
| Decided milestone state/readback | `APPROVE_PENDING`, first verdict `APPROVED` |
| Prevent early payout from AI verdict alone | Locked funds still 25; queued payout 0 after verdict |
| Validator vote maps | CREATE, SUBMIT and ASSESS each: **3 agree, 2 idle, 0 unexpected** |
| Studio internal transaction database | **FINALIZED = 4** (deploy, create, submit, assess) |
| GitHub Actions cleanup | Temporary local Studio stack and volumes removed successfully |

Important: two `idle` validators were stopped after a decisive quorum. Do **not** count them as independently agreeing votes or call these tests 5/5 unanimity.

## Root cause closed

The initial Stage-2 source called `gl.vm.run_nondet_unsafe`, which the repository's **pinned** GenVM Python runner did not export. Earlier real Studio runs deployed/funded/submitted successfully but `assess` raised `AttributeError`; Python compile, static linter and Direct Mode test mocks had not caught missing runtime API. Read the exact pinned SDK at `vendor/genvm/runners/genlayer-py-std/src/genlayer/vm/__init__.py` in the previously verified ConsensusGuard vendor tree: exported `run_nondet` but not `run_nondet_unsafe`.

Fixed in the isolated Phase-3 branch by calling **`gl.vm.run_nondet(leader_fn, validator_fn)`** with the existing explicit validator type check, independent re-fetch/reclassification and exception-to-False handling. The pinned SDK's `run_nondet` does not apply an extra error-handling validator sandbox; it matches our custom validation mode. The corrected code passed **23/23 Direct Mode regression tests**, GenVM lint `3/3` and the real Studio five-validator verification. This replacement was tested against the actual pinned runner, not assumed from newer documentation.

## Security and next-stage gates (not silently closed)

- **No real payout/refund recipient receipt or EVM Ghost transfer proof**. A contract's `PAYOUT_QUEUED` or `REFUND_QUEUED` is not actual recipient credit.
- No independent malicious-validator split/appeal attack suite or Studio end-to-end real transfer failure recovery proof.
- No validated arbitrary URL DNS rebinding/redirect policy, HTTP issuer authenticity, independent publisher guarantee or adversarial live website behavior.
- No public Studio Dev, Bradbury or mainnet deployment; no production wallet signing; no Portal submission.
- No claim of zero bugs or production financial security. Runtime integration coverage is limited to the documented path and deterministic mocked sources.

## Branch discipline / STOP

All Stage-3 changes are in `test/phase3-five-validators-20261015`. `main` and the original Phase-2 branch were **not merged**, no PR created, no Vercel/Portal deploy, no real GEN movement.

**Phase 3 ends here by user instruction. Phase 4 has NOT started.**

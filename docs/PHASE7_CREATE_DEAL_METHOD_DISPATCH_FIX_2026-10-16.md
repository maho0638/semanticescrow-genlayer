# SemanticEscrow — Bradbury payable create_deal dispatch mismatch FIX — 2026-10-16

## Confirmed root-cause chain

- Known **FINALIZED + FINISHED_WITH_ERROR** GenLayer transaction: `0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06`.
- Exact onchain v0.6 ConsensusData payload: 299-byte RLP envelope; 292-byte encoded call inner body, SHA-256 `262ffce30179f612b8ad127d0972cb1569c4aaaf8fb0a8663bc0917d3abc248f`.
- Decoded inner call, **actual keys**: `['', 'args']`, with `'' == 'create_deal'`. The buyer, seller, milestone values and `100000000000000` native wei were all as intended.
- GitHub CI reproduced **byte-for-byte identical** inner calldata with **installed exact `genlayer-py==0.19.0rc2`** `make_calldata_object(method='create_deal', args=onchain_args)`: `SE7_COMPARISON_PINNED_SDK_BYTE_IDENTICAL True`.
- The actual **GenVM v0.2.16** published runner `runners/genlayer-py-std/src/_genlayer_runner.py` resolves a method using `ctx.cd.get('method', '')` and sends `case ''` to `__receive__`/fallback. The deployed SemanticEscrow intentionally has neither public handler; therefore the empty-key wire call cannot invoke its `create_deal` method. This directly explains the observed GenVM failure without requiring a change to the Intelligent Contract source.
- CI verifies the official runner dispatch source at tag `v0.2.16` before running tests. Official tags and docs:
  https://github.com/genlayerlabs/genvm/blob/v0.2.16/runners/genlayer-py-std/src/_genlayer_runner.py ,
  https://docs.genlayer.com/developers/intelligent-contracts/features/special-methods ,
  https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers .

## Fix, boundaries and tests

- `tools/phase7_legacy_method_dispatch.py` adapts the SDK's *outgoing* calldata only, after Bradbury chain ID 4221 and legacy consensus ABI checks:
  `{'':'create_deal','args':...}` → `{'method':'create_deal','args':...}`.
- All method args, kwargs and GEN amounts are preserved; blank-method deployment stays unchanged; unexpected SDK ABI fails closed. No contract bytes / deployed source / GenVM dependency pin changes, so **NO new deployment** is needed.
- `tests/test_phase7_bradbury_external.py` installs this adapter *before* ContractFactory and signed writes.
- `tools/phase7_bradbury_windows.py` runs a zero-funds canonical method gate and confirms the **existing exact pinned FINALIZED Ghost** before showing any new wallet to fund. `--force-new-deploy` is disallowed.
- GitHub Actions full regression completed **261/261 PASS** (1+153+12+95), with new SDK mismatch reproduction, official runner dispatch source, and early pre-funding guards:
  https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38943634974
- Earlier original onchain versus SDK identical-key proof:
  https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38942865746

## Important unproven step

**This fixes the proven client/run-time ABI mismatch, but has NOT yet generated a new successful live Bradbury `create_deal` receipt.** The existing previous test wallet was RAM-only and its keys exited; do not fund that old address. A new one must be funded with **Bradbury TEST GEN ONLY** after zero-funding preflight; the user's Windows network was able to reach the Bradbury RPC while GitHub could not. The original verified Ghost `0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a` is reused. Final receipt must be actual `FINALIZED + FINISHED_WITH_RETURN`. Later mutual cancel and observed GEN refund is separate Phase7 work.

If GitHub DNS is broken on the user's computer, the standalone offline patch `SemanticEscrow_Bradbury_Duzeltme.py` is provided through the conversation file (not a GitHub release). It validates contract source SHA-256 and only modifies prior local Phase7 test scripts with backups. Execute with `--run` only when ready to keep the ephemeral wallet session open and fund a fresh test wallet. Do not claim the offline patch itself is a successful chain transaction.

No `main` update, PR, merge, Portal submission, production deployment, or actual new test GEN spending occurred during this code correction.

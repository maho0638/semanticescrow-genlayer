# SemanticEscrow Phase 7 — Bradbury verification report (2026-10-16)

## Exact scope and source

- GitHub project: `maho0638/semanticescrow-genlayer`, test branch `test/phase7-bradbury-runtime-compat-20261015`.
- `main` is untouched, no PR or merge.
- Current Intelligent Contract blob SHA (GitHub): `ce250b37decc7b833206b991b8f91dcb5af4746d`.
- Exact contract source SHA-256 pinned by `tools/phase7_schema_compat.py`: `ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70`.
- `# v0.2.16` runner: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.
- The current contract blob was independently confirmed identical to the one used by the 3/3 five-validator Studio test commit `9be4f42fda0d1ea54e936789c0ad640dbbe63321`. No contract behavior was modified in this verification pass.

## Technical issues corrected

1. Real signed deployment's read-only `preview_deploy` now uses the **funded current buyer** rather than simulating from a previous expired test signer. Historical read-only pre-funding preview still deliberately uses an address without a private key; no GEN funding is requested before that guard.
2. Strict legacy v0.6 finality gate refuses to call `ACCEPTED` or `FINISHED_WITH_ERROR` a success. A successful tested write must have **status=7 FINALIZED** and **execution=1 FINISHED_WITH_RETURN**, as well as pass the SDK execution assertion.
3. EVM seller-funding receipts must contain both transaction hash and destination; missing identity or destination now fails closed.
4. Added offline regression cases for funded-signer gas preview, legacy finality status, malformed EVM receipts and live-runner safety wiring; explicitly included them in the CI test command.
5. Retrieved the genuine official GenVM `v0.2.16` release artifact `genvm-universal.tar.xz`; verified GitHub-published SHA-256 `4f0b358ec98ec148be9b95cdfb0f0e1a6cbe64da0194fdfac3fffc6f5d1d93e2` and found the exact pinned runner at `runners/py-genlayer/1j/b45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6.tar`. Executed the tests with this **official packaged SDK artifact** using Direct Mode; this is still not a byte-for-byte audit of the Bradbury validators' installed runner binaries and not native on-chain GenVM execution.

## Verified test evidence

- [Updated offline runner regression, 232 passed (1+153+9+69), source pin/compile/lint](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38814785855) — PASS.
- [Official published package SHA-256 and runner pin present](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38814928487) — PASS.
- [**Same 232 tests using the official packaged v0.2.16 runner SDK in Direct Mode**](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38815095631) — PASS (1+153+78). Source reconstructed emulation not used in this particular run.
- [Real local five-validator Studio finance/appeal/adversarial testing](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38809165022) — 3/3 PASS against identical contract blob, simulated GEN and deterministic mock evidence/LLM. Consensus votes were 3 agree and 2 idle.

These are **separate kinds** of evidence; no result should be called a live Bradbury payment receipt merely because it passed offline/Studio tests.

## Remaining decisive live validation — NOT COMPLETE

Still required against actual Bradbury 4221 using a **new RAM-only test wallet**:

1. Windows Powershell bridge read-only SDK, legacy on-chain ABI/proxy, exact schema SHA and padded deploy preflight.
2. New test wallet funded with **testnet GEN only** after read-only preflight. The existing `scripts/run-bradbury-windows.ps1` creates two RAM keys and waits on a public buyer address; its current guidance suggests **5 Bradbury TEST GEN**, minimum run threshold 2. Do not fund prior ephemeral addresses. The wallet session expires after 50 minutes: only fund while it remains open.
3. Signed deploy: capture EVM tx inclusion and separate GenLayer transaction ID; require `FINALIZED` **and** `FINISHED_WITH_RETURN`, then active contract code/storage.
4. Payable `create_deal`; signed `propose_cancel`; minimal second signer gas funds only after these succeed; counterparty signed `confirm_cancel`.
5. Read immutable refund intent and exact ledger, followed by independent observed recipient EVM balance delta equal to the expected native-GEN refund. An emitted intent, ghost contract, EVM `status=1`, parent finalization or empty triggered-transactions list alone is **insufficient**.
6. No blind retries if a tx times out; investigate known tx IDs before spending further test GEN.

A hosted automation environment cannot substitute for the user's own Windows session with working Bradbury RPC connectivity, and GitHub CI historically received HTTP 403 from some network endpoints. No new signed Bradbury deployment or test-GEN transfer took place in this verification pass. Do **not** report Phase 7 as complete until all live evidence above is collected.

## Risk boundary

The user explicitly authorizes **test GEN**, temporary test wallets and testnet contract calls; no authorization for valuable funds, production or mainnet. DNS/redirect/SSRF egress and asynchronous child-transfer failure/retry safety still require dedicated separate validation and design review before valuable user custody. No PR, `main` change, Portal submission, mail access or production deployment occurred.

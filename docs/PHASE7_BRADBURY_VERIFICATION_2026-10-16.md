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

## Real signed Bradbury v0.2.16 deployment — read-only postmortem (2026-10-16, after original report)

**This is the first true successful GenVM execution for the v0.2.16 source on Bradbury, but NOT yet finalization or escrow cash-flow success.**

- Original ephemeral buyer: `0x1B982344f53257768E971DBb152907cBa33D632C`. It was funded with 5 Bradbury **TEST** GEN; Python process exited after receipt-decoder failure and its disposable private key is unavailable. **Never fund this address again.**
- EVM submission: `0x2bddc2919cde1aee0cc751e3735daa7e0ecc9fbcbab91b2bc28dd6d698455bf8`. EVM receipt `status=1`, block `25,302,687`, gas used `12,515,307`, 12 EVM logs, 6-input selector `0xe71d5196`, verified sender and ConsensusMain target.
- Separate GenLayer ID from the genuine EVM ConsensusMain `NewTransaction` event: `0x1ac72cb02a02cdf8709615b8aeed51610128dddd1a87128b58623aab73220c43`.
- Legacy ConsensusData v0.6: `status=5 ACCEPTED`, `txExecutionResult=1 FINISHED_WITH_RETURN`, both transaction ID fields match. **This is a successful GenVM execution, but not `FINALIZED`.**
- Ghost contract address: `0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a`; 300-byte Ghost runtime code exists. That is NOT independent proof of finality or beneficiary payment.
- At public read-only 2026-10-16 09:04 UTC: `canFinalize=false`; its returned future timestamp `1792142110` = 2026-10-16 09:15:10 UTC = 12:15:10 Türkiye. A deadline passing alone does not materialize onchain finalization.
- At same time, read-only old buyer `eth_getBalance=4973692551852307400 wei` (about 4.9736925518523074 test GEN), nonce=1. Private key wasn't preserved, and spending this remainder must not be promised.
- Onchain signed calldata was **byte-identical** to the exact source-pin-passing local `_build_payload` with buyer `0x1B98...` and 15,738 source bytes; no another-source ambiguity.
- These facts were verified by [actual-chain read-only workflow](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38876301749), [finality and bytecode probe](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38876532744), [exact signed source match](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38877938857).

### Why original Windows runner stopped

It displayed `DeploymentError` caused by `LegacyReceiptError` **after a real EVM broadcast**. The exact early malformed record was not preserved, so its precise underlying reason cannot be proven retrospectively. However, a later identical-ID read decoded cleanly and confirmed GenVM successful execution. The first version's v0.6 reader also omitted the mandatory `lifecycle` that pinned `genlayer-py==0.19.0rc2`'s `wait_for_finalization` requires; that was a separate definite latent failure.

Corrections are now on the test branch:
1. v0.6 reader decodes a truthful `lifecycle`: ACCEPTED is `decided`, FINALIZED is `finalized`; never prematurely finalizes.
2. Bounded retry handles briefly inconsistent legacy reads without suppressing persistent invalid data or RPC failure.
3. Existing exact signed deployment is now re-attested read-only against EVM original input, pinned contract SHA, known GenLayer tx ID and Ghost, real `status=FINALIZED + FINISHED_WITH_RETURN`. No new buyer wallet is requested **unless the existing deployment is provably finalized**. Default subsequent Windows run reuses the existing contract and skips duplicate deploy. It asks for approximately **2 test GEN** for remaining payable deal/counterparty cancellation/beneficiary refund proof only after that gate. User can explicitly opt into fresh deployment, but blind duplicate deploy must be avoided.
4. Test suite updated: `1` old web + `153` Direct Mode + `12` legacy receipt + `82` additional offline/adversarial tests = **248 PASS** [GitHub workflow](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38877848740). Other five-validator full Studio tests used the identical contract blob; contract source unchanged.

### Decisive remaining tests

- Observe a stored protocol `FINALIZED` for the known GenLayer tx ID; mere passage of 12:15:10 Türkiye or a `canFinalize=true` getter is insufficient.
- After that, from user's Windows repository folder run `git pull` and then `powershell -ExecutionPolicy Bypass -File .\\scripts\\run-bradbury-windows.ps1`. Current new runner first tests the existing signed calldata and finality; **only if it passes** does it print a new temporary buyer address for 2 Bradbury TEST GEN. The user must not send anything to old address or to a closed temporary test wallet.
- Confirm fresh real payable `create_deal`, mutual cancel and actually credited EVM buyer refund with before/after balances. Neither this step nor child payment receipts have yet occurred.
- Investigate/propose safe failed-child message recovery before valuable live funds, independent audit. No production deployment, main update, PR, merge or Portal submission.

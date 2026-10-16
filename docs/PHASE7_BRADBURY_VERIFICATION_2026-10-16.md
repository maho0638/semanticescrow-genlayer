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

### Live execution duration safety update (2026-10-16)

The real deployment took roughly 30 minutes from ACCEPTED to its earliest reported finalization timestamp, while the older runner waited **only 140 x 3 seconds = 7 minutes**. That timeout was insufficient for a signed onchain transaction, even with a correct reader. The updated test path uses **1,200 x 3 seconds = up to 60 minutes** for each finalization wait. The asynchronous refund EVM beneficiary balance polling also lasts up to 60 minutes; the PowerShell parent holds the ephemeral signing session in RAM for up to 6 hours while the integration test runs. These are read-only polls after each signed action, NOT retries of signed payments. The user must keep the PowerShell process alive; if a timeout occurs, stop and inspect public tx IDs and recipient balances rather than funding a new ephemeral wallet blindly. Do not treat mere passage of an appeal deadline as proof of materialized FINALIZED status.

Additional timeout and funding-order regression: [249 successful tests (1+153+12+83)](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38878413843). The actual live refund path remains unexecuted/uncertified until another disposable onchain test after original finalization.

## 2026-10-16 REAL payable create_deal FAILED on Bradbury (additional signed 2 TEST GEN session)

After the first v0.2.16 deployment was genuinely `FINALIZED` +
`FINISHED_WITH_RETURN`, the Windows test reused Ghost
`0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a`.
The temporary buyer `0xa9afeBFEc83cEddcAE9b61a3A22971BF5e426e0C` received 2
Bradbury **TEST** GEN and submitted one exact payable `create_deal` with
`100000000000000` wei (0.0001 TEST GEN). No seller gas funding, cancel
proposal, seller confirmation, or refund was sent.

Evidence:
- EVM tx: `0xa8ea226dc7cce9dd9265c400198d08673774b4ebdf31f40171ac3e6d491441a4`.
- Independent GenLayer transaction ID from ConsensusMain event:
  `0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06`.
- EVM receipt: status 1, block `25,305,039`, gas used `1,052,166`, 4 logs, six-input legacy selector `0xe71d5196`. **Not proof of GenVM success.**
- Legacy ConsensusData `getTransactionData` and `getTransactionAllData` return matching GenLayer ID, correct buyer (origin + sender), correct Ghost recipient, recorded native value `100000000000000` wei, **status 7 FINALIZED but txExecutionResult 2 FINISHED_WITH_ERROR**. The failure is a real GenVM execution failure, not merely the patched SDK receipt reader or a pending appeal.
- `eqBlocksOutputs`: only 8 bytes in the public record, with no legible error reason. Its digest is `d9c1f8a6a5cc9da94f792987d84d66d4bce31cc4c659b0e339a2a026724dbd9a`. Root cause (old runtime ABI/call-data/value/storage/contract logic or upstream validator failure) is **not yet proven**. Do not invent a specific source-line diagnosis.
- Most recent read-only buyer `eth_getBalance` returned
  `1997701684850299000` wei (approximately 1.997701684850299 TEST GEN);
  nonce 1. The process finished, ephemeral keys were RAM-only, so this
  remaining wallet balance is **not a recoverable budget**.
- Read-only chain evidence: [initial paid create receipt and execution](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38886548880);
  [independent amount/recipient/result/8-byte outputs confirmation](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38886787565).

**SAFETY NO-GO:** The Windows funded runner is intentionally blocked
immediately after safe read-only preflight on the current pinned source, with
`SE7_PUBLIC_KNOWN_PAID_CREATE_DEAL_FAILURE_FINALIZED_WITH_ERROR` and return 5,
BEFORE it prints a new fundable ephemeral wallet. `--force-new-deploy` does
NOT bypass this. No more blind redeploys or paid `create_deal` until the
actual runtime failure is identified, a new compatible candidate is
validated in Direct Mode plus full five-validator Studio and given a fresh
source attestation before a deliberately approved new Bradbury test.

The existing Bradbury-deployed source was **NOT modified**; `main`,
Phase 8/9 audit branches, and Portal are not involved. Stage 7 remains
**INCOMPLETE**, real-value release still blocked.

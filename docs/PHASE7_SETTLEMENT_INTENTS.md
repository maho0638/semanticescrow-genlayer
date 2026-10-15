# SemanticEscrow — Phase 7 settlement-intent audit interface (2026-10-15)

## Status and original-scope warning

This is a **scoped technical implementation** of an unresolved transfer-accountability risk after Phase 6. The original nine-stage plan's exact Phase 7 heading and acceptance checklist were **not preserved in the handoff**. Do not assert that this work satisfies every requirement of that missing plan. Mark COMPLETE only for the local checks when their CI runs pass.

## Change

- New read-only `get_transfer_intents(deal_id)` and `get_transfer_intent(deal_id, milestone_index)`.
- Every queued payout/refund can be reconciled against frozen parties, amount, milestone index, original terms hash, and a domain-separated SHA-256 intent identifier.
- Aggregate amounts are cross-checked against the original `payout_queued_total` and `refund_queued_total`, with a fail-closed error on inconsistency.
- A refund after one or more payouts is represented as a single remaining locked amount assigned to the active failed/cancelled milestone. Later cancelled milestones are not duplicated as transfer messages.
- No additional state-mutating, payable, admin, rescue, retry, or credit-confirmation method was added. Existing settlement emissions and economic outcomes stay unchanged.
- The exact `status` string is `QUEUED_UNVERIFIED` for all intents. This state is **never** a blockchain payment receipt. Intent IDs are commitments to contract terms, *not* child transaction hashes.

## Local verification

Workflow: `.github/workflows/phase7-intents.yml` (full Phase 2–6 Direct Mode regression, new Stage 7 checks, pinned GenVM lint, Phase 1 invariants).

Studio: `.github/workflows/phase7-studio.yml` (five locally registered validator identities; mocked source/LLM; the source-tampering and expiry-refund scenario now also checks actual post-finality read-only intent output).

**Verified Phase-7 immutable tested commit:** `bb9df849b12f2eb646fc9cb73bf7f360831af68e`.

- Full regression: **153/153 pytest PASS** (142 historical + 11 new), **3/3 GenVM lint PASS**, Phase 1 static invariants **18,203** and abstract ledger scenarios **2,000**: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38713765216 — completed SUCCESS.
- Real pinned Studio local five-validator run: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38713765220 — completed SUCCESS. Chain 61127, five registered local validator identities, CREATE/SUBMIT/ASSESS/REFUND each 3 `agree` + 2 `idle`; `idle` is not agreement. Altered source remained inconclusive; no seller payout. The timeout refund (25 simulated wei) emitted one read-only `QUEUED_UNVERIFIED` intent to buyer. Studio checkpoint `STUDIO_QUEUED_REFUND_INTENT_READBACK_PASS` recorded; test error classes empty, 6 FINALIZED database transactions including child/system operations.
- The full post-test direct and Studio checks ran on the **same contract blob** at the tested commit; any later updates to documents alone are not new contract execution evidence.
- This is a local, controlled/mock-source and mock-LLM test. There is no EVM Ghost-layer recipient credit proof.

## Production release blockers — intentionally unresolved

**A**. DNS resolution, redirect chains, egress private IP restrictions, remote source ownership and real prompt-injection resilience are not demonstrated by the local mocks.

**B**. GenLayer native value-bearing child messages are asynchronous; on failure the value is not automatically returned. A parent FINALIZED, a stored intent, or `total_locked=0` does **not** prove beneficiary EVM credit. Child receipts, Ghost-level transaction status and balance effects need read-only cross-chain reconciliation with trusted RPC endpoints.

**C**. No safe retry or failed-transfer recovery mechanism is established. An unverified retry might double-pay. Do not add one without protocol proof and adversarial tests.

**D**. No public chain, actual independent model provider, independent external security audit or real GEN spend was performed. The contract is **PRE-RELEASE / NOT SAFE TO FUND**.

Docs: https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers and https://docs.genlayer.com/developers/intelligent-contracts/features/messages.

## Stop point

Code and tests can be concluded for **this limited, local Phase-7 evidence interface** only. The withheld real-funds authorization, original missing Stage 7 specification and external delivery-safety gates remain open. Never claim a live payment has reached the recipient merely from the presence of a row.

## 15 Oct 2026 — Actual Bradbury public RPC execution attempt (after user test-GEN approval)

The user explicitly approved spending **free test GEN** from an independently generated ephemeral wallet, without disclosing or committing mnemonic/private key material. The intended integration test was to deploy SemanticEscrow on Bradbury, fund a deal, mutually cancel with a separate signer, and independently confirm beneficiary EVM balance credit. The entire test harness was isolated on `test/phase7-bradbury-ephemeral-20261015`, not `main`.

- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38740606209> — **FAIL (transport blocker, not contract execution failure)**: Bradbury RPC returned HTTP 403 during the preflight `eth_chainId`, before the ephemeral wallet was created. No test GEN was funded, spent, or stranded.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38740830771> — **SUCCESS as diagnostic** from Ubuntu: 2/2 `rpc-bradbury.genlayer.com` requests HTTP 403; 2/2 `rpc-asimov.genlayer.com` requests HTTP 403; the separate official `rpc.testnet-chain.genlayer.com` returned HTTP 200 with chain ID 4221 on both attempts.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38741064285> — **SUCCESS as diagnostic** from macOS with identical results: GenLayer-specific RPCs HTTP 403; underlying L2 chain RPC HTTP 200, chain ID 4221.

The GenLayer-specific JSON-RPC is needed for deploying/calling the Intelligent Contract and reading `gen_*` consensus status. Standard `eth_*` L2 access is insufficient to certify a GenVM/Ghost payout or child transfer recovery. HTTP 403 must not be circumvented by routing secret signing keys through unverified proxies.

**Phase 7 remains locally verified only**, with 153 Direct Mode PASS + local Studio five-validator PASS; Bradbury end-to-end EVM credit and child-message failure recovery remain **NOT VERIFIED**. Do not mark fully completed or ready for live escrow money.

**Wallet safety:** The wallet-generation path was not reached on the failing run, so no fundable public address with a currently retained key exists. Never ask the user to send test GEN to previously expired ephemeral wallet addresses. A fresh wallet address may be shared ONLY after a confirmed-access session has successfully started and its key remains available to the signing process. No main branch, Portal, PR, merge, or production deployment was affected.

## 15 Oct 2026 — Cloudflare cf-mitigated=challenge diagnosis (read-only)

A precise HTTP-header probe at https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38746191325 confirmed the root transport obstruction for the current GitHub-hosted RPC test:

| POST eth_chainId endpoint | HTTP | Server | cf-mitigated | Body |
| --- | --- | --- | --- | --- |
| rpc-bradbury.genlayer.com | 403 on both tries | cloudflare | challenge | text/html |
| rpc-asimov.genlayer.com | 403 on both tries | cloudflare | challenge | text/html |
| rpc.testnet-chain.genlayer.com | 200 on both tries | ordinary JSON RPC | none | application/json, chain 4221 |
| studio.genlayer.com/api | 200 on both tries | cloudflare | none | application/json, chain 61999 |

Cloudflare's own documentation confirms that `cf-mitigated: challenge` indicates a challenge page being served, not an actual JSON-RPC response. JSON-RPC clients cannot complete a browser challenge, so the request does not reach the GenLayer RPC method handler. This is conclusively an edge-gateway challenge for the tested CI requests, **not a contract compile/test-gas/GEN balance error**. It also distinguishes the earlier separate Bradbury reported internal upstream proxy failure (https://github.com/genlayerlabs/genlayer-cli/issues/425) and MetaMask `net_version` omission (https://github.com/genlayerlabs/genlayer-docs/issues/486) from our specific 403.

The specific Cloudflare WAF, Bot Management, rate-limiting, IP/geo or other matched rule is **not known** without the GenLayer site's Security Events/Cloudflare configuration. Owner-side remediation should exempt legitimate JSON-RPC API traffic from interstitial challenge actions, while retaining appropriate API authentication, rate limiting and abuse controls. An approved IP allowlist or officially authenticated machine-to-machine path are other owner-controlled options. Users cannot solve this reliably by adding GEN, changing wallets, or modifying escrow source.

Cloudflare sources:
- https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/
- https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/
- https://developers.cloudflare.com/waf/custom-rules/skip/

**Operational consequence:** Bradbury end-to-end escrow transfer and EVM/Ghost recipient credit remain unverified until the operator corrects challenge handling or supplies an official supported accessible GenLayer RPC. Never route keys through random proxies, or send test GEN to expired ephemeral wallet addresses.

## 2026-10-15 — Bradbury Windows user-funded first-attempt incident

**Status: FAILED; Phase 7 real beneficiary refund remains UNVERIFIED.**

After the user's PowerShell successfully passed the Bradbury GenLayer RPC and read-only SDK chain/account checks through the local PowerShell loopback bridge, two transient test accounts were generated in process memory. The user supplied **5 Bradbury TEST GEN** to the publicly displayed buyer address `0xFd9D26a2bAf8B26a21DF64D6bEE54ed50823Bc18`. The runner printed `TEST GEN RECEIVED 5000000000000000000 wei`, then terminated with only a generic `AssertionError` class; it suppressed the exact test stack frame. No successful Intelligent Contract deployment, deal, or refund was demonstrated.

Independent **read-only** public L2 inspection:
- https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38755660435 — Bradbury chain 4221, EOA latest/pending nonce **1** and balance **4,989,996,626,586,250,000 wei** after the failed run; exactly one EVM outbound transaction.
- https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38756560311 — that outbound transaction `0x5c4d81b873d6f5d86acf6082565c4eac8ce2b536e3eadcd4e9e291fb7aed0df3` transferred **10,000,000,000,000,000 wei (0.01 GEN)** to `0x351714b6052f66cf62986fe013868e401c8df3c7` in block `0x181270c`; EVM receipt status **0x1**, successful. No second outgoing EVM transaction was observed. The account's diminished balance reflects the transfer plus network fees.

**Important limits:** The exact Python assertion is not recoverable from the captured output; never assert the transaction itself failed, and do not guess which following fee quote / deployment substep failed. The runner terminated and no account secret was saved. Therefore the remaining ephemeral account balance is not spendable using the available test tooling. This operational key-retention defect must be addressed before any further user-funding request. **Do not fund the expired EOA again.**

On isolated `test/phase7-windows-bradbury-20261015`, subsequent technical work added robust EVM receipt format checks, additional public step checkpoints, pre-funding live fee-quote and ABI-readback gates, and offline tests. CI https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38756963913 passed **153/153 historical contract regression**, **19 EVM receipt tests**, **2 loopback relay tests**, **3/3 GenVM lint**. These tests are **not** public-network proof and did not spend any more GEN.

Safe release gate: prior to accepting new test GEN, adopt a user-approved locally recoverable test-wallet strategy (e.g. Windows DPAPI-encrypted local backup, with no secret sent to GitHub/ChatGPT), or a tested alternate mechanism that preserves signing availability across failures. Restore signed-test diagnostic granularity without leaking keys. No contract deploy/merge/Portal/main actions authorized by this incident.

## 2026-10-15 — Bradbury fee-estimation failure independently reproduced (zero spend)

User's Windows readonly run showed `BRADBURY POWERSHELL RPC OK: 4221`, then `SE7_PUBLIC_FAILURE_STAGE GET_CURRENT_FEE_POLICY` and `SE7_PUBLIC_FAILURE_CLASS GenLayerError`, before requesting a new test GEN wallet funding.

A separate **public L2 RPC** check, with no keys or value transfer, independently queried the **configured GenLayer-PY Bradbury FeeManager** `0xF205868bf5db79d2162843742D18D0900A9E462a` using method selectors from the SDK's `get_current_fee_policy` implementation. Evidence: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38760753721 (SUCCESS, read-only).

| View call against Bradbury chain 4221 | Response |
| --- | --- |
| `eth_getCode(FeeManager)` | Nonempty deployed code, 1159 bytes |
| `GENPerTimeUnit()` | Success, 0 |
| `storageUnitPrice()` | Success, 0 |
| `quoteGasPrice()` | JSON-RPC error code 3 |
| `messageFeeParamsBudgetFloor()` | JSON-RPC error code 3 |
| `eth_gasPrice` | Success |

SDK source: https://github.com/genlayerlabs/genlayer-py/blob/main/genlayer_py/contracts/actions.py , `get_current_fee_policy` near lines 615–666. It requires all four getters when a FeeManager is configured, therefore an error in the third method prevents the fee estimate. The pinned `genlayer-py==0.19.0rc2` fee-policy interface appears incompatible with this deployed Bradbury FeeManager. **RPC error code 3 alone does not establish whether the selector is missing, the contract reverts for another reason, or a network-specific precondition fails**. These must not be conflated with Cloudflare's separate 403 transport challenge (the user's PowerShell transport already overcame that).

**BLOCKER:** Do not retry arbitrary zero-cost fee configurations or pretend these results validate the current protocol version; GenLayer contract deploy and value-bearing child refund still need verified fee policy, ABI and execution. Official SDK/network deployment compatibility confirmation or a supported legacy fee-policy path is needed. No test GEN was transferred in the readonly reproduction. Local tests passing cannot certify Bradbury receipt credit.

## 2026-10-15 — Bradbury v0.6 fee/ABI compatibility repair (188 offline tests PASS)

**Root cause confirmed by deployed EIP-1967 proxy/implementation read-only inspection** at https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38762871201:

- FeeManager proxy `0xF205868bf5db79d2162843742D18D0900A9E462a` implementation `0x31199772507933c5ad94da28ab7b02bf9c41069c` has old seven-element `calculateRoundFees((...),uint256,uint256)` selector `0x4fe8920e`; it does not contain new `quoteGasPrice()` and `messageFeeParamsBudgetFloor()` selectors.
- ConsensusMain proxy `0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D` implementation `0x0a2c393975da79505ed930efc55ae4aeb88b0d62` has legacy `addTransaction(address,address,uint256,uint256,bytes,uint256)` selector `0xe71d5196`.
- Installed GenLayer-PY 0.19 RC instead encoded a modern fee-aware tuple ABI at selector `0x35a251fb`, while its new fee-policy helper invoked two nonexistent functions. Thus merely omitting fee estimation was **insufficient**.
- Live old price getters `GENPerTimeUnit()` and `storageUnitPrice()` each returned zero, and `getValidatorsPerRound(0)` returned five. This is not evidence of a general zero-fee future deployment, only this pinned testnet implementation.
- The isolated Windows test branch `test/phase7-windows-bradbury-20261015` now has `tools/phase7_legacy_compat.py` as a **fail-closed read-only gate**. It verifies chain 4221, exact proxy and implementation addresses, bytecode selectors, legacy fee getter values, validator count, then replaces only the installed SDK's **in-memory** `addTransaction` ABI entry with the official six-argument legacy entry. It submits with the SDK's native `fees=None` legacy path. No arbitrary fee pricing or global/persistent SDK patch.
- The pinned SDK's actual EVM ABI encoding is tested offline and yields exact `0xe71d5196`; full six-input arguments are ABI-decoded and compared.
- Exact tested source commit `ae683ac30c2e16062a3bb2a68569e38b4fe5c459`. CI https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38764895747 **SUCCESS**: 153 Direct Mode regression + 19 receipt + 2 loopback + 13 compatibility guard + 1 real SDK calldata-encoding = **188/188 Python tests**, plus GenVM lint 3/3. **No Bradbury GEN spent by this patch/test.**

**Important remaining verification:** Only a Windows PC whose PowerShell can access Bradbury can finish the real contract deployment, creation, dual-signed cancellation and independent Ghost recipient EVM credit test. GitHub Cloud runners were blocked by Cloudflare. Do not claim Phase 7 completely closed from offline evidence. The release's failed-message recovery and DNS/source security gates are also not established by this compatibility patch.

The runner must first be executed with `--diagnose-only`. Only after it prints `SE7_PUBLIC_LEGACY_PROTOCOL_GATE_PASS` and `SE7_PUBLIC_CONTRACT_SCHEMA_CHECK_PASS` should it display a new temporary funding address in normal mode. Never send tokens to the previous expired address. The ephemeral wallet key is not saved, in accordance with the user's stated preference.

## 2026-10-15 — Studio-dev contract schema bridge after legacy Bradbury fee/ABI correction

User's Windows screenshot shows `SE7_PUBLIC_LEGACY_PROTOCOL_GATE_PASS`, immediately followed by `SDK READ-ONLY PREFLIGHT FAILED: AssertionError`. This is after the validated old Bradbury ABI/fee gate. Source inspection of GenLayer-PY `get_contract_schema_for_code` shows it deliberately rejects non-localnet networks; gltest's `ContractFactory._get_schema_with_fallback` silently returns `None` if all fallbacks fail. This is a **schema compilation API limitation**, not a failed GenVM contract deployment.

Read-only hosted API proof:
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38775305078>: `gen_getContractSchemaForCode` on `studio.genlayer.com/api` failed `-32603`; `studio-dev.genlayer.com/api` succeeded, returning `ctor` and **17 methods**.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38775566652>: complete 17 method names matched the SemanticEscrow source byte hash `4fae50929d9e98e1d166661acaac120d5153e5dd8ca1b203a444475330223b66`.
- Isolated Windows test branch adds `tools/phase7_schema_compat.py`, which requests the same public source from **the official Studio-dev JSON-RPC only**, verifies the exact source hash and 17 required method names, and binds the returned schema on **one ContractFactory instance**. If blocked in Windows Python, only the official Studio-dev RPC via native PowerShell is allowed; no arbitrary proxies or private wallet credentials. No global SDK modification.
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38776193493>: **SUCCESS**: 153 historical Direct Mode + 19 EVM receipts + 13 old ABI + 1 SDK encoding + 2 PowerShell localhost + 10 static/schema fail-closed + 1 real Studio-dev source compilation test = **199 passed**, GenVM lint 3/3. Tested code commit `8045b0d47c4195bf027dc3133215b0e8da2a9dd4`.

No actual Bradbury contract deployment, seller approval, or real Ghost refund was proven after this patch. Before any new test-GEN transfer, execute Windows `--diagnose-only` and **require** both `SE7_PUBLIC_LEGACY_PROTOCOL_GATE_PASS` and `SE7_PUBLIC_CONTRACT_SCHEMA_CHECK_PASS`, followed by `DIAGNOSTIC COMPLETE`. Never fund expired earlier accounts.

**Stage 7 is NOT fully complete**: live transaction receipt/balance proof and reliable child-transfer failure handling remain separate production release gates.

## 2026-10-15 — Windows second funded Bradbury attempt — EVM deploy was NEVER broadcast

The user ran the Windows PowerShell/gltest escrow scenario after a successful free `--diagnose-only` gate. Buyer public address `0x84D37542B362F96282b19D479cF9b06E15ff62eA` received **5 Bradbury TEST GEN**. Seller fee funding EVM tx `0x77c2f76798c8bf52b4d741352c6d67d2ccde03b43af7bb7aa7db7ae5eaffc860` completed with status `0x1`, seller credit exactly **0.01 GEN**. SDK's old onchain ABI gate and Studio-dev 17-method source schema gate passed. The next step `DEPLOY_BEGIN` failed with wrapper `DeploymentError`; pytest showed line 78 but discarded the chained cause. No GenLayer Intelligent Contract was deployed or refunded.

**Independent chain receipts (no keys, no signing):** <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38777646415> proved buyer latest/pending nonce **1**, buyer balance **4,989,996,232,628,350,000 wei**, and confirmed seller-funding tx. Therefore no deploy EVM transaction was broadcast, and no deploy failure receipt exists to inspect. The only EVM send was the successful 0.01 GEN transfer. Do not fund this expired wallet: its in-memory signing key was destroyed on process exit.

**Deploy simulation of exact bytecode and onchain Legacy ConsensusMain ABI:**
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38777982145>: source hash `4fae50929d9e98e1d166661acaac120d5153e5dd8ca1b203a444475330223b66`, legacy selector `0xe71d5196`, serialized deploy payload ~31,460 bytes; `eth_estimateGas` returned `0x184420e` (25,444,878 gas).
- <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38778311392>: 100,000,000 block gas limit; projected **54,070,365,750,000,000 wei** at current base+priority pricing; `eth_call` with default gas reverted, while the same call with **estimated gas + 3,000,000** returned successfully. This suggests an insufficient default gas simulation limit, but the lost chained SDK exception leaves the **exact Windows deployment failure unproven**. Separate publicly filed GenLayer CLI issue <https://github.com/genlayerlabs/genlayer-cli/issues/402> describes exact-`eth_estimateGas` gas limits causing real consensus EVM reverts; it is related risk rather than proof of this unsent transaction.

**Repair:** In isolated `test/phase7-windows-bradbury-20261015`, `tools/phase7_deploy_preflight.py` now prepares the exact source/ABI deployment, simulates `eth_estimateGas` and padded `eth_call` before any funding request, and only after live ABI attestation installs **scoped 20%-or-3M gas headroom** on legacy ConsensusMain `addTransaction` estimates within the single cached `gltest` client's provider. Unknown selectors, networks, contracts, RPCs are untouched; no automatic retries. `tests/test_phase7_bradbury_external.py` exposes *exception class chain only* for subsequent deployment failures, never private keys or full RPC request bodies. `tools/phase7_bradbury_windows.py` suppresses pytest source excerpts masquerading as progress markers.

**Verification boundary:** These source and CI checks do not show that actual Bradbury deployment, custody/refund, or failing child-message recovery works. Require successful Windows free `--diagnose-only`, then a separate new temporary test GEN wallet and explicit onchain GenLayer + Ghost beneficiary receipt/balance proof before considering Stage 7 complete. Do not use valuable production funds.

## 2026-10-15 — Compact Bradbury candidate verified offline and schema-compiled

After the third Windows signed attempt (fresh temporary buyer `0x5FF26d32Ae57cdE75C741aC3a7E4cdF352e285B5` with **2 TEST GEN**), stage 7 again stopped at GenLayer `DeploymentError`. SDK legacy ABI, official Studio-dev 17-method schema, 25.4M-gas unsent deployment simulation and 30.53M-gas headroom all passed. Signed seller EVM funding 0.01 TEST GEN (tx `0x9f4309c5fd221007af6d91b6617632d5c7a53f726ac518d16034ed82608931f1`) succeeded. The attempted deployment itself never reached a transaction receipt.

Independent chain verification: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38781700731> chain ID 4221, buyer latest and pending nonce **1** (only the seller funding transfer), buyer balance **1,989,996,062,500,000,000 wei**, seller transfer receipt status 0x1. Keys were ephemeral and not retained. Do not fund these expired addresses.

Possible related Bradbury hard cap: <https://github.com/genlayerlabs/genlayer-cli/issues/419> reports deployment transactions at **16,000,000 gas or above rejected**, distinct from undersized gas <https://github.com/genlayerlabs/genlayer-cli/issues/402>. This is supporting circumstantial evidence, **not yet a confirmed RPC diagnosis** for SemanticEscrow. An isolated Windows test branch added sanitized `eth_sendRawTransaction` instrumentation to distinguish error codes from gateway transport errors if a future test is permitted.

Without spending any further GEN, the original `contracts/semantic_escrow.py` **31,197 byte**, **25,444,878 gas** version was compacted under explicit source/ABI hash assertions. Aggressive minifier initially broke a public `str` annotation and renamed `verdict_prompt`, caught by ABI and adversarial tests. Both were corrected. Final candidate **15,842 bytes**, SHA-256 **24cee2dd31e38cde646911fb5ae6ca1c0f46b82b8349ea4919199119115a94d5**, keeps 17 public methods and passes:
- **153/153 GenLayer Direct Mode contract behavior tests** and **GenVM lint 3/3**: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38784369780>.
- **63/63 compatible SDK, gas, RPC/error-redaction and wallet relay tests**, plus above 153, and chain 4221 read-only exact deploy simulation with gas **13,591,340** + conservative **14,950,474** capped to less than 15M: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38785228880>.
- **17/17 method real official Studio-dev schema compiler verification**: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38785953388>.
- Adjusted live test sequence: seller gas funding now happens *only after* signed deployment, creation and cancel proposal succeed, so repeated early deployment errors no longer waste the seller funding transfer. Isolated static safety test: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38786164669>.

Full compact source, matching SHA-pinned schema validator and test runner live only on isolated branch `test/phase7-compact-bradbury-20261015`. `main` remains unchanged and no PR/portal submission was created. **No compact-contract signed deployment has been sent yet, and actual beneficiary refund transfer/settlement still unproven. Do NOT call phase 7 finished or ready for production until genuine buyer/child GEN transfer receipts and balances are verified and child-transfer failures are addressed.**

## 2026-10-15 — First successful compact Bradbury EVM deployment submission, but GenVM execution error

User ran the fully preflighted compact 15,842-byte SemanticEscrow contract from `test/phase7-compact-bradbury-20261015` on Windows Bradbury chain **4221**. Buyer ephemeral public EOA `0xf11c3eBa500755F408Eceb16A9c79e724a596e95` received **2 TEST GEN**. Exact real compact source SHA-256 `24cee2dd31e38cde646911fb5ae6ca1c0f46b82b8349ea4919199119115a94d5`, estimated gas **13,591,340**, padded limit **14,950,474**, native legacy `addTransaction` selector `0xe71d5196`. `eth_sendRawTransaction` returned **EVM transaction hash `0x01a2fb2728253002bc3c2668bedb17b56d57b19f68795301c2950d9f51b722ba`**. The installed v0.19rc2 SDK's contract factory then raised `DeploymentError` wrapping `GenLayerError`.

**Definitive public EVM receipt** <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38787954952>:
- EVM receipt status **1** at block **25,252,597**, gas used **12,584,078**, transaction nonce **0**, buyer latest/pending nonce **1**, to official ConsensusMain `0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D`, 12 events, one emitted at ConsensusMain.
- Buyer EVM balance after attempted deploy **1,973,407,433,335,063,000 wei** (original **2,000,000,000,000,000,000 wei**). No seller fee funding in this newer safe-order scenario.
- The GenLayer `NewTransaction` event's correctly decoded `txId` is **`0x0c91636fc0354024f6e26c88d81c23c47c3e547022dada171a698c2e7cc065ca`**: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38788200638>. **EVM hash and GenLayer txId must never be confused.**

**Direct onchain v0.6 ConsensusData**, not the incompatible v0.19 Train abstraction:
- Official ConsensusData `0x85D7bf947A512Fc640C75327A780c90847267697`.
- `getTransactionStatus(txId,timestamp)` returned **5 = ACCEPTED**, confirmed with different timestamps: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38788940714>.
- The precise official legacy ABI `getTransactionData` / `getTransactionAllData` returned transaction and rounds; Ghost recipient `0xfe3ADf6da8C9d4e13BA60791770E2A1d3852b45E`, 300 bytes of EVM ghost code; stored transaction consensus result **1** and execution result **2 = FINISHED_WITH_ERROR**, while `canFinalize(...)` returned **false**: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38790107194>. **Ghost creation and EVM status=1 do NOT prove successful GenVM contract deployment.** This attempt did not reach `create_deal`, escrow funding, two-signer cancellation, actual refund or beneficiary balance evidence.
- The pinned package's default `client.get_transaction` tries an `eth_call` to `0x8aCE036C8C3C5D603dB546b031302FCf149648E8` selector `0x6eb9c474`, which reverts RPC code 3. This follows a successful initial ConsensusData call and produces the wrapper `DeploymentError`: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38789309337>, <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38789504198>. Direct ordinary `eth_call` without gas overrides to legacy `getTransactionData` and `getTransactionAllData` both succeed: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38789148246>. Therefore this SDK read failure is not a real EVM-revert diagnosis and not attributable to its `eth_call` gas budget. **But bypassing the SDK reader alone is insufficient**, because stored GenVM execution genuinely failed.
- The public node returns **-32601** for `gen_dbg_traceTransaction` and `gen_getTransactionReceipt`; thus exact GenVM stderr is unavailable through these RPCs: <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38790361294>, <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38790687107>.
- A disposable **Studio v0.123.0-rc.7 five-validator full GenVM regression** for the same committed compact contract was initiated at <https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38790911152>. This audit note makes no claim about its result until it completes.

**Stage 7 remains OPEN / NOT PRODUCTION SAFE.** Do not fund `0xf11c3eBa500755F408Eceb16A9c79e724a596e95` again: its private key was never saved and vanished when the Windows process exited, as the user instructed. Do not submit a new signed deal or claim escrow funds are held or refunded. Further live funding is not requested. Only isolated test/audit branches were changed, not `main`, no PR or Portal submission.


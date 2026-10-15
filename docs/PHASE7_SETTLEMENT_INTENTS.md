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

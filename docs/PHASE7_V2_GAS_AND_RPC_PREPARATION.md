# Phase 7: Bradbury gas and RPC preparation

Status snapshot: 2026-10-17. These are read-only estimates for Bradbury chain ID 4221, not signed or broadcast transactions. The v2 source was pinned at SHA-256 `abe10708f56f68f389a440321122c43a8753853e595a3ebd337cfc29978cfc61` (16,681 bytes).

## Live unsigned gas probe

Unsigned gas units were observed at EVM block 25,341,401. A fresh RPC read at block 25,342,238 returned base fee 116,024,300 wei; fee caps below are recalculated at base fee + 2,000,000,000 wei priority fee (2,116,024,300 wei/gas). `eth_call` verified the padded budgets at the estimate block. Estimates have at least 10% / 1,000,000 gas headroom and are rejected above the 15,900,000 Bradbury safe ceiling.

| Operation | Estimated gas | Gas cap used | Maximum fee at sampled price |
| --- | ---: | ---: | ---: |
| v2 Intelligent Contract deploy | 14,222,029 | 15,644,232 | 0.03310358 GEN |
| Solidity payout router deploy | 317,232 | 380,679 | 0.00080553 GEN |
| v1 create deal | 1,086,649 | 2,086,649 | 0.00441540 GEN |
| v1 propose cancel | 867,658 | 1,867,658 | 0.00395201 GEN |
| v1 confirm cancel | 867,658 | 1,867,658 | 0.00395201 GEN |
| v2 configure router | 891,917 | 1,891,917 | 0.00400334 GEN |
| v2 create deal | 1,086,649 | 2,086,649 | 0.00441540 GEN |
| v2 submit evidence | 1,035,475 | 2,035,475 | 0.00430711 GEN |
| v2 assess | 820,751 | 1,820,751 | 0.00385275 GEN |
| v2 settle | 820,751 | 1,820,751 | 0.00385275 GEN |

The maximum-fee column is a cap using the sampled base fee plus 2 gwei priority fee, not a prediction of actual paid gas. The provider returned a 100,000,000 block gas limit. Legacy parent writes are estimated through the pinned SDK ABI and official Bradbury EVM endpoint; calls are simulated without signing or broadcasting.

## GEN budget requested for live execution

The sampled maximum-fee caps for all listed first-attempt operations total 0.06665988 GEN. One full v2 redeploy raises that to 0.09976346 GEN. Applying 25% headroom plus 0.005 GEN child/correction reserve and 0.0002 GEN for two possibly simultaneous deposits gives a 0.12990432 GEN modeled budget. Request 0.15 TEST GEN total, split across two fresh temporary signers:

- Buyer/deployer: 0.13 GEN. Covers v2 deployment, router deployment, buyer-paid parent writes, one v2 redeployment allowance, 0.0002 GEN test principal (refund proceeds may be reused), and about 20% margin for gas movement and one or two corrections.
- Seller: 0.02 GEN. Covers v1 mutual-cancel confirmation and v2 evidence submission, plus one retry and gas margin.

This is a budget, not a promise to spend all of it. The 0.005 GEN subset is held as child-delivery / correction contingency; uncertain protocol fees and external child gas are not assumed to be zero. Recheck live balances and fee estimates before each signed action. Do not use a different address or an old key.

## GenLayer read path and 403 diagnosis

Reads use the pinned `genlayer-py` Bradbury chain definition (`rpc-bradbury.genlayer.com`) and `gen_call` with the contract address, SDK-encoded calldata, `type=read`, and `status=finalized`. `tools/phase7_live_sdk_reads.py` exercised `deal_count`, `get_ledger(0)`, `get_deal(0)`, and `get_transfer_intents(0)` against the deployed Ghost; it completed with normalized result types and SHA-256 digests, without printing user data. The v0.2.16 method-dispatch and legacy response-envelope adapters remain narrowly pinned.

GenLayer JSON-RPC (`gen_*`) and Bradbury EVM JSON-RPC (`eth_*`, `https://rpc.testnet-chain.genlayer.com`) are separate services. The latter is used only for EVM estimates, simulations, balances, and receipts; it is not a substitute for GenLayer contract reads. A 403 from one egress path is an access-layer rejection, not evidence that the SDK read path or contract failed. The approved alternatives are the official Bradbury GenLayer RPC through an allowed network path, the official GenLayer CLI using the `testnet-bradbury` profile, or an authorized provider endpoint. No proxy or access-control bypass is used.

## Verification limits

The gas probe does not sign, deploy, or spend GEN. Local pytest/GenVM/Studio runs are separate from live-chain proof. A future signed test succeeds only after a GenLayer parent is `FINALIZED` successfully and, for a transfer, the child transaction, router event, recipient balance delta, receipt, and 12-block confirmation are independently matched.

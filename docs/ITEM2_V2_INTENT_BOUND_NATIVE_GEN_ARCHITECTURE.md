# SemanticEscrow — Item 2 genuine native GEN payout attribution, v2

## Why merely running the old 469 tests did NOT finish Item 2

The original live Bradbury v0.2.16 escrow emits value to an EOA with
`Au(Address(recipient)).emit_transfer(value=u256(D))`. The external
message then contains only an EVM recipient and amount. The original
`intent_id_sha256` is in the **GenVM escrow state**, not in the
**EVM calldata or event**. Multiple separate deals can pay the same
recipient the same wei amount. Thus no offchain heuristic (including
matching amount+address+time) can establish an authentic one-to-one link
for every native GEN transfer from that *already deployed* source.

Simply editing its local source would **not** update the existing immutable
IC. Re-deployment is necessary for a provable future payout link.

## Source-preserving v2 candidate built on isolated branch

Branch `feature/intent-bound-gen-payout-v2-20261016`.

- `contracts/semantic_escrow_attributed_v2.py`: a **new** IC source,
  derived from the exact original v0.2.16 deployed source. It retains
  all of the existing deal, dispute, settlement, and SHA-256 commitment
  rules but uses a linked EVM payout router instead of directly sending
  GEN to an EOA. The original `contracts/semantic_escrow.py` has not
  been touched and remains pinned to SHA-256
  `ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70`.
- The v2 administrator must explicitly configure a payout router once.
  `configure_payment_router` requires the IC deployer, cannot be
  repeated, and verifies the EVM router's immutable `escrowGhost`
  equals the IC's Ghost and `expectedChainId` equals chain 4221.
  `create_deal` blocks all native GEN deposits until configuration is
  verified.
- On settlement it computes the **exact** existing SHA-256 transfer
  intent from frozen `terms_digest_sha256,deal_id,milestone_index,kind,
  recipient,amount_wei`, and emits an external EVM message:
  `router.disburse(bytes.fromhex(intentId),Address(recipient))`,
  `value=u256(amount)`, on protocol finalization.
- `contracts/evm/SemanticEscrowNativePayoutRouter.sol` is a new
  Solidity 0.8.24 contract constructor-bound to the specific approved
  Ghost and chain. Its `disburse(bytes,address)` accepts **only**
  authenticated Ghost calls, validates exact 32-byte intent bytes,
  blocks the zero address and malformed/zero-value payments, marks
  `delivered[bytes32(intentId)]` before any external call, reverts
  atomically on failed recipient transfer, and emits indexed
  `NativeIntentPaid(intentId,recipient,ghost,amountWei)` **only after**
  EVM transfer succeeds. Replay of the same intent can never pay twice.
- `tools/v2_attributed_payout_proof.py` correlates actual RPC inputs:
  final successful GenLayer parent receipt, its **external (0)**
  message's exact router calldata + value, immutable escrow onchain
  intent commitment, source-pinned EVM router bytecode, executed
  non-reverted transaction, indexed event, router replay marker, 12
  confirmations and EOA balance difference.
  Public RPC callbacks must independently query the chain. A JSON
  fixture or a self-selected expected bytecode hash is **not** an
  authenticated real-chain proof.

## Why the address-only matching problem is resolved in v2

The EVM log carries the precise onchain intent SHA-256 as an indexed
topic. The router can emit that event only in the *same nonreverting*
EVM transaction as native GEN value delivery, and only after being called
by the EVM Ghost. Its bytecode and bound Ghost must be independently
attested, and the parent transaction's finalized external message
contains those very same 32 bytes in signed/consensus data.

Two separate deals with same recipient and wei create **different**
intent IDs. An unrelated payment cannot mimic both the approved
Ghost and verified router bytecode. Missing/malformed parent, mismatched
intent, duplicate message, router bytecode drift, EVM revert, wrong
beneficiary or incorrect balance delta all **fail closed**.

## What the tests mean, and what they do not

GitHub CI `.github/workflows/v2-attributed-payout.yml` re-runs the
earlier 469 historical tests and compiles/lints the independent GenVM v2
source with the pinned v0.2.16 runner. It installs fixed Solidity
compiler `solc-js@0.8.24`, then runs an **actual in-memory Ethereum
Virtual Machine** using `py-evm` / `eth-tester`. The tests verify:
- a genuine native wei transfer changes an EOA balance;
- the receipt contains the exact indexed SHA identity;
- replay cannot pay twice;
- wrong caller, zero amount, wrong chain, zero recipient or bad intent
  are rejected;
- recipient revert rolls back both EVM state and event;
- an independent verifier binds a mock finalized parent message's exact
  dynamic bytes calldata to the real locally executed EVM transaction;
- fake successful parent, forged intent, wrong bytecode pin, incorrect
  event/transaction/reorg, insufficient confirmations and bad balances
  cannot pass.

**A local simulated GenLayer parent is not a real Bradbury parent**, and
the EthereumTester chain ID is not Bradbury 4221. Therefore even a green
CI does **not** prove that a new payment has already been sent on Bradbury.

## Mandatory deployment order — not executed without explicit rollout

1. Let the existing real Phase-7 Windows session complete; preserve all
   its GEN/escrow logs and **do not change its deployed v1 contract**.
2. Deploy **new** immutable v2 SemanticEscrow intelligent contract on
   Bradbury, using the already validated v0.2.16 runner with the correct
   outgoing `method` key in the Python SDK. Wait for a real
   `FINALIZED + FINISHED_WITH_RETURN` result and verify exact source hash.
3. Deploy the Solidity native payout router on Bradbury, constructor
   parameters: **new v2 IC Ghost address** and **4221**. Record the
   actual deployed runtime bytecode SHA-256 and construction event/receipt
   from a trusted canonical EVM RPC.
4. From the **same deployer** as Step 2, invoke
   `configure_payment_router(routerAddress)`, check GenLayer finality.
   Contract checks the real router's Ghost and chain.
5. Only now create one low-value **Bradbury TEST GEN** deal from a
   durable controlled signer and settle it. Verify the frozen
   onchain `get_transfer_intent`, FINALIZED parent message, exact
   EVM `disburse` payload, canonical EVM receipt, indexed
   `NativeIntentPaid` and EOA balance at the receipt block.
6. Try a duplicate of the same ID in a local EVM test (already run), not
   with live value. Do **not** submit paid duplicate attempts to
   Bradbury merely to prove protection.
7. Deploy to production or merge `main` **only after** additional
   security review and the user's separate explicit authorization.

## Unresolved independent risks

- This v2 solves unique **payout attribution**; it does NOT solve
  stranded funds following a failed GenLayer external/child message.
  The separate child recovery audit still blocks blind refunds/retries.
- There has been **no new onchain v2 router/IC deployment or Bradbury
  payout** in this audit. The current v1 live test cannot retroactively
  produce v2 intent-indexed transfer events.
- EOA historical B-1/B balance deltas can be affected by unrelated
  transfers in the same block. The verifier conservatively refuses
  ambiguous blocks rather than guessing or falsely claiming delivery.
- Official GenLayer external messages are executed only on finality
  via Ghost `handleOp()` and are not the same as internal child GenLayer
  transaction IDs.

Official protocol references:
https://docs.genlayer.com/developers/intelligent-contracts/features/messages
https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
https://docs.genlayer.com/developers/intelligent-contracts/features/interacting-with-evm-contracts
https://docs.genlayer.com/api-references/genlayer-node

## Final verified test evidence (16 October 2026)

The latest complete GitHub Actions workflow:
https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38959318830

**534/534 tests passed (completed/success)**:
- 1 legacy API + 153 original Direct Mode + 12 legacy receipt +
  83 SDK safety + 220 payment/incident correlation regression;
- 52 new Solidity EVM + intent-bound receipt tests;
- 13 actual pinned GenVM v0.2.16 constructor/permission and
  method-dispatch adapter tests (2 new Direct Mode + 11 SDK adapter tests).

The EVM tests use an actual in-memory EVM execution backend and
compile Solidity 0.8.24 bytecode. Old IC source SHA, compilation,
pinned GenVM lint and pip dependency check also passed. The
v2 GenVM Direct Mode uses v0.2.16 official SDK source emulation;
it does NOT include a real EVM Ghost implementation.

Earlier candidate CI runs found and corrected: wrong Web3 HexBytes hash
format, non-checksummed address input for historical RPC reads,
missing transaction receipt rejection, and **v0.2.16
EVM contract-interface parameters requiring positional-only (/)
annotations**. The final passing run above supersedes these failures.

### Operational status / release boundary

**The source/code-level v2 fix and local cross-layer verification
engine are complete, not the Bradbury deployment.** New v2 Ghost and
EVM router must actually be deployed and one test GEN payout finalized
before signing off an *end-to-end live* Item 2. No new test wallet,
testnet GEN transaction, contract/gas expenditure, PR, merge,
Portal redeployment or Vercel deployment was performed. The ongoing
Phase-7 original Windows test remains untouched.


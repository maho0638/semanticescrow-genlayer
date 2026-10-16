# SemanticEscrow — isolated next-release audit (16 October 2026)

> **Original Phase 8 definition NOT RECOVERED.** The project's 2026-10-16
> handoff explicitly states that the original nine-stage roadmap's full
> Phase 7, Phase 8 and Phase 9 headings and acceptance criteria are missing.
> This scoped effort audits the known **unresolved release risks**, but must
> **not** be advertised as completion of the lost original Phase 8 spec.

## Isolation and immutable source

- Branch: `audit/phase8-release-gates-20261016`, based on the *unchanged*
  Phase-7 `560d1d00bdd81df36da708ede49096fbeb80ebd6` commit.
- `main` and the currently running Windows Phase-7 test branch were not
  modified by this audit; no PR, merge, Portal submission, deployment or GEN
  transfer was made.
- The released/tested `contracts/semantic_escrow.py` remains source-pinned
  to SHA-256 `ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70`.
  Modifying the signed Intelligent Contract source would invalidate the
  deployed Bradbury runtime/source attestation, so this audit adds **only
  offchain tools, tests and documentation**.

## Completed technical audit work (precisely scoped)

### 1. Cryptographic intent and ledger reconciliation (read-only)

`tools/phase8_release_gate.py:reconcile_queued_intents` checks:
- exact ledger field set and `initial_deposit = remaining_locked +
  payout_queued_total + refund_queued_total`;
- canonical decimal u256 wei with no negatives/leading zeros;
- exact SHA-256 intent commitment for frozen `deal_id`, milestone, kind,
  recipient, amount and original terms digest, with the actual onchain JSON
  serializer (`sort_keys=True, separators=(',', ':'), ensure_ascii=True`);
- buyer-only REFUND and seller-only PAYOUT, one terminal refund, strict
  milestone ordering, no post-refund payout, zero-value or duplicate intents;
- sums of all queued intents equal the ledger's queued payout/refund totals;
- any forged `credited`, `delivered`, `FINALIZED` or additional field is
  rejected. **Valid queued intent does not attest beneficiary credit.**

### 2. Conservative Ghost native-GEN transfer observation

`tools/phase8_ghost_public_probe.py` is restricted to read-only public
Bradbury EVM methods; it accepts an independently recovered signed child /
finalization EVM transaction ID and a separately read frozen intent row.

The observer checks:
- chain **4221**, mined transaction and receipt identity, `status=1`;
- canonical EVM block hash and at least **12 confirmations**;
- Ghost → frozen beneficiary **internal CALL** with exactly the claimed wei,
  no EVM trace errors or duplicate matching calls;
- historical beneficiary balance from EVM block `B-1` to `B` changes by
  the expected wei amount. A shared block can contain other transactions, so
  a mismatch is **unverified**, not permission to repeat a payment;
- `debug_traceTransaction` / callTracer support **cannot be assumed** on
  Bradbury; unsupported/missing trace fails closed.
- A direct `receipt.to == beneficiary` rule is not used: official GenLayer
  docs specify Ghost `handleOp` forwarding for external messages.

**Critical limitation:** This confirms at most an *observed Ghost value CALL
that is not attributed to the particular transfer intent*. Separate deals
can send identical recipient/wei amounts, and `intent_id_sha256` is not an
onchain child transaction identifier. The result is deliberately
`GHOST_VALUE_CALL_OBSERVED_UNATTRIBUTED` with
`delivery=UNVERIFIED_FOR_SPECIFIC_INTENT`. It NEVER emits `PAID`,
`CREDITED` or `RELEASE_APPROVED`. These checks do not establish the
actual failure-recovery semantics of a failed external message.

The tool **does not submit**, sign, fund, send, retry or "rescue" transactions,
nor does it read local wallet secrets. It never connects to an untrusted
public proxy; the public RPC address is hardcoded. Supported use, after a
newly identified finalized transfer transaction and read-only intent:

```powershell
# Read-only only. Not needed while the current Phase-7 test is running.
python tools/phase8_ghost_public_probe.py --intent-json intent.json --ghost 0xYOUR_VERIFIED_GHOST --evm-tx 0xYOUR_VERIFIED_EVM_TX_HASH
```

### 3. Irreversible RELEASE_BLOCKED policy

`release_gate` refuses production approval from unchecked user-provided
status booleans, even if a JSON payload says every security check passed.
It requires independent human/deployment signoff not obtainable by this
standalone script. It never authorizes a blind GEN resend or refund retry.

## Verification and evidence

CI workflow `.github/workflows/phase8-release-gates.yml` on this audit
branch runs the full previously passing **249** legacy-v0.2.16 offline tests
plus new adversarial reconciliation/EVM trace tests. All tests use mocks or
local Direct Mode; no onchain GEN is spent. Linter, contract-source SHA pin
and Python compilation are asserted.

**Final verified CI:** https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38882846009
— `completed/success`, **326/326 tests passed**, comprising 1 legacy web
probe + 153 Direct Mode + 12 old receipt checks + 83 SDK/safety checks +
**77 new release/trace adversarial checks**. Pinned contract SHA-256 check,
Python compilation and GenVM lint also passed. Previous 62-test version:
https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38882562182.

These new 77 are mock/offchain verification-policy tests, NOT 77 new signed
Bradbury transactions, and do NOT establish real refund credit.

## Release blockers — not fixed / no release permission

1. **Unknown original Phase 8 acceptance checklist.** Actual scope cannot
   be declared fully finished without the original task definition.
2. **Independent intent → real child EVM transfer binding.** Event, trace,
   unique intent and recipient credit attribution for a real case are still
   required. Merely detecting a Ghost CALL is not enough.
3. **Failed-child transfer safe recovery.** Official GenLayer docs warn that
   failed child-message value is not automatically returned. There is no
   chain-proven, duplicate-safe recredit/refund/retry mechanism here.
4. **Real DNS/redirect/private-IP egress.** String host parsing is *not* a
   network access policy, and arbitrary remote HTML/redirect safety depends
   on actual GenVM egress/provider behavior. This requires execution-boundary
   restrictions or verified network gateway/SDK semantics, plus SSRF tests.
5. **Evidence authenticity and model independence.** Different hostnames
   are not independently controlled source publishers; mocked LLM validators
   do not certify honest independent real-world source judgments.
6. **Independent external security audit and production mainnet readiness.**
   Neither was performed. Real-value escrow remains **NOT SAFE CERTIFIED**.

Official docs:
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/intelligent-contracts/features/messages
- https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/finality
- https://docs.genlayer.com/developers/decentralized-applications/writing-data

**Stop boundary:** This isolated audit does not interrupt the running Phase-7
Windows process or claim Phase-7 beneficiary credit. Once its live trace and
refund data arrive, reconciliation can be performed without replaying the
old settlement or risking double payment.

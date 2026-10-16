# SemanticEscrow — child GEN delivery failure and safe retry guard

Date: 2026-10-16. Branch: `audit/child-delivery-recovery-guard-20261016`.
Scope: **first independent remaining security item after the ongoing Bradbury
7th-stage signed payment/cancel/refund session**.

## Network facts verified from the official 2026 GenLayer documentation

- An outbound **external** EOA GEN payment is an external message from an
  Intelligent Contract through its EVM ghost `handleOp()`, processed **only
  when its parent reaches FINALIZED**. An emitted message or finalized parent
  is **not** the same as recipient credit.
- GEN carried in a child message is withheld from the sender and
  **NOT automatically returned on failed child execution**.
- An EVM child value transfer observation is **not bound automatically**
  to the contract's separate `intent_id_sha256` commitment.
- No chain-attested, contract-callable exactly-once **failed external value
  recovery API** has been established for this specific pinned v0.2.16
  deployment. Blind resends can double pay.

Sources:
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/intelligent-contracts/features/messages

## Implemented, isolated code

- `tools/child_delivery_recovery_guard.py` is an **offchain only**
  `ChildIncidentJournal` and no-send decision controller; writes exclusively
  to a **LOCAL** SQLite WAL database with `synchronous=FULL`, atomic
  transactions and uniquely keyed frozen intent commitments.
- It only accepts transfer-intent rows after the Phase-8 reconciler checks
  chain ID 4221, address/amount/terms hash/recipient, strict canonical wei,
  committed SHA-256 intent IDs, exact ledger totals and correct buyer/seller.
- An existing intent ID cannot be overwritten using a different ghost,
  parent GenLayer transaction ID, address, amount or ledger commitment.
- Re-registering the exact same data is idempotent across process restarts.
  Event deduplication is keyed by intent, type and evidence digest.
- A reported failed child ID and evidence digest are **incidents to review**,
  not proof that value was refunded or safely available for retry.
- A mocked or retrieved Ghost CALL is subject to the earlier Phase-8
  receipt, onchain block, confirmation, exact internal transfer value and
  beneficiary balance checks. Even passing returns **unattributed only**,
  and cannot be proof of delivery to this particular intent.
- The journal provides `authorize_retry` and `authorize_rescue` denial
  methods which **always raise** `RecoveryForbidden`; no signing or
  transaction-broadcast route exists in this module.
- Append-only logical event hashes detect **accidental local corruption**,
  but **DO NOT** prevent a privileged local attacker from rewriting all DB
  contents: hashes are **not digitally signed/anchored**.
- `tools/child_delivery_incident_cli.py` provides offline
  `register`, `reported-failure`, `status`, and `audit` commands;
  it reads JSON exported by an operator; such JSON **must be authenticated
  separately against trusted onchain state**. It does not access private
  wallets, submit EVM calls, send GEN, or offer manual retry authorization.
- The prior real contract source SHA-256
  `ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70`
  and its currently running Phase 7 test branch are unchanged.
- Extensive offline adversarial tests cover repeated use, frozen snapshot
  conflicts, wrong amounts, wrong beneficiaries, duplicate matching EVM calls,
  missing confirmation, malformed TX IDs, replay, restart, invalid status,
  no-resend, and accidental event tampering.

## Practical local use (after exporting independently verified public data)

Save a **public-only** JSON envelope containing exactly:
`chain_id,ghost,parent_genlayer_tx,ledger,rows,deal_id,buyer,seller`.
Never include a mnemonic, key, password, login cookie, or wallet JSON.

From this branch's repository root (no network needed):

```powershell
python tools/child_delivery_incident_cli.py --database escrow_incidents.sqlite register --input public-onchain-intents.json
python tools/child_delivery_incident_cli.py --database escrow_incidents.sqlite status --intent YOUR_64_HEX_INTENT_ID
python tools/child_delivery_incident_cli.py --database escrow_incidents.sqlite audit
```

The output deliberately says `SE_CHILD_VALUE_RECOVERY_UNVERIFIED_NO_RETRY`.
Do not use this journal file itself as a valid payout receipt.

## Limits — DO NOT misrepresent as complete financial recovery

This is **a tested fail-closed offchain control and incident response**,
**not** a deployed onchain child-recovery smart contract. Neither the existing
Bradbury deployment nor the ongoing Windows signed runtime was altered.
The module does NOT:
- recover value stranded after a real failed external child message;
- prove which child belongs to a specific `intent_id_sha256`;
- prove another entity/operator has not paid onchain already;
- authorize GEN retries or satisfy real-value custody safety controls;
- auto-enforce at every independent signing channel or third-party wallet.

**Final unresolved integration:** obtain official authenticated
GenLayer-child ↔ parent ↔ intent ↔ Ghost-EVM receipt linkage and a separately
audited protocol-supported compensation method. Until then, the correct
default is **STOP, READ, DOCUMENT, NEVER AUTOMATICALLY RESEND**. The live
Bradbury test needs to finish and produce independent escrow beneficiary
balance proof. Owner production deployment approval and external security
audit are separate tasks.

## Test status

The existing 368 historical Stage-9 regressions and new offline test
cases run in `.github/workflows/child-delivery-recovery-guard.yml`.
Do not report the final test count or an overall PASS until the latest
workflow run is completed/success. The first new workflow run failed from
a SQLite placeholder-count error, which was corrected before re-running.

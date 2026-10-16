# SemanticEscrow Phase 7 — create_deal GenVM error root cause investigation (2026-10-16)

## Status: ROOT CAUSE NOT YET PROVEN; NO CODE FIX AUTHORIZED

The scoped objective is **only** to find and eliminate the underlying
Bradbury `create_deal` GenVM error, not deploy / do a new payable test
blindly. The original live escrow source and its prior 250 tests have NOT
been changed.

## Independent public chain findings

- Bradbury consensus `FINALIZED`, execution vote `FINISHED_WITH_ERROR`:
  `0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06`.
- EVM `status=1`, txn hash
  `0xa8ea226dc7cce9dd9265c400198d08673774b4ebdf31f40171ac3e6d491441a4`.
  Success at this EVM level DOES NOT override GenVM failure.
- Actual L2 ConsensusData `getTransactionAllData` stores a 299-byte
  RLP envelope whose inner 292-byte GenVM payload decodes as a dictionary
  with an empty-string method-dispatch key and `args` of length 3:
  - `create_deal`;
  - seller `0x1B57202109aB62Bfe04ae8F3a9A0B8E0053612dA`;
  - one milestone with exactly the required fields, amount
    `100000000000000` wei and future deadline `1792315577`;
  - buyer nonce `phase7-live`.
- The separately stored native transaction value is also
  `100000000000000` wei. **This proves transport/signer/consensus value
  matches the requested amount, but does NOT prove GenVM's
  `gl.message.value` was delivered correctly to the running contract.**
- The actual onchain binary calldata SHA-256 is
  `262ffce30179f612b8ad127d0972cb1569c4aaaf8fb0a8663bc0917d3abc248f`.
- EVM and consensus data include no definitive source-line traceback.
  A runtime `UserError` (e.g. exact-value invariant) and validator
  VM/runner/storage failures cannot be distinguished from those receipts
  alone. No unsupported root-cause claim should be made.

## Official full GenVM debug API and blocker

Per https://docs.genlayer.com/api-references/genlayer-node/debug/gen_dbg_traceTransaction
the public JSON-RPC method is:

```json
{"jsonrpc":"2.0","id":1,"method":"gen_dbg_traceTransaction",
 "params":[{"txID":"0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06","round":0}]}
```

Bradbury's GenLayer RPC endpoint
`https://rpc-bradbury.genlayer.com` returned **HTTP 403** to every
GitHub-hosted CI attempt, including `gen_dbg_ping`,
`gen_getTransactionStatus` and `gen_dbg_traceTransaction`.
This is public-rpc access control, not a confirmed GenVM failure class.
Do not claim the root cause was found by this attempted RPC.

The already working Windows PowerShell RPC bridge uses the user's **local
Windows network**, where Bradbury `eth_*` calls previously succeeded.
The new `tools/phase7_genvm_trace_windows.py` uses that same local
loopback bridge with a hardcoded public upstream to query two known IDs.
It **does not read any account secrets, send transactions, spend test GEN
or generate a new wallet**. It redacts arbitrary trace strings before
printing. Its complete result is indispensable if the RPC endpoint exposes
the debug method on the user's Windows network.

### Needed user action (only if willing to supply the final missing proof)

From a separate PowerShell window:

```powershell
cd C:\\Users\\kabus
git clone -b fix/phase7-create-deal-root-cause-20261016 --single-branch https://github.com/maho0638/semanticescrow-genlayer.git SemanticEscrow-Diagnostic
cd SemanticEscrow-Diagnostic
python tools/phase7_genvm_trace_windows.py
```

If `python` is not recognized, use `py`. This script requires the
`requests` module already used by the Windows runner. Return only the
`SE7_TRACE_...` output, NOT wallet keys, private environment files or
arbitrary login details.

If Bradbury refuses `gen_dbg_traceTransaction` even from Windows
(`-32601`/403/debug-disabled), an authorized node operator / validator
must supply the GenVM log to establish the actual cause. Local Direct Mode
simulations or RLP decoding cannot prove a particular remote runtime
exception in that case.

## Tests and safety

- Read-only GitHub investigation:
  https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38888711294
  confirmed exact calldata envelope and amount.
- The Windows forensic script has offline regression tests for output
  sanitation, redaction, and accurate separation of successful, user-error
  and VM-error traces.
- No live user funds or test GEN were spent; no new payable call or
  `main` change, PR/merge, Portal or Vercel deployment happened.
- Existing Stage-7 funded runner remains halted after the previous real
  GenVM failure. Do not remove that halt or request any new test GEN before
  a trace-driven candidate passes exact pinned-runner Studio validation.

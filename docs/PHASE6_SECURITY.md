# SemanticEscrow — PHASE 6 evidence and consensus security (2026-10-15)

**Status:** Direct Mode, full historical regression and pinned GenVM lint **PASS**. Independent full five-validator local Studio poisoned-source/timeout-refund verification **pending final GitHub result**. This is NOT a mainnet audit or a claim that arbitrary evidence URLs can never reach private IPs, that AI cannot be tricked, or that final EVM beneficiary credit is proven.

## Scope and immutable source

- Repository: https://github.com/maho0638/semanticescrow-genlayer
- Isolated branch: `audit/phase6-evidence-validators-20261015`. `main` unchanged.
- Last verified Direct Mode financial and dispute regression: **142/142 PASS**, GenVM semantic lint **3/3**, original design invariants 18,203, abstract ledger scenarios 2,000: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38709393039
- Real five-validator malicious-source run: https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38709210875 (final result must be checked and attached; no pass until GitHub job completes)
- Phase-3 through Phase-5 local Studio consensus and money intent evidence remains recorded in `docs/PHASE3_VERIFICATION.md`, `docs/PHASE4_PAYMENT_SECURITY.md` and `docs/PHASE5_DISPUTES.md`.

## Stage-6 technical changes

1. **URL robustness:** Known IP-embedding DNS services (`nip.io`, `sslip.io`, `xip.io`, `lvh.me`, `localtest.me`, `traefik.me`, `localhost.direct`) are excluded for both original and appeal source manifests. The parser already rejects HTTP, explicit ports, IPv4/IPv6 authority syntax, embedded credentials, encoded paths, double slashes, dot-segments and unsafe controls. Domain uniqueness is canonicalized and SHA-256 fingerprints cannot repeat.
2. **HTTP integrity:** A complete HTTP **200** response is now necessary for a source to count as verified. Partial-content (206), alternate 2xx and redirect/error statuses cannot support payout. 408, 425, 429 and 5xx are classified as temporarily unavailable and may be retried. Response bytes are checked before UTF-8 decode and model use, bounded to 1–6000 bytes. An unchanged URL whose response body has changed fails hash verification.
3. **Human review input:** Directionality overrides and invisible formatting controls are refused in terms and challenge reasons. Even if an external verified text includes invisible controls, the model's prompt renders them as visible escaped codes. XML-delimiter-like malicious text is entity-escaped and enclosed in `<untrusted_evidence>` framing. This mitigates some prompt-construction attacks but **does not prove an AI model cannot be injected**.
4. **AI output:** Strict JSON with one `labels` array, exactly matching rubric size, and only `PASS`, `FAIL`, `UNKNOWN` is accepted. Extra keys, duplicate keys, malformed syntax, NaN, booleans and wrong label counts reject the assessment without triggering any transfer.
5. **Validators:** An independent validator recomputes both source HTTP-byte digests, observation status and frozen rubric labels. Modified source bytes, HTTP status or model judgment are rejected; agreement based only on the leader's output shape is not counted as consensus. Repeatability across real independent unmocked publishers/models **not proved**.
6. **Financial fail-safe:** No application assessment that is unknown, invalid or under the minimum two verified-source threshold can release GEN early. The hard-coded review timeout permits third-party-triggered refund of unqueued deposit, not a claim of recipient credit.

## Executed regression samples

The 142 passing Direct Mode tests include all 63 Phase-5 tests and roughly 79 additional parametrized malicious-source and parser cases. New cases cover 10 known dynamic DNS origins, 17 syntactically ambiguous/bogus URLs, seven bidirectional/invisible formatting variations, 13 non-200 HTTP statuses, seven retryable HTTP statuses, 13 corrupted LLM output envelopes, exact 0/1/6000/6001-byte response boundaries, changed-content hash mismatch, duplicate host/digest commitments, forged XML-delimiters and autonomous validator disagreement. Tests use mocked data. Passing them is **not** proof the actual GenVM egress layer refuses every redirect or DNS rebinding.

## Critical unresolved production hazards

**GATE A — SSRF/DNS/redirect network policy.** These parser-level exclusions cover only known public services. A custom public domain can resolve to a private address, change DNS between validators, or issue a redirect; the pinned Python `nondet.web.get` response API here has not been shown to expose the redirect destination or actual resolved IP. Production requires network-layer resolver/IP/redirect safety controls, tests with controlled redirect/DNS servers and independent verification of the GenVM web module settings. We do not claim A is solved.

**GATE B — Source truth and AI prompt injection.** SHA-256 proves content immutability relative to the submitter commitment, **not author identity, independent publisher ownership or semantic truth**. Two distinct domains may share an owner. Contract-level escaped prompt framing and 3-validator quorum reduce some risk but cannot guarantee model safety. Live hostile-model/provider tests and publisher provenance evidence remain necessary.

**GATE C — Actual native GEN payout/refund delivery.** GenLayer documents that value-bearing child message failures do not automatically restore value, and Studio simulates balances without EVM Ghost contracts. A `PAYOUT_QUEUED` or `REFUND_QUEUED` ledger transition, or `FINALIZED` parent transaction, is not beneficiary EVM credit. Failed external transfers cannot be blindly retried without risking double-payment. Actual receipt/credit verification and a proven safe recovery policy remain **production blockers**.

**GATE D — Public deployments, independent audit, economic model.** No external/hosted five-validator LLM-provider diversity, real signed Studio Dev/mainnet/Bradbury production money movement, third-party security review, realistic fee and gas failure simulations or untrusted EVM receiver failure-recovery proof was performed at this stage.

## Boundary and stopping point

No change to `main`, no PR merge, no public deploy, no GenLayer Portal submission and no real GEN spend or user wallet secret. The stage only adds deterministic source guards, adversarial tests and one disposable local five-validator Studio scenario. Stage 7 is outside this work and MUST NOT start without an explicit new command.

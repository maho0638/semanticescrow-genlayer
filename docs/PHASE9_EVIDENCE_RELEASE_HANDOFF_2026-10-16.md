# SemanticEscrow — isolated Phase 9 readiness / evidence handoff (2026-10-16)

## Scope truthfulness

**The original nine-stage development plan's exact Stage 9 title, tasks and
acceptance criteria were NOT preserved.** They were searched in the available
handoff and repository; they cannot be inferred from a numbered phase.
Accordingly, this is a **self-contained scoped Stage-9-adjacent release
readiness handoff**, not proof that all requirements of the lost original
Stage 9 were fulfilled.

## Completed without affecting Phase 7 live test

- Branch `audit/phase9-evidence-release-20261016` created from the
  separately audited Stage 8 commit `f15fce1207eddaf426b7162861c3b18faee148c4`.
- `main`, `test/phase7-bradbury-runtime-compat-20261015` and
  `audit/phase8-release-gates-20261016` remain unchanged. No PR/merge,
  Portal submission, mail access, production deployment, live wallet, or GEN
  spend occurred in this work.
- **Unchanged signed SemanticEscrow contract source**:
  SHA-256 `ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70`,
  **15,738 bytes**, # v0.2.16, exact
  `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.
  Contract Git blob (historical) `ce250b37decc7b833206b991b8f91dcb5af4746d`.
- `tools/phase9_release_packet.py` builds an **offline deterministic**
  JSON release-review handoff. It fingerprints the pinned deployed source,
  source schema binder, Bradbury existing-deploy checker, legacy receipt reader,
  Stage 8 queued-intent reconciler, and Ghost public read-only observer.
  It includes relevant Phase 7 and Phase 8 GitHub CI run references; these are
  historical evidence links, **not new onchain transactions**. The published
  GenVM archive digest is recorded as release-metadata evidence, **not**
  a validator-binary attestation.
- All approvals are **forbidden by construction** in the packet.
  `release_review.status=BLOCKED`; `escrow_real_money_authorized=false`,
  `production_deployment_authorized=false`,
  `automatic_child_resend_authorized=false`, etc. It explicitly records
  outstanding validation items.
- `verify_packet` rejects source drift, schema ABI binder drift,
  modified tool fingerprints, missing or changed release blockers, altered
  party/network or deployment IDs, fake refunds, fake signoffs, modified
  historical CI links, missing limitations and all forged release approvals.
  Even a self-recomputed hash cannot reclassify the packet from BLOCKED
  to READY: **a SHA-256 checksum is NOT a cryptographic signature**.
- `tests/test_phase9_release_packet.py` adversarially verifies the
  source pin, output repeatability, CLI generation, schema integrity,
  provenance anchors, forged-signed-then-rehashed payloads and attempted
  late changes to critical tooling.
- `.github/workflows/phase9-evidence-packet.yml` runs the full legacy
  regression, Stage 8 negative tests and new Stage 9 tests. All tests are
  offline/mock, with temporary local dummy identities only, plus pinned
  GenVM lint and compilation. After success it uploads
  `phase9-NOT-READY-handoff`, containing **no wallet key**.

## Confirmed test result

- **368/368 PASS:** 1 legacy web API + 153 functional Direct Mode + 12
  legacy receipt + 83 SDK/safety + 119 Stage 8 & Stage 9 audit tests.
- **Completed/success workflow**:
  https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38885168323
- GitHub Actions artifact `phase9-NOT-READY-handoff`, id
  `12039810393`, exists under that workflow. Artifact JSON SHA-256 internal
  checksum: `5be7d5603c6903d81313616b3d09cdede286967e7e088a3ade317b4b8b053576`.
  The archived file itself has an independent ZIP digest; these are
  integrity diagnostics, not endorsements or legal attestations.

**A previous initial CI run failed** because the new packet validator
mistakenly required 64 hex characters for a Git commit ID; actual Git SHA-1
commit IDs are 40 characters. This was corrected by separating
`GIT_SHA_RE` and `SHA_RE`. The first failed run is
https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38885040840 .
Only the later green run above proves the final tested implementation.

## Hard blockers and who can clear them

| Item | Current status | Responsible action |
| --- | --- | --- |
| Original Stage-9 original spec | **UNKNOWN** | Recover the actual initial nine-stage plan; until then do not label the original stage complete |
| Phase-7 live mutual cancellation + buyer refund | **NOT VERIFIED by this Stage-9 work** | Existing Windows test must produce actual signed outcomes and recipient value proof; no secret-key upload or blind replay |
| Independent intent-to-child proof | **NOT VERIFIED** | Contract protocol event/GenLayer child ID/EVM transaction binding with independent source and exact recipient/amount; Stage-8 merely flags unattributed Ghost internal calls |
| Failed child value recovery/double-pay prevention | **NOT DEMONSTRATED** | Needs protocol implementation evidence, safe idempotent claim/recovery design and adversarial test before real funds |
| DNS / redirect / SSRF egress policy | **NOT PROVEN** | Must be enforced and audited at real GenVM network boundary; contract string validation is not network egress proof |
| Independent publisher evidence / live model resilience | **NOT PROVEN** | Audit real external publisher identity and cross-validator/model behavior; mocked Direct Mode is not proof |
| Independent real-value security review | **NOT PERFORMED** | Independent external audit and explicit user production release authorization would be required |
| Main/Portal/prod rollout | **NOT AUTHORIZED AND NOT RUN** | Must remain blocked; no auto merge, deploy or submissions |

**Important constraints:** Bradbury GEN is testnet-only. Existing already
funded RAM wallet sessions must never be interrupted to generate audit data,
and never fund expired wallet addresses. The active Phase-7 test branch
must remain unchanged until its live test finishes, with no automatic resends.

## Proof the packet does and does not provide

The artifact is a deterministic **technical handoff**, cross-checking
repository source and the prior CI references. It is *not* signed by the
external network, a regulator, auditors or the user. It does *not*
authenticate a particular child transfer to a particular intent, certify
production egress, or prove beneficiary balance increased in the ongoing
live test. The Phase-9 work could not ethically manufacture any of those
claims.

## Stopping point

All technical tasks **within this explicitly limited proof-packet scope**
have been implemented and CI-tested; none of the external release blockers
or the unrecovered original Stage-9 specification has been misrepresented as
complete. Stop and await separate Phase-7 live evidence.

# SemanticEscrow — evidence-verified milestone settlement (architecture v1)

**Status: PHASE 1 ONLY — design specification, not a functioning contract.**

SemanticEscrow is a reusable **GenLayer Intelligent Contract primitive** for escrowed native GEN milestone payments. The buyer funds all milestones at creation; the seller submits independently fetchable evidence; GenLayer leader and validators independently evaluate the frozen acceptance rubric. A contract-level challenge can rerun judgment on supplemental evidence. Deterministic settlement either schedules a payout or refunds remaining locked money.

- [Architecture and API](docs/ARCHITECTURE.md)
- [Finite-state machine and timeout semantics](docs/STATE_MACHINE.md)
- [Independent validator and evidence rules](docs/CONSENSUS.md)
- [Threat model and safety gates](docs/SECURITY.md)
- [Architecture test matrix](docs/TEST_MATRIX.md)
- [Research and official sources](docs/SOURCES.md)
- [Turkish stage-1 handoff](docs/PHASE1_TR.md)
- [Machine-readable design contract](spec/phase1_design.json)

**No deployable source, no real balance movements, no Studio transactions, no CI pass claims.** Phase 2 (contract implementation) has **not** started. Public deploy, GitHub main promotion, and Portal submission require separate approval. This branch is intentionally isolated from the minimal main bootstrap.

Important limitation: the GenLayer consensus verdict, protocol transaction finality, queued external transfer, and a confirmed recipient transfer are **four separate facts**; a queued transfer is never advertised as money received.

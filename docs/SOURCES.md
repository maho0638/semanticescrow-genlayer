# Official documentation verified 2026-10-15

Sources are **external documentation**; spec rules and timeouts are local design decisions, not automatically endorsed by GenLayer.

1. [When to use GenLayer](https://docs.genlayer.com/developers/intelligent-contracts/when-to-use-genlayer): milestone escrow is a meaningful use case; evaluate non-deterministic evidence instead of just saving an LLM answer.
2. [Value Transfers](https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers): payable `gl.message.value`, `u256` native GEN, external value transfers to EOA, and **nonautomatic recovery of failed child value**.
3. [Messages](https://docs.genlayer.com/developers/intelligent-contracts/features/messages): internal vs external; `on='finalized'` safe timing; ghost holds GEN; Studio lacks live EVM layer.
4. [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle): independently rerun/review evidence, reject shape-only validator checks; docs illustrate `run_nondet_unsafe`, but the repository's exact pinned GenVM runner exposes `gl.vm.run_nondet` (proven by Studio), with independently rerun leader/validator closures.
5. [Non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism): isolate web/LLM nondeterminism from storage modifications and outbound messages.
6. [Transaction Context](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context): immediate sender identity and pinned deterministic transaction timestamp.
7. [Transaction statuses](https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/transactions/transaction-statuses): Accepted, Undetermined, Finalized refer to protocol state, not application truth.
8. [Fee outcomes](https://docs.genlayer.com/developers/decentralized-applications/fee-outcomes-and-debugging): transaction success requires accepted/finalized AND `FINISHED_WITH_RETURN`.
9. [Use cases](https://docs.genlayer.com/understand-genlayer-protocol/typical-use-cases): milestone payouts and freelance escrow.
10. [Optimistic Democracy](https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy): consensus vs contract appeals; source quorum != validator majority.

No claim is made that a hosted RPC supports each proposed implementation path until tested. Full mainnet security, source ownership, or token delivery is not established at design stage.

## Phase-6 supplementary current references

11. [Web Access](https://docs.genlayer.com/developers/intelligent-contracts/features/web-access): HTTP requests and status codes, but does not establish that contract-level URL regex enforces redirect/DNS egress safety.
12. [GenVM Configuration](https://docs.genlayer.com/validators/genvm-configuration): network module TLD and host allow/deny rules belong in validator-host web module config; need actual runtime validation.
13. [Prompt Injection](https://docs.genlayer.com/developers/intelligent-contracts/security-and-best-practices/prompt-injection): input restriction, output schema and contract guardrails are mitigations, not a mathematical guarantee that models resist a malicious prompt.
14. [nip.io / sslip.io operator documentation](https://nip.io/): dynamically resolve hostnames containing arbitrary IP addresses, so source names must not be assumed publicly routable solely from hostname syntax.

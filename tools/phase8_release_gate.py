"""Offline, read-only release-safety audit for SemanticEscrow's queued intents.

NOT the missing original 'Phase 8' roadmap. No RPC credentials, signing,
transfers, automatic retries, or claim that an intent proves beneficiary credit.

The canonical source contract serializes json.dumps(sort_keys=True,
separators=(',', ':'), ensure_ascii=True). Its intent commitment uses domain
SemanticEscrow.transfer-intent.v1 and the frozen deal/terms/recipient/amount.
"""
import hashlib
import json
import re

U256 = 2**256-1
RE_HEX = re.compile(r"^[0-9a-f]{64}$")
RE_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
RE_TX = re.compile(r"^0x[0-9a-fA-F]{64}$")
EXPECTED_LEDGER = frozenset({
    "initial_deposit", "remaining_locked", "payout_queued_total", "refund_queued_total",
})
EXPECTED_INTENT = frozenset({
    "deal_id", "milestone_index", "kind", "recipient", "amount_wei",
    "status", "terms_digest_sha256", "intent_id_sha256",
})

class EvidenceRejected(ValueError):
    """Untrusted or inconsistent evidence must NEVER authorize release/retry."""


def require(condition, message):
    if not condition:
        raise EvidenceRejected(message)


def wei(raw, positive=False):
    require(type(raw) is str and raw and raw.isascii() and raw.isdecimal(),
            "wei must be a canonical decimal string")
    require(raw == "0" or not raw.startswith("0"), "noncanonical wei")
    n = int(raw)
    require(n <= U256 and (not positive or n > 0), "wei out of range")
    return n


def address(raw):
    require(isinstance(raw, str) and RE_ADDR.fullmatch(raw) is not None,
            "invalid EVM address")
    return raw.lower()


def integer(raw, *, positive=False):
    require(type(raw) is int and raw >= (1 if positive else 0) and raw <= U256,
            "invalid unsigned integer")
    return raw


def digest(raw):
    require(type(raw) is str and RE_HEX.fullmatch(raw) is not None, "invalid sha256")
    return raw


def commitment(obj):
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def reconcile_queued_intents(ledger, rows, *, deal_id, buyer, seller):
    """Reconcile exact read-only intent commitments; NEVER claim delivery."""
    integer(deal_id)
    buyer, seller = address(buyer), address(seller)
    require(buyer != seller, "buyer and seller must differ")
    require(type(ledger) is dict and set(ledger) == EXPECTED_LEDGER,
            "unexpected ledger schema")
    require(type(rows) is list, "intents must be a list")
    deposits = {field: wei(value) for field, value in ledger.items()}
    require(deposits["initial_deposit"] > 0, "empty deposit")
    require(sum(deposits[k] for k in (
        "remaining_locked","payout_queued_total","refund_queued_total")) == deposits["initial_deposit"],
        "locked ledger mismatch")
    payout = refund = 0
    previous_index = -1
    seen_ids = set()
    seen_refund = False
    terms_digest = None
    for row in rows:
        require(type(row) is dict and set(row) == EXPECTED_INTENT,
                "unexpected intent fields; credited or receipt fields not authoritative")
        require(integer(row["deal_id"]) == deal_id, "deal id mismatch")
        idx = integer(row["milestone_index"])
        require(idx > previous_index, "duplicate or unordered milestone index")
        previous_index = idx
        require(row["status"] == "QUEUED_UNVERIFIED", "onchain credit claim forbidden")
        kind = row["kind"]
        require(type(kind) is str and kind in ("PAYOUT","REFUND"), "invalid intent kind")
        if kind == "REFUND":
            require(not seen_refund, "multiple refund messages")
            seen_refund = True
        else:
            require(not seen_refund, "payout after terminal refund")
        actual_recipient = address(row["recipient"])
        require(actual_recipient == (seller if kind == "PAYOUT" else buyer),
                "beneficiary differs from frozen parties")
        amount = wei(row["amount_wei"], positive=True)
        td = digest(row["terms_digest_sha256"])
        terms_digest = td if terms_digest is None else terms_digest
        require(td == terms_digest, "mixed frozen terms digests")
        expected = commitment({
            "domain":"SemanticEscrow.transfer-intent.v1",
            "terms_digest_sha256":td,
            "deal_id":deal_id,
            "milestone_index":idx,
            "kind":kind,
            "recipient":row["recipient"],
            "amount_wei":row["amount_wei"],
        })
        ident = digest(row["intent_id_sha256"])
        require(expected == ident and ident not in seen_ids,
                "invalid or duplicate transfer-intent commitment")
        seen_ids.add(ident)
        if kind == "PAYOUT":
            payout += amount
        else:
            refund += amount
        require(payout <= U256 and refund <= U256, "aggregate overflow")
    require(payout == deposits["payout_queued_total"], "queued payout mismatch")
    require(refund == deposits["refund_queued_total"], "queued refund mismatch")
    return {
        "intent_count": len(rows),
        "payout_queued_wei": str(payout),
        "refund_queued_wei": str(refund),
        "ledger_reconciled": True,
        "delivery": "UNVERIFIED",
        "retry_authorized": False,
    }


def rpc_quantity(value):
    require(type(value) is str and value.startswith("0x") and
            re.fullmatch(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)", value) is not None,
            "invalid RPC quantity")
    return int(value, 16)


def _trace_value_calls(node, ghost, recipient):
    """Find successful EVM value CALLs; return their values, never a receipt proof."""
    require(type(node) is dict, "malformed callTracer node")
    require(not node.get("error"), "failed EVM call in trace")
    kind = node.get("type")
    require(type(kind) is str and kind in ("CALL", "DELEGATECALL", "STATICCALL",
                                         "CALLCODE", "CREATE", "CREATE2", "SELFDESTRUCT"),
            "unknown EVM trace type")
    found = []
    if kind == "CALL" and address(node.get("from")) == ghost and address(node.get("to")) == recipient:
        found.append(rpc_quantity(node.get("value", "0x0")))
    calls = node.get("calls", [])
    require(type(calls) is list, "invalid child call list")
    for child in calls:
        found.extend(_trace_value_calls(child, ghost, recipient))
    return found


def assess_evm_transfer_observation(intent, *, ghost, tx_hash,
                                    tx, receipt, trace, before_wei,
                                    after_wei, block_hash, confirmations):
    """Conservative public-EVM observation, NOT per-intent attribution.

    Ghost contract handleOp transfers may execute inside the parent EVM tx,
    so a top-level receipt.to == beneficiary check is INVALID for GenLayer.
    CallTracer internal CALL matching is required. Read RPC data at the
    transaction's block, use block B-1 vs B balances and minimum confirmations.

    If proof is complete return OBSERVED_UNATTRIBUTED: identical transfers
    can belong to other deals and Ghost messages have no onchain intent-id link.
    """
    require(type(intent) is dict and set(intent) == EXPECTED_INTENT, "invalid intent")
    require(intent["status"] == "QUEUED_UNVERIFIED", "invalid onchain status")
    amount = wei(intent["amount_wei"], positive=True)
    recipient = address(intent["recipient"])
    ghost = address(ghost)
    require(type(tx_hash) is str and RE_TX.fullmatch(tx_hash), "invalid child tx hash")
    require(type(tx) is dict and type(receipt) is dict, "missing EVM transaction/receipt")
    require(type(trace) is dict, "debug trace unavailable")
    integer(confirmations)
    require(confirmations >= 12, "insufficient EVM block confirmations")
    require(type(block_hash) is str and RE_TX.fullmatch(block_hash), "invalid canonical block hash")
    require(type(tx.get("hash")) is str and tx["hash"].lower() == tx_hash.lower(),
            "EVM transaction hash mismatch")
    require(type(receipt.get("transactionHash")) is str and
            receipt["transactionHash"].lower() == tx_hash.lower(), "EVM receipt hash mismatch")
    require(type(receipt.get("blockHash")) is str and
            receipt["blockHash"].lower() == block_hash.lower(), "EVM receipt block hash mismatch")
    block_num = rpc_quantity(receipt.get("blockNumber"))
    require(block_num > 0 and rpc_quantity(tx.get("blockNumber")) == block_num,
            "transaction not mined at proven block")
    require(rpc_quantity(receipt.get("status")) == 1, "EVM transaction reverted")
    require(address(tx.get("to")) == address(receipt.get("to")), "EVM target mismatch")
    require(address(trace.get("from")) == address(tx.get("from")) and
            address(trace.get("to")) == address(tx.get("to")),
            "call trace root differs from included EVM transaction")
    calls = _trace_value_calls(trace, ghost, recipient)
    require(calls == [amount], "exactly one successful matching Ghost CALL required")
    prior = wei(before_wei)
    after = wei(after_wei)
    require(after - prior == amount, "recipient balance effect not isolated in this block")
    return {
        "observation": "GHOST_VALUE_CALL_OBSERVED_UNATTRIBUTED",
        "transfer_tx_hash": tx_hash.lower(),
        "recipient": recipient,
        "amount_wei": str(amount),
        "delivery": "UNVERIFIED_FOR_SPECIFIC_INTENT",
        "retry_authorized": False,
        "production_release_authorized": False,
    }


def release_gate(findings):
    """Fail closed: technical tests are not an independent production audit."""
    require(type(findings) is dict, "findings must be structured")
    known = {
        "proven_child_intent_binding", "failure_recovery_audited",
        "egress_network_policy_audited", "independent_security_audit",
        "live_escrow_scenario_finalized",
    }
    require(set(findings).issubset(known), "unexpected release attestation fields")
    missing = sorted(k for k in known if findings.get(k) is not True)
    # Booleans supplied by a caller are NOT cryptographic proof. Even all true
    # must not override a human independent audit and a deployment-specific signoff.
    if not missing:
        missing = ["independent_human_release_signoff_not_obtainable_by_this_tool"]
    return {"status":"RELEASE_BLOCKED","missing":missing,
            "retry_authorized":False,"production_release_authorized":False}

"""Two-layer SemanticEscrow payout correlation: fail-closed, READ ONLY.

Official GenLayer v0.6: internal IC messages can spawn GenLayer children;
external EOA native-GEN transfers are Ghost handleOp EVM calls, NOT
necessarily GenLayer child tx IDs. Never equate them.

This analyzer accepts publicly fetched evidence but *does not authenticate
the JSON itself*. A finality receipt plus an exact address/value pairing
cannot cryptographically bind the onchain escrow intent SHA to an external
EVM call: the deployed v0.2.16 contract emits native-value calls without
an intent ID in EVM calldata. The verdict intentionally stays UNVERIFIED
unless an independently checked, onchain intent↔message↔EVM link exists.
"""
from __future__ import annotations

import hashlib
import json
from phase8_release_gate import (
    EvidenceRejected,EXPECTED_INTENT,reconcile_queued_intents,
    assess_evm_transfer_observation,address,integer,wei,require,RE_TX,
)

SCHEMA="SemanticEscrow.payment-correlation.v1"
UNVERIFIED="UNVERIFIED_INTENT_TO_EVM_DELIVERY"
NO_RETRY=False
PROTOCOL_STATUSES=frozenset({"FINALIZED","Finalized"})
SUCCESS=frozenset({"FINISHED_WITH_RETURN","FinishedWithReturn"})
MAX_MESSAGES=128

def txid(s):
    require(type(s) is str and RE_TX.fullmatch(s) is not None,"invalid tx hash")
    return s.lower()

def sha(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),
                   ensure_ascii=True,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _native_amount(value):
    # Chain RPC messages specify value in 0x format. For historic
    # normalized receipts only decimal strings are accepted.
    require(type(value) is str and value,"invalid chain native value")
    if value.startswith("0x"):
        require(value=="0x0" or (len(value)>3 and value[2]!="0"),
                "noncanonical RPC hex amount")
        try:
            out=int(value,16)
        except ValueError as exc:
            raise EvidenceRejected("invalid native hex amount") from exc
        require(value.lower()==hex(out),"noncanonical hex case/value")
        require(out<2**256,"native value overflow")
        return out
    return wei(value)

def _message(msg):
    require(type(msg) is dict,"unexpected GenLayer message type")
    require(set(msg)=={"messageType","recipient","value","data","onAcceptance","saltNonce"},
            "unexpected GenLayer message format")
    require(type(msg["messageType"]) is int and msg["messageType"] in (0,1),
            "unsupported GenLayer message type")
    require(type(msg["onAcceptance"]) is bool,"invalid emission phase")
    require(type(msg["data"]) is str and msg["data"].startswith("0x"),"bad call data")
    require(type(msg["saltNonce"]) in (str,int),"bad salt nonce")
    return (address(msg["recipient"]),_native_amount(msg["value"]))

def _parent(parent,parent_tx,ghost):
    require(type(parent) is dict,"missing final parent transaction")
    require(txid(parent.get("id"))==parent_tx,"wrong parent GenLayer transaction")
    require(address(parent.get("recipient"))==ghost,"wrong parent Ghost")
    require(parent.get("status_name") in PROTOCOL_STATUSES and
            parent.get("tx_execution_result_name") in SUCCESS,
            "parent is not finalized successful GenVM")
    messages=parent.get("messages")
    require(type(messages) is list and len(messages)<=MAX_MESSAGES,
            "missing or unbounded finalized message list")
    for m in messages:_message(m)
    return messages

def correlate_payment(*,chain_id,ghost,parent_tx,parent,ledger,rows,
                      deal_id,buyer,seller,intent_id,
                      triggered_child_ids=None,child_receipts=None,
                      external_evm=None):
    """Validate all candidate records. Never certify the missing cryptographic link.

    If caller supplied EVM details, assess_evm_transfer_observation applies
    real transaction/receipt/trace and balance checks. Source must still
    independently authenticate all JSON using chain-specific RPC.
    """
    require(type(chain_id) is int and chain_id==4221,"wrong chain")
    ghost=address(ghost)
    parent_tx=txid(parent_tx)
    integer(deal_id)
    report=reconcile_queued_intents(ledger,rows,deal_id=deal_id,
                                    buyer=buyer,seller=seller)
    require(type(intent_id) is str and len(intent_id)==64,"invalid intent identifier")
    found=[r for r in rows if r["intent_id_sha256"]==intent_id]
    require(len(found)==1,"intent not in frozen onchain ledger")
    intent=found[0]
    messages=_parent(parent,parent_tx,ghost)
    matching=[]
    for pos,m in enumerate(messages):
        recipient,value=_message(m)
        # Published genlayer-js/src/types/transactions.ts:
        # enum MessageType { External=0, Internal=1 }. EOA native payments
        # MUST NOT be correlated from IC→IC child messages.
        if recipient==address(intent["recipient"]) and value==wei(intent["amount_wei"]):
            require(m["messageType"]==0,"matching message is INTERNAL, not a Ghost EVM transfer")
            require(m["onAcceptance"] is False,
                    "external value must be emitted only on finalized")
            # A transfer-to-EOA must carry no EVM function calldata; otherwise
            # this might be a token call, not a pure native GEN transfer.
            if m["data"]!="0x":
                continue
            matching.append(pos)
    require(len(matching)==1,
            "zero or ambiguous matching parent native-value message")
    index=matching[0]
    # If two distinct queued intents have the same destination/wei, neither
    # uniquely matches a native EVM call even when only one was emitted.
    duplicates=[r for r in rows if
        address(r["recipient"])==address(intent["recipient"]) and
        wei(r["amount_wei"])==wei(intent["amount_wei"])]
    require(len(duplicates)==1,"multiple equivalent intents; cannot attribute message")

    children=[] if triggered_child_ids is None else triggered_child_ids
    require(type(children) is list and len(children)<=MAX_MESSAGES,"invalid triggered ID list")
    normalized=[txid(c) for c in children]
    require(len(set(normalized))==len(normalized),"duplicate child transaction id")
    receipts=[] if child_receipts is None else child_receipts
    require(type(receipts) is list,"invalid child receipt list")
    require(len(receipts)==len(normalized),"missing triggered child receipts")
    checked=[]
    for r in receipts:
        require(type(r) is dict,"malformed child consensus receipt")
        require(txid(r.get("id")) in normalized,"unknown child id")
        require(address(r.get("sender"))==ghost,"child sender differs from ghost")
        require(r.get("status_name") in PROTOCOL_STATUSES and
                r.get("tx_execution_result_name") in SUCCESS,
                "child GenLayer execution not finalized success")
        checked.append(txid(r["id"]))
    require(set(checked)==set(normalized),"duplicate or missing child receipts")

    evm_observation=None
    if external_evm is not None:
        require(type(external_evm) is dict,"invalid external EVM evidence")
        require(set(external_evm)=={
            "tx_hash","tx","receipt","trace","before_wei","after_wei",
            "block_hash","confirmations",
        },"unexpected EVM evidence fields")
        evm_observation=assess_evm_transfer_observation(
            intent,ghost=ghost,**external_evm)
        require(evm_observation["delivery"]=="UNVERIFIED_FOR_SPECIFIC_INTENT",
                "unexpected proof escalation from observational EVM tracer")

    return {
        "schema":SCHEMA,
        "chain_id":4221,
        "parent_genlayer_tx":parent_tx,
        "parent_finalized_and_successful":True,
        "intent_id_sha256":intent_id,
        "native_message_index":index,
        "native_message_uniquely_matches_intent_terms":True,
        "protocol_triggered_internal_child_ids":normalized,
        "external_evm_ghost_value_call":(
            evm_observation["transfer_tx_hash"] if evm_observation else None),
        "value_call_observed_unattributed":bool(evm_observation),
        "onchain_intent_to_external_call_binding":False,
        "beneficiary_credit_for_this_specific_intent":UNVERIFIED,
        "retry_authorized":NO_RETRY,
        "production_release_authorized":False,
        "evidence_sha256":sha({
            "intent":intent,"parent":parent_tx,"messages":messages,
            "internal_child_ids":normalized,
            "evm":evm_observation,
        }),
    }

def verdict_for_missing_data(code):
    require(type(code) is str and code in (
        "NO_FINALIZED_PARENT","NO_CHILD_SOURCE","NO_EVM_TRACE",
        "NO_INTENT_MESSAGE_BINDING","NO_CANONICAL_BALANCE_PROOF",
    ),"unknown missing evidence state")
    return {"status":"BLOCKED","reason":code,
            "intent_to_child_delivery":"UNVERIFIED",
            "retry_authorized":False,"production_release_authorized":False}

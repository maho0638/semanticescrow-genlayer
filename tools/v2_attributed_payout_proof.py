"""Read-only v2 GenLayer intent -> Ghost -> router -> EOA payout attestation.

All proofs require an authenticated GenLayer parent receipt and an escrow
onchain intent getter from TRUSTED chain sources, PLUS EVM RPC with code
pin. Caller callbacks MUST fetch those values from chain; a supplied local
JSON without network authentication is NOT a delivery proof. Never sign,
fund, replay, rescue, or merge based on this report.

The new router emits NativeIntentPaid only *after* the EVM value CALL succeeds,
and its delivered[id] state forbids replay. This code is unusable for the OLD
Bradbury v1 IC, whose native EOA messages contain no intent id.
"""
from __future__ import annotations
import hashlib

from phase8_release_gate import (
    EvidenceRejected,address,digest,integer,require,wei,commitment,
    EXPECTED_INTENT,RE_TX,
)
from phase2_intent_child_correlator import _native_amount,txid

TOPIC="NativeIntentPaid(bytes32,address,address,uint256)"

def verify_attributed_native_gen(
    *, w3, router, ghost, intent_id, parent_id, payout_evm_tx,
    read_finalized_parent, read_canonical_intent,
    trusted_router_runtime_sha256, expected_chain_id=4221,
    minimum_confirmations=12,
):
    """Validate independently read receipts. Never auto-authorize a new GEN send.

    Inputs read_finalized_parent(tx) and read_canonical_intent(intent_id)
    MUST query trusted chain sources, not load unauthenticated JSON.
    trusted_router_runtime_sha256 must be independently anchored to audited
    source and its specific constructor immutables/deployed address.
    """
    integer(expected_chain_id,positive=True)
    integer(minimum_confirmations)
    require(w3.eth.chain_id==expected_chain_id,"wrong EVM chain")
    if expected_chain_id==4221:
        require(minimum_confirmations>=12,"Bradbury needs >=12 confirmations")
    ghost=address(ghost)
    router_addr=address(router.address)
    intent_id=digest(intent_id)
    parent_id=txid(parent_id)
    payout_evm_tx=txid(payout_evm_tx)
    pin=digest(trusted_router_runtime_sha256)

    # Trusted externally acquired GenLayer onchain view.
    item=read_canonical_intent(intent_id)
    require(type(item) is dict and set(item)==EXPECTED_INTENT,"bad frozen IC intent schema")
    require(item["intent_id_sha256"]==intent_id,"wrong onchain intent ID")
    require(item["status"]=="QUEUED_UNVERIFIED","not an onchain queued escrow payment")
    amount=wei(item["amount_wei"],positive=True)
    receiver=address(item["recipient"])
    require(type(item["kind"]) is str and item["kind"] in ("PAYOUT","REFUND"),"wrong intent kind")
    require(commitment({
        "domain":"SemanticEscrow.transfer-intent.v1",
        "terms_digest_sha256":item["terms_digest_sha256"],
        "deal_id":integer(item["deal_id"]),
        "milestone_index":integer(item["milestone_index"]),
        "kind":item["kind"],
        "recipient":item["recipient"],
        "amount_wei":item["amount_wei"],
    })==intent_id,"intent hash mismatch")

    # GenLayer protocol consensus and message evidence.
    parent=read_finalized_parent(parent_id)
    require(type(parent) is dict,"GenLayer parent unavailable")
    require(txid(parent.get("id"))==parent_id,"wrong parent ID")
    require(address(parent.get("recipient"))==ghost,"wrong parent recipient")
    # Official GenLayer node receipt uses camelCase statusName /
    # txExecutionResultName; the verified old Bradbury decoder exposes
    # snake_case status_name / tx_execution_result_name instead.
    status=parent.get("statusName",parent.get("status_name"))
    execution=parent.get("txExecutionResultName",parent.get("tx_execution_result_name"))
    require(status in ("FINALIZED","Finalized") and
            execution in ("FINISHED_WITH_RETURN","FinishedWithReturn"),
            "parent not finalized with successful GenVM result")
    if "status" in parent:
        require(parent["status"]==7,"consensus numeric parent status differs")
    if "txExecutionResult" in parent:
        require(parent["txExecutionResult"]==1,"consensus numeric execution failed")
    messages=parent.get("messages")
    require(type(messages) is list and len(messages)<=128,"no authenticated parent messages")
    calldata=router.encode_abi("disburse",args=[
        bytes.fromhex(intent_id),w3.to_checksum_address(receiver)])
    matches=[]
    for index, m in enumerate(messages):
        require(type(m) is dict,"malformed onchain parent message")
        if (m.get("recipient") is not None and
            address(m["recipient"])==router_addr and
            type(m.get("data")) is str and
            m["data"].lower()==calldata.lower()):
            require(m.get("messageType")==0 and
                    m.get("onAcceptance") is False and
                    _native_amount(m.get("value"))==amount,
                    "authenticated parent native payout call differs from intent")
            matches.append(index)
    require(len(matches)==1,"missing or duplicate intent-bound external parent message")

    # Independently pin real EVM runtime code. A self-selected digest from
    # the same untrusted RPC is NOT a trusted code pin.
    receipt=w3.eth.get_transaction_receipt(payout_evm_tx)
    require(receipt is not None and receipt["status"]==1,"failed/missing EVM transfer receipt")
    height=integer(receipt["blockNumber"],positive=True)
    latest=w3.eth.block_number
    require(latest-height>=minimum_confirmations,"EVM receipt not sufficiently confirmed")
    canonical=w3.eth.get_block(height)
    require(canonical["hash"]==receipt["blockHash"],"reorg/mismatched receipt block hash")
    bytecode=w3.eth.get_code(router_addr,block_identifier=height)
    require(bool(bytecode),"router EVM code missing")
    require(hashlib.sha256(bytes(bytecode)).hexdigest()==pin,"router bytecode does not match trusted audited deployment")
    require(address(router.functions.escrowGhost().call(block_identifier=height))==ghost,
            "router not bound to escrow Ghost")
    require(router.functions.expectedChainId().call(block_identifier=height)==expected_chain_id,
            "router chain binding differs from approved network")

    # Onchain event emitted AFTER a native value CALL by known source, in
    # the same EVM tx. Check event emitter, actual topics and exact wei.
    target_logs=[l for l in receipt["logs"] if
                 address(l["address"])==router_addr]
    require(len(target_logs)==1,"wrong number of payout router EVM events")
    raw=target_logs[0]
    event=router.events.NativeIntentPaid().process_log(raw)
    args=event["args"]
    require(bytes(args["intentId"])==bytes.fromhex(intent_id),"event intent mismatch")
    require(address(args["ghost"])==ghost and
            address(args["recipient"])==receiver and
            integer(args["amountWei"],positive=True)==amount,
            "event recipient/Ghost/value mismatch")
    require(len(raw["topics"])==4,"malformed indexed EVM event")
    require(bytes(raw["topics"][0])==bytes(w3.keccak(text=TOPIC)),
            "not the audited NativeIntentPaid event")
    require(router.functions.delivered(bytes.fromhex(intent_id)).call(
            block_identifier=height) is True,
            "onchain replay marker not present at receipt block")

    # EOA requirement ensures the beneficiary cannot forward value from a
    # contract fallback during delivery. The block-balance delta is a
    # conservative *extra* guard; concurrent activity may cause fail-closed.
    require(w3.eth.get_code(receiver,block_identifier=height)==b"",
            "beneficiary is a contract, not an EOA")
    pre=w3.eth.get_balance(receiver,block_identifier=height-1)
    post=w3.eth.get_balance(receiver,block_identifier=height)
    require(type(pre) is int and type(post) is int and post-pre==amount,
            "EOA block-balance delta not uniquely attributable")
    return {
        "network":expected_chain_id,
        "status":"V2_ROUTER_PAYMENT_PROVEN_FOR_INTENT",
        "intent_id_sha256":intent_id,
        "parent_genlayer_tx":parent_id,
        "external_message_index":matches[0],
        "payout_evm_tx":payout_evm_tx,
        "eoa_recipient":receiver,
        "native_wei_credited":str(amount),
        "proof_basis":"FINALIZED_PARENT_EXACT_CALLDATA_AND_PINNED_ROUTER_EVM_EVENT_AND_EOA_BALANCE",
        "new_contract_required":True,
        "old_v1_payment_claim":False,
        "automatic_retry_authorized":False,
        "production_release_authorized":False,
    }

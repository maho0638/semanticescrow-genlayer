"""Security-focused offline checks. No wallets, network, keys or token spending."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase8_release_gate import (
    EvidenceRejected, commitment, wei, reconcile_queued_intents,
    assess_evm_transfer_observation, release_gate,
)

BUYER="0x"+"11"*20
SELLER="0x"+"22"*20
GHOST="0x"+"33"*20
HASH="0x"+"ab"*32
BLOCK="0x"+"cd"*32
TERMS="55"*32

def intent(index,kind,amount,deal=0):
    recipient=SELLER if kind=="PAYOUT" else BUYER
    row={"deal_id":deal,"milestone_index":index,"kind":kind,
         "recipient":recipient,"amount_wei":str(amount),
         "status":"QUEUED_UNVERIFIED","terms_digest_sha256":TERMS}
    row["intent_id_sha256"]=commitment({
        "domain":"SemanticEscrow.transfer-intent.v1",
        "terms_digest_sha256":TERMS,
        "deal_id":deal,"milestone_index":index,"kind":kind,
        "recipient":recipient,"amount_wei":str(amount)})
    return row

def ledger(deposit=25,locked=0,payout=10,refund=15):
    return {"initial_deposit":str(deposit),"remaining_locked":str(locked),
            "payout_queued_total":str(payout),"refund_queued_total":str(refund)}

def run(rows=None,book=None):
    if rows is None:rows=[intent(0,"PAYOUT",10),intent(1,"REFUND",15)]
    if book is None:book=ledger()
    return reconcile_queued_intents(book,rows,deal_id=0,buyer=BUYER,seller=SELLER)

def test_real_contract_intent_commitment_canonicalization():
    row=intent(0,"REFUND",25)
    expected={
      "amount_wei":"25","deal_id":0,"domain":"SemanticEscrow.transfer-intent.v1",
      "kind":"REFUND","milestone_index":0,"recipient":BUYER,"terms_digest_sha256":TERMS
    }
    direct=hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(",",":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()
    assert row["intent_id_sha256"]==direct

def test_clean_mixed_payout_refund_reconciles_without_claiming_credit():
    x=run()
    assert x=={"intent_count":2,"payout_queued_wei":"10","refund_queued_wei":"15",
               "ledger_reconciled":True,"delivery":"UNVERIFIED","retry_authorized":False}

def test_unsettled_and_partially_settled_are_accounted_separately():
    x=run(rows=[],book=ledger(25,25,0,0))
    assert x["delivery"]=="UNVERIFIED"
    x=run(rows=[intent(0,"PAYOUT",10)],book=ledger(25,15,10,0))
    assert x["intent_count"]==1

@pytest.mark.parametrize("raw",["","00","01","-1","+2"," 1","1 ","2.0","2e1","nan","0x1",
    "１","٣","1\n","-0"])
def test_malformed_or_noncanonical_wei_never_accepted(raw):
    with pytest.raises(EvidenceRejected):wei(raw)

@pytest.mark.parametrize("field,new",[
    ("amount_wei","11"),("recipient",BUYER),("kind","REFUND"),
    ("deal_id",1),("milestone_index",8),("terms_digest_sha256","ab"*32),
    ("intent_id_sha256","cd"*32),("status","DELIVERED"),
    ("status","FINALIZED"),("status","PAYOUT_QUEUED"),
    ("recipient","0x00"),("amount_wei","0"),
])
def test_mutated_intent_fails_closed(field,new):
    rows=[intent(0,"PAYOUT",10),intent(1,"REFUND",15)]
    rows[0][field]=new
    with pytest.raises(EvidenceRejected):run(rows=rows)

@pytest.mark.parametrize("field,new",[
    ("initial_deposit","26"),("remaining_locked","1"),
    ("payout_queued_total","11"),("refund_queued_total","14"),
    ("initial_deposit","01"),("payout_queued_total","-10"),
    ("refund_queued_total","0xF")
])
def test_wrong_ledgers_are_rejected(field,new):
    book=ledger()
    book[field]=new
    with pytest.raises(EvidenceRejected):run(book=book)

def test_duplicate_or_unordered_intents_fail():
    rows=[intent(1,"PAYOUT",10),intent(1,"REFUND",15)]
    with pytest.raises(EvidenceRejected):run(rows=rows)
    rows=[intent(1,"PAYOUT",10),intent(0,"REFUND",15)]
    with pytest.raises(EvidenceRejected):run(rows=rows)

def test_multiple_refunds_and_payout_after_refund_fail():
    rows=[intent(0,"REFUND",10),intent(1,"REFUND",15)]
    with pytest.raises(EvidenceRejected):run(rows=rows)
    rows=[intent(0,"REFUND",15),intent(1,"PAYOUT",10)]
    with pytest.raises(EvidenceRejected):run(rows=rows)

def test_unauthorized_credit_field_is_forbidden():
    rows=[intent(0,"REFUND",25)]
    rows[0]["credited"]=True
    with pytest.raises(EvidenceRejected):
        run(rows=rows,book=ledger(25,0,0,25))

def test_wrong_schema_and_fake_signoffs_fail():
    with pytest.raises(EvidenceRejected):run(rows={})
    with pytest.raises(EvidenceRejected):run(book={"initial_deposit":"25"})
    with pytest.raises(EvidenceRejected):reconcile_queued_intents(
        ledger(25,0,0,25),[intent(0,"REFUND",25)],
        deal_id=0,buyer=SELLER,seller=SELLER)

def evm():
    tx={"hash":HASH,"from":BUYER,"to":GHOST,"blockNumber":"0x10"}
    receipt={"transactionHash":HASH,"to":GHOST,"status":"0x1",
             "blockHash":BLOCK,"blockNumber":"0x10"}
    trace={"type":"CALL","from":BUYER,"to":GHOST,"value":"0x0",
           "calls":[{"type":"CALL","from":GHOST,"to":SELLER,"value":"0xa","calls":[]}]}
    return tx,receipt,trace

def audit(tx=None,receipt=None,trace=None,**extra):
    base_tx,base_receipt,base_trace=evm()
    base={"ghost":GHOST,"tx_hash":HASH,
          "tx":base_tx if tx is None else tx,
          "receipt":base_receipt if receipt is None else receipt,
          "trace":base_trace if trace is None else trace,
          "before_wei":"100","after_wei":"110","block_hash":BLOCK,
          "confirmations":12}
    base.update(extra)
    return assess_evm_transfer_observation(intent(0,"PAYOUT",10),**base)

def test_proven_ghost_call_never_claims_specific_intent_delivered():
    result=audit()
    assert result["observation"]=="GHOST_VALUE_CALL_OBSERVED_UNATTRIBUTED"
    assert result["delivery"]=="UNVERIFIED_FOR_SPECIFIC_INTENT"
    assert result["retry_authorized"] is False
    assert result["production_release_authorized"] is False

@pytest.mark.parametrize("variation",[
    "evm_revert","tx_hash_mismatch","receipt_hash_mismatch","trace_ghost_mismatch",
    "trace_beneficiary_mismatch","trace_wrong_value","trace_call_error",
    "trace_root_error","trace_root_mismatch","missing_trace","missing_receipt",
    "block_hash_mismatch","unconfirmed","not_mined","wrong_balance",
    "duplicate_value_calls","wrong_target","bad_hex_status"
])
def test_unreliable_evm_observations_never_certified(variation):
    tx,receipt,trace=evm()
    opts={}
    if variation=="evm_revert":receipt["status"]="0x0"
    elif variation=="tx_hash_mismatch":tx["hash"]="0x"+"fe"*32
    elif variation=="receipt_hash_mismatch":receipt["transactionHash"]="0x"+"fe"*32
    elif variation=="trace_ghost_mismatch":trace["calls"][0]["from"]=SELLER
    elif variation=="trace_beneficiary_mismatch":trace["calls"][0]["to"]=BUYER
    elif variation=="trace_wrong_value":trace["calls"][0]["value"]="0xb"
    elif variation=="trace_call_error":trace["calls"][0]["error"]="execution reverted"
    elif variation=="trace_root_error":trace["error"]="execution reverted"
    elif variation=="trace_root_mismatch":trace["from"]=SELLER
    elif variation=="missing_trace":opts["trace"]={}
    elif variation=="missing_receipt":opts["receipt"]={}
    elif variation=="block_hash_mismatch":receipt["blockHash"]="0x"+"fe"*32
    elif variation=="unconfirmed":opts["confirmations"]=11
    elif variation=="not_mined":receipt["blockNumber"]="0x0";tx["blockNumber"]="0x0"
    elif variation=="wrong_balance":opts["after_wei"]="111"
    elif variation=="duplicate_value_calls":trace["calls"].append(dict(trace["calls"][0]))
    elif variation=="wrong_target":receipt["to"]=SELLER
    elif variation=="bad_hex_status":receipt["status"]="1"
    opts.setdefault("tx",tx); opts.setdefault("receipt",receipt);opts.setdefault("trace",trace)
    with pytest.raises(EvidenceRejected):audit(**opts)

def test_release_gate_never_trusts_user_supplied_boolean_attestations():
    blocked=release_gate({})
    assert blocked["status"]=="RELEASE_BLOCKED"
    assert len(blocked["missing"])==5
    fully_forged={name:True for name in (
        "proven_child_intent_binding","failure_recovery_audited",
        "egress_network_policy_audited","independent_security_audit",
        "live_escrow_scenario_finalized")}
    forged=release_gate(fully_forged)
    assert forged["status"]=="RELEASE_BLOCKED"
    assert forged["production_release_authorized"] is False
    assert forged["retry_authorized"] is False

def test_unknown_release_attestation_field_is_rejected():
    with pytest.raises(EvidenceRejected):
        release_gate({"paid":True})

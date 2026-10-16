"""Adversarial offline correlation tests. No wallet / RPC / GEN."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase2_intent_child_correlator import correlate_payment,verdict_for_missing_data
from phase8_release_gate import EvidenceRejected
from test_phase8_release_gate import BUYER,SELLER,GHOST,HASH,BLOCK,intent,ledger,evm

PARENT="0x"+"ee"*32
CHILD="0x"+"ff"*32

def msg(addr=SELLER,amount=10,**changes):
    v={"messageType":0,"recipient":addr,"value":hex(amount),
       "data":"0x","onAcceptance":False,"saltNonce":"0x0"}
    v.update(changes)
    return v

def parent(messages=None,**changes):
    v={"id":PARENT,"recipient":GHOST,"status_name":"FINALIZED",
       "tx_execution_result_name":"FINISHED_WITH_RETURN",
       "messages":[msg()] if messages is None else messages}
    v.update(changes)
    return v

def external():
    tx,receipt,trace=evm()
    return {"tx_hash":HASH,"tx":tx,"receipt":receipt,"trace":trace,
            "before_wei":"100","after_wei":"110","block_hash":BLOCK,
            "confirmations":12}

def run(**changes):
    params={"chain_id":4221,"ghost":GHOST,"parent_tx":PARENT,
            "parent":parent(),"ledger":ledger(25,15,10,0),
            "rows":[intent(0,"PAYOUT",10)],"deal_id":0,
            "buyer":BUYER,"seller":SELLER,
            "intent_id":intent(0,"PAYOUT",10)["intent_id_sha256"],
            "triggered_child_ids":[],"child_receipts":[]}
    params.update(changes)
    return correlate_payment(**params)

def test_single_outbound_message_only_candidates_without_delivered_claim():
    r=run()
    assert r["parent_finalized_and_successful"]
    assert r["native_message_index"]==0
    assert r["native_message_uniquely_matches_intent_terms"] is True
    assert r["onchain_intent_to_external_call_binding"] is False
    assert r["value_call_observed_unattributed"] is False
    assert r["beneficiary_credit_for_this_specific_intent"]=="UNVERIFIED_INTENT_TO_EVM_DELIVERY"
    assert r["retry_authorized"] is False

def test_full_ghost_trace_even_with_exact_matching_value_is_not_intent_proof():
    r=run(external_evm=external())
    assert r["external_evm_ghost_value_call"]==HASH
    assert r["value_call_observed_unattributed"] is True
    assert r["onchain_intent_to_external_call_binding"] is False
    assert r["production_release_authorized"] is False
    assert r["beneficiary_credit_for_this_specific_intent"].startswith("UNVERIFIED_")

def test_same_input_digest_is_deterministic():
    assert run()["evidence_sha256"]==run()["evidence_sha256"]

@pytest.mark.parametrize("change",[
    {"chain_id":1},{"chain_id":"4221"},{"ghost":BUYER},
    {"parent_tx":HASH},{"parent":None},
    {"parent":parent(id=HASH)},
    {"parent":parent(recipient=BUYER)},
    {"parent":parent(status_name="ACCEPTED")},
    {"parent":parent(tx_execution_result_name="FINISHED_WITH_ERROR")},
    {"parent":parent(messages=[])},
    {"parent":parent(messages=[msg(addr=BUYER)])},
    {"parent":parent(messages=[msg(amount=11)])},
    {"parent":parent(messages=[msg(onAcceptance=True)])},
    {"parent":parent(messages=[msg(data="0x1234")])},
    {"parent":parent(messages=[msg(),msg()])},
    {"parent":parent(messages=[msg(),msg(addr=BUYER),msg()])},
    {"parent":parent(messages=[msg(value="0x00")])},
    {"parent":parent(messages=[msg(value="-1")])},
    {"parent":parent(messages=[msg(messageType=True)])},
    {"parent":parent(messages=[msg(messageType=256)])},
    {"parent":parent(messages=[msg(messageType=1)])},
    {"parent":parent(messages=[msg(saltNonce=None)])},
    {"parent":parent(messages=[msg(recipient="not address")])},
    {"parent":parent(messages=[msg(foo="bar")])},
    {"parent":parent(messages=[msg(data="1234")])},
    {"parent":parent(messages=[msg(),{"messageType":1}])},
    {"triggered_child_ids":[CHILD],"child_receipts":[]},
    {"triggered_child_ids":[CHILD,CHILD],"child_receipts":[{},{}]},
    {"triggered_child_ids":[CHILD],"child_receipts":[{"id":CHILD,"sender":BUYER,"status_name":"FINALIZED","tx_execution_result_name":"FINISHED_WITH_RETURN"}]},
    {"triggered_child_ids":[CHILD],"child_receipts":[{"id":CHILD,"sender":GHOST,"status_name":"ACCEPTED","tx_execution_result_name":"FINISHED_WITH_RETURN"}]},
    {"triggered_child_ids":[CHILD],"child_receipts":[{"id":CHILD,"sender":GHOST,"status_name":"FINALIZED","tx_execution_result_name":"FINISHED_WITH_ERROR"}]},
    {"triggered_child_ids":[CHILD],"child_receipts":[{"id":HASH,"sender":GHOST,"status_name":"FINALIZED","tx_execution_result_name":"FINISHED_WITH_RETURN"}]},
    {"ledger":ledger(25,14,10,0)},{"intent_id":"ab"*32},
])
def test_malicious_missing_or_ambiguous_evidence_fails_closed(change):
    with pytest.raises(EvidenceRejected):
        run(**copy.deepcopy(change))

def test_internal_child_can_be_observed_but_not_bound_to_eoa_intent():
    r=run(triggered_child_ids=[CHILD],child_receipts=[
        {"id":CHILD,"sender":GHOST,"status_name":"FINALIZED",
         "tx_execution_result_name":"FINISHED_WITH_RETURN"}])
    assert r["protocol_triggered_internal_child_ids"]==[CHILD]
    assert r["onchain_intent_to_external_call_binding"] is False
    assert r["beneficiary_credit_for_this_specific_intent"].startswith("UNVERIFIED")

def test_identical_intents_among_deals_never_credited_by_amount_only():
    # A strict escrow commitment can create different IDs for different
    # milestones paying same recipient and wei; amount-only inference fails.
    first=intent(0,"PAYOUT",10)
    second=intent(1,"PAYOUT",10)
    with pytest.raises(EvidenceRejected,match="equivalent intents"):
        run(rows=[first,second],ledger=ledger(25,5,20,0))

@pytest.mark.parametrize("mutator",[
    lambda x:x.update({"confirmations":11}),
    lambda x:x.update({"after_wei":"111"}),
    lambda x:x["receipt"].update({"status":"0x0"}),
    lambda x:x["trace"]["calls"][0].update({"value":"0xb"}),
    lambda x:x["receipt"].update({"blockHash":"0x"+"23"*32}),
    lambda x:x["trace"]["calls"][0].update({"from":BUYER}),
    lambda x:x.update({"unexpected_delivery":True}),
])
def test_evm_failures_cannot_be_accepted_as_credited(mutator):
    evidence=external()
    mutator(evidence)
    with pytest.raises(EvidenceRejected):
        run(external_evm=evidence)

def test_missing_evidence_states_always_block():
    for code in ("NO_FINALIZED_PARENT","NO_CHILD_SOURCE","NO_EVM_TRACE",
                 "NO_INTENT_MESSAGE_BINDING","NO_CANONICAL_BALANCE_PROOF"):
        r=verdict_for_missing_data(code)
        assert r["status"]=="BLOCKED"
        assert r["retry_authorized"] is False
        assert r["production_release_authorized"] is False

def test_unexpected_missing_evidence_status_is_rejected():
    with pytest.raises(EvidenceRejected):
        verdict_for_missing_data("DELIVERED")

def test_core_source_not_modified_or_non_authoritative_payment_assertion():
    src=(Path(__file__).resolve().parents[1]/"tools/phase2_intent_child_correlator.py").read_text()
    assert "eth_sendRawTransaction" not in src
    assert "send_transaction(" not in src
    assert "private_key" not in src
    assert '"onchain_intent_to_external_call_binding":False' in src

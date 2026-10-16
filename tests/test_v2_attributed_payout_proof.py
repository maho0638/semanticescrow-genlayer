"""Live EVM state and GenLayer-parent proof integration, with mock parent RPC.

The EVM source is actually deployed to eth-tester; nothing is deployed to
real Bradbury. Fake parent RPC for test only; never label public-chain paid.
"""
import copy
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from v2_attributed_payout_proof import verify_attributed_native_gen
from phase8_release_gate import EvidenceRejected
from test_phase8_release_gate import intent
from test_v2_evm_payout_router import env,compiled,execute

PARENT="0x"+"af"*32

@pytest.fixture
def case(env):
    chain,router,ghost,outsider,recipient=env
    amount=10**12
    item=intent(0,"PAYOUT",amount)
    # The base fixture seller is irrelevant to this voucher's recipient;
    # its recomputed SHA matches the original frozen commitment.
    item["recipient"]=recipient.lower()
    from phase8_release_gate import commitment
    item["intent_id_sha256"]=commitment({
        "domain":"SemanticEscrow.transfer-intent.v1",
        "terms_digest_sha256":item["terms_digest_sha256"],
        "deal_id":item["deal_id"],"milestone_index":item["milestone_index"],
        "kind":item["kind"],"recipient":item["recipient"],
        "amount_wei":item["amount_wei"],
    })
    ident=item["intent_id_sha256"]
    abi=router.encode_abi("disburse",args=[bytes.fromhex(ident),recipient])
    parent={"id":PARENT,"recipient":ghost,"status_name":"FINALIZED",
            "tx_execution_result_name":"FINISHED_WITH_RETURN",
            "messages":[{
                "messageType":0,"recipient":router.address,
                "value":hex(amount),"data":abi,"onAcceptance":False,
            }]}
    receipt=execute(chain,router,ghost,bytes.fromhex(ident),recipient,amount)
    assert receipt.status==1
    expected=hashlib.sha256(bytes(chain.eth.get_code(router.address))).hexdigest()
    def check(**extra):
        conf={
          "w3":chain,"router":router,"ghost":ghost,
          "intent_id":ident,"parent_id":PARENT,
          "payout_evm_tx":chain.to_hex(receipt.transactionHash),
          "read_finalized_parent":lambda _:parent,
          "read_canonical_intent":lambda _:item,
          "trusted_router_runtime_sha256":expected,
          "expected_chain_id":chain.eth.chain_id,
          "minimum_confirmations":0,
        }
        conf.update(extra)
        return verify_attributed_native_gen(**conf)
    return locals()

def test_actual_evm_receipt_plus_exact_parent_intent_and_eoa_delta(case):
    outcome=case["check"]()
    assert outcome["status"]=="V2_ROUTER_PAYMENT_PROVEN_FOR_INTENT"
    assert outcome["intent_id_sha256"]==case["ident"]
    assert outcome["native_wei_credited"]==str(case["amount"])
    assert outcome["old_v1_payment_claim"] is False
    assert outcome["automatic_retry_authorized"] is False
    assert outcome["production_release_authorized"] is False

@pytest.mark.parametrize("case_name",[
    "wrong_parent_id","unfinalized","failed_parent","wrong_parent_ghost",
    "wrong_parent_value","wrong_parent_data","internal_message",
    "on_accepted","duplicate_parent_message","missing_parent_message",
    "malformed_intent","wrong_intent_commitment",
    "incorrect_payout_tx","wrong_bytecode_pin","wrong_claimed_ghost",
    "wrong_chain","insufficient_confirmations",
    "untrusted_intent_read","untrusted_parent_read",
    "unexpected_address","wrong_wei",
])
def test_forged_or_incomplete_evm_and_parent_evidence_never_proves_credit(case,case_name):
    item=copy.deepcopy(case["item"])
    parent=copy.deepcopy(case["parent"])
    obj={
      "read_finalized_parent":lambda _:parent,
      "read_canonical_intent":lambda _:item,
    }
    if case_name=="wrong_parent_id":parent["id"]="0x"+"aa"*32
    elif case_name=="unfinalized":parent["status_name"]="ACCEPTED"
    elif case_name=="failed_parent":parent["tx_execution_result_name"]="FINISHED_WITH_ERROR"
    elif case_name=="wrong_parent_ghost":parent["recipient"]=case["recipient"]
    elif case_name=="wrong_parent_value":parent["messages"][0]["value"]="0x2"
    elif case_name=="wrong_parent_data":parent["messages"][0]["data"]="0x1234"
    elif case_name=="internal_message":parent["messages"][0]["messageType"]=1
    elif case_name=="on_accepted":parent["messages"][0]["onAcceptance"]=True
    elif case_name=="duplicate_parent_message":parent["messages"].append(dict(parent["messages"][0]))
    elif case_name=="missing_parent_message":parent["messages"]=[]
    elif case_name=="malformed_intent":item["credited"]=True
    elif case_name=="wrong_intent_commitment":item["intent_id_sha256"]="ff"*32
    elif case_name=="incorrect_payout_tx":obj["payout_evm_tx"]="0x"+"dd"*32
    elif case_name=="wrong_bytecode_pin":obj["trusted_router_runtime_sha256"]="00"*32
    elif case_name=="wrong_claimed_ghost":obj["ghost"]=case["outsider"]
    elif case_name=="wrong_chain":obj["expected_chain_id"]=1
    elif case_name=="insufficient_confirmations":obj["minimum_confirmations"]=100
    elif case_name=="untrusted_intent_read":obj["read_canonical_intent"]=lambda _:None
    elif case_name=="untrusted_parent_read":obj["read_finalized_parent"]=lambda _:None
    elif case_name=="unexpected_address":item["recipient"]=case["outsider"].lower()
    elif case_name=="wrong_wei":item["amount_wei"]="5"
    with pytest.raises((EvidenceRejected,ValueError)):
        case["check"](**obj)

def test_evm_logs_are_necessary_parent_cannot_claim_payment_without_log(case):
    ghost=case["ghost"]
    chain=case["chain"]
    other=chain.eth.accounts[0]
    other_tx=chain.eth.send_transaction({"from":other,"to":case["outsider"],"value":1})
    with pytest.raises((EvidenceRejected,ValueError)):
        case["check"](payout_evm_tx=chain.to_hex(other_tx))

def test_a_reverted_evm_payout_is_never_delivery(case):
    chain,router=case["chain"],case["router"]
    tx=execute(chain,router,case["ghost"],bytes.fromhex(case["ident"]),
               case["recipient"],case["amount"])
    assert tx.status==0
    with pytest.raises((EvidenceRejected,ValueError)):
        case["check"](payout_evm_tx=chain.to_hex(tx.transactionHash))

def test_actual_official_genlayer_node_receipt_camelcase_and_numeric_codes(case):
    parent=copy.deepcopy(case["parent"])
    parent["statusName"]="Finalized"
    parent["txExecutionResultName"]="FinishedWithReturn"
    parent["status"]=7
    parent["txExecutionResult"]=1
    parent.pop("status_name")
    parent.pop("tx_execution_result_name")
    proof=case["check"](read_finalized_parent=lambda _:parent)
    assert proof["status"]=="V2_ROUTER_PAYMENT_PROVEN_FOR_INTENT"

@pytest.mark.parametrize("numeric_status,numeric_execution",[
    (5,1),(8,1),(7,2),(7,0)
])
def test_protocol_numeric_codes_cannot_contradict_success(case,numeric_status,numeric_execution):
    parent=copy.deepcopy(case["parent"])
    parent["status"]=numeric_status
    parent["txExecutionResult"]=numeric_execution
    with pytest.raises(EvidenceRejected):
        case["check"](read_finalized_parent=lambda _:parent)

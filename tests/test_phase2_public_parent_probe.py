"""Read-only GenLayer parent/child EVM separation mock tests; ZERO GEN."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase2_public_parent_probe import inspect,PublicReadUnavailable,BRADBURY_GEN,BRADBURY_EVM
from phase8_release_gate import EvidenceRejected

PARENT="0x"+"ab"*32
CHILD="0x"+"cd"*32

def client(*,status="Finalized",execution="FINISHED_WITH_RETURN",child=None,
           fail_children=False,chain="0x107d",missing_messages=False):
    events=[]
    def rpc(endpoint,method,params):
        events.append((endpoint,method))
        if method=="eth_chainId":return chain
        if method=="gen_getTransactionReceipt":
            d={"id":PARENT,"statusName":status,
               "txExecutionResultName":execution,
               "messages":[{"messageType":0,"recipient":"0x"+"11"*20}]}
            if missing_messages:del d["messages"]
            return d
        if method=="gen_getTriggeredTransactionIds":
            if fail_children:raise PublicReadUnavailable("unsupported")
            return [] if child is None else child
        raise EvidenceRejected("unknown method")
    return rpc,events

def test_no_signing_no_delivery_even_with_finalized_parent():
    rpc,seen=client(child=[CHILD])
    result=inspect(PARENT,request=rpc)
    assert result["parent_success_proven"] is True
    assert result["triggered_internal_child_ids"]==[CHILD]
    assert result["intent_to_external_transfer_proof"]=="UNVERIFIED"
    assert result["external_eoa_transfer_evm_proof"]=="NOT_COLLECTED"
    assert all(m in ("eth_chainId","gen_getTransactionReceipt","gen_getTriggeredTransactionIds")
               for _,m in seen)

@pytest.mark.parametrize("status,execution",[
    ("Accepted","FINISHED_WITH_RETURN"),
    ("Finalized","FINISHED_WITH_ERROR"),
    ("Finalized",None),
    (None,"FINISHED_WITH_RETURN"),
])
def test_not_finalized_or_vm_error_never_success(status,execution):
    req,_=client(status=status,execution=execution)
    assert inspect(PARENT,request=req)["parent_success_proven"] is False

def test_unsupported_child_lookup_does_not_become_no_children():
    req,_=client(fail_children=True)
    data=inspect(PARENT,request=req)
    assert data["triggered_internal_child_ids"] is None
    assert data["internal_child_lookup"]=="UNAVAILABLE_NOT_EMPTY"

def test_missing_parent_messages_not_fabricated():
    req,_=client(missing_messages=True)
    out=inspect(PARENT,request=req)
    assert out["emitted_message_count"] is None
    assert out["intent_to_external_transfer_proof"]=="UNVERIFIED"

def test_wrong_chain_and_hash_are_rejected():
    req,_=client(chain="0x1")
    with pytest.raises(EvidenceRejected):inspect(PARENT,request=req)
    req,_=client()
    with pytest.raises(EvidenceRejected):inspect("0xdead",request=req)

def test_no_private_or_signing_methods():
    src=(Path(__file__).resolve().parents[1]/"tools/phase2_public_parent_probe.py").read_text()
    assert "eth_sendRawTransaction" not in src
    assert "eth_sendTransaction" not in src
    assert "private_key" not in src
    assert '"retry_authorized":False' in src

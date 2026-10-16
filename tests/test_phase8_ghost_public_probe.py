"""Mock RPC tests — no actual network and no private-key handling."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase8_release_gate import EvidenceRejected
from phase8_ghost_public_probe import (
    inspect_ghost_call, UnsupportedPublicRPC, ALLOWED,
)
from test_phase8_release_gate import intent, BUYER, SELLER, GHOST, HASH, BLOCK, evm

def backend(**changes):
    tx,receipt,trace=evm()
    data={
        "eth_chainId":"0x107d",
        "eth_getTransactionByHash":tx,
        "eth_getTransactionReceipt":receipt,
        "eth_blockNumber":"0x20",
        "eth_getBlockByNumber":{"number":"0x10","hash":BLOCK},
        "eth_getBalance":{"0xf":"0x64","0x10":"0x6e"},
        "debug_traceTransaction":trace,
    }
    data.update(changes)
    seen=[]
    def request(method,params):
        seen.append(method)
        if method=="eth_getBalance":return data[method][params[1]]
        return data[method]
    return request,seen,data

def test_public_ghost_observer_preserves_unattributed_semantics():
    req,seen,_=backend()
    result=inspect_ghost_call(intent(0,"PAYOUT",10),GHOST,HASH,request=req)
    assert result["observation"]=="GHOST_VALUE_CALL_OBSERVED_UNATTRIBUTED"
    assert result["production_release_authorized"] is False
    assert result["delivery"]=="UNVERIFIED_FOR_SPECIFIC_INTENT"
    assert set(seen).issubset(ALLOWED)
    assert "eth_sendRawTransaction" not in seen
    assert seen.count("eth_getBalance")==2
    assert seen.count("debug_traceTransaction")==1

@pytest.mark.parametrize("which",[
    "wrong_chain","low_confirmations","missing_receipt","wrong_block_hash",
    "no_trace","failed_trace","not_mined","missing_block","balance_mismatch",
    "wrong_sender","wrong_value","reverted_receipt"
])
def test_public_ghost_observer_fail_closed(which):
    request,seen,data=backend()
    if which=="wrong_chain":data["eth_chainId"]="0x1"
    elif which=="low_confirmations":data["eth_blockNumber"]="0x1b"
    elif which=="missing_receipt":data["eth_getTransactionReceipt"]=None
    elif which=="wrong_block_hash":data["eth_getBlockByNumber"]["hash"]="0x"+"12"*32
    elif which=="no_trace":data["debug_traceTransaction"]=None
    elif which=="failed_trace":data["debug_traceTransaction"]["error"]="execution reverted"
    elif which=="not_mined":data["eth_getTransactionReceipt"]["blockNumber"]="0x0"
    elif which=="missing_block":data["eth_getBlockByNumber"]=None
    elif which=="balance_mismatch":data["eth_getBalance"]["0x10"]="0x6f"
    elif which=="wrong_sender":data["debug_traceTransaction"]["calls"][0]["from"]=SELLER
    elif which=="wrong_value":data["debug_traceTransaction"]["calls"][0]["value"]="0x9"
    elif which=="reverted_receipt":data["eth_getTransactionReceipt"]["status"]="0x0"
    with pytest.raises(EvidenceRejected):
        inspect_ghost_call(intent(0,"PAYOUT",10),GHOST,HASH,request=request)
    assert "eth_sendRawTransaction" not in seen

def test_unsupported_trace_rpc_is_blocker_not_fake_success():
    original,seen,data=backend()
    def failed(method,params):
        if method=="debug_traceTransaction":raise UnsupportedPublicRPC("unsupported")
        return original(method,params)
    with pytest.raises(UnsupportedPublicRPC):
        inspect_ghost_call(intent(0,"PAYOUT",10),GHOST,HASH,request=failed)

def test_observer_cannot_be_tricked_into_sending_transactions():
    req,seen,data=backend()
    result=inspect_ghost_call(intent(0,"PAYOUT",10),GHOST,HASH,request=req)
    assert all(method in ALLOWED for method in seen)
    assert result["retry_authorized"] is False

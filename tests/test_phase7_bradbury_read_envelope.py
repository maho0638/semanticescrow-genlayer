"""Bradbury v0.6 status/data gen_call regression; ZERO keys and GEN."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from genlayer_py.contracts import actions,utils
from genlayer_py.abi import calldata
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_bradbury_read_envelope import (
    PINNED_GHOST,BradburyReadMismatch,
    normalize_legacy_gen_call_response,
    install_bradbury_finalized_read_adapter,
)
from phase7_legacy_method_dispatch import install_bradbury_v0216_dispatch

BUYER="0x81Ebc097Ea4F54a9D240719870c504e89B1f5c34"
LOCKED='{"initial_deposit":"100000000000000","remaining_locked":"100000000000000","payout_queued_total":"0","refund_queued_total":"0"}'

@pytest.fixture(autouse=True)
def restore_process_sdk():
    a=actions.make_calldata_object
    u=utils.make_calldata_object
    yield
    actions.make_calldata_object=a
    utils.make_calldata_object=u

def envelope(status=0,data=None):
    if data is None:
        data="0x"+calldata.encode(LOCKED).hex()
    return {"jsonrpc":"2.0","id":1,"result":{
        "status":{"code":status,"message":"success" if status==0 else "failed"},
        "data":data,
    }}

def client(reply=None):
    events=[]
    def original(method,params):
        events.append((method,params))
        return envelope() if reply is None else reply
    provider=SimpleNamespace(make_request=original)
    return SimpleNamespace(chain=SimpleNamespace(id=4221),provider=provider,
                           local_account=SimpleNamespace(address=BUYER)),events

def test_screenshot_public_success_wrapper_normalizes_to_old_sdk_format():
    raw=envelope()
    clean=normalize_legacy_gen_call_response(raw)
    assert clean["result"]==calldata.encode(LOCKED).hex()
    assert raw["result"]["status"]["code"]==0
    assert json.loads(calldata.decode(bytes.fromhex(clean["result"])))["remaining_locked"]=="100000000000000"

def test_legacy_sdk_real_read_contract_runs_against_real_response_shape():
    c,logs=client()
    install_bradbury_v0216_dispatch(c)
    install_bradbury_finalized_read_adapter(c)
    val=actions.read_contract(c,PINNED_GHOST,"get_ledger",args=[0])
    assert json.loads(val)["remaining_locked"]=="100000000000000"
    assert len(logs)==1 and logs[0][0]=="gen_call"
    query=logs[0][1][0]
    assert query["status"]=="finalized"
    assert "transaction_hash_variant" not in query
    assert query["type"]=="read"
    assert query["to"].lower()==PINNED_GHOST.lower()

def test_response_does_not_mutate_original_or_other_rpc_calls():
    r=envelope()
    c,logs=client(r)
    install_bradbury_finalized_read_adapter(c)
    b=c.provider.make_request("gen_call",[{
        "type":"read","to":PINNED_GHOST,"from":BUYER,
        "data":"0xab","transaction_hash_variant":"latest-nonfinal",
    }])
    assert b["result"]==calldata.encode(LOCKED).hex()
    assert "status" not in r
    assert r["result"]["data"].startswith("0x")
    other=c.provider.make_request("eth_getBalance",[BUYER,"latest"])
    assert other is r
    assert len(logs)==2

def test_idempotent_install_never_double_prefixes_decoded_payload():
    c,_=client()
    install_bradbury_finalized_read_adapter(c)
    first=c.provider.make_request
    install_bradbury_finalized_read_adapter(c)
    assert c.provider.make_request is first

@pytest.mark.parametrize("response",[
    {"error":{"code":-32000}},
    {},{"result":None},{"result":[]},
    {"result":{"status":{"code":-1},"data":"0x81"}},
    {"result":{"status":{"code":1},"data":"0x81"}},
    {"result":{"status":{"code":"0"},"data":"0x81"}},
    {"result":{"data":"0x81"}},
    {"result":{"status":{"code":0},"data":None}},
    {"result":{"status":{"code":0},"data":"0x"}},
    {"result":{"status":{"code":0},"data":"0x1"}},
    {"result":{"status":{"code":0},"data":"0x12z4"}},
    {"result":{"status":{"code":0},"data":"0x12","paid":True}},
])
def test_false_or_malformed_evidence_is_always_rejected(response):
    with pytest.raises(BradburyReadMismatch):
        normalize_legacy_gen_call_response(response)

@pytest.mark.parametrize("invalid",[
    {"type":"write","to":PINNED_GHOST,"from":BUYER,"data":"0xab"},
    {"type":"read","to":"0x"+"aa"*20,"from":BUYER,"data":"0xab"},
    {"type":"read","to":PINNED_GHOST,"from":"invalid","data":"0xab"},
    {"type":"read","to":PINNED_GHOST,"from":BUYER,"data":"abcdef"},
    {"type":"read","to":PINNED_GHOST,"from":BUYER,"data":"0x1"},
])
def test_adapter_never_adapts_unverified_or_signed_write_call(invalid):
    c,logs=client()
    install_bradbury_finalized_read_adapter(c)
    with pytest.raises(BradburyReadMismatch):
        c.provider.make_request("gen_call",[invalid])
    assert not logs

def test_chain_mismatch_fails_before_installing():
    c,_=client()
    c.chain.id=1
    before=c.provider.make_request
    with pytest.raises(BradburyReadMismatch):
        install_bradbury_finalized_read_adapter(c)
    assert c.provider.make_request is before

def test_normal_sdk_hex_response_stays_well_formed():
    r={"result":"0x"+calldata.encode(LOCKED).hex()}
    assert normalize_legacy_gen_call_response(r)["result"]==calldata.encode(LOCKED).hex()

def test_public_read_helper_has_no_live_payment_paths():
    src=(Path(__file__).resolve().parents[1]/"tools/phase7_bradbury_read_envelope.py").read_text()
    assert "eth_sendRawTransaction" not in src
    assert "sign_transaction" not in src
    assert "private_key" not in src
    assert "eth_sendTransaction" not in src

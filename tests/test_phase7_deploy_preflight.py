"""Offline safeguards around Brabury deploy gas preview and selective headroom."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_deploy_preflight import (
    padded_gas, DeployPreviewError, install_deploy_gas_headroom
)
from phase7_legacy_compat import CONSENSUS_PROXY

def test_small_contract_headroom_stays_below_reported_bradbury_cap():
    assert padded_gas(13_591_367,100_000_000)==14_950_504

def test_large_original_deploy_fails_before_taking_test_gen():
    with pytest.raises(DeployPreviewError):
        padded_gas(25_444_878,100_000_000)

@pytest.mark.parametrize("est,limit",[(0,10),(-1,10),(100,101),(105,100),(100,0),(14_900_000,100_000_000)])
def test_invalid_headroom_fails_closed(est,limit):
    with pytest.raises(DeployPreviewError):
        padded_gas(est,limit)

def test_scoped_interception_only_pads_verified_consensus_selector():
    seen=[]
    def req(method,params):
        seen.append((method,params))
        if method=="eth_getBlockByNumber":
            return {"result":{"gasLimit":hex(100_000_000)}}
        return {"result":hex(13_591_367)}
    provider=SimpleNamespace(make_request=req)
    client=SimpleNamespace(provider=provider)
    install_deploy_gas_headroom(client)
    tx={"to":CONSENSUS_PROXY,"data":"0xe71d5196"+"00"*32}
    assert int(provider.make_request("eth_estimateGas",[tx])["result"],16)==14_950_504
    assert provider.make_request("eth_estimateGas",[{"to":CONSENSUS_PROXY,"data":"0xdeadbeef"}])["result"]==hex(13_591_367)
    assert provider.make_request("eth_getBalance",["0xab","latest"])["result"]==hex(13_591_367)
    before=len(seen)
    install_deploy_gas_headroom(client)
    assert len(seen)==before

def test_does_not_adjust_rpc_errors():
    provider=SimpleNamespace(make_request=lambda method,params:{"error":{"code":3}})
    client=SimpleNamespace(provider=provider)
    install_deploy_gas_headroom(client)
    assert provider.make_request("eth_estimateGas",[{"to":CONSENSUS_PROXY,"data":"0xe71d5196"}])["error"]["code"]==3

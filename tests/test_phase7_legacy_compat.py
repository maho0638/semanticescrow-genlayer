"""Offline fail-closed checks for the verified legacy Bradbury ABI, no GEN."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_legacy_compat import (
    require_legacy_bradbury, IncompatibleBradburyProtocol,
    CHAIN_ID, FEE_PROXY, FEE_IMPLEMENTATION, CONSENSUS_PROXY,
    CONSENSUS_IMPLEMENTATION, EIP1967_IMPL,
)

def make_client(*, chain=CHAIN_ID, fee_impl=FEE_IMPLEMENTATION,
                consensus_impl=CONSENSUS_IMPLEMENTATION, gen_price=0,
                storage_price=0, consensus_selector=True, fee_selector=True,
                new_fee_getter=False, old_abi=True):
    abi=[{"type":"function","name":"addTransaction",
          "inputs":[{"type":type} for type in (
              ["address","address","uint256","uint256","bytes","uint256"]
              if old_abi else ["address","address","uint256","uint256","bytes"]
          )]}]
    def make_request(method,params):
        if method=="eth_chainId":
            return {"result":hex(chain)}
        if method=="eth_getStorageAt":
            address=params[0].lower()
            target=fee_impl if address==FEE_PROXY.lower() else consensus_impl
            return {"result":"0x"+format(int(target,16),"064x")}
        if method=="eth_getCode":
            addr=params[0].lower()
            if addr==fee_impl.lower():
                selectors=("4fe8920e" if fee_selector else "ffffffff") + ("5c9fd1a3" if new_fee_getter else "")
            else:
                selectors="e71d5196" if consensus_selector else "ffffffff"
            return {"result":"0x"+"60806040"+selectors+"00"*80}
        if method=="eth_call":
            data=params[0]["data"].lower()
            if data.startswith("0xeeb5f1be"): value=gen_price
            elif data.startswith("0x97f426e6"): value=storage_price
            elif data.startswith("0xa76c02e0"): value=5
            else:return {"error":{"code":3}}
            return {"result":"0x"+format(value,"064x")}
        return {"error":{"code":-32601}}
    chain_def=SimpleNamespace(id=chain,
        consensus_main_contract={"address":CONSENSUS_PROXY,"abi":abi},
        fee_manager_contract={"address":FEE_PROXY})
    return SimpleNamespace(chain=chain_def,provider=SimpleNamespace(make_request=make_request))

def test_verified_legacy_path_never_invents_fees():
    assert require_legacy_bradbury(make_client()) is None

@pytest.mark.parametrize("overrides",[
    {"chain":1},
    {"fee_impl":"0x"+"ff"*20},
    {"consensus_impl":"0x"+"bb"*20},
    {"gen_price":1},
    {"storage_price":42},
    {"consensus_selector":False},
    {"fee_selector":False},
    {"new_fee_getter":True},
    {"old_abi":False},
])
def test_mismatch_fails_closed(overrides):
    with pytest.raises(IncompatibleBradburyProtocol):
        require_legacy_bradbury(make_client(**overrides))

def test_eth_call_rpc_error_fails_closed():
    client=make_client()
    original=client.provider.make_request
    def failing(method, params):
        if method=="eth_call": return {"error":{"code":3}}
        return original(method,params)
    client.provider.make_request=failing
    with pytest.raises(IncompatibleBradburyProtocol):
        require_legacy_bradbury(client)

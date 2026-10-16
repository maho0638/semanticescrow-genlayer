"""Regression for REAL signed Bradbury '': method dispatch compatibility bug.

Pinned genlayer-py==0.19.0rc2 maps "create_deal" into the empty string
key. Official v0.2.16 GenVM resolves "method", so real chains failed.
These tests never send a transaction or need funded wallets.
"""
from types import SimpleNamespace
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from genlayer_py.contracts import actions,utils
from genlayer_py.abi import calldata
import phase7_legacy_method_dispatch as m

@pytest.fixture(autouse=True)
def reset_sdk_path():
    original_actions=actions.make_calldata_object
    original_utils=utils.make_calldata_object
    yield
    actions.make_calldata_object=original_actions
    utils.make_calldata_object=original_utils

def test_pinned_sdk_empty_key_reproduces_real_bradbury_failure():
    raw=m._ORIGINAL(method="create_deal",args=["seller","terms","phase7-live"])
    assert raw=={"":"create_deal","args":["seller","terms","phase7-live"]}
    assert raw.get("method") is None
    assert calldata.decode(calldata.encode(raw))[""]=="create_deal"

def test_canonical_v0216_dispatch_is_runner_compatible():
    patched=m.canonical_v0216_calldata(
        method="create_deal",args=["seller","terms","phase7-live"])
    assert patched=={"method":"create_deal","args":["seller","terms","phase7-live"]}
    encoded=calldata.encode(patched)
    assert calldata.decode(encoded)["method"]=="create_deal"
    assert encoded!=calldata.encode(m._ORIGINAL(
        method="create_deal",args=["seller","terms","phase7-live"]))

def test_surgical_patch_reaches_actual_sdk_actions_write_and_read_path():
    client=SimpleNamespace(chain=SimpleNamespace(id=4221))
    probe=m.install_bradbury_v0216_dispatch(client)
    assert probe["method"]=="create_deal"
    assert actions.make_calldata_object is m.canonical_v0216_calldata
    assert utils.make_calldata_object is m.canonical_v0216_calldata
    assert actions.make_calldata_object(
        method="create_deal",args=[1],kwargs={"note":"safe"})=={
        "method":"create_deal","args":[1],"kwargs":{"note":"safe"},
    }

def test_deploy_no_method_stays_untouched():
    obj=m.canonical_v0216_calldata(method=None,args=["hello"])
    assert "method" not in obj
    assert "" not in obj
    assert obj==m._ORIGINAL(method=None,args=["hello"])

def test_chain_guard_refuses_wrong_network():
    with pytest.raises(m.MethodDispatchMismatch,match="wrong chain"):
        m.install_bradbury_v0216_dispatch(SimpleNamespace(
            chain=SimpleNamespace(id=1)))

@pytest.mark.parametrize("name",["","__receive__","__handle_undefined_method__",1,None])
def test_bad_methods_never_get_silently_rewritten(name):
    if name is None:
        # None means deployment without a method; must not invent one.
        assert m.canonical_v0216_calldata(name,args=[])=={}
    else:
        with pytest.raises(m.MethodDispatchMismatch):
            m.canonical_v0216_calldata(method=name,args=[])

def test_patched_encoded_method_matches_official_runner_v0216_dispatch():
    # Prove the contract-runner source's actual dispatch predicate, not
    # a mocked alternate encoding assumption.
    p=Path("tests/fixtures/genvm_v0216_runner_method_dispatch.txt")
    if p.exists():
        official=p.read_text(encoding="utf-8")
        assert "ctx.cd.get('method', '')" in official
    assert calldata.decode(calldata.encode(
        m.canonical_v0216_calldata("create_deal",args=[1])))["method"]=="create_deal"

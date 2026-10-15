"""Offline checks for error-redaction and precise deployment RPC trace."""
import pytest
from types import SimpleNamespace
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_rpc_diagnostics import classification,install_rpc_diagnostics


@pytest.mark.parametrize("message,code,category",[
  ("eth_sendRawTransaction failed (code=-32603): sequencer-leader", "-32603","UPSTREAM_SEQUENCER"),
  ("Response 403 cf-mitigated: challenge", "UNKNOWN","CLOUDFLARE_CHALLENGE"),
  ("eth_sendRawTransaction failed (code=-32000): insufficient funds", "-32000","INSUFFICIENT_FUNDS"),
  ("eth_sendRawTransaction failed (code=-32098): PowerShell RPC transport failed",
     "-32098", "LOCAL_GATEWAY_TRANSPORT"),
  ("eth_sendRawTransaction failed (code=-32603): no detail", "-32603","UNCLASSIFIED"),
])
def test_classification_only_publishes_whitelist(message,code,category):
    assert classification(RuntimeError(message)) == (code,category)


def test_signed_transaction_not_logged(capsys):
    # Even if the upstream error includes raw secret markers, never echo it.
    sensitive="PRIVATE_KEY_ABC0123456789"
    def rpc(method,params):
        raise RuntimeError("eth_sendRawTransaction failed (code=-32603): "+sensitive)
    obj=SimpleNamespace(provider=SimpleNamespace(make_request=rpc))
    install_rpc_diagnostics(obj)
    with pytest.raises(RuntimeError):
        obj.provider.make_request("eth_sendRawTransaction",["0x"+"ab"*40])
    output=capsys.readouterr().out
    assert sensitive not in output
    assert "SE7_PUBLIC_RPC_SEND_BEGIN 40" in output
    assert "SE7_PUBLIC_RPC_EXCEPTION eth_sendRawTransaction" in output
    assert "CODE -32603" in output


def test_success_emits_only_public_hash(capsys):
    h="0x"+"ab"*32
    obj=SimpleNamespace(provider=SimpleNamespace(
        make_request=lambda method,params:{"result":h}
    ))
    install_rpc_diagnostics(obj)
    assert obj.provider.make_request("eth_sendRawTransaction",["0xab"])["result"]==h
    text=capsys.readouterr().out
    assert "SE7_PUBLIC_RPC_SEND_RESULT "+h in text
    install_rpc_diagnostics(obj)
    assert obj.provider._phase7_diagnostics_installed is True


def test_only_relevant_rpc_error_is_reported(capsys):
    def fail(method,params): raise RuntimeError("oops SECRETXYZ")
    obj=SimpleNamespace(provider=SimpleNamespace(make_request=fail))
    install_rpc_diagnostics(obj)
    with pytest.raises(RuntimeError):
        obj.provider.make_request("eth_getBalance",["0x01","latest"])
    assert capsys.readouterr().out == ""

"""Offline safety regression for local PowerShell RPC transport (no GEN, no RPC)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import phase7_windows_rpc_bridge as relay


def request(url, payload):
    data = json.dumps(payload).encode("utf-8")
    with urlopen(Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=4) as r:
        return r.status, json.loads(r.read())


def test_loopback_forward_uses_only_hardcoded_bradbury_and_private_path(monkeypatch):
    seen = []
    def fake_run(cmd, input, **kwargs):
        seen.append((cmd, input, kwargs))
        return SimpleNamespace(returncode=0,
                               stdout='{"jsonrpc":"2.0","result":"0x107d","id":1}')
    monkeypatch.setattr(relay.subprocess, "run", fake_run)
    b = relay.PowerShellRpcBridge()
    b.start()
    try:
        assert b.url.startswith("http://127.0.0.1:")
        assert b.url.count("/") >= 3
        status, result = request(b.url, {"jsonrpc":"2.0","id":1,
                                          "method":"eth_chainId","params":[]})
        assert status == 200 and result["result"] == "0x107d"
        assert len(seen) == 1
        assert seen[0][0][0] == "powershell.exe"
        assert relay.UPSTREAM in seen[0][0][-1]
        assert seen[0][2]["capture_output"] is True
        bad = b.url.rsplit("/", 1)[0] + "/wrong"
        try:
            request(bad, {"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]})
            raise AssertionError("unauthorized loopback path accepted")
        except HTTPError as exc:
            assert exc.code == 404
        assert len(seen) == 1
    finally:
        b.close()


def test_failure_does_not_expose_upstream_details_or_secrets(monkeypatch):
    monkeypatch.setattr(relay.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1,
                               stdout="", stderr="private_key=DO_NOT_EXPOSE"))
    b = relay.PowerShellRpcBridge()
    b.start()
    try:
        try:
            request(b.url, {"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]})
            raise AssertionError("forwarding error was treated as success")
        except HTTPError as exc:
            assert exc.code == 502
            reply = exc.read().decode()
            assert "PowerShell RPC transport failed" in reply
            assert "private_key" not in reply
            assert "DO_NOT_EXPOSE" not in reply
    finally:
        b.close()

"""Loopback-only RPC bridge for a Windows PowerShell client accepted by Bradbury.

The upstream address is hardcoded. No external proxy, bypass credentials,
browser cookies, keys, mnemonic files, or public ports. Signed raw transactions
are already public blockchain payloads; private account keys are never sent.

Every forward uses native Invoke-RestMethod, identical in kind to the
PowerShell command that successfully returned eth_chainId on this machine.
"""
import json
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://rpc-bradbury.genlayer.com"
MAX_BODY = 3 * 1024 * 1024
POWER_SHELL_CODE = (
    "$ErrorActionPreference='Stop';"
    "$ProgressPreference='SilentlyContinue';"
    "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false);"
    "$raw=[Console]::In.ReadToEnd();"
    "$answer=Invoke-RestMethod -Uri '" + UPSTREAM + "'"
    " -Method Post -ContentType 'application/json'"
    " -Body $raw -TimeoutSec 40;"
    "$json=ConvertTo-Json -InputObject $answer -Depth 100 -Compress;"
    "[Console]::Out.Write($json)"
)


def forward_with_powershell(raw):
    """Return serialized JSON-RPC exactly once; fail closed on malformed data."""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", POWER_SHELL_CODE],
        input=raw, text=True, capture_output=True, timeout=55,
        encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError("PowerShell upstream transport failure")
    response = result.stdout.strip()
    try:
        parsed = json.loads(response)
        if not isinstance(parsed, (dict, list)):
            raise ValueError("Invalid JSON-RPC response container")
        if isinstance(parsed, dict) and parsed.get("jsonrpc") != "2.0":
            raise ValueError("Missing JSON-RPC version")
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PowerShell upstream returned malformed JSON-RPC") from exc
    return response.encode("utf-8")


class PowerShellRpcBridge:
    """Bind 127.0.0.1 to an OS-assigned port, protected by a random URL path."""

    def __init__(self):
        self._token = secrets.token_urlsafe(24)
        self._server = None
        self._thread = None
        self.url = None

    def start(self):
        path = "/" + self._token
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                # Never log JSON-RPC body, auth path or response.
                pass

            def do_GET(self):
                self.send_error(405)

            def do_POST(self):
                if self.path != path:
                    self.send_error(404)
                    return
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    n = 0
                if not 0 < n <= MAX_BODY:
                    self.send_error(413)
                    return
                body = self.rfile.read(n)
                try:
                    request = json.loads(body)
                    if not isinstance(request, (dict, list)):
                        raise ValueError()
                    reply = forward_with_powershell(body.decode("utf-8"))
                    self.send_response(200)
                except (UnicodeDecodeError, ValueError, TypeError):
                    reply = b'{"jsonrpc":"2.0","id":null,"error":{"code":-32600,"message":"Invalid RPC request"}}'
                    self.send_response(400)
                except (RuntimeError, subprocess.TimeoutExpired, OSError):
                    reply = b'{"jsonrpc":"2.0","id":null,"error":{"code":-32098,"message":"PowerShell RPC transport failed"}}'
                    self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.url = "http://127.0.0.1:" + str(self._server.server_address[1]) + path
        return self.url

    def close(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            if self._thread:
                self._thread.join(timeout=3)
            self._server = None

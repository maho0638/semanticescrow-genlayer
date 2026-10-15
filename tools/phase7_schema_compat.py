"""Scoped Studio-dev schema compatibility for the exact SemanticEscrow source.

Bradbury's pinned GenLayer SDK cannot fetch schema for code outside localnet;
the deployed old Bradbury protocol also lacks the SDK's modern price policy.
Studio-dev JSON-RPC supports gen_getContractSchemaForCode for the very same
public source bytes (2026-10-15 read-only confirmed).

No user keys, mnemonic, tokens, wallet, authentication, or writes.
Do not use arbitrary provider URLs, cached schema from unrelated contracts,
or infer successful deployment from a schema result.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

STUDIO_DEV = "https://studio-dev.genlayer.com/api"
SOURCE_SHA256 = "24cee2dd31e38cde646911fb5ae6ca1c0f46b82b8349ea4919199119115a94d5"
REQUIRED_METHODS = frozenset((
    "assess", "assess_challenge", "challenge", "confirm_cancel",
    "create_deal", "deal_count", "get_assessment", "get_deal",
    "get_ledger", "get_milestone", "get_terms_digest", "get_total_locked",
    "get_transfer_intent", "get_transfer_intents", "propose_cancel",
    "settle", "submit_evidence",
))


class SchemaUnavailable(RuntimeError):
    pass


def _check_source(factory):
    if not isinstance(factory.contract_code, str):
        raise SchemaUnavailable("not a text-source contract")
    code = factory.contract_code.encode("utf-8")
    if hashlib.sha256(code).hexdigest() != SOURCE_SHA256:
        raise SchemaUnavailable("contract source mismatch; refuse unchecked schema")
    return code


def _check_result(data):
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or data.get("error"):
        raise SchemaUnavailable("remote schema RPC returned an error")
    schema = data.get("result")
    if not isinstance(schema, dict) or not isinstance(schema.get("methods"), dict):
        raise SchemaUnavailable("missing or malformed compiled contract schema")
    if set(schema["methods"].keys()) != REQUIRED_METHODS:
        raise SchemaUnavailable("method set differs from pinned SemanticEscrow source")
    if "ctor" not in schema:
        raise SchemaUnavailable("missing constructor schema")
    return schema


def _powershell_request(payload):
    if os.name != "nt":
        raise SchemaUnavailable("Windows-only fallback unavailable")
    # Only the known public Studio-dev RPC is allowed; the payload contains
    # contract source only, never private keys or account data.
    script = (
        "$ErrorActionPreference='Stop';"
        "$ProgressPreference='SilentlyContinue';"
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
        "$raw=[Console]::In.ReadToEnd();"
        "$value=Invoke-RestMethod -Uri '" + STUDIO_DEV + "'"
        " -Method Post -ContentType 'application/json'"
        " -Body $raw -TimeoutSec 80;"
        "[Console]::Out.Write((ConvertTo-Json -InputObject $value -Depth 100 -Compress))"
    )
    try:
        process = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            input=json.dumps(payload), capture_output=True, text=True, timeout=95,
            encoding="utf-8", errors="replace",
        )
        if process.returncode != 0:
            raise SchemaUnavailable("Studio-dev PowerShell RPC failed")
        return json.loads(process.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise SchemaUnavailable("Studio-dev PowerShell RPC unavailable") from exc


def fetch_verified_schema(factory):
    code = _check_source(factory)
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "gen_getContractSchemaForCode",
        "params": ["0x" + code.hex()],
    }
    try:
        response = requests.post(STUDIO_DEV, json=body, timeout=80)
        if response.status_code == 200:
            try:
                return _check_result(response.json())
            except (ValueError, SchemaUnavailable):
                # Could be a compiler error; try the already-working
                # PowerShell transport on Windows before failing closed.
                pass
    except requests.RequestException:
        pass
    return _check_result(_powershell_request(body))


def bind_verified_schema(factory):
    """Bind only one ContractFactory instance; never mutate SDK globally."""
    schema = fetch_verified_schema(factory)
    factory._get_schema_with_fallback = lambda: schema
    return schema

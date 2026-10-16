"""Bradbury v0.6 public gen_call response compatibility — READ ONLY.

2026-10-16 public proof showed finalized GenVM create_deal SUCCESS, deal_count
1, get_ledger(0) and get_deal(0) readable with explicit status='finalized'.
Yet the installed genlayer-py 0.19.0rc2 read_contract expects result:
hex string and prepends '0x', whereas this Bradbury endpoint returns:
{'status':{'code':0,'message':'success'},'data':'0x...'}

This strictly scoped adapter performs:
  1. A read-only, exact-ghost query at finalized state, never pending;
  2. verified successful RPC envelope => unprefixed hex for pinned SDK;
  3. fail closed on malformed/errors/other chains/targets.
No signer, key, payment, contract code, write transaction or wallet is changed.
"""
from __future__ import annotations

import re

BRADBURY_CHAIN_ID = 4221
PINNED_GHOST = "0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a"

class BradburyReadMismatch(RuntimeError):
    pass

def normalize_legacy_gen_call_response(response):
    """Return genlayer-py legacy result as raw non-0x-prefixed hex bytes.

    Never mark an unsuccessful or unknown runtime status as success.
    """
    if type(response) is not dict or response.get("error"):
        raise BradburyReadMismatch("gen_call RPC error")
    data = response.get("result")
    if type(data) is str:
        payload = data
    elif type(data) is dict:
        # Public GenLayer Node gen_call includes execution metadata alongside
        # status/data. Previous exact-key guard rejected SUCCESSFUL reads.
        # Match the official node API v0.2.x response schema, not an invented
        # two-field response. Fail closed on unknown or malformed metadata.
        metadata = {
            "eqOutputs": list, "stdout": str, "stderr": str,
            "logs": list, "events": list, "messages": list,
            "nondetDisagreementCallNo": (int, type(None)),
        }
        if not {"status", "data"}.issubset(data):
            raise BradburyReadMismatch("missing gen_call status/data")
        extra=set(data)-{"status", "data"}
        if extra - set(metadata):
            raise BradburyReadMismatch("unrecognized gen_call execution metadata")
        for key in extra:
            if not isinstance(data[key], metadata[key]) or (
                key == "nondetDisagreementCallNo" and type(data[key]) is bool
            ):
                raise BradburyReadMismatch("malformed gen_call execution metadata")
        status = data["status"]
        if type(status) is not dict or type(status.get("code")) is not int or status["code"] != 0:
            raise BradburyReadMismatch("GenVM read was not successful")
        payload = data["data"]
    else:
        raise BradburyReadMismatch("missing GenVM read payload")
    if type(payload) is not str:
        raise BradburyReadMismatch("non-hex GenVM read")
    if payload.startswith("0x"):
        payload=payload[2:]
    if not payload or len(payload) % 2 or re.fullmatch(r"[0-9a-fA-F]+",payload) is None:
        raise BradburyReadMismatch("malformed GenVM read encoding")
    clean = response.copy()
    clean["result"] = payload
    return clean

def install_bradbury_finalized_read_adapter(client):
    """Patch only the public read RPC of the already validated old contract."""
    if type(client.chain.id) is not int or client.chain.id != BRADBURY_CHAIN_ID:
        raise BradburyReadMismatch("not the source-verified Bradbury chain")
    provider=client.provider
    if getattr(provider,"_phase7_v06_finalized_read_installed",False):
        return
    original=provider.make_request

    def read_only(method,params):
        if method != "gen_call":
            return original(method,params)
        if type(params) is not list or len(params)!=1 or type(params[0]) is not dict:
            raise BradburyReadMismatch("unrecognized read payload")
        req=params[0]
        if req.get("type")!="read" or type(req.get("to")) is not str or (
            req["to"].lower()!=PINNED_GHOST
        ):
            raise BradburyReadMismatch("cannot adapt an unverified contract/read")
        if type(req.get("from")) is not str or not re.fullmatch(
            r"0x[0-9a-fA-F]{40}",req["from"]
        ):
            raise BradburyReadMismatch("reader address missing")
        if type(req.get("data")) is not str or re.fullmatch(
            r"0x[0-9a-fA-F]+",req["data"]
        ) is None or len(req["data"])%2:
            raise BradburyReadMismatch("bad GenVM read calldata")
        # Source-pinned old v0.6 Bradbury supports the explicit 'finalized'
        # read-state selector used by the successful zero-GEN diagnostic.
        # Its Python RC client defaults to a newer non-final selector.
        request={k:v for k,v in req.items() if k not in (
            "transaction_hash_variant","status"
        )}
        request["status"]="finalized"
        return normalize_legacy_gen_call_response(original(method,[request]))

    provider.make_request=read_only
    provider._phase7_v06_finalized_read_installed=True

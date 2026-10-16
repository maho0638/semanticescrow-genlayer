"""Attest and reuse exact 2026-10-16 Bradbury deployment; read-only.

This reuses an actual successful GenVM execution only AFTER protocol finality.
It never signs, spends GEN, or accepts a successful EVM receipt as GenVM proof.
"""
from phase7_deploy_preflight import _build_payload
from phase7_legacy_compat import CONSENSUS_PROXY
from phase7_legacy_receipts import read_bradbury_transaction, is_finalized_success

EVM_TX="0x2bddc2919cde1aee0cc751e3735daa7e0ecc9fbcbab91b2bc28dd6d698455bf8"
GENLAYER_TX="0x1ac72cb02a02cdf8709615b8aeed51610128dddd1a87128b58623aab73220c43"
ORIGINAL_BUYER="0x1B982344f53257768E971DBb152907cBa33D632C"
GHOST="0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a"

class ReuseNotVerified(RuntimeError):
    pass

def _call(client,method,args):
    r=client.provider.make_request(method,args)
    if not isinstance(r,dict) or r.get("error") or "result" not in r:
        raise ReuseNotVerified("read-only RPC "+method+" failed")
    return r["result"]

def _number(value):
    if not isinstance(value,str) or not value.startswith("0x"):
        raise ReuseNotVerified("invalid numeric RPC result")
    return int(value,16)

def verify_existing_finalized_deployment(client,source):
    """Read-only check of exact signed input, parent finality and Ghost code.

    Caller must FIRST run require_legacy_bradbury(client) and prove the
    verified old six-input ABI; _build_payload asserts source hash and chain.
    """
    if _number(_call(client,"eth_chainId",[]))!=4221:
        raise ReuseNotVerified("wrong chain")
    tx=_call(client,"eth_getTransactionByHash",[EVM_TX])
    receipt=_call(client,"eth_getTransactionReceipt",[EVM_TX])
    if not isinstance(tx,dict) or not isinstance(receipt,dict):
        raise ReuseNotVerified("existing EVM tx or receipt missing")
    if str(tx.get("hash","")).lower()!=EVM_TX or str(receipt.get("transactionHash","")).lower()!=EVM_TX:
        raise ReuseNotVerified("existing EVM tx hash mismatch")
    if str(tx.get("from","")).lower()!=ORIGINAL_BUYER.lower() or str(tx.get("to","")).lower()!=CONSENSUS_PROXY.lower():
        raise ReuseNotVerified("existing EVM sender or consensus target mismatch")
    if str(receipt.get("to","")).lower()!=CONSENSUS_PROXY.lower() or _number(receipt.get("status"))!=1 or _number(receipt.get("blockNumber"))<=0:
        raise ReuseNotVerified("existing EVM receipt failed")
    # Exact encoded contract source and SDK legacy ABI call arguments must
    # match what was signed and INCLUDED; no lookalike Ghost/contract addresses.
    expected=_build_payload(client,source,ORIGINAL_BUYER)
    if str(tx.get("input","")).lower()!=expected.lower():
        raise ReuseNotVerified("existing deployment calldata/source hash mismatch")
    record=read_bradbury_transaction(client,GENLAYER_TX)
    if str(record.get("tx_data_decoded",{}).get("contract_address","")).lower()!=GHOST.lower():
        raise ReuseNotVerified("existing consensus Ghost address mismatch")
    if not is_finalized_success(record):
        raise ReuseNotVerified("existing GenLayer deployment not FINALIZED + FINISHED_WITH_RETURN")
    code=_call(client,"eth_getCode",[GHOST,"latest"])
    if not isinstance(code,str) or len(code)<=2 or code=="0x":
        raise ReuseNotVerified("existing Ghost runtime code absent")
    return GHOST

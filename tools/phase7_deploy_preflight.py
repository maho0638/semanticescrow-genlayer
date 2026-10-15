"""Read-only Bradbury deploy gas preview and scoped EVM gas headroom.

Applies ONLY to chain-4221, onchain-attested old addTransaction 0xe71d5196,
and a single gltest in-memory SDK client. Never signs or broadcasts during the
preview; the actual test's SDK still signs independently after user funding.
Refuses to send with unknown chain/proxy, missing gas estimate or gas > block.
"""
import hashlib
from types import SimpleNamespace

from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.contracts.utils import make_calldata_object
from genlayer_py.transactions.fees import normalize_transaction_fees

from phase7_legacy_compat import CONSENSUS_PROXY, LEGACY_CONSENSUS_ADD
from phase7_schema_compat import SOURCE_SHA256

# Existing public EOA received 5 TEST GEN, but its signing key was destroyed.
# Never fund it again. Read-only EVM sender simulation does NOT need its key.
PUBLIC_READONLY_SENDER = "0x84D37542B362F96282b19D479cF9b06E15ff62eA"
PRIORITY_FEE_WEI = 2_000_000_000
# GenLayer CLI #419 documents 16M gas being rejected at Bradbury.
# This is a conservative release gate, not a proven per-transaction maximum.
MAX_SAFE_LEGACY_GAS = 15_000_000
MIN_HEADROOM = 1_000_000


class DeployPreviewError(RuntimeError):
    pass


def _hex(value):
    if not isinstance(value,str) or not value.startswith("0x"):
        raise DeployPreviewError("RPC hex result missing")
    return int(value,16)


def _rpc(provider,method,params):
    result=provider.make_request(method,params)
    if not isinstance(result,dict) or "error" in result or "result" not in result:
        raise DeployPreviewError("read-only RPC "+method+" unavailable")
    return result["result"]


def padded_gas(estimated, limit):
    estimated=int(estimated)
    limit=int(limit)
    if estimated<=0 or limit<=0:
        raise DeployPreviewError("invalid estimate or block gas limit")
    # 10% or at least 1M gas headroom while respecting empirical
    # sub-16M Bradbury acceptance ceiling (GenLayer CLI issue #419).
    if estimated>=MAX_SAFE_LEGACY_GAS:
        raise DeployPreviewError("deploy estimate exceeds Bradbury safe gas ceiling")
    padded=estimated+max(MIN_HEADROOM,(estimated+9)//10)
    if padded>MAX_SAFE_LEGACY_GAS:
        raise DeployPreviewError("insufficient safe headroom under Bradbury gas ceiling")
    if padded>limit:
        raise DeployPreviewError("padded gas exceeds block limit")
    return padded


def _build_payload(client,source,sender):
    if getattr(client.chain,"id",None)!=4221:
        raise DeployPreviewError("wrong chain")
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA256:
        raise DeployPreviewError("different source bytes")
    schema=client.chain.consensus_main_contract["abi"]
    methods=[m for m in schema if m.get("name")=="addTransaction" and m.get("type")=="function"]
    if len(methods)!=1 or [x.get("type") for x in methods[0].get("inputs",[])]!=[
        "address","address","uint256","uint256","bytes","uint256"
    ]:raise DeployPreviewError("legacy consensus ABI not installed")
    encoded=serialize([source,calldata.encode(make_calldata_object(method=None,args=None,kwargs=None)),False])
    raw=_encode_add_transaction_data(client,SimpleNamespace(address=sender),
        "0x0000000000000000000000000000000000000000",3,encoded,
        transaction_fees=normalize_transaction_fees())
    if not raw.lower().startswith("0x"+LEGACY_CONSENSUS_ADD):
        raise DeployPreviewError("wrong transaction selector")
    return raw


def preview_deploy(client,source,sender=PUBLIC_READONLY_SENDER):
    """Read-only deploy preview; use actual funded sender before signing.

    Default historical sender is ONLY for an unfunded network preflight.
    The signed integration test MUST pass its own funded buyer address.
    """
    provider=client.provider
    payload=_build_payload(client,source,sender)
    block=_rpc(provider,"eth_getBlockByNumber",["latest",False])
    if not isinstance(block,dict):
        raise DeployPreviewError("unavailable latest block")
    limit=_hex(block["gasLimit"])
    base=_hex(block["baseFeePerGas"])
    bal=_hex(_rpc(provider,"eth_getBalance",[sender,"latest"]))
    nonce=_rpc(provider,"eth_getTransactionCount",[sender,"latest"])
    tx={"from":sender, "to":CONSENSUS_PROXY,
        "data":payload, "value":"0x0","nonce":nonce,"chainId":"0x107d",
        "maxFeePerGas":hex(base+PRIORITY_FEE_WEI),
        "maxPriorityFeePerGas":hex(PRIORITY_FEE_WEI)}
    estimate=_hex(_rpc(provider,"eth_estimateGas",[tx]))
    safe=padded_gas(estimate,limit)
    if safe*(base+PRIORITY_FEE_WEI)>bal:
        raise DeployPreviewError("read-only source has too little test GEN for simulation")
    answer=_rpc(provider,"eth_call",[{**tx,"gas":hex(safe)},"latest"])
    if not isinstance(answer,str) or not answer.startswith("0x"):
        raise DeployPreviewError("padded GenLayer deploy simulation failed")
    return {"estimated_gas":estimate,"padded_gas":safe,"block_gas_limit":limit}


def install_deploy_gas_headroom(client):
    """Wrap only this client, only old ConsensusMain addTransaction estimates.

    Must only be called AFTER require_legacy_bradbury's read-only attestation,
    and AFTER a successful padded preview. Other RPCs and gas estimates are
    passed through unchanged. The wrapper does not broadcast transactions.
    """
    provider=client.provider
    if getattr(provider,"_phase7_headroom_installed",False):
        return
    original=provider.make_request
    def guarded(method,params):
        response=original(method,params)
        if method!="eth_estimateGas" or not isinstance(response,dict) or response.get("error"):
            return response
        if not isinstance(params,list) or not params or not isinstance(params[0],dict):
            return response
        tx=params[0]
        if str(tx.get("to","")).lower()!=CONSENSUS_PROXY.lower():
            return response
        if not str(tx.get("data","")).lower().startswith("0x"+LEGACY_CONSENSUS_ADD):
            return response
        block=_rpc(provider,"eth_getBlockByNumber",["latest",False])
        safe=padded_gas(_hex(response["result"]),_hex(block["gasLimit"]))
        print("SE7_PUBLIC_GAS_HEADROOM_APPLIED",_hex(response["result"]),safe,flush=True)
        return {**response,"result":hex(safe)}
    provider.make_request=guarded
    provider._phase7_headroom_installed=True

"""Public-only EVM Ghost delivery observation for phase-8 release audit.

This deliberately NEVER signs, funds wallets, retries a payment, or labels an
individual SemanticEscrow transfer intent as delivered. External value may
flow through a Ghost's internal handleOp CALL, so receipt.to=recipient is not
a valid assumption. The public RPC may not support debug_traceTransaction:
that case must remain UNVERIFIED rather than a false PASS.

Invoke only after a finalized escrow/cancellation flow yields an independently
identified EVM *finalization* transaction hash and frozen intent JSON.
"""
import argparse
import json
import re
from pathlib import Path

from phase8_release_gate import (
    EvidenceRejected, address, assess_evm_transfer_observation,
    rpc_quantity, require,
)

RPC = "https://rpc.testnet-chain.genlayer.com"
ALLOWED = frozenset({
    "eth_chainId","eth_blockNumber","eth_getTransactionByHash",
    "eth_getTransactionReceipt","eth_getBlockByNumber","eth_getBalance",
    "debug_traceTransaction",
})

class UnsupportedPublicRPC(EvidenceRejected):
    pass

def public_jsonrpc(method, params):
    require(method in ALLOWED, "prohibited RPC operation")
    import requests
    try:
        response=requests.post(
            RPC, json={"jsonrpc":"2.0","id":8,"method":method,"params":params},
            timeout=25,
        )
        if response.status_code!=200:
            raise UnsupportedPublicRPC("public_rpc_http_unavailable")
        data=response.json()
    except (requests.RequestException,ValueError,TypeError) as exc:
        raise UnsupportedPublicRPC("public_rpc_transport_unavailable") from exc
    if not isinstance(data,dict) or "error" in data or "result" not in data:
        raise UnsupportedPublicRPC("public_rpc_method_or_result_unavailable")
    return data["result"]


def inspect_ghost_call(intent, ghost, tx_hash, *, request=public_jsonrpc):
    # Refuse accidental wrong chain and fake pending transactions.
    require(rpc_quantity(request("eth_chainId",[]))==4221, "wrong EVM chain")
    tx=request("eth_getTransactionByHash",[tx_hash])
    receipt=request("eth_getTransactionReceipt",[tx_hash])
    require(isinstance(tx,dict) and isinstance(receipt,dict),
            "transaction or EVM receipt missing")
    block_number=rpc_quantity(receipt.get("blockNumber"))
    require(block_number>0, "not included in non-genesis block")
    latest=rpc_quantity(request("eth_blockNumber",[]))
    require(latest>=block_number+12, "insufficient confirmations")
    block=request("eth_getBlockByNumber",[hex(block_number),False])
    require(isinstance(block,dict) and block.get("hash"), "canonical EVM block unavailable")
    prior=request("eth_getBalance",[address(intent["recipient"]),hex(block_number-1)])
    after=request("eth_getBalance",[address(intent["recipient"]),hex(block_number)])
    # Many operators deny debug_traceTransaction. Never guess child credit if
    # trace unavailable; no self-generated evidence or private proxy used.
    trace=request("debug_traceTransaction",[tx_hash,{"tracer":"callTracer","timeout":"15s"}])
    require(isinstance(trace,dict), "no internal Ghost call trace")
    return assess_evm_transfer_observation(
        intent,ghost=ghost,tx_hash=tx_hash,tx=tx,receipt=receipt,trace=trace,
        before_wei=str(rpc_quantity(prior)),after_wei=str(rpc_quantity(after)),
        block_hash=block["hash"],confirmations=latest-block_number,
    )


def main():
    ap=argparse.ArgumentParser(
        description="Read-only Ghost value CALL observer (NOT a release approval)")
    ap.add_argument("--intent-json",required=True,help="locally exported read-only intent row")
    ap.add_argument("--ghost",required=True)
    ap.add_argument("--evm-tx",required=True)
    args=ap.parse_args()
    try:
        require(re.fullmatch(r"0x[0-9a-fA-F]{64}",args.evm_tx) is not None,
                "invalid transaction hash")
        intent=json.loads(Path(args.intent_json).read_text(encoding="utf-8"))
        report=inspect_ghost_call(intent,args.ghost,args.evm_tx)
        print(json.dumps(report,sort_keys=True))
        print("SE8_PUBLIC_ONLY_TRANSFER_OBSERVED_NOT_ATTRIBUTED")
        return 0
    except (EvidenceRejected,ValueError,KeyError,OSError) as exc:
        # Errors are fixed classes/short codes. Avoid private JSON log leaks.
        label = str(exc) if type(exc) in (EvidenceRejected,UnsupportedPublicRPC) else type(exc).__name__
        print("SE8_UNVERIFIED",label[:100])
        return 2

if __name__=="__main__":
    raise SystemExit(main())

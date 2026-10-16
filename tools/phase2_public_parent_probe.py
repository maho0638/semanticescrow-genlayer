"""Public-only protocol inspection for escrow payout attribution (NO signing).

Separates parent GenLayer tx status, internal child IDs and EVM Ghost value.
Returns a *read-only diagnostic*, never 'paid'. Testnet v0.6 public node
can return 403/-32601: the only truthful result is UNVERIFIED.
"""
import argparse
import json
import urllib.request
import urllib.error

from phase8_release_gate import EvidenceRejected,require,RE_TX

BRADBURY_GEN="https://rpc-bradbury.genlayer.com"
BRADBURY_EVM="https://rpc.testnet-chain.genlayer.com"
METHODS=frozenset({
    "eth_chainId","eth_getTransactionReceipt","eth_getTransactionByHash",
    "gen_getTransactionReceipt","gen_getTriggeredTransactionIds",
})
class PublicReadUnavailable(EvidenceRejected):
    pass

def rpc(endpoint,method,params):
    require(endpoint in (BRADBURY_GEN,BRADBURY_EVM) and method in METHODS,
            "prohibited RPC request")
    data=json.dumps({"jsonrpc":"2.0","id":5,"method":method,"params":params}).encode()
    req=urllib.request.Request(endpoint,data=data,headers={
        "Content-Type":"application/json","Accept":"application/json",
    },method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            result=json.load(r)
    except (urllib.error.URLError,ValueError,TimeoutError) as e:
        raise PublicReadUnavailable("endpoint or method unavailable") from e
    if type(result) is not dict or "error" in result or "result" not in result:
        raise PublicReadUnavailable("RPC result unavailable; do not infer absence of children")
    return result["result"]

def inspect(parent_tx,*,request=rpc):
    require(type(parent_tx) is str and RE_TX.fullmatch(parent_tx),
            "invalid parent GenLayer id")
    chain=request(BRADBURY_EVM,"eth_chainId",[])
    require(chain=="0x107d","wrong chain: expected Bradbury 4221")
    parent=request(BRADBURY_GEN,"gen_getTransactionReceipt",[{"txId":parent_tx}])
    require(type(parent) is dict,"missing protocol parent receipt")
    require(str(parent.get("id","")).lower()==parent_tx.lower(),
            "protocol transaction ID mismatch")
    status=parent.get("statusName")
    execution=parent.get("txExecutionResultName")
    success=status in ("Finalized","FINALIZED") and execution in (
        "FINISHED_WITH_RETURN","FinishedWithReturn")
    # The v0.6 node may omit the successful-execution name. That is an
    # explicit unknown, NEVER a synthetically successful receipt.
    msg=parent.get("messages")
    messages=len(msg) if type(msg) is list else None
    try:
        child=request(BRADBURY_GEN,"gen_getTriggeredTransactionIds",[{"txId":parent_tx}])
        if type(child) is not list:
            raise PublicReadUnavailable("triggered child list malformed")
        children=child
        child_source="PUBLIC_GENLAYER_RPC"
    except PublicReadUnavailable:
        children=None
        child_source="UNAVAILABLE_NOT_EMPTY"
    return {
        "parent_genlayer_tx":parent_tx.lower(),
        "stored_parent_status":status,
        "execution_result":execution,
        "parent_success_proven":bool(success),
        "emitted_message_count":messages,
        "triggered_internal_child_ids":children,
        "internal_child_lookup":child_source,
        "external_eoa_transfer_evm_proof":"NOT_COLLECTED",
        "intent_to_external_transfer_proof":"UNVERIFIED",
        "retry_authorized":False,
        "production_release_authorized":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description="Bradbury READ-ONLY parent/child check, zero GEN")
    parser.add_argument("--parent-genlayer-tx",required=True)
    options=parser.parse_args(argv)
    try:
        result=inspect(options.parent_genlayer_tx)
    except (EvidenceRejected,TypeError,ValueError) as err:
        print("SE_PAYMENT_PROOF_UNVERIFIED",type(err).__name__)
        return 2
    print(json.dumps(result,sort_keys=True))
    print("SE_PAYMENT_PROOF_NO_SIGNING_NO_GEN_NO_RETRY")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

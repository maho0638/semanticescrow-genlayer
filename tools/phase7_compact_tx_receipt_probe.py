"""Public read-only Bradbury EVM tx / receipt postmortem for compact contract.

One user-supplied public transaction hash; no wallet keys, ETH signing, token
movement or sensitive runtime records. Failures are not interpreted as success.
"""
import requests
from eth_utils import keccak
RPC="https://rpc.testnet-chain.genlayer.com"
BUYER="0xf11c3eBa500755F408Eceb16A9c79e724a596e95"
HASH="0x01a2fb2728253002bc3c2668bedb17b56d57b19f68795301c2950d9f51b722ba"
CONSENSUS="0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"
s=requests.Session()
def rpc(m,p):
    try:
        r=s.post(RPC,json={"jsonrpc":"2.0","id":6,"method":m,"params":p},timeout=35)
        if r.status_code != 200:return None, "HTTP_"+str(r.status_code)
        obj=r.json()
        if obj.get("error"):
            e=obj["error"]
            return None,"RPC_"+str(e.get("code")) if isinstance(e,dict) else "RPC_UNKNOWN"
        return obj.get("result"),None
    except (requests.RequestException,ValueError,TypeError) as exc:
        return None,type(exc).__name__

def integer(v):
    try: return int(v,16) if isinstance(v,str) else None
    except ValueError: return None

c,e=rpc("eth_chainId",[])
print("SE7_COMPACT_TX", "CHAIN",c,"ERROR",e,flush=True)
assert c=="0x107d"
for label,method,params in [
    ("BALANCE_WEI","eth_getBalance",[BUYER,"latest"]),
    ("NONCE_LATEST","eth_getTransactionCount",[BUYER,"latest"]),
    ("NONCE_PENDING","eth_getTransactionCount",[BUYER,"pending"]),
    ("BLOCK_HEIGHT","eth_blockNumber",[]),
]:
    val,err=rpc(method,params)
    print("SE7_COMPACT_TX",label,integer(val),"ERROR",err,flush=True)
tx,e=rpc("eth_getTransactionByHash",[HASH])
if not isinstance(tx,dict):
    print("SE7_COMPACT_TX","RAW_TX_NOT_FOUND","ERROR",e,flush=True)
else:
    print("SE7_COMPACT_TX","RAW_TX_FOUND",True,"BLOCK",integer(tx.get("blockNumber")),
         "FROM_MATCH",str(tx.get("from","")).lower()==BUYER.lower(),
         "TO_CONSENSUS",str(tx.get("to","")).lower()==CONSENSUS.lower(),
         "NONCE",integer(tx.get("nonce")),"GAS_LIMIT",integer(tx.get("gas")),
         "VALUE_WEI",integer(tx.get("value")),"CALL_SELECTOR",str(tx.get("input",""))[:10],
         flush=True)
    print("SE7_COMPACT_TX","FEE_CAP",integer(tx.get("maxFeePerGas")),
         "PRIORITY_CAP",integer(tx.get("maxPriorityFeePerGas")),flush=True)
receipt,err=rpc("eth_getTransactionReceipt",[HASH])
if not isinstance(receipt,dict):
    print("SE7_COMPACT_TX","RECEIPT_MISSING","ERROR",err,flush=True)
else:
    logs=receipt.get("logs") or []
    print("SE7_COMPACT_TX","RECEIPT_FOUND",True,
         "STATUS",integer(receipt.get("status")),
         "BLOCK",integer(receipt.get("blockNumber")),
         "GAS_USED",integer(receipt.get("gasUsed")),
         "EFFECTIVE_GAS_PRICE",integer(receipt.get("effectiveGasPrice")),
         "CONTRACT_ADDRESS",receipt.get("contractAddress"),
         "LOG_COUNT",len(logs),flush=True)
    known=[
      "NewTransaction(bytes32,address,address)",
      "CreatedTransaction(bytes32,uint256)",
      "TransactionActivated(bytes32,address)",
      "TransactionAccepted(bytes32)",
      "TransactionFinalized(bytes32)",
      "TransactionUndetermined(bytes32)",
      "TransactionCancelled(bytes32,address)",
      "TransactionLeaderRevealed(bytes32)",
      "TransactionReceiptProposed(bytes32,address[])",
      "TransactionNeedsRecomputation(bytes32[])",
      "TransactionFinalizationFailed(bytes32)",
      "InternalMessageProcessed(bytes32,address,address)",
      "AppealStarted(bytes32,address,uint256,address[])",
      "VoteCommitted(bytes32,address,bool)",
      "VoteRevealed(bytes32,address,uint8,bool,uint8)"
    ]
    sigs={"0x"+keccak(text=k).hex():k.split("(")[0] for k in known}
    for idx,l in enumerate(logs[:20]):
        topic=(l.get("topics") or [""])[0].lower()
        label=sigs.get(topic,"OTHER")
        print("SE7_COMPACT_TX","EVENT",idx,"AT_CONSENSUS",
              str(l.get("address","")).lower()==CONSENSUS.lower(),
              "TYPE",label,"TOPIC0",topic[:66],
              "TOPIC1_TXID",str((l.get("topics") or ["",""])[1])[:66]
                  if len(l.get("topics") or [])>1
                  and str(l.get("address","")).lower()==CONSENSUS.lower()
                  else "NOT_APPLICABLE",
              flush=True)
    if integer(receipt.get("status"))!=1:
        print("SE7_COMPACT_TX","EVM_REVERT_CONFIRMED_DO_NOT_RETRY",flush=True)
    elif not logs:
        print("SE7_COMPACT_TX","EVM_SUCCEEDED_BUT_NO_EVENT_LOGS",flush=True)
    else:
        print("SE7_COMPACT_TX","EVM_SUCCESS_EVENTS_REQUIRE_ABI_DECODE",flush=True)

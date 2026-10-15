"""Read-only scan of Bradbury L2 for a known public test wallet's outbound tx.

Bounded near-tip scan; no account private keys, login, writes or transfers.
"""
import requests,time
ADDRESS="0xFd9D26a2bAf8B26a21DF64D6bEE54ed50823Bc18".lower()
URL="https://rpc.testnet-chain.genlayer.com"
session=requests.Session()
def single(method,params):
    r=session.post(URL,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=20)
    r.raise_for_status()
    j=r.json()
    if "error" in j:raise ValueError(method+" RPC error")
    return j["result"]
def scan():
    chain=int(single("eth_chainId",[]),16)
    assert chain==4221
    latest=int(single("eth_blockNumber",[]),16)
    count=0
    for offset in range(0,1600,50):
        ids=list(range(latest-offset,latest-offset-50,-1))
        req=[{"jsonrpc":"2.0","id":i,"method":"eth_getBlockByNumber",
              "params":[hex(block),True]} for i,block in enumerate(ids)]
        try:
            r=session.post(URL,json=req,timeout=30)
            if r.status_code!=200:
                print("SE7_TXSCAN_BATCH_HTTP",r.status_code,flush=True)
                return
            results=r.json()
            if not isinstance(results,list):
                print("SE7_TXSCAN_BATCH_UNSUPPORTED",flush=True)
                return
        except Exception as err:
            print("SE7_TXSCAN_NETWORK_FAILURE",type(err).__name__,flush=True)
            return
        for res in results:
            block=res.get("result") if isinstance(res,dict) else None
            if not isinstance(block,dict):continue
            count+=1
            for tx in block.get("transactions") or []:
                if not isinstance(tx,dict):continue
                if str(tx.get("from","")).lower()!=ADDRESS:continue
                hash=tx.get("hash")
                val=tx.get("value")
                receipt=single("eth_getTransactionReceipt",[hash]) if hash else None
                print("SE7_WALLET_OUTBOUND_TX",str(hash)[:70],flush=True)
                print("SE7_WALLET_OUTBOUND_BLOCK",block.get("number"),flush=True)
                print("SE7_WALLET_OUTBOUND_VALUE_WEI",int(val,16) if isinstance(val,str) else val,flush=True)
                print("SE7_WALLET_OUTBOUND_STATUS",
                      str(receipt.get("status")) if isinstance(receipt,dict) else "RECEIPT_MISSING",flush=True)
                print("SE7_WALLET_OUTBOUND_RECEIPT_TO_MATCH",
                      bool(isinstance(receipt,dict) and str(receipt.get("to","")).lower()==str(tx.get("to","")).lower()),flush=True)
                print("SE7_WALLET_OUTBOUND_TARGET",str(tx.get("to"))[:60],flush=True)
                print("SE7_WALLET_OUTBOUND_GAS_USED",str(receipt.get("gasUsed")) if isinstance(receipt,dict) else "N/A",flush=True)
                return
        time.sleep(.2)
    print("SE7_TXSCAN_NO_MATCH",count,"blocks scanned",flush=True)
if __name__=="__main__":
    try:scan()
    except Exception as e:print("SE7_TXSCAN_FAILURE_CLASS",type(e).__name__,flush=True)

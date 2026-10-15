"""Read-only Bradbury chain proof for most recent 2-test-GEN phase7 trial."""
import requests
ENDPOINT="https://rpc.testnet-chain.genlayer.com"
WALLET="0x5FF26d32Ae57cdE75C741aC3a7E4cdF352e285B5"
TX="0x9f4309c5fd221007af6d91b6617632d5c7a53f726ac518d16034ed82608931f1"
def rpc(method,params):
    try:
        response=requests.post(ENDPOINT,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=14)
        if response.status_code!=200:return None,"HTTP_"+str(response.status_code)
        j=response.json()
        if "error" in j:return None,"RPC_"+str(j["error"].get("code","?"))
        return j.get("result"),None
    except (requests.RequestException,TypeError,ValueError) as exc:
        return None,type(exc).__name__
chain,e=rpc("eth_chainId",[])
print("SE7_TRIAL3","CHAIN",chain,"ERROR",e,flush=True)
if chain!="0x107d":raise SystemExit(2)
for label,method,params in [
 ("BALANCE_WEI","eth_getBalance",[WALLET,"latest"]),
 ("LATEST_NONCE","eth_getTransactionCount",[WALLET,"latest"]),
 ("PENDING_NONCE","eth_getTransactionCount",[WALLET,"pending"]),
 ("TX_RECEIPT","eth_getTransactionReceipt",[TX]),
]:
    val,err=rpc(method,params)
    if label=="TX_RECEIPT" and isinstance(val,dict):
        val={"status":val.get("status"),"blockNumber":val.get("blockNumber"),"gasUsed":val.get("gasUsed")}
    elif isinstance(val,str) and val.startswith("0x"):
        val=str(int(val,16))
    print("SE7_TRIAL3",label,val,"ERROR",err,flush=True)

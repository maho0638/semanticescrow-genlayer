"""Public Bradbury read-only diagnostics for the 5 test-GEN wallet after deploy exception.
Never uses any private keys, signs any transaction or changes chain state.
"""
import requests
R="https://rpc.testnet-chain.genlayer.com"
WALLET="0x84D37542B362F96282b19D479cF9b06E15ff62eA"
SELLER_TX="0x77c2f76798c8bf52b4d741352c6d67d2ccde03b43af7bb7aa7db7ae5eaffc860"
def q(m,p):
    try:
        r=requests.post(R,json={"jsonrpc":"2.0","id":1,"method":m,"params":p},timeout=18)
        if r.status_code!=200:return None, "HTTP_"+str(r.status_code)
        d=r.json()
        if "error" in d:return None,"RPC_"+str(d["error"].get("code","?"))
        return d.get("result"),None
    except (requests.RequestException,ValueError,TypeError) as ex:
        return None,type(ex).__name__
chain,err=q("eth_chainId",[])
print("SE7_DEPLOY_POSTMORTEM_CHAIN",chain,"ERROR",err,flush=True)
if chain!="0x107d":raise SystemExit(2)
for label,method,params in [
    ("WALLET_BALANCE_WEI","eth_getBalance",[WALLET,"latest"]),
    ("WALLET_LATEST_NONCE","eth_getTransactionCount",[WALLET,"latest"]),
    ("WALLET_PENDING_NONCE","eth_getTransactionCount",[WALLET,"pending"]),
    ("BLOCK_NUMBER","eth_blockNumber",[]),
]:
    v,err=q(method,params)
    if isinstance(v,str):
        try:v=str(int(v,16))
        except ValueError:v="NON_HEX"
    print("SE7_DEPLOY_POSTMORTEM",label,v,"ERROR",err,flush=True)
r,err=q("eth_getTransactionReceipt",[SELLER_TX])
if isinstance(r,dict):
    print("SE7_DEPLOY_POSTMORTEM_SELLER_FUND_STATUS",r.get("status"),
          "BLOCK",r.get("blockNumber"),"TO",r.get("to"),
          "GAS_USED",r.get("gasUsed"),flush=True)
else:print("SE7_DEPLOY_POSTMORTEM_SELLER_RECEIPT_UNAVAILABLE",err,flush=True)

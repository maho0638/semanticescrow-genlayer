"""Phase7 post-failure public-chain evidence; never reads private keys.

Address was displayed in a screenshot. This is an unspent-value and
outgoing-nonce inventory, not proof of EVM/Ghost contract completion.
"""
import requests
RPCS=[
 ("chain","https://rpc.testnet-chain.genlayer.com"),
 ("genlayer_studio","https://studio.genlayer.com/api"),
]
ADDRESS="0xFd9D26a2bAf8B26a21DF64D6bEE54ed50823Bc18"
def query(url,method,params):
    try:
        r=requests.post(url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=15)
        if r.status_code!=200:return None,"HTTP_"+str(r.status_code)
        data=r.json()
        if data.get("error"):return None,"JSONRPC_ERROR_"+str(data["error"].get("code","?"))
        return data.get("result"),None
    except (requests.RequestException,ValueError,TypeError) as e:
        return None,type(e).__name__
for network,url in RPCS:
    chain,error=query(url,"eth_chainId",[])
    print("SE7_EVIDENCE",network,"CHAIN",chain,"ERROR",error,flush=True)
    if network!="chain" or chain!="0x107d":
        continue
    for name,method,params in [
        ("balance_wei","eth_getBalance",[ADDRESS,"latest"]),
        ("nonce_latest","eth_getTransactionCount",[ADDRESS,"latest"]),
        ("nonce_pending","eth_getTransactionCount",[ADDRESS,"pending"]),
        ("code","eth_getCode",[ADDRESS,"latest"]),
        ("latest_block","eth_blockNumber",[]),
    ]:
        value,err=query(url,method,params)
        if value is not None and name in ("balance_wei","nonce_latest","nonce_pending","latest_block"):
            try: value=str(int(value,16))
            except (ValueError,TypeError):value="INVALID_VALUE"
        if value is not None and name=="code":
            value="EMPTY" if value in ("0x","0x0") else "NOT_EMPTY"
        print("SE7_EVIDENCE",network,name,value,"ERROR",err,flush=True)

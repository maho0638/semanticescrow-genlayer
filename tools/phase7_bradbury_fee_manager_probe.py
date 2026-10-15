"""Read-only Bradbury FeeManager view probe against official L2 RPC.

No wallet, keys, value, transactions, contract writes, or SDK mutations.
Uses the exact address and getter names from pinned GenLayer v0.19 RC.
"""
import requests
from eth_utils import keccak

URL="https://rpc.testnet-chain.genlayer.com"
FEE_MANAGER="0xF205868bf5db79d2162843742D18D0900A9E462a"
METHODS=["GENPerTimeUnit()","storageUnitPrice()","quoteGasPrice()","messageFeeParamsBudgetFloor()"]
SESSION=requests.Session()

def rpc(method,params):
    try:
        r=SESSION.post(URL,json={"jsonrpc":"2.0","id":3,"method":method,"params":params},timeout=15)
        if r.status_code!=200:return None,"HTTP_"+str(r.status_code)
        j=r.json()
        if "error" in j:
            e=j["error"] if isinstance(j["error"],dict) else {}
            return None,"RPC_"+str(e.get("code","unknown"))
        return j.get("result"),None
    except (requests.RequestException,TypeError,ValueError) as exc:
        return None,type(exc).__name__

chain,err=rpc("eth_chainId",[])
print("FEE_PROBE_CHAIN",chain,"ERROR",err,flush=True)
assert chain=="0x107d", "Wrong chain"
code,err=rpc("eth_getCode",[FEE_MANAGER,"latest"])
print("FEE_PROBE_FEE_MANAGER_CODE",
      "EXISTS" if isinstance(code,str) and code not in ("0x","0x0") else "MISSING_OR_UNREADABLE",
      "CODE_BYTES",(len(code)-2)//2 if isinstance(code,str) else None,"ERROR",err,flush=True)
price,err=rpc("eth_gasPrice",[])
print("FEE_PROBE_ETH_GAS_PRICE","PRESENT" if price is not None else "MISSING","ERROR",err,flush=True)
for name in METHODS:
    selector="0x"+keccak(text=name)[:4].hex()
    result,error=rpc("eth_call",[{"to":FEE_MANAGER,"data":selector},"latest"])
    if isinstance(result,str) and len(result)>2:
        try:
            numeric=int(result,16)
            outcome="ZERO" if numeric==0 else "NONZERO"
        except ValueError:
            outcome="NON_HEX"
    elif result in ("0x","0x0"):
        outcome="EMPTY_RESULT"
    else:
        outcome="NO_RESULT"
    print("FEE_PROBE_GETTER",name,"SELECTOR",selector,
          "OUTCOME",outcome,"RETURN_LENGTH",len(result) if isinstance(result,str) else None,
          "ERROR",error,flush=True)

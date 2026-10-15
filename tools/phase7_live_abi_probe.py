"""Read-only onchain Bradbury proxy, fee manager and consensus ABI probe.

Does not sign or submit transactions or reveal keys. It is a protocol-version
probe; presence of method selectors is not proof of semantic compatibility.
"""
import requests
from eth_utils import keccak
RPC="https://rpc.testnet-chain.genlayer.com"
FEE="0xF205868bf5db79d2162843742D18D0900A9E462a"
CONS="0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"
EIP1967_IMPL="0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
SIGNATURES=[
 "GENPerTimeUnit()",
 "storageUnitPrice()",
 "quoteGasPrice()",
 "messageFeeParamsBudgetFloor()",
 "getValidatorsPerRound(uint256)",
 "calculateRoundFees(bytes32,(uint256,uint256,uint256,uint256,uint256,uint256,uint256[]),uint256,uint256)",
 "calculateRoundFees((uint256,uint256,uint256,uint256,uint256,uint256,uint256[]),uint256,uint256)",
 "addTransaction(address,address,uint256,uint256,bytes)",
 "addTransaction(address,address,uint256,uint256,bytes,uint256)",
 "legacy-sdk-selector-diagnostic",
 "getCurrentFeePolicy()",
]
session=requests.Session()
def rpc(method,params):
    reply=session.post(RPC,json={"jsonrpc":"2.0","id":7,"method":method,"params":params},timeout=20)
    if reply.status_code!=200:return None,"HTTP_"+str(reply.status_code)
    out=reply.json()
    if "error" in out:
        error=out.get("error",{})
        return None,"RPC_"+str(error.get("code","?"))
    return out.get("result"),None
def selector(signature):
    return "0x"+keccak(text=signature)[:4].hex()
def addr_from_storage(raw):
    try:
        if not isinstance(raw,str) or len(raw)!=66: return None
        val=int(raw,16)
        if val==0: return None
        return "0x"+format(val & ((1<<160)-1),"040x")
    except Exception:return None
assert rpc("eth_chainId",[])[0]=="0x107d"
for label,addr in [("FEE",FEE),("CONS",CONS)]:
    code,error=rpc("eth_getCode",[addr,"latest"])
    slot,e2=rpc("eth_getStorageAt",[addr,EIP1967_IMPL,"latest"])
    impl=addr_from_storage(slot)
    print("SE7_ABI",label,"RPC_ERRORS",error,e2,
          "PROXY_BYTES",(len(code)-2)//2 if isinstance(code,str) else "N/A",
          "IMPL",impl or "NONE",flush=True)
    objcode=code
    if impl:
        objcode,e3=rpc("eth_getCode",[impl,"latest"])
        print("SE7_ABI",label,"IMPL_CODE_BYTES",
              (len(objcode)-2)//2 if isinstance(objcode,str) else "N/A",
              "ERROR",e3,flush=True)
    found={}
    if isinstance(objcode,str):
        hexcode=objcode.lower()[2:]
        for sig in SIGNATURES:
            sel= "0x35a251fb" if sig=="legacy-sdk-selector-diagnostic" else selector(sig)
            found[sig]=sel[2:] in hexcode
    for sig,hit in found.items():
        print("SE7_ABI",label,"SIGNATURE",sig,"SELECTOR",sel,
              "IN_BYTECODE",hit,flush=True)
if True:
    sig="getValidatorsPerRound(uint256)"
    calldata=selector(sig)+format(0,"064x")
    val,err=rpc("eth_call",[{"to":FEE,"data":calldata},"latest"])
    try:
        value=int(val,16) if isinstance(val,str) else None
    except ValueError:value=None
    print("SE7_ABI","FEE","LEGACY_GET_VALIDATORS_ROUND0",value,"ERROR",err,flush=True)

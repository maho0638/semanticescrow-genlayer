"""Read-only reproduction of SemanticEscrow Bradbury EVM deployment gas estimation.

All requests are eth_* reads against official public GenLayer Chain RPC.
No private keys, signing, faucet, storage of secrets, or eth_sendRawTransaction.
The 'from' is a PUBLIC address observed in the user's prior test logs.
"""
import hashlib
import json
from pathlib import Path
import requests
from eth_account import Account
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.contracts.utils import make_calldata_object
from genlayer_py.transactions.fees import normalize_transaction_fees
from tools.phase7_legacy_compat import _install_legacy_consensus_abi, CONSENSUS_PROXY, CONSENSUS_IMPLEMENTATION, FEE_PROXY, FEE_IMPLEMENTATION, EIP1967_IMPL

URL = "https://rpc.testnet-chain.genlayer.com"
FROM = "0x84D37542B362F96282b19D479cF9b06E15ff62eA"
SOURCE_HASH = "4fae50929d9e98e1d166661acaac120d5153e5dd8ca1b203a444475330223b66"

def rpc(method,params):
    r=requests.post(URL,json={"jsonrpc":"2.0","id":3,"method":method,"params":params},timeout=40)
    if r.status_code != 200:
        return None,{"code":"HTTP_"+str(r.status_code)}
    try: obj=r.json()
    except ValueError: return None,{"code":"NON_JSON"}
    return obj.get("result"),obj.get("error")

def verify_onchain():
    chain,err=rpc("eth_chainId",[])
    if err or chain!="0x107d":raise RuntimeError("chain check failed")
    for proxy,expected,selector in [
       (CONSENSUS_PROXY,CONSENSUS_IMPLEMENTATION,"e71d5196"),
       (FEE_PROXY,FEE_IMPLEMENTATION,"4fe8920e"),
    ]:
       storage,err=rpc("eth_getStorageAt",[proxy,EIP1967_IMPL,"latest"])
       if err or "0x"+format(int(storage,16)&((1<<160)-1),"040x")!=expected.lower():
           raise RuntimeError("implementation changed")
       code,err=rpc("eth_getCode",[expected,"latest"])
       if err or not isinstance(code,str) or selector not in code.lower():
           raise RuntimeError("bytecode selector changed")
    print("SE7_DEPLOY_DRY_CHAIN_AND_ABI_VERIFIED",flush=True)

def main():
    verify_onchain()
    source=Path("contracts/semantic_escrow.py").read_text(encoding="utf-8")
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_HASH:
        raise RuntimeError("contract bytes changed")
    account=Account.create() # never used as signer; unused random address never printed
    client=GenLayerClient(testnet_bradbury,account)
    _install_legacy_consensus_abi(client.chain.consensus_main_contract)
    data=serialize([source,calldata.encode(make_calldata_object(method=None,args=None,kwargs=None)),False])
    payload=_encode_add_transaction_data(
        client, type("PublicAddress",(),{"address":FROM})(),
        "0x0000000000000000000000000000000000000000", 3, data,
        transaction_fees=normalize_transaction_fees(),
    )
    if not payload.startswith("0xe71d5196"):raise RuntimeError("wrong selector")
    print("SE7_DEPLOY_DRY_PAYLOAD_SELECTOR",payload[:10],"PAYLOAD_BYTES",(len(payload)-2)//2,flush=True)
    latest,err=rpc("eth_getBlockByNumber",["latest",False])
    if err or not isinstance(latest,dict):raise RuntimeError("latest block unreadable")
    base=int(latest.get("baseFeePerGas") or "0x0",16)
    priority=2_000_000_000
    nonce,err=rpc("eth_getTransactionCount",[FROM,"latest"])
    if err:raise RuntimeError("nonce unavailable")
    tx={
      "from":FROM, "to":CONSENSUS_PROXY, "data":payload,
      "chainId":"0x107d", "value":"0x0",
      "nonce":nonce,
      "maxFeePerGas":hex(base+priority),
      "maxPriorityFeePerGas":hex(priority),
    }
    estimate,error=rpc("eth_estimateGas",[tx])
    print("SE7_DRY_GAS_ESTIMATE_WEI",estimate if error is None else "FAILED",flush=True)
    if estimate is not None:
        gas_limit=int(estimate,16)
        blockgas=int(latest.get("gasLimit","0x0"),16)
        print("SE7_DRY_BLOCK_GAS_LIMIT",blockgas,"ESTIMATED_GAS",gas_limit,
              "MAX_TX_FEE_WEI",gas_limit*(base+priority),flush=True)
    for method in ("eth_estimateGas","eth_call"):
        args=[tx] if method=="eth_estimateGas" else [
            {**tx,"gas":hex(min(int(estimate,16)+3000000,int(latest.get("gasLimit","0x0"),16)))
             } if estimate is not None else tx, "latest"]
        out,error=rpc(method,args)
        if error:
            ec=error.get("code") if isinstance(error,dict) else "UNKNOWN"
            msg=str(error.get("message","")) if isinstance(error,dict) else ""
            # Truncate PUBLIC revert diagnostics; never print raw tx payload.
            msg="".join(c if 32<=ord(c)<127 else " " for c in msg)[:220]
            ed=error.get("data") if isinstance(error,dict) else None
            if isinstance(ed,str) and ed.startswith("0x"):selector=ed[:10]
            elif isinstance(ed,dict):selector="STRUCTURED_ERROR"
            else:selector="NO_DATA"
            print("SE7_DEPLOY_DRY",method,"FAIL","RPC_CODE",ec,
                  "REVERT_SELECTOR",selector,"PUBLIC_MESSAGE",msg,flush=True)
        else:
            desc=("0x"+out[:8] if method=="eth_call" and isinstance(out,str) else out)
            print("SE7_DEPLOY_DRY",method,"OK","VALUE",str(desc)[:90],flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:print("SE7_DEPLOY_DRY_PROBE_FAILED_CLASS",type(e).__name__,flush=True)

"""Read-only Bradbury GenLayer consensus lifecycle for a confirmed EVM deployment.

Uses public GenLayer transaction ID extracted from the EVM NewTransaction event.
No private keys; no RPC writes; no token spending or wallet permissions.
"""
import copy
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient

RPC="https://rpc.testnet-chain.genlayer.com"
TX_ID="0x0c91636fc0354024f6e26c88d81c23c47c3e547022dada171a698c2e7cc065ca"
config=copy.deepcopy(testnet_bradbury)
config.rpc_urls["default"]["http"]=[RPC]
client=GenLayerClient(config,None)
print("SE7_GENLAYER","CHAIN",config.id,"CONSENSUS_DATA",config.consensus_data_contract["address"],flush=True)

# ABI-independent eth_call probes isolate getter reverts from Python decoding.
import requests
from web3 import Web3
import time
session=requests.Session()
data_addr=config.consensus_data_contract["address"]
current_ts=int(time.time())
def raw_rpc(method,params):
    try:
        res=session.post(RPC,json={"jsonrpc":"2.0","id":37,
                          "method":method,"params":params},timeout=25)
        if res.status_code!=200:return None,"HTTP_"+str(res.status_code)
        body=res.json()
        if "error" in body:
            err=body["error"]
            return None,"RPC_"+str(err.get("code","?"))
        return body.get("result"),None
    except (requests.RequestException,ValueError,TypeError) as ex:
        return None,type(ex).__name__

chain,err=raw_rpc("eth_chainId",[])
assert chain=="0x107d", "wrong chain"
block,e=raw_rpc("eth_getBlockByNumber",["latest",False])
ts_block=int(block["timestamp"],16) if isinstance(block,dict) else current_ts
for label,signature,argument_hex in [
    ("STATUS_CURRENT","getTransactionStatus(bytes32,uint256)",TX_ID[2:]+format(current_ts,"064x")),
    ("STATUS_BLOCK","getTransactionStatus(bytes32,uint256)",TX_ID[2:]+format(ts_block,"064x")),
    ("STATUS_ZERO","getTransactionStatus(bytes32,uint256)",TX_ID[2:]+format(0,"064x")),
    ("GET_DATA_CURRENT","getTransactionData(bytes32,uint256)",TX_ID[2:]+format(current_ts,"064x")),
    ("GET_DATA_ZERO","getTransactionData(bytes32,uint256)",TX_ID[2:]+format(0,"064x")),
    ("GET_ALL_DATA","getTransactionAllData(bytes32)",TX_ID[2:]),
    ("GET_VALIDATORS_LAST","getValidatorsForLastRound(bytes32)",TX_ID[2:]),
    ("CAN_FINALIZE","canFinalize(bytes32,uint256)",TX_ID[2:]+format(current_ts,"064x")),
]:
    selector=Web3.keccak(text=signature)[:4].hex()
    call={"to":data_addr,"data":"0x"+selector+argument_hex,"gas":hex(10_000_000)}
    output,error=raw_rpc("eth_call",[call,"latest"])
    size=(len(output)-2)//2 if isinstance(output,str) and output.startswith("0x") else 0
    u8=(int(output,16) if isinstance(output,str) and size==32 else None)
    print("SE7_GENLAYER","DIRECT",label,"ERROR",error,"RETURN_BYTES",size,
          "WORD",u8 if label.startswith("STATUS_") else "HIDDEN",flush=True)
    if label in ("STATUS_CURRENT","GET_DATA_CURRENT","GET_ALL_DATA"):
        # SDK's web3 contract call omits explicit gas; compare to the above
        # identical call that intentionally sets a 10M eth_call gas budget.
        output_default, error_default = raw_rpc("eth_call",[
            {"to":data_addr,"data":"0x"+selector+argument_hex}, "latest"])
        print("SE7_GENLAYER","DEFAULT_GAS",label,
              "ERROR",error_default,"RETURN_BYTES",
              (len(output_default)-2)//2 if isinstance(output_default,str)
                   and output_default.startswith("0x") else 0,flush=True)

# Instrument only read-only chain queries. Never send signed transactions.
# Read-only compatibility path for the still-deployed Bradbury ConsensusData
# v0.6, which the v0.19rc2 SDK's Train lookup currently fails to query.
from genlayer_py.consensus.abi import CONSENSUS_DATA_ABI_V06
try:
    storage=client.w3.eth.contract(address=data_addr,abi=CONSENSUS_DATA_ABI_V06)
    raw=storage.functions.getTransactionData(TX_ID,current_ts).call()
    all_data=storage.functions.getTransactionAllData(TX_ID).call()
    can=storage.functions.canFinalize(TX_ID,current_ts).call()
    print("SE7_GENLAYER","LEGACY_READ_OK",True,
          "DATA_FIELDS",len(raw),"ALL_DATA_FIELDS",len(all_data),
          "RECIPIENT",str(raw[2]) if len(raw)>2 else "N/A",
          "CONSENSUS_STATUS",raw[18] if len(raw)>18 else "N/A",
          "RESULT",raw[8] if len(raw)>8 else "N/A",
          "EXECUTION_RESULT",all_data[0][1] if isinstance(all_data[0],(list,tuple)) else "N/A",
          "CAN_FINALIZE",str(can)[:200],flush=True)
    if len(raw)>2 and isinstance(raw[2],str):
        ghost_code=client.w3.eth.get_code(raw[2])
        print("SE7_GENLAYER","GHOST_CODE_BYTES",len(ghost_code),flush=True)
except Exception as exc:
    print("SE7_GENLAYER","LEGACY_READ_FAILED_CLASS",type(exc).__name__,flush=True)

original_request = client.provider.make_request
def observe(method, params):
    if method == "eth_call" and isinstance(params,(list,tuple)) and params:
        tx=params[0] if isinstance(params[0],dict) else {}
        data=str(tx.get("data") or tx.get("input") or "")
        print("SE7_GENLAYER","SDK_CALL_BEGIN",
              "TO",str(tx.get("to",""))[:50],
              "SELECTOR",data[:10],
              "GAS",str(tx.get("gas","DEFAULT"))[:25],flush=True)
    try:
        response=original_request(method,params)
    except Exception as exc:
        print("SE7_GENLAYER","SDK_CALL_FAILURE",
              "METHOD",str(method),"CLASS",type(exc).__name__,
              "TO",str(params[0].get("to",""))[:50]
                if method=="eth_call" and isinstance(params,(list,tuple))
                    and params and isinstance(params[0],dict) else "N/A",
              "SELECTOR",str(params[0].get("data",""))[:10]
                if method=="eth_call" and isinstance(params,(list,tuple))
                    and params and isinstance(params[0],dict) else "N/A",
              flush=True)
        raise
    return response
client.provider.make_request=observe
try:
    obj=client.get_transaction(TX_ID)
    if not isinstance(obj,dict):
        print("SE7_GENLAYER","RESPONSE_TYPE",type(obj).__name__,flush=True)
    else:
        safe_keys=sorted(str(k) for k in obj.keys())
        print("SE7_GENLAYER","READ_OK",True,"FIELDS",",".join(safe_keys)[:700],flush=True)
        for name in ("status","status_name","tx_execution_result","tx_execution_result_name",
                     "contract_address","to","recipient","from","sender","tx_id",
                     "transaction_hash","leader_id","read_state_block_range"):
            value=obj.get(name)
            if isinstance(value,(int,str,bool)) or value is None:
                print("SE7_GENLAYER",name.upper(),str(value)[:200],flush=True)
            elif isinstance(value,dict) and name=="read_state_block_range":
                print("SE7_GENLAYER",name.upper(),"KEYS",",".join(sorted(map(str,value.keys()))),flush=True)
        triggered=obj.get("triggered_transactions")
        print("SE7_GENLAYER","TRIGGERED_TX_COUNT",len(triggered) if isinstance(triggered,list) else "UNKNOWN",flush=True)
except Exception as exc:
    import re, traceback
    print("SE7_GENLAYER","READ_FAILED_CLASS",type(exc).__name__,flush=True)
    # This diagnostic has NO wallet and ONLY public read-only RPC calls.
    # Avoid echoing arbitrary RPC payloads or 64-hexbyte fields anyway.
    msg=re.sub(r"0x[0-9a-fA-F]{32,}","0x[public_hex]",str(exc))
    safe="".join(c if 32<=ord(c)<127 else " " for c in msg)
    print("SE7_GENLAYER","PUBLIC_ERROR_SUMMARY",safe[:450],flush=True)
    frames=traceback.extract_tb(exc.__traceback__)
    print("SE7_GENLAYER","FRAME_COUNT",len(frames),flush=True)
    for tb in frames[:14]+frames[-3:]:
        print("SE7_GENLAYER","ERROR_FRAME",tb.filename.rsplit("/",1)[-1].rsplit("\\",1)[-1],
              tb.name,tb.lineno,flush=True)
    caused=exc.__cause__
    if caused is not None:
        print("SE7_GENLAYER","READ_CAUSE_CLASS",type(caused).__name__,flush=True)
        caused_msg=re.sub(r"0x[0-9a-fA-F]{32,}","0x[public_hex]",str(caused))
        print("SE7_GENLAYER","CAUSE_SUMMARY",
              "".join(c if 32<=ord(c)<127 else " " for c in caused_msg)[:300],flush=True)

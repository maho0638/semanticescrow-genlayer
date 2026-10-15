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
    for tb in traceback.extract_tb(exc.__traceback__)[-8:]:
        print("SE7_GENLAYER","ERROR_FRAME",tb.filename.rsplit("/",1)[-1].rsplit("\\",1)[-1],
              tb.name,tb.lineno,flush=True)
    caused=exc.__cause__
    if caused is not None:
        print("SE7_GENLAYER","READ_CAUSE_CLASS",type(caused).__name__,flush=True)
        caused_msg=re.sub(r"0x[0-9a-fA-F]{32,}","0x[public_hex]",str(caused))
        print("SE7_GENLAYER","CAUSE_SUMMARY",
              "".join(c if 32<=ord(c)<127 else " " for c in caused_msg)[:300],flush=True)

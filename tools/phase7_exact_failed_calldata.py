"""Inspect the EXACT failed GenLayer v0.6 tx calldata, read-only EVM RPC.

Parses the same runtime binary calldata protocol with strict bounds.
Prints only known expected values/booleans and anonymized digest.
No private keys, new wallets, network writes or GEN transfers.
"""
import json,hashlib,datetime
import requests
from eth_abi import decode
from eth_utils import keccak
from eth_utils.abi import collapse_if_tuple
from pathlib import Path

TX="0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06"
BUYER="0xa9afeBFEc83cEddcAE9b61a3A22971BF5e426e0C"
GHOST="0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a"
CONSENSUS_DATA="0x85D7bf947A512Fc640C75327A780c90847267697"
RPC="https://rpc.testnet-chain.genlayer.com"
ABI=json.loads(Path(__file__).with_name("phase7_legacy_consensus_data_abi.json").read_text())
def rpc(m,p):
    r=requests.post(RPC,json={"jsonrpc":"2.0","id":1,"method":m,"params":p},timeout=30)
    r.raise_for_status()
    o=r.json()
    if "error" in o:raise ValueError("RPC failed code "+str(o["error"].get("code")))
    return o.get("result")
def cd_decode(raw):
    pos=0
    def read(n):
        nonlocal pos
        if n<0 or pos+n>len(raw):raise ValueError("calldata truncated")
        b=raw[pos:pos+n];pos+=n;return b
    def var():
        v=0;s=0
        while 1:
            t=read(1)[0];v|=(t&127)<<s;s+=7
            if s>300:raise ValueError("oversize LEB128")
            if not t&128:return v
    def item(level=0):
        if level>10:raise ValueError("deep calldata")
        code=var();typ=code&7;cnt=code>>3
        if typ==0:
            if code==0:return None
            if code==8:return False
            if code==16:return True
            if code==24:return "0x"+read(20).hex()
            raise ValueError("invalid special")
        if typ==1:return cnt
        if typ==2:return -cnt-1
        if typ==3:return read(cnt)
        if typ==4:return read(cnt).decode("utf8")
        if typ==5:return [item(level+1) for _ in range(cnt)]
        if typ==6:
            d={};prev=""
            for i in range(cnt):
                key=read(var()).decode("utf8")
                if key<=prev or key in d:raise ValueError("unordered keys")
                prev=key;d[key]=item(level+1)
            return d
        raise ValueError("unknown calldata tag")
    result=item()
    if pos!=len(raw):raise ValueError("trailing bytes")
    return result

def main():
    data="0x"+keccak(text="getTransactionAllData(bytes32)")[:4].hex()+TX[2:]
    res=rpc("eth_call",[{"to":CONSENSUS_DATA,"data":data},"latest"])
    abi=next(item for item in ABI if item["name"]=="getTransactionAllData")["outputs"]
    all_data=decode([collapse_if_tuple(x) for x in abi],bytes.fromhex(res[2:]))[0]
    calldata=all_data[16]
    print("SE7_EXACT_CALLDATA_BYTES",len(calldata),"SHA256",hashlib.sha256(calldata).hexdigest(),flush=True)
    print("SE7_EXACT_CALLDATA_PREFIX",calldata[:12].hex(),flush=True)
    # Bradbury v0.6 consensus wraps GenVM calldata bytes in RLP:
    # f9 01 28 (RLP list of 296 bytes) + b9 01 24 (292-byte string)
    # + 292 GenVM calldata bytes + empty second list element.
    # Require exact length to avoid silently interpreting arbitrary offsets.
    from rlp import decode as rlp_decode
    envelope=rlp_decode(calldata)
    if not isinstance(envelope,list) or len(envelope)!=2:
        raise ValueError("unexpected legacy calldata RLP layout")
    inner=envelope[0]
    print("SE7_EXACT_RLP_INNER_BYTES",len(inner),"SECOND_ELEMENT_BYTES",len(envelope[1]),flush=True)
    obj=cd_decode(inner)
    print("SE7_EXACT_CALLDATA_DECODE_OFFSET","RLP_INNER",flush=True)
    print("SE7_EXACT_CALLDATA_TYPE",type(obj).__name__,flush=True)
    if isinstance(obj,dict):
        print("SE7_EXACT_CALLDATA_FIELDS",sorted(obj),flush=True)
        print("SE7_EXACT_CALLDATA_METHOD",obj.get("method"),flush=True)
        args=obj.get("args")
        if isinstance(args,list):
            print("SE7_EXACT_CALLDATA_ARG_COUNT",len(args),flush=True)
            if len(args)==3:
                print("SE7_EXACT_SELLER_TYPE",type(args[0]).__name__,flush=True)
                print("SE7_EXACT_SELLER_ADDRESS",args[0],flush=True)
                try:
                    milestones=json.loads(args[1])
                    print("SE7_EXACT_MILESTONES_COUNT",len(milestones),flush=True)
                    if isinstance(milestones,list) and len(milestones)==1:
                        milestone=milestones[0]
                        print("SE7_EXACT_MILESTONE_FIELDS",sorted(milestone),flush=True)
                        print("SE7_EXACT_MILESTONE_AMOUNT",milestone.get("amount_wei"),flush=True)
                        due=milestone.get("delivery_due_at")
                        created=int(all_data[11]) if isinstance(all_data[11],int) else -1
                        print("SE7_EXACT_DUE_TIMESTAMP",due,flush=True)
                        print("SE7_EXACT_EPOCH",created,flush=True)
                        print("SE7_EXACT_CRITERIA_KEYS",sorted(milestone.get("criteria_items",[{}])[0]),flush=True)
                except Exception as exc:
                    print("SE7_EXACT_MILESTONE_DECODE_FAILURE",type(exc).__name__,flush=True)
                print("SE7_EXACT_NONCE",args[2],flush=True)
    print("SE7_EXACT_CHAIN_VALUE",int(all_data[20]),flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())

"""Public, read-only Bradbury postmortem for the 2026-10-16 signed test.

No wallet keys, no transactions, no retries, no token transfers. A successful
EVM receipt must never be confused with successful GenVM execution.
"""
import json
import time
from pathlib import Path

import requests
from web3 import Web3
from eth_utils import keccak

EVM_TX="0x2bddc2919cde1aee0cc751e3735daa7e0ecc9fbcbab91b2bc28dd6d698455bf8"
BUYER="0x1B982344f53257768E971DBb152907cBa33D632C"
CHAIN=4221
CONSENSUS="0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"
DATA="0x85D7bf947A512Fc640C75327A780c90847267697"
RPC="https://rpc.testnet-chain.genlayer.com"
ABI=json.loads(Path(__file__).with_name("phase7_legacy_consensus_data_abi.json").read_text(encoding="utf-8"))
session=requests.Session()

def rpc(method, params):
    try:
        response=session.post(RPC,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=25)
        if response.status_code!=200:
            print("SE7_POSTMORTEM",method,"HTTP",response.status_code,flush=True)
            return None
        obj=response.json()
        if obj.get("error"):
            print("SE7_POSTMORTEM",method,"RPC_ERROR_CODE",obj["error"].get("code"),flush=True)
            return None
        return obj.get("result")
    except (requests.RequestException,ValueError,TypeError) as exc:
        print("SE7_POSTMORTEM",method,"ERROR_CLASS",type(exc).__name__,flush=True)
        return None

def n(value):
    if isinstance(value,str) and value.startswith("0x"):
        try:return int(value,16)
        except ValueError:return None
    return None

def call(selector,encoded):
    result=rpc("eth_call",[{"to":DATA,"data":selector+encoded,"gas":hex(10000000)},"latest"])
    if not isinstance(result,str):return None
    return bytes.fromhex(result[2:])

def check(candidate):
    if not isinstance(candidate,str) or len(candidate)!=66:return
    try:blob=Web3.to_bytes(hexstr=candidate)
    except (ValueError,TypeError):return
    print("SE7_POSTMORTEM","CANDIDATE_ID",candidate,flush=True)
    t=int(time.time())
    payload=blob.hex()+format(t,"064x")
    s1="0x"+keccak(text="getTransactionData(bytes32,uint256)")[:4].hex()
    s2="0x"+keccak(text="getTransactionAllData(bytes32)")[:4].hex()
    raw=call(s1,payload)
    all_data=call(s2,blob.hex())
    print("SE7_POSTMORTEM","GET_DATA_BYTES",len(raw) if raw is not None else "RPC_FAIL",
          "GET_ALL_BYTES",len(all_data) if all_data is not None else "RPC_FAIL",flush=True)
    if raw is None or all_data is None:return
    try:
        contract=Web3().eth.contract(address=Web3.to_checksum_address(DATA),abi=ABI)
        d=contract.decode_function_input(s1+payload)[0]
        # Decode with exact old ABI; immutable public protocol state only.
        from eth_abi import decode
        abi_d=next(x for x in ABI if x["name"]=="getTransactionData")["outputs"]
        abi_a=next(x for x in ABI if x["name"]=="getTransactionAllData")["outputs"]
        from eth_utils.abi import collapse_if_tuple
        types_d=[collapse_if_tuple(x) for x in abi_d]
        types_a=[collapse_if_tuple(x) for x in abi_a]
        dec_d=decode(types_d,raw)[0]
        dec_a=decode(types_a,all_data)[0]
        print("SE7_POSTMORTEM","LEGACY_SHAPES",len(dec_d),len(dec_a),
              "STATUS",int(dec_d[17]),"ALL_STATUS",int(dec_a[3]),
              "GENVM_EXECUTION",int(dec_a[1]),flush=True)
        print("SE7_POSTMORTEM","ID_MATCH_DATA",bytes(dec_d[18])==blob,
              "ID_MATCH_ALL",bytes(dec_a[12])==blob,
              "GHOST",dec_d[2],flush=True)
        try:
            from phase7_legacy_receipts import decode_bradbury_transaction
            res=decode_bradbury_transaction(candidate,dec_d,dec_a)
            print("SE7_POSTMORTEM","CURRENT_READER_DECODE_OK",True,
                  "STATUS",res["status_name"],
                  "EXECUTION",res["tx_execution_result_name"],flush=True)
        except Exception as ex:
            print("SE7_POSTMORTEM","CURRENT_READER_ERROR_CLASS",type(ex).__name__,
                  "REASON",str(ex)[:125],flush=True)
    except Exception as ex:
        print("SE7_POSTMORTEM","ABI_DECODE_ERROR_CLASS",type(ex).__name__,flush=True)

def run():
    chain=rpc("eth_chainId",[])
    print("SE7_POSTMORTEM","CHAIN_ID",n(chain),flush=True)
    if n(chain)!=CHAIN:return 2
    for label,method,params in (
        ("BALANCE","eth_getBalance",[BUYER,"latest"]),
        ("NONCE","eth_getTransactionCount",[BUYER,"latest"]),
    ):
        print("SE7_POSTMORTEM",label,n(rpc(method,params)),flush=True)
    tx=rpc("eth_getTransactionByHash",[EVM_TX])
    if isinstance(tx,dict):
        print("SE7_POSTMORTEM","EVM_TX_INCLUDED_BLOCK",n(tx.get("blockNumber")),
              "EVM_FROM_MATCH",str(tx.get("from","")).lower()==BUYER.lower(),
              "CONSENSUS_TO_MATCH",str(tx.get("to","")).lower()==CONSENSUS.lower(),
              "CALL_SELECTOR",str(tx.get("input",""))[:10],flush=True)
    receipt=rpc("eth_getTransactionReceipt",[EVM_TX])
    if not isinstance(receipt,dict):
        print("SE7_POSTMORTEM","NO_EVM_RECEIPT_AVAILABLE",flush=True)
        return 3
    print("SE7_POSTMORTEM","EVM_RECEIPT_STATUS",n(receipt.get("status")),
          "BLOCK",n(receipt.get("blockNumber")),
          "GAS_USED",n(receipt.get("gasUsed")),
          "LOG_COUNT",len(receipt.get("logs") or []),flush=True)
    if n(receipt.get("status"))!=1:
        print("SE7_POSTMORTEM","EVM_FAILED_STOP",flush=True)
        return 4
    new_tx_event="0x"+keccak(text="NewTransaction(bytes32,address,address)").hex()
    seen=set()
    for idx,entry in enumerate(receipt.get("logs") or []):
        if str(entry.get("address","")).lower()!=CONSENSUS.lower():continue
        topics=entry.get("topics") or []
        print("SE7_POSTMORTEM","CONSENSUS_LOG",idx,
              "TOPIC0",topics[0] if topics else "", "TOPICS",len(topics),flush=True)
        if len(topics)>1 and topics[1] not in seen:
            seen.add(topics[1])
            # Limit candidates, and only decode exact 32-byte event topics.
            if len(seen)<=5:check(topics[1])
    if not seen:print("SE7_POSTMORTEM","NO_INDEXED_GENLAYER_TXID_CANDIDATE",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(run())

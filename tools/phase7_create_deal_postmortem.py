"""Public-only chain postmortem for paid create_deal (16 Oct 2026).

NO signing, sender keys, tx replay, retries, wallet funding or branch merge.
Reuse proven legacy v0.6 getTransactionData/getTransactionAllData decoding.
The original deploy postmortem keeps its own historic constants unchanged.
"""
import phase7_current_deploy_postmortem as probe

EVM_TX="0xa8ea226dc7cce9dd9265c400198d08673774b4ebdf31f40171ac3e6d491441a4"
BUYER="0xa9afeBFEc83cEddcAE9b61a3A22971BF5e426e0C"
GHOST="0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a"

def run():
    probe.EVM_TX=EVM_TX
    probe.BUYER=BUYER
    print("SE7_CREATE_DEAL_TX",EVM_TX,flush=True)
    print("SE7_CREATE_DEAL_BUYER",BUYER,flush=True)
    tx=probe.rpc("eth_getTransactionByHash",[EVM_TX])
    if isinstance(tx,dict):
        print("SE7_CREATE_DEAL_VALUE_WEI",probe.n(tx.get("value")),flush=True)
        print("SE7_CREATE_DEAL_TX_TO_CONSENSUS",
              str(tx.get("to","")).lower()==probe.CONSENSUS.lower(),flush=True)
    r=probe.run()
    # Independent ABI-consistent forensic facts; do not claim that any EVM
    # status proves success in GenVM or expose raw user calldata in logs.
    import time,hashlib,re
    from eth_abi import decode
    from eth_utils import keccak
    from eth_utils.abi import collapse_if_tuple
    txid="0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06"
    blob=bytes.fromhex(txid[2:]).hex()
    stamp=format(int(time.time()),"064x")
    s1="0x"+keccak(text="getTransactionData(bytes32,uint256)")[:4].hex()
    s2="0x"+keccak(text="getTransactionAllData(bytes32)")[:4].hex()
    try:
        raw=probe.call(s1,blob+stamp)
        all_raw=probe.call(s2,blob)
        if raw is None or all_raw is None:
            print("SE7_CREATE_DEAL_DEEP_STATUS","READ_UNAVAILABLE",flush=True)
            return r
        abi_d=next(x for x in probe.ABI if x["name"]=="getTransactionData")["outputs"]
        abi_a=next(x for x in probe.ABI if x["name"]=="getTransactionAllData")["outputs"]
        one=decode([collapse_if_tuple(x) for x in abi_d],raw)[0]
        all_data=decode([collapse_if_tuple(x) for x in abi_a],all_raw)[0]
        print("SE7_CREATE_DEAL_CONSENSUS_NATIVE_VALUE",int(all_data[20]),flush=True)
        print("SE7_CREATE_DEAL_RESULT_TYPE",int(all_data[0]),
              "PREVIOUS_STATUS",int(all_data[2]),
              "EXECUTION_VOTE",int(all_data[1]),
              "CURRENT_STATUS",int(all_data[3]),flush=True)
        print("SE7_CREATE_DEAL_TX_ORIGIN_IS_BUYER",str(all_data[4]).lower()==BUYER.lower(),
              "SENDER_IS_BUYER",str(all_data[5]).lower()==BUYER.lower(),
              "TARGET_GHOST",str(all_data[6]).lower()==GHOST.lower(),flush=True)
        print("SE7_CREATE_DEAL_CODE_HASHES",
              all_data[14].hex(),all_data[15].hex(),flush=True)
        for label,v in (("ALL_EQ",all_data[17]),("LIVE_EQ",one[11])):
            if isinstance(v,bytes):
                print("SE7_CREATE_DEAL_"+label+"_BYTES",len(v),
                      "SHA256",hashlib.sha256(v).hexdigest(),flush=True)
                # Textual traceback may be stored here; only safe error
                # sentences; never dump untrusted calldata, binary or secrets.
                txt=v.decode("utf-8","replace")
                for line in txt.splitlines():
                    if any(k in line.lower() for k in (
                        "exception","error","revert","fail","traceback","attribute",
                        "validation","calldata","assertion","usererror")):
                        safe=re.sub(r"[^a-zA-Z0-9 .:_/=-]","?",line)[:180]
                        print("SE7_CREATE_DEAL_"+label+"_ERROR_HINT",safe,flush=True)
                        break
        print("SE7_CREATE_DEAL_CONSENSUS_MESSAGES",len(one[12]),
              "ROUNDS",int(one[20]),flush=True)
    except Exception as exc:
        print("SE7_CREATE_DEAL_DEEP_ERROR_CLASS",type(exc).__name__,flush=True)
    return r

if __name__=="__main__":
    raise SystemExit(run())

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
    return r

if __name__=="__main__":
    raise SystemExit(run())

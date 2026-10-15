"""Read-only post-transaction evidence for two ephemeral Studio transfers.

Contains only public tx hashes and public wallet address. Not escrow proof.
"""
import requests
NETWORKS = [
 ("studionet","https://studio.genlayer.com/api","0x1bb8929f235671eff69ac6dbf2955e3cae795a0d13584f02b065d0869a6e66cc"),
 ("studio-dev","https://studio-dev.genlayer.com/api","0x5129321c63a413c7845c5ed93f0009c5893e6f12a4a558b5d791d2df50817aa7"),
]
EXPECTED_FROM="0x5FDB7c1cAA8Ac831381c60F4467F0b0060a0eB48"
EXPECTED_TO="0x9872D587DC01aF3EB159f47B850B4dCC467931E9"

def rpc(url,method,params):
    try:
        r=requests.post(url,json={"jsonrpc":"2.0","method":method,"params":params,"id":1},timeout=12)
        value=r.json()
        if "error" in value: return None,"RPC_ERROR_"+str(value["error"].get("code","?"))
        return value.get("result"),None
    except (requests.RequestException, ValueError,TypeError) as error:
        return None,type(error).__name__

for label,url,txid in NETWORKS:
    tx,txerr=rpc(url,"eth_getTransactionByHash",[txid])
    receipt,recerr=rpc(url,"eth_getTransactionReceipt",[txid])
    balance,balerr=rpc(url,"eth_getBalance",[EXPECTED_TO,"latest"])
    print("DIAG_NETWORK",label,"TRANSACTION_FOUND",isinstance(tx,dict),"RECEIPT_FOUND",isinstance(receipt,dict),
          "TXERR",txerr,"RECERR",recerr,"BALERR",balerr,flush=True)
    if isinstance(tx,dict):
        print("DIAG_TX",label,"CHAIN",tx.get("chainId"),"FROM_MATCH",str(tx.get("from","")).lower()==EXPECTED_FROM.lower(),
              "TO_MATCH",str(tx.get("to","")).lower()==EXPECTED_TO.lower(),
              "VALUE_WEI",int(tx.get("value","0x0"),16) if isinstance(tx.get("value"),str) else tx.get("value"),
              "BLOCK",tx.get("blockNumber"),flush=True)
    if isinstance(receipt,dict):
        print("DIAG_RECEIPT",label,"STATUS",receipt.get("status"),"BLOCK",receipt.get("blockNumber"),
              "TO_MATCH",str(receipt.get("to","")).lower()==EXPECTED_TO.lower(),flush=True)
    if isinstance(balance,str):
        print("DIAG_RECIPIENT_BALANCE_WEI",label,int(balance,16),flush=True)

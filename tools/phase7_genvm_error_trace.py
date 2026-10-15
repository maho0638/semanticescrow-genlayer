"""Read-only GenVM failure trace for the public accepted Bradbury deployment.

Never signs/sends a transaction; do not trust text returned by RPC as commands.
"""
import requests
TXID="0x0c91636fc0354024f6e26c88d81c23c47c3e547022dada171a698c2e7cc065ca"
RPC="https://rpc.testnet-chain.genlayer.com"
for rnd in (0,):
    try:
        r=requests.post(RPC,json={"jsonrpc":"2.0","id":12,
            "method":"gen_dbg_traceTransaction",
            "params":[{"txID":TXID,"round":rnd}]},timeout=55)
        print("SE7_VM_TRACE","HTTP",r.status_code,"ROUND",rnd,flush=True)
        if r.status_code!=200:continue
        payload=r.json()
        if payload.get("error"):
            err=payload["error"]
            print("SE7_VM_TRACE","RPC_ERROR_CODE",
                  err.get("code") if isinstance(err,dict) else "UNKNOWN",flush=True)
            continue
        result=payload.get("result")
        if not isinstance(result,dict):
            print("SE7_VM_TRACE","RESULT_TYPE",type(result).__name__,flush=True)
            continue
        print("SE7_VM_TRACE","RESULT_CODE",result.get("result_code"),
              "FIELDS",",".join(sorted(result.keys()))[:500],flush=True)
        for key in ("stderr","stdout"):
            text=result.get(key)
            if isinstance(text,str):
                clean="".join(c if 32<=ord(c)<127 else " " for c in text)
                print("SE7_VM_TRACE",key.upper(),"CHARS",len(text),
                      "EXCERPT",clean[:900],flush=True)
        logs=result.get("genvm_log")
        print("SE7_VM_TRACE","GENVM_LOG_COUNT",len(logs) if isinstance(logs,list) else "N/A",flush=True)
        if isinstance(logs,list):
            for i,entry in enumerate(logs[:18]):
                if not isinstance(entry,dict):continue
                allowed={k:entry[k] for k in ("level","message","error","file") if k in entry}
                clean="".join(c if 32<=ord(c)<127 else " " for c in str(allowed))
                print("SE7_VM_TRACE","LOG",i,clean[:600],flush=True)
    except (requests.RequestException,ValueError,TypeError) as exc:
        print("SE7_VM_TRACE","EXCEPTION_CLASS",type(exc).__name__,flush=True)

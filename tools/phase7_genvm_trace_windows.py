"""READ-ONLY Bradbury GenVM error trace on Windows, no wallet/key/test GEN.

Uses the existing bounded loopback PowerShell bridge which previously passed
Bradbury RPC from Windows. Only requests known public transaction IDs.
Do NOT submit any transaction, sign, fund, or replay.
"""
import json
import re
import sys
from pathlib import Path

import requests
from phase7_windows_rpc_bridge import PowerShellRpcBridge

TXID = "0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06"
EXPECTED_DEPLOY="0x1ac72cb02a02cdf8709615b8aeed51610128dddd1a87128b58623aab73220c43"
PUBLIC_METHODS={"gen_dbg_traceTransaction","gen_getTransactionStatus"}

def clean(value):
    """Only public redacted error excerpts: no raw long data or secrets."""
    if not isinstance(value,str):
        return ""
    value = re.sub(r"https?://\S+","<URL>",value)
    value = re.sub(r"0x[0-9a-fA-F]{24,}","<HEX>",value)
    value = re.sub(r"(?i)(api[_ -]?key|authorization|bearer|private[_ -]?key|mnemonic)(\s*[:=]\s*)\S+",r"\1\2<REDACTED>",value)
    value = re.sub(r"[a-zA-Z0-9+/=]{90,}","<DATA>",value)
    return re.sub(r"[\r\n\t]+"," ",value)[:260]

def result_code_data(trace):
    if not isinstance(trace,dict):
        return {"available":False}
    ret={"available":True,"result_code":trace.get("result_code")}
    raw=trace.get("return_data","")
    if isinstance(raw,str) and raw.startswith("0x"):
        try:
            b=bytes.fromhex(raw[2:])
            ret["return_data_size"]=len(b)
            candidate=b.decode("utf-8","replace")
            if candidate.strip().isprintable():
                ret["return_text"]=clean(candidate)
        except (UnicodeError,ValueError):
            ret["return_data_invalid"]=True
    for key in ("stderr","stdout"):
        s=trace.get(key,"")
        if isinstance(s,str):
            clues=[clean(x) for x in s.splitlines() if any(w in x.lower()
                 for w in ("error","exception","traceback","failed","line ","typeerror","valueerror","usererror","vmerror"))]
            ret[key+"_hints"]=clues[-8:]
    logs=trace.get("genvm_log",[])
    if isinstance(logs,list):
        ret["log_count"]=len(logs)
        ret["log_hints"]=[clean(json.dumps(item,ensure_ascii=True)[:1200]) for item in logs[-12:]]
    return ret

def main():
    if sys.platform!="win32":
        print("SE7_TRACE_WINDOWS_ONLY");return 2
    bridge=PowerShellRpcBridge()
    endpoint=bridge.start()
    try:
        def read(method,params):
            if method not in PUBLIC_METHODS:
                raise ValueError("read-only RPC allowlist")
            resp=requests.post(endpoint,json={
                "jsonrpc":"2.0","id":1,"method":method,"params":params
            },timeout=70)
            resp.raise_for_status()
            obj=resp.json()
            if not isinstance(obj,dict) or "error" in obj:
                e=obj.get("error",{}) if isinstance(obj,dict) else {}
                print("SE7_TRACE_RPC_UNAVAILABLE",method,
                      "CODE",e.get("code","UNKNOWN") if isinstance(e,dict) else "UNKNOWN",flush=True)
                return None
            return obj.get("result")
        print("SE7_TRACE_SAFETY READ_ONLY_NO_KEYS_NO_GEN",flush=True)
        for name,tx in (("FAILED_CREATE_DEAL",TXID),("SUCCESSFUL_DEPLOY_REFERENCE",EXPECTED_DEPLOY)):
            print("SE7_TRACE_TARGET",name,tx,flush=True)
            status=read("gen_getTransactionStatus",[{"txId":tx}])
            if isinstance(status,dict):
                print("SE7_TRACE_STATUS",status.get("statusCode"),clean(status.get("status")),flush=True)
            trace=read("gen_dbg_traceTransaction",[{"txID":tx,"round":0}])
            if trace is not None:
                report=result_code_data(trace)
                print("SE7_TRACE_DETAIL",json.dumps(report,ensure_ascii=True,sort_keys=True),flush=True)
            else:
                print("SE7_TRACE_DETAIL_UNAVAILABLE",name,flush=True)
        return 0
    except (requests.RequestException,ValueError,OSError) as e:
        print("SE7_TRACE_TRANSPORT_ERROR",type(e).__name__,flush=True)
        return 3
    finally:
        bridge.close()

if __name__=="__main__":
    raise SystemExit(main())

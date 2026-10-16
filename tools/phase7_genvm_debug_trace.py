"""Read-only failed create_deal GenVM trace forensic report.
Only public GenLayer JSON-RPC; NO private keys, test GEN, submission or writes.
Do not echo raw calldatas, stdout or arbitrary errors (secrets may be embedded).
"""
import json, re, urllib.request, urllib.error

URL="https://rpc-bradbury.genlayer.com"
TX="0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06"
DEPLOY="0x1ac72cb02a02cdf8709615b8aeed51610128dddd1a87128b58623aab73220c43"

def rpc(method,args):
    payload=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":args}).encode()
    req=urllib.request.Request(URL,data=payload,
            headers={"Content-Type":"application/json","Accept":"application/json"},
            method="POST")
    try:
        with urllib.request.urlopen(req,timeout=45) as res:
            result=json.load(res)
    except urllib.error.HTTPError as e:
        print("SE7_DEBUG",method,"HTTP_STATUS",e.code,flush=True)
        return None
    except (urllib.error.URLError,TimeoutError,ValueError) as e:
        print("SE7_DEBUG",method,"TRANSPORT_ERROR_CLASS",type(e).__name__,flush=True)
        return None
    if not isinstance(result,dict):
        print("SE7_DEBUG",method,"MALFORMED_RESPONSE",flush=True);return None
    if "error" in result:
        err=result["error"]
        print("SE7_DEBUG",method,"RPC_ERROR_CODE",
            err.get("code") if isinstance(err,dict) else "UNKNOWN",flush=True)
        return None
    return result.get("result")

def sanitized(s):
    if not isinstance(s,str):return ""
    # Only errors, stack frames and source locations. Strip URLs, keys, raw
    # values, tokens and long hex/base64 strings; trace is untrusted.
    s=re.sub(r"0x[0-9a-fA-F]{10,}","<HEX>",s)
    s=re.sub(r"https?://[^\s]+","<URL>",s)
    s=re.sub(r"[A-Za-z0-9+/=]{70,}","<DATA>",s)
    return re.sub(r"[^a-zA-Z0-9 .,:'()_=/\[\]<>+-]","?",s)[:350]

def describe(txid,round_id=0):
    print("SE7_DEBUG_TRACE_ID",txid,"ROUND",round_id,flush=True)
    result=rpc("gen_dbg_traceTransaction",[{"txID":txid,"round":round_id}])
    if result is None:return False
    if not isinstance(result,dict):
        print("SE7_DEBUG_TRACE_MALFORMED",flush=True);return False
    print("SE7_DEBUG_TRACE_RESULT_CODE",result.get("result_code"),flush=True)
    print("SE7_DEBUG_TRACE_DURATION",sanitized(str(result.get("run_time","?"))),flush=True)
    for field in ("return_data","stdout","stderr"):
        value=result.get(field,"")
        print("SE7_DEBUG_TRACE_FIELD",field,"SIZE",len(str(value)),flush=True)
        if field=="return_data" and isinstance(value,str) and value.startswith("0x"):
            try:
                data=bytes.fromhex(value[2:])
                text=data.decode("utf-8","replace")
                print("SE7_DEBUG_TRACE_RETURN_DECODED",sanitized(text[:400]),flush=True)
            except Exception:pass
        if field in ("stderr","stdout") and isinstance(value,str):
            for line in value.splitlines()[-12:]:
                if any(w in line.lower() for w in ("error","traceback","attribute","exception","line ","invalid","typeerror","usererror","vmerror","file ")):
                    print("SE7_DEBUG_TRACE_TEXT",field,sanitized(line),flush=True)
    gl=result.get("genvm_log",[])
    print("SE7_DEBUG_TRACE_GENVM_LOG_COUNT",len(gl) if isinstance(gl,list) else "UNKNOWN",flush=True)
    for item in (gl if isinstance(gl,list) else [])[-20:]:
        print("SE7_DEBUG_TRACE_LOG",sanitized(json.dumps(item,ensure_ascii=True)[:1000]),flush=True)
    return True

def main():
    print("SE7_DEBUG_GENLAYER_RPC_CHECK",flush=True)
    ping=rpc("gen_dbg_ping",[])
    print("SE7_DEBUG_PING_AVAILABLE",ping is not None,flush=True)
    for tx in (TX,DEPLOY):
        status=rpc("gen_getTransactionStatus",[{"txId":tx}])
        if isinstance(status,dict):
            print("SE7_DEBUG_CONSENSUS_STATUS",tx,
                sanitized(str(status.get("status"))),status.get("statusCode"),flush=True)
        describe(tx)
    return 0
if __name__=="__main__":raise SystemExit(main())

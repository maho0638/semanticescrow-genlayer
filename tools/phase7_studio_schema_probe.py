"""Read-only Studio contract schema availability; no user wallet, keys or GEN.

Some newer SDK releases forbid get_contract_schema_for_code outside localnet.
This diagnoses whether the Studio JSON-RPC itself can still compute the schema
for the exact public contract bytes. No raw source/schema/error bodies logged.
"""
from pathlib import Path
import hashlib
import requests
CODE=Path("contracts/semantic_escrow.py").read_bytes()
RPCS=[
  ("hosted-studionet","https://studio.genlayer.com/api"),
  ("hosted-studio-dev","https://studio-dev.genlayer.com/api"),
]
for name,url in RPCS:
    payload={"jsonrpc":"2.0","id":23,
      "method":"gen_getContractSchemaForCode",
      "params":["0x"+CODE.hex()]}
    try:
        resp=requests.post(url,json=payload,timeout=65)
        try: data=resp.json()
        except ValueError: data={}
        result=data.get("result")
        err=data.get("error")
        fields=sorted(str(key) for key in result.keys()) if isinstance(result,dict) else []
        print("SE7_SCHEMA_PROBE",name,
             "HTTP",resp.status_code,
             "SUCCESS",isinstance(result,dict) and bool(result),
             "RPC_ERROR_CODE",err.get("code") if isinstance(err,dict) else None,
             "SCHEMA_FIELDS",",".join(fields[:18]),
             "SCHEMA_METHODS",
             len(result.get("methods",[])) if isinstance(result,dict) and isinstance(result.get("methods"),(dict,list)) else "N/A",
             "METHODS_TYPE",type(result.get("methods")).__name__ if isinstance(result,dict) else "N/A",
             "METHOD_NAMES",",".join(sorted(str(k) for k in result.get("methods",{}).keys())) if isinstance(result,dict) and isinstance(result.get("methods"),dict) else "N/A",
             "CODE_BYTES",len(CODE),
             "CODE_SHA256",hashlib.sha256(CODE).hexdigest(),
             flush=True)
    except requests.RequestException as e:
        print("SE7_SCHEMA_PROBE",name,"NETWORK_EXCEPTION",type(e).__name__,flush=True)

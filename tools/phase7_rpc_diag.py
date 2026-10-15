"""Read-only GenLayer RPC gateway diagnostics. No keys, transactions, or raw response bodies."""
import requests
import time

TARGETS = [
 ("bradbury", "https://rpc-bradbury.genlayer.com"),
 ("asimov", "https://rpc-asimov.genlayer.com"),
 ("chain", "https://rpc.testnet-chain.genlayer.com"),
 ("studionet", "https://studio.genlayer.com/api"),
]
REQ={"jsonrpc":"2.0", "id":1, "method":"eth_chainId", "params":[]}
for name,url in TARGETS:
    for attempt in range(2):
        try:
            r=requests.post(url,json=REQ,timeout=10,headers={"Content-Type":"application/json"})
            headers={k.lower():v for k,v in r.headers.items()}
            try:
                content=r.json()
                chain=content.get("result","N/A")
                code=content.get("error",{}).get("code","NONE")
            except (TypeError,ValueError):
                chain="NON_JSON"
                code="N/A"
            # We do not print CF-Ray values, IPs, cookies, or request body content.
            body=r.text[:2000].lower()
            body_class=("cloudflare" if "cloudflare" in body or "cf-" in body else
                "access_denied" if any(k in body for k in ("access denied","forbidden","request blocked")) else
                "other")
            print("SE7_RPC_DIAG",name,"ATTEMPT",attempt+1,
                  "HTTP",r.status_code,
                  "CHAIN",chain,
                  "RPC_ERROR",code,
                  "SERVER",headers.get("server","none")[:80],
                  "CF_RAY_PRESENT","cf-ray" in headers,
                  "CF_MITIGATED",headers.get("cf-mitigated","none"),
                  "WWW_AUTH","www-authenticate" in headers,
                  "CONTENT_TYPE",headers.get("content-type","none")[:90],
                  "BODY_CLASS",body_class,flush=True)
        except requests.RequestException as exc:
            print("SE7_RPC_DIAG",name,"FAIL_CLASS",type(exc).__name__,flush=True)
        time.sleep(1)

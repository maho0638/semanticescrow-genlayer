"""Temporary Bradbury testnet wallet runner, public keys printed, secrets in RAM only."""
import datetime, os, re, subprocess, sys, time
from pathlib import Path
import requests
from phase7_windows_rpc_bridge import PowerShellRpcBridge
from eth_account import Account
URL=None
END_AFTER=50*60
FUND_MIN=2*10**18

def rpc(method,params):
    r=requests.post(URL,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=15)
    if r.status_code==403 or r.headers.get("cf-mitigated")=="challenge":
        raise RuntimeError("Cloudflare has blocked this RPC connection")
    r.raise_for_status()
    data=r.json()
    if "error" in data: raise RuntimeError("RPC error "+str(data["error"].get("code","?")))
    return data.get("result")

def main():
    global URL
    import atexit
    bridge = PowerShellRpcBridge()
    URL = bridge.start()
    atexit.register(bridge.close)
    print("CHECKING BRADBURY RPC VIA LOCAL POWERSHELL...",flush=True)
    result=rpc("eth_chainId",[])
    assert isinstance(result,str) and int(result,16)==4221,"Wrong network"
    print("BRADBURY POWERSHELL RPC OK: 4221",flush=True)
    buyer,seller=Account.create(),Account.create()
    expires=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=END_AFTER)
    print("SEND ONLY BRADBURY TEST GEN TO THIS NEW ADDRESS:",flush=True)
    print(buyer.address,flush=True)
    print("Suggested: 5 TEST GEN. Script starts once >=2 TEST GEN is received.",flush=True)
    print("KEEP THIS WINDOW OPEN. SESSION EXPIRES UTC:",expires.isoformat(),flush=True)
    print("Never send GEN after the process exits; the keys are not stored.",flush=True)
    last=None
    while datetime.datetime.now(datetime.timezone.utc)<expires:
        try:
            value=int(rpc("eth_getBalance",[buyer.address,"latest"]),16)
            if value>=FUND_MIN:
                print("TEST GEN RECEIVED:",value,"wei",flush=True)
                break
            if value!=last:
                print("Balance now:",value,"wei",flush=True)
                last=value
        except Exception as e:
            print("Balance check failed:",type(e).__name__,flush=True)
        time.sleep(12)
    else:
        print("SESSION EXPIRED. DO NOT SEND TO THE ADDRESS NOW.",flush=True)
        return 2
    env=os.environ.copy()
    env["ACCOUNT_PRIVATE_KEY_1"]=buyer.key.hex()
    env["ACCOUNT_PRIVATE_KEY_2"]=seller.key.hex()
    binary=Path(sys.executable).parent/("gltest.exe" if os.name=="nt" else "gltest")
    args=[str(binary),"tests/test_phase7_bradbury_external.py","-v","-s",
          "--network","testnet_bradbury","--rpc-url",URL]
    print("Executing signed escrow test against Bradbury. Private keys stay in RAM.",flush=True)
    try:
        proc=subprocess.run(args,env=env,capture_output=True,text=True,errors="replace",timeout=55*60)
    except subprocess.TimeoutExpired:
        print("TIMEOUT: inspect chain state before retry.",flush=True)
        return 3
    finally:
        env.pop("ACCOUNT_PRIVATE_KEY_1",None)
        env.pop("ACCOUNT_PRIVATE_KEY_2",None)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("SE7_PUBLIC_"):
            print(line[:260],flush=True)
    if proc.returncode==0:
        print("CONTRACT TEST PASSED. Validate transaction hashes on Bradbury explorer.",flush=True)
        return 0
    errors=sorted(set(re.findall(
        r"\b(?:AssertionError|RuntimeError|TimeoutError|DeploymentError|TransactionError|ImportError|KeyError|AttributeError)\b",
        (proc.stdout or "")+"\n"+(proc.stderr or ""))))
    print("TEST FAILED, ERROR CLASSES:",",".join(errors) or "unknown",flush=True)
    print("No automatic retries; inspect transaction state before running again.",flush=True)
    return 1

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc:
        print("SESSION ENDED:",type(exc).__name__,str(exc)[:120],flush=True)
        sys.exit(1)

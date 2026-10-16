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
    env_preflight=os.environ.copy()
    env_preflight["ACCOUNT_PRIVATE_KEY_1"]=buyer.key.hex()
    env_preflight["ACCOUNT_PRIVATE_KEY_2"]=seller.key.hex()
    cli=Path(sys.executable).parent/("gltest.exe" if os.name=="nt" else "gltest")
    check_args=[str(cli),"tests/test_phase7_bradbury_readonly.py","-q","-s",
                "--network","testnet_bradbury","--rpc-url",URL]
    print("VERIFYING GENLAYER SDK OVER POWERSHELL BEFORE FUNDING...",flush=True)
    try:
        check=subprocess.run(check_args,env=env_preflight,capture_output=True,
                             text=True,errors="replace",timeout=240)
    except subprocess.TimeoutExpired:
        print("SDK READ-ONLY PREFLIGHT TIMED OUT. NO TEST GEN REQUESTED.",flush=True)
        return 4
    finally:
        env_preflight.pop("ACCOUNT_PRIVATE_KEY_1",None)
        env_preflight.pop("ACCOUNT_PRIVATE_KEY_2",None)
    # Print only explicitly authored public checkpoints, never raw gltest logs.
    for line in (check.stdout or "").splitlines():
        # Do not confuse pytest's source-code excerpts with real checkpoints.
        # Actual stdout is either a bare marker or a pytest test node prefix.
        stripped=line.strip()
        if stripped.startswith("SE7_PUBLIC_"):
            print(stripped[:280],flush=True)
        elif stripped.startswith("tests/") and " SE7_PUBLIC_" in stripped:
            print(stripped.split(" SE7_PUBLIC_",1)[1].join(("SE7_PUBLIC_",""))[:280],flush=True)
    if check.returncode!=0:
        failures=sorted(set(re.findall(
            r"\b(?:AssertionError|RuntimeError|TimeoutError|ImportError|"
            r"AttributeError|ValueError|KeyError|ConnectionError)\b",
            (check.stdout or "")+"\n"+(check.stderr or ""))))
        print("SDK READ-ONLY PREFLIGHT FAILED:",",".join(failures) or "unclassified",flush=True)
        print("DO NOT SEND GEN. RECHECK SDK/RPC CONFIGURATION.",flush=True)
        return 4
    print("GENLAYER SDK READ-ONLY PREFLIGHT OK",flush=True)
    if "--diagnose-only" in sys.argv:
        print("DIAGNOSTIC COMPLETE. NO TEST WALLET FUNDING REQUESTED.",flush=True)
        return 0
    # Default: reuse the first successful GenVM deployment, not another
    # expensive deploy. A new signing wallet is requested ONLY once the
    # prior contract's exact source and FINALIZED result are verified.
    reuse="--force-new-deploy" not in sys.argv
    if reuse:
        print("CHECKING EXISTING BRADBURY DEPLOYMENT FINALITY BEFORE FUNDING...",flush=True)
        read_env=os.environ.copy()
        read_env["ACCOUNT_PRIVATE_KEY_1"]=buyer.key.hex()
        read_env["ACCOUNT_PRIVATE_KEY_2"]=seller.key.hex()
        existing_cmd=[str(cli),"tests/test_phase7_bradbury_reuse_readonly.py","-q","-s",
                      "--network","testnet_bradbury","--rpc-url",URL]
        try:
            prior=subprocess.run(existing_cmd,env=read_env,capture_output=True,
                                 text=True,errors="replace",timeout=240)
        except subprocess.TimeoutExpired:
            print("EXISTING DEPLOY FINALITY CHECK TIMED OUT. DO NOT SEND GEN.",flush=True)
            return 4
        finally:
            read_env.pop("ACCOUNT_PRIVATE_KEY_1",None)
            read_env.pop("ACCOUNT_PRIVATE_KEY_2",None)
        for line in (prior.stdout or "").splitlines():
            line=line.strip()
            if line.startswith("SE7_PUBLIC_EXISTING_DEPLOY_FINALIZED_AND_SOURCE_ATTESTED"):
                print(line[:250],flush=True)
        if prior.returncode:
            print("EXISTING DEPLOYMENT NOT VERIFIED FINALIZED. NO NEW GEN REQUESTED.",flush=True)
            print("Wait for Bradbury finalization; do not redeploy blindly.",flush=True)
            return 4
        print("EXISTING DEPLOY VERIFIED. SKIPPING DUPLICATE DEPLOY.",flush=True)
    expires=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=END_AFTER)
    print("SEND ONLY BRADBURY TEST GEN TO THIS NEW ADDRESS:",flush=True)
    print(buyer.address,flush=True)
    print("Suggested: 2 TEST GEN for the existing contract. Script starts once >=2 TEST GEN is received.",flush=True)
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
    if reuse:
        env["SE7_USE_FINALIZED_EXISTING"]="1"
    binary=Path(sys.executable).parent/("gltest.exe" if os.name=="nt" else "gltest")
    args=[str(binary),"tests/test_phase7_bradbury_external.py","-v","-s",
          "--network","testnet_bradbury","--rpc-url",URL]
    print("Executing signed escrow test against Bradbury. Private keys stay in RAM.",flush=True)
    print("This may take several hours while onchain consensus and refund finalize. KEEP THIS WINDOW OPEN.",flush=True)
    try:
        proc=subprocess.run(args,env=env,capture_output=True,text=True,errors="replace",timeout=6*60*60)
    except subprocess.TimeoutExpired:
        print("TIMEOUT: inspect chain state before retry.",flush=True)
        return 3
    finally:
        env.pop("ACCOUNT_PRIVATE_KEY_1",None)
        env.pop("ACCOUNT_PRIVATE_KEY_2",None)
    for line in (proc.stdout or "").splitlines():
        # Keep only genuine public markers; pytest also prints failed-source
        # excerpts with marker text inside quotes, which are not checkpoints.
        stripped=line.strip()
        if stripped.startswith("SE7_PUBLIC_"):
            print(stripped[:260],flush=True)
        elif " SE7_PUBLIC_" in stripped and "::test_" in stripped:
            print(("SE7_PUBLIC_"+stripped.split(" SE7_PUBLIC_",1)[1])[:260],flush=True)
    if proc.returncode:
        # Only known project source frames, never raw receipts, headers,
        # env/private keys, URLs or raw exception text.
        for filename,line_number in re.findall(
            r"(test_phase7_bradbury_external\.py):(\d+):", (proc.stdout or "")+"\\n"+(proc.stderr or "")
        )[:4]:
            print("SE7_PUBLIC_FAILURE_SOURCE",filename,line_number,flush=True)

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

"""Ephemeral, public Bradbury test-only wallet. Key in RAM only; never output key."""
import os,json,time,base64,datetime,subprocess,sys
import requests
from eth_account import Account
REPO="maho0638/semanticescrow-genlayer"
BRANCH="test/phase7-bradbury-ephemeral-20261015"
PATH="status/phase7_live_wallet.json"
RPC="https://rpc-bradbury.genlayer.com"
http=requests.Session()
def rpc(method,args):
    r=http.post(RPC,json={"jsonrpc":"2.0","method":method,"params":args,"id":1},timeout=12)
    r.raise_for_status()
    obj=r.json()
    if "error" in obj:raise RuntimeError("RPC error code "+str(obj["error"].get("code")))
    return obj.get("result")
def publish(data):
    token=os.environ["GITHUB_TOKEN"]
    h={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json"}
    u=f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    old=http.get(u,headers=h,params={"ref":BRANCH},timeout=15)
    payload={"branch":BRANCH,"message":"test: update PUBLIC transient Bradbury funding status",
             "content":base64.b64encode(json.dumps(data,indent=2).encode()).decode()}
    if old.status_code==200: payload["sha"]=old.json()["sha"]
    res=http.put(u,headers=h,json=payload,timeout=20)
    if res.status_code not in (200,201):raise RuntimeError("Public wallet status update failed")
def main():
    if int(rpc("eth_chainId",[]),16)!=4221:raise RuntimeError("Wrong network: no test funds")
    buyer=Account.create()
    seller=Account.create()
    start=datetime.datetime.now(datetime.timezone.utc)
    expires=start+datetime.timedelta(minutes=40)
    state={"network":"Bradbury testnet ONLY","chain_id":4221,
           "public_buyer_address":buyer.address,"public_seller_address":seller.address,
           "expires_at_utc":expires.isoformat(),
           "state":"AWAITING_TEST_GEN","minimum_gen":"0.1",
           "suggested_gen":"2","warning":"DO NOT SEND AFTER EXPIRY. Key exists only in ephemeral job memory."}
    publish(state)
    print("SE7_PUBLIC_FUNDING_ADDRESS",buyer.address,flush=True)
    print("SE7_PUBLIC_EXPIRES",expires.isoformat(),flush=True)
    try:
        funded=False
        while datetime.datetime.now(datetime.timezone.utc)<expires:
            b=rpc("eth_getBalance",[buyer.address,"latest"])
            if b and int(b,16)>=10**17:funded=True;break
            time.sleep(12)
        if not funded:
            state["state"]="EXPIRED_UNFUNDED"
            state["warning"]="PRIVATE KEY NO LONGER AVAILABLE. DO NOT FUND."
            publish(state)
            print("SE7_PUBLIC_UNFUNDED_EXPIRED",flush=True)
            return
        state["state"]="FUNDED_TEST_RUNNING"
        state["funded_wei"]=str(int(b,16))
        publish(state)
        print("SE7_PUBLIC_FUNDED",state["funded_wei"],flush=True)
        env=os.environ.copy()
        env["ACCOUNT_PRIVATE_KEY_1"]=buyer.key.hex()
        env["ACCOUNT_PRIVATE_KEY_2"]=seller.key.hex()
        # No secrets in files, logs, repo, artifacts or output.
        p=subprocess.run(["gltest","tests/test_phase7_bradbury_external.py","-s",
                          "--network","testnet_bradbury"],env=env,
                          capture_output=True,text=True,timeout=60*45)
        for line in p.stdout.splitlines():
            if line.startswith("SE7_PUBLIC_"): print(line[:300],flush=True)
        state["state"]="PASSED" if p.returncode==0 else "FAILED"
        state["exit_code"]=p.returncode
        publish(state)
        print("SE7_PUBLIC_TEST_EXIT",p.returncode,flush=True)
        if p.returncode:sys.exit(1)
    except Exception as e:
        print("SE7_PUBLIC_FAILURE_CLASS",type(e).__name__,flush=True)
        try:
            state["state"]="FAILED_DO_NOT_FUND"
            publish(state)
        except Exception:pass
        sys.exit(1)
if __name__=="__main__":main()

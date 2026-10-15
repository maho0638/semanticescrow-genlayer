import requests,time
sites=[("bradbury","https://rpc-bradbury.genlayer.com"),("chain","https://rpc.testnet-chain.genlayer.com"),("asimov","https://rpc-asimov.genlayer.com")]
for k,url in sites:
    for attempt in range(2):
        try:
            r=requests.post(url,json={"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]},timeout=10,headers={"Content-Type":"application/json"})
            try: obj=r.json()
            except ValueError:obj={}
            print("SE7_RPC_PROBE",k,"ATTEMPT",attempt+1,"HTTP",r.status_code,"CHAIN",obj.get("result") or "N/A","RPC_ERROR",obj.get("error",{}).get("code","NONE"),flush=True)
        except Exception as e:print("SE7_RPC_PROBE",k,"FAIL_CLASS",type(e).__name__,flush=True)
        time.sleep(2)

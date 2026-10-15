"""Real Bradbury escrow cancel/refund; real Ghost recipient delta required."""
import os,json,time,datetime
from pathlib import Path
from eth_account import Account
from gltest import get_contract_factory,get_gl_client,get_default_account,get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.utils import extract_contract_address
BUYER=Account.from_key(os.environ["ACCOUNT_PRIVATE_KEY_1"])
SELLER=Account.from_key(os.environ["ACCOUNT_PRIVATE_KEY_2"])
VALUE=10**14
def query(p,m,args):
    r=p.make_request(m,args)
    if "error" in r:raise RuntimeError(m+" returned RPC error")
    return r.get("result")
def balance(p,addr):
    return int(query(p,"eth_getBalance",[addr,"latest"]),16)
def ok(receipt,step):
    passed=tx_execution_succeeded(receipt)
    print("SE7_PUBLIC_CONSENSUS",step,"PASS" if passed else "FAIL",flush=True)
    assert passed
def send(method,args,fees,value=0):
    return method(args=args).transact(value=value,fees=fees,consensus_max_rotations=3,
                                     wait_until="finalized",wait_interval=3000,wait_retries=140)
def test_bradbury_real_ghost_refund():
    c=get_gl_client()
    p=c.provider
    assert int(query(p,"eth_chainId",[]),16)==4221
    buyer=get_default_account()
    seller=next(a for a in get_accounts() if a.address.lower()==SELLER.address.lower())
    assert buyer.address.lower()==BUYER.address.lower()
    # Give seller funds to sign the two-party cancel confirmation.
    nonce=int(query(p,"eth_getTransactionCount",[buyer.address,"pending"]),16)
    gas_price=int(query(p,"eth_gasPrice",[]),16)
    signed=Account.sign_transaction({"nonce":nonce,"to":seller.address,"value":10**16,
                                    "gas":21000,"gasPrice":gas_price,"chainId":4221},BUYER.key)
    txid=query(p,"eth_sendRawTransaction",[signed.raw_transaction.to_0x_hex()])
    for _ in range(45):
        receipt=query(p,"eth_getTransactionReceipt",[txid])
        if receipt:
            assert receipt.get("status")=="0x1"
            break
        time.sleep(2)
    else:raise AssertionError("seller fee funding not mined")
    print("SE7_PUBLIC_SELLER_FUNDED",txid,flush=True)
    q=c.estimate_transaction_fees({"leaderTimeunitsAllocation":100,
         "validatorTimeunitsAllocation":200,
         "executionBudgetPerRound":10**15,
         "totalMessageFees":10**15,"appealRounds":0,"rotations":[3]})
    assert "feeValue" in q and "distribution" in q
    fees={"distribution":q["distribution"],"feeValue":q["feeValue"]}
    fac=get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    d=fac.deploy_contract_tx(account=buyer,fees=fees,wait_until="finalized",
                             consensus_max_rotations=3,wait_retries=140,wait_interval=3000)
    ok(d,"DEPLOY")
    ghost=extract_contract_address(d)
    code=query(p,"eth_getCode",[ghost,"latest"])
    assert code and code not in ("0x","0x0")
    print("SE7_PUBLIC_GHOST",ghost,flush=True)
    con=fac.build_contract(contract_address=ghost,account=buyer)
    due=int(datetime.datetime.now(datetime.timezone.utc).timestamp())+2*86400
    terms=[{"amount_wei":str(VALUE),"delivery_due_at":due,
          "criteria_text":"Bradbury testnet refund verification",
          "criteria_items":[{"id":"delivery","text":"Valid delivery proof","mandatory":True}]}]
    ok(send(con.create_deal,[seller.address,json.dumps(terms),"phase7-live"],fees,VALUE),"DEAL_FUNDED")
    assert json.loads(con.get_ledger(args=[0]).call())["remaining_locked"]==str(VALUE)
    ok(send(con.propose_cancel,[0],fees),"CANCEL_PROPOSED")
    before=balance(p,buyer.address)
    ok(send(con.connect(seller).confirm_cancel,[0],fees),"CANCEL_CONFIRMED")
    rows=json.loads(con.get_transfer_intents(args=[0]).call())
    assert len(rows)==1 and rows[0]["recipient"].lower()==buyer.address.lower()
    assert rows[0]["amount_wei"]==str(VALUE) and rows[0]["status"]=="QUEUED_UNVERIFIED"
    print("SE7_PUBLIC_SETTLEMENT_INTENT",rows[0]["intent_id_sha256"],flush=True)
    assert int(con.get_total_locked().call())==0
    for _ in range(65):
        delta=balance(p,buyer.address)-before
        if delta==VALUE:
            print("SE7_PUBLIC_EVM_BENEFICIARY_CREDIT",delta,flush=True)
            return
        time.sleep(3)
    raise AssertionError("Ghost real beneficiary credit not independently proven")

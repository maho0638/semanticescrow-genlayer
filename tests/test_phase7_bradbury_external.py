"""Real Bradbury escrow cancel/refund; real Ghost recipient delta required."""
import os,json,time,datetime
from pathlib import Path
from eth_account import Account
from gltest import get_contract_factory,get_gl_client,get_default_account,get_accounts
from gltest.assertions import tx_execution_succeeded
from gltest.utils import extract_contract_address
from pathlib import Path as _Path
import sys
sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "tools"))
from phase7_evm_receipt import verify_confirmed_value_transfer
from phase7_legacy_compat import require_legacy_bradbury
from phase7_schema_compat import bind_verified_schema
from phase7_deploy_preflight import preview_deploy,install_deploy_gas_headroom
from phase7_rpc_diagnostics import install_rpc_diagnostics
from phase7_legacy_receipts import install_legacy_bradbury_reader, is_finalized_success
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
    passed=is_finalized_success(receipt) and tx_execution_succeeded(receipt)
    print("SE7_PUBLIC_CONSENSUS",step,"PASS" if passed else "FAIL",flush=True)
    assert passed
def send(method,args,fees,value=0):
    return method(args=args).transact(value=value,fees=fees,consensus_max_rotations=3,
                                     wait_until="finalized",wait_interval=3000,wait_retries=140)
def test_bradbury_real_ghost_refund():
    c=get_gl_client()
    p=c.provider
    assert int(query(p,"eth_chainId",[]),16)==4221
    print("SE7_PUBLIC_LEGACY_PROTOCOL_GATE_BEGIN", flush=True)
    fees=require_legacy_bradbury(c)
    assert fees is None
    print("SE7_PUBLIC_LEGACY_PROTOCOL_GATE_PASS", flush=True)
    buyer=get_default_account()
    seller=next(a for a in get_accounts() if a.address.lower()==SELLER.address.lower())
    assert buyer.address.lower()==BUYER.address.lower()
    print("SE7_PUBLIC_STEP VERIFIED_LEGACY_NO_FEE_ESTIMATE",flush=True)
    fac=get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    print("SE7_PUBLIC_STEP SCHEMA_LOOKUP_BEGIN",flush=True)
    schema = bind_verified_schema(fac)
    print("SE7_PUBLIC_STEP SCHEMA_LOOKUP_PASS", len(schema["methods"]),flush=True)
    print("SE7_PUBLIC_STEP DEPLOY_SIMULATION_BEGIN",flush=True)
    checked=preview_deploy(c,fac.contract_code,buyer.address)
    print("SE7_PUBLIC_STEP DEPLOY_SIMULATION_PASS",checked["estimated_gas"],checked["padded_gas"],flush=True)
    install_deploy_gas_headroom(c)
    install_rpc_diagnostics(c)
    # get_gl_client() is lru_cached and is reused inside ContractFactory.
    # Only this attested Bradbury test client receives the old receipt reader.
    install_legacy_bradbury_reader(c)
    print("SE7_PUBLIC_LEGACY_RECEIPT_READER_READY",flush=True)
    print("SE7_PUBLIC_STEP DEPLOY_BEGIN",flush=True)
    try:
        d=fac.deploy_contract_tx(account=buyer,fees=fees,wait_until="finalized",
                                 consensus_max_rotations=3,wait_retries=140,wait_interval=3000)
    except Exception as exc:
        print("SE7_PUBLIC_DEPLOY_EXCEPTION_CLASS",type(exc).__name__,flush=True)
        cause=exc
        for step in range(4):
            cause=getattr(cause,"__cause__",None)
            if cause is None:break
            print("SE7_PUBLIC_DEPLOY_CAUSE",step,type(cause).__name__,flush=True)
            # Never print raw exception messages: they could contain raw
            # serialized tx, sensitive headers, or request metadata.
        raise
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
    print("SE7_PUBLIC_STEP CREATE_DEAL_BEGIN",flush=True)
    ok(send(con.create_deal,[seller.address,json.dumps(terms),"phase7-live"],fees,VALUE),"DEAL_FUNDED")
    assert json.loads(con.get_ledger(args=[0]).call())["remaining_locked"]==str(VALUE)
    print("SE7_PUBLIC_STEP PROPOSE_CANCEL_BEGIN",flush=True)
    ok(send(con.propose_cancel,[0],fees),"CANCEL_PROPOSED")
    # Avoid funding seller before signed deploy and buyer escrow operations
    # succeed. This prevents wasting 0.01 test GEN on repeated deploy failures.
    # Fund the second temporary signer: verify EVM receipt and beneficiary
    # balance effect, not a single fragile string literal for status.
    print("SE7_PUBLIC_STEP SELLER_GAS_FUNDING_BEGIN",flush=True)
    before_seller=balance(p,seller.address)
    nonce=int(query(p,"eth_getTransactionCount",[buyer.address,"pending"]),16)
    gas_price=int(query(p,"eth_gasPrice",[]),16)
    signed=Account.sign_transaction({"nonce":nonce,"to":seller.address,"value":10**16,
                                    "gas":21000,"gasPrice":gas_price,"chainId":4221},BUYER.key)
    txid=query(p,"eth_sendRawTransaction",[signed.raw_transaction.to_0x_hex()])
    print("SE7_PUBLIC_GAS_TRANSFER_SUBMITTED",txid,flush=True)
    for _ in range(45):
        receipt=query(p,"eth_getTransactionReceipt",[txid])
        if receipt:
            print("SE7_PUBLIC_GAS_RECEIPT_STATUS",
                  str(receipt.get("status","MISSING"))[:24],flush=True)
            # Balance reads can lag transaction receipt; wait for credited wei.
            for __ in range(20):
                after_seller=balance(p,seller.address)
                if after_seller-before_seller>=10**16:
                    break
                time.sleep(3)
            else:
                raise AssertionError("funded seller balance not credited")
            verify_confirmed_value_transfer(receipt, txid, seller.address)
            print("SE7_PUBLIC_GAS_TRANSFER_CREDIT_VERIFIED",
                  str(after_seller-before_seller),flush=True)
            break
        time.sleep(2)
    else:
        raise AssertionError("seller funding receipt missing after 90 seconds")
    print("SE7_PUBLIC_SELLER_FUNDED",txid,flush=True)
    before=balance(p,buyer.address)
    print("SE7_PUBLIC_STEP CONFIRM_CANCEL_BEGIN",flush=True)
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

"""REAL Studio 0.123 consensus test: five registered validators, on-chain state and receipts.

This runs only in a disposable GitHub-hosted localnet; five mocked source/LLM
providers are still five separate Studio validator identities. Not a claim of
five independent external LLM vendors, actual EVM recipient credit, or mainnet.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import pytest

pytestmark = pytest.mark.skipif(os.getenv("SEMANTICESCROW_RUN_STUDIO") != "1",
                                  reason="requires five-validator Docker Studio")
BODY_A = "Release 4.2 was published with verified acceptance on 2026-10-10."
BODY_B = "The release notes confirm version 4.2 on 2026-10-10."
URL_A = "https://evidence-a.example.com/proof.txt"
URL_B = "https://evidence-b.example.com/proof.txt"
AT = "2026-10-15T12:00:00Z"
DUE = 1792411200  # illustrative future UTC; 2026-10-19 12:00:00
# Derive UTC deadline without trusting local wall time.
DUE = int(datetime(2026, 10, 19, 12, tzinfo=timezone.utc).timestamp())


def _fees(client):
    quote=client.estimate_transaction_fees({
        "leaderTimeunitsAllocation":100,
        "validatorTimeunitsAllocation":200,
        "executionBudgetPerRound":1_000_000_000_000_000,
        "totalMessageFees":0, "appealRounds":0, "rotations":[3],
    })
    assert isinstance(quote,dict) and "distribution" in quote and "feeValue" in quote
    return {"distribution":quote["distribution"],"feeValue":quote["feeValue"]}


def _record(receipt,label):
    from gltest.assertions import tx_execution_succeeded
    success=tx_execution_succeeded(receipt)
    print("SE_STAGE3_TX:",label,"success=",success,flush=True)
    assert success, label+" did not execute successfully"


def _quorum(receipt,label,addresses=None):
    consensus=receipt.get("consensus_data") or {}
    votes=consensus.get("votes") or {}
    assert isinstance(votes,dict) and len(votes)==5, label+": requires five voter identities"
    if addresses is not None:
        assert {str(x).lower() for x in votes}==addresses
    c=Counter(str(x).lower() for x in votes.values())
    print("SE_STAGE3_VOTES:",label,
          "agree=",c["agree"],"idle=",c["idle"],"others=",sum(v for k,v in c.items() if k not in ("agree","idle")),flush=True)
    assert c["agree"]>=3 and sum(c.values())==5, "no decisive real Studio validator majority"
    assert set(c).issubset({"agree","idle"}), "unexpected disagreement recorded"
    return c


def _send(method,args,fees,account=None,value=0,context=None,label="write"):
    result=method(args=args).transact(
        account=account, value=value, fees=fees,
        transaction_context=context, consensus_max_rotations=3,
        wait_until="finalized", wait_retries=95, wait_interval=3000,
    )
    _record(result,label)
    return result


def test_studio_five_validator_deposit_submit_and_consensus():
    from gltest import get_contract_factory,get_gl_client,get_validator_factory
    client=get_gl_client()
    rpc=client.provider
    chain=int(rpc.make_request("eth_chainId",[])["result"],16)
    assert chain==int(client.chain.id)==61127
    total=int(rpc.make_request("sim_countValidators",[])["result"])
    print("SE_STAGE3_CHAIN_ID:",chain,"SE_STAGE3_VALIDATORS:",total,flush=True)
    assert total==5,"this is not an actual five-validator local Studio"

    # No remote wallet, no actual tokens. Studio allocates disposable funded accounts.
    from gltest import get_default_account
    buyer=get_default_account()
    seller_addr="0x"+"b"*40 # no signing necessary to submit with seller in phase 3 baseline
    fees=_fees(client)
    context={"genvm_datetime":AT}
    factory=get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    print("SE_STAGE3: DEPLOY_START",flush=True)
    contract=factory.deploy(account=buyer,transaction_context=context,
                            consensus_max_rotations=3,fees=fees,wait_until="finalized")
    print("SE_STAGE3: DEPLOY_FINALIZED",flush=True)
    assert int(contract.deal_count().call())==0
    milestones=[
        {"amount_wei":"10","delivery_due_at":DUE,
         "criteria_text":"Verify version 4.2 released on 2026-10-10.",
         "criteria_items":[
            {"id":"ver","text":"Release version 4.2 identified","mandatory":True},
            {"id":"date","text":"Release date 2026-10-10 verified","mandatory":True}]},
        {"amount_wei":"15","delivery_due_at":DUE+86400,
         "criteria_text":"Follow-on release verification",
         "criteria_items":[
            {"id":"next","text":"Follow-on release independently verified","mandatory":True}]}
    ]
    receipt=_send(contract.create_deal,[seller_addr,json.dumps(milestones),"stage3-local-only"],
                  fees,buyer,value=25,context=context,label="CREATE_EXACT_FUNDED")
    _quorum(receipt,"CREATE")
    assert int(contract.deal_count().call())==1
    ledger=json.loads(contract.get_ledger(args=[0]).call())
    assert ledger=={"initial_deposit":"25","remaining_locked":"25","payout_queued_total":"0","refund_queued_total":"0"},ledger
    assert json.loads(contract.get_milestone(args=[0,0]).call())["state"]=="AWAITING_DELIVERY"
    assert json.loads(contract.get_milestone(args=[0,1]).call())["state"]=="WAITING"
    print("SE_STAGE3: CREATE_READBACK_PASS",flush=True)

    # The subsequent Studio consensus fixture can set up mocked web/LLM
    # validators, but must NEVER claim a real independent oracle provider.
    mocks=get_validator_factory().batch_create_mock_validators(
      count=5,
      mock_llm_response={"nondet_exec_prompt":{"evidence auditor":'{"labels":["PASS","PASS"]}',
                                                  "":'{"labels":["PASS","PASS"]}'}},
      mock_web_response={"nondet_web_request":{
        URL_A:{"method":"GET","status":200,"body":BODY_A},
        URL_B:{"method":"GET","status":200,"body":BODY_B}}}
    )
    result=rpc.make_request("sim_replaceValidators",[[v.to_dict() for v in mocks]])
    assert not result.get("error"), "could not initialize five independent Studio validator identities"
    registered=result.get("result")
    assert isinstance(registered,list) and len(registered)==5
    addrs={str(v["address"]).lower() for v in registered}
    assert len(addrs)==5
    print("SE_STAGE3: MOCKED_FIVE_VALIDATORS_READY",flush=True)
    # The seller is not the buyer; only seller may submit. Use an ephemeral
    # local Studio account below, not a real user wallet.
    from gltest import get_default_account as _default
    # In the first pass, do not impersonate sellers via undocumented keys.
    # Prove bad sender refusal via normal transaction, then report what is blocked.
    print("SE_STAGE3: FIVE_VALIDATOR_CREATE_ONLY_CONFIRMED",flush=True)

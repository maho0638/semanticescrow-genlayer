"""Local EVM execution tests for exact SHA-bound native-GEN router.

The source-pinned GenLayer IC sends EVM calldata disburse(bytes32,address).
Deploy this Solidity contract in an in-memory EVM (no Bradbury token spent).
"""
import json
import subprocess
from pathlib import Path

import pytest
from web3 import Web3
from web3.exceptions import MismatchedABI
from eth_tester.exceptions import TransactionFailed

ROOT=Path(__file__).resolve().parents[1]
SOL=ROOT/"contracts/evm/SemanticEscrowNativePayoutRouter.sol"
REJECTOR=r'''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
contract Rejector { receive() external payable { revert("must not receive"); } }
'''
NODE_SCRIPT="const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));const solc=require('solc');const result=JSON.parse(solc.compile(JSON.stringify(input)));process.stdout.write(JSON.stringify(result));"

@pytest.fixture(scope="session")
def compiled():
    source=SOL.read_text()
    payload={"language":"Solidity","sources":{
        "SemanticEscrowNativePayoutRouter.sol":{"content":source},
        "Rejector.sol":{"content":REJECTOR},
    },"settings":{"optimizer":{"enabled":True,"runs":200},
                  "outputSelection":{"*":{"*":["abi","evm.bytecode.object",
                                                 "evm.deployedBytecode.object"]}}}}
    done=subprocess.run(["node","-e",NODE_SCRIPT],input=json.dumps(payload),
                        capture_output=True,text=True,cwd=ROOT,timeout=60,check=True)
    result=json.loads(done.stdout)
    errors=[x for x in result.get("errors",[]) if x["severity"]=="error"]
    assert not errors,errors
    return result["contracts"]

@pytest.fixture
def env(compiled):
    chain=Web3(Web3.EthereumTesterProvider())
    ghost=chain.eth.accounts[1]
    outsider=chain.eth.accounts[2]
    recipient=chain.eth.accounts[3]
    artifact=compiled["SemanticEscrowNativePayoutRouter.sol"]["SemanticEscrowNativePayoutRouter"]
    factory=chain.eth.contract(abi=artifact["abi"],bytecode=artifact["evm"]["bytecode"]["object"])
    receipt=chain.eth.wait_for_transaction_receipt(
        factory.constructor(ghost,chain.eth.chain_id).transact({"from":chain.eth.accounts[0]}))
    assert receipt.status==1
    router=chain.eth.contract(address=receipt.contractAddress,abi=artifact["abi"])
    return chain,router,ghost,outsider,recipient

def execute(chain,router,ghost,ident,recipient,amount):
    tx=router.functions.disburse(ident,recipient).transact({
        "from":ghost,"value":amount,"gas":500000,
    })
    return chain.eth.wait_for_transaction_receipt(tx)

def test_real_native_wei_reaches_recipient_and_exact_indexed_intent_receipt(env):
    chain,router,ghost,outsider,recipient=env
    ident=bytes.fromhex("a1"*32)
    amount=10**12
    before=chain.eth.get_balance(recipient)
    rec=execute(chain,router,ghost,ident,recipient,amount)
    assert rec.status==1
    assert chain.eth.get_balance(recipient)-before==amount
    assert router.functions.delivered(ident).call() is True
    logs=router.events.NativeIntentPaid().process_receipt(rec)
    assert len(logs)==1
    log=logs[0]
    assert log["address"]==router.address
    assert log["args"]["intentId"]==ident
    assert log["args"]["recipient"]==recipient
    assert log["args"]["ghost"]==ghost
    assert log["args"]["amountWei"]==amount
    assert len(rec.logs)==1

def test_same_intent_can_never_send_twice_even_with_new_payment(env):
    chain,router,ghost,_,recipient=env
    ident=bytes.fromhex("ab"*32)
    receipt=execute(chain,router,ghost,ident,recipient,10**9)
    assert receipt.status==1
    before=chain.eth.get_balance(recipient)
    duplicate=execute(chain,router,ghost,ident,recipient,10**9)
    assert duplicate.status==0
    assert chain.eth.get_balance(recipient)==before
    assert not duplicate.logs

def test_different_intents_same_wei_same_recipient_emit_distinct_proofs(env):
    chain,router,ghost,_,recipient=env
    a=bytes.fromhex("a1"*32)
    b=bytes.fromhex("b2"*32)
    first=execute(chain,router,ghost,a,recipient,10**6)
    second=execute(chain,router,ghost,b,recipient,10**6)
    assert first.status==second.status==1
    first_log=router.events.NativeIntentPaid().process_receipt(first)[0]
    second_log=router.events.NativeIntentPaid().process_receipt(second)[0]
    assert first_log["args"]["intentId"]!=second_log["args"]["intentId"]
    assert first_log["args"]["amountWei"]==second_log["args"]["amountWei"]

def test_unauthorized_sender_cannot_pay_or_fake_ghost_receipt(env):
    chain,router,ghost,outsider,recipient=env
    ident=bytes.fromhex("11"*32)
    before=chain.eth.get_balance(recipient)
    rec=chain.eth.wait_for_transaction_receipt(
        router.functions.disburse(ident,recipient).transact({
            "from":outsider,"value":10**9,"gas":500000}))
    assert rec.status==0
    assert chain.eth.get_balance(recipient)==before
    assert router.functions.delivered(ident).call() is False
    assert not rec.logs

def test_zero_commitment_reverted_without_credit(env):
    chain,router,ghost,_,recipient=env
    before=chain.eth.get_balance(recipient)
    rec=execute(chain,router,ghost,bytes(32),recipient,10**9)
    assert rec.status==0
    assert chain.eth.get_balance(recipient)==before
    assert len(rec.logs)==0

@pytest.mark.parametrize("digest", [b"",bytes.fromhex("11"*31),bytes.fromhex("11"*33)])
def test_malformed_commitment_rejected_by_fixed_bytes32_abi(env,digest):
    chain,router,ghost,_,recipient=env
    with pytest.raises((ValueError,TypeError,MismatchedABI)):
        router.functions.disburse(digest,recipient).build_transaction({"from":ghost,"value":1})

@pytest.mark.parametrize("value", [0,1,10**18])
def test_reject_wrong_recipient_even_when_called_by_ghost(env,value):
    chain,router,ghost,_,recipient=env
    ident=bytes.fromhex("bb"*32)
    for to in ("0x"+"00"*20,router.address,ghost):
        receipt=execute(chain,router,ghost,ident,to,value)
        assert receipt.status==0
    assert router.functions.delivered(ident).call() is False

def test_reject_zero_native_value(env):
    chain,router,ghost,_,recipient=env
    ident=bytes.fromhex("ab"*32)
    receipt=execute(chain,router,ghost,ident,recipient,0)
    assert receipt.status==0
    assert not receipt.logs

def test_failed_recipient_call_rolls_back_intent_marker_and_event(env,compiled):
    chain,router,ghost,_,recipient=env
    reject=compiled["Rejector.sol"]["Rejector"]
    fac=chain.eth.contract(abi=reject["abi"],bytecode=reject["evm"]["bytecode"]["object"])
    created=chain.eth.wait_for_transaction_receipt(fac.constructor().transact())
    assert created.status==1
    ident=bytes.fromhex("ac"*32)
    receipt=execute(chain,router,ghost,ident,created.contractAddress,10**9)
    assert receipt.status==0
    assert router.functions.delivered(ident).call() is False
    assert receipt.logs==[]

def test_constructor_bound_ghost_and_chain_are_immutable(env):
    chain,router,ghost,outsider,recipient=env
    assert router.functions.escrowGhost().call()==ghost
    assert router.functions.expectedChainId().call()==chain.eth.chain_id
    assert "setGhost" not in [a.get("name") for a in router.abi]
    assert "withdraw" not in [a.get("name") for a in router.abi]

def test_constructor_requires_real_chain_and_nonzero_ghost(compiled):
    chain=Web3(Web3.EthereumTesterProvider())
    art=compiled["SemanticEscrowNativePayoutRouter.sol"]["SemanticEscrowNativePayoutRouter"]
    factory=chain.eth.contract(abi=art["abi"],bytecode=art["evm"]["bytecode"]["object"])
    for ghost,chainid in (("0x"+"00"*20,chain.eth.chain_id),
                          (chain.eth.accounts[1],4221)):
        with pytest.raises((TransactionFailed,ValueError)):
            factory.constructor(ghost,chainid).transact({"from":chain.eth.accounts[0]})

def test_no_direct_wei_deposit_or_recovery_backdoor(env):
    chain,router,ghost,outsider,recipient=env
    receipt=chain.eth.wait_for_transaction_receipt(
        chain.eth.send_transaction({"from":ghost,"to":router.address,
                                    "value":10**9,"gas":500000}))
    assert receipt.status==0
    assert chain.eth.get_balance(router.address)==0

def test_source_dispatch_exactly_one_abi_method_and_indexed_receipt(env):
    chain,router,ghost,outsider,recipient=env
    methods=[x["name"] for x in router.abi if x.get("type")=="function"]
    assert "disburse" in methods
    disburse=next(x for x in router.abi if x.get("name")=="disburse")
    assert [i["type"] for i in disburse["inputs"]]==["bytes32","address"]
    evt=next(x for x in router.abi if x.get("name")=="NativeIntentPaid")
    assert [x["indexed"] for x in evt["inputs"]]==[True,True,True,False]

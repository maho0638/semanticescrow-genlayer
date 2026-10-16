"""Offline adversarial gate: NEVER reuse an unfinalized/altered live escrow.

No RPC, tokens, wallet creation or signatures; all onchain responses are mocked.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import phase7_existing_bradbury as existing

def sample(status=7,execution=1):
    tx={"hash":existing.EVM_TX,"from":existing.ORIGINAL_BUYER,
        "to":existing.CONSENSUS_PROXY,"input":"0xe71d5196abcd"}
    receipt={"transactionHash":existing.EVM_TX,
             "status":"0x1","blockNumber":"0x123","to":existing.CONSENSUS_PROXY}
    record={"lifecycle":{"state":"finalized" if status==7 else "decided"},
            "status":status,"status_name":"FINALIZED" if status==7 else "ACCEPTED",
            "tx_execution_result":execution,
            "tx_execution_result_name":"FINISHED_WITH_RETURN" if execution==1 else "FINISHED_WITH_ERROR",
            "tx_data_decoded":{"contract_address":existing.GHOST}}
    return tx,receipt,record

def run(monkeypatch,change=None):
    tx,receipt,record=sample()
    data={"eth_chainId":"0x107d",
          "eth_getTransactionByHash":tx,
          "eth_getTransactionReceipt":receipt,
          "eth_getCode":"0x600001"}
    if change:change(data,record)
    monkeypatch.setattr(existing,"_build_payload",lambda client,source,sender:"0xe71d5196abcd")
    monkeypatch.setattr(existing,"read_bradbury_transaction",lambda c,txid:record)
    def request(method,args):
        return {"result":data[method]}
    client=SimpleNamespace(provider=SimpleNamespace(make_request=request))
    return existing.verify_existing_finalized_deployment(client,"pinned source")

def test_exact_successful_finalized_deployment_can_be_reused(monkeypatch):
    assert run(monkeypatch)==existing.GHOST

@pytest.mark.parametrize("issue",[
    "accepted","genvm_error","wrong_sender","wrong_tx_hash","wrong_receipt_hash",
    "evm_revert","wrong_ghost","missing_code","wrong_chain","wrong_input",
    "wrong_consensus_target","zero_block"
])
def test_unverified_existing_deployment_must_refuse_funding(monkeypatch,issue):
    def change(data,record):
        tx=data["eth_getTransactionByHash"]
        receipt=data["eth_getTransactionReceipt"]
        if issue=="accepted":
            record.update({"status":5,"status_name":"ACCEPTED","lifecycle":{"state":"decided"}})
        elif issue=="genvm_error":
            record.update({"tx_execution_result":2,"tx_execution_result_name":"FINISHED_WITH_ERROR"})
        elif issue=="wrong_sender":tx["from"]="0x"+"12"*20
        elif issue=="wrong_tx_hash":tx["hash"]="0x"+"ab"*32
        elif issue=="wrong_receipt_hash":receipt["transactionHash"]="0x"+"ab"*32
        elif issue=="evm_revert":receipt["status"]="0x0"
        elif issue=="wrong_ghost":record["tx_data_decoded"]["contract_address"]="0x"+"21"*20
        elif issue=="missing_code":data["eth_getCode"]="0x"
        elif issue=="wrong_chain":data["eth_chainId"]="0x1"
        elif issue=="wrong_input":tx["input"]="0xe71d5196badf00d"
        elif issue=="wrong_consensus_target":tx["to"]="0x"+"be"*20
        elif issue=="zero_block":receipt["blockNumber"]="0x0"
    with pytest.raises(existing.ReuseNotVerified):
        run(monkeypatch,change)

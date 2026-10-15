"""Read-only, fail-closed transaction decoder for Bradbury's proven v0.6 ABI.

Installed genlayer-py 0.19rc2 assumes newer ConsensusData/Train return shapes.
This compatibility shim is installed on ONE cached gltest client AFTER the
Bradbury chain, EIP-1967 implementations and fee policy have been verified.
It does not send or sign, invent successful execution, retry EVM payments, or
change any SDK module/class global.
"""
import json
import time
from pathlib import Path
from types import MethodType
from web3 import Web3
from genlayer_py.types import (
    TRANSACTION_STATUS_NUMBER_TO_NAME,
    EXECUTION_RESULT_NUMBER_TO_NAME,
)

BRADBURY_DATA = "0x85D7bf947A512Fc640C75327A780c90847267697"
_ABI = json.loads(Path(__file__).with_name("phase7_legacy_consensus_data_abi.json").read_text(encoding="utf-8"))
_REQUIRED = {"getTransactionData","getTransactionAllData","canFinalize"}
assert {entry.get("name") for entry in _ABI}==_REQUIRED


class LegacyReceiptError(RuntimeError):
    pass


def _canonical_id(v):
    try:
        blob=Web3.to_bytes(hexstr=v) if isinstance(v,str) else bytes(v)
    except Exception as exc:
        raise LegacyReceiptError("invalid transaction identifier") from exc
    if len(blob)!=32:
        raise LegacyReceiptError("transaction identifier must have 32 bytes")
    return "0x"+blob.hex()


def decode_bradbury_transaction(tx_id, data, all_record):
    tx_id=_canonical_id(tx_id)
    if not isinstance(data,(tuple,list)) or len(data)!=23:
        raise LegacyReceiptError("invalid legacy transaction data shape")
    if not isinstance(all_record,(tuple,list)) or len(all_record)!=21:
        raise LegacyReceiptError("invalid legacy all-data shape")
    if _canonical_id(data[18]).lower()!=tx_id.lower() or _canonical_id(all_record[12]).lower()!=tx_id.lower():
        raise LegacyReceiptError("inconsistent consensus transaction ids")
    status=int(data[17])
    execution=int(all_record[1])
    if status!=int(all_record[3]):
        raise LegacyReceiptError("legacy transaction status mismatch")
    status_name=TRANSACTION_STATUS_NUMBER_TO_NAME.get(str(status))
    execution_name=EXECUTION_RESULT_NUMBER_TO_NAME.get(str(execution))
    if status_name is None or execution_name is None:
        raise LegacyReceiptError("unknown legacy consensus status/result")
    destination=str(data[2])
    if not Web3.is_address(destination) or Web3.to_checksum_address(destination)=="0x0000000000000000000000000000000000000000":
        raise LegacyReceiptError("missing/invalid consensus recipient")
    return {
        "tx_id":tx_id,
        "status":status,
        "status_name":getattr(status_name,"value",str(status_name)),
        "tx_execution_result":execution,
        "tx_execution_result_name":getattr(execution_name,"value",str(execution_name)),
        "tx_data_decoded":{"contract_address":Web3.to_checksum_address(destination)},
        "triggered_transactions":[],
    }


def read_bradbury_transaction(client,transaction_hash):
    if client.chain.id!=4221:
        raise LegacyReceiptError("wrong chain")
    if client.chain.consensus_data_contract["address"].lower()!=BRADBURY_DATA.lower():
        raise LegacyReceiptError("ConsensusData address not verified")
    tx_id=_canonical_id(transaction_hash)
    storage=client.w3.eth.contract(address=BRADBURY_DATA,abi=_ABI)
    # No broad exception catch: RPC errors must remain visible, not fabricated as pending.
    raw=storage.functions.getTransactionData(tx_id,int(time.time())).call()
    all_record,rounds=storage.functions.getTransactionAllData(tx_id).call()
    return decode_bradbury_transaction(tx_id,raw,all_record)


def install_legacy_bradbury_reader(client):
    """Install only after caller completed require_legacy_bradbury(client)."""
    if client.chain.id!=4221:
        raise LegacyReceiptError("wrong chain")
    if client.chain.consensus_data_contract["address"].lower()!=BRADBURY_DATA.lower():
        raise LegacyReceiptError("ConsensusData address not verified")
    if getattr(client,"_phase7_legacy_reader_installed",False):
        return
    def bound(self,transaction_hash):
        return read_bradbury_transaction(self,transaction_hash)
    client.get_transaction=MethodType(bound,client)
    client._phase7_legacy_reader_installed=True

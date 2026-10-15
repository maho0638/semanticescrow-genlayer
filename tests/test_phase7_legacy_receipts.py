"""Offline fail-closed v0.6 ConsensusData -> SDK receipt conversion tests."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from eth_utils import to_checksum_address
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_legacy_receipts import (
    decode_bradbury_transaction,install_legacy_bradbury_reader,
    LegacyReceiptError,BRADBURY_DATA,
)

TXID="0x"+"ab"*32
DEST="0xfe3ADf6da8C9d4e13BA60791770E2A1d3852b45E"

def samples(status=5,execution=1):
    raw=[0]*23
    raw[2]=DEST
    raw[17]=status
    raw[18]=bytes.fromhex(TXID[2:])
    entire=[0]*21
    entire[1]=execution
    entire[3]=status
    entire[12]=bytes.fromhex(TXID[2:])
    return raw,entire

def test_verified_deploy_receipt_success_codes_and_address():
    raw,entire=samples()
    receipt=decode_bradbury_transaction(TXID,raw,entire)
    assert receipt["tx_data_decoded"]["contract_address"]==DEST
    assert receipt["status_name"]=="ACCEPTED"
    assert receipt["tx_execution_result_name"]=="FINISHED_WITH_RETURN"
    assert receipt["triggered_transactions"]==[]

def test_real_prior_bradbury_error_must_stay_error():
    raw,entire=samples(execution=2)
    receipt=decode_bradbury_transaction(TXID,raw,entire)
    assert receipt["tx_execution_result_name"]=="FINISHED_WITH_ERROR"
    from gltest.assertions import tx_execution_succeeded
    assert not tx_execution_succeeded(receipt)

@pytest.mark.parametrize("what",["bad_shape","id_mismatch","status_mismatch","zero_recipient","unknown_execution"])
def test_receipt_never_approves_bad_consensus_data(what):
    raw,entire=samples()
    if what=="bad_shape":raw.pop()
    if what=="id_mismatch":entire[12]=bytes.fromhex("cd"*32)
    if what=="status_mismatch":entire[3]=7
    if what=="zero_recipient":raw[2]="0x"+"00"*20
    if what=="unknown_execution":entire[1]=99
    with pytest.raises(LegacyReceiptError):
        decode_bradbury_transaction(TXID,raw,entire)

def test_only_scoped_bradbury_client_can_be_patched():
    good=SimpleNamespace(chain=SimpleNamespace(id=4221,consensus_data_contract={"address":BRADBURY_DATA}))
    install_legacy_bradbury_reader(good)
    assert good._phase7_legacy_reader_installed
    cached=good.get_transaction
    install_legacy_bradbury_reader(good)
    assert good.get_transaction==cached
    bad=SimpleNamespace(chain=SimpleNamespace(id=1,consensus_data_contract={"address":BRADBURY_DATA}))
    with pytest.raises(LegacyReceiptError):install_legacy_bradbury_reader(bad)

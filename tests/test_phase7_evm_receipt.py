"""Offline receipt-format test cases, no wallet/GEN and no network needed."""
import pytest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_evm_receipt import parse_evm_status, verify_confirmed_value_transfer

@pytest.mark.parametrize("status",["0x1","0x01","0X01",1,"0x0001"])
def test_successful_status_forms(status):
    if status=="0X01":
        with pytest.raises(AssertionError):
            parse_evm_status(status)
    else:
        assert parse_evm_status(status)==1

@pytest.mark.parametrize("status",["0x0",0,"0x00","0x2",None,"1",True,False,{},[]])
def test_bad_receipt_status_fails_closed(status):
    with pytest.raises(AssertionError):
        verify_confirmed_value_transfer({"status":status,"blockNumber":"0x123"}, "0xab", "0xcd")

def test_receipt_hash_and_to_are_consistent():
    receipt={"status":"0x01","blockNumber":"0x12",
             "transactionHash":"0xAA","to":"0xBB"}
    assert verify_confirmed_value_transfer(receipt,"0xaa","0xbb")
    with pytest.raises(AssertionError):
        verify_confirmed_value_transfer(receipt,"0xff","0xbb")
    with pytest.raises(AssertionError):
        verify_confirmed_value_transfer(receipt,"0xaa","0xcc")

@pytest.mark.parametrize("block",["0x0",0,None])
def test_unmined_receipt_cannot_pass(block):
    with pytest.raises(AssertionError):
        verify_confirmed_value_transfer({"status":"0x1","blockNumber":block},
                                        "0x01","0x02")

"""Offline tests for redacted READ-ONLY Windows transaction forensics."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_genvm_trace_windows import clean,result_code_data,TXID

def test_public_trace_preserves_short_error_but_not_raw_key():
    sample="ValueError: exact native GEN deposit required"
    assert clean(sample)==sample
    assert "LEAKED" not in clean("private_key=LEAKED")
    assert "LEAKED" not in clean("Authorization: LEAKED")
    assert "https://" not in clean("https://internal.example.com/secret")
    assert len(clean("A"*1000))<300

def test_failed_user_error_and_runtime_trace_can_be_diagnosed():
    trace={
        "result_code":1,
        "return_data":"0x"+b"exact native GEN deposit required".hex(),
        "stdout":"",
        "stderr":"Traceback (most recent call last):\nValueError: exact native GEN deposit required",
        "genvm_log":[{"level":"error","message":"UserError: exact native GEN deposit required"}],
    }
    parsed=result_code_data(trace)
    assert parsed["available"] is True
    assert parsed["result_code"]==1
    assert "exact native GEN deposit required" in parsed["return_text"]
    assert parsed["log_count"]==1
    assert parsed["stderr_hints"]

def test_vm_error_trace_does_not_invent_root_cause():
    trace={
        "result_code":2,"return_data":"0xdead",
        "stdout":"","stderr":"",
        "genvm_log":[{"level":"error","message":"VMError: unknown failure"}],
    }
    parsed=result_code_data(trace)
    assert parsed["result_code"]==2
    assert parsed["return_data_size"]==2
    assert "root_cause" not in parsed
    assert result_code_data(None)=={"available":False}

def test_known_failed_call_is_not_existing_successful_deploy():
    assert TXID=="0x1ba86f039ae5b7b6fc7cd6e1b4f8349fb16f3124f6c7e4b9f235d08b83e82c06"

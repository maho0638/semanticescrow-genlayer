"""Static safety ordering for the live, test-GEN-only escrow runner.

This does not assert onchain success. It prevents seller gas transfer from
occurring before signed deploy and create/propose events have succeeded.
"""
from pathlib import Path

EXTERNAL = Path("tests/test_phase7_bradbury_external.py")

def test_seller_transfer_happens_after_confirmed_deploy_and_deal():
    src = EXTERNAL.read_text(encoding="utf-8")
    markers = (
        'print("SE7_PUBLIC_STEP DEPLOY_BEGIN",flush=True)',
        'ok(d,"DEPLOY")',
        'ok(send(con.create_deal',
        'ok(send(con.propose_cancel',
        'print("SE7_PUBLIC_STEP SELLER_GAS_FUNDING_BEGIN",flush=True)',
        'txid=query(p,"eth_sendRawTransaction"',
        'ok(send(con.connect(seller).confirm_cancel',
    )
    indices=[src.index(m) for m in markers]
    assert indices==sorted(indices)
    assert len(set(indices))==len(indices)

def test_real_bradbury_gate_uses_current_funded_buyer_and_finalization():
    src=EXTERNAL.read_text(encoding="utf-8")
    assert "checked=preview_deploy(c,fac.contract_code,buyer.address)" in src
    assert "passed=is_finalized_success(receipt) and tx_execution_succeeded(receipt)" in src


def test_no_unconditional_private_key_logging_or_duplicate_retries():
    src=EXTERNAL.read_text(encoding="utf-8")
    assert 'BUYER.key' in src
    assert 'SE7_PUBLIC_GAS_TRANSFER_SUBMITTED' in src
    assert 'install_rpc_diagnostics(c)' in src
    assert 'print(BUYER.key' not in src
    assert 'print(SELLER.key' not in src
    assert 'while True:' not in src

def test_full_finality_windows_are_longer_than_bradbury_appeal_window():
    # 2026-10-16 real deployment was ACCEPTED yet could not finalize until
    # roughly 30 minutes later. Seven-minute client timeout lost wallet RAM.
    src=EXTERNAL.read_text(encoding="utf-8")
    runner=Path("tools/phase7_bradbury_windows.py").read_text(encoding="utf-8")
    assert src.count("wait_retries=1200")==2
    assert "for _ in range(1200)" in src
    assert "timeout=6*60*60" in runner
    assert "EXISTING DEPLOYMENT NOT VERIFIED FINALIZED. NO NEW GEN REQUESTED." in runner

"""Execute v2 IC constructor/zero-funds gate in v0.2.16 Direct Mode.

EVM Ghosts are NOT implemented in Studio/Direct Mode, so these tests
intentionally never pretend that Studio can prove EVM native payout.
"""
from datetime import datetime,timezone,timedelta
from pathlib import Path

V2="contracts/semantic_escrow_attributed_v2.py"
SELLER="0x"+"b"*40
BUYER="0x"+"a"*40

def sample_terms():
    import json
    now=datetime(2026,10,15,12,tzinfo=timezone.utc)
    return json.dumps([{
      "amount_wei":"100",
      "delivery_due_at":int((now+timedelta(days=4)).timestamp()),
      "criteria_text":"Verify completed source delivery",
      "criteria_items":[{"id":"delivery","text":"Public delivery receipt","mandatory":True}],
    }])

def test_v2_deploy_constructor_fails_closed_until_evm_router_bound(direct_vm,direct_deploy):
    direct_vm.warp("2026-10-15T12:00:00+00:00")
    c=direct_deploy(V2)
    assert int(c.deal_count())==0
    direct_vm.sender=BUYER
    direct_vm.value=100
    with direct_vm.expect_revert("payout router must be configured before deposit"):
        c.create_deal(SELLER,sample_terms(),"should-not-fund")
    assert int(c.deal_count())==0

def test_v2_rejects_unapproved_router_update_without_evm_rpc(direct_vm,direct_deploy):
    direct_vm.warp("2026-10-15T12:00:00+00:00")
    direct_vm.sender=BUYER
    c=direct_deploy(V2)
    direct_vm.sender="0x"+"f"*40
    direct_vm.value=0
    with direct_vm.expect_revert("only deployer can configure router"):
        c.configure_payment_router("0x"+"c"*40)
    assert int(c.deal_count())==0

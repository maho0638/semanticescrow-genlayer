"""Stage-4 direct GEN ledger and transfer-intent safety regression suite.

Never confuse outbound message intent with proof of recipient credit.
Runs with deterministic local GenVM Direct Mode, without real GEN.
"""
import json
from datetime import datetime, timezone, timedelta
import pytest

from test_phase2_contract import (
    CONTRACT, BUYER, SELLER, DUE, A, B, BODY_A, BODY_B, NOW,
    terms, manifest, deploy, open_deal, submitted, mock_evidence,
)

ATTACKER="0x"+"c"*40
SECOND_BUYER="0x"+"d"*40


def ledger(c, idx):
    return {k:int(v) for k,v in json.loads(c.get_ledger(idx)).items()}


def check(c, *ids):
    assert sum(ledger(c,x)["remaining_locked"] for x in ids)==int(c.get_total_locked())
    for i in ids:
        l=ledger(c,i)
        assert l["initial_deposit"]==l["remaining_locked"]+l["payout_queued_total"]+l["refund_queued_total"]
        assert all(0<=n<2**256 for n in l.values())


def at(vm, unix):
    vm.warp(datetime.fromtimestamp(unix,tz=timezone.utc).isoformat())


def approve_first(vm,c,idx):
    vm.value=0
    vm.sender=SELLER
    c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))
    mock_evidence(vm,["PASS","PASS"])
    assert c.assess(idx)=="APPROVED"
    milestone=json.loads(c.get_milestone(idx,0))
    at(vm,milestone["assessed_at"]+172800)
    vm.sender=ATTACKER
    c.settle(idx)


def test_empty_contract_has_no_liabilities(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    assert int(c.get_total_locked())==0
    assert int(c.deal_count())==0


def test_multiple_deals_isolated_aggregate_and_refunds(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(20,30),"one")
    y=open_deal(direct_vm,c,(8,12),"two")
    check(c,x,y)
    assert int(c.get_total_locked())==70
    direct_vm.value=0
    direct_vm.sender=ATTACKER
    at(direct_vm,DUE+172800)
    c.settle(x)
    check(c,x,y)
    assert ledger(c,x)["refund_queued_total"]==50
    assert ledger(c,y)["remaining_locked"]==20
    assert int(c.get_total_locked())==20
    c.settle(y)
    check(c,x,y)
    assert int(c.get_total_locked())==0
    with direct_vm.expect_revert("deal terminated"):
        c.settle(x)
    with direct_vm.expect_revert("deal terminated"):
        c.settle(y)


def test_multistage_one_payout_then_remaining_refund_no_double(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(20,30))
    check(c,x)
    approve_first(direct_vm,c,x)
    check(c,x)
    assert ledger(c,x)==dict(initial_deposit=50,remaining_locked=30,
                              payout_queued_total=20,refund_queued_total=0)
    with direct_vm.expect_revert("delivery active"):
        c.settle(x)
    at(direct_vm,DUE+86400+172800)
    c.settle(x)
    check(c,x)
    assert ledger(c,x)==dict(initial_deposit=50,remaining_locked=0,
                              payout_queued_total=20,refund_queued_total=30)
    with direct_vm.expect_revert("deal terminated"):
        c.settle(x)


def test_verified_failure_returns_all_including_future(direct_vm,direct_deploy):
    c,x=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["FAIL","PASS"])
    assert c.assess(x)=="REJECTED"
    m=json.loads(c.get_milestone(x,0))
    at(direct_vm,m["assessed_at"]+172800)
    direct_vm.sender=ATTACKER
    c.settle(x)
    check(c,x)
    assert ledger(c,x)["refund_queued_total"]==50
    assert json.loads(c.get_milestone(x,1))["state"]=="CANCELED_REFUNDED_QUEUED"


def test_inconclusive_review_expiry_refund_is_permissionless(direct_vm,direct_deploy):
    c,x=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["UNKNOWN","PASS"])
    assert c.assess(x)=="INCONCLUSIVE"
    assert int(c.get_total_locked())==50
    m=json.loads(c.get_milestone(x,0))
    direct_vm.sender=ATTACKER
    at(direct_vm,m["submitted_at"]+604800-1)
    with direct_vm.expect_revert("review active"):
        c.settle(x)
    check(c,x)
    at(direct_vm,m["submitted_at"]+604800)
    c.settle(x)
    assert ledger(c,x)["refund_queued_total"]==50
    check(c,x)


def test_mutual_cancel_after_first_payout_only_refunds_unqueued(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c)
    approve_first(direct_vm,c,x)
    direct_vm.sender=BUYER
    c.propose_cancel(x)
    direct_vm.sender=SELLER
    c.confirm_cancel(x)
    check(c,x)
    assert ledger(c,x)["payout_queued_total"]==20
    assert ledger(c,x)["refund_queued_total"]==30
    with direct_vm.expect_revert("deal terminated"):
        c.confirm_cancel(x)


def test_permissionless_settle_cannot_redirect_buyer_refund(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(42,),"sole")
    direct_vm.value=0
    direct_vm.sender=ATTACKER
    at(direct_vm,DUE+172800)
    c.settle(x)
    meta=json.loads(c.get_deal(x))
    assert meta["buyer"]==BUYER
    assert meta["seller"]==SELLER
    assert ledger(c,x)["refund_queued_total"]==42
    check(c,x)


def test_wrong_deposit_and_replay_never_increase_global_locked(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    direct_vm.sender=BUYER
    direct_vm.value=1
    with direct_vm.expect_revert("exact native GEN deposit required"):
        c.create_deal(SELLER,terms(20,30),"bad")
    assert int(c.get_total_locked())==0
    x=open_deal(direct_vm,c)
    assert int(c.get_total_locked())==50
    with direct_vm.expect_revert("duplicate buyer nonce"):
        open_deal(direct_vm,c)
    check(c,x)
    assert int(c.deal_count())==1


def test_different_buyers_same_nonce_do_not_conflict(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(7,),"same")
    direct_vm.sender=SECOND_BUYER
    direct_vm.value=11
    y=c.create_deal(SELLER,terms(11),"same")
    check(c,x,y)
    assert int(c.get_total_locked())==18


def test_non_parties_cannot_cancel_or_force_unearned_payout(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.sender=ATTACKER
    with direct_vm.expect_revert("not a deal party"):
        c.propose_cancel(x)
    with direct_vm.expect_revert("not a deal party"):
        c.confirm_cancel(x)
    with direct_vm.expect_revert("delivery active"):
        c.settle(x)
    check(c,x)


def test_global_liability_after_early_and_late_deals(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(20,30),"first")
    approve_first(direct_vm,c,x)
    assert int(c.get_total_locked())==30
    direct_vm.sender=BUYER
    direct_vm.value=7
    y=c.create_deal(SELLER,terms(7),"later")
    check(c,x,y)
    assert int(c.get_total_locked())==37
    direct_vm.value=0
    at(direct_vm,DUE+86400+172800)
    direct_vm.sender=ATTACKER
    c.settle(x)
    c.settle(y)
    check(c,x,y)
    assert ledger(c,x)["payout_queued_total"]==20
    assert ledger(c,x)["refund_queued_total"]==30
    assert ledger(c,y)["refund_queued_total"]==7


def test_overflow_terms_fail_before_any_global_change(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    direct_vm.sender=BUYER
    direct_vm.value=0
    huge=json.loads(terms(1,1))
    huge[0]["amount_wei"]=str((1<<256)-1)
    with direct_vm.expect_revert("total deposit overflow"):
        c.create_deal(SELLER,json.dumps(huge),"overflow")
    assert int(c.get_total_locked())==0


def test_zero_and_oversized_amounts_cannot_create_liabilities(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    direct_vm.sender=BUYER
    direct_vm.value=0
    for amount in ["0",str(1<<256),"0001","-2","1.4"]:
        item=json.loads(terms(1))
        item[0]["amount_wei"]=amount
        with direct_vm.expect_revert():
            c.create_deal(SELLER,json.dumps(item),"invalid-"+amount[:8])
    assert int(c.deal_count())==0
    assert int(c.get_total_locked())==0


def test_mutual_cancellation_expiry_cannot_freeze_or_overpay(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.sender=BUYER
    c.propose_cancel(x)
    p=json.loads(c.get_deal(x))["cancel_expires_at"]
    at(direct_vm,p)
    direct_vm.sender=SELLER
    with direct_vm.expect_revert("cancellation expired"):
        c.confirm_cancel(x)
    check(c,x)
    direct_vm.sender=ATTACKER
    with direct_vm.expect_revert("delivery active"):
        c.settle(x)


def test_queued_outflow_is_not_claimed_as_recipient_credit(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c,(9,),"single")
    direct_vm.value=0
    at(direct_vm,DUE+172800)
    c.settle(x)
    meta=json.loads(c.get_deal(x))
    assert meta["state"]=="TERMINATED_QUEUED"
    assert ledger(c,x)["refund_queued_total"]==9
    assert not any("credited" in key or "received" in key for key in meta)
    assert int(c.get_total_locked())==0

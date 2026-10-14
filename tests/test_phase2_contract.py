"""Stage-2 contract input, authorization and deterministic ledger tests.

These are GenLayer Direct Mode tests, NOT five independent validators,
chain finalization proofs or beneficiary EVM receipt tests.
"""
import ast
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

CONTRACT = "contracts/semantic_escrow.py"
SELLER = "0x" + "b" * 40
BUYER = "0x" + "a" * 40
NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
DUE = int((NOW + timedelta(days=4)).timestamp())
A = "https://proof-a.example/release.txt"
B = "https://proof-b.example/manifest.txt"
BODY_A = b"Release version 4.2 completed and accepted on 2026-10-10."
BODY_B = b"Official changelog includes release 4.2 completed 2026-10-10."


def terms(*amounts):
    return json.dumps([
        {"amount_wei": str(amount), "delivery_due_at": DUE + i*86400,
         "criteria_text": "Verify version 4.2 was released on 2026-10-10.",
         "criteria_items": [
            {"id":"release", "text":"Explicit release version 4.2", "mandatory":True},
            {"id":"date", "text":"Explicit release date 2026-10-10", "mandatory":True},
         ]}
        for i, amount in enumerate(amounts)
    ])


def manifest(*entries):
    return json.dumps([{"url":url,"sha256":hashlib.sha256(body).hexdigest()}
                       for url,body in entries])


def deploy(direct_vm,direct_deploy):
    direct_vm.warp(NOW.isoformat())
    contract=direct_deploy(CONTRACT)
    direct_vm.sender=BUYER
    return contract


def open_deal(direct_vm,contract,amounts=(20,30),nonce="first"):
    direct_vm.sender=BUYER
    direct_vm.value=sum(amounts)
    return contract.create_deal(SELLER,terms(*amounts),nonce)


def test_contract_read_api_available(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    assert c.deal_count()==0


def test_public_api_fixed_width_not_python_int():
    tree=ast.parse(Path(CONTRACT).read_text(encoding="utf-8"))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="SemanticEscrow")
    names={n.name for n in cls.body if isinstance(n,ast.FunctionDef)}
    required={"create_deal","submit_evidence","assess","challenge","assess_challenge",
              "propose_cancel","confirm_cancel","settle","deal_count","get_deal",
              "get_milestone","get_assessment","get_ledger","get_terms_digest"}
    assert required<=names
    public=[f for f in cls.body if isinstance(f,ast.FunctionDef) and any(
        isinstance(d,ast.Attribute) and isinstance(d.value,ast.Attribute)
        and isinstance(d.value.value,ast.Name) and d.value.value.id=="gl"
        and d.value.attr=="public" for d in f.decorator_list)]
    assert len(public)>=13
    for fn in public:
        annotations=[p.annotation for p in fn.args.args if p.annotation]
        if fn.returns:annotations.append(fn.returns)
        assert not any(isinstance(a,ast.Name) and a.id=="int" for a in annotations)


def test_exact_funding_and_immutable_terms(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    assert int(idx)==0
    ledger=json.loads(c.get_ledger(idx))
    assert ledger=={"initial_deposit":"50","remaining_locked":"50",
                    "payout_queued_total":"0","refund_queued_total":"0"}
    meta=json.loads(c.get_deal(idx))
    assert meta["buyer"].lower()==BUYER.lower()
    assert meta["seller"].lower()==SELLER.lower()
    assert meta["state"]=="RUNNING"
    assert len(c.get_terms_digest(idx))==64
    assert json.loads(c.get_milestone(idx,0))["state"]=="AWAITING_DELIVERY"
    assert json.loads(c.get_milestone(idx,1))["state"]=="WAITING"


def test_duplicate_nonce_rejected(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    open_deal(direct_vm,c)
    with direct_vm.expect_revert("duplicate buyer nonce"):
        open_deal(direct_vm,c)
    assert int(c.deal_count())==1


@pytest.mark.parametrize("amounts",[(0,),(1,2,3,4,5,6),(-1,),(2,3)])
def test_value_or_term_shape_fail_closed(direct_vm,direct_deploy,amounts):
    c=deploy(direct_vm,direct_deploy)
    direct_vm.sender=BUYER
    direct_vm.value=1
    with direct_vm.expect_revert():
        c.create_deal(SELLER,terms(*amounts),"fail")
    assert int(c.deal_count())==0


def test_buyer_cannot_submit_seller_evidence(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    with direct_vm.expect_revert("unauthorized"):
        c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))


def test_seller_submit_and_freeze_manifest(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.sender=SELLER
    c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))
    m=json.loads(c.get_milestone(idx,0))
    assert m["state"]=="SUBMITTED"
    assert len(m["manifest_sha256"])==64
    with direct_vm.expect_revert("submission not available"):
        c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))


def test_duplicate_json_keys_and_private_host_fail(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.sender=SELLER
    with direct_vm.expect_revert("invalid evidence JSON"):
        c.submit_evidence(idx,'[{"url":"https://a.example/x","url":"https://b.example/x","sha256":"'+'0'*64+'"}]')
    with direct_vm.expect_revert("local or IP host"):
        c.submit_evidence(idx,manifest(("https://host.local/a",BODY_A),(B,BODY_B)))
    assert json.loads(c.get_milestone(idx,0))["state"]=="AWAITING_DELIVERY"


def test_no_early_settlement_or_unilateral_cancel(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    with direct_vm.expect_revert("delivery active"):
        c.settle(idx)
    c.propose_cancel(idx)
    with direct_vm.expect_revert("counterparty confirmation required"):
        c.confirm_cancel(idx)
    assert json.loads(c.get_ledger(idx))["remaining_locked"]=="50"

def mock_evidence(vm, labels):
    vm.mock_web(r"proof-a\.example",{"status":200,"body":BODY_A.decode()})
    vm.mock_web(r"proof-b\.example",{"status":200,"body":BODY_B.decode()})
    vm.mock_llm(r"evidence auditor",json.dumps({"labels":labels}))


def submitted(vm,deploy_fn):
    c=deploy(vm,deploy_fn)
    idx=open_deal(vm,c)
    vm.value=0
    vm.sender=SELLER
    c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))
    return c,idx


def test_approved_assessment_does_not_pay_early(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["PASS","PASS"])
    assert c.assess(idx)=="APPROVED"
    assert json.loads(c.get_milestone(idx,0))["state"]=="APPROVE_PENDING"
    assert json.loads(c.get_ledger(idx))["remaining_locked"]=="50"
    assert json.loads(c.get_assessment(idx,0,0))["outcome"]=="APPROVED"
    with direct_vm.expect_revert("challenge window active"):
        c.settle(idx)


def test_rejected_assessment_buyer_has_no_challenge_right(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["FAIL","PASS"])
    assert c.assess(idx)=="REJECTED"
    assert json.loads(c.get_milestone(idx,0))["state"]=="REJECT_PENDING"
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("unauthorized"):
        c.challenge(idx,manifest(("https://proof-c.example/report",b"More evidence")),"review")


def test_inconclusive_stays_submitted_without_release(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["UNKNOWN","PASS"])
    assert c.assess(idx)=="INCONCLUSIVE"
    assert json.loads(c.get_milestone(idx,0))["state"]=="SUBMITTED"
    assert json.loads(c.get_ledger(idx))["payout_queued_total"]=="0"


def test_buyer_challenge_cannot_be_repeated(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["PASS","PASS"])
    c.assess(idx)
    direct_vm.sender=BUYER
    new=manifest(("https://proof-c.example/report",b"New supplemental proof"))
    c.challenge(idx,new,"Not complete")
    m=json.loads(c.get_milestone(idx,0))
    assert m["challenge_used"] and m["state"]=="CHALLENGED"
    with direct_vm.expect_revert("not challengeable"):
        c.challenge(idx,new,"repeat")
    assert json.loads(c.get_assessment(idx,0,0))["outcome"]=="APPROVED"


def test_unavailable_source_does_not_commit_verdict(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    direct_vm.mock_web(r"proof-a\.example",{"status":503,"body":""})
    direct_vm.mock_web(r"proof-b\.example",{"status":503,"body":""})
    with direct_vm.expect_revert("unavailable evidence; retry"):
        c.assess(idx)
    assert json.loads(c.get_milestone(idx,0))["state"]=="SUBMITTED"
    assert json.loads(c.get_ledger(idx))["remaining_locked"]=="50"

def test_two_party_cancellation_queues_only_one_refund(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    c.propose_cancel(idx)
    direct_vm.sender=SELLER
    c.confirm_cancel(idx)
    led=json.loads(c.get_ledger(idx))
    assert led["remaining_locked"]=="0"
    assert led["refund_queued_total"]=="50"
    assert led["payout_queued_total"]=="0"
    assert json.loads(c.get_deal(idx))["state"]=="TERMINATED_QUEUED"
    with direct_vm.expect_revert("deal terminated"):
        c.settle(idx)


def test_timeout_settlement_refunds_when_delivery_missing(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.warp(datetime.fromtimestamp(DUE+172800,tz=timezone.utc).isoformat())
    c.settle(idx)
    led=json.loads(c.get_ledger(idx))
    assert led["refund_queued_total"]=="50" and led["remaining_locked"]=="0"
    with direct_vm.expect_revert("deal terminated"):
        c.settle(idx)


def test_successful_assessment_waits_then_advances_one_milestone(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["PASS","PASS"])
    assert c.assess(idx)=="APPROVED"
    first=json.loads(c.get_milestone(idx,0))
    direct_vm.warp(datetime.fromtimestamp(first["assessed_at"]+172800,tz=timezone.utc).isoformat())
    c.settle(idx)
    led=json.loads(c.get_ledger(idx))
    assert led["payout_queued_total"]=="20"
    assert led["remaining_locked"]=="30"
    assert json.loads(c.get_milestone(idx,0))["state"]=="PAYOUT_QUEUED"
    assert json.loads(c.get_milestone(idx,1))["state"]=="AWAITING_DELIVERY"
    direct_vm.sender=SELLER
    c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))
    assert json.loads(c.get_milestone(idx,1))["state"]=="SUBMITTED"

def test_final_challenge_reversal_keeps_first_verdict(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["PASS","PASS"])
    assert c.assess(idx)=="APPROVED"
    direct_vm.sender=BUYER
    extra_url="https://proof-c.example/third"
    extra_body=b"A dispute says version 4.2 did not ship."
    c.challenge(idx,manifest((extra_url,extra_body)),"Confirm release authenticity")
    direct_vm.clear_mocks()
    mock_evidence(direct_vm,["FAIL","PASS"])
    direct_vm.mock_web(r"proof-c\.example",{"status":200,"body":extra_body.decode()})
    assert c.assess_challenge(idx)=="REJECTED"
    m=json.loads(c.get_milestone(idx,0))
    assert m["first_verdict"]=="APPROVED"
    assert m["final_verdict"]=="REJECTED"
    assert m["state"]=="CHALLENGE_REJECT_PENDING"
    assert json.loads(c.get_assessment(idx,0,0))["outcome"]=="APPROVED"
    assert json.loads(c.get_assessment(idx,0,1))["outcome"]=="REJECTED"
    c.settle(idx)
    ledger=json.loads(c.get_ledger(idx))
    assert ledger["refund_queued_total"]=="50"
    assert ledger["payout_queued_total"]=="0"


def test_validator_rechecks_evidence_in_direct_mode(direct_vm,direct_deploy):
    c,idx=submitted(direct_vm,direct_deploy)
    mock_evidence(direct_vm,["PASS","PASS"])
    assert c.assess(idx)=="APPROVED"
    assert direct_vm.run_validator() is True
    direct_vm.clear_mocks()
    mock_evidence(direct_vm,["FAIL","PASS"])
    assert direct_vm.run_validator() is False


def test_delivery_expiry_exact_second_blocks_submission(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    idx=open_deal(direct_vm,c)
    direct_vm.value=0
    direct_vm.sender=SELLER
    direct_vm.warp(datetime.fromtimestamp(DUE+172800,tz=timezone.utc).isoformat())
    with direct_vm.expect_revert("delivery expired"):
        c.submit_evidence(idx,manifest((A,BODY_A),(B,BODY_B)))
    c.settle(idx)
    assert json.loads(c.get_ledger(idx))["remaining_locked"]=="0"

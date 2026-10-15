"""SemanticEscrow Stage 5: adversarial appeal / dispute flow tests (Direct Mode).

Application challenge != protocol validator appeal. No live GEN or deployment.
"""
import hashlib
import json
from datetime import datetime, timezone

import pytest
from test_phase2_contract import (
    A, B, BODY_A, BODY_B, BUYER, SELLER, DUE, NOW,
    deploy, open_deal, terms, manifest, submitted, mock_evidence,
)

ATTACKER = "0x" + "c" * 40
C = ("https://proof-c.example/review.txt", b"independent dispute report C")
D = ("https://proof-d.example/review.txt", b"independent dispute report D")
E = ("https://proof-e.example/review.txt", b"independent dispute report E")
F = ("https://proof-f.example/appeal.txt", b"new independent corrective appeal report F")
G = ("https://proof-g.example/appeal.txt", b"new independent corrective appeal report G")


def stage(c, x=0):
    return json.loads(c.get_milestone(x, 0))


def account(c, x=0):
    return {k: int(v) for k,v in json.loads(c.get_ledger(x)).items()}


def at(vm, moment):
    vm.warp(datetime.fromtimestamp(moment, tz=timezone.utc).isoformat())


def check_cash(c, x=0):
    bal=account(c,x)
    assert bal["initial_deposit"] == (bal["remaining_locked"]+bal["payout_queued_total"]+bal["refund_queued_total"])
    assert bal["remaining_locked"] == int(c.get_total_locked())
    return bal


def first(vm,deploy_fn,labels):
    c,x=submitted(vm,deploy_fn)
    mock_evidence(vm,labels)
    result=c.assess(x)
    vm.value=0
    return c,x,result


def supplemental(entries=(C,)):
    return manifest(*entries)


def case_challenge(vm,c,x,manifest_text,who=BUYER):
    vm.value=0
    vm.sender=who
    c.challenge(x,manifest_text,"Additional independent evidence disputes the prior decision")


def add_source_mocks(vm, entries):
    for url,body in entries:
        # Anchored host matching: avoid accidental overlap or unmocked URLs.
        hostname=url.split("/")[2].replace(".","\\.")
        vm.mock_web(hostname,{"status":200,"body":body.decode("utf-8")})


def test_buyer_can_challenge_approval_and_reversal_refunds(direct_vm,direct_deploy):
    c,x,result=first(direct_vm,direct_deploy,["PASS","PASS"])
    assert result=="APPROVED"
    original=json.loads(c.get_assessment(x,0,0))
    assert original["outcome"]=="APPROVED"
    case_challenge(direct_vm,c,x,supplemental())
    assert stage(c)["state"]=="CHALLENGED"
    assert stage(c)["first_verdict"]=="APPROVED"
    assert stage(c)["challenge_justification_sha256"]
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B),C])
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["FAIL","PASS"]}')
    assert c.assess_challenge(x)=="REJECTED"
    m=stage(c)
    assert m["first_verdict"]=="APPROVED" and m["final_verdict"]=="REJECTED"
    assert m["state"]=="CHALLENGE_REJECT_PENDING"
    assert json.loads(c.get_assessment(x,0,0))==original
    assert json.loads(c.get_assessment(x,0,1))["outcome"]=="REJECTED"
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["refund_queued_total"]==50
    assert account(c,x)["payout_queued_total"]==0
    assert check_cash(c,x)["remaining_locked"]==0


def test_seller_can_challenge_rejection_and_reversal_pays_once(direct_vm,direct_deploy):
    c,x,result=first(direct_vm,direct_deploy,["FAIL","PASS"])
    assert result=="REJECTED"
    case_challenge(direct_vm,c,x,supplemental(),who=SELLER)
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B),C])
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["PASS","PASS"]}')
    assert c.assess_challenge(x)=="APPROVED"
    assert stage(c)["first_verdict"]=="REJECTED"
    assert stage(c)["final_verdict"]=="APPROVED"
    assert stage(c)["state"]=="CHALLENGE_APPROVE_PENDING"
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["payout_queued_total"]==20
    assert account(c,x)["remaining_locked"]==30
    with direct_vm.expect_revert("delivery active"):
        c.settle(x)
    assert check_cash(c,x)["payout_queued_total"]==20


def test_approval_only_buyer_may_challenge(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    for role in [SELLER,ATTACKER]:
        direct_vm.sender=role
        with direct_vm.expect_revert("unauthorized"):
            c.challenge(x,supplemental(),"Protest by the wrong party")
    assert stage(c)["state"]=="APPROVE_PENDING"
    assert not stage(c)["challenge_used"]


def test_rejection_only_seller_may_challenge(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["FAIL","PASS"])
    for role in [BUYER,ATTACKER]:
        direct_vm.sender=role
        with direct_vm.expect_revert("unauthorized"):
            c.challenge(x,supplemental(),"Protest by the wrong party")
    assert stage(c)["state"]=="REJECT_PENDING"


def test_challenge_exact_cutoff_is_closed(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    at(direct_vm,stage(c)["assessed_at"]+172800)
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("challenge window expired"):
        c.challenge(x,supplemental(),"Too late")
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["payout_queued_total"]==20


def test_challenge_just_before_cutoff_is_open(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    at(direct_vm,stage(c)["assessed_at"]+172800-1)
    case_challenge(direct_vm,c,x,supplemental())
    assert stage(c)["state"]=="CHALLENGED"
    with direct_vm.expect_revert("challenge assessment active"):
        c.settle(x)


def test_challenge_appeal_review_exact_expiration_restores_original_approval(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    expiry=stage(c)["challenged_at"]+604800
    at(direct_vm,expiry)
    direct_vm.sender=SELLER
    with direct_vm.expect_revert("challenge review expired"):
        c.assess_challenge(x)
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["payout_queued_total"]==20
    assert stage(c)["first_verdict"]=="APPROVED"
    assert stage(c)["final_verdict"]==""
    assert json.loads(c.get_assessment(x,0,0))["outcome"]=="APPROVED"


def test_challenge_appeal_review_expiration_restores_original_rejection(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["FAIL","PASS"])
    case_challenge(direct_vm,c,x,supplemental(),who=SELLER)
    at(direct_vm,stage(c)["challenged_at"]+604800)
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["refund_queued_total"]==50
    assert account(c,x)["payout_queued_total"]==0


def test_replay_challenge_cannot_change_original_evidence(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    original_hash=stage(c)["manifest_sha256"]
    case_challenge(direct_vm,c,x,supplemental())
    challenged=stage(c)
    with direct_vm.expect_revert("not challengeable"):
        c.challenge(x,supplemental((D,)),"try to replace")
    assert stage(c)["challenge_sha256"]==challenged["challenge_sha256"]
    assert stage(c)["manifest_sha256"]==original_hash
    assert stage(c)["first_verdict"]=="APPROVED"


def test_challenge_requires_new_hash_and_hostname(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("challenge host duplicated"):
        c.challenge(x,manifest((A,C[1])),"existing host")
    with direct_vm.expect_revert("challenge evidence not new"):
        c.challenge(x,manifest((C[0],BODY_A)),"same raw hash")
    assert stage(c)["state"]=="APPROVE_PENDING"


def test_challenge_justification_must_be_bounded(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    direct_vm.sender=BUYER
    for note in ["", "x"*513, "invalid\ncontrol"]:
        with direct_vm.expect_revert("challenge note invalid"):
            c.challenge(x,supplemental(),note)
    assert stage(c)["challenge_used"] is False


def test_five_initial_sources_do_not_eliminate_challenge(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c)
    direct_vm.sender=SELLER
    direct_vm.value=0
    original=[(A,BODY_A),(B,BODY_B),C,D,E]
    c.submit_evidence(x,manifest(*original))
    add_source_mocks(direct_vm,original)
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["PASS","PASS"]}')
    assert c.assess(x)=="APPROVED"
    case_challenge(direct_vm,c,x,supplemental((F,G)))
    m=stage(c)
    assert m["state"]=="CHALLENGED"
    assert len(m["manifest"])==5 and len(m["challenge_manifest"])==2
    assert m["first_verdict"]=="APPROVED"
    assert m["challenge_used"] is True


def test_two_additional_sources_cap_enforced(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("evidence count"):
        c.challenge(x,supplemental((C,D,E)),"oversized added proof")
    assert stage(c)["state"]=="APPROVE_PENDING"
    assert not stage(c)["challenge_used"]


def test_inconclusive_challenge_preserves_state_and_original(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B),C])
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["UNKNOWN","PASS"]}')
    assert c.assess_challenge(x)=="INCONCLUSIVE"
    m=stage(c)
    assert m["state"]=="CHALLENGED"
    assert m["first_verdict"]=="APPROVED"
    assert m["final_verdict"]==""
    assert account(c,x)["remaining_locked"]==50
    assert json.loads(c.get_assessment(x,0,1))["outcome"]=="INCONCLUSIVE"


def test_unavailable_challenge_cannot_pay_or_change_verdict(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"proof-a\.example",{"status":503,"body":""})
    direct_vm.mock_web(r"proof-b\.example",{"status":503,"body":""})
    direct_vm.mock_web(r"proof-c\.example",{"status":503,"body":""})
    with direct_vm.expect_revert("challenge evidence unavailable; retry"):
        c.assess_challenge(x)
    assert stage(c)["state"]=="CHALLENGED"
    assert stage(c)["first_verdict"]=="APPROVED"
    assert account(c,x)["remaining_locked"]==50


def test_challenge_attacker_cannot_call_reassessment(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.sender=ATTACKER
    with direct_vm.expect_revert("not a deal party"):
        c.assess_challenge(x)
    assert stage(c)["state"]=="CHALLENGED"


def test_challenge_reversal_then_one_time_settlement_only(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B),C])
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["FAIL","PASS"]}')
    assert c.assess_challenge(x)=="REJECTED"
    direct_vm.sender=ATTACKER
    c.settle(x)
    with direct_vm.expect_revert("deal terminated"):
        c.settle(x)
    assert check_cash(c,x)["refund_queued_total"]==50


def test_challenge_is_frozen_after_mutual_cancel(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    direct_vm.sender=BUYER
    c.propose_cancel(x)
    direct_vm.sender=SELLER
    c.confirm_cancel(x)
    assert account(c,x)["refund_queued_total"]==50
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("deal terminated"):
        c.challenge(x,supplemental(),"cannot reopen")
    assert check_cash(c,x)["remaining_locked"]==0


def test_challenge_after_settlement_cannot_reopen_next_stage(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    at(direct_vm,stage(c)["assessed_at"]+172800)
    direct_vm.sender=ATTACKER
    c.settle(x)
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("not challengeable"):
        c.challenge(x,supplemental(),"late replay")
    assert stage(c)["state"]=="PAYOUT_QUEUED"
    assert account(c,x)["remaining_locked"]==30


def test_proposed_cancel_does_not_pause_challenge_clock(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    direct_vm.sender=SELLER
    c.propose_cancel(x)
    at(direct_vm,stage(c)["assessed_at"]+172800)
    direct_vm.sender=BUYER
    with direct_vm.expect_revert("challenge window expired"):
        c.challenge(x,supplemental(),"expired even with cancellation proposal")
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert account(c,x)["payout_queued_total"]==20


def test_verdicts_distinguish_app_challenge_from_protocol_appeal():
    # Protocol-level appeals are paid, pre-finality operations on consensus
    # contracts. An application-level challenge is a normal escrow write.
    # Do not mistakenly call a local challenge a network appeal.
    from pathlib import Path
    t=Path("contracts/semantic_escrow.py").read_text(encoding="utf-8")
    assert "def challenge(" in t and "def assess_challenge(" in t
    assert "gl.vm.run_nondet(" in t
    assert "sim_appeal" not in t


def test_unverified_new_source_cannot_overturn_first_verdict(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B)])
    direct_vm.mock_web(r"proof-c\.example",{"status":200,"body":"different bytes from SHA256 commitment"})
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["FAIL","PASS"]}')
    assert c.assess_challenge(x)=="INCONCLUSIVE"
    m=stage(c)
    assert m["state"]=="CHALLENGED"
    assert m["first_verdict"]=="APPROVED" and m["final_verdict"]==""
    decision=json.loads(c.get_assessment(x,0,1))
    assert decision["reason"]=="NO_VERIFIED_NEW_CHALLENGE_EVIDENCE"
    assert account(c,x)["remaining_locked"]==50


def test_unavailable_supplement_cannot_change_verdict_using_original_sources(direct_vm,direct_deploy):
    c,x,_=first(direct_vm,direct_deploy,["PASS","PASS"])
    case_challenge(direct_vm,c,x,supplemental())
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,[(A,BODY_A),(B,BODY_B)])
    direct_vm.mock_web(r"proof-c\.example",{"status":503,"body":""})
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["FAIL","PASS"]}')
    with direct_vm.expect_revert("challenge evidence unavailable; retry"):
        c.assess_challenge(x)
    assert stage(c)["state"]=="CHALLENGED"
    assert stage(c)["final_verdict"]==""
    assert account(c,x)["payout_queued_total"]==0
    assert account(c,x)["refund_queued_total"]==0


def test_seven_source_max_challenge_reversal_end_to_end(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    x=open_deal(direct_vm,c)
    initial=[(A,BODY_A),(B,BODY_B),C,D,E]
    direct_vm.sender=SELLER
    direct_vm.value=0
    c.submit_evidence(x,manifest(*initial))
    add_source_mocks(direct_vm,initial)
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["PASS","PASS"]}')
    assert c.assess(x)=="APPROVED"
    case_challenge(direct_vm,c,x,supplemental((F,G)))
    direct_vm.clear_mocks()
    add_source_mocks(direct_vm,initial+[F,G])
    direct_vm.mock_llm(r"evidence auditor",'{"labels":["FAIL","PASS"]}')
    assert c.assess_challenge(x)=="REJECTED"
    last=json.loads(c.get_assessment(x,0,1))
    assert len(last["source_results"])==7
    assert sum(row["integrity"]=="VERIFIED" for row in last["source_results"])==7
    assert stage(c)["first_verdict"]=="APPROVED"
    assert stage(c)["final_verdict"]=="REJECTED"
    direct_vm.sender=ATTACKER
    c.settle(x)
    assert check_cash(c,x)["refund_queued_total"]==50
    assert check_cash(c,x)["payout_queued_total"]==0

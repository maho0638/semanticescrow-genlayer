"""Phase 7 fail-closed, read-only transfer-intent accounting.

No transfer can be declared EVM-credited by a local state getter. Tests run
entirely on simulated Direct Mode balances; no wallets, GEN, network or gas.
"""
import json
import pytest
from test_phase2_contract import BUYER, SELLER, DUE, deploy, open_deal, submitted, mock_evidence
from test_phase4_payment import ATTACKER, at, approve_first, ledger, check


def intents(contract, idx):
    return json.loads(contract.get_transfer_intents(idx))


def assert_intent(row, deal, milestone, kind, recipient, amount):
    assert row["deal_id"] == int(deal)
    assert row["milestone_index"] == milestone
    assert row["kind"] == kind
    assert row["recipient"] == recipient
    assert row["amount_wei"] == str(amount)
    assert row["status"] == "QUEUED_UNVERIFIED"
    assert len(row["intent_id_sha256"]) == 64
    assert len(row["terms_digest_sha256"]) == 64
    assert "credited" not in row and "delivered" not in row
    assert "receipt" not in row and "child_status" not in row


def test_empty_and_pre_settlement_intents(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (20, 30))
    assert intents(c, x) == []
    with direct_vm.expect_revert("no queued transfer"):
        c.get_transfer_intent(x, 0)
    with direct_vm.expect_revert("milestone does not exist"):
        c.get_transfer_intent(x, 2)
    with direct_vm.expect_revert("deal does not exist"):
        c.get_transfer_intents(x + 1)
    assert ledger(c, x)["remaining_locked"] == 50


def test_payout_then_refund_have_unique_stable_intents(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (20, 30))
    approve_first(direct_vm, c, x)
    first = intents(c, x)
    assert len(first) == 1
    assert_intent(first[0], x, 0, "PAYOUT", SELLER, 20)
    assert json.loads(c.get_transfer_intent(x, 0)) == first[0]
    assert first[0]["terms_digest_sha256"] == c.get_terms_digest(x)
    assert ledger(c, x)["remaining_locked"] == 30
    with direct_vm.expect_revert("no queued transfer"):
        c.get_transfer_intent(x, 1)
    direct_vm.sender = ATTACKER
    at(direct_vm, DUE + 86400 + 172800)
    c.settle(x)
    rows = intents(c, x)
    assert len(rows) == 2 and rows[0] == first[0]
    assert_intent(rows[1], x, 1, "REFUND", BUYER, 30)
    assert rows[0]["intent_id_sha256"] != rows[1]["intent_id_sha256"]
    assert json.loads(c.get_transfer_intent(x, 1)) == rows[1]
    check(c, x)
    assert ledger(c, x) == dict(initial_deposit=50, remaining_locked=0,
                                 payout_queued_total=20, refund_queued_total=30)
    with direct_vm.expect_revert("deal terminated"):
        c.settle(x)
    assert intents(c, x) == rows


def test_single_stage_timeout_refund(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (9,), "late")
    direct_vm.sender = ATTACKER
    direct_vm.value = 0
    at(direct_vm, DUE + 172800)
    c.settle(x)
    rows = intents(c, x)
    assert len(rows) == 1
    assert_intent(rows[0], x, 0, "REFUND", BUYER, 9)
    assert int(c.get_total_locked()) == 0


def test_mutual_cancel_refunds_only_remaining_deposit(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (20, 30), "cancel")
    approve_first(direct_vm, c, x)
    direct_vm.sender = BUYER
    c.propose_cancel(x)
    direct_vm.sender = SELLER
    c.confirm_cancel(x)
    rows = intents(c, x)
    assert len(rows) == 2
    assert_intent(rows[0], x, 0, "PAYOUT", SELLER, 20)
    assert_intent(rows[1], x, 1, "REFUND", BUYER, 30)
    assert int(c.get_total_locked()) == 0


def test_failed_rubric_first_verdict_refunds_all(direct_vm, direct_deploy):
    c, x = submitted(direct_vm, direct_deploy)
    mock_evidence(direct_vm, ["FAIL", "PASS"])
    assert c.assess(x) == "REJECTED"
    assert intents(c, x) == []
    assessed = json.loads(c.get_milestone(x, 0))["assessed_at"]
    direct_vm.sender = ATTACKER
    at(direct_vm, assessed + 172800)
    c.settle(x)
    rows = intents(c, x)
    assert len(rows) == 1
    assert_intent(rows[0], x, 0, "REFUND", BUYER, 50)
    assert json.loads(c.get_milestone(x, 1))["state"] == "CANCELED_REFUNDED_QUEUED"
    with direct_vm.expect_revert("no queued transfer"):
        c.get_transfer_intent(x, 1)


def test_independent_deals_maintain_separate_intent_ids(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (12,), "alpha")
    y = open_deal(direct_vm, c, (12,), "beta")
    direct_vm.value = 0
    direct_vm.sender = ATTACKER
    at(direct_vm, DUE + 172800)
    c.settle(x)
    c.settle(y)
    a, b = intents(c, x), intents(c, y)
    assert_intent(a[0], x, 0, "REFUND", BUYER, 12)
    assert_intent(b[0], y, 0, "REFUND", BUYER, 12)
    assert a[0]["intent_id_sha256"] != b[0]["intent_id_sha256"]
    assert a[0]["terms_digest_sha256"] != b[0]["terms_digest_sha256"]
    check(c, x, y)


@pytest.mark.parametrize("amounts", [(1,), (7, 11), (3, 5, 8), (2, 3, 4, 5, 6)])
def test_multiple_milestones_refund_is_single_outbound_intent(direct_vm, direct_deploy, amounts):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, amounts, "multi")
    direct_vm.value = 0
    direct_vm.sender = ATTACKER
    at(direct_vm, DUE + 172800)
    c.settle(x)
    rows = intents(c, x)
    assert len(rows) == 1
    assert_intent(rows[0], x, 0, "REFUND", BUYER, sum(amounts))
    check(c, x)
    assert all(json.loads(c.get_milestone(x, i))["state"] ==
               "CANCELED_REFUNDED_QUEUED" for i in range(1, len(amounts)))


def test_read_only_intents_cannot_mutate_ledger(direct_vm, direct_deploy):
    c = deploy(direct_vm, direct_deploy)
    x = open_deal(direct_vm, c, (40,), "ro")
    before = c.get_ledger(x), int(c.get_total_locked()), c.get_deal(x)
    for _ in range(5):
        assert intents(c, x) == []
        with direct_vm.expect_revert("no queued transfer"):
            c.get_transfer_intent(x, 0)
    after = c.get_ledger(x), int(c.get_total_locked()), c.get_deal(x)
    assert before == after

"""Offline recovery guard adversarial tests; NEVER send, sign or fund test GEN."""
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from child_delivery_recovery_guard import ChildIncidentJournal,RecoveryForbidden,STATUS,_sha,canonical
from phase8_release_gate import EvidenceRejected
from test_phase8_release_gate import BUYER,SELLER,GHOST,HASH,BLOCK,intent,ledger,evm

PARENT="0x"+"ed"*32
NOTES="aa"*32

@pytest.fixture
def book(tmp_path):
    journal=ChildIncidentJournal(tmp_path/"incident.sqlite3")
    yield journal
    journal.close()

def enroll(book,rows=None,history=None,**changes):
    rows=rows if rows is not None else [intent(0,"PAYOUT",10),intent(1,"REFUND",15)]
    options={"chain_id":4221,"ghost":GHOST,"parent_tx":PARENT,"ledger":ledger(),
             "rows":rows,"deal_id":0,"buyer":BUYER,"seller":SELLER}
    options.update(changes)
    return book.register_queued(**options)

def item(index=0,kind="PAYOUT",amount=10):
    return intent(index,kind,amount)["intent_id_sha256"]

def observe(book,ident=None,**changes):
    tx,receipt,trace=evm()
    options={"tx_hash":HASH,"tx":tx,"receipt":receipt,"trace":trace,
             "before_wei":"100","after_wei":"110","block_hash":BLOCK,
             "confirmations":12}
    options.update(changes)
    return book.record_ghost_observation(ident or item(),**options)

def test_queued_intent_freezes_claim_and_never_authorizes_retry(book):
    assert enroll(book)["intent_count"]==2
    result=book.decision(item())
    assert result["state"]==STATUS
    assert result["child_value_credited_to_recipient"]=="UNPROVEN"
    assert result["native_value_recovered_by_ghost"]=="UNPROVEN"
    assert result["automatic_retry_allowed"] is False
    assert result["manual_resend_allowed"] is False
    assert book.audit()["events"]==2

def test_repeated_registration_same_data_is_idempotent(book):
    enroll(book)
    first=book.audit()
    enroll(book)
    assert book.audit()==first

def test_local_database_persists_immutable_frozen_snapshot(tmp_path):
    db=tmp_path/"evidence.sqlite3"
    with ChildIncidentJournal(db) as j:
        enroll(j)
        j.report_child_failure(item(),child_tx=HASH,reporter_notes_digest=NOTES)
        frozen=j.audit()
        assert frozen["events"]==3
    with ChildIncidentJournal(db) as j:
        assert j.audit()==frozen
        assert j.decision(item())["manual_resend_allowed"] is False
        assert enroll(j)["delivery"]=="UNVERIFIED"
        assert j.audit()==frozen

def test_reported_failure_does_not_imply_recoverable_funds(book):
    enroll(book)
    result=book.report_child_failure(item(),child_tx=HASH,reporter_notes_digest=NOTES)
    assert result["native_value_recovered_by_ghost"]=="UNPROVEN"
    assert result["automatic_retry_allowed"] is False
    assert book.audit()["events"]==3
    book.report_child_failure(item(),child_tx=HASH,reporter_notes_digest=NOTES)
    assert book.audit()["events"]==3

def test_ghost_value_call_unattributed_still_blocks_second_transfer(book):
    enroll(book)
    ret=observe(book)
    assert ret["child_value_credited_to_recipient"]=="UNPROVEN"
    assert ret["manual_resend_allowed"] is False
    assert book.audit()["events"]==3
    observe(book)
    assert book.audit()["events"]==3

def test_failed_then_observed_transfer_still_unknown(book):
    enroll(book)
    book.report_child_failure(item(),child_tx=HASH,reporter_notes_digest=NOTES)
    decision=observe(book)
    assert book.audit()["events"]==4
    assert decision["native_value_recovered_by_ghost"]=="UNPROVEN"
    assert decision["automatic_retry_allowed"] is False

@pytest.mark.parametrize("operation",["authorize_retry","authorize_rescue"])
def test_no_automatic_or_manual_authorization_even_when_incident_closed(book,operation):
    enroll(book)
    observe(book)
    for kw in ({},{"approved_by":"user"},{"receipt":"SUCCESS","operator_confirmed":True}):
        with pytest.raises(RecoveryForbidden):
            getattr(book,operation)(item(),**kw)

@pytest.mark.parametrize("change",[
    {"chain_id":1},{"chain_id":"4221"},
    {"ghost":BUYER+"BAD"},{"parent_tx":"0x123"},
    {"deal_id":1},{"buyer":SELLER},{"seller":BUYER},
])
def test_bad_ledger_context_rejected_before_journal_write(book,change):
    with pytest.raises(EvidenceRejected):
        enroll(book,**change)
    assert book.audit()["events"]==0

@pytest.mark.parametrize("field,invalid",[
    ("initial_deposit","24"),("payout_queued_total","9"),
    ("remaining_locked","25"),("refund_queued_total","14")
])
def test_inconsistent_bookkeeping_never_registers(book,field,invalid):
    b=ledger()
    b[field]=invalid
    with pytest.raises(EvidenceRejected):
        enroll(book,ledger=b)
    assert book.audit()["events"]==0

@pytest.mark.parametrize("field,invalid",[
    ("recipient",BUYER),("amount_wei","11"),
    ("status","PAID"),("intent_id_sha256","ab"*32),
    ("terms_digest_sha256","cc"*32),("kind","REFUND")
])
def test_forged_intent_is_not_enrolled(book,field,invalid):
    rows=[intent(0,"PAYOUT",10),intent(1,"REFUND",15)]
    rows[0][field]=invalid
    with pytest.raises(EvidenceRejected):
        enroll(book,rows=rows)
    assert book.audit()["events"]==0

def test_conflicting_exact_intent_with_different_ghost_never_overwrites(book):
    enroll(book)
    with pytest.raises(EvidenceRejected,match="conflicting"):
        enroll(book,ghost="0x"+"77"*20)
    assert book.audit()["events"]==2

def test_conflicting_exact_intent_with_different_parent_never_overwrites(book):
    enroll(book)
    with pytest.raises(EvidenceRejected,match="conflicting"):
        enroll(book,parent_tx="0x"+"de"*32)
    assert book.audit()["events"]==2

def test_ghost_observation_mismatched_recipient_rejected(book):
    enroll(book)
    tx,receipt,trace=evm()
    trace["calls"][0]["to"]=BUYER
    with pytest.raises(EvidenceRejected):
        observe(book,trace=trace)
    assert book.audit()["events"]==2

def test_ghost_observation_wrong_wei_rejected(book):
    enroll(book)
    with pytest.raises(EvidenceRejected):
        observe(book,after_wei="111")
    assert book.audit()["events"]==2

def test_ghost_observation_duplicate_calls_rejected(book):
    enroll(book)
    tx,receipt,trace=evm()
    trace["calls"].append(dict(trace["calls"][0]))
    with pytest.raises(EvidenceRejected):
        observe(book,trace=trace)
    assert book.audit()["events"]==2

def test_ghost_observation_unconfirmed_rejected(book):
    enroll(book)
    with pytest.raises(EvidenceRejected):
        observe(book,confirmations=11)
    assert book.audit()["events"]==2

def test_observation_cannot_be_recorded_for_unregistered_intent(book):
    with pytest.raises(EvidenceRejected,match="unregistered"):
        observe(book)
    assert book.audit()["events"]==0

def test_failed_message_report_must_have_nonempty_digest_and_hash(book):
    enroll(book)
    with pytest.raises(EvidenceRejected):
        book.report_child_failure(item(),child_tx="0xaa",reporter_notes_digest=NOTES)
    with pytest.raises(EvidenceRejected):
        book.report_child_failure(item(),child_tx=HASH,reporter_notes_digest="not-a-sha")
    assert book.audit()["events"]==2

def test_one_broken_intent_rolls_back_entire_batch(book):
    enroll(book)
    x=intent(2,"PAYOUT",4,deal=1)
    # First registrant has same intent id but different parent; second new
    # intent must not enter database if batch fails on conflict.
    with pytest.raises(EvidenceRejected):
        enroll(book,ghost="0x"+"77"*20)
    assert book.audit()["events"]==2

def test_no_fake_delivery_or_recovery_fields_in_journal_code():
    text=(Path(__file__).resolve().parents[1]/"tools/child_delivery_recovery_guard.py").read_text()
    assert "eth_sendRawTransaction" not in text
    assert "send_transaction(" not in text
    assert "private_key" not in text
    assert "automatic_retry_allowed" in text
    assert "manual_resend_allowed" in text

def test_detect_casual_local_incident_log_corruption(book):
    enroll(book)
    book.db.execute("UPDATE events SET event_hash=? WHERE seq=1",("0"*64,))
    with pytest.raises(EvidenceRejected,match="tampered"):
        book.audit()

def test_intent_snapshot_hash_is_verified_on_reads_and_audit(book):
    enroll(book)
    ident=item()
    row=book.db.execute("SELECT snapshot_json FROM intents WHERE intent_id=?",(ident,)).fetchone()
    mutated=row[0].replace('"amount_wei":"10"','"amount_wei":"11"')
    book.db.execute("UPDATE intents SET snapshot_json=? WHERE intent_id=?",(mutated,ident))
    with pytest.raises(EvidenceRejected,match="tampered immutable intent snapshot"):
        book.decision(ident)
    with pytest.raises(EvidenceRejected,match="tampered immutable intent snapshot"):
        book.audit()

def test_rehashed_snapshot_cannot_be_detached_from_original_queue_event(book):
    enroll(book)
    ident=item()
    row=book.db.execute("SELECT snapshot_json FROM intents WHERE intent_id=?",(ident,)).fetchone()
    import json
    snapshot=json.loads(row[0])
    snapshot["intent"]["amount_wei"]="11"
    raw=canonical(snapshot).decode("ascii")
    book.db.execute("UPDATE intents SET snapshot_json=?,snapshot_hash=? WHERE intent_id=?",
                    (raw,_sha(raw.encode("ascii")),ident))
    with pytest.raises(EvidenceRejected,match="not bound to its queued journal event"):
        book.decision(ident)
    with pytest.raises(EvidenceRejected,match="not bound to its queued journal event"):
        book.audit()

def test_locally_deleted_event_is_detected(book):
    enroll(book)
    book.db.execute("DELETE FROM events WHERE seq=1")
    with pytest.raises(EvidenceRejected,match="not bound to its queued journal event"):
        book.audit()

def test_mixed_refund_and_payout_are_both_independent_unknowns(book):
    enroll(book)
    assert book.decision(item(0,"PAYOUT",10))["manual_resend_allowed"] is False
    assert book.decision(item(1,"REFUND",15))["manual_resend_allowed"] is False
    assert book.audit()["events"]==2

def test_no_queued_intents_means_no_claim_that_value_moved(book):
    b=ledger(25,25,0,0)
    ret=enroll(book,rows=[],ledger=b)
    assert ret["intent_count"]==0
    assert book.audit()["events"]==0

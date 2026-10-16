"""Persistent, no-signature, no-retry GenLayer child-GEN incident journal.

An intent can be queued in a FINALIZED parent while the external Ghost
message's recipient credit is NOT known. This journal never assumes:
  - emitted intent == child transaction;
  - successful parent == beneficiary credit;
  - child failure == refunded/recoverable GEN;
  - timeout == authorization to send GEN again.

All writes are LOCAL SQLite records; no GenLayer RPC, wallets, keys, ETH
transactions, payouts or network are used by this module.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path

from phase8_release_gate import (
    EvidenceRejected, reconcile_queued_intents, assess_evm_transfer_observation,
    address, integer, require, RE_TX,
)

SCHEMA="SemanticEscrow.child-incident.v1"
STATUS="UNVERIFIED_MANUAL_INVESTIGATION"
EVENTS=frozenset({"QUEUED", "CHILD_FAILURE_REPORTED", "EVM_CALL_UNATTRIBUTED", "INCIDENT_REVIEWED"})
MAX_JSON_BYTES=16000

class RecoveryForbidden(EvidenceRejected):
    pass

def canonical(data):
    try:
        result=json.dumps(data,sort_keys=True,separators=(",",":"),
                          ensure_ascii=True,allow_nan=False).encode("ascii")
    except (ValueError,TypeError,UnicodeError) as exc:
        raise EvidenceRejected("invalid incident input JSON") from exc
    require(len(result)<=MAX_JSON_BYTES,"incident input too large")
    return result

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _hash_event(previous, seq, intent_id, code, evidence_digest):
    return _sha(canonical({
        "domain":SCHEMA,
        "previous":previous,
        "sequence":seq,
        "intent_id":intent_id,
        "event":code,
        "evidence_sha256":evidence_digest,
    }))

class ChildIncidentJournal:
    """Durable local double-send lock, NOT authenticated proof of payment."""

    def __init__(self,path):
        self.path=Path(path)
        if self.path.is_symlink():
            raise EvidenceRejected("symlink journal path forbidden")
        if self.path.exists() and not self.path.is_file():
            raise EvidenceRejected("journal must be a regular file")
        self.db=sqlite3.connect(str(self.path),timeout=20,isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=20000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS intents (
            intent_id TEXT PRIMARY KEY,
            snapshot_hash TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            chain_id INTEGER NOT NULL CHECK(chain_id=4221),
            ghost TEXT NOT NULL,
            parent_tx TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state='UNVERIFIED_MANUAL_INVESTIGATION')
          );
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_id TEXT NOT NULL,
            event TEXT NOT NULL,
            evidence_digest TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            FOREIGN KEY(intent_id) REFERENCES intents(intent_id)
          );
          CREATE UNIQUE INDEX IF NOT EXISTS idx_event_duplicate
            ON events(intent_id,event,evidence_digest);
        """)
        self.db.execute("PRAGMA foreign_keys=ON")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close()

    def _atomic(self,operation):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result=operation()
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _append(self,ident,event,digest):
        require(event in EVENTS,"unknown incident event")
        require(type(digest) is str and len(digest)==64 and
                all(v in "0123456789abcdef" for v in digest),"bad evidence digest")
        if self.db.execute("SELECT 1 FROM events WHERE intent_id=? AND event=? AND evidence_digest=?",
                           (ident,event,digest)).fetchone():
            return False
        last=self.db.execute("SELECT seq,event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous=last[1] if last else "0"*64
        # Single writer transaction makes global hash ordering deterministic.
        seq=self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM events").fetchone()[0]
        event_hash=_hash_event(previous,seq,ident,event,digest)
        self.db.execute("INSERT INTO events(seq,intent_id,event,evidence_digest,previous_hash,event_hash) VALUES(?,?,?,?,?,?)",
                        (seq,ident,event,digest,previous,event_hash))
        return True

    def register_queued(self,*,chain_id,ghost,parent_tx,ledger,rows,deal_id,buyer,seller):
        """Freeze exactly reconciled onchain-intent rows; lock out blind sends."""
        require(type(chain_id) is int and chain_id==4221,"wrong chain ID")
        ghost=address(ghost)
        require(type(parent_tx) is str and RE_TX.fullmatch(parent_tx) is not None,
                "invalid parent GenLayer transaction id")
        report=reconcile_queued_intents(ledger,rows,deal_id=deal_id,buyer=buyer,seller=seller)
        require(report["delivery"]=="UNVERIFIED" and report["retry_authorized"] is False,
                "ledger does not support a safe transfer conclusion")
        if not rows:
            return report
        batch=[]
        for row in rows:
            snapshot={
                "schema":SCHEMA,"chain_id":chain_id,"ghost":ghost,
                "parent_tx":parent_tx.lower(),"intent":row,
            }
            raw=canonical(snapshot)
            ident=row["intent_id_sha256"]
            batch.append((ident,_sha(raw),raw.decode("ascii")))
        def commit():
            for ident,digest,raw in batch:
                existing=self.db.execute(
                    "SELECT snapshot_hash,snapshot_json FROM intents WHERE intent_id=?",
                    (ident,)).fetchone()
                if existing and existing!=(digest,raw):
                    raise EvidenceRejected("conflicting immutable child intent snapshot")
                if not existing:
                    self.db.execute("INSERT INTO intents VALUES(?,?,?,?,?,?,?)",
                                    (ident,digest,raw,chain_id,ghost,parent_tx.lower(),STATUS))
                self._append(ident,"QUEUED",digest)
            return report
        return self._atomic(commit)

    def _fetch(self,ident):
        require(type(ident) is str and len(ident)==64 and
                all(c in "0123456789abcdef" for c in ident),"bad intent id")
        row=self.db.execute("SELECT snapshot_json,state FROM intents WHERE intent_id=?",
                            (ident,)).fetchone()
        require(row is not None,"unregistered intent: no transfer classification")
        require(row[1]==STATUS,"unexpected incident status")
        data=json.loads(row[0])
        require(data["intent"]["intent_id_sha256"]==ident,"snapshot altered")
        return data

    def report_child_failure(self,ident,*,child_tx,reporter_notes_digest):
        """A reported failure is NOT proof of refunded tokens or safe retry."""
        require(type(child_tx) is str and RE_TX.fullmatch(child_tx) is not None,
                "child transaction ID must be a full hash")
        require(type(reporter_notes_digest) is str and len(reporter_notes_digest)==64 and
                all(c in "0123456789abcdef" for c in reporter_notes_digest),
                "raw incident notes are not persisted")
        def commit():
            data=self._fetch(ident)
            evidence={"child_id_UNATTESTED":child_tx.lower(),
                      "report_digest_UNVERIFIED":reporter_notes_digest}
            self._append(ident,"CHILD_FAILURE_REPORTED",_sha(canonical(evidence)))
            return self._decision(data)
        return self._atomic(commit)

    def record_ghost_observation(self,ident,*,tx_hash,tx,receipt,trace,before_wei,after_wei,
                                 block_hash,confirmations):
        """Require structured Ghost CALL evidence, but NEVER bind to intent."""
        snapshot=self._fetch(ident)
        observation=assess_evm_transfer_observation(
            snapshot["intent"],ghost=snapshot["ghost"],tx_hash=tx_hash,
            tx=tx,receipt=receipt,trace=trace,before_wei=before_wei,
            after_wei=after_wei,block_hash=block_hash,confirmations=confirmations,
        )
        require(observation["delivery"]=="UNVERIFIED_FOR_SPECIFIC_INTENT",
                "unsupported child-attribution claim")
        def commit():
            live=self._fetch(ident)
            require(live==snapshot,"immutable snapshot altered concurrently")
            # Never store unredacted trace/raw return data or user secrets.
            evidence={"observation":observation["observation"],
                      "tx_hash":observation["transfer_tx_hash"],
                      "recipient":observation["recipient"],
                      "amount_wei":observation["amount_wei"]}
            self._append(ident,"EVM_CALL_UNATTRIBUTED",_sha(canonical(evidence)))
            return self._decision(live)
        return self._atomic(commit)

    def _decision(self,snapshot):
        return {
            "intent_id_sha256":snapshot["intent"]["intent_id_sha256"],
            "state":STATUS,
            "child_value_credited_to_recipient":"UNPROVEN",
            "native_value_recovered_by_ghost":"UNPROVEN",
            "automatic_retry_allowed":False,
            "manual_resend_allowed":False,
            "recommendation":"STOP_SENDS_AND_OBTAIN_TRUSTED_CHILD_BINDING",
        }

    def decision(self,ident):
        return self._decision(self._fetch(ident))

    def authorize_retry(self,*args,**kwargs):
        raise RecoveryForbidden("no proof of fund recovery or exactly-once delivery; retry forbidden")

    def authorize_rescue(self,*args,**kwargs):
        raise RecoveryForbidden("no authenticated recovery primitive for external GEN transfer")

    def audit(self):
        """Detect accidental corruption of local journal only, NOT remote fraud."""
        previous="0"*64
        expected_seq=1
        for seq,ident,evt,digest,prev,actual in self.db.execute(
                "SELECT seq,intent_id,event,evidence_digest,previous_hash,event_hash FROM events ORDER BY seq"):
            require(evt in EVENTS,"unknown event in local audit log")
            require(seq==expected_seq and prev==previous,"broken local incident chain")
            require(actual==_hash_event(previous,seq,ident,evt,digest),
                    "tampered local incident event hash")
            require(self.db.execute("SELECT 1 FROM intents WHERE intent_id=?",
                                    (ident,)).fetchone() is not None,
                    "orphan incident event")
            expected_seq+=1
            previous=actual
        return {"events":expected_seq-1,"head_sha256":previous,
                "local_integrity":True,"chain_attestation":False,
                "value_recovery_attested":False}

"""Offline incident log CLI. Never signs, broadcasts, retries or recovers GEN.

Inputs MUST be exported from separately independently verified public contract
read-only getters; a JSON file alone is not authenticated chain data.
"""
import argparse
import json
import sys
from pathlib import Path

from child_delivery_recovery_guard import ChildIncidentJournal,RecoveryForbidden
from phase8_release_gate import EvidenceRejected

def main(argv=None):
    p=argparse.ArgumentParser(description="Bradbury child transfer no-retry guard; LOCAL DATA ONLY")
    p.add_argument("--database",required=True,help="local durable SQLite incident journal path")
    cmd=p.add_subparsers(dest="command",required=True)
    en=cmd.add_parser("register",help="record audited onchain intent export, no transfer")
    en.add_argument("--input",required=True,help="JSON exported read-only from verified source")
    st=cmd.add_parser("status",help="unverified incident state only")
    st.add_argument("--intent",required=True)
    ff=cmd.add_parser("reported-failure",help="report unverified child failure, no rescue")
    ff.add_argument("--intent",required=True)
    ff.add_argument("--child-tx",required=True)
    ff.add_argument("--evidence-sha256",required=True)
    cmd.add_parser("audit",help="local accidental-corruption check only")
    args=p.parse_args(argv)
    try:
        with ChildIncidentJournal(args.database) as journal:
            if args.command=="register":
                data=json.loads(Path(args.input).read_text(encoding="utf-8"))
                if type(data) is not dict or set(data)!={
                    "chain_id","ghost","parent_genlayer_tx","ledger","rows","deal_id","buyer","seller"
                }:
                    raise EvidenceRejected("unexpected incident export schema")
                result=journal.register_queued(
                    chain_id=data["chain_id"],ghost=data["ghost"],
                    parent_tx=data["parent_genlayer_tx"],ledger=data["ledger"],
                    rows=data["rows"],deal_id=data["deal_id"],
                    buyer=data["buyer"],seller=data["seller"])
            elif args.command=="reported-failure":
                result=journal.report_child_failure(
                    args.intent,child_tx=args.child_tx,
                    reporter_notes_digest=args.evidence_sha256)
            elif args.command=="status":
                result=journal.decision(args.intent)
            else:
                result=journal.audit()
            print(json.dumps(result,sort_keys=True))
            print("SE_CHILD_VALUE_RECOVERY_UNVERIFIED_NO_RETRY")
            return 0
    except (EvidenceRejected,ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
        print("SE_CHILD_VALUE_RECOVERY_BLOCKED",type(exc).__name__)
        return 2

if __name__=="__main__":
    import sqlite3
    sys.exit(main())

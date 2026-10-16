"""Offline operator CLI never signs or sends. No actual wallets or GEN."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))

from child_delivery_incident_cli import main
from test_phase8_release_gate import BUYER,SELLER,GHOST,intent,ledger

def sample():
    return {"chain_id":4221,"ghost":GHOST,"parent_genlayer_tx":"0x"+"11"*32,
            "ledger":ledger(),"rows":[intent(0,"PAYOUT",10),intent(1,"REFUND",15)],
            "deal_id":0,"buyer":BUYER,"seller":SELLER}

def test_operator_cli_offline_roundtrip(tmp_path,capsys):
    db=tmp_path/"incidents.sqlite"
    data=tmp_path/"public-read-only-export.json"
    rows=sample()
    data.write_text(json.dumps(rows),encoding="utf-8")
    assert main(["--database",str(db),"register","--input",str(data)])==0
    ident=rows["rows"][0]["intent_id_sha256"]
    assert main(["--database",str(db),"status","--intent",ident])==0
    assert "UNPROVEN" in capsys.readouterr().out
    assert main(["--database",str(db),"audit"])==0
    assert main(["--database",str(db),"reported-failure",
                 "--intent",ident,"--child-tx","0x"+"22"*32,
                 "--evidence-sha256","33"*32])==0
    assert main(["--database",str(db),"status","--intent",ident])==0
    assert "False" not in capsys.readouterr().out  # JSON uses false
    assert main(["--database",str(db),"audit"])==0

def test_operator_cli_fake_credit_flag_rejected(tmp_path,capsys):
    db=tmp_path/"guard.sqlite"
    payload=sample()
    payload["delivered"]=True
    js=tmp_path/"fake.json"
    js.write_text(json.dumps(payload),encoding="utf-8")
    assert main(["--database",str(db),"register","--input",str(js)])==2
    assert "SE_CHILD_VALUE_RECOVERY_BLOCKED" in capsys.readouterr().out

def test_operator_cli_missing_intent_and_invalid_child_hash_fail(tmp_path):
    db=tmp_path/"guard.sqlite"
    assert main(["--database",str(db),"status","--intent","not-a-hash"])==2
    assert main(["--database",str(db),"reported-failure",
                "--intent","0x123","--child-tx","0x4",
                "--evidence-sha256","aa"*32])==2

def test_cli_is_not_a_live_payment_gateway():
    src=(Path(__file__).resolve().parents[1]/"tools/child_delivery_incident_cli.py").read_text()
    assert "eth_sendRawTransaction" not in src
    assert "eth_sendTransaction" not in src
    assert ".transact(" not in src
    assert "authorize_retry(" not in src
    assert "authorize_rescue(" not in src

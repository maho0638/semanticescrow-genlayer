"""Phase 9 scoped release-review evidence packet: fail-closed adversarial tests.

These are OFFLINE tests. They cannot certify production funds or a lost
original Phase 9 specification.
"""
import copy
import json
from pathlib import Path

import pytest
from tools import phase9_release_packet as p

ROOT=Path(__file__).resolve().parents[1]
COMMIT="a"*40
PHASE7="560d1d00bdd81df36da708ede49096fbeb80ebd6"

def signed():
    return p.make_packet(ROOT,COMMIT,parent_branch_sha=PHASE7)

def resign(packet):
    packet["artifact_sha256"]=p.sha(p.canonical({
        k:v for k,v in packet.items() if k!="artifact_sha256"
    }))
    return packet

def test_real_source_is_exactly_sized_and_v0216_pinned():
    fingerprints=p.get_local_source_fingerprints(ROOT)
    assert fingerprints["sha256"]==p.SOURCE_SHA
    assert fingerprints["source_bytes"]==15738
    assert fingerprints["genvm_version"]=="v0.2.16"
    assert fingerprints["py_genlayer_dependency"]==p.RUNNER_PIN
    assert len(fingerprints["repository_file_sha256"])==5

def test_final_handoff_passes_structural_validation_but_never_allows_release():
    packet=signed()
    assert p.verify_packet(packet,ROOT) is True
    assert packet["release_review"]["status"]=="BLOCKED"
    assert packet["release_review"]["escrow_real_money_authorized"] is False
    assert packet["release_review"]["automatic_child_resend_authorized"] is False
    assert packet["release_review"]["production_deployment_authorized"] is False
    assert len(packet["release_review"]["missing_attestations"])==8

def test_repeatable_checksums_no_timestamps_or_random_keys():
    assert signed()==signed()

def test_cli_creates_parseable_handoff_but_does_not_deploy(tmp_path):
    dst=tmp_path/"release-packet.json"
    assert p.main(["--repo-root",str(ROOT),"--commit",COMMIT,"--output",str(dst)])==0
    packet=json.loads(dst.read_text())
    assert p.verify_packet(packet,ROOT)
    assert packet["release_review"]["status"]=="BLOCKED"

@pytest.mark.parametrize("bad",["","notasha","A"*40,"f"*39,"a"*41,"../evil"])
def test_bad_commit_rejected(bad):
    with pytest.raises(p.PacketRejected):
        p.make_packet(ROOT,bad,parent_branch_sha=PHASE7)
    with pytest.raises(p.PacketRejected):
        p.make_packet(ROOT,COMMIT,parent_branch_sha=bad)

@pytest.mark.parametrize("path",[
    p.CONTRACT_REL,"tools/phase7_existing_bradbury.py",
    "tools/phase7_legacy_receipts.py","tools/phase8_release_gate.py",
    "tools/phase8_ghost_public_probe.py","tools/phase7_schema_compat.py"
])
def test_modification_or_missing_verification_file_rejected(tmp_path,path):
    # Copy only the pin-scoped files; do not need dependencies or network.
    paths=[p.CONTRACT_REL,"tools/phase7_schema_compat.py",*p.TOOLS_REQUIRED]
    for name in paths:
        output=tmp_path/name
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes((ROOT/name).read_bytes())
    item=tmp_path/path
    item.write_bytes(item.read_bytes()+b"\n# malicious drift\n")
    with pytest.raises(p.PacketRejected):
        p.verify_packet(signed(),tmp_path)

@pytest.mark.parametrize("kind",[
    "release_status","production_deployment","escrow_authorization",
    "refund_credited","resend","child_bound","remove_blocker",
    "extra_field","wrong_branch","wrong_chain","different_ghost",
    "fake_funding_receipt","changed_signed_source","change_runner_pin",
    "fake_ci","missing_limitation","provenance_branch","remove_file_digest",
])
def test_forged_signed_packet_even_with_fresh_checksum_rejected(kind):
    packet=signed()
    review=packet["release_review"]
    if kind=="release_status":review["status"]="READY"
    elif kind=="production_deployment":review["production_deployment_authorized"]=True
    elif kind=="escrow_authorization":review["escrow_real_money_authorized"]=True
    elif kind=="refund_credited":review["phase7_live_refund_credited"]=True
    elif kind=="resend":review["automatic_child_resend_authorized"]=True
    elif kind=="child_bound":review["authenticated_intent_child_link"]=True
    elif kind=="remove_blocker":review["missing_attestations"].pop()
    elif kind=="extra_field":review["ready"]=True
    elif kind=="wrong_branch":packet["audit_branch"]="main"
    elif kind=="wrong_chain":packet["network"]["chain_id"]=1
    elif kind=="different_ghost":packet["network"]["verified_deploy_ghost"]="0x"+"11"*20
    elif kind=="fake_funding_receipt":packet["network"]["beneficiary_credited"]=True
    elif kind=="changed_signed_source":packet["contract"]["sha256"]="0"*64
    elif kind=="change_runner_pin":packet["contract"]["py_genlayer_dependency"]="x"*52
    elif kind=="fake_ci":packet["regression_evidence"]["phase8_tests"]="http://example.com"
    elif kind=="missing_limitation":packet["limitations"]["original_phase9_spec_not_found"]=False
    elif kind=="provenance_branch":packet["project"]="someone/other"
    elif kind=="remove_file_digest":del packet["contract"]["repository_file_sha256"][p.CONTRACT_REL]
    with pytest.raises(p.PacketRejected):
        p.verify_packet(resign(packet),ROOT)

def test_checksum_corruption_and_extra_top_level_field_rejected():
    packet=signed()
    packet["artifact_sha256"]="f"*64
    with pytest.raises(p.PacketRejected):
        p.verify_packet(packet,ROOT)
    packet=signed()
    packet["security_audit_passed"]=True
    with pytest.raises(p.PacketRejected):
        p.verify_packet(resign(packet),ROOT)

@pytest.mark.parametrize("value",[None,[],1,True,"\ud800"])
def test_malformed_artifact_is_not_a_valid_release(value):
    packet=signed()
    packet["release_review"]=value
    with pytest.raises((p.PacketRejected,TypeError,UnicodeError,ValueError)):
        p.verify_packet(resign(packet),ROOT)

def test_original_nine_stage_spec_is_explicitly_unverified():
    packet=signed()
    assert packet["limitations"]["original_phase9_spec_not_found"] is True
    assert "ORIGINAL_PHASE9_REQUIREMENTS_UNRECOVERED" in packet["release_review"]["missing_attestations"]

def test_document_requires_review_not_fake_signatures():
    packet=signed()
    assert packet["limitations"]["artifact_sha256_is_not_a_digital_signature"] is True
    assert packet["limitations"]["offline_CI_is_not_independent_audit"] is True
    assert packet["limitations"]["archive_sha_is_published_asset_metadata_not_validator_binary_attestation"] is True

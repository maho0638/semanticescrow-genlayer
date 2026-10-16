"""Deterministic, OFFLINE release-audit handoff for SemanticEscrow.

Not the lost original nine-stage roadmap's Phase 9 definition.
No keys, network access, chain writes, approvals, Portal submissions, PRs,
token transfers or deceptive "release ready" statuses.

A CI artifact checksum detects accidental artifact modifications, not an
authenticated signature. An outside auditor must verify the GitHub source,
runner, live Bradbury settlement and independent security review separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_SHA="ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70"
RUNNER_PIN="1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"
GENVM_VERSION="v0.2.16"
GENVM_OFFICIAL_ARCHIVE_SHA256="4f0b358ec98ec148be9b95cdfb0f0e1a6cbe64da0194fdfac3fffc6f5d1d93e2"
BRADBURY_CHAIN=4221
BRADBURY_GHOST="0x73dc7ee6f7406b01ef7d607f8d1a48a780afa12a"
DEPLOY_GENLAYER_TX="0x1ac72cb02a02cdf8709615b8aeed51610128dddd1a87128b58623aab73220c43"
DEPLOY_EVM_TX="0x2bddc2919cde1aee0cc751e3735daa7e0ecc9fbcbab91b2bc28dd6d698455bf8"
EXPECTED_CONTRACT_BYTES=15738

# These are required missing attestations, not booleans supplied by a user.
# No automatic client script can waive them.
BLOCKERS=(
    "ORIGINAL_PHASE9_REQUIREMENTS_UNRECOVERED",
    "BRADBURY_SETTLEMENT_CHILD_DELIVERY_NOT_INDEPENDENTLY_PROVEN",
    "INTENT_TO_CHILD_TRANSACTION_LINK_NOT_PROVEN",
    "FAILED_CHILD_RETRY_OR_RECOVERY_NOT_PROTOCOL_AUDITED",
    "NETWORK_EGRESS_DNS_REDIRECT_SSRF_NOT_PROVEN",
    "REAL_PUBLISHER_AND_INDEPENDENT_MODEL_REVIEW_NOT_PROVEN",
    "EXTERNAL_SECURITY_AUDIT_NOT_PERFORMED",
    "OWNER_PRODUCTION_RELEASE_APPROVAL_NOT_GIVEN",
)
CONTRACT_REL="contracts/semantic_escrow.py"
TOOLS_REQUIRED=(
    "tools/phase7_existing_bradbury.py",
    "tools/phase7_legacy_receipts.py",
    "tools/phase8_release_gate.py",
    "tools/phase8_ghost_public_probe.py",
)
SCHEMA="SemanticEscrow.audit.handoff.v1"
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
BRANCH="audit/phase9-evidence-release-20261016"

class PacketRejected(ValueError):
    pass

def require(flag, reason):
    if not flag:
        raise PacketRejected(reason)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def _load_text(root, relative):
    path=root.joinpath(*relative.split("/"))
    require(path.is_file() and not path.is_symlink(),"missing/symlinked audit file: "+relative)
    return path.read_bytes()

def get_local_source_fingerprints(root):
    root=Path(root).resolve(strict=True)
    raw=_load_text(root,CONTRACT_REL)
    require(sha(raw)==SOURCE_SHA,"contract changed since Bradbury deploy; source pin mismatch")
    require(len(raw)==EXPECTED_CONTRACT_BYTES,"unexpected signed source length")
    require(raw.startswith(("# "+GENVM_VERSION+"\n# { \"Depends\": \"py-genlayer:"+RUNNER_PIN+"\" }\n").encode("ascii")),
            "GenVM version and runner pin mismatch")
    # Force the SHA constant imported by the Phase7 schema binder to be equal.
    binder=_load_text(root,"tools/phase7_schema_compat.py").decode("utf-8")
    require(re.search(r"^SOURCE_SHA256\s*=\s*['\"]"+SOURCE_SHA+r"['\"]",binder,re.M) is not None,
            "schema compiler source-pin mismatch")
    files={CONTRACT_REL:SOURCE_SHA,"tools/phase7_schema_compat.py":sha(_load_text(root,"tools/phase7_schema_compat.py"))}
    for relative in TOOLS_REQUIRED:
        files[relative]=sha(_load_text(root,relative))
    return {
        "sha256":SOURCE_SHA,"source_bytes":EXPECTED_CONTRACT_BYTES,
        "genvm_version":GENVM_VERSION,"py_genlayer_dependency":RUNNER_PIN,
        "official_release_archive_sha256":GENVM_OFFICIAL_ARCHIVE_SHA256,
        "repository_file_sha256":files,
    }

def make_packet(root, commit_sha, *, parent_branch_sha):
    require(type(commit_sha) is str and SHA_RE.fullmatch(commit_sha) is not None,
            "unverified audit commit format")
    require(type(parent_branch_sha) is str and SHA_RE.fullmatch(parent_branch_sha) is not None,
            "invalid Phase7 pinned parent SHA format")
    fp=get_local_source_fingerprints(root)
    packet={
        "schema":SCHEMA,
        "project":"maho0638/semanticescrow-genlayer",
        "audit_branch":BRANCH,
        "audit_commit":commit_sha,
        "origin_phase7_commit":parent_branch_sha,
        "contract":fp,
        "network":{
            "chain_id":BRADBURY_CHAIN,
            "verified_deploy_ghost":BRADBURY_GHOST,
            "verified_deploy_evm_tx":DEPLOY_EVM_TX,
            "verified_deploy_genlayer_tx":DEPLOY_GENLAYER_TX,
            "note":"Deployment evidence is NOT a refund/child-transfer receipt.",
        },
        "regression_evidence":{
            "phase7_tests":"https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38878413843",
            "phase8_tests":"https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38882846009",
            "status":"HISTORICAL_PASS_REFERENCES_VERIFY_IN_GITHUB",
        },
        "release_review":{
            "status":"BLOCKED",
            "missing_attestations":list(BLOCKERS),
            "phase7_live_refund_credited":False,
            "authenticated_intent_child_link":False,
            "automatic_child_resend_authorized":False,
            "escrow_real_money_authorized":False,
            "production_deployment_authorized":False,
            "pr_or_merge_authorized":False,
        },
        "limitations":{
            "archive_sha_is_published_asset_metadata_not_validator_binary_attestation":True,
            "offline_CI_is_not_independent_audit":True,
            "artifact_sha256_is_not_a_digital_signature":True,
            "original_phase9_spec_not_found":True,
        },
    }
    packet["artifact_sha256"]=sha(canonical(packet))
    return packet

def verify_packet(packet,root):
    """Reject fabricated success, altered fingerprints or unsafely changed schema."""
    require(type(packet) is dict and set(packet)=={
        "schema","project","audit_branch","audit_commit","origin_phase7_commit",
        "contract","network","regression_evidence","release_review","limitations",
        "artifact_sha256",
    },"unknown/missing packet keys")
    claimed=packet["artifact_sha256"]
    require(type(claimed) is str and SHA_RE.fullmatch(claimed) is not None,
            "invalid packet checksum")
    copy={k:v for k,v in packet.items() if k!="artifact_sha256"}
    require(sha(canonical(copy))==claimed,"packet content checksum mismatch")
    require(packet["schema"]==SCHEMA and packet["project"]=="maho0638/semanticescrow-genlayer",
            "wrong project or packet schema")
    require(packet["audit_branch"]==BRANCH,"unexpected branch")
    require(type(packet["audit_commit"]) is str and SHA_RE.fullmatch(packet["audit_commit"]) is not None,
            "bad audit commit")
    require(type(packet["origin_phase7_commit"]) is str and
            SHA_RE.fullmatch(packet["origin_phase7_commit"]) is not None,"bad phase7 parent")
    require(packet["contract"]==get_local_source_fingerprints(root),
            "contract/tool fingerprints inconsistent with working tree")
    require(packet["network"]=={
        "chain_id":BRADBURY_CHAIN,"verified_deploy_ghost":BRADBURY_GHOST,
        "verified_deploy_evm_tx":DEPLOY_EVM_TX,
        "verified_deploy_genlayer_tx":DEPLOY_GENLAYER_TX,
        "note":"Deployment evidence is NOT a refund/child-transfer receipt.",
    },"untrusted network claims")
    require(packet["regression_evidence"]=={
        "phase7_tests":"https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38878413843",
        "phase8_tests":"https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38882846009",
        "status":"HISTORICAL_PASS_REFERENCES_VERIFY_IN_GITHUB",
    },"test run provenance unexpected")
    require(packet["release_review"]=={
        "status":"BLOCKED","missing_attestations":list(BLOCKERS),
        "phase7_live_refund_credited":False,"authenticated_intent_child_link":False,
        "automatic_child_resend_authorized":False,"escrow_real_money_authorized":False,
        "production_deployment_authorized":False,"pr_or_merge_authorized":False,
    },"release permission forgery")
    require(packet["limitations"]=={
        "archive_sha_is_published_asset_metadata_not_validator_binary_attestation":True,
        "offline_CI_is_not_independent_audit":True,
        "artifact_sha256_is_not_a_digital_signature":True,
        "original_phase9_spec_not_found":True,
    },"missing evidence limitations")
    return True

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline NO-GO handoff, never deploys")
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--commit",required=True,help="Git commit SHA to label artifact; not a Git signature")
    parser.add_argument("--phase7-commit",default="560d1d00bdd81df36da708ede49096fbeb80ebd6")
    parser.add_argument("--output",required=True)
    args=parser.parse_args(argv)
    try:
        packet=make_packet(args.repo_root,args.commit,
                           parent_branch_sha=args.phase7_commit)
        verify_packet(packet,args.repo_root)
        path=Path(args.output)
        require(not path.is_symlink(),"output cannot be a symlink")
        require(path.parent.is_dir(),"output parent must already exist")
        path.write_bytes(canonical(packet)+b"\n")
    except (PacketRejected,ValueError,OSError) as e:
        print("SEMANTICESCROW_RELEASE_PACKET_FAILED",type(e).__name__,str(e)[:100])
        return 2
    print("SEMANTICESCROW_RELEASE_PACKET_CHECKED_NOT_READY",
          packet["artifact_sha256"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())

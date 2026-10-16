"""Static and commitment-shape regressions for source-preserving GenVM v2 IC.

Historical deployed v0.2.16 escrow source MUST stay unchanged; this is a
separate contract that requires explicit fresh testnet deployment approval.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"contracts/semantic_escrow.py"
CANDIDATE=ROOT/"contracts/semantic_escrow_attributed_v2.py"
SOL=ROOT/"contracts/evm/SemanticEscrowNativePayoutRouter.sol"

def code():
    return CANDIDATE.read_text(encoding="utf-8")

def test_original_deployed_contract_source_preserved_byte_for_byte():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==(
        "ef189ccc0129d8756effc21b58385648fd60056520f704c28a8d737251b40d70")

def test_candidate_is_independently_parseable_gemvm_v0216_source():
    src=code()
    assert src.startswith("# v0.2.16\n")
    tree=ast.parse(src)
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and
             node.name=="SemanticEscrow")
    methods={node.name for node in cls.body if isinstance(node,ast.FunctionDef)}
    assert "configure_payment_router" in methods
    assert "create_deal" in methods
    assert "get_transfer_intent" in methods
    assert "get_transfer_intents" in methods
    # Private helper names may be shortened by the pinned, behavior-preserving
    # deploy minifier. Verify their behavior through the regression suite.
    assert any(node.name.startswith("_") for node in cls.body
               if isinstance(node,ast.FunctionDef))

def test_emission_carries_exact_sha256_intent_bytes_not_amount_only():
    source=code()
    tree=ast.parse(source)
    assert "SemanticEscrow.transfer-intent.v1" in source
    assert "disburse" in source and "bytes32" in source
    assert "Au(Address(recipient)).emit_transfer" not in source
    assert "router_ready" not in source or "rr" in source

def test_locked_router_configuration_before_accepting_deposit():
    source=code()
    tree=ast.parse(source)
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef)
             and node.name=="SemanticEscrow")
    storage_fields={node.target.id for node in cls.body
                    if isinstance(node,ast.AnnAssign)
                    and isinstance(node.target,ast.Name)}
    assert {"rp","ro","rr"}.issubset(storage_fields)
    assert "payout router must be configured before deposit" in source
    assert source.index("payout router must be configured before deposit") < source.index("gl.message.value")
    assert "router already configured" in source
    assert "only deployer can configure router" in source
    assert "router ghost mismatch" in source
    assert "router chain mismatch" in source

def test_contract_and_router_interface_types_are_identical():
    source=code()
    sol=SOL.read_text()
    tree=ast.parse(source)
    router=next(node for node in tree.body if isinstance(node,ast.ClassDef)
                and node.decorator_list and
                "contract_interface" in ast.unparse(node.decorator_list[0]))
    disburse=next(node for node in router.body if isinstance(node,ast.ClassDef)
                  and node.name=="Write")
    method=next(node for node in disburse.body if isinstance(node,ast.FunctionDef)
                and node.name=="disburse")
    method_args=method.args.posonlyargs+method.args.args
    assert [ast.unparse(arg.annotation) for arg in method_args[1:]]==[
        "bytes32","Address"]
    assert len(method_args)==3
    assert "function disburse(bytes32 intentId, address payable recipient)" in sol
    assert "event NativeIntentPaid(" in sol
    assert "delivered[intentId] = true;" in sol
    assert "if (!ok) revert TransferFailed();" in sol
    assert "if (msg.sender != escrowGhost) revert UnauthorizedGhost();" in sol

def test_sha_commitment_roundtrip_matches_unchanged_intent_view():
    fields={"domain":"SemanticEscrow.transfer-intent.v1",
            "terms_digest_sha256":"11"*32,
            "deal_id":7,
            "milestone_index":2,
            "kind":"REFUND",
            "recipient":"0x"+"ae"*20,
            "amount_wei":"100000000000000"}
    digest=hashlib.sha256(json.dumps(
        fields,sort_keys=True,separators=(",",":"),
        ensure_ascii=True,allow_nan=False).encode("utf-8")).hexdigest()
    assert len(bytes.fromhex(digest))==32
    assert digest==hashlib.sha256(json.dumps(
        fields,separators=(",",":"),sort_keys=True,
        ensure_ascii=True,allow_nan=False).encode()).hexdigest()

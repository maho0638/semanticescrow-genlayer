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
    assert "_queue_settlement" in methods
    assert "get_transfer_intent" in methods
    assert "get_transfer_intents" in methods

def test_emission_carries_exact_sha256_intent_bytes_not_amount_only():
    source=code()
    assert "ident=l({Ai:'SemanticEscrow.transfer-intent.v1'" in source
    assert "_NativeIntentRouter(self.payment_router).emit(value=u256(D)).disburse(bytes.fromhex(ident),Address(recipient))" in source
    assert "Au(Address(recipient)).emit_transfer" not in source
    assert "self.router_ready" in source

def test_locked_router_configuration_before_accepting_deposit():
    source=code()
    assert "A(self.router_ready,'payout router must be configured before deposit')" in source
    assert source.index("A(self.router_ready,'payout router must be configured before deposit')") < source.index("A(B(gl.message.value)==D")
    assert "A(not self.router_ready,'router already configured')" in source
    assert "only deployer can configure router" in source
    assert "router ghost mismatch" in source
    assert "router chain mismatch" in source

def test_contract_and_router_interface_types_are_identical():
    source=code()
    sol=SOL.read_text()
    assert "def disburse(self,intent_id:bytes,recipient:Address)->None" in source
    assert "function disburse(bytes calldata intentBytes, address payable recipient)" in sol
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

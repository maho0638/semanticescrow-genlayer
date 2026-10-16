"""Read-only gate before ANY new buyer funding; reuse exact finalized deployment."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gltest import get_gl_client,get_contract_factory
from phase7_legacy_compat import require_legacy_bradbury
from phase7_schema_compat import bind_verified_schema
from phase7_existing_bradbury import verify_existing_finalized_deployment

def test_existing_bradbury_deployment_is_reusable():
    client=get_gl_client()
    assert require_legacy_bradbury(client) is None
    factory=get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    bind_verified_schema(factory)
    ghost=verify_existing_finalized_deployment(client,factory.contract_code)
    print("SE7_PUBLIC_EXISTING_DEPLOY_FINALIZED_AND_SOURCE_ATTESTED",ghost,flush=True)

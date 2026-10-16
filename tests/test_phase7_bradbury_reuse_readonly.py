"""Read-only gate before ANY new buyer funding; reuse exact finalized deployment."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gltest import get_gl_client,get_contract_factory,get_default_account
from phase7_legacy_compat import require_legacy_bradbury
from phase7_schema_compat import bind_verified_schema
from phase7_existing_bradbury import verify_existing_finalized_deployment
from phase7_legacy_method_dispatch import install_bradbury_v0216_dispatch
from phase7_bradbury_read_envelope import install_bradbury_finalized_read_adapter
import json

def test_existing_bradbury_deployment_is_reusable():
    client=get_gl_client()
    assert require_legacy_bradbury(client) is None
    factory=get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    bind_verified_schema(factory)
    ghost=verify_existing_finalized_deployment(client,factory.contract_code)
    install_bradbury_v0216_dispatch(client)
    install_bradbury_finalized_read_adapter(client)
    # Zero-GEN proof that the very SDK path which failed at live step 98
    # can actually read the finalized contract state before any funding.
    reader=factory.build_contract(contract_address=ghost,account=get_default_account())
    n=int(reader.deal_count().call())
    assert n>=0
    if n:
        ledger=json.loads(reader.get_ledger(args=[0]).call())
        assert set(ledger)=={"initial_deposit","remaining_locked","payout_queued_total","refund_queued_total"}
        assert int(ledger["initial_deposit"])>=0 and int(ledger["remaining_locked"])>=0
        print("SE7_PUBLIC_EXISTING_FINALIZED_SDK_LEDGER_READ_PASS",n,flush=True)
    else:
        print("SE7_PUBLIC_EXISTING_FINALIZED_SDK_EMPTY_LEDGER_READ_PASS",flush=True)
    print("SE7_PUBLIC_EXISTING_DEPLOY_FINALIZED_AND_SOURCE_ATTESTED",ghost,flush=True)

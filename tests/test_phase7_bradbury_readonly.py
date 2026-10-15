"""Read-only Bradbury GenLayer SDK connectivity gate. Never signs or spends GEN."""
import os
from pathlib import Path
from eth_account import Account
from gltest import get_gl_client, get_default_account, get_accounts


def test_bradbury_sdk_can_access_rpc_and_configured_ephemeral_accounts():
    client = get_gl_client()
    response = client.provider.make_request("eth_chainId", [])
    assert not response.get("error"), "Bradbury SDK provider returned RPC error"
    assert int(response["result"], 16) == 4221
    assert get_default_account().address.lower() == Account.from_key(
        os.environ["ACCOUNT_PRIVATE_KEY_1"]).address.lower()
    known = {a.address.lower() for a in get_accounts()}
    assert Account.from_key(os.environ["ACCOUNT_PRIVATE_KEY_2"]).address.lower() in known
    print("SE7_PUBLIC_SDK_READONLY_BrADBURY_OK", flush=True)
    # This must be checked BEFORE requesting test GEN. The previous version
    # requested funding after checking only chain ID and account registration.
    # This deployed Bradbury version uses the verified legacy ABI; the newer
    # FeeManager price policy API is unavailable on that deployed contract.
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from phase7_legacy_compat import require_legacy_bradbury
    print("SE7_PUBLIC_LEGACY_PROTOCOL_GATE_BEGIN",flush=True)
    assert require_legacy_bradbury(client) is None
    print("SE7_PUBLIC_LEGACY_PROTOCOL_GATE_PASS",flush=True)

    # Ensure this release is ABI-compatible with the public network before
    # putting test GEN in an ephemeral buyer address.
    from pathlib import Path
    from gltest import get_contract_factory
    factory = get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    schema = factory._get_schema_with_fallback()
    assert schema is not None, "GenVM schema unavailable before funding"
    print("SE7_PUBLIC_CONTRACT_SCHEMA_CHECK_PASS",flush=True)


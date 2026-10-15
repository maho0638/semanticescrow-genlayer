"""Read-only Bradbury GenLayer SDK connectivity gate. Never signs or spends GEN."""
import os
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
    print("SE7_PUBLIC_FEE_QUOTE_CHECK_BEGIN", flush=True)
    fee = client.estimate_transaction_fees({
        "leaderTimeunitsAllocation": 100,
        "validatorTimeunitsAllocation": 200,
        "executionBudgetPerRound": 10**15,
        "totalMessageFees": 10**15,
        "appealRounds": 0,
        "rotations": [3],
    })
    if isinstance(fee,dict):
        print("SE7_PUBLIC_FEE_QUOTE_FIELDS",
              ",".join(sorted(map(str,fee.keys()))), flush=True)
    else:
        print("SE7_PUBLIC_FEE_QUOTE_TYPE",type(fee).__name__,flush=True)
    assert isinstance(fee,dict) and "feeValue" in fee and "distribution" in fee, (
        "GenLayer Bradbury fee quote is incompatible with the pinned test client"
    )
    print("SE7_PUBLIC_FEE_QUOTE_CHECK_PASS",flush=True)

    # Ensure this release is ABI-compatible with the public network before
    # putting test GEN in an ephemeral buyer address.
    from pathlib import Path
    from gltest import get_contract_factory
    factory = get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    schema = factory._get_schema_with_fallback()
    assert schema is not None, "GenVM schema unavailable before funding"
    print("SE7_PUBLIC_CONTRACT_SCHEMA_CHECK_PASS",flush=True)


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
    print("SE7_PUBLIC_FEE_QUOTE_CHECK_BEGIN", flush=True)
    import traceback
    def safe_error(stage, error):
        # Only exception class and public module/function locations.
        # NEVER log exception values, request data, RPC payloads, or keys.
        print("SE7_PUBLIC_FAILURE_STAGE", stage, flush=True)
        print("SE7_PUBLIC_FAILURE_CLASS", type(error).__name__, flush=True)
        for frame in traceback.extract_tb(error.__traceback__)[-5:]:
            module = Path(frame.filename).name
            if module in ("client.py", "fees.py", "fee.py", "base.py",
                          "exceptions.py", "provider.py", "rpc.py",
                          "api.py", "transactions.py", "contract.py",
                          "networks.py", "requests.py", "models.py"):
                print("SE7_PUBLIC_FAILURE_SDK_FRAME", module,
                      str(frame.name)[:55], frame.lineno, flush=True)
        response = getattr(error, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            print("SE7_PUBLIC_FAILURE_HTTP_STATUS", status, flush=True)

    try:
        policy = client.get_current_fee_policy()
        print("SE7_PUBLIC_FEE_POLICY_TYPE", type(policy).__name__, flush=True)
        if isinstance(policy, dict):
            print("SE7_PUBLIC_FEE_POLICY_FIELDS",
                  ",".join(sorted(str(k) for k in policy.keys())), flush=True)
    except Exception as exc:
        safe_error("GET_CURRENT_FEE_POLICY", exc)
        raise AssertionError("Bradbury get_current_fee_policy failed") from None

    original_options = {
        "leaderTimeunitsAllocation": 100,
        "validatorTimeunitsAllocation": 200,
        "executionBudgetPerRound": 10**15,
        "totalMessageFees": 10**15,
        "appealRounds": 0,
        "rotations": [3],
    }
    try:
        fee = client.estimate_transaction_fees(original_options)
        if isinstance(fee, dict):
            print("SE7_PUBLIC_FEE_QUOTE_FIELDS",
                  ",".join(sorted(map(str, fee.keys()))), flush=True)
        else:
            print("SE7_PUBLIC_FEE_QUOTE_TYPE", type(fee).__name__, flush=True)
        assert isinstance(fee,dict) and "feeValue" in fee and "distribution" in fee
    except Exception as exc:
        safe_error("EXISTING_FEE_QUOTE", exc)
        # Official minimal preset isolates excessive options from transport
        # failures. This is DIAGNOSTIC ONLY: NEVER fund a child refund with
        # this smaller preset without a separate message budget proof.
        try:
            minimal = client.estimate_transaction_fees({
                "leaderTimeunitsAllocation": 100,
                "validatorTimeunitsAllocation": 200,
                "rotations": [0],
            })
            print("SE7_PUBLIC_MINIMAL_FEE_QUOTE_VALID",
                  bool(isinstance(minimal, dict)
                       and "feeValue" in minimal and "distribution" in minimal),
                  flush=True)
        except Exception as minimal_exc:
            safe_error("MINIMAL_FEE_QUOTE", minimal_exc)
        raise AssertionError("live Bradbury fee quote not ready; DO NOT FUND") from None
    print("SE7_PUBLIC_FEE_QUOTE_CHECK_PASS",flush=True)

    # Ensure this release is ABI-compatible with the public network before
    # putting test GEN in an ephemeral buyer address.
    from pathlib import Path
    from gltest import get_contract_factory
    factory = get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
    schema = factory._get_schema_with_fallback()
    assert schema is not None, "GenVM schema unavailable before funding"
    print("SE7_PUBLIC_CONTRACT_SCHEMA_CHECK_PASS",flush=True)


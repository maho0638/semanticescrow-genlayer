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

"""Offline unit proof pinned genlayer-py serializes the legacy six-input ABI.

No RPC, no wallet funding and no private keys are persisted.
"""
from eth_account import Account
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.transactions.fees import normalize_transaction_fees

def test_native_sdk_default_uses_verified_legacy_selector_without_fee_policy():
    buyer, seller = Account.create(), Account.create()
    client = GenLayerClient(testnet_bradbury, buyer)
    calldata = _encode_add_transaction_data(
        client, buyer, seller.address, 3, "0x1234",
        transaction_fees=normalize_transaction_fees(),
    )
    # This is exactly the selector found on Bradbury's deployed consensus
    # implementation 0x0a2c393975da79505ed930efc55ae4aeb88b0d62.
    assert calldata[:10].lower() == "0xe71d5196"
    assert isinstance(calldata,str)
    assert len(calldata)>300
    assert calldata.endswith("0000000000000000000000000000000000000000000000000000000000000000")

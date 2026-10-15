"""Offline unit proof pinned genlayer-py serializes the legacy six-input ABI.

No RPC, no wallet funding and no private keys are persisted.
"""
from eth_account import Account
from eth_abi import decode
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.transactions.fees import normalize_transaction_fees
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from phase7_legacy_compat import _install_legacy_consensus_abi

def test_native_sdk_default_uses_verified_legacy_selector_without_fee_policy():
    buyer, seller = Account.create(), Account.create()
    client = GenLayerClient(testnet_bradbury, buyer)
    _install_legacy_consensus_abi(client.chain.consensus_main_contract)
    calldata = _encode_add_transaction_data(
        client, buyer, seller.address, 3, "0x1234",
        transaction_fees=normalize_transaction_fees(),
    )
    # This is exactly the selector found on Bradbury's deployed consensus
    # implementation 0x0a2c393975da79505ed930efc55ae4aeb88b0d62.
    signature = client.w3.eth.contract(
        abi=client.chain.consensus_main_contract["abi"]
    ).get_function_by_name("addTransaction").signature
    print("SE7_SDK_ADD_SIGNATURE",signature,flush=True)
    print("SE7_SDK_ENCODED_SELECTOR",calldata[:10],flush=True)
    assert calldata[:10].lower() == "0xe71d5196"
    assert isinstance(calldata,str)
    assert len(calldata)>300
    decoded = decode(
        ["address", "address", "uint256", "uint256", "bytes", "uint256"],
        bytes.fromhex(calldata[10:]),
    )
    assert decoded[0].lower() == buyer.address.lower()
    assert decoded[1].lower() == seller.address.lower()
    assert decoded[2] == 5
    assert decoded[3] == 3
    assert decoded[4] == bytes.fromhex("1234")
    assert decoded[5] == 0

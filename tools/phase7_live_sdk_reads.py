"""Read the known Bradbury escrow through pinned genlayer-py, without writes.

Uses the GenLayer RPC from the official Bradbury chain definition (not the
EVM-only Chain RPC). The ephemeral SDK account is read-only and never printed,
persisted, or used to sign. This is an operational probe, not a test fixture.
"""
import hashlib
import json

from eth_account import Account
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.contracts import actions

from phase7_bradbury_read_envelope import (
    PINNED_GHOST,
    install_bradbury_finalized_read_adapter,
)
from phase7_legacy_compat import require_legacy_bradbury
from phase7_legacy_method_dispatch import install_bradbury_v0216_dispatch


def main():
    account = Account.create()
    client = GenLayerClient(testnet_bradbury, account)
    endpoints = client.chain.rpc_urls["default"]["http"]
    if len(endpoints) != 1 or "rpc-bradbury.genlayer.com" not in endpoints[0]:
        raise RuntimeError("unexpected Bradbury GenLayer RPC endpoint")

    # Attest the live chain's old consensus/fee ABI before installing the
    # byte-pinned v0.2.16 read compatibility adapters.
    require_legacy_bradbury(client)
    install_bradbury_v0216_dispatch(client)
    install_bradbury_finalized_read_adapter(client)

    values = {}
    for method, args in (("deal_count", []), ("get_ledger", [0]),
                         ("get_deal", [0]), ("get_transfer_intents", [0])):
        value = actions.read_contract(client, PINNED_GHOST, method, args=args)
        normalized = json.loads(value) if isinstance(value, str) else value
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        values[method] = {
            "type": type(normalized).__name__,
            "sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        }
    print("SE7_PINNED_SDK_FINALIZED_READS_PASS", json.dumps(values, sort_keys=True))


if __name__ == "__main__":
    main()

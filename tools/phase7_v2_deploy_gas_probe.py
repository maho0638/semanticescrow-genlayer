"""Read-only Bradbury deployment gas preview for the pinned v2 source."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

from eth_account import Account
from eth_abi import encode
from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.transactions.fees import normalize_transaction_fees

from phase7_deploy_preflight import (
    ESTIMATE_GAS_CAP, PUBLIC_READONLY_SENDER, V2_SOURCE_SHA256,
    padded_gas, preview_deploy,
)
from phase7_bradbury_read_envelope import PINNED_GHOST
from phase7_legacy_compat import CONSENSUS_PROXY, require_legacy_bradbury

EVM_RPC = "https://rpc.testnet-chain.genlayer.com"
ROUTER_SOURCE = Path("contracts/evm/SemanticEscrowNativePayoutRouter.sol")
NODE_SCRIPT = (
    "const fs=require('fs');const solc=require('solc');"
    "const input=JSON.parse(fs.readFileSync(0,'utf8'));"
    "process.stdout.write(solc.compile(JSON.stringify(input)));"
)


def main():
    source = Path("contracts/semantic_escrow_attributed_v2.py").read_text(
        encoding="utf-8"
    )
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    if source_hash != V2_SOURCE_SHA256:
        raise RuntimeError("v2 source pin mismatch")

    client = GenLayerClient(testnet_bradbury, Account.create())
    # EVM-only methods have a separate official Bradbury endpoint. The
    # GenLayer endpoint remains reserved for gen_* SDK operations.
    client.provider.url = EVM_RPC
    require_legacy_bradbury(client)
    result = preview_deploy(client, source)
    latest = client.provider.make_request("eth_getBlockByNumber", ["latest", False])["result"]
    base_fee = int(latest["baseFeePerGas"], 16)
    block_limit = int(latest["gasLimit"], 16)
    gas_price = base_fee + 2_000_000_000
    nonce = client.provider.make_request(
        "eth_getTransactionCount", [PUBLIC_READONLY_SENDER, "latest"]
    )["result"]

    terms = json.dumps([{
        "amount_wei": "100000000000000",
        "delivery_due_at": int(time.time()) + 4 * 86400,
        "criteria_text": "Gas-only escrow profile",
        "criteria_items": [{"id": "delivery", "text": "delivery proof", "mandatory": True}],
    }], separators=(",", ":"))
    evidence = json.dumps([
        {"url": "https://one.example/proof", "sha256": "11" * 32},
        {"url": "https://two.example/proof", "sha256": "22" * 32},
    ], separators=(",", ":"))
    writes = [
        ("v1_create_deal", "create_deal", ["0x" + "11" * 20, terms, "gas-v1"], 10**14),
        ("v1_propose_cancel", "propose_cancel", [0], 0),
        ("v1_confirm_cancel", "confirm_cancel", [0], 0),
        ("v2_configure_payment_router", "configure_payment_router", ["0x" + "11" * 20], 0),
        ("v2_create_deal", "create_deal", ["0x" + "11" * 20, terms, "gas-v2"], 10**14),
        ("v2_submit_evidence", "submit_evidence", [0, evidence], 0),
        ("v2_assess", "assess", [0], 0),
        ("v2_settle", "settle", [0], 0),
    ]
    write_estimates = {}
    for label, method, args, value in writes:
        wire = calldata.encode({"method": method, "args": args})
        serialized = serialize([wire, False])
        payload = _encode_add_transaction_data(
            client, SimpleNamespace(address=PUBLIC_READONLY_SENDER),
            PINNED_GHOST, 3, serialized, user_value=value,
            transaction_fees=normalize_transaction_fees(),
        )
        tx = {
            "from": PUBLIC_READONLY_SENDER, "to": CONSENSUS_PROXY,
            "data": payload, "value": hex(value), "nonce": nonce,
            "chainId": "0x107d", "maxFeePerGas": hex(gas_price),
            "maxPriorityFeePerGas": hex(2_000_000_000),
            "gas": hex(min(ESTIMATE_GAS_CAP, block_limit)),
        }
        reply = client.provider.make_request("eth_estimateGas", [tx])
        if not isinstance(reply, dict) or "error" in reply:
            raise RuntimeError("unsigned parent gas estimate unavailable: " + label)
        estimate = int(reply["result"], 16)
        write_estimates[label] = (estimate, padded_gas(estimate, block_limit))

    router_sol = ROUTER_SOURCE.read_text(encoding="utf-8")
    compile_input = {
        "language": "Solidity",
        "sources": {ROUTER_SOURCE.name: {"content": router_sol}},
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
        },
    }
    compiled = subprocess.run(
        ["node", "-e", NODE_SCRIPT], input=json.dumps(compile_input),
        capture_output=True, text=True, check=True, timeout=60,
    )
    artifact = json.loads(compiled.stdout)["contracts"][ROUTER_SOURCE.name][
        "SemanticEscrowNativePayoutRouter"
    ]
    initcode = "0x" + artifact["evm"]["bytecode"]["object"] + encode(
        ["address", "uint256"], ["0x" + "11" * 20, 4221]
    ).hex()
    sender = "0x84D37542B362F96282b19D479cF9b06E15ff62eA"
    router_tx = {
        "from": sender, "data": initcode, "value": "0x0",
        "chainId": "0x107d", "maxFeePerGas": hex(gas_price),
        "maxPriorityFeePerGas": hex(2_000_000_000), "gas": hex(2_000_000),
    }
    gas_reply = client.provider.make_request("eth_estimateGas", [router_tx])
    if not isinstance(gas_reply, dict) or "error" in gas_reply:
        raise RuntimeError("router deployment gas estimate unavailable")
    router_estimate = int(gas_reply["result"], 16)
    router_padded = max(router_estimate + 50_000, (router_estimate * 120 + 99) // 100)
    router_call = client.provider.make_request(
        "eth_call", [{**router_tx, "gas": hex(router_padded)}, "latest"]
    )
    if not isinstance(router_call, dict) or "error" in router_call:
        raise RuntimeError("padded router deployment simulation failed")
    router_fee_wei = router_padded * gas_price

    print("SE7_V2_PARENT_GAS_ESTIMATES", json.dumps({
        key: {"estimated_gas": value[0], "padded_gas": value[1],
              "max_fee_gen": f"{value[1]*gas_price/10**18:.8f}"}
        for key, value in write_estimates.items()
    }, sort_keys=True), flush=True)
    print(
        "SE7_V2_UNSIGNED_DEPLOY_PREVIEW_PASS",
        "SOURCE_SHA256", source_hash,
        "BLOCK", result["block_number"],
        "SOURCE_BYTES", len(source.encode()),
        "ESTIMATED_GAS", result["estimated_gas"],
        "PADDED_GAS", result["padded_gas"],
        "GAS_CEILING", 15_900_000,
        "MAX_FEE_PER_GAS_WEI", result["max_fee_per_gas_wei"],
        "MAX_DEPLOY_FEE_WEI", result["max_fee_wei"],
        "MAX_DEPLOY_FEE_GEN", f"{result['max_fee_wei']/10**18:.8f}",
        "ROUTER_ESTIMATED_GAS", router_estimate,
        "ROUTER_PADDED_GAS", router_padded,
        "ROUTER_MAX_DEPLOY_FEE_WEI", router_fee_wei,
        "ROUTER_MAX_DEPLOY_FEE_GEN", f"{router_fee_wei/10**18:.8f}",
        flush=True,
    )


if __name__ == "__main__":
    main()

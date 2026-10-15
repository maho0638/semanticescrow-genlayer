"""Ephemeral test-only EOAs and public network capability probe.

No private keys printed, written, uploaded or saved as job artifacts.
Only hosted Studio simulator faucet endpoints may be tried. Never request
the public Bradbury faucet without its required interactive authentication.
"""
import json
import time
import requests
from eth_account import Account

RPCS = (
    ("studionet", "https://studio.genlayer.com/api", 61999),
    ("studio-dev", "https://studio-dev.genlayer.com/api", 61997),
    ("bradbury", "https://rpc-bradbury.genlayer.com", 4221),
    ("genlayer-chain", "https://rpc.testnet-chain.genlayer.com", 4221),
)
session = requests.Session()
session.headers.update({"Content-Type": "application/json", "User-Agent": "SemanticEscrow-Ephemeral-Test-2026"})
counter = 0


def rpc(url, method, params):
    global counter
    counter += 1
    try:
        reply = session.post(url, json={"jsonrpc": "2.0", "id": counter, "method": method, "params": params}, timeout=12)
        if reply.status_code != 200:
            return None, "HTTP_" + str(reply.status_code)
        obj = reply.json()
        if "error" in obj:
            error = obj["error"]
            code = error.get("code", "?") if isinstance(error, dict) else "?"
            # Do not dump raw remote content into a public CI log.
            return None, "RPC_ERROR_" + str(code)
        if obj.get("result") is None:
            return None, "NULL_RESULT"
        return obj["result"], None
    except requests.RequestException as exc:
        return None, "NETWORK_" + type(exc).__name__
    except (ValueError, TypeError):
        return None, "MALFORMED_JSON"


def balance(url, addr):
    val, err = rpc(url, "eth_getBalance", [addr, "latest"])
    if err:
        return None, err
    try:
        return int(val, 16), None
    except (TypeError, ValueError):
        return None, "INVALID_BALANCE"


def attempt_studio_faucet(name, url, addr):
    # Documented glsim snake_case and previous pinned Studio camelCase
    # are attempted only if the prior method is unknown.
    amount = 10**16  # 0.01 simulation GEN, not valuable network money.
    for method in ("sim_fundAccount", "sim_fund_account"):
        result, err = rpc(url, method, [addr, amount])
        print("EPHEMERAL_FAUCET_METHOD", name, method, "OK" if not err else err, flush=True)
        if err is None:
            return "RPC_ACCEPTED"
        if err != "RPC_ERROR_-32601":
            return "NOT_AVAILABLE"
    return "NOT_SUPPORTED"


def test_direct_evm_transfer(name, url, chain_id, buyer, seller, funded):
    # Never confuse a standard EVM payment test with a GenLayer Ghost child.
    if funded < 1:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "SKIPPED_INSUFFICIENT_FUNDS", flush=True)
        return
    gas_price_hex, err = rpc(url, "eth_gasPrice", [])
    if err:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "GAS_PRICE_" + err, flush=True)
        return
    try:
        gas_price = int(gas_price_hex, 16)
    except (ValueError, TypeError):
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "INVALID_GAS_PRICE", flush=True)
        return
    cost = 21000 * gas_price + 1
    if funded < cost:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "INSUFFICIENT_GAS", flush=True)
        return
    nonce_hex, err = rpc(url, "eth_getTransactionCount", [buyer.address, "latest"])
    if err:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "NONCE_" + err, flush=True)
        return
    before_seller, err = balance(url, seller.address)
    if err:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "SELLER_BALANCE_" + err, flush=True)
        return
    nonce = int(nonce_hex, 16)
    signed = Account.sign_transaction({
        "nonce": nonce, "to": seller.address, "value": 1,
        "gas": 21000, "gasPrice": gas_price, "chainId": chain_id,
    }, buyer.key)
    raw = signed.raw_transaction.to_0x_hex()
    txid, err = rpc(url, "eth_sendRawTransaction", [raw])
    raw = None
    signed = None
    if err:
        print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "SUBMISSION_" + err, flush=True)
        return
    print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "SUBMITTED", str(txid)[:66], flush=True)
    for _ in range(8):
        receipt, err = rpc(url, "eth_getTransactionReceipt", [txid])
        if receipt is not None:
            after, balance_error = balance(url, seller.address)
            status = receipt.get("status") if isinstance(receipt, dict) else None
            paid = after is not None and after - before_seller == 1
            print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "RECEIPT_STATUS", status,
                  "EXACT_RECIPIENT_DELTA", paid, "ERROR", balance_error or "NONE", flush=True)
            return
        time.sleep(2)
    print("DIRECT_EVM_ONLY_NOT_ESCROW", name, "NOT_FINALIZED_WITHIN_PROBE", flush=True)


def main():
    # Secure OS randomness inside a disposable GitHub-hosted runner.
    # Only public addresses are logged. No mnemonic is ever generated.
    buyer, seller = Account.create(), Account.create()
    assert buyer.address != seller.address
    print("EPHEMERAL_WALLET_CREATED", "buyer", buyer.address, "seller", seller.address, flush=True)
    for name, url, expected_chain in RPCS:
        chain, err = rpc(url, "eth_chainId", [])
        if err:
            print("NETWORK_PROBE", name, err, flush=True)
            continue
        try:
            actual_chain = int(chain, 16)
        except (ValueError, TypeError):
            print("NETWORK_PROBE", name, "INVALID_CHAIN_ID", flush=True)
            continue
        if actual_chain != expected_chain:
            print("NETWORK_PROBE", name, "CHAIN_MISMATCH", actual_chain, expected_chain, flush=True)
            continue
        buyer_balance, err = balance(url, buyer.address)
        if err:
            print("NETWORK_PROBE", name, "BALANCE_" + err, flush=True)
            continue
        print("NETWORK_PROBE", name, "CHAIN_OK", actual_chain,
              "BUYER_BALANCE_WEI", buyer_balance, flush=True)
        if name in ("studionet", "studio-dev"):
            faucet = attempt_studio_faucet(name, url, buyer.address)
            print("EPHEMERAL_FAUCET_RESULT", name, faucet, flush=True)
            for _ in range(3):
                buyer_balance, err = balance(url, buyer.address)
                if not err and buyer_balance:
                    break
                time.sleep(2)
            print("EPHEMERAL_FUNDING_VERIFIED", name, bool(buyer_balance), flush=True)
            if not err and buyer_balance:
                test_direct_evm_transfer(name, url, actual_chain, buyer, seller, buyer_balance)
        else:
            print("FAUCET_AUTH_REQUIRED", name, "NO_AUTOMATED_CLAIM_ATTEMPTED", flush=True)
    print("EPHEMERAL_PRIVATE_KEYS_NOT_STORED", flush=True)


if __name__ == "__main__":
    main()

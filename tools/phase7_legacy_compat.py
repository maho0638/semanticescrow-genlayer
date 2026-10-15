"""Fail-closed read-only Bradbury v0.6 legacy transaction compatibility gate.

The pinned GenLayer-PY v0.19 RC tries new FeeManager price getters that are NOT
implemented by Bradbury's deployed contract as of 2026-10-15. The actual
ConsensusMain supports the legacy six-argument addTransaction selector.
Only for this pinned, verified deployment, permit SDK's *native legacy path*
(fees=None). Never fabricate price caps or deploy using an unverified ABI.

All checks are read-only. This module does NOT approve production escrow.
"""
CHAIN_ID = 4221
FEE_PROXY = "0xF205868bf5db79d2162843742D18D0900A9E462a"
FEE_IMPLEMENTATION = "0x31199772507933c5ad94da28ab7b02bf9c41069c"
CONSENSUS_PROXY = "0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D"
CONSENSUS_IMPLEMENTATION = "0x0a2c393975da79505ed930efc55ae4aeb88b0d62"
EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

# Onchain bytecode selectors verified from each EIP-1967 implementation.
LEGACY_FEE_CALCULATE = "4fe8920e"
LEGACY_CONSENSUS_ADD = "e71d5196"
GET_GEN_PER_TIME_UNIT = "0xeeb5f1be"
GET_STORAGE_UNIT_PRICE = "0x97f426e6"
GET_VALIDATORS_PER_ROUND = "0xa76c02e0"
MISSING_NEW_GETTERS = ("5c9fd1a3", "c0809aa4")

class IncompatibleBradburyProtocol(RuntimeError):
    """The current chain does not match the verified fee-free legacy path."""


def _rpc(client, method, params):
    response = client.provider.make_request(method, params)
    if not isinstance(response, dict) or response.get("error") or "result" not in response:
        raise IncompatibleBradburyProtocol(method + " did not succeed")
    return response["result"]


def _hex_int(value):
    if not isinstance(value, str) or not value.startswith("0x"):
        raise IncompatibleBradburyProtocol("missing hex RPC result")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise IncompatibleBradburyProtocol("malformed hex RPC result") from exc


def _impl(client, proxy, expected_impl, required_selector, disallowed=()):
    slot = _rpc(client, "eth_getStorageAt", [proxy, EIP1967_IMPL, "latest"])
    impl = "0x" + format(_hex_int(slot) & ((1 << 160) - 1), "040x")
    if impl.lower() != expected_impl.lower():
        raise IncompatibleBradburyProtocol("EIP-1967 implementation changed")
    code = _rpc(client, "eth_getCode", [impl, "latest"])
    if not isinstance(code, str) or len(code) < 100 or not code.startswith("0x"):
        raise IncompatibleBradburyProtocol("implementation runtime code absent")
    bc = code.lower()[2:]
    if required_selector not in bc:
        raise IncompatibleBradburyProtocol("required legacy function selector absent")
    if any(sig in bc for sig in disallowed):
        raise IncompatibleBradburyProtocol("fee manager has upgraded; verify prices anew")
    return impl


def _read_word(client, to, selector, data=""):
    res = _rpc(client, "eth_call", [{"to": to, "data": selector + data}, "latest"])
    if not isinstance(res, str) or len(res) != 66:
        raise IncompatibleBradburyProtocol("unexpected eth_call return data")
    return _hex_int(res)


# Published six-argument v0.6 consensus ABI, verified against deployed
# 0xe71d5196. Preserve unrelated ABI entries (appeals, receipts etc).
LEGACY_ADD_ABI = {
    "inputs": [
        {"internalType":"address","name":"_sender","type":"address"},
        {"internalType":"address","name":"_recipient","type":"address"},
        {"internalType":"uint256","name":"_numOfInitialValidators","type":"uint256"},
        {"internalType":"uint256","name":"_maxRotations","type":"uint256"},
        {"internalType":"bytes","name":"_calldata","type":"bytes"},
        {"internalType":"uint256","name":"_validUntil","type":"uint256"},
    ],
    "name":"addTransaction", "outputs":[], "stateMutability":"payable",
    "type":"function"
}
OLD_ADD_INPUT_TYPES=[e["type"] for e in LEGACY_ADD_ABI["inputs"]]


def _install_legacy_consensus_abi(chain_config):
    """Repair ONLY the in-process SDK ABI after onchain verification.

    No network activity or account changes. No global writes to GitHub/files.
    """
    abi = chain_config["abi"]
    methods = [m for m in abi if m.get("type") == "function" and m.get("name") == "addTransaction"]
    if len(methods) != 1:
        raise IncompatibleBradburyProtocol("unknown SDK addTransaction overloads")
    current_types = [arg.get("type") for arg in methods[0].get("inputs", [])]
    if current_types not in (OLD_ADD_INPUT_TYPES, ["tuple"]):
        raise IncompatibleBradburyProtocol("unrecognized SDK consensus ABI")
    if current_types != OLD_ADD_INPUT_TYPES:
        # Retain object identity in case gltest creates a second client using
        # the same SDK chain config singleton.
        abi[:] = [
            dict(LEGACY_ADD_ABI) if item is methods[0] else item for item in abi
        ]
    return None


def require_legacy_bradbury(client):
    """Return fee kwargs for the SDK's *existing* legacy ABI: None, or fail.

    This has no write side effects, and does not calculate nor assume feeValue.
    """
    if getattr(client.chain, "id", None) != CHAIN_ID:
        raise IncompatibleBradburyProtocol("wrong GenLayer chain")
    if _hex_int(_rpc(client, "eth_chainId", [])) != CHAIN_ID:
        raise IncompatibleBradburyProtocol("RPC and configured chain ID differ")

    ch = client.chain.consensus_main_contract
    fee = client.chain.fee_manager_contract
    if ch is None or fee is None:
        raise IncompatibleBradburyProtocol("missing chain contract configuration")
    if str(ch.get("address", "")).lower() != CONSENSUS_PROXY.lower():
        raise IncompatibleBradburyProtocol("wrong ConsensusMain address")
    if str(fee.get("address", "")).lower() != FEE_PROXY.lower():
        raise IncompatibleBradburyProtocol("wrong FeeManager address")

    abi = ch.get("abi")
    methods = [m for m in abi if m.get("name") == "addTransaction" and m.get("type") == "function"] if isinstance(abi, list) else []
    if len(methods) != 1 or [
        v.get("type") for v in methods[0].get("inputs", [])
    ] not in (OLD_ADD_INPUT_TYPES, ["tuple"]):
        raise IncompatibleBradburyProtocol("unknown SDK consensus ABI; refusing to patch")

    _impl(client, CONSENSUS_PROXY, CONSENSUS_IMPLEMENTATION, LEGACY_CONSENSUS_ADD)
    _impl(client, FEE_PROXY, FEE_IMPLEMENTATION, LEGACY_FEE_CALCULATE, MISSING_NEW_GETTERS)

    if _read_word(client, FEE_PROXY, GET_GEN_PER_TIME_UNIT) != 0:
        raise IncompatibleBradburyProtocol("GenLayer timeunit fees are now active")
    if _read_word(client, FEE_PROXY, GET_STORAGE_UNIT_PRICE) != 0:
        raise IncompatibleBradburyProtocol("GenLayer storage price is now active")
    if _read_word(client, FEE_PROXY, GET_VALIDATORS_PER_ROUND, format(0, "064x")) != 5:
        raise IncompatibleBradburyProtocol("unexpected first-round validator count")
    # The installed 0.19 RC exposes a fee-aware tuple ABI, while the actual
    # deployed v0.6 ConsensusMain supports the six-input selector. Correct
    # only this in-memory ABI object after all proxy/price guards pass.
    _install_legacy_consensus_abi(ch)
    return None  # SDK's native old path, no guessed deposit or price values.

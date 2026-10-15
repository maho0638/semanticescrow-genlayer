"""Sanitized transaction-path diagnostics, never print raw signed transactions.

Only method name, short public hash, RPC code, class and a fixed known error
category are emitted. Raw request/response payloads, exception args, tokens,
mnemonics, private keys, headers and private endpoints must remain invisible.
"""
import re

RELEVANT = frozenset({
    "eth_sendRawTransaction", "eth_estimateGas", "eth_getTransactionCount",
    "eth_getBlockByNumber", "eth_chainId", "eth_getTransactionReceipt"
})
CATEGORIES = (
    ("cf-mitigated", "CLOUDFLARE_CHALLENGE"),
    ("403", "HTTP_403"),
    ("-32098", "LOCAL_GATEWAY_TRANSPORT"),
    ("insufficient funds", "INSUFFICIENT_FUNDS"),
    ("replacement transaction underpriced", "NONCE_REPLACEMENT_UNDERPRICED"),
    ("nonce too low", "NONCE_TOO_LOW"),
    ("intrinsic gas", "INTRINSIC_GAS"),
    ("max fee per gas", "EIP1559_FEE_CAP"),
    ("base fee", "EIP1559_BASEFEE"),
    ("gas required exceeds", "GAS_TOO_LOW"),
    ("execution reverted", "EVM_REVERT"),
    ("internal server error", "UPSTREAM_INTERNAL"),
    ("sequencer-leader", "UPSTREAM_SEQUENCER"),
    ("invalid json", "INVALID_JSON"),
    ("timeout", "RPC_TIMEOUT"),
    ("timed out", "RPC_TIMEOUT"),
)


def classification(error):
    """Strict fixed vocabulary; no arbitrary exception content revealed."""
    # Catch both GenLayerError strings and underlying requests exceptions.
    try:
        summary=str(error).lower()
    except Exception:
        summary=""
    match=re.search(r"\bcode[=:]\s*(-?\d+)\b",summary)
    rpc_code=match.group(1) if match else "UNKNOWN"
    return rpc_code, next((name for fragment,name in CATEGORIES if fragment in summary),"UNCLASSIFIED")


def install_rpc_diagnostics(client):
    provider=client.provider
    if getattr(provider, "_phase7_diagnostics_installed", False):
        return
    original=provider.make_request

    def observed(method,params):
        name=str(method)
        if name=="eth_sendRawTransaction":
            raw=params[0] if isinstance(params,(list,tuple)) and params else None
            byte_count=(len(raw)-2)//2 if isinstance(raw,str) and raw.startswith("0x") else 0
            print("SE7_PUBLIC_RPC_SEND_BEGIN",byte_count,flush=True)
        try:
            response=original(method,params)
        except Exception as exc:
            if name in RELEVANT:
                code,category=classification(exc)
                print("SE7_PUBLIC_RPC_EXCEPTION",name,type(exc).__name__,
                      "CODE",code,"CATEGORY",category,flush=True)
            raise
        if name=="eth_sendRawTransaction":
            result=response.get("result") if isinstance(response,dict) else None
            public_hash=(result if isinstance(result,str)
                and bool(re.fullmatch(r"0x[0-9a-fA-F]{64}",result)) else "NO_HASH")
            print("SE7_PUBLIC_RPC_SEND_RESULT",public_hash,flush=True)
        return response

    provider.make_request=observed
    provider._phase7_diagnostics_installed=True

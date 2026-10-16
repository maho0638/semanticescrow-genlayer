"""Fix the real Bradbury v0.6 → pinned GenVM v0.2.16 method-dispatch mismatch.

On 2026-10-16 the signed create_deal payload on Bradbury was conclusively
decoded as {"": "create_deal", "args": [...]}. The *official v0.2.16*
_genlayer_runner.py dispatches using cd.get("method", ""), so this wire
format selects fallback/__receive__ instead of create_deal.

genlayer-py==0.19.0rc2's make_calldata_object uses the old empty-name key.
Patch only the public Python SDK's outgoing calldata adapter, not deployed
contract code, signer, chain ID, fee encoding, wallet, EVM ABI, or GenVM.
Never patch arbitrary methods to bypass SDK security guards.
"""
from genlayer_py.contracts import actions as _actions
from genlayer_py.contracts import utils as _utils

class MethodDispatchMismatch(RuntimeError):
    pass

_ORIGINAL=_utils.make_calldata_object
_INSTALLED=False

def canonical_v0216_calldata(method=None,args=None,kwargs=None):
    obj=_ORIGINAL(method=method,args=args,kwargs=kwargs)
    if type(obj) is not dict:
        raise MethodDispatchMismatch("SDK calldata must be a dict")
    output=obj.copy()
    if method is None:
        if "method" in output or "" in output:
            raise MethodDispatchMismatch("deployment calldata unexpectedly contains a method")
        return output
    if type(method) is not str or not method or method.startswith("__"):
        raise MethodDispatchMismatch("invalid user method")
    if output.get("method")==method and "" not in output:
        return output
    if output.get("")!=method or "method" in output:
        raise MethodDispatchMismatch("unexpected pinned SDK dispatch field")
    del output[""]
    output["method"]=method
    return output

def install_bradbury_v0216_dispatch(client):
    """Install after read-only Bradbury ABI gate and BEFORE any signed write.

    Only for the existing Bradbury testnet 4221 and source-pinned v0.2.16
    runner. To undo, terminate this temporary test process.
    """
    global _INSTALLED
    if type(client.chain.id) is not int or client.chain.id!=4221:
        raise MethodDispatchMismatch("wrong chain ID")
    # Verify that the imported action path is the exact module we modify,
    # and that our rewrite yields the canonical wire method and retains args.
    probe=canonical_v0216_calldata("create_deal",["seller","terms","nonce"])
    if probe!={"method":"create_deal","args":["seller","terms","nonce"]}:
        raise MethodDispatchMismatch("canonical method calldata probe failed")
    _utils.make_calldata_object=canonical_v0216_calldata
    _actions.make_calldata_object=canonical_v0216_calldata
    _INSTALLED=True
    return probe

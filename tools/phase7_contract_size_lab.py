"""Zero-cost SemanticEscrow code-size lab: compare AST-preserving variants.

Never broadcasts, signs, or changes state. Every candidate uses the exact
source metadata dependency pin and identical public ABI method names.
GenLayer Chain is queried with eth_estimateGas only.
"""
import ast
import hashlib
import json
from pathlib import Path

import python_minifier
import requests
from eth_account import Account
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient
from genlayer_py.abi import calldata
from genlayer_py.abi.transactions import serialize
from genlayer_py.contracts.actions import _encode_add_transaction_data
from genlayer_py.contracts.utils import make_calldata_object
from genlayer_py.transactions.fees import normalize_transaction_fees
from tools.phase7_legacy_compat import _install_legacy_consensus_abi, CONSENSUS_PROXY

RPC="https://rpc.testnet-chain.genlayer.com"
FROM="0x84D37542B362F96282b19D479cF9b06E15ff62eA"
MAX_REPORTED_GAS=16_000_000
SOURCE=Path("contracts/semantic_escrow.py").read_text(encoding="utf-8")
LINES=SOURCE.splitlines()
assert LINES[1].startswith('# { "Depends": "py-genlayer:')
META="\n".join(LINES[:2])+"\n"
ORIGINAL=SOURCE

def rpc(method,params):
    response=requests.post(RPC,json={"jsonrpc":"2.0","id":5,"method":method,"params":params},timeout=65)
    response.raise_for_status()
    obj=response.json()
    if obj.get("error"):
        error=obj["error"]
        code=error.get("code") if isinstance(error,dict) else "UNKNOWN"
        return None,str(code)
    return obj.get("result"),None

def public_signature_shape(source):
    tree=ast.parse(source)
    shapes={}
    for cls in tree.body:
        if not isinstance(cls,ast.ClassDef):continue
        for f in cls.body:
            if not isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            if any(ast.unparse(d).startswith("gl.public.") for d in f.decorator_list):
                shapes[f.name]=[
                  (a.arg,ast.dump(a.annotation) if a.annotation else None)
                  for a in f.args.args
                ]
    return shapes

SIGNATURES=public_signature_shape(ORIGINAL)
assert len(SIGNATURES)==17
PRESERVE={name for signature in SIGNATURES.values() for name,_ in signature}
PRESERVE.update(["self","idx","result","args","kwargs","account","sender","recipient"])
print("SE7_SIZE","ORIGINAL_BYTES",len(SOURCE.encode()),"API_COUNT",len(SIGNATURES),flush=True)

client=GenLayerClient(testnet_bradbury,Account.create())
_install_legacy_consensus_abi(client.chain.consensus_main_contract)

def source_variant(tag,replace):
    return {
       "tag":tag,
       "source":META+replace+"\n"
    }

variants=[{"tag":"original","source":ORIGINAL}]
opts=dict(
   remove_annotations=False,remove_literal_statements=True,hoist_literals=False,
   rename_globals=False,remove_asserts=False,remove_debug=False,
   remove_dead_branches=False,constant_folding=False,
   remove_builtin_exception_brackets=False,
   remove_object_base=False,convert_posargs_to_args=False
)
for tag,diff in [
    ("conservative",{"rename_locals":False,"prefer_single_line":False}),
    ("dense",{"rename_locals":False,"prefer_single_line":True}),
    ("local_names",{"rename_locals":True,"preserve_locals":sorted(PRESERVE),"prefer_single_line":True}),
    ("literals_hoisted",{"rename_locals":True,"preserve_locals":sorted(PRESERVE),
                          "hoist_literals":True,"constant_folding":True,"remove_dead_branches":True,
                          "remove_builtin_exception_brackets":True,"prefer_single_line":True}),
    ("globals_condensed",{"rename_locals":True,"preserve_locals":sorted(PRESERVE),
                          "rename_globals":True,
                          "preserve_globals":sorted({
                              "SemanticEscrow","gl","Address","u256","DynArray","TreeMap",
                              "hashlib","json","datetime","timezone"
                          }|set(SIGNATURES.keys())),
                          "hoist_literals":True,"constant_folding":True,
                          "remove_dead_branches":True,
                          "remove_builtin_exception_brackets":True,
                          "prefer_single_line":True}),
]:
    try:
        # Remove initial dependency comments and prepend them verbatim.
        out=python_minifier.minify("\n".join(LINES[2:]),**opts,**diff)
        variants.append(source_variant(tag,out))
    except Exception as exc:
        print("SE7_SIZE",tag,"COMPILER_FAILURE_CLASS",type(exc).__name__,flush=True)

for candidate in variants:
    tag,source=candidate["tag"],candidate["source"]
    try:
        ast.parse(source)
        shape=public_signature_shape(source)
        match=shape==SIGNATURES
        print("SE7_SIZE",tag,"BYTES",len(source.encode("utf-8")),"SHA256",
              hashlib.sha256(source.encode()).hexdigest(),
              "API_SIGNATURE_MATCH",match,flush=True)
        if not match:continue
        payload=serialize([source,calldata.encode(make_calldata_object(method=None,args=None,kwargs=None)),False])
        data=_encode_add_transaction_data(client,type("Pub",(),{"address":FROM})(),
               "0x0000000000000000000000000000000000000000",3,payload,
               transaction_fees=normalize_transaction_fees())
        if not data.startswith("0xe71d5196"):raise AssertionError("wrong legacy selector")
        tx={"from":FROM,"to":CONSENSUS_PROXY,"data":data,"value":"0x0"}
        estimate,error=rpc("eth_estimateGas",[tx])
        if error:
            print("SE7_SIZE",tag,"ESTIMATE_ERROR_CODE",error,flush=True)
        else:
            gas=int(estimate,16)
            print("SE7_SIZE",tag,"GAS",gas,"WITHIN_REPORTED_LIMIT",gas<MAX_REPORTED_GAS,
                  "PAYLOAD_BYTES",(len(data)-2)//2,flush=True)
    except Exception as exc:
        print("SE7_SIZE",tag,"ERROR_CLASS",type(exc).__name__,flush=True)

"""Inspect the EXACT pinned deployed GenLayer-PY/gltest source; read-only.

Shows hash selection and wait behavior without executing any real network call.
"""
import importlib.util
from pathlib import Path

for name in ("gltest","genlayer_py"):
    spec=importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit("SE7_SDK_PACKAGE_MISSING "+name)
    root=Path(spec.origin).parent
    print("SE7_SDK_PACKAGE",name,root,flush=True)
    for file in root.rglob("*.py"):
        rel=file.relative_to(root).as_posix()
        if rel.count("/")>5:continue
        source=file.read_text(encoding="utf-8",errors="replace")
        lines=source.splitlines()
        needles=("def deploy_contract_tx(","def _deploy_contract","def wait_for_transaction_receipt(",
                 "def get_transaction(","def deploy_contract(","def _submit_transaction(",
                 "def _send_transaction(","def extract_transaction_id(",
                 "def extract_contract_address(","def wait_for_finalization(",
                 "def wait_for_decision(","def _wait_for_","def _simplify_transaction_receipt(")
        matches=[i for i,line in enumerate(lines) if any(n in line for n in needles)]
        for i in matches:
            start=max(0,i-6)
            end=min(len(lines),i+95)
            print("SE7_SDK_SOURCE_BEGIN",name,rel,"LINE",i+1,flush=True)
            print("\n".join(f"{j+1:4} {lines[j]}" for j in range(start,end)),flush=True)
            print("SE7_SDK_SOURCE_END",flush=True)

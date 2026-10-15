"""Check exact SemanticEscrow schema against hosted Studio-dev from gltest CLI.

The gltest CLI initializes contract artifact configuration; standalone Python
scripts do not. This test never interacts with Bradbury or signs transactions.
"""
from pathlib import Path
import sys

from gltest import get_contract_factory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from phase7_schema_compat import bind_verified_schema, REQUIRED_METHODS


def test_exact_contract_compiles_in_hosted_studio_dev():
    factory = get_contract_factory(
        contract_file_path=Path("contracts/semantic_escrow.py").resolve()
    )
    result = bind_verified_schema(factory)
    assert set(result["methods"]) == REQUIRED_METHODS
    assert factory._get_schema_with_fallback() is result
    print("SE7_STUDIO_SCHEMA_ACTUAL_COMPILATION_PASS", len(result["methods"]), flush=True)

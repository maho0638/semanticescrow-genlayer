"""Read-only hosted Studio-dev schema compile smoke for actual checked-in code."""
from pathlib import Path
from gltest import get_contract_factory
from phase7_schema_compat import bind_verified_schema, REQUIRED_METHODS

factory = get_contract_factory(contract_file_path=Path("contracts/semantic_escrow.py").resolve())
result = bind_verified_schema(factory)
assert set(result["methods"]) == REQUIRED_METHODS
print("SE7_STUDIO_SCHEMA_ACTUAL_COMPILATION_PASS", len(result["methods"]), flush=True)

"""Fail-closed fake Studio schema tests and exact on-disk code hash."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from phase7_schema_compat import (
    SOURCE_SHA256, STUDIO_DEV, REQUIRED_METHODS, SchemaUnavailable,
    _check_result, _check_source, bind_verified_schema, fetch_verified_schema,
)


@pytest.fixture
def factory():
    return SimpleNamespace(contract_code=Path("contracts/semantic_escrow.py").read_text(encoding="utf-8"))


def schema():
    return {"ctor": {}, "methods": {name: {"params": []} for name in REQUIRED_METHODS}}


def test_actual_contract_code_is_pinned(factory):
    data = _check_source(factory)
    import hashlib
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA256


def test_accept_only_exact_schema(factory, monkeypatch):
    body = {"jsonrpc": "2.0", "id": 1, "result": schema()}
    seen = {}
    def fake_post(url, json, timeout):
        seen["url"] = url
        seen["body"] = json
        return SimpleNamespace(status_code=200, json=lambda: body)
    from phase7_schema_compat import requests
    monkeypatch.setattr(requests, "post", fake_post)
    result = bind_verified_schema(factory)
    assert set(result["methods"]) == REQUIRED_METHODS
    assert factory._get_schema_with_fallback() is result
    assert seen["url"] == STUDIO_DEV
    assert seen["body"]["method"] == "gen_getContractSchemaForCode"
    assert bytes.fromhex(seen["body"]["params"][0][2:]).decode() == factory.contract_code


@pytest.mark.parametrize("bad", [
    {}, {"jsonrpc":"2.0","error":{"code":-32603}},
    {"jsonrpc":"2.0","result":None},
    {"jsonrpc":"2.0","result":{"methods":{}}},
    {"jsonrpc":"2.0","result":{"ctor":{},"methods":{}}},
    {"jsonrpc":"2.0","result":{"ctor":{},"methods":None}},
    {"jsonrpc":"2.0","result":{"ctor":{},"methods":{**schema()["methods"],"extra":{}}}},
])
def test_bad_schema_refused(bad):
    with pytest.raises(SchemaUnavailable):
        _check_result(bad)


def test_source_change_fails_before_network(factory, monkeypatch):
    factory.contract_code += "\\n"
    def never(*args, **kwargs):
        raise AssertionError("must not contact network")
    from phase7_schema_compat import requests
    monkeypatch.setattr(requests, "post", never)
    with pytest.raises(SchemaUnavailable):
        fetch_verified_schema(factory)

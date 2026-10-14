"""GenLayer test compatibility and strict Direct Mode serialization checks."""

import tempfile
import importlib
from pathlib import Path
import os

import pytest

from gltest.direct import loader, sdk_loader, wasi_mock

os.environ["GENVM_PREBUILT_DIR"] = str(Path(__file__).resolve().parents[1] / "vendor")



_cache = Path(
    os.environ.get(
        "SEMANTICESCROW_GENVM_CACHE",
        str(Path(tempfile.gettempdir()) / "semanticescrow-gltest-cache"),
    )
)
sdk_loader.CACHE_DIR = _cache
sdk_loader.BUNDLE_CACHE_DIR = _cache / "bundles-v2"
sdk_loader.TREE_CACHE_DIR = _cache / "trees-v2"

@pytest.fixture(autouse=True)
def _enable_direct_mode_pickling_checks(request):
    """Exercise the serialization boundary for every test using Direct Mode."""
    if "direct_vm" in request.fixturenames:
        request.getfixturevalue("direct_vm").check_pickling = True


def _patch_nondet_for_current_sdk(vm):
    if getattr(vm, "_gltest_direct_mode_patched", False):
        return

    from genlayer.types import Lazy

    def require_picklable_roundtrip(function, label):
        # The upstream Direct Mode helper only warns when cloudpickle fails.
        # Fail this suite instead: production must transfer both closures
        # across the nondeterministic boundary.
        import cloudpickle

        serialized = cloudpickle.dumps(function)
        restored = cloudpickle.loads(serialized)
        if not callable(restored):
            raise AssertionError(label + " did not round-trip as a callable")

    def direct_nondet(leader_fn, validator_fn, /, **kwargs):
        active_vm = wasi_mock.get_vm()
        if active_vm._check_pickling:
            require_picklable_roundtrip(leader_fn, "leader_fn")
            require_picklable_roundtrip(validator_fn, "validator_fn")
        active_vm._in_nondet = True
        try:
            result = leader_fn()
        finally:
            active_vm._in_nondet = False
        active_vm._captured_validators.append((result, leader_fn, validator_fn))
        return result

    def lazy_nondet(leader_fn, validator_fn, /, **kwargs):
        return Lazy(lambda: direct_nondet(leader_fn, validator_fn, **kwargs))

    direct_nondet.lazy = lazy_nondet
    vm.run_nondet = direct_nondet
    vm.run_nondet_unsafe = direct_nondet
    vm._gltest_direct_mode_patched = True





def _allocate_contract_current_layout(contract_cls, vm, *args, **kwargs):
    # Preserve Direct Mode storage allocation using the pinned SDK builder.
    from genlayer.storage import ROOT_SLOT_ID, Root
    from genlayer.storage._internal.generate import (
        ORIGINAL_INIT_ATTR,
        _storage_build,
        _BuilderCtx,
    )

    descriptor = _storage_build(_BuilderCtx.empty(), contract_cls)
    Root.MANAGER = vm._storage
    slot = vm._storage.get_store_slot(ROOT_SLOT_ID)
    instance = descriptor.get(slot, 0)
    init = getattr(descriptor, "cls", None)
    init = getattr(init, "__init__", None) if init is not None else getattr(contract_cls, "__init__", None)
    if init is not None:
        if hasattr(init, ORIGINAL_INIT_ATTR):
            init = getattr(init, ORIGINAL_INIT_ATTR)
        init(instance, *args, **kwargs)
    return instance


loader._allocate_contract = _allocate_contract_current_layout

_original_load_module = loader._load_module


def _load_module_reset_contract_registration(contract_path):
    genvm_contracts = importlib.import_module("genlayer.contract")
    genvm_contracts.__known_contract__ = None
    return _original_load_module(contract_path)


loader._load_module = _load_module_reset_contract_registration



def _patch_nondet_current_sdk():
    vm = importlib.import_module("genlayer.vm")
    _patch_nondet_for_current_sdk(vm)


loader._patch_run_nondet_for_direct_mode = _patch_nondet_current_sdk

# The pinned SDK decodes JSON text itself. gltest 0.30.0rc2 prematurely
# parses mock JSON into a dict. Adapt only the mock transport envelope.
_original_llm_request = wasi_mock._handle_llm_request


def _llm_json_text_envelope(vm, data):
    import json
    response = vm._match_llm_mock(data.get("prompt", ""))
    if response is not None:
        return {"ok": response if isinstance(response, (str, bytes, bytearray)) else json.dumps(response)}
    result = _original_llm_request(vm, data)
    if isinstance(result, dict) and 'ok' in result and not isinstance(result['ok'], (str, bytes, bytearray)):
        return {**result, 'ok': json.dumps(result['ok'])}
    return result


wasi_mock._handle_llm_request = _llm_json_text_envelope

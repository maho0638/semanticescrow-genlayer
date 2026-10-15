"""GenLayer 0.2.16 web GET smoke with gltest 0.30 Direct Mode mocks.

Only synthetic proof data. No network, funds, or user secrets.
"""
import os
import pytest

@pytest.mark.skipif(os.getenv("SEMANTICESCROW_SDK_0_2_EMULATION")!="1",
                    reason="old GenVM SDK source emulation only")
def test_legacy_web_mock_decodes_response(direct_vm):
    direct_vm.mock_web(r"proof-a\\.example", {
        "status":200,
        "body":"Release version 4.2 completed and accepted on 2026-10-10."
    })
    try:
        with direct_vm.activate():
            from genlayer.gl.nondet.web import get
            response=get("https://proof-a.example/release.txt")
            print("SE7_LEGACY_WEB_DIAG","TYPE",type(response).__name__,
                  "STATUS",response.status,
                  "BODY_TYPE",type(response.body).__name__,
                  "BODY_BYTES",len(response.body),flush=True)
            assert response.status==200
            assert response.body==b"Release version 4.2 completed and accepted on 2026-10-10."
    except Exception as exc:
        print("SE7_LEGACY_WEB_DIAG","ERROR_CLASS",type(exc).__name__,flush=True)
        cause=exc.__cause__
        print("SE7_LEGACY_WEB_DIAG","CAUSE_CLASS",type(cause).__name__ if cause else "NONE",flush=True)
        raise

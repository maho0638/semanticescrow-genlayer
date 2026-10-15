"""Generate compact, semantics-preserving candidate only inside CI workspace.

Original audit source is unchanged on GitHub. This candidate is NOT deployed.
It must be independently verified by 153 Direct Mode tests, GenVM lint, and
a source-hash-bounded compiled schema before any test-GEN funding.
"""
import ast
import hashlib
from pathlib import Path
import python_minifier

TARGET=Path("contracts/semantic_escrow.py")
EXPECTED_SOURCE_SHA256="4fae50929d9e98e1d166661acaac120d5153e5dd8ca1b203a444475330223b66"

def exported_shape(source):
    names={}
    module=ast.parse(source)
    for cls in module.body:
        if not isinstance(cls,ast.ClassDef):
            continue
        for fn in cls.body:
            if not isinstance(fn,ast.FunctionDef):
                continue
            if any(ast.unparse(x).startswith("gl.public.") for x in fn.decorator_list):
                names[fn.name]=tuple(
                    (a.arg,ast.dump(a.annotation) if a.annotation is not None else None)
                    for a in fn.args.args
                )
    return names

def main():
    original=TARGET.read_text(encoding="utf-8")
    if hashlib.sha256(original.encode("utf-8")).hexdigest()!=EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Original source changed; source pin mismatch")
    lines=original.splitlines()
    if not lines[1].startswith('# { "Depends": "py-genlayer:'):
        raise RuntimeError("Dependency pin header not found")
    exported=exported_shape(original)
    if len(exported)!=17:
        raise RuntimeError("Public ABI method count changed")
    preserved=set(a for fields in exported.values() for a,_ in fields)
    preserved.update(["self","idx","result","args","kwargs","account","sender","recipient"])
    body=python_minifier.minify(
        "\n".join(lines[2:]),
        remove_annotations=False,
        remove_literal_statements=True,
        hoist_literals=True,
        rename_globals=False,
        rename_locals=True,
        preserve_locals=sorted(preserved),
        constant_folding=True,
        remove_dead_branches=True,
        remove_builtin_exception_brackets=True,
        remove_object_base=False,
        convert_posargs_to_args=False,
        remove_asserts=False,
        remove_debug=False,
        prefer_single_line=True,
    )
    compact="\n".join(lines[:2])+"\n"+body+"\n"
    ast.parse(compact)
    if exported_shape(compact)!=exported:
        raise RuntimeError("ABI signature differs after code compaction")
    if len(compact.encode())>=19_000:
        raise RuntimeError("Candidate is not small enough for size lab")
    TARGET.write_text(compact,encoding="utf-8")
    print("SE7_COMPACT","ORIGINAL_BYTES",len(original.encode()),flush=True)
    print("SE7_COMPACT","CANDIDATE_BYTES",len(compact.encode()),flush=True)
    print("SE7_COMPACT","SOURCE_SHA256",hashlib.sha256(compact.encode()).hexdigest(),flush=True)
    print("SE7_COMPACT","PUBLIC_ABI_SIGNATURES",len(exported),"MATCH",True,flush=True)

if __name__=="__main__":main()

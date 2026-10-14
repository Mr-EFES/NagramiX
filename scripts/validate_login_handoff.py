#!/usr/bin/env python3
"""Validate the login overlay boundary and fail-closed guards, not device behavior."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "submodules/TelegramCore/Sources/Account/Account.swift"
CONTEXT = "submodules/TelegramUI/Sources/SharedAccountContext.swift"


def snapshot(folder):
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


def validate(before, after):
    spec = importlib.util.spec_from_file_location("features", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original, result = snapshot(before), snapshot(after)
    assert original.keys() == result.keys(), "Native file set changed"
    assert {name for name in original if original[name] != result[name]} == {ACCOUNT, CONTEXT}

    function = next(node for node in ast.parse((ROOT / "ios/apply_features.py").read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "apply_login_postbox_handoff")
    expression = next(node.value for node in function.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "substitutions" for target in node.targets))
    patches = eval(compile(ast.Expression(expression), "<login-overlay>", "eval"),
                   {"__builtins__": {}}, {"account": ACCOUNT, "context": CONTEXT})
    restored = {name: (after / name).read_text() for name in (ACCOUNT, CONTEXT)}
    for name, old, new in reversed(patches):
        assert restored[name].count(new) == 1, name
        restored[name] = restored[name].replace(new, old, 1)
    for name in restored:
        assert restored[name].encode() == (before / name).read_bytes(), name

    # Both inputs must pass before either is written. Include drift in the second
    # file and a second invocation, so partial application cannot go unnoticed.
    for drift in (ACCOUNT, CONTEXT, None):
        with tempfile.TemporaryDirectory(prefix="nagramix-login-guards-") as directory:
            tree = Path(directory)
            for name in (ACCOUNT, CONTEXT):
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((before / name).read_bytes())
            if drift is None:
                module.apply_login_postbox_handoff(tree)
                for name in (ACCOUNT, CONTEXT):
                    assert (tree / name).read_bytes() == (after / name).read_bytes()
            else:
                with (tree / drift).open("a") as stream:
                    stream.write("\n// simulated upstream drift\n")
            previous = snapshot(tree)
            try:
                module.apply_login_postbox_handoff(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Drift or reapplication was accepted")
            assert snapshot(tree) == previous, "Input failure changed a native file"
    print("PASS: only Account/SharedAccountContext changed; reversibility and atomic guards verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    validate(args.before, args.after)

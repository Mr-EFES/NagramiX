#!/usr/bin/env python3
"""Проверить интеграцию исправления picker: область изменений и отказ без записи."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HELPER = "apply_notification_exception_picker_lifecycle"


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before: Path, after: Path) -> dict:
    tree = ast.parse((ROOT / "ios/apply_features.py").read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == HELPER)
    values = {}
    for node in helper.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("picker", "patches"):
                values[node.targets[0].id] = eval(
                    compile(ast.Expression(node.value), "<patches>", "eval"),
                    {"__builtins__": {}}, values)
    patches = values["patches"]
    previous, current = hashes(before), hashes(after)
    assert previous.keys() == current.keys(), "Изменился состав файлов"
    changed = sorted(name for name in previous if previous[name] != current[name])
    assert changed == sorted(patches), changed
    reversals = 0
    for name, (digest, replacements) in patches.items():
        assert previous[name] == digest, name
        restored = (after / name).read_text()
        for old, new in reversed(replacements):
            assert restored.count(new) == 1, name
            restored = restored.replace(new, old, 1)
            reversals += 1
        assert restored.encode() == (before / name).read_bytes(), name

    entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_features")
    calls = [n.func.id for n in ast.walk(entry) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.count(HELPER) == 1
    assert calls.index("apply_notification_exception_peer_picker") < calls.index(HELPER)
    assert calls.index("apply_directional_swipe_picture_in_picture") < calls.index(HELPER)
    spec = importlib.util.spec_from_file_location("exception_lifecycle", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = 0
    scenarios = [("clean", None), ("rerun", None)]
    scenarios += [(kind, name) for kind in ("drift", "missing") for name in patches]
    for kind, target in scenarios:
        with tempfile.TemporaryDirectory(prefix="nagramix-exception-lifecycle-") as folder:
            fixture = Path(folder)
            for name in patches:
                path = fixture / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(((after if kind == "rerun" else before) / name).read_bytes())
            if kind == "drift":
                with (fixture / target).open("ab") as file:
                    file.write(b"\n// unexpected native drift\n")
            elif kind == "missing":
                (fixture / target).unlink()
            initial = hashes(fixture)
            if kind == "clean":
                getattr(module, HELPER)(fixture)
                assert hashes(fixture) == {name: current[name] for name in patches}
            else:
                try:
                    getattr(module, HELPER)(fixture)
                except (SystemExit, FileNotFoundError):
                    assert hashes(fixture) == initial, "Частичная запись при отказе"
                    rejected += 1
                else:
                    raise AssertionError(f"Принят неверный вход: {kind}, {target}")
    return {
        "outputs": len(current), "changed": changed,
        "byte_identical": len(current) - len(changed),
        "exact_reverse_patches": reversals,
        "clean_integration": "PASS", "rejected_without_partial_writes": rejected,
        "native_compile": "pending", "postbox_uikit_device": "not_executed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = json.dumps(validate(args.before, args.after), ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(result)
    print(result, end="")

#!/usr/bin/env python3
"""Verify exact root-search overlay scope and guards; does not execute UIKit."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_global_tab_search_fix")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    # Native paths in the patch list are local names, not computed runtime paths.
    patches = []
    native_names = dict(zip(("root", "controller", "node"), guards))
    for item in assignments["patches"].elts:
        path, old, new = item.elts
        patches.append((native_names[path.id], ast.literal_eval(old), ast.literal_eval(new)))
    assert len(patches) == 13
    assert before.keys() == after.keys(), "Unexpected added/removed output"
    assert {n for n in before if before[n] != after[n]} == set(guards), "Unexpected native scope"
    restored = {n: after[n].decode() for n in guards}
    for name, old, new in reversed(patches):
        assert restored[name].count(new) == 1
        restored[name] = restored[name].replace(new, old, 1)
    for name, digest in guards.items():
        assert restored[name].encode() == before[name], "Unreviewed native change"
        assert hashlib.sha256(before[name]).hexdigest() == digest

    root, controller, node = (after[n].decode() for n in guards)
    assert "self?.openChatsController(activateSearch: true)" in root
    assert "public weak var nagramiXGlobalSearchController: ViewController?" in controller
    assert "let activateGlobalSearch = self.nagramiXActivateGlobalSearch" in controller
    assert "self.currentController?.tabBarActivateSearch()" in controller, "Generic native fallback lost"
    assert "self.currentController?.tabBarDeactivateSearch()" in controller
    assert "[weak self]" in controller and "[weak self]" in root
    params = node[node.index("private struct Params: Equatable"):node.index("private struct LayoutResult")]
    for flag in ("nagramiXShowSearchButton", "nagramiXHasGlobalSearch", "nagramiXIsGlobalSearchController"):
        assert f"let {flag}: Bool" in params
        assert f"self.{flag} = {flag}" in params
    assert "nagramiXShowSearchButton: NagramiXTabSettings.current.showSearchButton" in node
    assert "params.nagramiXHasGlobalSearch || params.currentControllerSearchState != nil" in node
    assert "!params.nagramiXHasGlobalSearch || params.nagramiXIsGlobalSearchController" in node
    assert "search: self.currentController?.tabBarSearchState.flatMap" not in node
    # Exact reversal also preserves the entire tab list/selection calculation,
    # theme/keyboard/toolbar paths, preference keys/defaults and previous PiP fix.
    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-search-", dir="/workspace") as directory:
            tree = Path(directory)
            initial = {}
            for name in guards:
                data = after[name] if scenario == "rerun" else before[name]
                if scenario == name:
                    data += b"\n// Unexpected native change\n"
                initial[name] = data
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if scenario == "clean":
                module.apply_global_tab_search_fix(tree)
                assert all((tree / n).read_bytes() == after[n] for n in guards)
            else:
                try:
                    module.apply_global_tab_search_fix(tree)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift/rerun")
                assert all((tree / n).read_bytes() == initial[n] for n in guards), "Partial write after rejection"
    print("PASS: 3 native files, 13 exact reversals, global activation/cache visibility; 3 SHA drift/rerun guards without partial writes")
    print("Not verified: Apple SDK build or search interaction on physical iPhone")


if __name__ == "__main__":
    main()

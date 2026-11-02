#!/usr/bin/env python3
"""Verify the unread-folder overlay's immutable inputs and reversible boundaries.
This is source integration validation, not a substitute for an Apple SDK build.
"""
import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--audited-native', required=True, type=Path)
    args = parser.parse_args()
    overlay = ROOT / 'ios/apply_features.py'
    tree = ast.parse(overlay.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_unread_chats_first')
    expected = ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    names = {n.targets[0].id: ast.literal_eval(n.value) for n in function.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant)}
    patches = []
    for node in function.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'patch':
            name, old, new = node.value.args
            patches.append((names[name.id], ast.literal_eval(old), ast.literal_eval(new)))
    spec = importlib.util.spec_from_file_location('nagramix_overlay', overlay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-unread-validation-') as folder:
        fixture = Path(folder)
        originals = {}
        for name, digest in expected.items():
            candidate = args.baseline / name
            if not candidate.exists():
                candidate = args.audited_native / name
            data = candidate.read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest, name
            originals[name] = data
            target = fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        module.apply_unread_chats_first(fixture, ROOT / 'ios')
        outputs = {n: (fixture / n).read_bytes() for n in expected}
        reversed_texts = {n: d.decode() for n, d in outputs.items()}
        for name, inc in [('ChatListNodeLocation.swift', 'NagramiXUnreadChatListView.swift.inc'), ('ChatListNodeEntries.swift', 'NagramiXUnreadChatListEntries.swift.inc')]:
            key = 'submodules/ChatListUI/Sources/Node/' + name
            suffix = '\n' + (ROOT / 'ios/Sources/ChatListUI' / inc).read_text()
            assert reversed_texts[key].endswith(suffix)
            reversed_texts[key] = reversed_texts[key][:-len(suffix)]
        for name, old, new in reversed(patches):
            assert reversed_texts[name].count(new) == 1, (name, new)
            reversed_texts[name] = reversed_texts[name].replace(new, old)
        assert all(reversed_texts[n].encode() == originals[n] for n in expected)
        # Every drift, plus accidental reapplication, must fail before writes.
        cases = [('rerun', outputs)]
        for name in expected:
            cases.append((name, {n: d + (b'\n// drift\n' if n == name else b'') for n, d in originals.items()}))
        for label, inputs in cases:
            for name, data in inputs.items():
                (fixture / name).write_bytes(data)
            try:
                module.apply_unread_chats_first(fixture, ROOT / 'ios')
            except SystemExit:
                pass
            else:
                raise AssertionError('Unsafe patch accepted: ' + label)
            assert all((fixture / n).read_bytes() == d for n, d in inputs.items())
        print(f'{len(patches)} exact reverse patches; {len(cases)} drift/rerun refusals before writes: PASS')


if __name__ == '__main__':
    main()

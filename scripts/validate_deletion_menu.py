#!/usr/bin/env python3
"""Check deletion overlay scope and fail-closed anchors; does not render UIKit."""

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
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_full_name_deletion_menu")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    name, digest, patches = (ast.literal_eval(assignments[k]) for k in ("name", "digest", "patches"))
    assert len(patches) == 18
    assert before.keys() == after.keys(), "Unexpected added/removed output"
    assert {n for n in before if before[n] != after[n]} == {name}, "Unexpected native scope"
    assert hashlib.sha256(before[name]).hexdigest() == digest
    replay = before[name].decode()
    steps = []
    for old, new in patches:
        assert replay.count(old) == 1
        steps.append((replay.index(old), old, new))
        replay = replay.replace(old, new, 1)
    assert replay.encode() == after[name], "Unreviewed native change"
    restored = after[name].decode()
    for offset, old, new in reversed(steps):
        assert restored[offset:offset + len(new)] == new
        restored = restored[:offset] + old + restored[offset + len(new):]
    assert restored.encode() == before[name], "Exact reversal failed"

    old = before[name].decode()
    new = after[name].decode()
    start = "    func presentDeleteMessageOptions("
    end = "    func presentClearCacheSuggestion()"
    assert old[:old.index(start)] == new[:new.index(start)], "Deletion backend/undo changed"
    assert old[old.index(end):] == new[new.index(end):], "Other chat operations changed"
    # Financial and repeating-message warnings still have their native extra semantics.
    marker = "            var personalPeerName: String?"
    assert old[old.index(start):old.index("            let actionSheet =", old.index(start))] == new[new.index(start):new.index(marker, new.index(start))]
    menu = new[new.index(marker, new.index(start)):new.index(end)]
    assert "compactDisplayTitle" not in menu
    assert menu.count("displayTitle(strings: self.presentationData.strings, displayOrder: self.presentationData.nameDisplayOrder)") == 2
    assert "ActionSheet" not in menu and "canDisplayContextMenu" not in menu
    for line in menu.splitlines():
        if "ContextMenuActionItem(" in line:
            assert "textLayout: .multiline" in line, "Limited deletion label"
    assert "nagramiXSelectedDeletionWarning(messageIds.count)" in menu
    assert "nagramiXLocalCopiesDeletionWarning(archivedCount)" in menu
    assert "sourceView ?? self.chatDisplayNode.view" in menu
    assert "type: .forLocalPeer" in menu and "type: .forEveryone" in menu
    assert "options.contains(.unsendPersonal)" in menu
    assert "Chat_UnsendMyMessagesAlertTitle(personalPeerName" in menu
    assert "Chat_UnsendMyMessages, textColor: .destructive" in menu
    assert "unsendPersonalMessages" not in menu

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Drift/rerun must reject before any write, including minimal fixture invocation.
    for scenario in ("clean", "drift", "rerun"):
        with tempfile.TemporaryDirectory(prefix="nagramix-deletion-", dir="/workspace") as directory:
            tree = Path(directory)
            initial = after[name] if scenario == "rerun" else before[name]
            if scenario == "drift":
                initial += b"\n// Unexpected native change\n"
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(initial)
            if scenario == "clean":
                module.apply_full_name_deletion_menu(tree)
                assert target.read_bytes() == after[name]
            else:
                try:
                    module.apply_full_name_deletion_menu(tree)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift/rerun")
                assert target.read_bytes() == initial, "Partial write on rejection"
    print("PASS: 1 native file, 18 exact patches; deletion menu scope, permissions/undo boundaries, SHA drift/rerun guards")
    print("Not verified: Apple SDK build, rendered layout, physical iPhone deletion")


if __name__ == "__main__":
    main()

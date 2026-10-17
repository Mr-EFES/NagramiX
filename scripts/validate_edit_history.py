#!/usr/bin/env python3
"""Check the edit-history overlay against a supplied pre-change source fixture.

This checks patch isolation/fail-closed behavior, not UIKit or Apple SDK types.
Native revision-retention tests live in ios/Tests/TelegramCore.
"""
import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile


def digest_tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    overlay = root / "ios"
    module_spec = importlib.util.spec_from_file_location("features", overlay / "apply_features.py")
    features = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(features)
    menu = "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"
    state = "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift"
    ui = "submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift"
    tests = "submodules/TelegramCore/Tests/NagramiXEditHistoryTests.swift"
    # Locate the actual archive copy; its destination belongs to the older overlay.
    archives = list(args.after.rglob("NagramiXMessageArchive.swift"))
    assert len(archives) == 1
    core = str(archives[0].relative_to(args.after))
    old = digest_tree(args.before)
    new = digest_tree(args.after)
    changed = {p for p in old.keys() & new.keys() if old[p] != new[p]}
    expected_changed = {
        menu, state, core,
        "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
        "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings",
        "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings",
    }
    assert changed == expected_changed, changed
    assert new.keys() - old.keys() == {ui, tests}
    assert not old.keys() - new.keys()
    tree = ast.parse((overlay / "apply_features.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_edit_history_screen")
    replacements = {n.targets[0].id: ast.literal_eval(n.value) for n in function.body
                    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id in {"old", "new", "state_old", "state_new"}}
    result = (args.after / menu).read_text()
    assert result.count(replacements["new"]) == 1
    assert result.replace(replacements["new"], replacements["old"], 1) == (args.before / menu).read_text()
    # The archived branch still reuses the same action; all other menu callbacks
    # (including selection, saving, deletion and forwarding) are byte-identical.
    assert result.count("actions.append(editHistoryAction)") == 2
    state_result = (args.after / state).read_text()
    assert state_result.count(replacements["state_new"]) == 1
    assert state_result.replace(replacements["state_new"], replacements["state_old"], 1) == (args.before / state).read_text()
    before_insertion = replacements["state_new"].split("let _ = transaction.addMessages", 1)[0]
    assert "transaction.getMessage(id)" in before_insertion
    assert "messageArchive.capturesMessageEdits" in before_insertion
    assert "recordIncomingEdit(previousMessage: previousMessage" in before_insertion

    with tempfile.TemporaryDirectory(prefix="nagramix-edit-history-") as tmp:
        base = Path(tmp)
        scenarios = ["clean", "rerun", "input-drift", "state-drift", "ui-collision", "test-collision", "missing-helper"]
        for scenario in scenarios:
            case = base / scenario
            (case / menu).parent.mkdir(parents=True)
            shutil.copy2(args.before / menu, case / menu)
            (case / state).parent.mkdir(parents=True)
            shutil.copy2(args.before / state, case / state)
            if scenario == "input-drift":
                (case / menu).write_text((case / menu).read_text() + "\n// drift\n")
            if scenario == "state-drift":
                (case / state).write_text((case / state).read_text() + "\n// drift\n")
            if scenario in {"ui-collision", "test-collision"}:
                path = case / (ui if scenario == "ui-collision" else tests)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Existing file must survive")
            if scenario == "rerun":
                features.apply_edit_history_screen(case, overlay)
            before = digest_tree(case)
            target_overlay = overlay
            if scenario == "missing-helper":
                target_overlay = base / "missing-overlay"
                target_overlay.mkdir()
            try:
                features.apply_edit_history_screen(case, target_overlay)
            except SystemExit:
                assert scenario != "clean", scenario
                assert digest_tree(case) == before, scenario
            else:
                assert scenario == "clean", scenario
                assert (case / menu).read_bytes() == (args.after / menu).read_bytes()
                assert (case / state).read_bytes() == (args.after / state).read_bytes()
                assert (case / ui).read_bytes() == (overlay / "Sources/TelegramUI/NagramiXEditHistoryController.swift").read_bytes()

    archive = archives[0].read_text()
    assert archive == (overlay / "Sources/TelegramCore/NagramiXMessageArchive.swift").read_text()
    assert "revisions.remove" not in archive and "revisions.prefix" not in archive and "revisions.suffix" not in archive
    controller = (args.after / ui).read_text()
    assert controller == (overlay / "Sources/TelegramUI/NagramiXEditHistoryController.swift").read_text()
    assert "UITableView.automaticDimension" in controller
    assert "self.textView.isEditable = false" in controller
    assert "self.textView.isScrollEnabled = false" in controller
    assert "self.textView.isSelectable = canExport" in controller
    assert "storeMessageTextInPasteboard(revision.text, entities: revision.entities)" in controller
    assert "self.forwardRevision?([nagramiXEditHistorySnapshot" in controller
    snapshot = controller.split("func nagramiXEditHistorySnapshot", 1)[1].split("private final class", 1)[0]
    assert "withUpdatedText(revision.text).withUpdatedMedia([])" in snapshot
    assert "TextEntitiesMessageAttribute(entities: revision.entities)" in snapshot
    assert "NagramiXArchivedMessageAttribute(" in snapshot
    assert "withUpdatedFlags" not in snapshot  # Original protection survives.
    assert ".forward(source:" not in controller
    assert "self.updatesDisposable?.dispose()" in controller
    print(f"PASS: {len(changed)} changed, 2 added, {len(old) - len(changed)} unchanged outputs; 2 exact reversals; {len(scenarios)} patch scenarios")
    print("UIKit interaction / Apple SDK compilation / native XCTest execution still require macOS and iPhone.")


if __name__ == "__main__":
    main()

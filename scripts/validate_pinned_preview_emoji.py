#!/usr/bin/env python3
"""Validate the scoped pinned-emoji overlay; does not execute UIKit/XCTest."""
import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile


def digests(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    overlay = root / "ios"
    panel = "submodules/TelegramUI/Sources/ChatPinnedMessageTitlePanelNode.swift"
    helper = "submodules/TelegramStringFormatting/Sources/NagramiXPinnedPreviewEmoji.swift"
    tests = "submodules/TelegramStringFormatting/Tests/NagramiXPinnedPreviewEmojiTests.swift"
    old, new = digests(args.before), digests(args.after)
    changed = {p for p in old.keys() & new.keys() if old[p] != new[p]}
    assert changed == {panel}, changed
    assert new.keys() - old.keys() == {helper, tests}
    assert not old.keys() - new.keys()

    patcher = (overlay / "apply_features.py").read_text()
    function = next(n for n in ast.parse(patcher).body if isinstance(n, ast.FunctionDef) and n.name == "apply_pinned_preview_emoji")
    pairs = ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "replacements"))
    output = (args.after / panel).read_text()
    reversed_text = output
    for before, after in reversed(pairs):
        assert reversed_text.count(after) == 1, before[:80]
        reversed_text = reversed_text.replace(after, before, 1)
    assert reversed_text == (args.before / panel).read_text()

    spec = importlib.util.spec_from_file_location("features", overlay / "apply_features.py")
    features = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(features)
    scenarios = ["clean", "rerun", "source-drift", "helper-collision", "test-collision", "missing-helper", "missing-test"]
    with tempfile.TemporaryDirectory(prefix="nagramix-pinned-emoji-") as temporary:
        temporary = Path(temporary)
        for scenario in scenarios:
            source = temporary / scenario
            (source / panel).parent.mkdir(parents=True)
            shutil.copy2(args.before / panel, source / panel)
            origin = overlay
            if scenario == "source-drift":
                (source / panel).write_text((source / panel).read_text() + "\n// drift\n")
            if scenario in {"helper-collision", "test-collision"}:
                path = source / (helper if scenario == "helper-collision" else tests)
                path.parent.mkdir(parents=True)
                path.write_text("Existing source must survive")
            if scenario.startswith("missing-"):
                origin = temporary / (scenario + "-overlay")
                present = "Sources/TelegramStringFormatting/NagramiXPinnedPreviewEmoji.swift" if scenario == "missing-test" else "Tests/TelegramStringFormatting/NagramiXPinnedPreviewEmojiTests.swift"
                (origin / present).parent.mkdir(parents=True)
                shutil.copy2(overlay / present, origin / present)
            if scenario == "rerun":
                features.apply_pinned_preview_emoji(source, origin)
            snapshot = digests(source)
            try:
                features.apply_pinned_preview_emoji(source, origin)
            except SystemExit:
                assert scenario != "clean", scenario
                assert digests(source) == snapshot, scenario
            else:
                assert scenario == "clean", scenario
                for path in [panel, helper, tests]:
                    assert (source / path).read_bytes() == (args.after / path).read_bytes(), path

    for relative, origin in [(helper, "Sources/TelegramStringFormatting/NagramiXPinnedPreviewEmoji.swift"), (tests, "Tests/TelegramStringFormatting/NagramiXPinnedPreviewEmojiTests.swift")]:
        assert (args.after / relative).read_bytes() == (overlay / origin).read_bytes()
    # Original source/dates/translation/spoiler and action paths must remain
    # untouched. Only the two text layouts receive the hydrated attributed text.
    assert output.count("attributedString: nagramiXMessageText") == 2
    assert output.count("context.engine.stickers.resolveInlineStickers(fileIds: missingIds)") == 1
    assert "self.nagramiXEmojiGeneration == generation" in output
    assert "self.currentMessage?.message.id == messageId" in output
    assert "self.nagramiXEmojiDisposable.dispose()" in output
    assert "self.nagramiXEmojiFiles.removeAll()" in output
    assert "self.nagramiXEmojiInterfaceState = interfaceState" in output
    assert "self.enqueueTransition(width: layout.0, panelHeight: 50.0" in output
    assert "pinnedMessage: currentMessage, theme: interfaceState.theme" in output
    print(f"PASS: {len(pairs)} exact reversals, {len(scenarios)} patch scenarios; 1 changed / 2 added / {len(old) - 1} unchanged outputs")
    print("Native XCTest, Apple SDK compilation and physical iPhone remain pending.")


if __name__ == "__main__":
    main()

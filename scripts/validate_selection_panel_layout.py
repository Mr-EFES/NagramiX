#!/usr/bin/env python3
"""Check selection-panel layout integration; no UIKit execution is claimed."""

import argparse
import ast
import hashlib
import importlib.util
import math
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NATIVE = "submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift"


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    assert before.keys() == after.keys(), "Unexpected added/removed overlay output"
    assert {n for n in before if before[n] != after[n]} == {NATIVE}, "Changes outside selection panel"
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_selection_panel_layout_fix")
    patches = ast.literal_eval(next(n.value for n in helper.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "patches" for t in n.targets)))
    original, changed = (args.before / NATIVE).read_text(), (args.after / NATIVE).read_text()
    restored = changed
    for old, new in reversed(patches):
        assert restored.count(new) == 1
        restored = restored.replace(new, old, 1)
    assert restored == original, "Unexplained native delta"

    # A pending update must discard permissions and cancel stale work. The one
    # retained bit controls visibility only; it never substitutes old actions.
    start = changed.index("    private func updateActions() {")
    end = changed.index("    public func updateTheme(", start)
    actions = changed[start:end]
    assert actions.index("self.actions = nil") < actions.index("let selectedIds = self.selectedMessages")
    assert "if self.selectedMessages.isEmpty {\n            self.nagramiXHasActionLayout = false" in actions
    for name in ("deleteButton", "reportButton", "tagButton", "tagEditButton"):
        assert f"self.{name}.isEnabled = false" in actions
    for name in ("forwardButton", "shareButton", "forwardWithoutSourceButton", "broadcastButton"):
        assert f"self.{name}.isImplicitlyDisabled = true" in actions
    for contract in (
        "self.nagramiXSelectionGeneration &+= 1",
        "self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds",
        "self.nagramiXTransferDisposable.set(nil)",
        "self.canDeleteMessagesDisposable.set(nil)",
        "messages.count == selectedIds.count",
        "options.formUnion(resolvedActions.options.intersection([.forward, .externalShare]))",
    ):
        assert contract in actions
    pending = changed[changed.index("        } else {\n            self.deleteButton.isEnabled = false", end):]
    pending = pending[:pending.index("        let transferSettings")]
    gate = pending.index("if !self.nagramiXHasActionLayout || self.selectedMessages.isEmpty {")
    assert ".isHidden =" not in pending[:gate], "Pending selection removes visible slots"
    assert "self.nagramiXHasActionLayout = true" in changed
    assert "self.tagButton.isEnabled = actions.setTag" in changed
    assert "self.tagEditButton.isEnabled = actions.setTag" in changed
    assert "transition.updateFrame(view: button, frame: buttonFrame)" not in changed
    assert "button.layer.removeAnimation(forKey: \"position\")" in changed
    assert "button.layer.removeAnimation(forKey: \"bounds\")" in changed
    assert "ContainedViewLayoutTransition.immediate.updateFrame(view: button, frame: buttonFrame)" in changed
    assert "size: buttonFrame.size, transition: .immediate)" in changed
    assert "self.buttonScrollView.convert(tagButton.frame, to: self.view)" in changed
    assert "self.buttonScrollView.setContentOffset(CGPoint(x: maximumOffset, y: 0.0), animated: false)" in changed

    # Bounds proof for the unchanged spacing algorithm, including narrow
    # viewports, every optional action, landscape and scroll offset clamping.
    geometry = 0
    for available in (0.0, 180.0, 240.0, 280.0, 304.0, 343.0, 374.0, 398.0, 600.0, 844.0):
        for count in range(3, 8):
            content = max(available, 40.0 * count + 8.0 * (count - 1))
            spacing = max(8.0, math.floor((content - 40.0 * count) / (count - 1)))
            frames = [(i * (40.0 + spacing), 40.0) for i in range(count - 1)] + [(content - 40.0, 40.0)]
            assert all(frames[i + 1][0] - frames[i][0] - 40.0 >= 8.0 for i in range(count - 1))
            assert frames[0][0] == 0.0 and frames[-1][0] + 40.0 == content
            assert 0.0 <= min(content, max(0.0, content - available)) <= content
            geometry += 1

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "drift", "anchor-drift"):
        with tempfile.TemporaryDirectory(prefix="nagramix-selection-layout-") as folder:
            root = Path(folder)
            path = root / NATIVE
            path.parent.mkdir(parents=True)
            text = changed if scenario == "rerun" else original
            if scenario == "drift":
                text += "\n// Unexpected drift\n"
            elif scenario == "anchor-drift":
                text = text.replace("self.actions = nil", "self.actions = actions", 1)
            path.write_text(text)
            snapshot = path.read_bytes()
            if scenario == "clean":
                module.apply_selection_panel_layout_fix(root)
                assert path.read_text() == changed
            else:
                try:
                    module.apply_selection_panel_layout_fix(root)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted " + scenario)
                assert path.read_bytes() == snapshot, "Partial write on rejection"
    print(f"PASS: {len(after)} outputs, only selection panel changed; 6 exact reversals, pending-visibility/permission contracts, {geometry} bounds cases, 4 guard cases")
    print("Not executed: native Swift typecheck or UIKit animation/input on iPhone")


if __name__ == "__main__":
    main()

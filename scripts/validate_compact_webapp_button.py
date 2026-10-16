#!/usr/bin/env python3
"""Verify compact mini-app geometry contracts; no UIKit execution is claimed."""

import argparse
import ast
import hashlib
import importlib.util
import math
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NATIVE = "submodules/ChatListUI/Sources/Node/ChatListItem.swift"


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def geometry_contracts():
    cases = inline_cases = stacked_cases = previous_clipping = 0
    # Measured text sizes are inputs to this bounds model. It does not pretend
    # to measure UIFont or execute the Swift renderer/gesture recognizers.
    for width in (190.0, 218.0, 242.0, 280.0, 320.0, 380.0, 640.0):
        for font in (14.0, 17.0, 20.0, 24.0, 30.0):
            scale = font / 17.0
            top = math.floor(5.0 * font / 17.0)
            side = math.floor(font * 12.0 / 17.0)
            button_height = math.ceil(18.0 * scale) + math.floor(font * 5.0 / 17.0) + math.floor(font * 4.0 / 17.0)
            button_width = 54.0 * scale + side * 2.0
            for date_width in (24.0 * scale, 40.0 * scale, 55.0 * scale):
                for pin_width in (0.0, 16.0 * scale):
                    for status_width in (0.0, 24.0):
                        for screen_scale in (2.0, 3.0):
                            title_icons = 14.0 * scale
                            date_height = math.ceil(14.0 * scale)
                            badge = pin_width + 5.0 if pin_width else 0.0
                            badge += (4.0 if badge else 5.0) + button_width
                            column = badge + 4.0
                            inline = width - date_width - 10.0 - status_width - title_icons - column >= math.floor(40.0 * font / 17.0)
                            date_inset = column if inline else 0.0
                            title_height = math.ceil(18.0 * scale)
                            preview_height = math.ceil(18.0 * scale)
                            base_height = max(48.0, math.ceil(top + title_height - 2.0 + preview_height + top))
                            height = max(base_height, math.ceil(button_height + top * 2.0))
                            if not inline:
                                bottom = top + 2.0 + date_height + math.floor(font * 4.0 / 17.0) + 4.0 + button_height
                                height = max(height, math.ceil(bottom + top))
                            date_bottom = top + 2.0 + date_height
                            if inline:
                                button_y = math.floor((height - button_height) * 0.5 * screen_scale) / screen_scale
                                assert abs(button_y + button_height * 0.5 - height * 0.5) <= 1.0 / screen_scale
                                inline_cases += 1
                            else:
                                centered = top + math.floor((height - top * 2.0 - button_height) * 0.5)
                                button_y = max(centered, date_bottom + math.floor(font * 4.0 / 17.0)) + 4.0
                                stacked_cases += 1
                            button_x = width - (pin_width + 6.0 if pin_width else 0.0) - button_width
                            assert button_x >= 0.0
                            assert top <= button_y and button_y + button_height <= height - top + 1e-6
                            date_right = width - date_inset
                            assert date_right <= button_x or date_bottom <= button_y, "Date overlaps launch button"
                            assert width - badge <= button_x, "Preview overlaps launch button"
                            # The native button view receives precisely this
                            # fully contained frame; its center is hittable.
                            assert 0.0 < button_x + button_width * 0.5 < width
                            assert 0.0 < button_y + button_height * 0.5 < height
                            old_y = max(top + math.floor((base_height - top * 2.0 - button_height) * 0.5), date_bottom + math.floor(font * 4.0 / 17.0)) + 4.0
                            previous_clipping += old_y + button_height > base_height
                            cases += 1
    assert inline_cases > 0 and stacked_cases > 0 and previous_clipping > 0
    return cases, inline_cases, stacked_cases, previous_clipping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == {NATIVE}
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_compact_webapp_button_layout")
    patches = ast.literal_eval(next(n.value for n in helper.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "patches" for t in n.targets)))
    original, changed = (args.before / NATIVE).read_text(), (args.after / NATIVE).read_text()
    restored = changed
    for old, new in reversed(patches):
        assert restored.count(new) == 1
        restored = restored.replace(new, old, 1)
    assert restored == original
    assert "if nagramiXCompact, let (buttonTitleLayout, _) = actionButtonTitleNodeLayoutAndApply" in changed
    assert "nagramiXCompactActionSize?.width ?? (actionButtonTitleNodeLayout.size.width + 12.0 * 2.0)" in changed
    assert "nagramiXCompactActionSize != nil ? badgeSize + 4.0 : 0.0" in changed
    assert "titleRectWidth -= nagramiXActionDateInset" in changed
    for token in ("dateLayout.size.width - nagramiXActionDateInset", "dateIconImage.size.width - nagramiXActionDateInset", "statusOffset - nagramiXActionDateInset"):
        assert token in changed
    assert "actionButtonNode.frame = actionButtonFrame" in changed
    assert "actionButtonNode.isUserInteractionEnabled = true" in changed
    assert "#selector(strongSelf.actionButtonPressed), forControlEvents: .touchUpInside" in changed
    assert "item.interaction.openWebApp(user)" in changed
    assert "let contentRect = rawContentRect.offsetBy(dx: editingOffset + leftInset + revealOffset, dy: 0.0)" in changed
    cases = geometry_contracts()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "drift", "anchor-drift"):
        with tempfile.TemporaryDirectory(prefix="nagramix-compact-webapp-") as folder:
            root = Path(folder)
            path = root / NATIVE
            path.parent.mkdir(parents=True)
            text = changed if scenario == "rerun" else original
            if scenario == "drift":
                text += "\n// Unexpected native drift\n"
            elif scenario == "anchor-drift":
                text = text.replace("var badgeSize: CGFloat = 0.0", "var badgeSize: CGFloat = 1.0", 1)
            path.write_text(text)
            snapshot = path.read_bytes()
            if scenario == "clean":
                module.apply_compact_webapp_button_layout(root)
                assert path.read_text() == changed
            else:
                try:
                    module.apply_compact_webapp_button_layout(root)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted native drift/reapplication")
                assert path.read_bytes() == snapshot
    print(f"PASS: {len(after)} outputs, only ChatListItem changed; {len(patches)} exact reversals, 4 guard cases; geometry total/inline/stacked/old-clipped={cases}")
    print("Not executed: Apple SDK typecheck, UIKit rendering or physical mini-app taps")


if __name__ == "__main__":
    main()

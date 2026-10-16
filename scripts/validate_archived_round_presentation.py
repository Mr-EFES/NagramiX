#!/usr/bin/env python3
"""Verify the archive-circle presentation scope and fail-closed integration.

Source checks only: this does not execute UIKit, the decoder or an iPhone test.
Pass complete overlay output trees before and after the presentation change.
"""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NATIVE = "submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift"


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    assert set(before) == set(after), "Unexpected added/removed overlay outputs"
    assert {n for n in before if before[n] != after[n]} == {NATIVE}, "Changes outside round presentation"
    patcher = ROOT / "ios/apply_features.py"
    tree = ast.parse(patcher.read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_archived_round_presentation_fix")
    patches = ast.literal_eval(next(n.value for n in helper.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "patches" for t in n.targets)))
    original = (args.before / NATIVE).read_text()
    changed = (args.after / NATIVE).read_text()
    restored = changed
    for old, new in reversed(patches):
        if new:
            assert restored.count(new) == 1
            restored = restored.replace(new, old, 1)
        else:
            anchor = "                            strongSelf.bubbleBackgroundNode?.layer.mask = strongSelf.maskLayer\n"
            assert restored.count(anchor) == 1
            restored = restored.replace(anchor, old + anchor, 1)
    assert restored == original, "Unexplained native delta"

    # Both deletion and view-once snapshots share this attribute. A retained
    # circle gets the native free style; expanded transcription and ordinary
    # messages retain .never. No separate player or geometry is introduced.
    assert "let nagramiXArchivedCircle = !isExpanded && item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })" in changed
    assert "hidesBackground: nagramiXArchivedCircle ? .always : .never" in changed
    assert "nagramiXMaskAnimator" not in changed and "nagramiXArchivedMask" not in changed
    assert "strongSelf.maskForeground.removeAllAnimations()" not in changed
    for line in (
        "animation.animator.updateCornerRadius(layer: strongSelf.maskForeground,",
        "animation.animator.updateFrame(layer: strongSelf.maskForeground,",
        "animation.animator.updateFrame(layer: strongSelf.backdropMaskForeground,",
        "animator: animation.animator",
    ):
        assert line in changed

    # Verify the real parent still consumes .always through backgroundType.none;
    # its group compositing, footer and interactions must be byte-identical.
    parent = "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"
    text = (args.after / parent).read_text()
    assert "case .always:\n                        backgroundHiding = .always" in text
    assert "if hideBackground {\n            backgroundType = .none" in text
    assert "let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0" in text
    assert "strongSelf.clippingNode.layer.allowsGroupOpacity = true" in text
    for component in ("backgroundNode", "backgroundWallpaperNode", "shadowNode"):
        assert "strongSelf." + component + ".setType(type: backgroundType," in text

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "drift", "anchor-drift"):
        with tempfile.TemporaryDirectory(prefix="nagramix-round-presentation-") as folder:
            root = Path(folder)
            path = root / NATIVE
            path.parent.mkdir(parents=True)
            data = changed if scenario == "rerun" else original
            if scenario == "drift":
                data += "\n// Unexpected native drift\n"
            elif scenario == "anchor-drift":
                data = data.replace("hidesBackground: .never", "hidesBackground: .always", 1)
            path.write_text(data)
            snapshot = path.read_bytes()
            if scenario == "clean":
                module.apply_archived_round_presentation_fix(root)
                assert path.read_text() == changed
            else:
                try:
                    module.apply_archived_round_presentation_fix(root)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted " + scenario)
                assert path.read_bytes() == snapshot, "Partial write on rejection"
    print(f"PASS: {len(after)} outputs, only round presentation changed; exact reversal, native background-free path, 50% parent/footer preserved, 4 guard cases")
    print("Not executed: Apple SDK compilation or iPhone playback/animation")


if __name__ == "__main__":
    main()

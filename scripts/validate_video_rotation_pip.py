#!/usr/bin/env python3
"""Check the bounded PiP integration diff; not an AVKit or iPhone runtime test."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    assert before.keys() == after.keys(), "Unexpected file addition/removal"
    assert [name for name in before if before[name] != after[name]] == [TARGET], "Unexpected scope"
    patcher = ROOT / "ios/apply_features.py"
    tree = ast.parse(patcher.read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_video_rotation_pip_lifetime_fix")
    patches = next(ast.literal_eval(n.value) for n in helper.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "patches" for t in n.targets))
    assert len(patches) == 9
    restored = after[TARGET].decode()
    for old, new in reversed(patches):
        assert restored.count(new) == 1
        restored = restored.replace(new, old, 1)
    assert restored.encode() == before[TARGET], "Unreviewed native changes"
    assert hashlib.sha256(before[TARGET]).hexdigest() == "f06ec98b6002eb52386eba27c2e756adcf4675d5ad9d357f1062ac0047412114"

    text = after[TARGET].decode()
    # A playback status update must not register an AVKit adapter. Only explicit
    # swipe/button paths can prepare it; the original paths remain byte-identical.
    status_start = text.index("strongSelf.playerStatusValue = value")
    assert "setupNativePictureInPicture()" not in text[status_start:status_start + 650]
    assert text.count("self.setupNativePictureInPicture()") == 2
    assert "guard self.nativePictureInPictureContent == nil," in text
    assert "self.node.getVideoLayer() === sourceLayer" in text
    cleanup = text.index("controller.contentSource = nil")
    assert cleanup < text.index("self.pictureInPictureController = nil", cleanup)
    assert cleanup < text.index("self.nagramiXPictureInPictureLayer = nil", cleanup)
    assert "controller.delegate = nil" in text[:cleanup]
    assert "self.nagramiXPictureInPictureLayer = videoLayer" in text
    assert "let deadline = CACurrentMediaTime() + 2.0" in text
    assert "self.nagramiXPendingPiPStart == requestId" in text
    assert "UIApplication.shared.applicationState == .active" in text
    assert "[weak self, weak content]" in text
    assert "if !isCentral {\n            self.nagramiXCancelPendingPiPStart()" in text
    assert "self.nativePictureInPictureContent === content" in text
    # Reverse scope proves layout/rotation/decoder/seek/background and all other
    # functions have not acquired any unrelated modifications.
    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "drift", "rerun"):
        with tempfile.TemporaryDirectory(prefix="nagramix-pip-", dir="/workspace") as folder:
            target = Path(folder) / TARGET
            target.parent.mkdir(parents=True)
            initial = before[TARGET] if scenario != "rerun" else after[TARGET]
            if scenario == "drift":
                initial += b"\n// Unexpected upstream change\n"
            target.write_bytes(initial)
            if scenario == "clean":
                module.apply_video_rotation_pip_lifetime_fix(Path(folder))
                assert target.read_bytes() == after[TARGET]
            else:
                try:
                    module.apply_video_rotation_pip_lifetime_fix(Path(folder))
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Guard accepted drift or repeated application")
                assert target.read_bytes() == initial, "Partial write on rejection"
    print("PASS: one native file, 9 exact reversals, lazy PiP/source cleanup/readiness cancellation; SHA drift/rerun rejected without writes")
    print("Not checked: Apple SDK compilation, AVKit rotation/PiP lifecycle on iPhone")


if __name__ == "__main__":
    main()

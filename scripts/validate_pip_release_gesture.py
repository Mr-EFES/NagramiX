#!/usr/bin/env python3
"""Проверить текущий источник PiP, единый ended-путь и отказ без частичной записи."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
C = "submodules/GalleryUI/Sources/GalleryControllerNode.swift"
I = "submodules/GalleryUI/Sources/GalleryItemNode.swift"
V = "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"
POLICY = "submodules/GalleryUI/Sources/NagramiXPiPReleaseDecision.swift"
SOURCES = {
    "previous_gesture": "Sources/GalleryUI/NagramiXResponsivePiPSwipe.swift.inc",
    "previous_source": "Sources/GalleryUI/NagramiXPiPSourceReadiness.swift.inc",
    "__GESTURE__": "Sources/GalleryUI/NagramiXReleasePiPGesture.swift.inc",
    "__SOURCE__": "Sources/GalleryUI/NagramiXCurrentPiPSource.swift.inc",
}
ORIGIN = "Sources/GalleryUI/NagramiXPiPReleaseDecision.swift"


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before: Path, after: Path, swiftc: Path | None):
    a, b = hashes(before), hashes(after)
    assert b.keys() - a.keys() == {POLICY} and not a.keys() - b.keys()
    changed = {n for n in a if a[n] != b[n]}
    assert changed == {C, I, V}, changed
    assert (after / POLICY).read_bytes() == (ROOT / "ios" / ORIGIN).read_bytes()
    tree = ast.parse((ROOT / "ios/apply_features.py").read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_pip_release_gesture_fix")
    assignments = {n.targets[0].id: n.value for n in helper.body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    assert guards == {n: a[n] for n in guards}
    templates = {n: (ROOT / "ios" / path).read_text().rstrip("\n") + "\n\n" for n, path in SOURCES.items()}

    def literal(n):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name) and n.id in templates: return templates[n.id]
        if isinstance(n, (ast.List, ast.Tuple)): return [literal(e) for e in n.elts]
        raise AssertionError(ast.dump(n))

    patches = literal(assignments["patches"])
    restored = {n: (after / n).read_text() for n in guards}
    for name, old, new in reversed(patches):
        for marker in ("__GESTURE__", "__SOURCE__"): new = new.replace(marker, templates[marker])
        assert restored[name].count(new) == 1, (name, new[:80])
        restored[name] = restored[name].replace(new, old, 1)
    assert all(restored[n].encode() == (before / n).read_bytes() for n in guards)
    entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_features")
    calls = [n.func.id for n in ast.walk(entry) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.count(helper.name) == 1 and calls.index(helper.name) > calls.index("apply_pip_swipe_readiness_followup")
    spec = importlib.util.spec_from_file_location("release_pip", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary); fixture = root / "native"; overlay = root / "ios"

        def seed():
            for path in (fixture, overlay):
                if path.exists(): shutil.rmtree(path)
            for n in guards:
                p = fixture / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((before / n).read_bytes())
            for n in [*SOURCES.values(), ORIGIN]:
                p = overlay / n; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / "ios" / n, p)

        def reject(label):
            previous = hashes(fixture)
            try: module.apply_pip_release_gesture_fix(fixture, overlay)
            except (SystemExit, FileNotFoundError):
                assert hashes(fixture) == previous, label
                rejected.append(label)
            else: raise AssertionError("Принято некорректное состояние: " + label)

        seed(); module.apply_pip_release_gesture_fix(fixture, overlay)
        assert all((fixture / n).read_bytes() == (after / n).read_bytes() for n in [*guards, POLICY])
        reject("повторное применение")
        seed(); (fixture / C).write_bytes((after / C).read_bytes()); reject("частичный overlay")
        seed(); (fixture / POLICY).write_text("collision"); reject("коллизия policy")
        for n in guards:
            seed(); p = fixture / n; p.write_bytes(p.read_bytes() + b"\n// drift\n"); reject("drift " + n)
            seed(); (fixture / n).unlink(); reject("отсутствует " + n)
        for n in [*SOURCES.values(), ORIGIN]:
            seed(); (overlay / n).unlink(); reject("отсутствует " + n)

    controller, video = (after / C).read_text(), (after / V).read_text()
    gesture = templates["__GESTURE__"]
    assert "item.view.transform" not in gesture and "item.view.layer" not in gesture
    assert "nagramiXPiPSwipeView.transform" in gesture
    pan = gesture.split("    @objc private func nagramiXDirectionalPiPPan")[1]
    assert "prepareForPictureInPictureSwipe" not in pan
    assert pan.count("self.nagramiXCommitDirectionalPiPSwipe(item)") == 1
    assert pan.index("guard gesture.state == .ended") < pan.index("self.nagramiXCommitDirectionalPiPSwipe(item)")
    assert "x: translation.x, y: translation.y" in pan and "let limit" not in pan
    assert "touch.timestamp" in gesture and "nagramiXBlocksPiPSourcePan" in gesture
    assert "nagramiXStartSwipePictureInPicture" not in video
    assert "nagramiXCommitSwipePiP" not in controller
    assert "nagramiXPreparedSwipePiPItem" not in controller
    assert "override var nagramiXPiPSwipeView: UIView { return self.scrollNode.view }" in video
    assert "self.pictureInPictureNode == nil, self.videoNode?.ownsContentNode == true" in video
    assert "guard self.node === videoNode" in video and "videoNode.getVideoLayer() === layer" in video
    assert "guard !previous.nagramiXHasPiPRequest" in video
    assert "currentItem.content.id == self.item?.content.id" in video
    assert "private let willBegin: (NativePictureInPictureContentImpl) -> Bool" in video
    assert "guard self.willBegin(self) else" in video
    assert "didExpand = false\n                return true\n            }, didBegin:" in video
    source = templates["__SOURCE__"]
    assert source.index("content.stop()") < source.index("self.prepareForPictureInPictureSwipe()")
    assert "current === previousOwner" in source and "askedPreviousToStop" in source
    assert "deadline - CACurrentMediaTime()" in source
    assert "content.nagramiXMatchesSource(videoNode, requireLayer: false)" in source
    assert "self.nativePictureInPictureContent === content" in source

    execution = "not_run"
    if swiftc:
        # Компилируем именно файл, вышедший из полного overlay, вместе с тестами.
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for mode, flags in (("debug", []), ("optimized", ["-O"])):
                executable = folder / mode
                cmd = [str(swiftc), "-module-cache-path", str(folder / "cache"), "-warnings-as-errors", *flags,
                       str(after / POLICY), str(ROOT / "scripts/tests/NagramiXPiPReleaseDecisionTests.swift"),
                       "-o", str(executable)]
                import sys
                if sys.platform == "linux": cmd += ["-Xlinker", "-lm"]
                subprocess.run(cmd, check=True)
                subprocess.run([str(executable)], check=True)
            subprocess.run([str(swiftc), "-frontend", "-parse", *(str(after / n) for n in (C, I, V))], check=True)
        execution = "PASS: real Swift policy debug/optimized; UIKit files syntax only"
    return {"outputs": len(b), "changed": sorted(changed), "new": POLICY,
            "unchanged": len(a) - len(changed), "exact_reverse_patches": len(patches),
            "guard_cases": len(rejected), "rejected": rejected, "policy_execution": execution,
            "ios_native_compile": "pending", "physical_device": "pending"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", type=Path, required=True); p.add_argument("--after", type=Path, required=True)
    p.add_argument("--swiftc", type=Path); p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = json.dumps(validate(args.before, args.after, args.swiftc), ensure_ascii=False, indent=2) + "\n"
    if args.report: args.report.write_text(result)
    print(result, end="")

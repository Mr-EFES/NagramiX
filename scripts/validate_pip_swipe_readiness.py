#!/usr/bin/env python3
"""Проверить реальный PiP overlay: scope, обратимость и атомарный отказ."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = "submodules/GalleryUI/Sources/GalleryControllerNode.swift"
ITEM = "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"
TEMPLATES = {
    "__CONTROLLER_METHODS__": "Sources/GalleryUI/NagramiXResponsivePiPSwipe.swift.inc",
    "__SOURCE_METHODS__": "Sources/GalleryUI/NagramiXPiPSourceReadiness.swift.inc",
}
PREVIOUS = "Sources/GalleryUI/NagramiXDirectionalPiPGesture.swift.inc"


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before: Path, after: Path) -> dict:
    previous, current = hashes(before), hashes(after)
    assert previous.keys() == current.keys()
    changed = sorted(n for n in previous if previous[n] != current[n])
    assert changed == sorted([CONTROLLER, ITEM]), changed
    source = (ROOT / "ios/apply_features.py").read_text()
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "apply_pip_swipe_readiness_followup")
    assignments = {n.targets[0].id: n.value for n in function.body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    assert guards == {n: previous[n] for n in (CONTROLLER, ITEM)}
    previous_gesture = (ROOT / "ios" / PREVIOUS).read_text().rstrip("\n") + "\n\n"

    def literal(node):
        if isinstance(node, ast.Name) and node.id == "previous_gesture":
            return previous_gesture
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            return [literal(n) for n in node.elts]
        raise AssertionError(ast.dump(node))

    patches = literal(assignments["patches"])
    templates = {marker: (ROOT / "ios" / name).read_text().rstrip("\n")
                 + ("\n\n" if marker == "__CONTROLLER_METHODS__" else "\n")
                 for marker, name in TEMPLATES.items()}
    restored = {n: (after / n).read_text() for n in guards}
    for name, old, new in reversed(patches):
        for marker, template in templates.items():
            new = new.replace(marker, template)
        assert restored[name].count(new) == 1, (name, new[:80])
        restored[name] = restored[name].replace(new, old, 1)
    assert all(restored[n].encode() == (before / n).read_bytes() for n in guards)

    entry = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_features")
    calls = [n.func.id for n in ast.walk(entry) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert calls.count(function.name) == 1
    assert calls.index(function.name) > calls.index("apply_edit_history_interaction_fix")
    spec = importlib.util.spec_from_file_location("pip_readiness", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory) / "native"
        overlay = Path(directory) / "ios"

        def seed():
            for name in guards:
                p = fixture / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((before / name).read_bytes())
            for name in [PREVIOUS, *TEMPLATES.values()]:
                p = overlay / name
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "ios" / name, p)

        def reject(label):
            initial = hashes(fixture)
            try:
                module.apply_pip_swipe_readiness_followup(fixture, overlay)
            except (SystemExit, FileNotFoundError):
                assert hashes(fixture) == initial, label
                rejected.append(label)
            else:
                raise AssertionError("Некорректный вход принят: " + label)

        seed()
        module.apply_pip_swipe_readiness_followup(fixture, overlay)
        assert all((fixture / n).read_bytes() == (after / n).read_bytes() for n in guards)
        reject("повторное применение")
        seed()
        (fixture / CONTROLLER).write_bytes((after / CONTROLLER).read_bytes())
        reject("частично применённый overlay")
        for name in guards:
            seed()
            with (fixture / name).open("ab") as f:
                f.write(b"\n// drift\n")
            reject("drift " + name)
            seed()
            (fixture / name).unlink()
            reject("отсутствует " + name)
        for name in [PREVIOUS, *TEMPLATES.values()]:
            seed()
            (overlay / name).unlink()
            reject("отсутствует " + name)

    # Дополнительные контракты исходников; это не исполнение UIKit/AVKit.
    controller = (after / CONTROLLER).read_text()
    item = (after / ITEM).read_text()
    eligibility = item.split("    override var nagramiXCanBeginDirectionalPiPSwipe:")[1].split(
        "    override func nagramiXRequireDirectionalPiPGesture")[0]
    assert "getVideoLayer" not in eligibility
    assert "minimumZoomScale * 1.005" in eligibility
    assert 'data["ios_killswitch_disable_swipe_pip"]' in eligibility
    assert 'data["ios_killswitch_disable_native_pip_v2"]' in eligibility
    assert "NagramiXTabSettings.videoPiPSwipeEnabled" in eligibility
    assert "!item.isSecret" in eligibility and "media.isAnimated" in eligibility
    assert "self.view.addGestureRecognizer(gesture)" in controller
    assert "gesture.minimumNumberOfTouches = 1" in controller
    assert "gesture.maximumNumberOfTouches = 1" in controller
    assert "gesture.numberOfTouches == 1" not in controller
    began = controller.split("    @objc private func nagramiXDirectionalPiPPan")[1].split("case .changed, .ended:")[0]
    assert "let _ = item.prepareForPictureInPictureSwipe()" in began
    assert "item.prepareForPictureInPictureSwipe() else" not in began
    changed_body = controller.split("    @objc private func nagramiXDirectionalPiPPan")[1].split("case .changed, .ended:")[1]
    assert changed_body.index("item.view.transform =") < changed_body.index("guard self.nagramiXDirectionalPiPRequest == nil")
    assert "x: translation.x * factor, y: translation.y * factor" in changed_body
    assert "x: delta.x / distance * travel, y: delta.y / distance * travel" in controller
    assert "asyncAfter(deadline: .now() + 0.22)" in controller
    assert "guard !self.nagramiXDirectionalPiPTransferring" in controller
    assert "let deadline = CACurrentMediaTime() + 3.0" in item
    assert "timeout: max(0.0, deadline - CACurrentMediaTime())" in item
    assert "self.nagramiXDirectionalPiPSourceRequest == request" in item
    assert "self.videoNode === videoNode" in item
    assert "self.nagramiXDirectionalPiPSourceTimer?.invalidate()" in item
    # Остальные методы native AVKit и ветка кнопки побайтно восстанавливаются выше.
    return {"outputs": len(previous), "changed": changed,
            "byte_identical": len(previous) - len(changed), "exact_reverse_patches": len(patches),
            "rejected_without_partial_writes": rejected, "patch_integration": "PASS",
            "native_compile": "pending", "physical_device": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = json.dumps(validate(args.before, args.after), ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(result)
    print(result, end="")

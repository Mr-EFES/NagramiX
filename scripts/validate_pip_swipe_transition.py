#!/usr/bin/env python3
"""Проверить ранний PiP-свайп, ограниченный scope и guards без исполнения UIKit."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "controller": "submodules/GalleryUI/Sources/GalleryControllerNode.swift",
    "item": "submodules/GalleryUI/Sources/GalleryItemNode.swift",
    "video": "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift",
}


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def part(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def literal(node):
    if isinstance(node, ast.Name):
        return TARGETS[node.id]
    if isinstance(node, ast.Tuple):
        return tuple(literal(value) for value in node.elts)
    if isinstance(node, ast.List):
        return [literal(value) for value in node.elts]
    return ast.literal_eval(node)


def validate(before: Path, after: Path) -> dict:
    previous, current = hashes(before), hashes(after)
    assert previous.keys() == current.keys()
    changed = sorted(name for name in previous if previous[name] != current[name])
    assert changed == sorted(TARGETS.values()), changed
    tree = ast.parse((ROOT / "ios/apply_features.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "apply_responsive_swipe_picture_in_picture")
    patches = []
    guards = None
    for n in function.body:
        if isinstance(n, ast.Assign):
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if "patches" in names:
                patches = literal(n.value)
            elif "guards" in names:
                guards = ast.literal_eval(n.value)
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == "patches":
            patches.append(literal(n.value.args[0]))
    assert guards is not None and set(guards) == set(TARGETS.values())
    restored = {name: (after / name).read_text() for name in TARGETS.values()}
    for name, old, new in reversed(patches):
        assert restored[name].count(new) == 1, (name, new[:80])
        restored[name] = restored[name].replace(new, old, 1)
    for name, text in restored.items():
        assert text.encode() == (before / name).read_bytes(), name
        assert guards[name] == previous[name]
    controller, item, video = [(after / TARGETS[k]).read_text() for k in ["controller", "item", "video"]]
    assert "return false" in part(item, "    open func prepareForPictureInPictureSwipe()", "    open func cancelPictureInPictureSwipePreparation()")
    drag = part(controller, "    open func scrollViewDidScroll(", "    open func scrollViewWillEndDragging(")
    assert "scrollView.isDragging, !self.nagramiXSwipePiPCommitted" in drag
    assert "abs(distanceFromEquilibrium) >= 8.0" in drag
    assert "abs(distanceFromEquilibrium) >= 48.0" in drag
    assert "item.prepareForPictureInPictureSwipe()" in drag
    assert "self.nagramiXCommitSwipePiP(item: item, distance: distanceFromEquilibrium)" in drag
    assert "self.nagramiXOpaqueSwipeBackground ? 1.0" in drag
    commit = part(controller, "    private func nagramiXCommitSwipePiP(", "    open func scrollViewDidScroll(")
    assert commit.index("self.nagramiXSwipePiPCommitted = true") < commit.index("self.scrollView.panGestureRecognizer.isEnabled = false") < commit.index("item.maybePerformActionForSwipeDismiss()")
    assert "self.scrollView.panGestureRecognizer.isEnabled = true" in commit
    assert "let limitedDistance = min(48.0, max(-48.0, distance))" in commit
    assert "isScrollEnabled = false" not in commit
    assert "if !handled" in commit and "animated: true" in commit
    end_drag = part(controller, "    open func scrollViewWillEndDragging(", "    open func updatePresentationState(")
    assert end_drag.index("if self.nagramiXSwipePiPCommitted") < end_drag.index("let minimalDismissDistance")
    assert "item === self.pager.centralItemNode()" in end_drag
    assert "abs(velocity.y) > 1.0" in end_drag
    assert "scrollView.contentSize.height / 12.0" in end_drag
    assert "UIApplication.willResignActiveNotification" in controller
    assert "previousLayout.size != layout.size" in controller
    assert "NotificationCenter.default.removeObserver(observer)" in controller
    assert "open func scrollViewDidEndDragging" in controller
    prepare = part(video, "    override func prepareForPictureInPictureSwipe()", "    override func cancelPictureInPictureSwipePreparation()")
    for needle in ["NagramiXTabSettings.videoPiPSwipeEnabled", "self.isCentral == true", "!item.isSecret", "self.videoNode?.getVideoLayer() != nil", "AVPictureInPictureController.isPictureInPictureSupported()", 'data["ios_killswitch_disable_swipe_pip"]', 'data["ios_killswitch_disable_native_pip_v2"]', "message.adAttribute != nil", "content.fileReference.media.isAnimated"]:
        assert needle in prepare
    assert "self.nagramiXOwnsSwipePiPPreparation = self.nativePictureInPictureContent != nil" in prepare
    cancel = part(video, "    override func cancelPictureInPictureSwipePreparation()", "    override func maybePerformActionForSwipeDismiss()")
    assert "guard self.nagramiXOwnsSwipePiPPreparation" in cancel
    assert "!content.nagramiXCancelSwipePreparation()" in cancel
    assert cancel.index("return\n") < cancel.index("self.nativePictureInPictureContent = nil")
    native_cancel = part(video, "    func nagramiXCancelSwipePreparation()", "    func beginPictureInPicture()")
    assert "!self.nagramiXPiPStartRequested" in native_cancel
    assert "self.pictureInPictureController?.isPictureInPictureActive != true" in native_cancel
    assert "self.nagramiXCancelPendingPiPStart()" in native_cancel
    request = part(video, "    func nagramiXRequestPictureInPicture(", "    func invalidatePlaybackState()")
    assert "self.nagramiXPendingPiPStart != nil || self.nagramiXPiPStartRequested || controller.isPictureInPictureActive" in request
    assert request.index("self.nagramiXPiPStartRequested = true") < request.index("controller.startPictureInPicture()")
    assert "let deadline = CACurrentMediaTime() + 2.0" in request
    assert "SwiftSignalKit.Timer(timeout: 0.05" in request
    assert "self.node.getVideoLayer() === sourceLayer" in request
    assert "self.nagramiXPendingPiPStart == requestId" in request
    assert "UIApplication.shared.applicationState == .active" in request
    failure = part(video, "    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, failedToStartPictureInPictureWithError", "    public func pictureInPictureControllerWillStopPictureInPicture(")
    assert "self.nagramiXPiPStartRequested = false" in failure and "unavailable?()" in failure
    will_start = part(video, "    public func pictureInPictureControllerWillStartPictureInPicture(", "    public func pictureInPictureControllerDidStartPictureInPicture(")
    assert will_start.index("self.nagramiXPiPStartFailure = nil") < will_start.index("self.willBegin(self)")
    assert "self.nativePictureInPictureContent === content" in video
    cleanup = video.index("controller.contentSource = nil")
    assert cleanup < video.index("self.pictureInPictureController = nil", cleanup) < video.index("self.nagramiXPictureInPictureLayer = nil", cleanup)
    status = video.index("strongSelf.playerStatusValue = value")
    assert "setupNativePictureInPicture()" not in video[status:status + 650]
    assert video.count("self.setupNativePictureInPicture()") == 3
    spec = importlib.util.spec_from_file_location("pip_patch", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        for name in TARGETS.values():
            path = fixture / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((before / name).read_bytes())
        module.apply_responsive_swipe_picture_in_picture(fixture)
        assert all((fixture / name).read_bytes() == (after / name).read_bytes() for name in TARGETS.values())
        applied = hashes(fixture)
        try:
            module.apply_responsive_swipe_picture_in_picture(fixture)
            raise AssertionError("Repeated patch accepted")
        except SystemExit:
            assert hashes(fixture) == applied
        for drift in TARGETS.values():
            for name in TARGETS.values():
                (fixture / name).write_bytes((before / name).read_bytes())
            with (fixture / drift).open("ab") as f:
                f.write(b"\n// drift\n")
            initial = hashes(fixture)
            try:
                module.apply_responsive_swipe_picture_in_picture(fixture)
                raise AssertionError("Changed input accepted")
            except SystemExit:
                assert hashes(fixture) == initial
    return {"outputs": len(previous), "changed": changed, "byte_identical": len(previous) - 3, "exact_reverse_patches": len(patches), "drift_and_rerun_rejected_without_writes": 4, "gesture_and_lifetime_source_contracts": "PASS", "native_compile": "pending", "physical_device": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.before, args.after)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(output)
    print(output, end="")

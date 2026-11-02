#!/usr/bin/env python3
"""Validate the watchdog fix's overlay/ownership; does not run AVFoundation."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "ios"
PATCHER = OVERLAY / "apply_features.py"
METHODS = "Sources/CameraNeo/NagramiXPreviewSession.swift.inc"
TEST = "submodules/Camera/CameraNeo/Tests/NagramiXPreviewSessionTests.swift"
TEST_SOURCE = "Tests/CameraNeo/NagramiXPreviewSessionTests.swift"


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    helper = next(n for n in ast.parse(PATCHER.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_camera_preview_lifecycle")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    guards = ast.literal_eval(assignments["guards"])
    patches = ast.literal_eval(assignments["patches"])
    methods = (OVERLAY / METHODS).read_text().rstrip("\n") + "\n\n"
    assert len(guards) == 3 and len(patches) == 21
    before, after = inventory(args.before), inventory(args.after)
    assert after.keys() - before.keys() == {TEST}
    assert not before.keys() - after.keys()
    assert {n for n in before if before[n] != after[n]} == set(guards)
    assert after[TEST] == (OVERLAY / TEST_SOURCE).read_bytes()
    for name, digest in guards.items():
        assert hashlib.sha256(before[name]).hexdigest() == digest
        text, undo = before[name].decode(), []
        for target, old, new in patches:
            if target != name:
                continue
            new = new.replace("__NAGRAMIX_PREVIEW_SESSION__", methods)
            assert text.count(old) == 1
            undo.append((text.index(old), old, new))
            text = text.replace(old, new, 1)
        assert text.encode() == after[name]
        for offset, old, new in reversed(undo):
            assert text[offset:offset + len(new)] == new
            text = text[:offset] + old + text[offset + len(new):]
        assert text.encode() == before[name]

    spec = importlib.util.spec_from_file_location("features", PATCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scenarios = ["clean", "rerun", *guards, "missing-helper", "missing-test", "test-conflict"]
    for scenario in scenarios:
        with tempfile.TemporaryDirectory(prefix="nagramix-preview-lifetime-", dir="/workspace") as directory:
            tree, overlay = Path(directory) / "source", Path(directory) / "overlay"
            for name in guards:
                raw = after[name] if scenario == "rerun" else before[name]
                if scenario == name:
                    raw += b"\n// drift\n"
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            for name in (METHODS, TEST_SOURCE):
                target = overlay / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(OVERLAY / name, target)
            if scenario == "missing-helper":
                (overlay / METHODS).unlink()
            if scenario == "missing-test":
                (overlay / TEST_SOURCE).unlink()
            if scenario in ("test-conflict", "rerun"):
                target = tree / TEST
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(after[TEST] if scenario == "rerun" else b"do not overwrite\n")
            initial = inventory(tree)
            if scenario == "clean":
                module.apply_camera_preview_lifecycle(tree, overlay)
                assert inventory(tree) == {n: after[n] for n in (*guards, TEST)}
            else:
                try:
                    module.apply_camera_preview_lifecycle(tree, overlay)
                except SystemExit:
                    pass
                else:
                    raise AssertionError(f"Accepted unsafe scenario: {scenario}")
                assert inventory(tree) == initial, "Partial write on rejected input"

    neo = after["submodules/Camera/CameraNeo/Sources/CameraNeo.swift"].decode()
    preview = after["submodules/Camera/CameraNeo/Sources/CameraPreviewView.swift"].decode()
    build = after["submodules/Camera/CameraNeo/BUILD"].decode()
    view = preview.split("final class CameraPreviewView:", 1)[1]
    assert "private let sessionQueue = nagramiXCameraSessionQueue" in neo
    assert "sessionQueueKey" not in neo
    assert "self.videoPreviewLayer.session =" not in view
    assert "self.videoPreviewLayer.setSessionWithNoConnection" not in view
    assert ".connection?.videoOrientation" not in view and ".connection?.isEnabled" not in view
    assert "self.nagramiXSessionBinding.invalidate()" in view
    assert "self.nagramiXSessionBinding.bind(session, automaticallyConnect: automaticallyConnect)" in view
    assert "return self.nagramiXSessionBinding.captureOrientation" in view
    assert "Atomic<AVCaptureVideoOrientation>" in methods
    assert "dispatchPrecondition(condition: .onQueue(nagramiXCameraSessionQueue))" in methods
    assert "guard self.session === session else { return }" in methods
    assert methods.count("nagramiXCameraSessionQueue.async") == 5
    deinit = methods.split("    deinit {", 1)[1].split("    func bind(", 1)[0]
    queued_deinit = deinit.split("nagramiXCameraSessionQueue.async {", 1)[1]
    assert "self." not in queued_deinit
    assert "let layer = self.layer" in deinit and "layer.session === session" in queued_deinit
    assert ".sync" not in methods and ".wait(" not in methods
    camera_deinit = neo.split("    deinit {", 1)[1].split("    func startCapture", 1)[0]
    assert "let previewSession = self.nagramiXPreviewSession" in camera_deinit
    assert "let secondaryPreviewSession = self.nagramiXSecondaryPreviewSession" in camera_deinit
    assert camera_deinit.index("session.commitConfiguration()") < camera_deinit.index("previewSession?.detach(from: session)")
    assert "self." not in camera_deinit.split("self.sessionQueue.async {", 1)[1]
    release = camera_deinit.split("DispatchQueue.main.async {", 1)[1].split("            mediaQueue.async", 1)[0]
    assert "withExtendedLifetime(previewView) {}" in release
    assert "withExtendedLifetime(secondaryPreviewView) {}" in release
    assert ".detach(" not in release and ".session =" not in release
    stop = neo.split("    func stopCapture(", 1)[1].split("    var position:", 1)[0]
    assert "DispatchQueue.main" not in stop
    assert "self.nagramiXPreviewSession?.detach(from: self.session)" in stop
    assert "self.nagramiXSecondaryPreviewSession?.detach(from: self.session)" in stop
    assert "videoPreviewLayer: previewSession.layer" in neo
    assert "videoPreviewLayer: previewView.videoPreviewLayer" not in neo

    # New test targets compile the real production source. The production
    # CameraNeo library, its dependencies and compiler options are unchanged.
    old_build = before["submodules/Camera/CameraNeo/BUILD"].decode()
    assert old_build[old_build.index("filegroup("):] == build[build.index("filegroup("):build.index("\n# Compile the production preview source")]
    assert 'testonly = True' in build
    assert 'srcs = ["Sources/CameraPreviewView.swift"] + glob(["Tests/**/*.swift"])' in build
    assert 'name = "CameraNeoPreviewTests"' in build
    assert after[TEST].count(b"    func test") == 4
    print(f"PASS: {len(after)} outputs; 3 changed / 1 added / {len(before) - 3} byte-identical; 21 exact reversals")
    print(f"PASS: {len(scenarios)} clean/fail-closed scenarios; shared capture/preview queue; owner identity/lifetime; no main detach or sync wait")
    print("Native XCTest target prepared: //submodules/Camera/CameraNeo:CameraNeoPreviewTests (4 cases)")
    print("Not executed: Apple SDK compile, XCTest, hardware/watchdog regression on iPhone")


if __name__ == "__main__":
    main()

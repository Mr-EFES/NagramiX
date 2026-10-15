#!/usr/bin/env python3
"""Verify recording overlay scope, ownership and guards; not an AVFoundation test."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
METHODS = ROOT / "ios/Sources/VideoMessageCameraScreen/NagramiXSelfieRecording.swift.inc"


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_selfie_recording_lifecycle")
    assignments = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    names = {k: ast.literal_eval(assignments[k]) for k in ("screen", "neo")}
    guards = {names[k.id]: ast.literal_eval(v) for k, v in zip(assignments["guards"].keys, assignments["guards"].values)}
    patches = []
    for item in assignments["patches"].elts:
        name, old, new = item.elts
        old, new = ast.literal_eval(old), ast.literal_eval(new)
        if new == "__NAGRAMIX_SELFIE_RECORDING_STATE__":
            new = METHODS.read_text()
        patches.append((names[name.id], old, new))
    assert len(patches) == 21
    resources = {f"submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings" for lang in ("ru", "en")}
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == set(guards) | resources, "Unexpected native scope"
    # Reconstruct every changed native byte, including deleting the old timer implementation.
    for name, digest in guards.items():
        assert hashlib.sha256(before[name]).hexdigest() == digest
        replay, steps = before[name].decode(), []
        for path, old, new in patches:
            if path != name:
                continue
            assert replay.count(old) == 1
            steps.append((replay.index(old), old, new))
            replay = replay.replace(old, new, 1)
        assert replay.encode() == after[name]
        reverse = after[name].decode()
        for offset, old, new in reversed(steps):
            assert reverse[offset:offset + len(new)] == new
            reverse = reverse[:offset] + old + reverse[offset + len(new):]
        assert reverse.encode() == before[name]
    for name in resources:
        assert after[name] == (ROOT / "ios/Sources" / name.removeprefix("submodules/")).read_bytes()
        old_lines = set(before[name].decode().splitlines()) - set(after[name].decode().splitlines())
        assert len(old_lines) == 2 and all('"NagramiX.SelfieCountdown.' in line for line in old_lines)

    screen, neo = (after[names[k]].decode() for k in ("screen", "neo"))
    methods = METHODS.read_text()
    assert "nagramiXDidRequestInitialRecording" not in screen
    assert "cameraState.position == .front && NagramiXTabSettings.current.selfieCountdown" in methods
    assert "if isFrontCamera && NagramiXTabSettings.current.selfieCountdown && self.nagramiXWriterRequested" in screen
    assert "controller.node.nagramiXCameraSwitchPending = true" in methods
    assert "camera.setPosition(.front)" in methods
    assert "controller.node.nagramiXAppendSwitchResult(result)" in methods
    append = screen.split("fileprivate func nagramiXAppendSwitchResult", 1)[1].split("func addCaptureResult", 1)[0]
    assert "self.results.append(result)" in append
    assert "pauseCameraCapture" not in append and "resultsPipe.putNext" not in append
    assert screen.count("nagramiXCountdownPending && !self.node.nagramiXCameraSwitchPending") == 2
    assert "Queue.mainQueue().async" in methods and "self.nagramiXFinishStop(result)" in methods
    assert "self.nagramiXStopDisposable.set(request)" in methods
    assert "self.resultDisposable.set((camera.stopRecording()" not in screen
    assert "self.nagramiXRecordingGeneration == generation" in methods
    assert "let writerGeneration = self.nagramiXRecordingGeneration" in methods
    assert methods.count("self.nagramiXRecordingGeneration == writerGeneration") == 3
    assert "timeout(12.0" in methods and "self.nagramiXAbortRecording()" in methods
    assert "CACurrentMediaTime() + 3.0" in methods
    assert "controller.recordingStartTime = CACurrentMediaTime() - initialDuration" in methods
    assert "self.nagramiXPreviewReadyDisposables.dispose()" in screen
    assert "self.previewSnapshotView === snapshot" in screen
    deinit = neo.split("    deinit {", 1)[1].split("    func startCapture()", 1)[0]
    assert ".sync" not in deinit and "self.sessionQueue.async" in deinit
    queued = deinit.split("self.sessionQueue.async {", 1)[1]
    assert "self." not in queued, "Escaping capture of deinitializing camera"
    assert "mediaQueue.async" in queued and "recorder?.cancel()" in queued
    stop = neo.split("    func stopRecording()", 1)[1].split("    func focus(", 1)[0]
    assert stop.index("recordingCompletionPipe.signal()") < stop.index("recordingStopRequested.modify") < stop.index("recorder?.stop()")
    assert "completion: { [weak self, recordingCompletionPipe] result in" in neo

    # Persisted values and frozen rear-camera behavior remain byte-identical.
    settings = after["submodules/NagramiXCore/Sources/NagramiXTabSettings.swift"].decode()
    assert 'static let selfieCountdown = "nagramix.videoMessages.selfieCountdown"' in settings
    assert "selfieCountdown: defaults.object(forKey: Key.selfieCountdown) as? Bool ?? true" in settings
    assert "useRearCameraForVideoMessages: defaults.object(forKey: Key.useRearCameraForVideoMessages) as? Bool ?? true" in settings
    assert before["submodules/NagramiXCore/Sources/NagramiXTabSettings.swift"] == after["submodules/NagramiXCore/Sources/NagramiXTabSettings.swift"]
    assert '"NagramiX.SelfieCountdown.Title" = "Таймер селфи-камеры";' in after[next(n for n in resources if "/ru." in n)].decode()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", *guards):
        with tempfile.TemporaryDirectory(prefix="nagramix-recording-", dir="/workspace") as directory:
            tree = Path(directory)
            initial = {}
            for name in guards:
                data = after[name] if scenario == "rerun" else before[name]
                if scenario == name:
                    data += b"\n// Unexpected native change\n"
                initial[name] = data
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            if scenario == "clean":
                module.apply_selfie_recording_lifecycle(tree)
                assert all((tree / n).read_bytes() == after[n] for n in guards)
            else:
                try:
                    module.apply_selfie_recording_lifecycle(tree)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift/rerun")
                assert all((tree / n).read_bytes() == initial[n] for n in guards), "Partial mutation"
    print("PASS: 2 native files / 21 exact patches + 2 locale resources; SHA drift/rerun guards; recording lifecycle boundaries")
    print("Not verified: Swift typecheck, camera hardware, UI hangs, segment continuity or A/V timing on iPhone")


if __name__ == "__main__":
    main()

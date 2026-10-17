#!/usr/bin/env python3
"""Verify the pinned overlay and stop/preview ownership; no device simulation."""

import argparse
import ast
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "ios/apply_features.py"


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    helper = next(n for n in ast.parse(PATCHER.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_round_video_finalization")
    values = {t.id: n.value for n in helper.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    name = ast.literal_eval(values["name"])
    patches = ast.literal_eval(values["replacements"])
    assert len(patches) == 15
    before, after = inventory(args.before), inventory(args.after)
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == {name}

    replay, undo = before[name].decode(), []
    for old, new in patches:
        assert replay.count(old) == 1
        undo.append((replay.index(old), old, new))
        replay = replay.replace(old, new, 1)
    assert replay.encode() == after[name]
    for offset, old, new in reversed(undo):
        assert replay[offset:offset + len(new)] == new
        replay = replay[:offset] + old + replay[offset + len(new):]
    assert replay.encode() == before[name], "Unexpected edits outside the exact patch"

    spec = importlib.util.spec_from_file_location("features", PATCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", "drift"):
        with tempfile.TemporaryDirectory(prefix="nagramix-round-finalization-", dir="/workspace") as directory:
            target = Path(directory) / name
            target.parent.mkdir(parents=True)
            raw = after[name] if scenario == "rerun" else before[name]
            if scenario == "drift":
                raw += b"\n// unexpected native edit\n"
            target.write_bytes(raw)
            if scenario == "clean":
                module.apply_round_video_finalization(Path(directory))
                assert target.read_bytes() == after[name]
            else:
                try:
                    module.apply_round_video_finalization(Path(directory))
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted native drift/rerun")
                assert target.read_bytes() == raw

    screen = after[name].decode()
    current = screen.split("    private var currentResults:", 1)[1].split("    public func takenRecordedData", 1)[0]
    assert "resultsPipe" not in current
    assert "nagramiXCompletedResults.get()" in current
    assert "filter { $0.revision >= expectedRevision }" in current
    assert current.index("let expectedRevision") < current.index("waitingForNextResult = false")
    assert "self.nagramiXExpectedCompletedRevision = self.node.nagramiXCompletedRevision + 1" in screen
    append = screen.split("fileprivate func nagramiXAppendSwitchResult", 1)[1].split("func addCaptureResult", 1)[0]
    assert "self.results.append(result)" in append
    assert "nagramiXCompleted" not in append, "Camera flips must not satisfy a final-stop waiter"
    final = screen.split("private func nagramiXFinishStop", 1)[1].split("private func nagramiXStopWriter", 1)[0]
    assert final.index("controller.updateCameraState(") < final.index("self.completion.invoke(result)")
    add = screen.split("func addCaptureResult", 1)[1].split("private func debugSaveResult", 1)[0]
    assert add.index("self.results.append(result)") < add.index("self.nagramiXCompletedRevision += 1") < add.index("self.nagramiXCompletedResults.set(")
    assert "revision: self.nagramiXCompletedRevision, results: self.results" in add
    assert "[weak self, weak controller]" in add and "self.nagramiXCompletedRevision == revision" in add
    assert "!controller.didSend" in add and "!controller.isDismissed" in add
    assert "case .none = controller.cameraState.recording" in add

    # All three formerly synchronous composition callers now use the same
    # background signal; UI work remains downstream of deliverOnMainQueue.
    assert screen.count("nagramiXRecordingComposition(with:") == 3
    assert screen.count("nagramiXMakeRecordingComposition(with:") == 1
    background = screen.split("private func nagramiXRecordingComposition(", 1)[1].split("private func nagramiXMakeRecordingComposition(", 1)[0]
    assert "runOn(nagramiXRecordingCompositionQueue)" in background
    assert "deliverOnMainQueue" in background
    assert 'Queue(name: "NagramiX.RoundVideoComposition")' in screen
    assert screen.count("self.nagramiXCompositionDisposable.dispose()") == 1
    assert "self.node.nagramiXCompositionDisposable.dispose()" in screen
    assert "func resumeCameraCapture() {\n            self.nagramiXCompositionDisposable.set(nil)" in screen
    assert "self.didSend = true\n        self.node.nagramiXCompositionDisposable.set(nil)" in screen

    # The native sender, composition algorithm, persisted preferences and
    # camera implementation are preserved by exact reversal + full inventory.
    settings = "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift"
    assert before[settings] == after[settings]
    settings = after[settings].decode()
    for key in ("selfieCountdown", "useRearCameraForVideoMessages"):
        assert f"{key}: defaults.object(forKey: Key.{key}) as? Bool ?? true" in settings
    assert "timeout(12.0" in screen and "CACurrentMediaTime() + 3.0" in screen
    assert "LocalFileVideoMediaResource(randomId:" in screen
    assert "if duration < 1.0" in screen
    assert "cameraState.duration > 0.5" in screen
    assert "if duration > 59.5" in screen
    assert "if totalDuration > 59.5" in screen
    assert "Round media prepared for enqueue; segments=" in screen

    print(f"PASS: {len(after)} outputs; 1 changed / {len(after) - 1} byte-identical; 15 exact reversals; clean/drift/rerun guards")
    print("PASS: replayed final-stop snapshot / revision filter; background composition; callback/cancellation ownership; persisted defaults")
    print("Not verified: Swift typecheck, AVFoundation/Metal, cold launch crash or physical iPhone behavior")


if __name__ == "__main__":
    main()

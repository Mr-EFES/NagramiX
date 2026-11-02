#!/usr/bin/env python3
"""Check recording-transition patch boundaries; does not run AVAudioSession/AudioUnit."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "submodules/TelegramAudio/Sources/ManagedAudioSession.swift"
RECORDER = "submodules/TelegramUI/Sources/ManagedAudioRecorder.swift"
CAMERA = "submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift"
FILES = {SESSION, RECORDER, CAMERA}


def snapshot(folder):
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


def validate(before, after):
    old, new = snapshot(before), snapshot(after)
    assert old.keys() == new.keys(), "Native file set changed"
    assert {name for name in old if old[name] != new[name]} == FILES

    overlay = ROOT / "ios/apply_features.py"
    function = next(node for node in ast.parse(overlay.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "apply_mixed_recording_transition")
    expression = next(node.value for node in function.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "substitutions" for target in node.targets))
    patches = eval(compile(ast.Expression(expression), "<recording-overlay>", "eval"),
                   {"__builtins__": {}}, {"session": SESSION, "recorder": RECORDER, "camera": CAMERA})
    restored = {name: (after / name).read_text() for name in FILES}
    for name, original, replacement in reversed(patches):
        assert restored[name].count(replacement) == 1, name
        restored[name] = restored[name].replace(replacement, original, 1)
    for name in FILES:
        assert restored[name].encode() == (before / name).read_bytes(), name

    spec = importlib.util.spec_from_file_location("features", overlay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for drift in [*sorted(FILES), None]:
        with tempfile.TemporaryDirectory(prefix="nagramix-mixed-recording-") as directory:
            tree = Path(directory)
            for name in FILES:
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((before / name).read_bytes())
            if drift is None:
                module.apply_mixed_recording_transition(tree)
                for name in FILES:
                    assert (tree / name).read_bytes() == (after / name).read_bytes()
            else:
                with (tree / drift).open("a") as stream:
                    stream.write("\n// simulated upstream drift\n")
            unchanged = snapshot(tree)
            try:
                module.apply_mixed_recording_transition(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Drift/reapplication accepted")
            assert snapshot(tree) == unchanged, "Failed input caused a partial write"

    session = (after / SESSION).read_text()
    release = session.split("private func applyNone()", 1)[1].split("private func setup(type:", 1)[0]
    mixed, exclusive = release.split("if wasMixedRecording {", 1)[1].split("} else {", 1)
    assert "Thread.sleep" not in mixed
    assert "self.queue.after(2.0" in mixed
    assert "self.nagramiXMixedReleaseGeneration == releaseGeneration" in mixed
    assert "self.currentTypeAndOutputMode == nil, self.holders.isEmpty" in mixed
    assert "!self.callKitAudioSessionIsActive" in mixed
    assert "Thread.sleep(forTimeInterval: 2.0)" in exclusive
    assert "if case .system = outputMode, case .record(false, false, true) = type" in release

    recorder = (after / RECORDER).read_text()
    assert "let inputOnly = !self.pauseMusicOnRecording && !self.beginWithTone" in recorder
    assert "var outputEnabled: UInt32 = 0" in recorder
    assert recorder.index("kAudioUnitScope_Output, 0, &outputEnabled") < recorder.index("AudioUnitInitialize(audioUnit)")
    assert "audioRecorderNativeStreamDescription(sampleRate: 48000)" in recorder
    # Input capture, the Opus writer and the generation-protected teardown are
    # byte-identical, even though the unused output bus configuration changes.
    previous = (before / RECORDER).read_text()
    assert recorder.split("func audioSessionAcquired(headset:", 1)[1] == previous.split("func audioSessionAcquired(headset:", 1)[1]
    camera = (after / CAMERA).read_text()
    assert "if case .record(_, _, true) = audioSessionType" in camera
    assert "Queue.mainQueue().async(setupCamera)" in camera
    assert "Queue.mainQueue().after(0.05, setupCamera)" in camera
    print(f"PASS: {len(old)} native files, only 3 changed; {len(patches)} exact reversals; drift/rerun and mixed/OFF/lifecycle boundaries verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

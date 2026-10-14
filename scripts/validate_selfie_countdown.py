#!/usr/bin/env python3
"""Проверить scope и lifecycle интеграции селфи-таймера; не заменяет iPhone/Xcode."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CAMERA = "submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift"
SETTINGS = {
    "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift": "Sources/NagramiXCore/Sources/NagramiXTabSettings.swift",
    "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift": "Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
    "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings": "Sources/NagramiXCore/Resources/ru.lproj/Localizable.strings",
    "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings": "Sources/NagramiXCore/Resources/en.lproj/Localizable.strings",
    "submodules/SettingsUI/Sources/NagramiXSettingsController.swift": "Sources/SettingsUI/NagramiXSettingsController.swift",
}


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before, after):
    patcher = ROOT / "ios/apply_features.py"
    function = next(n for n in ast.parse(patcher.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == "apply_selfie_countdown")
    values = {n.targets[0].id: ast.literal_eval(n.value)
              for n in function.body if isinstance(n, ast.Assign)
              and isinstance(n.targets[0], ast.Name) and n.targets[0].id in {"hashes", "substitutions"}}
    native, patches = values["hashes"], values["substitutions"]
    assert set(native) == {CAMERA} and len(patches) == 15
    old, new = snapshot(before), snapshot(after)
    assert old.keys() == new.keys()
    changed = {name for name in old if old[name] != new[name]}
    assert {CAMERA} <= changed <= {CAMERA} | SETTINGS.keys()
    methods = (ROOT / "ios/Sources/VideoMessageCameraScreen/NagramiXSelfieCountdown.swift.inc").read_text().rstrip("\n") + "\n\n        private var nagramiXStoppingRecording = false\n"
    text = (after / CAMERA).read_text()
    restored = text
    for name, original, replacement in reversed(patches):
        assert name == CAMERA
        if replacement == "__NAGRAMIX_SELFIE_COUNTDOWN_STATE__":
            replacement = methods
        assert restored.count(replacement) == 1, original[:80]
        restored = restored.replace(replacement, original, 1)
    assert restored.encode() == (before / CAMERA).read_bytes()
    assert hashlib.sha256(restored.encode()).hexdigest() == native[CAMERA]
    for name, original in SETTINGS.items():
        assert (after / name).read_bytes() == (ROOT / "ios" / original).read_bytes()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ["clean", "drift"]:
        with tempfile.TemporaryDirectory(prefix="nagramix-selfie-") as directory:
            tree = Path(directory)
            target = tree / CAMERA
            target.parent.mkdir(parents=True)
            target.write_bytes((before / CAMERA).read_bytes())
            if scenario == "clean":
                module.apply_selfie_countdown(tree)
                assert target.read_bytes() == (after / CAMERA).read_bytes()
            else:
                target.write_text(target.read_text() + "\n// input drift\n")
            unchanged = snapshot(tree)
            try:
                module.apply_selfie_countdown(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Accepted drift/reapply")
            assert snapshot(tree) == unchanged, "Partial mutation on rejection"

    settings = (after / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift").read_text()
    assert 'static let selfieCountdown = "nagramix.videoMessages.selfieCountdown"' in settings
    assert "selfieCountdown: Bool = true" in settings
    assert "self.selfieCountdown = selfieCountdown" in settings
    assert "selfieCountdown: defaults.object(forKey: Key.selfieCountdown) as? Bool ?? true" in settings
    assert "defaults.set(value.selfieCountdown, forKey: Key.selfieCountdown)" in settings
    assert "useRearCameraForVideoMessages: defaults.object(forKey: Key.useRearCameraForVideoMessages) as? Bool ?? true" in settings
    ui = (after / "submodules/SettingsUI/Sources/NagramiXSettingsController.swift").read_text()
    assert "case .selfieCountdown: return 144" in ui
    assert "case .videoMessagesHeader, .selfieCountdown, .useRearCameraForVideoMessages" in ui
    assert "title: presentationData.strings.nagramiXSelfieCountdown" in ui
    assert "return strings.nagramiXSelfieCountdownSearchTerms" in ui
    assert ".selfieCountdown(settings.selfieCountdown)" in ui
    assert "updateSelfieCountdown: { value in update { $0.selfieCountdown = value } }" in ui
    for language in ["ru", "en"]:
        localized = (after / f"submodules/NagramiXCore/Resources/{language}.lproj/Localizable.strings").read_text()
        assert localized.count('"NagramiX.SelfieCountdown.Title"') == 1
        assert localized.count('"NagramiX.SelfieCountdown.SearchTerms"') == 1

    start = text.split("func startVideoRecording(pressing:", 1)[1].split("private var nagramiXDidRequestInitialRecording", 1)[0]
    assert "!self.nagramiXDidRequestInitialRecording && controller.cameraState.position == .front && NagramiXTabSettings.current.selfieCountdown" in start
    assert "self.nagramiXDidRequestInitialRecording = true" in start
    assert start.index("withReadyCamera") < start.index("self?.nagramiXBeginCountdown")
    assert "Queue.mainQueue().after(0.15, start)" in start  # OFF/rear native delay
    assert start.index("controller.recordingStartTime = CACurrentMediaTime()") < start.index("camera.startRecording()")
    assert "self.nagramiXRecordingGeneration == generation" in start and "!controller.isDismissed" in start
    assert start.count("camera.startRecording()") == 1
    assert "controller.node.setupLiveUpload(filePath: recordingData.filePath)" in start
    countdown = text.split("private func nagramiXArmCountdown", 1)[1].split("private var nagramiXStoppingRecording", 1)[0]
    assert "willResignActiveNotification" in countdown and "UIApplication.shared.applicationState == .active" in countdown
    assert "CACurrentMediaTime() + 3.0" in countdown and "deadline - CACurrentMediaTime()" in countdown
    assert "Timer(timeout: 0.05, repeat: true" in countdown
    assert "controller.cameraState.position != .front" in countdown and "if position != .front { finish() }" in countdown
    assert "self.nagramiXClearCountdown()\n                start()" in countdown
    assert "controller.node.nagramiXCountdownPending" in countdown and "self.nagramiXRecordingGeneration == generation" in countdown
    assert "camera.startRecording()" not in countdown and "setupLiveUpload" not in countdown
    assert "self.nagramiXCountdownTimer?.invalidate()" in countdown
    assert "self.nagramiXCountdownPositionDisposable?.dispose()" in countdown
    assert "NotificationCenter.default.removeObserver(observer)" in countdown
    cancel = text.split("func cancelVideoRecording()", 1)[1].split("func updateZoom", 1)[0]
    assert "self.nagramiXRecordingGeneration &+= 1" in cancel and "self.nagramiXClearCountdown()" in cancel
    assert "self.animateBrightnessChange()" in cancel
    send = text.split("public func sendVideoRecording", 1)[1].split("var skipAction", 1)[0]
    assert "if self.node.nagramiXCountdownPending" in send and "self.node.cancelRecording.invoke(Void())" in send
    stop = text.split("public func stopVideoRecording() -> Bool", 1)[1].split("fileprivate var recordingStartTime", 1)[0]
    assert stop.index("if self.node.nagramiXCountdownPending") < stop.index("self.waitingForNextResult = true")
    assert "self.discardVideo()" in stop and "return false" in stop
    dismiss = text.split("fileprivate func requestDismiss", 1)[1].split("override public func containerLayoutUpdated", 1)[0]
    assert "self.node.cancelRecording.invoke(Void())" in dismiss and "stopCapture(invalidate: true)" in dismiss
    assert "self.previewContainerContentView.addSubview(self.nagramiXCountdownLabel)" in text
    assert "self.nagramiXCountdownLabel.frame = previewBounds" in text
    assert "UIAccessibility.isReduceMotionEnabled" in text and "UIAccessibility.post(notification: .announcement" in text
    # Audio activation policy, camera configuration/focus, stop result and send metadata remain exact.
    for start_marker, end_marker in [("private func requestAudioSession()", "fileprivate var isDismissed"),
                                     ("fileprivate func setupCamera()", "@objc private func handlePinch"),
                                     ("var skipAction = false", "private var waitingForNextResult")]:
        assert text.split(start_marker, 1)[1].split(end_marker, 1)[0] == restored.split(start_marker, 1)[1].split(end_marker, 1)[0]
    print(f"PASS: {len(new)} outputs; {len(changed)} changed, none added; 15 exact reversals; SHA drift/reapply; front/OFF/rear, cancellation, cleanup and recording boundaries. Native/device pending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

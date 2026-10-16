#!/usr/bin/env python3
"""Verify offline exception tones and default preview integration.

This checks generated source, resources and rejection guards, not APNs delivery
or native audio/UI execution on a physical iPhone.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PEER = "submodules/TelegramUI/Components/NotificationPeerExceptionController/Sources/NotificationPeerExceptionController.swift"
PICKER = "submodules/NotificationSoundSelectionUI/Sources/NotificationSoundSelection.swift"
FRAGMENT = ROOT / "ios/Sources/NotificationPeerExceptionController/NagramiXExceptionSoundEntries.swift.inc"


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before, after = files(args.before), files(args.after)
    assert before.keys() == after.keys()
    assert {n for n in before if before[n] != after[n]} == {PEER, PICKER}
    old, new = (args.before / PEER).read_text(), (args.after / PEER).read_text()
    fragment = FRAGMENT.read_text().rstrip("\n") + "\n\n"
    assert new.count(fragment) == 1
    start = old.index("    if displaySounds {\n")
    end = old.index("    return entries\n", start)
    restored = new.replace(fragment, old[start:end], 1)
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "apply_notification_exception_sound_catalog")
    patches = ast.literal_eval(next(n.value for n in helper.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "patches" for t in n.targets)))
    for a, b in reversed(patches):
        assert restored.count(b) == 1
        restored = restored.replace(b, a, 1)
    assert restored == old, "Changed state/save/cancel/upload/delete or other peer logic"
    fallback = "return fileNameForNotificationSound(account: account, notificationSoundList: notificationSoundList, sound: defaultCloudPeerNotificationSound, defaultSound: nil)"
    picker = (args.after / PICKER).read_text()
    assert picker.count(fallback) == 2
    assert picker.replace(fallback, 'return "\\(100)"') == (args.before / PICKER).read_text()

    # Only custom cloud rows depend on the server cache. Upload, inheritance,
    # None and both builtin lists are outside it, including nil/empty cache.
    cache_start = fragment.index("        if let notificationSoundList = notificationSoundList {")
    cache_end = fragment.index("        index = 2000", cache_start)
    cache = fragment[cache_start:cache_end]
    assert fragment.index("let modernSounds = builtinNotificationSounds.filter") < cache_start
    assert fragment.index("let classicSounds = builtinNotificationSounds.filter") < cache_start
    assert "canBeDeleted: true" in cache and "state.removedSounds.contains" in cache
    for token in (".uploadSound(", ".default(", ".none(", "for sound in modernSounds", "for sound in classicSounds"):
        assert fragment.count(token) == 1 and fragment.index(token) > cache_end
    assert fragment.count("canBeDeleted: false") == 2
    assert "let defaultSound = isStories == true ? state.defaultStoriesSound : state.defaultSound" in fragment
    assert "selectedSound == .default" in fragment and "selectedSound == .none" in fragment
    assert "state.storiesMuted == .alwaysOff" in new and "displaySounds = false" in new
    assert "ensureDownloadedNotificationSoundList(postbox: context.account.postbox).start()" in new
    assert "refreshNotificationSoundList(postbox: context.account.postbox, network: context.account.network).start()" in new
    for name in ("fetchedSoundsDisposable", "refreshedSoundsDisposable"):
        assert new.count(name + ".dispose()") == 1

    core = (args.after / "submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramPeerNotificationSettings.swift").read_text()
    mapping_text = core[core.index("private let cloudSoundMapping"):core.index("\n]")]
    mapping = {int(k): int(v) for k, v in re.findall(r"^\s*(\d+):\s*(-?\d+)", mapping_text, re.M)}
    order = list(range(200, 211)) + list(range(100, 112)) + list(range(2, 10))
    assert len(order) == len({mapping[k] for k in order}) == 31
    assert "Array(Int32(200)...Int32(210)) + Array(Int32(100)...Int32(111)) + Array(Int32(2)...Int32(9))" in core
    assert "defaultCloudPeerNotificationSound: PeerMessageSound = .cloud(fileId: cloudSoundMapping[200]!)" in core
    assert "return (key >= 200 ? key - 200 + 12 : key - 100, .modern)" in core
    manifest = json.loads((ROOT / "ios/Resources/NotificationSounds/manifest.json").read_text())
    assert {r["key"] for r in manifest} == set(order) and len(manifest) == 31
    for row in manifest:
        data = (args.after / "Telegram/Telegram-iOS/Resources/notifications" / row["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
    assert "builtinNotificationSoundFileName(id: fileId)" in picker
    assert "return sound" in (args.after / "submodules/TelegramCore/Sources/TelegramEngine/Peers/NotificationSoundList.swift").read_text()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ("clean", "rerun", PEER, PICKER):
        with tempfile.TemporaryDirectory(prefix="nagramix-peer-notifications-") as folder:
            root = Path(folder)
            for name in (PEER, PICKER):
                data = (args.after / name).read_bytes() if scenario == "rerun" else (args.before / name).read_bytes()
                if scenario == name:
                    data += b"\n// Native drift\n"
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            snapshot = files(root)
            if scenario == "clean":
                module.apply_notification_exception_sound_catalog(root)
                assert all((root / n).read_bytes() == (args.after / n).read_bytes() for n in (PEER, PICKER))
            else:
                try:
                    module.apply_notification_exception_sound_catalog(root)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted native drift/reapplication")
                assert files(root) == snapshot, "Partial write on rejection"
    print(f"PASS: {len(after)} outputs, exactly peer editor+default preview changed; 23 modern+8 classic resources/IDs, cache-independent entries, exact reversal, 4 guard cases")
    print("Not executed: native compilation, UIKit/audio playback, APNs or physical iPhone delivery")


if __name__ == "__main__":
    main()

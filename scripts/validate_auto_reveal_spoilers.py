#!/usr/bin/env python3
"""Check spoiler overlay scope, reversibility, settings wiring and failure guards."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    patcher = ROOT / "ios/apply_features.py"
    helper = next(n for n in ast.parse(patcher.read_text()).body
                  if isinstance(n, ast.FunctionDef) and n.name == "apply_auto_reveal_spoilers")
    values = {}
    for node in helper.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("text_module", "media_module", "patches"):
                values[node.targets[0].id] = eval(compile(ast.Expression(node.value), "<patches>", "eval"),
                                                 {"__builtins__": {}}, values)
    patches = values["patches"]
    old, new = snapshot(args.before), snapshot(args.after)
    settings = {
        "submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift",
        "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
        "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings",
        "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings",
        "submodules/SettingsUI/Sources/NagramiXSettingsController.swift",
    }
    assert old.keys() == new.keys()
    assert {n for n in old if old[n] != new[n]} == patches.keys() | settings
    reversals = 0
    for name, (digest, replacements) in patches.items():
        assert old[name] == digest
        restored = (args.after / name).read_text()
        for original, replacement in reversed(replacements):
            assert restored.count(replacement) == 1, name
            restored = restored.replace(replacement, original, 1)
            reversals += 1
        assert restored.encode() == (args.before / name).read_bytes(), name

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ["clean", "rerun", *patches]:
        with tempfile.TemporaryDirectory(prefix="nagramix-auto-spoilers-") as folder:
            root = Path(folder)
            for name in patches:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(((args.after if scenario == "rerun" else args.before) / name).read_bytes())
            if scenario in patches:
                path = root / scenario
                path.write_bytes(path.read_bytes() + b"\n// native drift\n")
            before = snapshot(root)
            if scenario == "clean":
                module.apply_auto_reveal_spoilers(root)
                assert snapshot(root) == {n: new[n] for n in patches}
            else:
                try:
                    module.apply_auto_reveal_spoilers(root)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("Accepted drift/reapplication")
                assert snapshot(root) == before, "Partial write after guard failure"

    media_settings = (args.after / "submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift").read_text()
    for token in (
        'static let autoRevealSpoilers = "nagramix.messages.autoRevealSpoilers"',
        "autoRevealSpoilers: Bool = true",
        "UserDefaults.standard.object(forKey: Key.autoRevealSpoilers) as? Bool ?? true",
        "autoRevealSpoilers: Self.autoRevealSpoilersEnabled",
        "defaults.set(value.autoRevealSpoilers, forKey: Key.autoRevealSpoilers)",
        "previous.autoRevealSpoilers != value.autoRevealSpoilers",
        "NotificationCenter.default.post(name: Self.displayChangedNotification",
    ):
        assert token in media_settings, token
    assert "register(defaults:" not in media_settings
    ui_name = "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"
    ui, previous_ui = (args.after / ui_name).read_text(), (args.before / ui_name).read_text()
    stable = lambda text: dict(re.findall(r"case \.(\w+): return (\d+)\n", text.split("var stableId:", 1)[1].split("static func <", 1)[0]))
    ids, previous_ids = stable(ui), stable(previous_ui)
    assert {k: v for k, v in ids.items() if k != "autoRevealSpoilers"} == previous_ids
    assert ids["autoRevealSpoilers"] == "145" and "145" not in previous_ids.values()
    assert ui.count("case .autoRevealSpoilers, .hideBlockedMessages, .antiCaps,") == 2
    assert "case .autoRevealSpoilers: return 347" in ui
    assert ".autoRevealSpoilers(settings.media.autoRevealSpoilers)" in ui
    assert "updateAutoRevealSpoilers: { value in update { $0.media.autoRevealSpoilers = value } }" in ui
    assert "updated: arguments.updateAutoRevealSpoilers" in ui
    assert "return strings.nagramiXAutoRevealSpoilersSearchTerms" in ui
    for locale, title in (("ru", "Автораскрытие спойлеров"), ("en", "Auto-reveal spoilers")):
        text = (args.after / f"submodules/NagramiXCore/Resources/{locale}.lproj/Localizable.strings").read_text()
        key = "NagramiX.Settings.Messages.AutoRevealSpoilers"
        assert text.count(f'"{key}" = "{title}";') == 1
        assert text.count(f'"{key}.SearchTerms"') == 1

    node = (args.after / "submodules/TelegramUI/Sources/ChatControllerNode.swift").read_text()
    assert "forName: NagramiXMediaSettings.displayChangedNotification" in node
    assert "self.historyNode.requestMessageUpdate(messageId)" in node
    core = (args.after / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift").read_text()
    assert "NagramiXMediaSettings.update(value.media)" in core
    text = (args.after / (values["text_module"] + "/Sources/ChatMessageTextBubbleContentNode.swift")).read_text()
    assert "NagramiXMediaSettings.autoRevealSpoilersEnabled || self.displayContentsUnderSpoilers.value" in text
    # Auto-reveal never writes native manual reveal state: turning OFF restores
    # the native tap/selection state rather than persisting artificial taps.
    original_text = (args.before / (values["text_module"] + "/Sources/ChatMessageTextBubbleContentNode.swift")).read_text()
    for marker in ("private func updateDisplayContentsUnderSpoilers",):
        assert text.split(marker, 1)[1] == original_text.split(marker, 1)[1]
    media = (args.after / (values["media_module"] + "/Sources/ChatMessageInteractiveMediaNode.swift")).read_text()
    assert "&& !isSecretMedia && !isExtendedMediaPreview && !message.isSensitiveContent(platform: \"ios\")" in media
    # Paid previews and secret/sensitive branches remain ahead of/after the
    # ordinary spoiler branch; the exact reversal proves no payload mutation.
    status = media.split("var displaySpoiler = false", 1)[1]
    assert status.index("case .preview = extendedMedia") < status.index("!NagramiXMediaSettings.autoRevealSpoilersEnabled")
    assert "} else if isSecretMedia {\n            displaySpoiler = true" in status
    assert "} else if message.isSensitiveContent(platform: \"ios\") {" in status
    assert "strongSelf.internallyVisible != wasInternallyVisible" in media
    print(f"PASS: {len(new)} outputs, 9 changed; {reversals} exact reversals; 6 clean/rerun/drift cases, no partial writes")
    print("PASS: default ON/saved-choice wiring, stable IDs, search, live refresh, native manual state and special-media boundaries")
    print("Not executed: Apple SDK compilation, UIKit rendering, UserDefaults process relaunch, physical iPhone")


if __name__ == "__main__":
    main()

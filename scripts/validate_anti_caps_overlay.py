#!/usr/bin/env python3
"""Проверить область и защиту overlay анти-капса; не заменяет Swift XCTest."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENQUEUE = "submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift"
HELPER = "submodules/TelegramCore/Sources/NagramiXAntiCaps.swift"
TESTS = "submodules/TelegramCore/Tests/NagramiXAntiCapsTests.swift"
SETTINGS = "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"
CHANGED = {ENQUEUE, SETTINGS,
           "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift",
           "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
           "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings",
           "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings"}


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before, after):
    old, new = snapshot(before), snapshot(after)
    assert new.keys() - old.keys() == {HELPER, TESTS}
    assert not old.keys() - new.keys()
    changed = {name for name in old if old[name] != new[name]}
    assert ENQUEUE in changed and changed <= CHANGED
    overlay = ROOT / "ios/apply_features.py"
    function = next(node for node in ast.parse(overlay.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "apply_anti_caps")
    patches = ast.literal_eval(next(node.value for node in function.body
                                    if isinstance(node, ast.Assign)
                                    and any(isinstance(target, ast.Name) and target.id == "substitutions" for target in node.targets)))
    restored = (after / ENQUEUE).read_text()
    for original, replacement in reversed(patches):
        assert restored.count(replacement) == 1
        restored = restored.replace(replacement, original, 1)
    assert restored.encode() == (before / ENQUEUE).read_bytes()

    spec = importlib.util.spec_from_file_location("features", overlay)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ["clean", "drift", "helper_collision", "tests_collision"]:
        with tempfile.TemporaryDirectory(prefix="nagramix-anti-caps-") as folder:
            tree = Path(folder)
            path = tree / ENQUEUE
            path.parent.mkdir(parents=True)
            path.write_bytes((before / ENQUEUE).read_bytes())
            if scenario == "drift":
                path.write_text(path.read_text() + "\n// дрейф исходника\n")
            elif scenario.endswith("_collision"):
                collision = tree / (HELPER if scenario == "helper_collision" else TESTS)
                collision.parent.mkdir(parents=True, exist_ok=True)
                collision.write_text("// существующий файл\n")
            if scenario == "clean":
                module.apply_anti_caps(tree)
                for name in [ENQUEUE, HELPER, TESTS]:
                    assert (tree / name).read_bytes() == (after / name).read_bytes()
            unchanged = snapshot(tree)
            try:
                module.apply_anti_caps(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Дрейф/коллизия/повторное применение не отклонены")
            assert snapshot(tree) == unchanged, "Ошибка вызвала частичную запись"

    enqueue = (after / ENQUEUE).read_text()
    assert "let message = nagramiXAntiCapsMessage(originalMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)" in enqueue
    assert "ProfileLink" not in enqueue and "ProfileLinked" not in enqueue
    assert enqueue.count('"nagramix.messages.antiCaps"') == 1
    assert "isPremium: (transaction.getPeer(account.peerId) as? TelegramUser)?.isPremium ?? false" in enqueue
    for name, source in [(HELPER, "Sources/TelegramCore/NagramiXAntiCaps.swift"),
                         (TESTS, "Tests/TelegramCore/NagramiXAntiCapsTests.swift")]:
        assert (after / name).read_bytes() == (ROOT / "ios" / source).read_bytes()
    ui = (after / SETTINGS).read_text()
    old_ids = dict(re.findall(r"case \.(\w+): return (-?\d+)", (before / SETTINGS).read_text().split("var stableId: Int32", 1)[1].split("static func <", 1)[0]))
    new_ids = dict(re.findall(r"case \.(\w+): return (-?\d+)", ui.split("var stableId: Int32", 1)[1].split("static func <", 1)[0]))
    assert old_ids.pop("antiCaps", None) in (None, "141")
    assert new_ids.pop("antiCaps") == "141" and new_ids == old_ids
    assert ".antiCaps(settings.antiCaps)" in ui and "updateAntiCaps: { value in update { $0.antiCaps = value } }" in ui
    assert "antiCapsInfo" not in ui
    settings = (after / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift").read_text()
    assert 'static let antiCaps = "nagramix.messages.antiCaps"' in settings
    assert "antiCaps: defaults.object(forKey: Key.antiCaps) as? Bool ?? false" in settings
    assert "defaults.set(value.antiCaps, forKey: Key.antiCaps)" in settings
    for language in ["ru", "en"]:
        data = (after / f"submodules/NagramiXCore/Resources/{language}.lproj/Localizable.strings").read_text()
        keys = re.findall(r'^"([^"]+)"\s*=', data, re.M)
        assert len(keys) == len(set(keys)), language
        assert "NagramiX.Settings.Messages.AntiCaps" in keys
    print(f"Анти-капс: {len(old)} → {len(new)} файлов; {len(changed)} изменены, 2 добавлены; guards/scope/settings PASS. Swift XCTest не запускался.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    validate(args.before, args.after)

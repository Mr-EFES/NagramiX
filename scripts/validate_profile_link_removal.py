#!/usr/bin/env python3
"""Проверить полное удаление функции и точную область изменения native overlay."""

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ENQUEUE = "submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift"
REMOVED = {
    "submodules/SettingsUI/Sources/NagramiXProfileLinkSettingsController.swift",
    "submodules/TelegramCore/Sources/NagramiXProfileLinkedMessages.swift",
    "submodules/TelegramCore/Tests/NagramiXProfileLinkedMessagesTests.swift",
}
CHANGED = {
    ENQUEUE,
    "submodules/TelegramCore/Tests/NagramiXAntiCapsTests.swift",
    "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift",
    "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
    "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings",
    "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings",
    "submodules/SettingsUI/Sources/NagramiXSettingsController.swift",
}


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before, after):
    old, new = snapshot(before), snapshot(after)
    assert old.keys() - new.keys() == REMOVED
    assert not new.keys() - old.keys()
    changed = {name for name in new if old[name] != new[name]}
    assert changed == CHANGED
    for path in after.rglob("*.swift"):
        source = path.read_text()
        assert not any(token in source for token in ["profileLink", "ProfileLink", "ProfileLinked"]), path
    patcher = (ROOT / "ios/apply_features.py").read_text()
    assert "apply_profile_link_messages" not in patcher
    assert "NagramiXProfileLinkedMessage" not in patcher
    assert "nagramiXProfileLink" not in patcher
    assert '"profile_link_messages"' not in (ROOT / "product/features/registry.json").read_text()

    # В native send удалены только lookup профиля и последняя разметка.
    previous = (before / ENQUEUE).read_text()
    lookup = "            let profileLinkTarget = nagramiXProfileLinkTarget(transaction: transaction, accountPeerId: account.peerId)\n"
    assert previous.count(lookup) == 1
    previous = previous.replace(lookup, "", 1)
    old_chain = "                let uncappedMessage = nagramiXAntiCapsMessage(anonymousMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)\n                let message = nagramiXProfileLinkedMessage(uncappedMessage, targetPeerId: profileLinkTarget, isSecretChat: peerId.namespace == Namespaces.Peer.SecretChat)\n"
    new_chain = "                let message = nagramiXAntiCapsMessage(anonymousMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)\n"
    assert previous.count(old_chain) == 1
    assert previous.replace(old_chain, new_chain, 1) == (after / ENQUEUE).read_text()
    enqueue = (after / ENQUEUE).read_text()
    assert "let anonymousMessage = nagramiXAnonymousStickerMessage(originalMessage, enabled: anonymousStickersEnabled)" in enqueue
    assert enqueue.index("let anonymousMessage =") < enqueue.index(new_chain.strip())
    assert enqueue.count('"nagramix.messages.antiCaps"') == 1

    def ids(text):
        block = text.split("var stableId: Int32", 1)[1].split("static func <", 1)[0]
        return dict(re.findall(r"case \.(\w+): return (-?\d+)", block))
    name = "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"
    old_ids = ids((before / name).read_text())
    assert old_ids.pop("profileLinkSettings") == "136"
    assert ids((after / name).read_text()) == old_ids
    assert "136" not in old_ids.values()
    settings = (after / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift").read_text()
    assert "selfieCountdown: defaults.object(forKey: Key.selfieCountdown) as? Bool ?? true" in settings
    assert "useRearCameraForVideoMessages: defaults.object(forKey: Key.useRearCameraForVideoMessages) as? Bool ?? true" in settings
    tests = (after / "submodules/TelegramCore/Tests/NagramiXAntiCapsTests.swift").read_text()
    assert "func testMessageMetadataAndFormattingStayIntact" in tests
    assert "XCTAssertEqual(threadId, 10)" in tests and "XCTAssertEqual(grouping, 20)" in tests
    assert "XCTAssertEqual(correlation, 30)" in tests
    assert tests.count("func test") == (before / "submodules/TelegramCore/Tests/NagramiXAntiCapsTests.swift").read_text().count("func test")
    for lang in ["ru", "en"]:
        name = f"submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings"
        previous = (before / name).read_text()
        expected = "".join(line for line in previous.splitlines(keepends=True) if '"NagramiX.ProfileLink.' not in line)
        assert expected == (after / name).read_text()
        keys = re.findall(r'^"([^"]+)"\s*=', expected, re.M)
        assert len(keys) == len(set(keys))
    registry = json.loads((ROOT / "product/features/registry.json").read_text())
    assert not any(item["id"] == "profile_link_messages" for item in registry["features"])
    print(f"PASS removal: {len(old)}→{len(new)} outputs, 3 removed/7 changed/{len(new) - 7} unchanged; exact send delta, settings IDs/defaults, no runtime symbols. Native/device pending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

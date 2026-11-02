#!/usr/bin/env python3
"""Check author-selection/deletion integration boundaries; Apple runtime is separate."""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCHED = {
    "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
    "submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift",
    "submodules/TelegramUI/Sources/ChatHistoryListNode.swift",
    "submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessagesInteractively.swift",
}
COPIED = {
    "submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXAuthorSelection.swift": "ios/Sources/TelegramCore/NagramiXAuthorSelection.swift",
    "submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift": "ios/Sources/TelegramCore/NagramiXMessageArchive.swift",
    "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift": "ios/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
    "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings": "ios/Sources/NagramiXCore/Resources/ru.lproj/Localizable.strings",
    "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings": "ios/Sources/NagramiXCore/Resources/en.lproj/Localizable.strings",
}


def snapshot(folder):
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


def validate(before, after):
    old, new = snapshot(before), snapshot(after)
    assert old.keys() == new.keys(), "Native file set changed"
    changed = {name for name in old if old[name] != new[name]}
    assert PATCHED <= changed <= PATCHED | COPIED.keys()
    for name, source in COPIED.items():
        assert (after / name).read_bytes() == (ROOT / source).read_bytes(), name

    spec = importlib.util.spec_from_file_location("features", ROOT / "ios/apply_features.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Simulate each upstream drift, including the last input, and reapplication.
    for drift in [*sorted(PATCHED), None]:
        with tempfile.TemporaryDirectory(prefix="nagramix-author-delete-") as directory:
            tree = Path(directory)
            for name in PATCHED:
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((before / name).read_bytes())
            if drift is None:
                module.apply_author_selection_archive_deletion(tree)
                for name in PATCHED:
                    assert (tree / name).read_bytes() == (after / name).read_bytes(), name
            else:
                with (tree / drift).open("a") as stream:
                    stream.write("\n// simulated drift\n")
            unchanged = snapshot(tree)
            try:
                module.apply_author_selection_archive_deletion(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Drift/reapplication was accepted")
            assert snapshot(tree) == unchanged, "Failed input caused a partial write"

    load = (after / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift").read_text()
    block = load.split("}, deleteSelectedMessages:", 1)[1].split("}, reportSelectedMessages:", 1)[0]
    assert "messageIds: liveIds, keepUpdated: false" in block
    assert "!archivedIds.contains($0) || transaction.getMessage($0) != nil" in block, "Expired placeholders lost native permissions"
    assert "messageIds.allSatisfy" not in block
    assert "removeLocal" not in block, "Archive removed before confirmation"
    assert "options: [.deleteLocally]" in block, "No archive-only confirmation"
    assert "presentClearCacheSuggestion" not in block.split("nagramiXAuthorDeleteUnavailable", 1)[1].split("} else {", 1)[0]

    delete = (after / "submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessagesInteractively.swift").read_text()
    partition = delete.index("let localIds = Set(messageIds.filter")
    assert delete.index("messageIds.removeAll { localIds.contains($0.messageId) }", partition) < delete.index("cloudChatAddRemoveMessagesOperation", partition)
    assert "_internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: Array(localIds))" in delete
    assert "archive.isLocallyDeletedMessage(id: $0.messageId) && transaction.getMessage($0.messageId) == nil" in delete, "Live placeholders treated as absent server IDs"
    admin = (after / "submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift").read_text()
    assert "nagramiXSelectedDeletionWarning(messageIds.count)" in admin
    assert "nagramiXLocalCopiesDeletionWarning(archivedCount)" in admin
    history = (after / "submodules/TelegramUI/Sources/ChatHistoryListNode.swift").read_text()
    assert "pendingRemovedMessages: pendingRemovedMessages.union(update.4)" in history
    print(f"PASS: {len(old)} native files; {len(changed)} scoped files changed; 4 drift guards, rerun and confirmation/deletion boundaries verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

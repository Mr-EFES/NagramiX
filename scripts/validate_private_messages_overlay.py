#!/usr/bin/env python3
"""Проверить область overlay стикеров/блокировки; не заменяет XCTest и iPhone."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORE = "submodules/TelegramCore/Sources/"
UI = "submodules/TelegramUI/Sources/"


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before, after):
    patcher = ROOT / "ios/apply_features.py"
    function = next(node for node in ast.parse(patcher.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "apply_anonymous_stickers_and_blocked_filter")
    values = {node.targets[0].id: ast.literal_eval(node.value)
              for node in function.body if isinstance(node, ast.Assign)
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"hashes", "substitutions", "copies"}}
    native, patches, copies = values["hashes"], values["substitutions"], values["copies"]
    old, new = snapshot(before), snapshot(after)
    assert new.keys() - old.keys() == copies.keys()
    assert not old.keys() - new.keys()
    settings_files = {"submodules/NagramiXCore/Sources/NagramiXTabSettings.swift",
                      "submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift",
                      "submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings",
                      "submodules/NagramiXCore/Resources/en.lproj/Localizable.strings",
                      "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"}
    changed = {name for name in old if old[name] != new[name]}
    assert native.keys() <= changed <= native.keys() | settings_files
    restored = {name: (after / name).read_text() for name in native}
    for name, original, replacement in reversed(patches):
        assert restored[name].count(replacement) == 1, name
        restored[name] = restored[name].replace(replacement, original, 1)
    for name in native:
        assert restored[name].encode() == (before / name).read_bytes(), name
    for name, original in copies.items():
        assert (after / name).read_bytes() == (ROOT / "ios" / original).read_bytes(), name

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scenarios = ["clean"] + list(native) + list(copies)
    for scenario in scenarios:
        with tempfile.TemporaryDirectory(prefix="nagramix-private-messages-") as directory:
            tree = Path(directory)
            for name in native:
                path = tree / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((before / name).read_bytes())
            if scenario in native:
                path = tree / scenario
                path.write_text(path.read_text() + "\n// дрейф исходника\n")
            elif scenario in copies:
                path = tree / scenario
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("// коллизия файла\n")
            else:
                module.apply_anonymous_stickers_and_blocked_filter(tree)
                for name in native.keys() | copies.keys():
                    assert (tree / name).read_bytes() == (after / name).read_bytes(), name
            unchanged = snapshot(tree)
            try:
                module.apply_anonymous_stickers_and_blocked_filter(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Дрейф/коллизия/повторное применение не отклонены")
            assert snapshot(tree) == unchanged, "Отказ вызвал частичную запись"

    upload = (after / (CORE + "PendingMessages/PendingMessageUploadedContent.swift")).read_text()
    branch = upload.split("if let anonymous = attributes.first", 1)[1].split("if let resource = file.resource as? CloudDocumentMediaResource", 1)[0]
    assert "guard let source = anonymous.source else { return .fail(.generic) }" in branch
    assert "transformOutgoingMessageMedia: nil" in branch and "forceReupload: true" in branch
    assert "anonymousStickerSource: source" in branch
    assert "anonymousStickerSource == nil ? maybePredownloadedFileResource" in upload
    assert "forceRefresh: forceReupload) : .single(.none)" in upload
    direct = upload.split("if anonymousStickerSource != nil {", 1)[1].split("} else {", 1)[0]
    assert "multipartUpload(" in direct and "messageMediaPreuploadManager.upload" not in direct
    # Штатный mapper действительно кодирует отсутствующую ссылку пустым sticker set.
    mapper = upload.split("func inputDocumentAttributesFromFileAttributes", 1)[1].split("private enum UploadedMediaTransform", 1)[0]
    assert "var stickerSet: Api.InputStickerSet = .inputStickerSetEmpty" in mapper
    original_mapper = (before / (CORE + "PendingMessages/PendingMessageUploadedContent.swift")).read_text().split("func inputDocumentAttributesFromFileAttributes", 1)[1].split("private enum UploadedMediaTransform", 1)[0]
    assert mapper == original_mapper
    enqueue = (after / (CORE + "PendingMessages/EnqueueMessage.swift")).read_text()
    assert enqueue.index("let anonymousMessage = nagramiXAnonymousStickerMessage") < enqueue.index("let message = nagramiXAntiCapsMessage(anonymousMessage")
    assert "ProfileLink" not in enqueue and "ProfileLinked" not in enqueue
    assert "case _ as NagramiXAnonymousStickerMessageAttribute:\n            return true" in enqueue
    registry = (after / (CORE + "Account/AccountManager.swift")).read_text()
    assert "declareEncodable(NagramiXAnonymousStickerMessageAttribute.self" in registry

    provider = (after / (CORE + "NagramiXBlockedMessageFilter.swift")).read_text()
    assert "contacts.getBlocked(flags: 0, offset: offset, limit: 200)" in provider
    assert "loadPage(offset: Int32(nextOffset), collected: ids, generation: generation)" in provider
    assert "self.syncGeneration == generation" in provider and "changes: self.pendingChanges" in provider
    assert "cache.accountPeerId == self.peerId.toInt64()" in provider
    assert "contacts.block(" not in provider and "deleteMessages" not in provider
    assert "shouldHide(authorId: message.author?.id, isIncoming:" in provider
    assert "forwardInfo" not in provider
    blocks = (after / (CORE + "TelegramEngine/Privacy/BlockedPeers.swift")).read_text()
    original_blocks = (before / (CORE + "TelegramEngine/Privacy/BlockedPeers.swift")).read_text()
    assert blocks.split("func _internal_requestUpdatePeerIsBlockedFromStories", 1)[1] == original_blocks.split("func _internal_requestUpdatePeerIsBlockedFromStories", 1)[1]
    context = (after / (CORE + "TelegramEngine/Privacy/BlockedPeersContext.swift")).read_text()
    assert context.count("if case .blocked = subject {") == 3
    entries = (after / (UI + "ChatHistoryEntriesForView.swift")).read_text()
    assert entries.index("sourceEntries.sort(by:") < entries.index("nagramiXBlockedMessageFilter.shouldHide(message")
    history = (after / (UI + "ChatHistoryListNode.swift")).read_text()
    assert "context.account.nagramiXBlockedMessageFilter.updates" in history
    assert "self.chatHistoryLocationValue == update.2, NagramiXBlockedMessageFilter.enabled" in history
    assert "view.entries.allSatisfy" in history and "count: historyMessageCount, highlight: false" in history

    settings = (after / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift").read_text()
    for key in ["anonymousStickers", "hideBlockedMessages"]:
        assert f"{key}: defaults.object(forKey: Key.{key}) as? Bool ?? true" in settings
        assert f"defaults.set(value.{key}, forKey: Key.{key})" in settings
    assert "NagramiXBlockedMessagesSettingsChanged" in settings
    ui_path = "submodules/SettingsUI/Sources/NagramiXSettingsController.swift"
    def ids(text):
        block = text.split("var stableId: Int32", 1)[1].split("static func <", 1)[0]
        return dict(re.findall(r"case \.(\w+): return (-?\d+)", block))
    ui = (after / ui_path).read_text()
    new_ids = ids(ui)
    old_ids = ids((before / ui_path).read_text())
    assert old_ids.pop("anonymousStickers", None) in (None, "142")
    assert old_ids.pop("hideBlockedMessages", None) in (None, "143")
    assert new_ids.pop("anonymousStickers") == "142" and new_ids.pop("hideBlockedMessages") == "143"
    assert new_ids == old_ids
    assert ".anonymousStickers(settings.anonymousStickers)" in ui and ".hideBlockedMessages(settings.hideBlockedMessages)" in ui
    assert "anonymousStickersInfo" not in ui and "hideBlockedMessagesInfo" not in ui
    for language in ["ru", "en"]:
        data = (after / f"submodules/NagramiXCore/Resources/{language}.lproj/Localizable.strings").read_text()
        keys = re.findall(r'^"([^"]+)"\s*=', data, re.M)
        assert len(keys) == len(set(keys)), language
    print(f"Приватность: {len(old)} → {len(new)} файлов; {len(changed)} изменены/3 добавлены; {len(patches)} обратимых замен, 9 drift/3 collisions/reapply PASS. XCTest/iPhone не запускались.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

#!/usr/bin/env python3
"""Проверить точную область правки архивного выделения без Xcode и устройства."""

import argparse
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UI = "submodules/TelegramUI/Sources/"
PANEL = "submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift"
ARCHIVE = "submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift"


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def validate(before, after):
    patcher = ROOT / "ios/apply_features.py"
    function = next(node for node in ast.parse(patcher.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == "apply_archived_selection_actions_fix")
    values = {node.targets[0].id: ast.literal_eval(node.value)
              for node in function.body if isinstance(node, ast.Assign)
              and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id in {"hashes", "substitutions", "copies"}}
    native, patches, copies = values["hashes"], values["substitutions"], values["copies"]
    assert len(native) == 6 and len(patches) == 15 and len(copies) == 1
    old, new = snapshot(before), snapshot(after)
    assert new.keys() - old.keys() == copies.keys()
    assert not old.keys() - new.keys()
    changed = {name for name in old if old[name] != new[name]}
    assert native.keys() <= changed <= native.keys() | {ARCHIVE}
    methods = (ROOT / "ios/Sources/ChatMessageSelectionInputPanelNode/NagramiXArchiveSelectionActions.swift.inc").read_text().rstrip("\n") + "\n\n"
    restored = {name: (after / name).read_text() for name in native}
    for name, original, replacement in reversed(patches):
        if replacement == "__NAGRAMIX_ARCHIVE_SELECTION_ACTIONS__":
            replacement = methods
        assert restored[name].count(replacement) == 1, name
        restored[name] = restored[name].replace(replacement, original, 1)
    for name, expected in native.items():
        assert hashlib.sha256(restored[name].encode()).hexdigest() == expected
        assert restored[name].encode() == (before / name).read_bytes(), name
    for name, source in copies.items():
        assert (after / name).read_bytes() == (ROOT / "ios" / source).read_bytes()
    assert (after / ARCHIVE).read_bytes() == (ROOT / "ios/Sources/TelegramCore/NagramiXMessageArchive.swift").read_bytes()

    spec = importlib.util.spec_from_file_location("features", patcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for scenario in ["clean", *native, *copies]:
        with tempfile.TemporaryDirectory(prefix="nagramix-selection-") as directory:
            tree = Path(directory)
            for name in native:
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((before / name).read_bytes())
            if scenario in native:
                target = tree / scenario
                target.write_text(target.read_text() + "\n// changed input\n")
            elif scenario in copies:
                target = tree / scenario
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("// collision\n")
            else:
                module.apply_archived_selection_actions_fix(tree)
                for name in native.keys() | copies.keys():
                    assert (tree / name).read_bytes() == (after / name).read_bytes()
            unchanged = snapshot(tree)
            try:
                module.apply_archived_selection_actions_fix(tree)
            except SystemExit:
                pass
            else:
                raise AssertionError("Drift/collision/reapply accepted")
            assert snapshot(tree) == unchanged, "Partial write on rejected input"

    entries = (after / "submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift").read_text()
    assert "let foundPeers = foundPeers.filter { $0.0.id != savedMessagesPeer?.id }" in entries
    assert entries.index("let foundPeers = foundPeers.filter") < entries.index("var foundPeerIds = Set<EnginePeer.Id>()")
    forward = (after / (UI + "ChatControllerForwardMessages.swift")).read_text()
    assert "let peers = peers.filter { recipientIds.insert($0.id).inserted }" in forward
    assert forward.index("let peers = peers.filter") < forward.index("// Enforce the recipient contract")
    assert "guard !peers.isEmpty else { return }" in forward
    assert "sortedMessages.count == Set(messageIds).count" in forward
    assert "hasArchivedMessages ? (transferMode == .copyAsNew ? .copyAsNew : .copyToSingleRecipient) : transferMode" in forward
    assert "message.isCopyProtected()" in forward and "message.containsSecretMedia" in forward
    assert "nagramiXArchivedCopyAlert" in forward and "NagramiXArchivedMediaCopy" in forward

    panel = (after / PANEL).read_text()
    availability = panel.split("private func updateActions()", 1)[1].split("public func updateTheme", 1)[0]
    assert "self.actions = nil" in availability and "self.canDeleteMessagesDisposable.set(nil)" in availability
    assert "nagramiXSelectedMessagesSignal(context: context, ids: selectedIds, keepUpdated: true)" in availability
    assert "messages.count == selectedIds.count" in availability
    assert "options.subtract([.forward, .externalShare])" in availability
    assert "resolvedActions.options.intersection([.forward, .externalShare])" in availability
    for field in ["banAuthor", "banAuthors", "disableDelete", "setTag", "editTags"]:
        assert f"{field}: nativeActions.{field}" in availability
    assert "nativeActions.isCopyProtected || resolvedActions.isCopyProtected" in availability
    assert "self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds" in availability
    signal = panel.split("private func nagramiXSelectedMessagesSignal", 1)[1].split("@objc private func", 1)[0]
    assert "keepUpdated: Bool = false" in signal and "take(keepUpdated ? Int.max : 1)" in signal
    assert "context.engine.data.subscribe" in signal and "nagramiXMessageArchive.updates" in signal
    assert "interactionMessage(id: id, liveMessage:" in signal
    transfer = panel.split("private func nagramiXPerformSelectionTransfer", 1)[1].split("private func update(transition", 1)[0]
    assert "ids: selectedIds)" in transfer and "keepUpdated: true" not in transfer
    assert "self.nagramiXSelectionGeneration == generation" in transfer
    assert "isCopyProtected" in transfer and "canCopyMessagesWithoutSource?(messages) == true" in transfer

    core = (after / ARCHIVE).read_text()
    resolver = core.split("public func interactionMessage", 1)[1].split("public func deletedMessage", 1)[0]
    assert "!liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent })" in resolver
    assert "retainedMessage.id == id" in resolver and "$0 is NagramiXArchivedMessageAttribute" in resolver
    assert "liveMessage?.id == id" in resolver and "return liveMessage" in resolver
    assert "self.deletedMessage(id: id)" in resolver and "self.snapshotForExpiredMessage(id: id)" in resolver
    menus = (after / (UI + "ChatInterfaceStateContextMenus.swift")).read_text()
    assert "NagramiXMessageArchive.interactionMessage(id: messageId, liveMessage: live, retainedMessage: retained)" in menus
    assert "Item.Peer.CopyProtectionEnabled" in menus and "Item.Peer.MyCopyProtectionEnabled" in menus
    share = (after / (UI + "Chat/ChatControllerLoadDisplayNode.swift")).read_text().split("shareSelectedMessages: {", 1)[1].split("updateTextInputStateAndMode:", 1)[0]
    assert "selectedIds.sorted().compactMap" in share and "interactionMessage(id: id" in share
    assert "messages.count == selectedIds.count" in share and "selectionState?.selectedIds == selectedIds" in share
    assert "ShareControllerParams(subject: .messages(messages.sorted" in share
    assert "immediateExternalShare: true" in share
    tests = (after / next(iter(copies))).read_text()
    assert tests.count("func test") == 7
    print(f"PASS: {len(new)} outputs; {len(changed)} changed, 1 added; 15 exact reversals; 6 drift guards/collision/reapply; action boundaries. Native XCTest/device pending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    args = parser.parse_args()
    validate(args.before, args.after)

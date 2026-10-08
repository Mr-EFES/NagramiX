#!/usr/bin/env python3
"""Apply the isolated NagramiX next-version feature overlay."""

from __future__ import annotations

import json
import shutil
import re
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Pinned patch anchor was not found ({label}): {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_unique(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    occurrence_count = text.count(old)
    if occurrence_count != 1:
        raise SystemExit(f"Pinned patch anchor must occur exactly once, found {occurrence_count} ({label}): {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_between(path: Path, start: str, end: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise SystemExit(f"Pinned legacy patch range was not found ({label}): {path}")
    path.write_text(text[:start_index] + new + text[end_index:], encoding="utf-8")


def localize_debug_titles(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'title: "([^"\\]*(?:\\.[^"\\]*)*)"', lambda match: f'title: presentationData.strings.nagramiXDebugLocalized("{match.group(1)}")', text)
    text = re.sub(r'title: \.text\("([^"\\]*(?:\\.[^"\\]*)*)"\)', lambda match: f'title: .text(presentationData.strings.nagramiXDebugLocalized("{match.group(1)}"))', text)
    text = text.replace('text: "Now restart the app"', 'text: presentationData.strings.nagramiXDebugLocalized("Now restart the app")')
    text = text.replace('text = "Done"', 'text = presentationData.strings.nagramiXDebugLocalized("Done")')
    text = text.replace('text = "Failed"', 'text = presentationData.strings.nagramiXDebugLocalized("Failed")')
    path.write_text(text, encoding="utf-8")


def apply_telegram_theme_color_compatibility(source: Path) -> dict[str, bytes]:
    # Cloud theme settings can contain legacy RGB24 values as well as ARGB.
    # Keep the supplied RGB and any nonzero alpha; supply only the missing
    # opaque alpha byte. Do not alter palettes, UIColor globally, or theme files.
    patches = {
        "submodules/TelegramPresentationData/Sources/MakePresentationTheme.swift": [
            ("settings.accentColor", 4),
            ("$0", 4),
        ],
        "submodules/SettingsUI/Sources/Themes/ThemeSettingsAccentColorItem.swift": [("settings.accentColor", 1)],
        "submodules/TelegramUI/Components/Settings/ThemeAccentColorScreen/Sources/ThemeAccentColorController.swift": [("themeSettings.accentColor", 1)],
        "submodules/TelegramUI/Sources/OpenResolvedUrl.swift": [("settings.accentColor", 1)],
    }
    expected_sources: dict[str, bytes] = {}
    for name, conversions in patches.items():
        path = source / name
        text = path.read_text(encoding="utf-8")
        for value, expected_count in conversions:
            old = f"UIColor(argb: {value})"
            new = f"UIColor(argb: {value} | ({value} >> 24 == 0 ? 0xff000000 : 0))"
            count = text.count(old)
            if count != expected_count:
                raise SystemExit(f"Pinned theme color conversion must occur {expected_count} times, found {count}: {name}: {value}")
            text = text.replace(old, new)
        expected_sources[name] = text.encode("utf-8")
        path.write_bytes(expected_sources[name])
    return expected_sources


def apply_telegram_theme_variant_compatibility(source: Path) -> dict[str, bytes]:
    # Match Telegram's dark/light cloud-theme overload: an unavailable exact
    # base must try the same appearance family before the first (often day) entry.
    factory = source / "submodules/TelegramPresentationData/Sources/MakePresentationTheme.swift"
    for settings, indent in (("cloudTheme.settings", "    "), ("info.theme.settings", "            ")):
        old = f"{indent}}} else if let firstSettings = {settings}?.first {{\n{indent}    settings = firstSettings"
        new = f"""{indent}}} else if let baseTheme = baseTheme, let compatibleSettings = {settings}?.first(where: {{
{indent}    switch baseTheme {{
{indent}    case .night, .tinted:
{indent}        return $0.baseTheme == .night || $0.baseTheme == .tinted
{indent}    case .classic, .day:
{indent}        return $0.baseTheme == .classic || $0.baseTheme == .day
{indent}    }}
{indent}}}) {{
{indent}    settings = compatibleSettings
{indent}}} else if let firstSettings = {settings}?.first {{
{indent}    settings = firstSettings"""
        # Only the exact-base overload, not the existing dark: overload.
        text = factory.read_text(encoding="utf-8")
        marker = "public func makePresentationTheme(cloudTheme: TelegramTheme, baseTheme:"
        if settings == "info.theme.settings":
            marker = "public func makePresentationTheme(mediaBox: MediaBox, themeReference:"
        if text.count(marker) != 1:
            raise SystemExit(f"Pinned cloud theme overload must occur once: {marker}")
        start = text.index(marker)
        prefix, body = text[:start], text[start:]
        if body.count(old) != 1 or f"let compatibleSettings = {settings}?.first(where:" in body:
            raise SystemExit(f"Pinned cloud theme base fallback must occur once: {settings}")
        factory.write_text(prefix + body.replace(old, new, 1), encoding="utf-8")

    picker = source / "submodules/SettingsUI/Sources/ThemePickerController.swift"
    replace_unique(
        picker,
        "selectThemeImpl?(nil, initialThemeReference, true)",
        "selectThemeImpl?(theme.referenceTheme.baseTheme, initialThemeReference, true)",
        "Preserve the stock chat-theme preview base when applying a preset",
    )
    replace_unique(
        picker,
        """    selectThemeImpl = { baseTheme, theme, preset in
        guard let presentationTheme = makePresentationTheme(mediaBox: context.sharedContext.accountManager.mediaBox, themeReference: theme) else {""",
        """    selectThemeImpl = { baseTheme, theme, preset in
        guard let presentationTheme = makePresentationTheme(mediaBox: context.sharedContext.accountManager.mediaBox, themeReference: theme, baseTheme: baseTheme) else {""",
        "Resolve the chosen stock variant and its wallpaper before applying it",
    )
    return {str(path.relative_to(source)): path.read_bytes() for path in (factory, picker)}


def apply_media_controls(source: Path, overlay: Path) -> None:
    # Foundation-only preferences avoid a LocalMediaResources -> presentation
    # data -> MediaResources -> LocalMediaResources dependency cycle.
    target = source / "submodules/NagramiXMediaSettings"
    if target.exists():
        raise SystemExit(f"NagramiXMediaSettings already exists: {target}")
    shutil.copytree(overlay / "Sources/NagramiXMediaSettings", target)
    shutil.copy2(overlay / "Sources/SettingsUI/NagramiXPercentageItem.swift", source / "submodules/SettingsUI/Sources/NagramiXPercentageItem.swift")

    modules = [
        ("submodules/SettingsUI", '        "//submodules/AccountContext:AccountContext",\n'),
        ("submodules/TelegramUI", '        "//submodules/SettingsUI:SettingsUI",\n'),
        ("submodules/LegacyMediaPickerUI", '        "//submodules/TelegramCore:TelegramCore",\n'),
        ("submodules/LocalMediaResources", '        "//submodules/TelegramCore:TelegramCore",\n'),
        ("submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode", '        "//submodules/TelegramCore",\n'),
        ("submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode", '        "//submodules/TelegramCore",\n'),
    ]
    for module, anchor in modules:
        replace_unique(source / module / "BUILD", anchor, anchor + '        "//submodules/NagramiXMediaSettings:NagramiXMediaSettings",\n', f"{module} media settings dependency")

    picker = source / "submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift"
    fetch = source / "submodules/LocalMediaResources/Sources/FetchPhotoLibraryImageResource.swift"
    root = source / "submodules/TelegramUI/Sources/TelegramRootController.swift"
    static_sticker = source / "submodules/TelegramUI/Components/Chat/ChatMessageStickerItemNode/Sources/ChatMessageStickerItemNode.swift"
    animated_sticker = source / "submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift"
    for path in (picker, fetch, root, static_sticker, animated_sticker):
        replace_unique(path, "import Foundation\n", "import Foundation\nimport NagramiXMediaSettings\n", f"{path.name} media settings import")

    # Snapshot settings once per enqueue/fetch, never rewrite file uploads,
    # previews, video encoding, explicit JPEG XL exports or existing resources.
    replace_unique(picker, "        let disposable = SSignal.combineSignals(signals).start(next: { anyValues in\n", "        let mediaSettings = NagramiXMediaSettings.current\n        let disposable = SSignal.combineSignals(signals).start(next: { anyValues in\n", "Snapshot outgoing photo preferences")
    replace_unique(picker, "let maxSize = item.forceHd ? CGSize(width: 2560.0, height: 2560.0) : CGSize(width: 1280.0, height: 1280.0)", "let maxSize = (item.forceHd || mediaSettings.sendLargePhotos) ? CGSize(width: 2560.0, height: 2560.0) : CGSize(width: 1280.0, height: 1280.0)", "Enable native HD photo dimensions")
    replace_unique(picker, "compressImageToJPEG(scaledImage, quality: 0.6, tempFilePath: tempFile.path)", "scaledImage.jpegData(compressionQuality: CGFloat(mediaSettings.jpegQuality))", "Encode prepared photo using selected JPEG quality")
    replace_unique(picker, "let scaledSize = size.aspectFittedOrSmaller(CGSize(width: 1280.0, height: 1280.0))", "let maxSide: CGFloat = (item.forceHd || mediaSettings.sendLargePhotos) ? 2560.0 : 1280.0\n                                        let scaledSize = size.aspectFittedOrSmaller(CGSize(width: maxSide, height: maxSide))", "Keep asset representation dimensions consistent with HD resource")
    replace_unique(picker, "forceHd: item.forceHd)", "forceHd: item.forceHd || mediaSettings.sendLargePhotos)", "Carry native HD flag into photo library resource")

    replace_unique(fetch, "    return Signal { subscriber in\n        let queue = ThreadPoolQueue(threadPool: fetchPhotoWorkers)", "    return Signal { subscriber in\n        let mediaSettings = NagramiXMediaSettings.current\n        let queue = ThreadPoolQueue(threadPool: fetchPhotoWorkers)", "Snapshot photo library compression preferences")
    # Explicit width/height and JPEG XL formats remain the stock export path.
    replace_unique(fetch, "compressImageToJPEG(scaledImage, quality: 0.6, tempFilePath: tempFile.path)", "((width == nil && height == nil && format == nil) ? scaledImage.jpegData(compressionQuality: CGFloat(mediaSettings.jpegQuality)) : compressImageToJPEG(scaledImage, quality: 0.6, tempFilePath: tempFile.path))", "Encode photo library JPEG with selected quality")
    replace_unique(root, "compressImageToJPEG(image, quality: 0.7, tempFilePath: tempFile.path)", "image.jpegData(compressionQuality: CGFloat(NagramiXMediaSettings.current.jpegQuality))", "Apply JPEG preference to final outgoing photo story")

    replace_unique(static_sticker, "        let displaySize = CGSize(width: 184.0, height: 184.0)", "        let mediaSettings = NagramiXMediaSettings.current\n        let stickerScale = CGFloat(mediaSettings.stickerScale)\n        let displaySize = CGSize(width: 184.0 * stickerScale, height: 184.0 * stickerScale)", "Scale static sticker layout")
    replace_unique(static_sticker, "font: item.presentationData.messageEmojiFont,", "font: item.presentationData.messageEmojiFont.withSize(max(1.0, item.presentationData.messageEmojiFont.pointSize * stickerScale)),", "Scale static large emoji using existing typeface")
    replace_unique(animated_sticker, "        var displaySize = CGSize(width: 180.0, height: 180.0)", "        let mediaSettings = NagramiXMediaSettings.current\n        let stickerScale: CGFloat = self.telegramDice == nil ? CGFloat(mediaSettings.stickerScale) : 1.0\n        var displaySize = CGSize(width: 180.0 * stickerScale, height: 180.0 * stickerScale)", "Scale animated stickers and standalone emoji, keep dice stock")
    replace_unique(animated_sticker, "displaySize = CGSize(width: 240.0, height: 240.0)", "displaySize = CGSize(width: 240.0 * stickerScale, height: 240.0 * stickerScale)", "Scale video sticker layout")
    replace_unique(animated_sticker, "let font = Font.regular(fontSizeForEmojiString(item.message.text))", "let font = Font.regular(max(1.0, fontSizeForEmojiString(item.message.text) * stickerScale))", "Scale standalone emoji text without changing inline text")
    replace_unique(static_sticker, "                dateText: dateText,", '                dateText: mediaSettings.showStickerTime ? dateText : "",', "Hide only static sticker timestamp, keep delivery/reaction node")
    replace_unique(animated_sticker, "                dateText: dateText,", '                dateText: (mediaSettings.showStickerTime || telegramDice != nil) ? dateText : "",', "Hide only sticker/emoji time, keep dice and other statuses")

    # Reuse the existing visible-message invalidation path. Preferences do not
    # poll and neither sending nor the stock action/selection handlers change.
    chat_node = source / "submodules/TelegramUI/Sources/ChatControllerNode.swift"
    replace_unique(chat_node, "import Foundation\n", "import Foundation\nimport NagramiXMediaSettings\n", "Observe sticker presentation preferences")
    replace_unique(chat_node, "    private var nagramiXDeletedLabelObserver: NSObjectProtocol?\n", "    private var nagramiXDeletedLabelObserver: NSObjectProtocol?\n    private var nagramiXMediaDisplayObserver: NSObjectProtocol?\n", "Sticker presentation observer state")
    replace_unique(chat_node, "        self.nagramiXDeletedLabelObserver = NotificationCenter.default.addObserver", "        self.nagramiXMediaDisplayObserver = NotificationCenter.default.addObserver(forName: NagramiXMediaSettings.displayChangedNotification, object: nil, queue: .main, using: { _ in\n            nagramiXRefreshVisibleMessages()\n        })\n        self.nagramiXDeletedLabelObserver = NotificationCenter.default.addObserver", "Refresh visible sticker layouts when size/time changes")
    replace_unique(chat_node, "        if let nagramiXDeletedLabelObserver = self.nagramiXDeletedLabelObserver {", "        if let nagramiXMediaDisplayObserver = self.nagramiXMediaDisplayObserver {\n            NotificationCenter.default.removeObserver(nagramiXMediaDisplayObserver)\n        }\n        if let nagramiXDeletedLabelObserver = self.nagramiXDeletedLabelObserver {", "Remove sticker presentation observer")


def apply_archived_media_resources(source: Path) -> None:
    account = source / "submodules/TelegramCore/Sources/Account/Account.swift"
    state = source / "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift"
    managed = source / "submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift"
    consumed = source / "submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift"
    controller = source / "submodules/TelegramUI/Sources/ChatController.swift"
    history = source / "submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift"
    context_source = source / "submodules/TelegramUI/Sources/ChatMessageContextControllerContentSource.swift"
    replace_unique(
        account,
        "    account.pendingUpdateMessageManager.transformOutgoingMessageMedia = transformOutgoingMessageMedia\n}\n",
        "    account.pendingUpdateMessageManager.transformOutgoingMessageMedia = transformOutgoingMessageMedia\n    account.nagramiXMessageArchive.startMediaDownloads()\n}\n",
        "Start archive downloads only after the native MediaBox fetch callbacks exist",
    )
    replace_unique(
        state,
        """                if !resourceIds.isEmpty {
                    let _ = mediaBox.removeCachedResources(Array(Set(resourceIds)), force: true).start()
                }
                deletedMessageIds.append(contentsOf: ids.map { .global($0) })
""",
        """                let removableResourceIds = NagramiXMessageArchive.forPostbox(postbox)?.cacheResourcesToRemove(Array(Set(resourceIds))) ?? Array(Set(resourceIds))
                if !removableResourceIds.isEmpty {
                    let _ = mediaBox.removeCachedResources(removableResourceIds, force: true).start()
                }
                deletedMessageIds.append(contentsOf: ids.map { .global($0) })
""",
        "Keep received resources until a complete independent archive copy exists",
    )
    replace_unique(
        state,
        """                transaction.deleteMessagesInRange(peerId: id.peerId, namespace: id.namespace, minId: 1, maxId: id.id, forEachMedia: { media in
                    addMessageMediaResourceIdsToRemove(media: media, resourceIds: &resourceIds)
                })
                if !resourceIds.isEmpty {
                    let _ = mediaBox.removeCachedResources(Array(Set(resourceIds)), force: true).start()
                }
""",
        """                NagramiXMessageArchive.forPostbox(postbox)?.archiveServerDeletion(upToMessageId: id, deletedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
                transaction.deleteMessagesInRange(peerId: id.peerId, namespace: id.namespace, minId: 1, maxId: id.id, forEachMedia: { media in
                    addMessageMediaResourceIdsToRemove(media: media, resourceIds: &resourceIds)
                })
                let removableResourceIds = NagramiXMessageArchive.forPostbox(postbox)?.cacheResourcesToRemove(Array(Set(resourceIds))) ?? Array(Set(resourceIds))
                if !removableResourceIds.isEmpty {
                    let _ = mediaBox.removeCachedResources(removableResourceIds, force: true).start()
                }
""",
        "Archive received message ranges without purging pending attachment copies",
    )
    replace_unique(
        managed,
        """                    if let message = transaction.getMessage(entry.messageId) {
                        if message.id.peerId.namespace == Namespaces.Peer.SecretChat || isRemove {
""",
        """                    if let message = transaction.getMessage(entry.messageId) {
                        NagramiXMessageArchive.forPostbox(postbox)?.archiveTemporaryExpiration(message: message, expiredAt: Int32(timestamp))
                        if message.id.peerId.namespace == Namespaces.Peer.SecretChat || isRemove {
""",
        "Capture approved temporary media before the native expiry replaces or removes it",
    )
    replace_unique(
        consumed,
        """func _internal_markMessageContentAsConsumedInteractively(postbox: Postbox, messageId: MessageId) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
        if let message = transaction.getMessage(messageId), message.flags.contains(.Incoming) {
            var updateMessage = false
""",
        """func _internal_markMessageContentAsConsumedInteractively(postbox: Postbox, messageId: MessageId) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
        if let message = transaction.getMessage(messageId), message.flags.contains(.Incoming) {
            NagramiXMessageArchive.forPostbox(postbox)?.captureTemporaryBeforeViewing(message: message)
            var updateMessage = false
""",
        "Capture approved temporary attachments before their native consumption starts",
    )
    replace_unique(
        consumed,
        "func markMessageContentAsConsumedRemotely(transaction: Transaction, messageId: MessageId, consumeDate: Int32?) {\n",
        "func markMessageContentAsConsumedRemotely(transaction: Transaction, messageId: MessageId, consumeDate: Int32?, messageArchive: NagramiXMessageArchive? = nil) {\n",
        "Pass an optional archive through native remote media consumption",
    )
    replace_unique(
        consumed,
        """        if updateMessage {
            transaction.updateMessage(message.id, update: { currentMessage in
""",
        """        if updateMessage {
            if updatedMedia.contains(where: { $0 is TelegramMediaExpiredContent }) {
                messageArchive?.archiveTemporaryExpiration(message: message, expiredAt: consumeDate ?? Int32(Date().timeIntervalSince1970))
            }
            transaction.updateMessage(message.id, update: { currentMessage in
""",
        "Preserve approved view-once files before a remote consumption update",
    )
    for call in (
        "markMessageContentAsConsumedRemotely(transaction: transaction, messageId: MessageId(peerId: peerId, namespace: Namespaces.Message.Cloud, id: id), consumeDate: date)",
        "markMessageContentAsConsumedRemotely(transaction: transaction, messageId: messageId, consumeDate: date)",
    ):
        replace_unique(state, call, call[:-1] + ", messageArchive: NagramiXMessageArchive.forPostbox(postbox))", "Supply the account archive for remote read-content updates")
    replace_unique(
        controller,
        """            var standalone = false
            if case .customChatContents = self.chatLocation {
                standalone = true
            }
""",
        """            var standalone = message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
            if case .customChatContents = self.chatLocation {
                standalone = true
            }
""",
        "Open archived photos, videos, files and audio from their supplied snapshot, not a removed Postbox ID",
    )
    replace_unique(
        history,
        """    var sourceEntries = view.entries
    if let peerId = location.peerId {
        let existingIds = Set(sourceEntries.map { $0.message.id })
""",
        """    var sourceEntries = view.entries
    if let peerId = location.peerId {
        for index in sourceEntries.indices {
            let entry = sourceEntries[index]
            if entry.message.media.contains(where: { $0 is TelegramMediaExpiredContent }),
               let snapshot = context.account.nagramiXMessageArchive.snapshotForExpiredMessage(id: entry.message.id) {
                sourceEntries[index] = MessageHistoryEntry(message: snapshot, isRead: entry.isRead, location: entry.location, monthLocation: entry.monthLocation, attributes: entry.attributes)
            }
        }
        let existingIds = Set(sourceEntries.map { $0.message.id })
""",
        "Replace an expired placeholder with its approved local copy without inserting duplicate IDs",
    )
    replace_unique(
        context_source,
        "            |> map { _ in archive.deletedMessage(id: messageId) == nil }\n",
        "            |> map { _ in !archive.containsArchivedMessage(id: messageId) }\n",
        "Keep expired-media context extraction alive until the archive is cleared",
    )


def apply_archived_media_playback(source: Path) -> None:
    """Keep supplied archive snapshots on one native playlist and route voice taps."""
    manager = source / "submodules/AccountContext/Sources/MediaManager.swift"
    file_node = source / "submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift"
    bubble = source / "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"
    replace_unique(
        manager,
        """public func peerMessagesMediaPlaylistAndItemId(_ message: EngineMessage, isRecentActions: Bool, isGlobalSearch: Bool, isDownloadList: Bool, isSavedMusic: Bool, isAttachMusic: Bool) -> (SharedMediaPlaylistId, SharedMediaPlaylistItemId)? {
    if isSavedMusic {
""",
        """public func peerMessagesMediaPlaylistAndItemId(_ message: EngineMessage, isRecentActions: Bool, isGlobalSearch: Bool, isDownloadList: Bool, isSavedMusic: Bool, isAttachMusic: Bool) -> (SharedMediaPlaylistId, SharedMediaPlaylistItemId)? {
    // OpenChatMessage plays an archived snapshot via .recentActions(message).
    // Its controls, waveform and embedded video must observe that same playlist.
    if message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
        return (PeerMessagesMediaPlaylistId.recentActions(message.id.peerId), PeerMessagesMediaPlaylistItemId(messageId: message.id, messageIndex: message.index))
    }
    if isSavedMusic {
""",
        "Bind archived playback status and audio levels to the native snapshot playlist",
    )
    replace_unique(
        file_node,
        "public final class ChatMessageInteractiveFileNode: ASDisplayNode {\n",
        "public final class ChatMessageInteractiveFileNode: ASDisplayNode, ASGestureRecognizerDelegate {\n",
        "Use the native wrapped gesture delegate for archived voice controls",
    )
    replace_unique(
        file_node,
        """        let tapRecognizer = UITapGestureRecognizer(target: self, action: #selector(self.fileTap(_:)))
        self.view.addGestureRecognizer(tapRecognizer)
""",
        """        let tapRecognizer = UITapGestureRecognizer(target: self, action: #selector(self.fileTap(_:)))
        tapRecognizer.delegate = self.wrappedGestureRecognizerDelegate
        self.view.addGestureRecognizer(tapRecognizer)
""",
        "Reject archived voice body taps before the file recognizer consumes them",
    )
    replace_unique(
        file_node,
        """        self.tapRecognizer = tapRecognizer
    }
""" + "    \n" + """    @objc private func cacheProgressPressed() {
""",
        """        self.tapRecognizer = tapRecognizer
    }

    private var nagramiXIsArchivedVoice: Bool {
        return self.file?.isVoice == true && self.message?.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) == true
    }

    public func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        if gestureRecognizer === self.tapRecognizer && self.nagramiXIsArchivedVoice {
            return self.statusContainerNode.frame.contains(touch.location(in: self.view))
        }
        return true
    }

    @objc private func cacheProgressPressed() {
""",
        "Limit only archived voice activation to the native Play Pause download control",
    )
    replace_unique(
        file_node,
        """    public func hasTapAction(at point: CGPoint) -> Bool {
        if let _ = self.dateAndStatusNode.hitTest(self.view.convert(point, to: self.dateAndStatusNode.view), with: nil) {
""",
        """    public func hasTapAction(at point: CGPoint) -> Bool {
        if self.nagramiXIsArchivedVoice {
            if self.statusContainerNode.frame.contains(point) || self.audioTranscriptionButton?.frame.contains(point) == true {
                return true
            }
        }
        if let _ = self.dateAndStatusNode.hitTest(self.view.convert(point, to: self.dateAndStatusNode.view), with: nil) {
""",
        "Leave archived Play Pause and transcription taps to their native controls",
    )
    replace_unique(
        bubble,
        """    private var nagramiXDeletedStatusNode: ImmediateTextNode?
    private var nagramiXDeletedStatusIconNode: ASImageNode?
""",
        """    private var nagramiXDeletedStatusNode: ImmediateTextNode?

    private var nagramiXArchivedVoiceBodyMenuEnabled: Bool {
        guard self.selectionNode == nil, let item = self.item, item.controllerInteraction.tapMessage == nil else {
            return false
        }
        return item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
            && item.message.media.contains(where: { ($0 as? TelegramMediaFile)?.isVoice == true })
    }
    private var nagramiXDeletedStatusIconNode: ASImageNode?
""",
        "Identify archived voice body taps without intercepting message selection",
    )
    replace_unique(
        bubble,
        """                    }
                }
""" + "                \n" + """                if !strongSelf.backgroundNode.frame.contains(point) {
                    return .waitForDoubleTap
                }
""",
        """                    }
                }

                if strongSelf.nagramiXArchivedVoiceBodyMenuEnabled && strongSelf.backgroundNode.frame.contains(point) {
                    return .waitForSingleTap
                }
                if !strongSelf.backgroundNode.frame.contains(point) {
                    return .waitForDoubleTap
                }
""",
        "Resolve an archived voice body tap immediately after native control hit tests",
    )
    replace_unique(
        bubble,
        """                    }
                }
                if self.currentMessageEffect() != nil {
                    if self.backgroundNode.frame.contains(location) {
""",
        """                    }
                }
                if self.nagramiXArchivedVoiceBodyMenuEnabled && self.backgroundNode.frame.contains(location) {
                    return .action(InternalBubbleTapAction.Action({ [weak self] in
                        guard let self, let item = self.item else {
                            return
                        }
                        item.controllerInteraction.openMessageContextMenu(item.message, false, self, self.backgroundNode.frame, nil, location)
                    }, contextMenuOnLongPress: true))
                }
                if self.currentMessageEffect() != nil {
                    if self.backgroundNode.frame.contains(location) {
""",
        "Open the native archive menu on a voice body tap instead of starting playback",
    )


def apply_copy_send_options(source: Path) -> None:
    """Use the existing recipient panel and send menu instead of an implicit send."""
    protocol = source / "submodules/AccountContext/Sources/PeerSelectionController.swift"
    picker = source / "submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionController.swift"
    picker_node = source / "submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift"
    forwarding = source / "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift"
    replace_unique(
        protocol,
        """    var customDismiss: (() -> Void)? { get set }
}
""",
        """    var customDismiss: (() -> Void)? { get set }
    func nagramiXSelectCopyRecipient(_ peer: EnginePeer)
}
""",
        "Expose a narrow recipient-selection bridge for copy sending",
    )
    replace_unique(
        picker,
        """    }
""" + "    \n" + """    @objc private func beginSelection() {
""",
        """    }

    public func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {
        self.deactivateSearch()
        self.beginSelection()
        self.peerSelectionNode.nagramiXSelectCopyRecipient(peer)

        // A forum/community picker may still be above this recipient controller.
        // Return to its native send panel after choosing the destination topic.
        if let navigationController = self.navigationController as? NavigationController,
           let index = navigationController.viewControllers.firstIndex(where: { $0 === self }),
           index + 1 < navigationController.viewControllers.count {
            let viewControllers = Array(navigationController.viewControllers.prefix(index + 1))
            self.peerSelectionNode.pushedController = nil
            navigationController.setViewControllers(viewControllers, animated: true)
        }
    }

    @objc private func beginSelection() {
""",
        "Activate the native text send panel and return from destination-topic selection",
    )
    replace_unique(
        picker_node,
        """            self.containerLayoutUpdated(layout, navigationBarHeight: navigationBarHeight, actualNavigationBarHeight: actualNavigationBarHeight, transition: transition)
        }
    }

    private var selectedPeers: ([EnginePeer], [EnginePeer.Id: EnginePeer]) {
""",
        """            self.containerLayoutUpdated(layout, navigationBarHeight: navigationBarHeight, actualNavigationBarHeight: actualNavigationBarHeight, transition: transition)
        }
    }

    func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {
        if self.contactListActive {
            self.contactListNode?.updateSelectionState { state in
                let state = state ?? ContactListNodeGroupSelectionState()
                var foundPeers = state.foundPeers
                if !foundPeers.contains(where: { $0.id == .peer(peer.id) }) {
                    foundPeers.insert(.peer(peer: peer, isGlobal: false, participantCount: nil), at: 0)
                }
                var selectedPeerMap = state.selectedPeerMap
                selectedPeerMap[.peer(peer.id)] = .peer(peer: peer, isGlobal: false, participantCount: nil)
                let selectedState = state.selectedPeerIndices[.peer(peer.id)] == nil ? state.withToggledPeerId(.peer(peer.id)) : state
                return selectedState.withFoundPeers(foundPeers).withSelectedPeerMap(selectedPeerMap)
            }
        } else {
            let chatListNode = self.mainContainerNode?.currentItemNode ?? self.chatListNode
            chatListNode?.updateState { state in
                var state = state
                state.selectedPeerIds.insert(peer.id)
                state.selectedPeerMap[peer.id] = peer
                if !state.foundPeers.contains(where: { $0.0.id == peer.id }) {
                    state.foundPeers.insert((peer, nil), at: 0)
                }
                return state
            }
        }
        // Copy mode deliberately has no forward IDs or source-author header.
        if self.forwardedMessageIds.isEmpty, let panel = self.forwardAccessoryPanelNode {
            panel.removeFromSupernode()
            self.forwardAccessoryPanelNode = nil
            if let (layout, navigationBarHeight, actualNavigationBarHeight) = self.containerLayout {
                self.containerLayoutUpdated(layout, navigationBarHeight: navigationBarHeight, actualNavigationBarHeight: actualNavigationBarHeight, transition: .immediate)
            }
        }
        self.textInputPanelNode?.updateSendButtonEnabled(!self.selectedPeers.0.isEmpty, animated: true)
    }

    private var selectedPeers: ([EnginePeer], [EnginePeer.Id: EnginePeer]) {
""",
        "Preselect the tapped recipient using native chat and contact selection state",
    )
    replace_unique(
        forwarding,
        "                    strongController.multiplePeersSelected?([peer], [peer.id: peer], NSAttributedString(string: \"\"), .generic, nil, nil)\n",
        "                    strongController.nagramiXSelectCopyRecipient(peer)\n",
        "Wait for the user's native send mode instead of forcing immediate copy delivery",
    )
    replace_unique(
        forwarding,
        "threadId: strongSelf.chatLocation.threadId, replyToMessageId: nil",
        "threadId: transferMode == .copyAsNew ? nil : strongSelf.chatLocation.threadId, replyToMessageId: nil",
        "Keep a copy comment out of the source conversation's topic",
    )
    replace_unique(
        forwarding,
        """                        switch mode {
                        case .generic:
                            commit(result)
                        case .silent:
                            let transformedMessages = strongSelf.transformEnqueueMessages(result, silentPosting: true)
                            commit(transformedMessages)
                        case .schedule:
                            strongSelf.presentScheduleTimePicker(completion: { [weak self] timeResult in
                                if let strongSelf = self {
                                    let transformedMessages = strongSelf.transformEnqueueMessages(result, silentPosting: timeResult.silentPosting, scheduleTime: timeResult.time, repeatPeriod: timeResult.repeatPeriod)
                                    commit(transformedMessages)
                                }
                            })
                        case .whenOnline:
                            let transformedMessages = strongSelf.transformEnqueueMessages(result, silentPosting: strongSelf.presentationInterfaceState.interfaceState.silentPosting, scheduleTime: scheduleWhenOnlineTimestamp)
                            commit(transformedMessages)
                        }
""",
        """                        let transformForSend: (Bool, Int32?, Int32?) -> [EnqueueMessage] = { [weak self] silentPosting, scheduleTime, repeatPeriod in
                            guard let strongSelf = self else {
                                return []
                            }
                            let transformedMessages = strongSelf.transformEnqueueMessages(result, silentPosting: silentPosting, scheduleTime: scheduleTime, repeatPeriod: repeatPeriod)
                            guard transferMode == .copyAsNew else {
                                return transformedMessages
                            }
                            // The stock transform also applies the SOURCE chat's reply,
                            // topic, send-as, suggested post and paid-message defaults.
                            // Copies keep their content and only take the selected send mode;
                            // destination topic/payment handling remains in commit below.
                            return zip(result, transformedMessages).map { original, transformed in
                                let sendAttributes = transformed.attributes.filter { $0 is NotificationInfoMessageAttribute || $0 is OutgoingScheduleInfoMessageAttribute }
                                return original.withUpdatedAttributes { attributes in
                                    return attributes.filter { !($0 is NotificationInfoMessageAttribute) && !($0 is OutgoingScheduleInfoMessageAttribute) } + sendAttributes
                                }
                            }
                        }
                        switch mode {
                        case .generic:
                            commit(result)
                        case .silent:
                            commit(transformForSend(true, nil, nil))
                        case .schedule:
                            strongSelf.presentScheduleTimePicker(completion: { [weak self] timeResult in
                                if self != nil {
                                    commit(transformForSend(timeResult.silentPosting, timeResult.time, timeResult.repeatPeriod))
                                }
                            })
                        case .whenOnline:
                            commit(transformForSend(strongSelf.presentationInterfaceState.interfaceState.silentPosting, scheduleWhenOnlineTimestamp, nil))
                        }
""",
        "Use native silent schedule attributes without leaking source-chat defaults into copies",
    )


def apply_chat_hold_routing(source: Path) -> None:
    """Route the native context gesture by its initial area, not by a new recognizer."""
    row = source / "submodules/ChatListUI/Sources/Node/ChatListItem.swift"
    controller = source / "submodules/ChatListUI/Sources/ChatListController.swift"
    replace_unique(
        row,
        "    private var nagramiXLastActionsOnHold = true\n",
        "    private var nagramiXLastActionsOnHold = true\n    private var nagramiXHoldBeganOnAvatar = false\n",
        "Remember the initial hold area before native activation scaling",
    )
    replace_unique(
        row,
        """            self.nagramiXLastActionsOnHold = actionsOnHold
            self.nagramiXApplyRevealSettings()
""",
        """            self.nagramiXLastActionsOnHold = actionsOnHold
            self.contextContainer.cancelGesture()
            self.nagramiXApplyRevealSettings()
""",
        "Cancel an in-progress hold when its routing preference changes",
    )
    replace_unique(
        row,
        """            strongSelf.contextContainer.additionalActivationProgressLayer = nil
            if let inlineNavigationLocation = item.interaction.inlineNavigationLocation {
""",
        """            // Use the current native avatar bounds, including compact layout,
            // and capture the area before the context activation animation.
            let avatarLocation = strongSelf.avatarNode.view.convert(location, from: strongSelf.contextContainer.view)
            strongSelf.nagramiXHoldBeganOnAvatar = !strongSelf.avatarContainerNode.isHidden && strongSelf.avatarNode.bounds.contains(avatarLocation)

            strongSelf.contextContainer.additionalActivationProgressLayer = nil
            if let inlineNavigationLocation = item.interaction.inlineNavigationLocation {
""",
        "Resolve the avatar in the native context gesture's coordinate space",
    )
    replace_unique(
        row,
        """            item.interaction.activateChatPreview?(item, threadId, strongSelf.contextContainer, gesture, nil)
""",
        """            if NagramiXTabSettings.current.chatActionsOnHold && !strongSelf.nagramiXHoldBeganOnAvatar {
                let menuLocation = strongSelf.contextContainer.view.convert(location, to: nil)
                item.interaction.activateChatPreview?(item, threadId, strongSelf.contextContainer, gesture, menuLocation)
                return
            }
            item.interaction.activateChatPreview?(item, threadId, strongSelf.contextContainer, gesture, nil)
""",
        "Preserve native avatar preview; request a menu-only source for other areas",
    )
    replace_unique(
        controller,
        """            switch item.content {
            case .loading:
                break
            case let .groupReference(groupReference):
                let chatListController = ChatListControllerImpl(context: strongSelf.context, location: .chatList(groupId: groupReference.groupId), controlsHistoryPreload: false, hideNetworkActivityStatus: true, previewing: true, enableDebugActions: false)
""",
        """            if NagramiXTabSettings.current.chatActionsOnHold, gesture != nil, let menuLocation = location {
                let menuItems: Signal<[ContextMenuItem], NoError>
                switch item.content {
                case .loading:
                    gesture?.cancel()
                    return
                case let .groupReference(groupReference):
                    menuItems = archiveContextMenuItems(context: strongSelf.context, group: groupReference.groupId, chatListController: strongSelf)
                case let .peer(peerData):
                    let peer = peerData.peer
                    switch item.index {
                    case .chatList:
                        if let threadId = threadId, case let .channel(channel) = peer.peer, channel.isForum || channel.isMonoForum {
                            menuItems = chatForumTopicMenuItems(context: strongSelf.context, peerId: peer.peerId, threadId: threadId, isPinned: nil, isClosed: nil, chatListController: strongSelf, joined: joined, canSelect: false)
                        } else {
                            menuItems = chatContextMenuItems(context: strongSelf.context, peerId: peer.peerId, promoInfo: peerData.promoInfo, source: .chatList(filter: strongSelf.chatListDisplayNode.mainContainerNode.currentItemNode.chatListFilter), chatListController: strongSelf, joined: joined)
                        }
                    case let .forum(pinnedIndex, _, threadId, _, _):
                        let isPinned: Bool
                        switch pinnedIndex {
                        case .index:
                            isPinned = true
                        case .none:
                            isPinned = false
                        }
                        menuItems = chatForumTopicMenuItems(context: strongSelf.context, peerId: peer.peerId, threadId: threadId, isPinned: isPinned, isClosed: peerData.threadInfo?.isClosed, chatListController: strongSelf, joined: joined, canSelect: true)
                    }
                }
                // Use Telegram's menu-only source and existing action generators.
                // No preview controller is created and no read action is performed.
                let contextController = makeContextController(context: strongSelf.context, presentationData: strongSelf.presentationData, source: .location(ChatListContextLocationContentSource(controller: strongSelf, location: menuLocation)), items: menuItems |> map { ContextController.Items(content: .list($0)) }, gesture: gesture)
                strongSelf.presentInGlobalOverlay(contextController)
                return
            }

            switch item.content {
            case .loading:
                break
            case let .groupReference(groupReference):
                let chatListController = ChatListControllerImpl(context: strongSelf.context, location: .chatList(groupId: groupReference.groupId), controlsHistoryPreload: false, hideNetworkActivityStatus: true, previewing: true, enableDebugActions: false)
""",
        "Present native chat/archive/topic actions without opening a preview off the avatar",
    )
    apply_chat_avatar_read_mode(source)


def apply_chat_avatar_read_mode(source: Path) -> None:
    """Full native chat on avatar tap; keep the read gate closed for its lifetime."""
    container = source / "submodules/ChatListUI/Sources/ChatListControllerNode.swift"
    node = source / "submodules/ChatListUI/Sources/Node/ChatListNode.swift"
    row = source / "submodules/ChatListUI/Sources/Node/ChatListItem.swift"
    controller = source / "submodules/ChatListUI/Sources/ChatListController.swift"
    account = source / "submodules/AccountContext/Sources/AccountContext.swift"
    chat = source / "submodules/TelegramUI/Sources/ChatController.swift"
    navigation = source / "submodules/TelegramUI/Sources/NavigateToChatController.swift"

    replace_unique(container, "import GlassControls\n", "import GlassControls\nimport NagramiXCore\n", "Use the existing chat gesture preference for folder directions")
    replace_unique(container, """            if self.availableFilters.count > 1 {
                return [.leftCenter, .rightCenter]
""", """            if self.availableFilters.count > 1 {
                if NagramiXTabSettings.current.chatActionsOnHold {
                    // Telegram's aggregate directions include both edges and center.
                    return [.left, .right]
                }
                return [.leftCenter, .rightCenter]
""", "Allow native folder paging from both edges as well as the center when enabled")

    # Separate callback: nil gesture/location must retain their native preview meaning.
    replace_unique(node, "    let activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n", "    let activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n    var nagramiXOpenChatWithoutReadReceipts: ((ChatListItem) -> Void)?\n", "Add an explicit avatar-open intent to the row interaction")
    replace_unique(node, "    public var activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n", "    public var activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n    public var nagramiXOpenChatWithoutReadReceipts: ((ChatListItem) -> Void)?\n", "Expose avatar-open intent on the native list node")
    replace_unique(node, "        nodeInteraction.isInlineMode = isInlineMode\n", """        nodeInteraction.isInlineMode = isInlineMode
        if !previewing, !isInlineMode, case .chatList = mode {
            nodeInteraction.nagramiXOpenChatWithoutReadReceipts = { [weak self] item in
                self?.nagramiXOpenChatWithoutReadReceipts?(item)
            }
        }
""", "Keep avatar-open routing out of pickers, inline lists and preview controllers")
    replace_unique(container, "    var activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n", "    var activateChatPreview: ((ChatListItem, Int64?, ASDisplayNode, ContextGesture?, CGPoint?) -> Void)?\n    var nagramiXOpenChatWithoutReadReceipts: ((ChatListItem) -> Void)?\n", "Expose avatar-open intent on the folder container")
    replace_unique(container, "            previousItemNode.listNode.activateChatPreview = nil\n", "            previousItemNode.listNode.activateChatPreview = nil\n            previousItemNode.listNode.nagramiXOpenChatWithoutReadReceipts = nil\n", "Detach avatar-open routing from inactive cached folders")
    replace_unique(container, """        itemNode.listNode.activateChatPreview = { [weak self] item, threadId, sourceNode, gesture, location in
            self?.activateChatPreview?(item, threadId, sourceNode, gesture, location)
        }
""", """        itemNode.listNode.activateChatPreview = { [weak self] item, threadId, sourceNode, gesture, location in
            self?.activateChatPreview?(item, threadId, sourceNode, gesture, location)
        }
        itemNode.listNode.nagramiXOpenChatWithoutReadReceipts = { [weak self] item in
            self?.nagramiXOpenChatWithoutReadReceipts?(item)
        }
""", "Forward avatar taps from the current and rebound folder nodes")

    replace_unique(row, "    func setupItem(item: ChatListItem, synchronousLoads: Bool) {\n", """    private var nagramiXCanOpenAvatarWithoutReadReceipts: Bool {
        guard let item = self.item, !item.editing, !item.hasActiveRevealControls,
              !item.useCommunityViewLayout, item.interaction.inlineNavigationLocation == nil,
              !item.interaction.isInlineMode, item.interaction.nagramiXOpenChatWithoutReadReceipts != nil,
              case let .peer(peerData) = item.content, !peerData.displayAsMessage,
              let peer = peerData.peer.peer else {
            return false
        }
        if case .community = peer {
            return false
        }
        // setupItem precedes the avatar visibility/layout update on reused rows.
        // UIKit's hit test still excludes a hidden avatar at touch time.
        return true
    }

    func setupItem(item: ChatListItem, synchronousLoads: Bool) {
""", "Limit silent avatar opening to real non-editing chat rows")
    replace_unique(row, "        self.avatarNode.isUserInteractionEnabled = !item.useCommunityViewLayout && ((storyState != nil && !peerIsCommunity) || peerLinkedCommunityId != nil)\n", "        self.avatarNode.isUserInteractionEnabled = self.nagramiXCanOpenAvatarWithoutReadReceipts || (!item.useCommunityViewLayout && ((storyState != nil && !peerIsCommunity) || peerLinkedCommunityId != nil))\n", "Enable native avatar tap recognition even when the peer has no stories")
    replace_unique(row, "            var shouldHitTestAvatar = !isCommunity && self.avatarNode.storyStats != nil\n", "            var shouldHitTestAvatar = self.nagramiXCanOpenAvatarWithoutReadReceipts || (!isCommunity && self.avatarNode.storyStats != nil)\n", "Hit-test the actual avatar bounds without covering the rest of the row")
    replace_unique(row, """    @objc private func avatarStoryTapGesture(_ recognizer: UITapGestureRecognizer) {
        if case .ended = recognizer.state {
            guard let item = self.item else {
                return
            }
""", """    @objc private func avatarStoryTapGesture(_ recognizer: UITapGestureRecognizer) {
        if case .ended = recognizer.state {
            guard let item = self.item else {
                return
            }
            if self.nagramiXCanOpenAvatarWithoutReadReceipts {
                item.interaction.nagramiXOpenChatWithoutReadReceipts?(item)
                return
            }
""", "Open a full silent chat on ordinary avatar tap regardless of the checkbox")

    replace_unique(account, "    public let hideTopPanels: Bool\n", "    public let hideTopPanels: Bool\n    public let nagramiXReadHistoryDisabled: Bool\n", "Carry the per-controller read policy in the actual Telegram chat parameters")
    replace_unique(account, "        hideTopPanels: Bool = false\n", "        hideTopPanels: Bool = false,\n        nagramiXReadHistoryDisabled: Bool = false\n", "Keep all existing chat construction paths readable by default")
    replace_unique(account, "        self.hideTopPanels = hideTopPanels\n", "        self.hideTopPanels = hideTopPanels\n        self.nagramiXReadHistoryDisabled = nagramiXReadHistoryDisabled\n", "Initialize the immutable avatar read policy")
    replace_unique(chat, "    public let canReadHistory = ValuePromise<Bool>(true, ignoreRepeated: true)\n", "    public let canReadHistory = ValuePromise<Bool>(true, ignoreRepeated: true)\n    let nagramiXReadHistoryDisabled: Bool\n", "Store the permanent read policy on this chat instance only")
    replace_unique(chat, "        self.hideTopPanels = params?.hideTopPanels ?? false\n", "        self.hideTopPanels = params?.hideTopPanels ?? false\n        self.nagramiXReadHistoryDisabled = params?.nagramiXReadHistoryDisabled ?? false\n", "Install the read policy before the native history node is created")
    replace_unique(chat, """            if let strongSelf = self, strongSelf.canReadHistoryValue != value {
                strongSelf.canReadHistoryValue = value
                strongSelf.raiseToListen?.enabled = value
            }
""", """            if let strongSelf = self {
                // Native overlays may set canReadHistory back to true. This
                // instance's policy also gates queued foreground emissions.
                let effectiveValue = value && !strongSelf.nagramiXReadHistoryDisabled
                if strongSelf.canReadHistoryValue != effectiveValue {
                    strongSelf.canReadHistoryValue = effectiveValue
                    strongSelf.raiseToListen?.enabled = effectiveValue
                }
            }
""", "Keep every history binding false across foreground and overlay transitions")
    replace_unique(navigation, "        if case let .peer(peer) = params.chatLocation, case let .channel(channel) = peer, channel.flags.contains(.isForum), !viewForumAsMessages {\n", "        if (params.chatController as? ChatControllerImpl)?.nagramiXReadHistoryDisabled != true, case let .peer(peer) = params.chatLocation, case let .channel(channel) = peer, channel.flags.contains(.isForum), !viewForumAsMessages {\n", "Keep explicit silent forum opening full-screen instead of redirecting to a topic list")
    replace_unique(navigation, "                guard let controller = controller as? ChatControllerImpl else {\n", "                guard let controller = controller as? ChatControllerImpl, !controller.nagramiXReadHistoryDisabled else {\n", "Never reuse a silent avatar controller for an ordinary readable chat open")

    replace_unique(controller, "        self.chatListDisplayNode.mainContainerNode.activateChatPreview = { [weak self] item, threadId, node, gesture, location in\n", """        self.chatListDisplayNode.mainContainerNode.nagramiXOpenChatWithoutReadReceipts = { [weak self] item in
            guard let self, case let .peer(peerData) = item.content,
                  !item.editing, let peer = peerData.peer.peer else {
                return
            }
            var sourcePeer: Signal<EnginePeer?, NoError> = .single(peer)
            var threadId: Int64?
            if case let .forum(_, _, id, _, _) = item.index {
                threadId = id
            }
            if case let .savedMessagesChats(peerId) = item.chatListLocation, peerId != self.context.account.peerId {
                threadId = peer.id.toInt64()
                sourcePeer = self.context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: peerId))
            }
            let _ = (sourcePeer |> take(1) |> deliverOnMainQueue).startStandalone(next: { [weak self] peer in
                guard let self, let peer, let navigationController = self.navigationController as? NavigationController else {
                    return
                }
                let location: NavigateToChatControllerParams.Location
                if let threadId {
                    let isMonoforum: Bool
                    if case let .channel(channel) = peer {
                        isMonoforum = channel.isMonoForum
                    } else {
                        isMonoforum = false
                    }
                    location = .replyThread(ChatReplyThreadMessage(peerId: peer.id, threadId: threadId, channelMessageId: nil, isChannelPost: false, isForumPost: true, isMonoforumPost: isMonoforum, maxMessage: nil, maxReadIncomingMessageId: nil, maxReadOutgoingMessageId: nil, unreadCount: 0, initialFilledHoles: IndexSet(), initialAnchor: .automatic, isNotAvailable: false))
                } else {
                    location = .peer(peer)
                }
                let chatController = self.context.sharedContext.makeChatController(context: self.context, chatLocation: location.asChatLocation, subject: nil, botStart: nil, mode: .standard(.default), params: ChatControllerParams(nagramiXReadHistoryDisabled: true))
                chatController.canReadHistory.set(false)
                self.chatListDisplayNode.mainContainerNode.currentItemNode.clearHighlightAnimated(true)
                var parentGroupId: EnginePeerGroupId?
                if case let .chatList(groupId) = item.chatListLocation {
                    parentGroupId = groupId
                }
                self.context.sharedContext.navigateToChatController(NavigateToChatControllerParams(navigationController: navigationController, chatController: chatController, context: self.context, chatLocation: location, keepStack: .always, useExisting: false, parentGroupId: parentGroupId, chatListFilter: self.chatListDisplayNode.mainContainerNode.currentItemNode.chatListFilter?.id, forceOpenChat: true))
            })
        }

        self.chatListDisplayNode.mainContainerNode.activateChatPreview = { [weak self] item, threadId, node, gesture, location in
""", "Navigate through native age and navigation checks with a dedicated silent full chat")


def apply_video_playback_options(source: Path) -> None:
    gallery = source / "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"
    replace_unique(source / "submodules/GalleryUI/Sources/GalleryControllerNode.swift",
        """            if distanceFromEquilibrium < -1.0, let centralItemNode = self.pager.centralItemNode(), centralItemNode.maybePerformActionForSwipeDownDismiss() {
            }
""",
        """            if distanceFromEquilibrium < -1.0, let centralItemNode = self.pager.centralItemNode(), centralItemNode.maybePerformActionForSwipeDownDismiss() {
                return
            }
""", "Let a handled downward PiP gesture use native custom dismissal instead of closing its gallery twice")
    replace_unique(source / "submodules/GalleryUI/BUILD",
        '        "//submodules/AccountContext:AccountContext",\n',
        '        "//submodules/AccountContext:AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "Bind gallery video options to existing NagramiX preferences")
    replace_unique(gallery, "import AVKit\n", "import AVKit\nimport NagramiXCore\n", "Read swipe PiP and background audio preferences in the native video gallery")
    replace_unique(gallery, "    func beginPictureInPicture() {", """    var nagramiXCanStartPictureInPicture: Bool {
        return self.pictureInPictureController?.isPictureInPicturePossible == true
    }

    func beginPictureInPicture() {""", "Check native PiP availability before consuming a dismissal gesture")
    replace_unique(gallery, "    private var playerStatusValue: MediaPlayerStatus?", "    private let nagramiXBackgroundVideoId = UUID()\n    private var playerStatusValue: MediaPlayerStatus?", "Give each video gallery a distinct audio-session owner")
    replace_unique(gallery, "                    strongSelf.playerStatusValue = value", """                    strongSelf.playerStatusValue = value
                    strongSelf.nagramiXUpdateBackgroundVideoPlayback()
                    if NagramiXTabSettings.videoPiPSwipeEnabled && strongSelf.item?.isSecret == false && strongSelf.hasPictureInPicture && strongSelf.nativePictureInPictureContent == nil {
                        strongSelf.setupNativePictureInPicture()
                    }""", "Track native playing and buffering state and prepare eligible swipe PiP")
    replace_unique(gallery, "            self.isCentral = isCentral\n", "            self.isCentral = isCentral\n            self.nagramiXUpdateBackgroundVideoPlayback()\n", "Release background audio ownership when paging to another gallery item")
    replace_unique(gallery,
        """            videoNode.ownsContentNodeUpdated = { [weak self] value in
                if let strongSelf = self {
                    strongSelf.updateDisplayPlaceholder(!value)""",
        """            videoNode.ownsContentNodeUpdated = { [weak self] value in
                if let strongSelf = self {
                    strongSelf.nagramiXUpdateBackgroundVideoPlayback()
                    strongSelf.updateDisplayPlaceholder(!value)""",
        "Refresh background audio ownership when the existing video content is transferred")
    replace_unique(gallery, "    deinit {\n        self.statusDisposable.dispose()", """    deinit {
        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: false)
        self.statusDisposable.dispose()""", "Remove background video ownership when its gallery is destroyed")
    old_swipe = """    override func maybePerformActionForSwipeDismiss() -> Bool {
        if let data = self.context.currentAppConfiguration.with({ $0 }).data {
            if let _ = data["ios_killswitch_disable_swipe_pip"] {
                return false
            }
            var swipeUpToClose = false
            if let value = data["video_swipe_up_to_close"] as? Double, value == 1.0 {
                swipeUpToClose = true
            } else if let value = data["video_swipe_up_to_close"] as? Bool, value {
                swipeUpToClose = true
            }
           \x20
            if swipeUpToClose {
                self.context.engine.accountData.addAppLogEvent(type: "swipe_up_close")
               \x20
                return false
            }
        }
       \x20
        if #available(iOS 15.0, *) {
            if let nativePictureInPictureContent = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
                self.context.engine.accountData.addAppLogEvent(type: "swipe_up_pip")
                nativePictureInPictureContent.beginPictureInPicture()
                return true
            }
        }
        return false
    }
   \x20
    override func maybePerformActionForSwipeDownDismiss() -> Bool {
        self.context.engine.accountData.addAppLogEvent(type: "swipe_down_close")
        return false
    }
"""
    replace_unique(gallery, old_swipe, """    override func maybePerformActionForSwipeDismiss() -> Bool {
        return self.nagramiXStartSwipePictureInPicture(logEvent: "swipe_up_pip")
    }

    override func maybePerformActionForSwipeDownDismiss() -> Bool {
        if self.nagramiXStartSwipePictureInPicture(logEvent: "swipe_down_pip") {
            return true
        }
        self.context.engine.accountData.addAppLogEvent(type: "swipe_down_close")
        return false
    }

    private func nagramiXStartSwipePictureInPicture(logEvent: String) -> Bool {
        guard NagramiXTabSettings.videoPiPSwipeEnabled, self.hasPictureInPicture, let item = self.item, !item.isSecret else {
            return false
        }
        if let data = self.context.currentAppConfiguration.with({ $0 }).data, data["ios_killswitch_disable_swipe_pip"] != nil {
            return false
        }
        if self.nativePictureInPictureContent == nil {
            self.setupNativePictureInPicture()
        }
        if #available(iOS 15.0, *), let content = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl, content.nagramiXCanStartPictureInPicture {
            self.context.engine.accountData.addAppLogEvent(type: logEvent)
            content.beginPictureInPicture()
            return true
        }
        // A missing player/layer or unsupported PiP leaves native dismissal intact.
        return false
    }

    private func nagramiXUpdateBackgroundVideoPlayback() {
        var active = false
        if let item = self.item, !item.isSecret, !self.isLivePhoto, let status = self.playerStatusValue, status.soundEnabled,
            self.videoNode?.ownsContentNode == true,
            self.isCentral == true || self.context.sharedContext.mediaManager.currentPictureInPictureNode === self {
            var supportedContent = false
            if let content = item.content as? NativeVideoContent {
                supportedContent = !content.fileReference.media.isAnimated
            } else if let content = item.content as? HLSVideoContent {
                supportedContent = !content.fileReference.media.isAnimated
            }
            if supportedContent {
                switch status.status {
                case .playing:
                    active = true
                case let .buffering(_, whilePlaying, _, _):
                    active = whilePlaying
                default:
                    break
                }
            }
        }
        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: active)
    }
""", "Use native PiP for both vertical swipes and register only audible ordinary video playback")

    protocol = source / "submodules/AccountContext/Sources/MediaManager.swift"
    replace_unique(protocol, "    var currentPictureInPictureNode: AnyObject? { get set }", """    var currentPictureInPictureNode: AnyObject? { get set }

    // Gallery-owned audio only; this does not create or replace a media player.
    func setNagramiXBackgroundVideoPlayback(id: UUID, active: Bool)""", "Bridge current gallery playback to the existing media-manager audio-session policy")

    manager = source / "submodules/TelegramUI/Sources/MediaManager.swift"
    replace_unique(manager, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Read background video preference in the native audio-session owner")
    replace_unique(manager, "    private let inForeground: Signal<Bool, NoError>", """    private var nagramiXBackgroundVideoOwners = Set<UUID>()
    private let nagramiXBackgroundVideoPlaying = ValuePromise<Bool>(false, ignoreRepeated: true)
    private var nagramiXVideoSettingsObserver: NSObjectProtocol?
    private let inForeground: Signal<Bool, NoError>""", "Track live gallery audio without retaining gallery nodes")
    replace_unique(manager,
        "        let shouldKeepAudioSession: Signal<Bool, NoError> = combineLatest(queue: Queue.mainQueue(), self.globalMediaPlayerState, inForeground)\n        |> map { stateAndType, inForeground -> Bool in",
        """        self.nagramiXVideoSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.nagramiXUpdateBackgroundVideoState()
        })
        let shouldKeepAudioSession: Signal<Bool, NoError> = combineLatest(queue: Queue.mainQueue(), self.globalMediaPlayerState, inForeground, self.nagramiXBackgroundVideoPlaying.get())
        |> map { stateAndType, inForeground, backgroundVideoPlaying -> Bool in
            if backgroundVideoPlaying {
                return false
            }""", "Keep the native audio session for audible background-enabled video and react to live settings changes")
    replace_unique(manager, "    deinit {\n", """    public func setNagramiXBackgroundVideoPlayback(id: UUID, active: Bool) {
        let update: () -> Void = { [weak self] in
            guard let self else { return }
            if active {
                self.nagramiXBackgroundVideoOwners.insert(id)
            } else {
                self.nagramiXBackgroundVideoOwners.remove(id)
            }
            self.nagramiXUpdateBackgroundVideoState()
        }
        if Thread.isMainThread {
            update()
        } else {
            Queue.mainQueue().async(update)
        }
    }

    private func nagramiXUpdateBackgroundVideoState() {
        self.nagramiXBackgroundVideoPlaying.set(NagramiXTabSettings.backgroundVideoPlaybackEnabled && !self.nagramiXBackgroundVideoOwners.isEmpty)
    }

    deinit {
        if let observer = self.nagramiXVideoSettingsObserver {
            NotificationCenter.default.removeObserver(observer)
        }
""", "Serialize video owners on the main queue and dispose the settings observer")


def apply_compact_chat_list(source: Path) -> None:
    item = source / "submodules/ChatListUI/Sources/Node/ChatListItem.swift"
    replace_unique(item, "    public var approximateHeight: CGFloat {", """    fileprivate var nagramiXCompactLayout: Bool {
        guard NagramiXTabSettings.compactChatListEnabled, !self.interaction.isInlineMode, !self.useCommunityViewLayout else {
            return false
        }
        switch self.chatListLocation {
        case .chatList, .savedMessagesChats:
            break
        default:
            return false
        }
        if case .forum = self.index { return false }
        if case let .peer(data) = self.content, data.displayAsMessage || data.customMessageListData != nil {
            return false
        }
        return true
    }

    public var approximateHeight: CGFloat {""", "Limit compact geometry to standard chat rows, not message results or topic lists")
    replace_unique(item, "    public private(set) var item: ChatListItem?", "    private var nagramiXWasCompactAvatar = false\n\n    public private(set) var item: ChatListItem?", "Track compact placeholder font reuse")
    old = "var avatarDiameter = min(60.0, floor(item.presentationData.fontSize.baseDisplaySize * 60.0 / 17.0))"
    text = item.read_text()
    if text.count(old) != 2:
        raise SystemExit("Pinned chat avatar setup/layout diameter must occur twice")
    text = text.replace(old, old + "\n            if item.nagramiXCompactLayout {\n                avatarDiameter = min(36.0, floor(item.presentationData.fontSize.baseDisplaySize * 36.0 / 17.0))\n            }")
    item.write_text(text)
    replace_unique(item, "            if avatarDiameter != 60.0 {", "            if avatarDiameter != 60.0 || self.nagramiXWasCompactAvatar {", "Restore the original placeholder font when compact mode is disabled")
    replace_unique(item, "            let avatarClipStyle: AvatarNodeClipStyle", "            self.nagramiXWasCompactAvatar = item.nagramiXCompactLayout\n            let avatarClipStyle: AvatarNodeClipStyle", "Record avatar reuse state after resetting font")
    replace_unique(item, "synchronousLoad: synchronousLoads, displayDimensions: CGSize(width: 60.0, height: 60.0))", "synchronousLoad: synchronousLoads, displayDimensions: item.nagramiXCompactLayout ? CGSize(width: avatarDiameter, height: avatarDiameter) : CGSize(width: 60.0, height: 60.0))", "Render compact placeholder avatars at the same size as photos")
    replace_unique(item, "            let titleFont = Font.semibold", "            let nagramiXCompact = item.nagramiXCompactLayout\n            let nagramiXCompactVerticalInset = floor(5.0 * item.presentationData.fontSize.itemListBaseFontSize / 17.0)\n            let titleFont = Font.semibold", "Snapshot compact row geometry per layout")
    for declaration, compact_size, stock_size in [
        ("titleFont = Font.semibold", 15, 16),
        ("textFont = Font.regular", 14, 15),
        ("italicTextFont = Font.italic", 14, 15),
        ("dateFont = Font.regular", 12, 14),
    ]:
        old_font = f"            let {declaration}(floor(item.presentationData.fontSize.itemListBaseFontSize * {stock_size}.0 / 17.0))"
        new_font = f"            let {declaration}(floor(item.presentationData.fontSize.itemListBaseFontSize * (nagramiXCompact ? {compact_size}.0 : {stock_size}.0) / 17.0))"
        replace_unique(item, old_font, new_font, f"Compact chat {declaration.split(' = ')[0]} with native font scaling")
    replace_unique(item, "            let avatarLeftEdgeInset: CGFloat = item.useCommunityViewLayout ? 10.0 : 16.0", "            let avatarLeftEdgeInset: CGFloat = nagramiXCompact ? 14.0 : (item.useCommunityViewLayout ? 10.0 : 16.0)", "Align compact avatars with the reference list inset")
    replace_unique(item, "                    avatarLeftInset = 24.0 + avatarDiameter", "                    avatarLeftInset = (nagramiXCompact ? 22.0 : 24.0) + avatarDiameter", "Keep compact chat titles close to their avatars")
    replace_unique(item, "            let (authorLayout, authorApply) = authorLayout(item.context", """            if nagramiXCompact && forumThreads.isEmpty, let author = effectiveAuthorTitle, let preview = textAttributedString {
                let combinedPreview = NSMutableAttributedString(attributedString: author)
                combinedPreview.append(NSAttributedString(string: ": ", font: textFont, textColor: theme.authorNameColor))
                combinedPreview.append(preview)
                textAttributedString = combinedPreview
                effectiveAuthorTitle = nil
            }

            let (authorLayout, authorApply) = authorLayout(item.context""", "Preserve author and draft attribution inline in a compact preview")
    replace_unique(item, "maximumNumberOfLines: (authorAttributedString == nil && itemTags.isEmpty && forumThread == nil && topForumTopicItems.isEmpty) ? 2 : 1,", "maximumNumberOfLines: nagramiXCompact ? 1 : ((authorAttributedString == nil && itemTags.isEmpty && forumThread == nil && topForumTopicItems.isEmpty) ? 2 : 1),", "Use a single preview line only when compact mode is enabled")
    replace_unique(item, "            var inputActivitiesSize: CGSize?", """            // ChatListInputActivitiesNode returns its boundingSize even for .none.
            // In compact rows, bound it to one preview line, not the stock 40pt area.
            let inputActivitiesHeight: CGFloat = nagramiXCompact ? max(textLayout.size.height, ceil(titleFont.lineHeight) + 4.0) : 40.0
            var inputActivitiesSize: CGSize?""", "Bound compact typing indicators to the measured preview line")
    for activity_peer, activities in [("chatPeerId", "inputActivities"), ("nil", "[]")]:
        replace_unique(item,
            f"inputActivitiesLayout(CGSize(width: rawContentWidth - badgeSize, height: 40.0), item.presentationData, item.presentationData.theme.chatList.messageTextColor, {activity_peer}, {activities})",
            f"inputActivitiesLayout(CGSize(width: rawContentWidth - badgeSize, height: inputActivitiesHeight), item.presentationData, item.presentationData.theme.chatList.messageTextColor, {activity_peer}, {activities})",
            "Use compact typing bounds for active state and native state cleanup")
    replace_unique(item, "            let rawContentRect = CGRect(origin:", """            if nagramiXCompact {
                let fontScale = item.presentationData.fontSize.itemListBaseFontSize / 17.0
                let topPadding = nagramiXCompactVerticalInset
                let activityHeight: CGFloat = inputActivities?.isEmpty == false ? (inputActivitiesSize?.height ?? 0.0) : 0.0
                let previewHeight = max(textLayout.size.height, activityHeight)
                let textBottom = topPadding + titleLayout.size.height - 2.0 + max(0.0, authorLayout.height - 3.0) + previewHeight
                var compactHeight = max(48.0, max(avatarDiameter + 12.0, ceil(textBottom + nagramiXCompactVerticalInset)))
                if !itemTags.isEmpty {
                    let tagBottom = topPadding + measureLayout.size.height * 2.0 + floorToScreenPixels(22.0 * fontScale)
                    compactHeight = max(compactHeight, ceil(tagBottom + nagramiXCompactVerticalInset))
                }
                itemHeight = compactHeight
            }

            let rawContentRect = CGRect(origin:""", "Measure compact row height from text, activity, avatar, tags and topic details")
    replace_unique(item,
        "            let rawContentRect = CGRect(origin: CGPoint(x: 2.0, y: layoutOffset + floor(item.presentationData.fontSize.itemListBaseFontSize * 8.0 / 17.0)), size: CGSize(width: rawContentWidth, height: itemHeight - 12.0 - 9.0))",
        "            let rawContentRect = CGRect(origin: CGPoint(x: 2.0, y: layoutOffset + (nagramiXCompact ? nagramiXCompactVerticalInset : floor(item.presentationData.fontSize.itemListBaseFontSize * 8.0 / 17.0))), size: CGSize(width: rawContentWidth, height: nagramiXCompact ? max(0.0, itemHeight - nagramiXCompactVerticalInset * 2.0) : itemHeight - 12.0 - 9.0))",
        "Use the compact text surface for titles, previews, dates and trailing badges")

    node = source / "submodules/ChatListUI/Sources/Node/ChatListNode.swift"
    replace_unique(node, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Read compact chat preference in every list including cached folders")
    replace_unique(node, "    private let nagramiXSettingsRevision =", "    private var nagramiXCompactObserver: NSObjectProtocol?\n    private let nagramiXSettingsRevision =", "Compact list observer state")
    replace_unique(node, "        super.init()\n", """        super.init()

        self.nagramiXCompactObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.compactChatListChangedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.nagramiXRefreshSettings()
        })
""", "Refresh all existing chat list nodes on compact mode changes")
    replace_unique(node, "        let previousChatListFilters = Atomic<[ChatListFilter]?>(value: nil)", "        let previousCompactChatList = Atomic<Bool>(value: NagramiXTabSettings.compactChatListEnabled)\n        let previousChatListFilters = Atomic<[ChatListFilter]?>(value: nil)", "Track geometry change independently of backend entry equality")
    replace_unique(node, "            var forceAllUpdated = false", """            var forceAllUpdated = false
            let compactChatList = NagramiXTabSettings.compactChatListEnabled
            if previousCompactChatList.swap(compactChatList) != compactChatList {
                forceAllUpdated = true
            }""", "Force native row rebind when compact geometry changes but message data is equal")
    replace_unique(node, "    deinit {\n        self.chatListDisposable.dispose()", """    deinit {
        if let observer = self.nagramiXCompactObserver {
            NotificationCenter.default.removeObserver(observer)
        }
        self.chatListDisposable.dispose()""", "Remove compact list notification observer")


def apply_features(source: Path) -> None:
    overlay = Path(__file__).resolve().parent

    # Полный русский ресурс доступен до сети и авторизации. Нельзя
    # маскировать английские строки под русскую локализацию.
    # Preserve pinned appearance, allowing only exact color-read and variant
    # compatibility substitutions. Builtin palettes, fonts and layout stay stock.
    stock_appearance_paths = [
        "submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift",
        "submodules/Display/Source/Font.swift",
        "submodules/ItemListUI/Sources/ItemListControllerSegmentedTitleView.swift",
        "submodules/TelegramUI/Components/HorizontalTabsComponent/Sources/HorizontalTabsComponent.swift",
        "submodules/TelegramUI/Components/ChatThemeScreen/Sources/ChatThemeScreen.swift",
        "submodules/TelegramUI/Components/Settings/ThemeSettingsThemeItem/Sources/ThemeSettingsThemeItem.swift",
        "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderNode.swift",
        "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderActionButtonNode.swift",
        "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderNavigationButton.swift",
        "submodules/TelegramUI/Components/ChatListHeaderComponent/Sources/NavigationButtonComponent.swift",
        "submodules/SearchBarNode/Sources/SearchBarNode.swift",
        "submodules/PresentationDataUtils/Sources/SolidRoundedButtonNode.swift",
        "submodules/TelegramUI/Components/Settings/ThemeAccentColorScreen/Sources/ThemeAccentColorController.swift",
        "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/ListItems/PeerInfoScreenActionItem.swift",
        "submodules/SettingsUI/Sources/Themes/ThemeAutoNightSettingsController.swift",
        "submodules/SettingsUI/Sources/ThemePickerController.swift",
    ]
    stock_appearance_paths += [
        "submodules/TelegramPresentationData/Sources/" + name + ".swift"
        for name in ("DefaultDayPresentationTheme", "DefaultDarkPresentationTheme", "DefaultDarkTintedPresentationTheme", "MakePresentationTheme", "PresentationTheme", "PresentationThemeCodable", "PresentationThemeCoder")
    ]
    stock_appearance_paths += [
        "submodules/SettingsUI/Sources/Themes/" + name + ".swift"
        for name in ("ThemeSettingsController", "ThemeSettingsAccentColorItem", "ThemeSettingsBrightnessItem", "ThemeSettingsChatPreviewItem", "ThemeSettingsFontSizeItem")
    ]
    stock_appearance = {name: (source / name).read_bytes() for name in stock_appearance_paths}
    compatible_theme_sources = apply_telegram_theme_color_compatibility(source)
    compatible_theme_sources.update(apply_telegram_theme_variant_compatibility(source))

    english_app_strings = source / "Telegram" / "Telegram-iOS" / "en.lproj" / "Localizable.strings"
    russian_app_strings = source / "Telegram" / "Telegram-iOS" / "ru.lproj" / "Localizable.strings"
    russian_strings_text = (overlay / "Resources" / "ru.lproj" / "Localizable.strings").read_text(encoding="utf-8")
    # A shared, audited set of control labels applies both offline and after
    # Telegram downloads a Russian language pack. Never rewrite arbitrary text.
    full_russian_labels = json.loads((overlay / "Resources" / "ru-full-control-labels.json").read_text(encoding="utf-8"))
    for key, value in full_russian_labels.items():
        matches = re.findall(rf'^"{re.escape(key)}"\s*=\s*"((?:\\.|[^"\\])*)";', russian_strings_text, re.MULTILINE)
        if not matches or any(match != value for match in matches):
            raise SystemExit(f"Full Russian control label differs from bundled localization: {key}")
    full_russian_labels_swift = "\n".join(
        f"    {json.dumps(key, ensure_ascii=False)}: {json.dumps(value, ensure_ascii=False)},"
        for key, value in full_russian_labels.items()
    )
    key_pattern = re.compile(r'^"([^"\n]+)"\s*=', re.MULTILINE)
    missing_keys = set(key_pattern.findall(english_app_strings.read_text(encoding="utf-8"))) - set(key_pattern.findall(russian_strings_text))
    if missing_keys:
        raise SystemExit(f"Russian localization is missing upstream keys: {sorted(missing_keys)}")
    russian_tour_strings = {
        "Tour.Title1": "Telegram",
        "Tour.Text1": "Самый **быстрый** мессенджер в мире.\\nОн **бесплатный** и **безопасный**.",
        "Tour.Title2": "Быстрый",
        "Tour.Text2": "**Telegram** доставляет сообщения\\nбыстрее других приложений.",
        "Tour.Title3": "Мощный",
        "Tour.Text3": "В **Telegram** нет ограничений\\nна размер медиафайлов и чатов.",
        "Tour.Title4": "Безопасный",
        "Tour.Text4": "**Telegram** защищает ваши сообщения\\nот атак злоумышленников.",
        "Tour.Title5": "Облачный",
        "Tour.Text5": "**Telegram** даёт доступ к сообщениям\\nс нескольких устройств.",
        "Tour.Title6": "Бесплатный",
        "Tour.Text6": "**Telegram** предоставляет бесплатное\\nоблачное хранилище для чатов и медиа.",
        "Tour.StartButton": "Начать общение",
    }
    for key, value in russian_tour_strings.items():
        pattern = re.compile(rf'("{re.escape(key)}"\s*=\s*")([^"\\]*(?:\\.[^"\\]*)*)(";)')
        russian_strings_text, replacement_count = pattern.subn(
            lambda match, value=value: match.group(1) + value + match.group(3),
            russian_strings_text,
            count=1,
        )
        if replacement_count != 1:
            raise SystemExit(f"Pinned Russian welcome string anchor must occur exactly once ({key})")
    russian_app_strings.parent.mkdir(parents=True, exist_ok=True)
    russian_app_strings.write_text(russian_strings_text, encoding="utf-8")

    data_storage_controller = source / "submodules/SettingsUI/Sources/Data and Storage/DataAndStorageSettingsController.swift"
    replace_unique(
        data_storage_controller,
        """            case let .saveEditedPhotos(_, text, value):
                return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, sectionId: self.section, style: .blocks, updated: { value in""",
        """            case let .saveEditedPhotos(_, text, value):
                return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: { value in""",
        "Wrap the full edited-photo setting label using native ItemList sizing",
    )

    telegram_build = source / "Telegram" / "BUILD"
    replace_unique(
        telegram_build,
        '    "ru",\n',
        '',
        "Do not overwrite the NagramiX Russian strings with Telegram's empty placeholder",
    )
    replace_unique(
        telegram_build,
        '''    srcs = [
        "Telegram-iOS/en.lproj/Localizable.strings",
    ] + [''',
        '''    srcs = [
        "Telegram-iOS/en.lproj/Localizable.strings",
        "Telegram-iOS/ru.lproj/Localizable.strings",
    ] + [''',
        "Bundle the complete NagramiX Russian clean-install dictionary",
    )

    settings_icons_source = overlay / "Assets" / "SettingsIcons"
    settings_icons_target = source / "submodules" / "TelegramUI" / "Images.xcassets" / "Item List" / "Icons"
    for icon_source in settings_icons_source.iterdir():
        if icon_source.is_dir():
            shutil.copytree(icon_source, settings_icons_target / icon_source.name, dirs_exist_ok=True)

    presentation_resources_settings = source / "submodules" / "TelegramPresentationData" / "Sources" / "Resources" / "PresentationResourcesSettings.swift"
    replace_once(
        presentation_resources_settings,
        """    public static let support = renderSettingsIcon(name: "Item List/Icons/Support", backgroundColors: [colorOrange])
    public static let faq = renderSettingsIcon(name: "Item List/Icons/Faq", backgroundColors: [colorLightBlue])
    public static let tips = renderSettingsIcon(name: "Item List/Icons/Tips", backgroundColors: [UIColor(rgb: 0xffcc02)])
""",
        """    public static let support = renderSettingsIcon(name: "Item List/Icons/Support", backgroundColors: [colorOrange])
    public static let faq = renderSettingsIcon(name: "Item List/Icons/Faq", backgroundColors: [colorLightBlue])
    public static let tips = renderSettingsIcon(name: "Item List/Icons/Tips", backgroundColors: [UIColor(rgb: 0xffcc02)])
    public static let nagramiXSettings = renderSettingsIcon(name: "Chat List/Tabs/IconSettings", scaleFactor: 0.72, backgroundColors: [colorBlue])
    public static let nagramiXFeatures = renderSettingsIcon(name: "Item List/Icons/Tips", backgroundColors: [colorPurple])
    public static let nagramiXUpdates = renderSettingsIcon(name: "Item List/Icons/NagramiXUpdates", backgroundColors: [colorOrange])
""",
        "NagramiX information block icons",
    )

    default_strings = source / "submodules" / "TelegramPresentationData" / "Sources" / "DefaultPresentationStrings.swift"
    replace_once(
        default_strings,
        'PresentationStrings.Component(languageCode: "en", localizedName: "English", pluralizationRulesCode: nil, dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "en")!))',
        'PresentationStrings.Component(languageCode: "ru", localizedName: "Русский", pluralizationRulesCode: nil, dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!))',
        "Use Russian as the clean-install primary localization",
    )
    replace_once(
        default_strings,
        """public let defaultPresentationStrings = PresentationStrings(primaryComponent:""",
        "let nagramiXFullRussianControlLabels: [String: String] = [\n" + full_russian_labels_swift + "\n]\n\n" + """let nagramiXDefaultRussianDictionary: [String: String] = {
    var dictionary = NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!)) as! [String: String]
    dictionary.merge(nagramiXFullRussianControlLabels, uniquingKeysWith: { _, fullLabel in fullLabel })
    return dictionary
}()

public let defaultPresentationStrings = PresentationStrings(primaryComponent:""",
        "Use full Russian control labels in the default locale",
    )
    replace_once(
        default_strings,
        'dict: NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!)) as! [String : String]), secondaryComponent:',
        'dict: nagramiXDefaultRussianDictionary), secondaryComponent:',
        "Use the corrected Russian dictionary on clean install",
    )

    presentation_theme_settings = source / "submodules" / "TelegramUIPreferences" / "Sources" / "PresentationThemeSettings.swift"
    # Verify stock defaults; the application's missing-entry initialization below
    # selects a builtin theme without modifying these defaults or factories.
    expected_system_defaults = "PresentationThemeSettings(theme: .builtin(.dayClassic), themePreferredBaseTheme: [:], themeSpecificAccentColors: [:], themeSpecificChatWallpapers: [:], useSystemFont: true, fontSize: .regular, listsFontSize: .regular, chatBubbleSettings: .default, automaticThemeSwitchSetting: AutomaticThemeSwitchSetting(force: false, trigger: .system, theme: .builtin(.night)), largeEmoji: true, reduceMotion: false)"
    if presentation_theme_settings.read_text(encoding="utf-8").count(expected_system_defaults) != 1:
        raise SystemExit("Pinned Telegram system-theme defaults no longer match")

    app_delegate = source / "submodules" / "TelegramUI" / "Sources" / "AppDelegate.swift"
    replace_unique(
        app_delegate,
        "        let sharedContextSignal = currentPresentationDataAndSettings(accountManager: accountManager, systemUserInterfaceStyle: systemUserInterfaceStyle)\n",
        """        // Seed only a missing theme preference before the first UI is constructed.
        // Keep Telegram's default day theme; select System and builtin Dark (Tinted)
        // for night mode. All later choices use the stock presentation pipeline.
        let nagramiXInitialTheme = accountManager.transaction { transaction -> Void in
            transaction.updateSharedData(ApplicationSpecificSharedDataKeys.presentationThemeSettings, { entry in
                guard entry == nil else { return entry }
                let settings = PresentationThemeSettings.defaultSettings
                    .withUpdatedAutomaticThemeSwitchSetting(AutomaticThemeSwitchSetting(force: false, trigger: .system, theme: .builtin(.nightAccent)))
                return EnginePreferencesEntry(settings)
            })
        }
        let sharedContextSignal = nagramiXInitialTheme
        |> mapToSignal { _ in
            return currentPresentationDataAndSettings(accountManager: accountManager, systemUserInterfaceStyle: systemUserInterfaceStyle)
        }
""",
        "Select stock Telegram System with Dark night theme only when no choice exists",
    )

    presentation_data = source / "submodules" / "TelegramPresentationData" / "Sources" / "PresentationData.swift"
    replace_once(
        presentation_data,
        "public func dictFromLocalization(_ value: Localization) -> [String: String] {",
        "public func dictFromLocalization(_ value: Localization, languageCode: String? = nil) -> [String: String] {",
        "Pass locale identity into downloaded localization conversion",
    )
    replace_unique(
        presentation_data,
        """    var dict: [String: String] = [:]
    for entry in value.entries {""",
        """    var dict: [String: String] = [:]
    if languageCode?.lowercased().hasPrefix("ru") == true {
        dict = nagramiXDefaultRussianDictionary
    }
    for entry in value.entries {""",
        "Keep complete offline Russian strings underneath downloaded localization entries",
    )
    replace_once(
        presentation_data,
        """    return dict
}

private func currentDateTimeFormat()""",
        """    if languageCode?.lowercased().hasPrefix("ru") == true {
        dict.merge(nagramiXFullRussianControlLabels, uniquingKeysWith: { _, fullLabel in fullLabel })
    }
    return dict
}

private func currentDateTimeFormat()""",
        "Keep full control labels after Russian language-pack updates",
    )
    presentation_data_text = presentation_data.read_text(encoding="utf-8")
    presentation_data_text = presentation_data_text.replace(
        "dictFromLocalization(localizationSettings.primaryComponent.localization)",
        "dictFromLocalization(localizationSettings.primaryComponent.localization, languageCode: localizationSettings.primaryComponent.languageCode)",
    ).replace(
        "dictFromLocalization($0.localization)",
        "dictFromLocalization($0.localization, languageCode: $0.languageCode)",
    )
    presentation_data.write_text(presentation_data_text, encoding="utf-8")

    intro_controller = source / "submodules" / "RMIntro" / "Sources" / "platform" / "ios" / "RMIntroViewController.m"
    replace_once(
        intro_controller,
        'NSBundle *bundle = [NSBundle bundleWithPath:[[NSBundle mainBundle] pathForResource:@"en" ofType:@"lproj"]];',
        'NSBundle *bundle = [NSBundle bundleWithPath:[[NSBundle mainBundle] pathForResource:@"ru" ofType:@"lproj"]];',
        "Render every clean-install welcome carousel page from Russian resources",
    )

    authorization_splash = source / "submodules" / "AuthorizationUI" / "Sources" / "AuthorizationSequenceSplashController.swift"
    replace_unique(
        authorization_splash,
        '''        self.suggestedLocalization.set(.single(nil)
        |> then(TelegramEngineUnauthorized(account: self.account).localization.currentlySuggestedLocalization(extractKeys: ["Login.ContinueWithLocalization"])))
        let suggestedLocalization = self.suggestedLocalization
''',
        '''        self.suggestedLocalization.set(.single(nil))
''',
        "Skip automatic language suggestions on the Russian first launch",
    )
    replace_between(
        authorization_splash,
        "        let localizationSignal = SSignal(generator:",
        "        self.controller = RMIntroViewController(",
        """        let localizationSignal = SSignal(generator: { subscriber in
            subscriber.putCompletion()
            return SBlockDisposable(block: {})
        })

""",
        "Do not offer another language during the Russian welcome flow",
    )
    replace_once(
        authorization_splash,
        'self.startButton = SolidRoundedButtonNode(title: "Start Messaging", theme:',
        'self.startButton = SolidRoundedButtonNode(title: "Начать общение", theme:',
        "Show the clean-install welcome action in Russian",
    )
    replace_unique(
        authorization_splash,
        '''        self.controller.startMessaging = { [weak self] in
            self?.activateLocalization("en")
        }''',
        '''        self.controller.startMessaging = { [weak self] in
            self?.activateDefaultLocalization()
        }''',
        "Keep the native welcome action on Russian",
    )
    replace_unique(
        authorization_splash,
        '''        self.startButton.pressed = { [weak self] in
            self?.activateLocalization("en")
        }''',
        '''        self.startButton.pressed = { [weak self] in
            self?.activateDefaultLocalization()
        }''',
        "Start authorization in Russian",
    )
    replace_once(
        authorization_splash,
        '''            } else {
                return "en"
            }
        }
        let suggestedCode = self.suggestedLocalization.get()''',
        '''            } else {
                return ""
            }
        }
        let suggestedCode = self.suggestedLocalization.get()''',
        "Download and persist Russian before authorization when no language is saved",
    )

    replace_unique(
        authorization_splash,
        "    private func activateLocalization(_ code: String) {",
        """    private func activateDefaultLocalization() {
        let _ = (self.accountManager.transaction { transaction -> String in
            return transaction.getSharedData(SharedDataKeys.localizationSettings)?.get(LocalizationSettings.self)?.primaryComponent.languageCode ?? "ru"
        }
        |> deliverOnMainQueue).start(next: { [weak self] code in
            self?.activateLocalization(code)
        })
    }

    private func activateLocalization(_ code: String) {""",
        "Use Russian on first install while preserving a saved manual language for added accounts",
    )

    # Authorization and logged-in UI must agree about the missing-language default.
    localization_updates = source / "submodules" / "TelegramCore" / "Sources" / "State" / "ManagedLocalizationUpdatesOperations.swift"
    replace_unique(
        localization_updates,
        'return (primary: ("en", 0, []), secondary: nil)',
        'return (primary: ("ru", 0, []), secondary: nil)',
        "Synchronize Russian rather than English when no language preference exists",
    )
    localization_updates_text = localization_updates.read_text(encoding="utf-8")
    missing_localization_default = 'LocalizationSettings(primaryComponent: LocalizationComponent(languageCode: "en", localizedName: "English", localization: Localization(version: 0, entries: []), customPluralizationCode: nil), secondaryComponent: nil)'
    if localization_updates_text.count(missing_localization_default) != 2:
        raise SystemExit("Pinned localization update defaults no longer match")
    localization_updates.write_text(localization_updates_text.replace(
        missing_localization_default,
        missing_localization_default.replace('languageCode: "en", localizedName: "English"', 'languageCode: "ru", localizedName: "Русский"'),
    ), encoding="utf-8")
    authorization_splash_text = authorization_splash.read_text(encoding="utf-8")
    authorization_splash_text = authorization_splash_text.replace(
        "dictFromLocalization(localizationSettings.primaryComponent.localization)",
        "dictFromLocalization(localizationSettings.primaryComponent.localization, languageCode: localizationSettings.primaryComponent.languageCode)",
    ).replace(
        "dictFromLocalization($0.localization)",
        "dictFromLocalization($0.localization, languageCode: $0.languageCode)",
    )
    authorization_splash.write_text(authorization_splash_text, encoding="utf-8")

    core_source = overlay / "Sources" / "NagramiXCore"
    core_target = source / "submodules" / "NagramiXCore"
    if core_target.exists():
        raise SystemExit(f"NagramiXCore already exists in the source tree: {core_target}")
    shutil.copytree(core_source, core_target)

    mtproto_source = overlay / "Sources" / "MtProtoKit"
    mtproto_target = source / "submodules" / "MtProtoKit" / "Sources"
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.h", mtproto_target / "NagramiXDNSResolver.h")
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.m", mtproto_target / "NagramiXDNSResolver.m")
    mtproto_public = source / "submodules" / "MtProtoKit" / "PublicHeaders" / "MtProtoKit"
    shutil.copy2(mtproto_source / "NagramiXDNSResolver.h", mtproto_public / "NagramiXDNSResolver.h")
    replace_once(
        mtproto_public / "MtProtoKit.h",
        "#import <MtProtoKit/MTProxyConnectivity.h>\n",
        "#import <MtProtoKit/MTProxyConnectivity.h>\n#import <MtProtoKit/NagramiXDNSResolver.h>\n",
        "Expose NagramiX DoH endpoint validation to SettingsUI",
    )

    mt_dns = mtproto_target / "MTDNS.m"
    replace_once(
        mt_dns,
        '#import "MTDNS.h"\n',
        '#import "MTDNS.h"\n#import "NagramiXDNSResolver.h"\n',
        "NagramiX real DoH resolver import",
    )
    replace_once(
        mt_dns,
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    return [[self resolveHostname:hostname] timeout:10.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[self resolveHostnameNative:hostname port:port]];
}
""",
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    if ([NagramiXDNSResolver usesSystemResolver]) {
        return [self resolveHostnameNative:hostname port:port];
    }
    MTSignal *doh = [[NagramiXDNSResolver resolveHostname:hostname] timeout:12.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal fail:[NSError errorWithDomain:@"org.nagramix.dns" code:5 userInfo:nil]]];
    return [doh catch:^MTSignal *(__unused id error) {
        // Keep DoH primary, but never let an unreachable provider hold app
        // startup hostage by repeatedly closing every MTProto connection.
        if (MTLogEnabled()) {
            MTLog(@"[NagramiXDNS DoH unavailable; falling back to native resolver]");
        }
        return [self resolveHostnameNative:hostname port:port];
    }];
}

+ (MTSignal *)testDohEndpoint:(NSString *)endpoint hostname:(NSString *)hostname {
    return [[NagramiXDNSResolver testEndpoint:endpoint hostname:hostname] timeout:12.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal fail:[NSError errorWithDomain:@"org.nagramix.dns" code:6 userInfo:nil]]];
}
""",
        "Use selected System or DoH resolver in the real MTProto proxy DNS path",
    )

    mt_dns_header = mtproto_target / "MTDNS.h"
    replace_once(
        mt_dns_header,
        "+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port;\n",
        "+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port;\n+ (MTSignal *)testDohEndpoint:(NSString *)endpoint hostname:(NSString *)hostname;\n",
        "Expose Custom DoH validation through the actual resolver",
    )

    mt_tcp_connection = mtproto_target / "MTTcpConnection.m"
    replace_once(
        mt_tcp_connection,
        """                }];
            } file:__FILE_NAME__ line:__LINE__]];
""",
        """                }];
            } error:^(id error) {
                (void)error;
                [[MTTcpConnection tcpQueue] dispatchOnQueue:^{
                    __strong MTTcpConnection *strongSelf = weakSelf;
                    if (strongSelf != nil) {
                        [strongSelf closeAndNotifyWithError:true];
                    }
                }];
            } completed:nil file:__FILE_NAME__ line:__LINE__]];
""",
        "Close MTProto connection when the selected DoH resolver fails",
    )

    network_source = source / "submodules" / "TelegramCore" / "Sources" / "Network" / "Network.swift"
    replace_unique(
        network_source,
        'apiEnvironment = apiEnvironment.withUpdatedLangPackCode(languageCode ?? "en")',
        'apiEnvironment = apiEnvironment.withUpdatedLangPackCode(languageCode ?? "ru")',
        "Use Russian for the network language pack only when no language was selected",
    )
    replace_once(
        network_source,
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }
""",
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }

    public func reconnectForNagramiXDnsChange() {
        self.mtProto.simulateDisconnection()
        self.dropConnectionStatus()
    }
""",
        "Reconnect MTProto after a runtime DNS resolver change",
    )

    account_source = source / "submodules" / "TelegramCore" / "Sources" / "Account" / "Account.swift"
    replace_once(
        account_source,
        """        }))

        if !supplementary {
            let mediaBox = postbox.mediaBox
""",
        """        }))

        let nagramiXDnsObserver = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXDnsSettingsChanged"), object: nil, queue: nil, using: { _ in
            network.reconnectForNagramiXDnsChange()
        })
        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
            let mediaBox = postbox.mediaBox
""",
        "Reconnect every account network when the selected resolver changes",
    )
    replace_once(
        account_source,
        """        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
""",
        """        self.managedOperationsDisposable.add(ActionDisposable {
            NotificationCenter.default.removeObserver(nagramiXDnsObserver)
        })

        if !supplementary {
            let nagramiXProxyFailoverController = NagramiXProxyFailoverController()
            nagramiXProxyFailoverController.start(accountManager: accountManager, network: network)
            self.managedOperationsDisposable.add(ActionDisposable {
                nagramiXProxyFailoverController.stop()
            })
        }

        if !supplementary {
""",
        "Start the process-wide proxy failover controller outside UI lifecycle",
    )

    replace_unique(
        network_source,
        "public final class Network: NSObject, MTRequestMessageServiceDelegate {\n",
        "public final class Network: NSObject, MTRequestMessageServiceDelegate {\n    public let nagramiXProxyStatuses = Atomic<ProxyServersStatuses?>(value: nil)\n",
        "Share proxy health checks safely between the account and its settings UI",
    )

    settings_controller_source = overlay / "Sources" / "SettingsUI" / "NagramiXSettingsController.swift"
    settings_controller_target = source / "submodules" / "SettingsUI" / "Sources" / settings_controller_source.name
    shutil.copy2(settings_controller_source, settings_controller_target)
    shutil.copy2(overlay / "Sources" / "SettingsUI" / "NagramiXCustomDohController.swift", settings_controller_target.parent / "NagramiXCustomDohController.swift")

    item_list_controller = source / "submodules" / "ItemListUI" / "Sources" / "ItemListController.swift"
    replace_once(
        item_list_controller,
        "    case sectionControl([String], Int)\n",
        "    case sectionControl([String], Int)\n    case equalSectionControl([String], Int)\n",
        "Equal-width NagramiX settings title mode",
    )
    # Leave the stock sectionControl branch intact. Only NagramiX uses the custom view.
    item_list_text = item_list_controller.read_text(encoding="utf-8")
    section_start = "                            case let .sectionControl(sections, index):"
    section_end = "                            case let .textWithTabs(title, sections, index):"
    if item_list_text.count(section_start) != 1 or item_list_text.count(section_end) != 1:
        raise SystemExit("Pinned stock section-control branch no longer matches")
    stock_section = item_list_text[item_list_text.index(section_start):item_list_text.index(section_end)]
    custom_section = stock_section.replace(".sectionControl(sections, index)", ".equalSectionControl(sections, index)").replace("segmentedTitleView", "nagramiXSegmentedTitleView").replace("ItemListControllerSegmentedTitleView", "NagramiXItemListControllerSegmentedTitleView").replace("selectedIndex: index)", "selectedIndex: index, fillsAvailableWidth: true)")
    item_list_controller.write_text(item_list_text.replace(section_end, custom_section + section_end, 1), encoding="utf-8")
    replace_unique(
        item_list_controller,
        "    private var segmentedTitleView: ItemListControllerSegmentedTitleView?",
        "    private var segmentedTitleView: ItemListControllerSegmentedTitleView?\n    private var nagramiXSegmentedTitleView: NagramiXItemListControllerSegmentedTitleView?",
        "Keep NagramiX title state separate from Telegram title state",
    )
    replace_unique(
        item_list_controller,
        "                        strongSelf.segmentedTitleView?.theme = controllerState.presentationData.theme",
        "                        strongSelf.segmentedTitleView?.theme = controllerState.presentationData.theme\n                        strongSelf.nagramiXSegmentedTitleView?.theme = controllerState.presentationData.theme",
        "Update the isolated NagramiX title with the same native presentation data",
    )

    segmented_title_view = source / "submodules" / "ItemListUI" / "Sources" / "ItemListControllerSegmentedTitleView.swift"
    stock_segmented_title_view = segmented_title_view
    segmented_title_view = segmented_title_view.with_name("NagramiXItemListControllerSegmentedTitleView.swift")
    shutil.copy2(stock_segmented_title_view, segmented_title_view)
    replace_once(
        segmented_title_view,
        "    private let tabSelector = ComponentView<Empty>()\n",
        "    private let tabSelector = ComponentView<Empty>()\n    private let fillsAvailableWidth: Bool\n    private var expandedContentFrame: CGRect?\n",
        "Store full-width NagramiX segmented title layout",
    )
    replace_once(
        segmented_title_view,
        "    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int) {\n",
        "    public init(theme: PresentationTheme, segments: [String], selectedIndex: Int, fillsAvailableWidth: Bool = false) {\n",
        "Add equal-width segmented title initializer",
    )
    replace_once(
        segmented_title_view,
        "        self.index = selectedIndex\n        \n        self.backgroundContainer = GlassBackgroundContainerView()\n",
        "        self.index = selectedIndex\n        self.fillsAvailableWidth = fillsAvailableWidth\n        \n        self.backgroundContainer = GlassBackgroundContainerView()\n",
        "Initialize equal-width segmented title layout",
    )
    replace_once(
        segmented_title_view,
        "                content: .title(HorizontalTabsComponent.Tab.Title(text: segment, entities: [], enableAnimations: false)),\n",
        "                content: .title(HorizontalTabsComponent.Tab.Title(text: segment, entities: [], enableAnimations: false, isBold: self.fillsAvailableWidth)),\n",
        "Use bold NagramiX settings category titles",
    )
    replace_once(
        segmented_title_view,
        "                layout: .fit\n",
        "                layout: self.fillsAvailableWidth ? .equal : .fit\n",
        "Use equal-width NagramiX settings category sections",
    )
    replace_once(
        segmented_title_view,
        """        self.addSubview(self.backgroundContainer)
        self.backgroundContainer.contentView.addSubview(self.backgroundView)
""",
        """        self.clipsToBounds = !self.fillsAvailableWidth
        self.addSubview(self.backgroundContainer)
        self.backgroundContainer.contentView.addSubview(self.backgroundView)

        if self.fillsAvailableWidth {
            self.setContentHuggingPriority(.defaultLow, for: .horizontal)
            self.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        }
""",
        "Allow the NagramiX category panel to use the trailing navigation space",
    )
    replace_once(
        segmented_title_view,
        """    override public func layoutSubviews() {
""",
        """    override public var intrinsicContentSize: CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: UIView.noIntrinsicMetric, height: 44.0)
        }
        return super.intrinsicContentSize
    }

    override public func sizeThatFits(_ size: CGSize) -> CGSize {
        if self.fillsAvailableWidth {
            return CGSize(width: size.width, height: 44.0)
        }
        return super.sizeThatFits(size)
    }

    override public func layoutSubviews() {
""",
        "Make the category title adaptive instead of sizing it from localized text",
    )
    replace_once(
        segmented_title_view,
        "    private func update(transition: ComponentTransition) {\n        guard let size = self.validLayout else {\n            return\n        }\n",
        """    override public func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        if let expandedContentFrame = self.expandedContentFrame, expandedContentFrame.contains(point) {
            return true
        }
        return super.point(inside: point, with: event)
    }

    private func update(transition: ComponentTransition) {
        guard let size = self.validLayout else {
            return
        }

        var contentWidth = size.width
        if self.fillsAvailableWidth, let window = self.window {
            let windowFrame = self.convert(self.bounds, to: window)
            let trailingInset = max(16.0, window.safeAreaInsets.right)
            contentWidth = max(contentWidth, floor(window.bounds.width - windowFrame.minX - trailingInset))
        }
""",
        "Extend the category panel from its post-back-button origin to the content trailing inset",
    )
    replace_once(
        segmented_title_view,
        "            containerSize: CGSize(width: size.width, height: 44.0)\n",
        "            containerSize: CGSize(width: contentWidth, height: 44.0)\n",
        "Give equal category tabs the complete trailing navigation width",
    )
    replace_once(
        segmented_title_view,
        "        let tabSelectorFrame = CGRect(origin: CGPoint(x: floor((size.width - tabSelectorSize.width) / 2.0), y: floor((size.height - tabSelectorSize.height) / 2.0)), size: tabSelectorSize)\n",
        "        let tabSelectorFrame = CGRect(origin: CGPoint(x: self.fillsAvailableWidth ? 0.0 : floor((size.width - tabSelectorSize.width) / 2.0), y: floor((size.height - tabSelectorSize.height) / 2.0)), size: tabSelectorSize)\n        self.expandedContentFrame = tabSelectorFrame\n",
        "Anchor the full-width category panel after the back button instead of centering a compressed control",
    )

    horizontal_tabs = source / "submodules" / "TelegramUI" / "Components" / "HorizontalTabsComponent" / "Sources" / "HorizontalTabsComponent.swift"
    stock_horizontal_tabs = horizontal_tabs
    horizontal_tabs = horizontal_tabs.with_name("NagramiXHorizontalTabsComponent.swift")
    shutil.copy2(stock_horizontal_tabs, horizontal_tabs)
    replace_once(
        horizontal_tabs,
        """    public enum Layout {
        case fit
        case fill
    }
""",
        """    public enum Layout {
        case fit
        case fill
        case equal
    }
""",
        "Add unconditional equal-width horizontal tab layout",
    )
    replace_once(
        horizontal_tabs,
        """            public let enableAnimations: Bool
""" + "            \n" + """            public init(text: String, entities: [MessageTextEntity], enableAnimations: Bool) {
                self.text = text
                self.entities = entities
                self.enableAnimations = enableAnimations
            }
""",
        """            public let enableAnimations: Bool
            public let isBold: Bool
""" + "            \n" + """            public init(text: String, entities: [MessageTextEntity], enableAnimations: Bool, isBold: Bool = false) {
                self.text = text
                self.entities = entities
                self.enableAnimations = enableAnimations
                self.isBold = isBold
            }
""",
        "Support explicitly bold horizontal tab titles",
    )
    replace_once(
        horizontal_tabs,
        "                let font = Font.medium(15.0)\n",
        "                let font = title.isBold ? Font.bold(15.0) : Font.medium(15.0)\n",
        "Render NagramiX settings category titles in bold",
    )
    replace_once(
        horizontal_tabs,
        """            let scrollContentWidth: CGFloat
            if case .fill = component.layout, totalContentWidth < availableSize.width {
""",
        """            let scrollContentWidth: CGFloat
            let usesEqualItemWidths: Bool
            switch component.layout {
            case .fit:
                usesEqualItemWidths = false
            case .fill:
                usesEqualItemWidths = totalContentWidth < availableSize.width
            case .equal:
                usesEqualItemWidths = true
            }
            if usesEqualItemWidths {
""",
        "Always divide NagramiX settings categories equally",
    )
    replace_once(
        horizontal_tabs,
        """            switch component.layout {
            case .fill:
                sizeWidth = availableSize.width
            case .fit:
""",
        """            switch component.layout {
            case .fill, .equal:
                sizeWidth = availableSize.width
            case .fit:
""",
        "Size equal-width NagramiX settings categories to the full panel",
    )

    segmented_text = segmented_title_view.read_text(encoding="utf-8")
    segmented_text = segmented_text.replace("ItemListControllerSegmentedTitleView", "NagramiXItemListControllerSegmentedTitleView")
    segmented_text = segmented_text.replace("HorizontalTabsComponent", "NagramiXHorizontalTabsComponent").replace("import NagramiXHorizontalTabsComponent", "import HorizontalTabsComponent")
    segmented_title_view.write_text(segmented_text, encoding="utf-8")
    horizontal_tabs_text = horizontal_tabs.read_text(encoding="utf-8")
    for identifier in ("HorizontalTabsComponent", "ReorderingGestureRecognizerTimerTarget", "InternalGestureRecognizerDelegate", "ReorderingGestureRecognizer", "ItemComponent"):
        horizontal_tabs_text = re.sub(rf"\b{identifier}\b", "NagramiX" + identifier, horizontal_tabs_text)
    # NagramiX categories live on the navigation surface, not the chat composer.
    if horizontal_tabs_text.count("component.theme.chat.inputPanel.panelControlColor") != 3:
        raise SystemExit("Pinned custom tab color anchors no longer match")
    horizontal_tabs_text = horizontal_tabs_text.replace("component.theme.chat.inputPanel.panelControlColor", "component.theme.rootController.navigationBar.primaryTextColor")
    horizontal_tabs.write_text(horizontal_tabs_text, encoding="utf-8")

    telegram_voip_build = source / "submodules" / "TelegramVoip" / "BUILD"
    replace_once(
        telegram_voip_build,
        '        "//submodules/TelegramCore:TelegramCore",\n',
        '        "//submodules/TelegramCore:TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TelegramVoip NagramiX settings dependency",
    )
    ongoing_call_context = source / "submodules" / "TelegramVoip" / "Sources" / "OngoingCallContext.swift"
    replace_once(
        ongoing_call_context,
        "import CoreMedia\n",
        "import CoreMedia\nimport NagramiXCore\n",
        "VoIP Force TCP settings import",
    )
    replace_once(
        ongoing_call_context,
        "                var allowP2P = allowP2P\n",
        "                var allowP2P = allowP2P\n                let forceTcpCalls = NagramiXTabSettings.current.forceTcpCalls\n",
        "Snapshot Force TCP for the newly created call",
    )
    replace_once(
        ongoing_call_context,
        """                #if DEBUG && true
                var customParameters = customParameters
""",
        """                var customParameters = customParameters

                #if DEBUG && true
""",
        "Make VoIP custom parameters mutable in release builds",
    )
    replace_once(
        ongoing_call_context,
        """                #endif
""" + "                \n" + """                /*#if DEBUG
""",
        """                #endif
""" + "                \n" + """                if forceTcpCalls {
                    var customParametersValue = (try? JSONSerialization.jsonObject(with: (customParameters ?? "{}").data(using: .utf8)!) as? [String: Any]) ?? [:]
                    customParametersValue["network_use_tcponly"] = true as NSNumber
                    customParameters = String(data: try! JSONSerialization.data(withJSONObject: customParametersValue), encoding: .utf8)!
                    filteredConnections = filteredConnections.filter { $0.hasTcp }
                    allowP2P = false
                }

                /*#if DEBUG
""",
        "Force one-to-one calls onto Telegram TCP relay endpoints",
    )
    replace_once(
        ongoing_call_context,
        "                    allowTCP: enableTCP,\n",
        "                    allowTCP: enableTCP || forceTcpCalls,\n",
        "Enable Telegram TCP transport when Force TCP is active",
    )

    telegram_core_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXProxyFailoverController.swift"
    telegram_core_target = source / "submodules" / "TelegramCore" / "Sources" / "Network" / telegram_core_overlay.name
    shutil.copy2(telegram_core_overlay, telegram_core_target)

    proxy_statuses = source / "submodules" / "TelegramCore" / "Sources" / "Network" / "ProxyServersStatuses.swift"
    replace_between(
        proxy_statuses,
        "private final class ProxyServerItemContext {",
        "public final class ProxyServersStatuses {",
        (overlay / "Sources" / "TelegramCore" / "ProxyServersStatuses.swift.inc").read_text(encoding="utf-8"),
        "Bound native proxy checks and retain fresh results outside the UI",
    )
    replace_unique(
        proxy_statuses,
        "public init(network: Network, servers: Signal<[ProxyServerSettings], NoError>) {",
        "public init(network: Network, servers: Signal<[ProxyServerSettings], NoError>, refreshEnabled: Signal<Bool, NoError> = .single(false), activeServer: Signal<ProxyServerSettings?, NoError> = .single(nil)) {",
        "Opt in to periodic proxy checks while enabled",
    )
    replace_unique(
        proxy_statuses,
        "return ProxyServersStatusesImpl(queue: queue, network: network, servers: servers)",
        "return ProxyServersStatusesImpl(queue: queue, network: network, servers: servers, refreshEnabled: refreshEnabled, activeServer: activeServer)",
        "Pass automatic refresh state to the native checker",
    )
    replace_unique(
        proxy_statuses,
        "    public func statuses() -> Signal<[ProxyServerSettings: ProxyServerStatus], NoError> {",
        """    public func stop() {
        self.impl.with { $0.stop() }
    }

    public func recheckAll(servers: [ProxyServerSettings]) {
        self.impl.with { $0.recheckAll(servers: servers) }
    }

    public func refreshIfNeeded() {
        self.impl.with { $0.refreshIfNeeded() }
    }

    public func markUnavailable(_ server: ProxyServerSettings) {
        self.impl.with { $0.markUnavailable(server) }
    }

    public func recordAvailable(_ server: ProxyServerSettings, roundTripTime: Double) {
        self.impl.with { $0.recordAvailable(server, roundTripTime: roundTripTime) }
    }

    public func availableServers(maxAge: Double = 180.0) -> Signal<Set<ProxyServerSettings>, NoError> {
        return Signal { subscriber in
            self.impl.with { impl in
                subscriber.putNext(impl.availableServers(maxAge: maxAge))
                subscriber.putCompletion()
            }
            return EmptyDisposable
        }
    }

    public func statuses() -> Signal<[ProxyServerSettings: ProxyServerStatus], NoError> {""",
        "Expose manual refresh and a fresh snapshot to failover",
    )

    settings_build = source / "submodules" / "SettingsUI" / "BUILD"
    replace_once(
        settings_build,
        '        "//submodules/AccountContext:AccountContext",\n',
        '        "//submodules/AccountContext:AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "SettingsUI NagramiXCore dependency",
    )
    shutil.copy2(
        overlay / "Sources" / "SettingsUI" / "NagramiXSettingsSearchHeader.swift",
        source / "submodules" / "SettingsUI" / "Sources" / "NagramiXSettingsSearchHeader.swift",
    )

    proxy_list = source / "submodules" / "SettingsUI" / "Sources" / "Data and Storage" / "ProxyListSettingsController.swift"
    replace_once(
        proxy_list,
        "import UrlEscaping\n",
        "import UrlEscaping\nimport UndoUI\nimport NagramiXCore\n",
        "Proxy settings NagramiXCore import",
    )
    replace_between(
        proxy_list,
        "private final class ProxySettingsControllerArguments {",
        "private struct ProxySettingsControllerState: Equatable {",
        (overlay / "Sources" / "SettingsUI" / "ProxyListNagramiXBlock.swift.inc").read_text(encoding="utf-8"),
        "Proxy screen DNS and automatic failover controls",
    )
    replace_once(
        proxy_list,
        """private struct ProxySettingsControllerState: Equatable {
    var editing: Bool = false
    var revealedServer: ProxyServerSettings? = nil
}
""",
        """private struct ProxySettingsControllerState: Equatable {
    var editing: Bool = false
    var revealedServer: ProxyServerSettings? = nil
    var checkingAllProxies: Bool = false
}
""",
        "Track the manual proxy batch check state",
    )
    replace_once(
        proxy_list,
        """    var pushControllerImpl: ((ViewController) -> Void)?
    var dismissImpl: (() -> Void)?
""",
        """    var pushControllerImpl: ((ViewController) -> Void)?
    var presentControllerImpl: ((ViewController) -> Void)?
    var dismissImpl: (() -> Void)?
""",
        "Proxy settings presentation callback",
    )
    replace_once(
        proxy_list,
        "    var shareProxyListImpl: (() -> Void)?\n    \n    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in\n",
        """    var shareProxyListImpl: (() -> Void)?
    let nagramiXSettingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let updateNagramiXSettings: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        nagramiXSettingsPromise.set(NagramiXTabSettings.current)
    }
    var selectDnsImpl: (() -> Void)?
    var editCustomDohImpl: (() -> Void)?
    var selectTimeoutImpl: (() -> Void)?
    var checkAllProxiesImpl: (() -> Void)?
    let checkAllProxiesSettingsDisposable = MetaDisposable()
    let checkAllProxiesStatusesDisposable = MetaDisposable()

    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in
""",
        "Proxy settings persistent NagramiX state",
    )
    replace_unique(
        proxy_list,
        """    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in
        let _ = updateProxySettingsInteractively""",
        """    let arguments = ProxySettingsControllerArguments(toggleEnabled: { value in
        if value {
            updateNagramiXSettings { $0.proxyAutoSwitchEnabled = true }
        }
        let _ = updateProxySettingsInteractively""",
        "Enable automatic switching when Use Proxy is turned on",
    )
    replace_unique(
        proxy_list,
        """            current.enabled = value
            return current""",
        """            current.enabled = value
            if value && current.activeServer == nil {
                current.activeServer = current.servers.first
            }
            return current""",
        "Select a saved proxy when enabling without an active server",
    )
    replace_unique(
        proxy_list,
        """            if current.activeServer != server {
                if let _ = current.servers.firstIndex(of: server) {
                    current.activeServer = server
                    current.enabled = true
                }
            }""",
        """            if current.servers.contains(server) {
                current.activeServer = server
                current.enabled = true
            }""",
        "A tap also enables an already selected disabled proxy",
    )
    replace_unique(
        proxy_list,
        """    }, activateServer: { server in
        let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
            var current = current
            if current.servers.contains(server) {
                current.activeServer = server
                current.enabled = true
            }
            return current
        }).start()
    }, editServer: { server in""",
        """    }, activateServer: { server in
        NotificationCenter.default.post(name: Notification.Name("NagramiXProxySelectionRequested"), object: nil)
        let _ = (accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
        |> take(1)
        |> deliverOnMainQueue).start(next: { data in
            let settings = data.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings
            guard settings.servers.contains(server) else { return }
            updateNagramiXSettings { $0.proxyAutoSwitchEnabled = true }
            let _ = updateProxySettingsInteractively(accountManager: accountManager, { current in
                var current = current
                if current.servers.contains(server) {
                    current.activeServer = server
                    current.enabled = true
                }
                return current
            }).start()
        })
    }, editServer: { server in""",
        "Enable automatic switching when a row tap enables proxy use",
    )
    replace_unique(
        proxy_list,
        "    let statusesContext = ProxyServersStatuses(network: network, servers: proxySettings.get()",
        "    let statusesContext = network.nagramiXProxyStatuses.with { $0 } ?? ProxyServersStatuses(network: network, servers: proxySettings.get()",
        "Reuse account health results for the existing Check All button",
    )

    replace_once(
        proxy_list,
        """        }).start()
    }, addNewServer: {
""",
        """        }).start()
    }, selectDns: {
        selectDnsImpl?()
    }, editCustomDoh: {
        editCustomDohImpl?()
    }, toggleAutoSwitch: { value in
        updateNagramiXSettings { $0.proxyAutoSwitchEnabled = value }
    }, selectAutoSwitchTimeout: {
        selectTimeoutImpl?()
    }, checkAllProxies: {
        checkAllProxiesImpl?()
    }, addNewServer: {
""",
        "Proxy settings DNS and Auto-Switch actions",
    )
    replace_once(
        proxy_list,
        """    let proxySettings = Promise<ProxySettings>()
""",
        """    editCustomDohImpl = {
        guard let context else {
            return
        }
        let current = NagramiXTabSettings.current
        presentControllerImpl?(nagramiXCustomDohController(context: context, initialValue: current.customDohUrl, apply: { value in
            updateNagramiXSettings {
                $0.customDohUrl = value
                $0.dnsProvider = .customDoh
            }
        }, clear: {
            updateNagramiXSettings {
                $0.customDohUrl = ""
                $0.dnsProvider = .system
            }
        }))
    }
    selectDnsImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let actionSheet = ActionSheetController(presentationData: presentationData)
        let current = NagramiXTabSettings.current
        let providers: [NagramiXDnsProvider] = [.system, .google, .quad9, .adGuard, .mullvad, .cloudflare, .customDoh]
        let items: [ActionSheetItem] = providers.map { provider in
            ActionSheetButtonItem(title: (current.dnsProvider == provider ? "✓ " : "") + nagramiXDnsTitle(provider, strings: presentationData.strings), color: .accent, action: { [weak actionSheet] in
                actionSheet?.dismissAnimated()
                if provider == .customDoh && current.customDohUrl.isEmpty {
                    editCustomDohImpl?()
                } else {
                    updateNagramiXSettings { $0.dnsProvider = provider }
                }
            })
        }
        var providerItems: [ActionSheetItem] = [ActionSheetTextItem(title: presentationData.strings.nagramiXDns)]
        providerItems.append(contentsOf: items)
        actionSheet.setItemGroups([
            ActionSheetItemGroup(items: providerItems),
            ActionSheetItemGroup(items: [ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in actionSheet?.dismissAnimated() })])
        ])
        presentControllerImpl?(actionSheet)
    }
    selectTimeoutImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let actionSheet = ActionSheetController(presentationData: presentationData)
        let currentTimeout = NagramiXTabSettings.current.proxyAutoSwitchTimeout
        let values = [15, 30, 60]
        let items: [ActionSheetItem] = values.map { value in
            ActionSheetButtonItem(title: (currentTimeout == value ? "✓ " : "") + nagramiXTimeoutTitle(value, strings: presentationData.strings), color: .accent, action: { [weak actionSheet] in
                actionSheet?.dismissAnimated()
                updateNagramiXSettings { $0.proxyAutoSwitchTimeout = value }
            })
        }
        var timeoutItems: [ActionSheetItem] = [ActionSheetTextItem(title: presentationData.strings.nagramiXProxySwitchAfter)]
        timeoutItems.append(contentsOf: items)
        actionSheet.setItemGroups([
            ActionSheetItemGroup(items: timeoutItems),
            ActionSheetItemGroup(items: [ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in actionSheet?.dismissAnimated() })])
        ])
        presentControllerImpl?(actionSheet)
    }

    let proxySettings = Promise<ProxySettings>()
""",
        "Native DNS and Auto-Switch selectors plus Custom DoH editor",
    )
    replace_once(
        proxy_list,
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
""",
        """    checkAllProxiesImpl = {
        if stateValue.with({ $0.checkingAllProxies }) {
            return
        }
        checkAllProxiesSettingsDisposable.set((proxySettings.get()
        |> take(1)
        |> deliverOnMainQueue).start(next: { settings in
            var uniqueServers: [ProxyServerSettings] = []
            var seenServers = Set<ProxyServerSettings>()
            for server in settings.servers where seenServers.insert(server).inserted {
                uniqueServers.append(server)
            }
            guard !uniqueServers.isEmpty else {
                let presentationData = sharedContext.currentPresentationData.with { $0 }
                presentControllerImpl?(UndoOverlayController(presentationData: presentationData, content: .info(title: nil, text: presentationData.strings.nagramiXProxyNoneToCheck, timeout: nil, customUndoText: nil), elevatedLayout: false, action: { _ in return false }))
                return
            }
            updateState { state in
                var state = state
                state.checkingAllProxies = true
                return state
            }
            Logger.shared.log("NagramiX", "Proxy batch check started: count=\\(uniqueServers.count)")
            let targetServers = Set(uniqueServers)
            var observedCheckingState = false
            checkAllProxiesStatusesDisposable.set((combineLatest(statusesContext.statuses(), proxySettings.get())
            |> deliverOnMainQueue).start(next: { [weak checkAllProxiesStatusesDisposable] statuses, currentSettings in
                let currentServers = targetServers.intersection(Set(currentSettings.servers))
                var resultStatuses: [ProxyServerStatus] = []
                resultStatuses.reserveCapacity(currentServers.count)
                for server in currentServers {
                    guard let status = statuses[server] else {
                        return
                    }
                    resultStatuses.append(status)
                }
                if resultStatuses.contains(where: { status in
                    if case .checking = status {
                        return true
                    }
                    return false
                }) {
                    observedCheckingState = true
                    return
                }
                if currentServers.isEmpty {
                    observedCheckingState = true
                }
                guard observedCheckingState else {
                    return
                }
                var availableCount = 0
                for status in resultStatuses {
                    if case .available = status {
                        availableCount += 1
                    }
                }
                let totalCount = resultStatuses.count
                let unavailableCount = totalCount - availableCount
                checkAllProxiesStatusesDisposable?.set(nil)
                updateState { state in
                    var state = state
                    state.checkingAllProxies = false
                    return state
                }
                Logger.shared.log("NagramiX", "Proxy batch check completed: available=\\(availableCount) unavailable=\\(unavailableCount)")
                let presentationData = sharedContext.currentPresentationData.with { $0 }
                let text = presentationData.strings.nagramiXProxyCheckSummary(total: totalCount, available: availableCount, unavailable: unavailableCount)
                presentControllerImpl?(UndoOverlayController(presentationData: presentationData, content: .succeed(text: text, timeout: nil, customUndoText: nil), elevatedLayout: false, action: { _ in return false }))
            }))
            statusesContext.recheckAll(servers: uniqueServers)
        }))
    }

    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
""",
        "Run all saved proxies through Telegram's native checker",
    )
    replace_once(
        proxy_list,
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus)
    |> map { presentationData, state, proxySettings, statuses, connectionStatus -> (ItemListControllerState, (ItemListNodeState, Any)) in
""",
        """    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus, nagramiXSettingsPromise.get())
    |> map { presentationData, state, proxySettings, statuses, connectionStatus, nagramiXSettings -> (ItemListControllerState, (ItemListNodeState, Any)) in
""",
        "Observe NagramiX networking settings in Proxy screen",
    )
    replace_once(
        proxy_list,
        "entries: proxySettingsControllerEntries(theme: presentationData.theme, strings: presentationData.strings, state: state, proxySettings: proxySettings, statuses: statuses, connectionStatus: connectionStatus)",
        "entries: proxySettingsControllerEntries(theme: presentationData.theme, strings: presentationData.strings, state: state, proxySettings: proxySettings, nagramiXSettings: nagramiXSettings, statuses: statuses, connectionStatus: connectionStatus)",
        "Render NagramiX networking settings",
    )
    replace_once(
        proxy_list,
        """    pushControllerImpl = { [weak controller] c in
        (controller?.navigationController as? NavigationController)?.pushViewController(c)
    }
""",
        """    pushControllerImpl = { [weak controller] c in
        (controller?.navigationController as? NavigationController)?.pushViewController(c)
    }
    presentControllerImpl = { [weak controller] c in
        controller?.present(c, in: .window(.root))
    }
""",
        "Present Proxy selectors and Custom DoH editor",
    )

    proxy_action_item = source / "submodules" / "SettingsUI" / "Sources" / "Data and Storage" / "ProxySettingsActionItem.swift"
    replace_once(
        proxy_action_item,
        "import PresentationDataUtils\n",
        "import PresentationDataUtils\nimport AppBundle\n",
        "Proxy batch action refresh icon dependency",
    )
    replace_once(
        proxy_action_item,
        """enum ProxySettingsActionIcon {
    case none
    case add
}
""",
        """enum ProxySettingsActionIcon {
    case none
    case add
    case refresh
}
""",
        "Add the proxy batch refresh action icon",
    )
    replace_once(
        proxy_action_item,
        """            let icon = item.icon == .add ? PresentationResourcesItemList.plusIconImage(item.presentationData.theme) : nil
""",
        """            let icon: UIImage?
            switch item.icon {
            case .none:
                icon = nil
            case .add:
                icon = PresentationResourcesItemList.plusIconImage(item.presentationData.theme)
            case .refresh:
                icon = generateTintedImage(image: UIImage(bundleImageName: "Settings/Refresh"), color: item.presentationData.theme.list.itemAccentColor)
            }
""",
        "Render the themed proxy batch refresh icon",
    )

    telegram_ui_build = source / "submodules" / "TelegramUI" / "BUILD"
    replace_once(
        telegram_ui_build,
        '        "//submodules/SettingsUI:SettingsUI",\n',
        '        "//submodules/SettingsUI:SettingsUI",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TelegramUI NagramiXCore dependency",
    )

    chat_bubble_build = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageBubbleItemNode" / "BUILD"
    replace_once(
        chat_bubble_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "Chat message bubble NagramiX settings dependency",
    )
    chat_bubble_source = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageBubbleItemNode" / "Sources" / "ChatMessageBubbleItemNode.swift"
    replace_once(
        chat_bubble_source,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Chat message bubble NagramiX settings import",
    )
    replace_once(
        chat_bubble_source,
        "        let chatLocationPeerId: PeerId = item.chatLocation.peerId ?? item.content.firstMessage.id.peerId\n",
        """        let chatLocationPeerId: PeerId = item.chatLocation.peerId ?? item.content.firstMessage.id.peerId
        let nagramiXArchivedMessage = firstMessage.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
        let nagramiXWideChannelPost: Bool
        if NagramiXTabSettings.current.wideChannelPosts,
           case .peer = item.chatLocation,
           let channel = firstMessage.peers[firstMessage.id.peerId] as? TelegramChannel,
           case .broadcast = channel.info,
           firstMessage.adAttribute == nil,
           !isPreview {
            nagramiXWideChannelPost = true
        } else {
            nagramiXWideChannelPost = false
        }
""",
        "Identify only ordinary main-timeline broadcast posts for wide layout",
    )
    replace_once(
        chat_bubble_source,
        "    private var mosaicStatusNode: ChatMessageDateAndStatusNode?\n",
        """    private var mosaicStatusNode: ChatMessageDateAndStatusNode?
    private var nagramiXDeletedStatusNode: ImmediateTextNode?
    private var nagramiXDeletedStatusIconNode: ASImageNode?
    private var nagramiXOriginalClippingGroupOpacity: Bool?
""",
        "Deleted-message status node state",
    )
    replace_once(
        chat_bubble_source,
        "        /*if isInlinePage {\n            needsShareButton = false\n        }*/\n                        \n        var tmpWidth: CGFloat\n",
        """        /*if isInlinePage {
            needsShareButton = false
        }*/

        if nagramiXWideChannelPost {
            needsShareButton = false
            needsSummarizeButton = false
            allowFullWidth = true
        }

        var tmpWidth: CGFloat
""",
        "Use the floating-control gutter for optional wide channel posts",
    )
    replace_once(
        chat_bubble_source,
        "        maximumContentWidth = max(0.0, maximumContentWidth)\n        \n        var contentPropertiesAndPrepareLayouts:",
        """        if nagramiXWideChannelPost {
            // Content-type branches above retain Telegram's special sizing in
            // every other chat. A broadcast post deliberately receives the
            // common adaptive width so forwarded content, polls, media,
            // instant video and grouped content all start from one geometry.
            maximumContentWidth = floor(tmpWidth - layoutConstants.bubble.edgeInset * 3.0 - layoutConstants.bubble.contentInsets.left - layoutConstants.bubble.contentInsets.right - avatarInset)
        }
        maximumContentWidth = max(0.0, maximumContentWidth)

        var contentPropertiesAndPrepareLayouts:""",
        "Give every ordinary broadcast-post content node the shared adaptive width",
    )
    replace_once(
        chat_bubble_source,
        "            index += 1\n        }\n        \n        let topNodeMergeStatus:",
        """            index += 1
        }

        if nagramiXWideChannelPost {
            // Each content node reports its preferred maximum width during the
            // preparation pass. Telegram normally intersects those values, so
            // an intrinsically narrow photo can reduce the shared constraint
            // for the following caption, forward/reply headers and footers.
            // Wide channel posts instead keep the adaptive parent-derived
            // constraint for the common finalization pass. Individual nodes
            // still own aspect fitting/cropping and height calculation.
            maximumNodeWidth = maximumContentWidth
        }

        let topNodeMergeStatus:""",
        "Keep the adaptive width through every broadcast-post content layout",
    )
    replace_once(
        chat_bubble_source,
        """        if let mosaicRange = mosaicRange {
            let maxSize = layoutConstants.image.maxDimensions.fittedToWidthOrSmaller(maximumContentWidth - layoutConstants.image.bubbleInsets.left - layoutConstants.image.bubbleInsets.right)
            let (innerFramesAndPositions, innerSize) = chatMessageBubbleMosaicLayout(maxSize: maxSize, itemSizes: contentPropertiesAndLayouts[mosaicRange].map { item in
""",
        """        if let mosaicRange = mosaicRange {
            let availableMosaicWidth = max(0.0, maximumContentWidth - layoutConstants.image.bubbleInsets.left - layoutConstants.image.bubbleInsets.right)
            let maxSize: CGSize
            if nagramiXWideChannelPost {
                // Albums must receive the same adaptive width as the rest of
                // the post. Keep Telegram's own mosaic algorithm and aspect
                // handling; only replace its stock narrow width input.
                maxSize = CGSize(width: availableMosaicWidth, height: max(availableMosaicWidth, layoutConstants.image.maxDimensions.height))
            } else {
                maxSize = layoutConstants.image.maxDimensions.fittedToWidthOrSmaller(availableMosaicWidth)
            }
            let (innerFramesAndPositions, innerSize) = chatMessageBubbleMosaicLayout(maxSize: maxSize, itemSizes: contentPropertiesAndLayouts[mosaicRange].map { item in
""",
        "Give Telegram grouped-media layout the adaptive broadcast-post width",
    )
    replace_once(
        chat_bubble_source,
        "        var contentSize = CGSize(width: maxContentWidth, height: 0.0)\n",
        """        if nagramiXWideChannelPost {
            // Keep the bubble, content containers, reactions and footer on the
            // same width that was supplied to the content finalization pass.
            maxContentWidth = max(maxContentWidth, maximumNodeWidth)
        }
        var nagramiXDeletedStatusHeight: CGFloat = 0.0
        if nagramiXArchivedMessage {
            let configuredLabel = NagramiXTabSettings.current.deletedMessageLabel
            let label = configuredLabel.isEmpty ? item.presentationData.strings.nagramiXDeleted : configuredLabel
            let labelColor = incoming ? item.presentationData.theme.theme.chat.message.incoming.secondaryTextColor : item.presentationData.theme.theme.chat.message.outgoing.secondaryTextColor
            let labelString = NSAttributedString(string: label, font: Font.semibold(12.0), textColor: labelColor)
            let iconAndSpacingWidth: CGFloat = 17.0
            let horizontalInsets: CGFloat = 16.0
            let singleLineWidth = ceil(labelString.size().width) + iconAndSpacingWidth + horizontalInsets
            // Grow short bubbles for the status up to Telegram's ordinary
            // available width; labels that still do not fit wrap below content.
            maxContentWidth = max(maxContentWidth, min(maximumContentWidth, singleLineWidth))
            let availableLabelWidth = max(1.0, maxContentWidth - horizontalInsets - iconAndSpacingWidth)
            let labelBounds = labelString.boundingRect(
                with: CGSize(width: availableLabelWidth, height: CGFloat.greatestFiniteMagnitude),
                options: [.usesLineFragmentOrigin, .usesFontLeading],
                context: nil
            )
            nagramiXDeletedStatusHeight = max(16.0, ceil(labelBounds.height) + 2.0)
        }
        var contentSize = CGSize(width: maxContentWidth, height: 0.0)
""",
        "Force enabled broadcast post bubbles to the maximum safe width",
    )
    replace_once(
        chat_bubble_source,
        "        contentSize.height += totalContentNodesHeight\n",
        """        contentSize.height += totalContentNodesHeight
        if nagramiXArchivedMessage {
            // Keep the complete marker on its own measured footer row instead
            // of competing with Telegram's date/views/edited metadata.
            contentSize.height += nagramiXDeletedStatusHeight
        }
""",
        "Reserve an archived-message footer row",
    )
    replace_once(
        chat_bubble_source,
        """                let (size, apply) = finalize(maxContentWidth)
                let containerFrame = CGRect(origin: CGPoint(x: 0.0, y: contentNodeOriginY), size: size)
                contentNodeFramesPropertiesAndApply.append((containerFrame, properties, contentGroupId == nil, apply))
""",
        """                let (intrinsicSize, apply) = finalize(maxContentWidth)
                let size: CGSize
                if nagramiXWideChannelPost {
                    // Some content nodes intentionally return their intrinsic
                    // width even after being finalized with a wider constraint.
                    // Give every linear node the same wide frame so media,
                    // text/caption, previews, files, polls and footers cannot
                    // leave an unused strip inside the expanded background.
                    size = CGSize(width: max(maxContentWidth, intrinsicSize.width), height: intrinsicSize.height)
                } else {
                    size = intrinsicSize
                }
                let containerFrame = CGRect(origin: CGPoint(x: 0.0, y: contentNodeOriginY), size: size)
                contentNodeFramesPropertiesAndApply.append((containerFrame, properties, contentGroupId == nil, apply))
""",
        "Give every finalized broadcast-post content node the shared wide frame",
    )

    chat_controller_node = source / "submodules" / "TelegramUI" / "Sources" / "ChatControllerNode.swift"
    replace_once(
        chat_controller_node,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Chat controller NagramiX settings import",
    )
    replace_once(
        chat_controller_node,
        "    private var openStickersDisposable: Disposable?\n    private var displayVideoUnmuteTipDisposable: Disposable?\n    \n    private var onLayoutCompletions:",
        """    private var openStickersDisposable: Disposable?
    private var displayVideoUnmuteTipDisposable: Disposable?
    private var nagramiXSettingsObserver: NSObjectProtocol?
    private var nagramiXDeletedLabelObserver: NSObjectProtocol?

    private var onLayoutCompletions:""",
        "Chat controller NagramiX settings observer state",
    )
    replace_once(
        chat_controller_node,
        """        super.init()

        getContentAreaInScreenSpaceImpl = { [weak self] in""",
        """        super.init()

        let nagramiXRefreshVisibleMessages: () -> Void = { [weak self] in
            guard let self else {
                return
            }
            var messageIds = Set<MessageId>()
            self.historyNode.forEachVisibleItemNode { itemNode in
                guard let itemNode = itemNode as? ChatMessageItemView, let item = itemNode.item else {
                    return
                }
                switch item.content {
                case let .message(message, _, _, _, _):
                    messageIds.insert(message.id)
                case let .group(messages):
                    for message in messages {
                        messageIds.insert(message.0.id)
                    }
                }
            }
            for messageId in messageIds {
                self.historyNode.requestMessageUpdate(messageId)
            }
        }
        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.wideChannelPostsChangedNotification, object: nil, queue: .main, using: { _ in
            nagramiXRefreshVisibleMessages()
        })
        self.nagramiXDeletedLabelObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.deletedMessageLabelChangedNotification, object: nil, queue: .main, using: { _ in
            nagramiXRefreshVisibleMessages()
        })

        getContentAreaInScreenSpaceImpl = { [weak self] in""",
        "Refresh visible message layouts after a NagramiX setting changes",
    )
    replace_once(
        chat_controller_node,
        """        self.displayVideoUnmuteTipDisposable?.dispose()
        self.inputMediaNodeDataDisposable?.dispose()
""",
        """        self.displayVideoUnmuteTipDisposable?.dispose()
        if let nagramiXSettingsObserver = self.nagramiXSettingsObserver {
            NotificationCenter.default.removeObserver(nagramiXSettingsObserver)
        }
        if let nagramiXDeletedLabelObserver = self.nagramiXDeletedLabelObserver {
            NotificationCenter.default.removeObserver(nagramiXDeletedLabelObserver)
        }
        self.inputMediaNodeDataDisposable?.dispose()
""",
        "Remove the chat controller NagramiX settings observer",
    )

    replace_once(
        chat_bubble_source,
        "        strongSelf.updateSearchTextHighlightState()\n",
        """        let nagramiXIsArchived = item.content.firstMessage.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
        let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0
        // Reset every reused cell explicitly. Alpha changes presentation only;
        // gesture recognizers and all native interactions remain enabled.
        strongSelf.backgroundNode.alpha = nagramiXContentAlpha
        strongSelf.backgroundWallpaperNode.alpha = nagramiXContentAlpha
        strongSelf.shadowNode.alpha = nagramiXContentAlpha
        strongSelf.clippingNode.alpha = nagramiXContentAlpha
        // Composite the native thumbnail/video/control stack before dimming it.
        // Otherwise each overlapping layer can blend separately at 50% alpha.
        if nagramiXIsArchived {
            if strongSelf.nagramiXOriginalClippingGroupOpacity == nil {
                strongSelf.nagramiXOriginalClippingGroupOpacity = strongSelf.clippingNode.layer.allowsGroupOpacity
            }
            strongSelf.clippingNode.layer.allowsGroupOpacity = true
        } else if let original = strongSelf.nagramiXOriginalClippingGroupOpacity {
            strongSelf.clippingNode.layer.allowsGroupOpacity = original
            strongSelf.nagramiXOriginalClippingGroupOpacity = nil
        }
        strongSelf.backgroundHighlightNode?.alpha = nagramiXContentAlpha
        strongSelf.actionButtonsNode?.alpha = nagramiXContentAlpha
        strongSelf.reactionButtonsNode?.alpha = nagramiXContentAlpha

        if nagramiXIsArchived {
            let statusNode: ImmediateTextNode
            if let current = strongSelf.nagramiXDeletedStatusNode {
                statusNode = current
            } else {
                statusNode = ImmediateTextNode()
                statusNode.maximumNumberOfLines = 0
                statusNode.isUserInteractionEnabled = false
                strongSelf.nagramiXDeletedStatusNode = statusNode
                strongSelf.mainContextSourceNode.contentNode.addSubnode(statusNode)
            }

            let messageTheme = incoming ? item.presentationData.theme.theme.chat.message.incoming : item.presentationData.theme.theme.chat.message.outgoing
            let configuredLabel = NagramiXTabSettings.current.deletedMessageLabel
            let label = configuredLabel.isEmpty ? item.presentationData.strings.nagramiXDeleted : configuredLabel
            let iconNode: ASImageNode
            if let current = strongSelf.nagramiXDeletedStatusIconNode {
                iconNode = current
            } else {
                iconNode = ASImageNode()
                iconNode.isUserInteractionEnabled = false
                strongSelf.nagramiXDeletedStatusIconNode = iconNode
                strongSelf.mainContextSourceNode.contentNode.addSubnode(iconNode)
            }
            iconNode.image = generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Delete"), color: messageTheme.secondaryTextColor)
            statusNode.attributedText = NSAttributedString(string: label, font: Font.semibold(12.0), textColor: messageTheme.secondaryTextColor)
            let statusSize = statusNode.updateLayout(CGSize(width: max(1.0, backgroundFrame.width - 33.0), height: CGFloat.greatestFiniteMagnitude))
            statusNode.frame = CGRect(
                x: max(backgroundFrame.minX + 25.0, backgroundFrame.maxX - 8.0 - statusSize.width),
                y: backgroundFrame.maxY - statusSize.height - 4.0,
                width: statusSize.width,
                height: statusSize.height
            )
            iconNode.frame = CGRect(x: statusNode.frame.minX - 17.0, y: statusNode.frame.minY + 1.0, width: 13.0, height: 13.0)
        } else {
            strongSelf.nagramiXDeletedStatusNode?.removeFromSupernode()
            strongSelf.nagramiXDeletedStatusNode = nil
            strongSelf.nagramiXDeletedStatusIconNode?.removeFromSupernode()
            strongSelf.nagramiXDeletedStatusIconNode = nil
        }

        strongSelf.updateSearchTextHighlightState()
""",
        "Apply archived-message dimming and an undimmed footer marker",
    )

    tab_bar_build = source / "submodules" / "TabBarUI" / "BUILD"
    replace_once(
        tab_bar_build,
        '        "//submodules/Display",\n',
        '        "//submodules/Display",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "TabBarUI NagramiXCore dependency",
    )

    chat_list_build = source / "submodules" / "ChatListUI" / "BUILD"
    replace_once(
        chat_list_build,
        '        "//submodules/AccountContext:AccountContext",\n',
        '        "//submodules/AccountContext:AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "ChatListUI NagramiXCore dependency",
    )

    video_message_build = source / "submodules" / "TelegramUI" / "Components" / "VideoMessageCameraScreen" / "BUILD"
    replace_once(
        video_message_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "VideoMessageCameraScreen NagramiXCore dependency",
    )

    story_container_build = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "BUILD"
    replace_once(
        story_container_build,
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/NagramiXCore:NagramiXCore",\n        "//submodules/PhotoResources",\n',
        "StoryContainerScreen NagramiXCore dependency",
    )

    debug_settings_build = source / "submodules" / "DebugSettingsUI" / "BUILD"
    replace_once(
        debug_settings_build,
        '        "//submodules/Display:Display",\n',
        '        "//submodules/Display:Display",\n        "//submodules/NagramiXCore:NagramiXCore",\n',
        "DebugSettingsUI NagramiXCore dependency",
    )
    for debug_source_name in ["DebugController.swift", "DebugAccountsController.swift"]:
        debug_source = source / "submodules" / "DebugSettingsUI" / "Sources" / debug_source_name
        replace_once(
            debug_source,
            "import TelegramPresentationData\n",
            "import TelegramPresentationData\nimport NagramiXCore\n",
            f"{debug_source_name} NagramiXCore import",
        )
        localize_debug_titles(debug_source)

    story_content = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryContent.swift"
    replace_once(
        story_content,
        """    public let itemPeer: EnginePeer?

    public init(
""",
        """    public let itemPeer: EnginePeer?
    public let isSeen: Bool

    public init(
""",
        "Story items carry their server read state",
    )
    replace_once(
        story_content,
        """        entityFiles: [EngineMedia.Id: TelegramMediaFile],
        itemPeer: EnginePeer?
    ) {
""",
        """        entityFiles: [EngineMedia.Id: TelegramMediaFile],
        itemPeer: EnginePeer?,
        isSeen: Bool = false
    ) {
""",
        "Add backward-compatible story read-state parameter",
    )
    replace_once(
        story_content,
        """        self.itemPeer = itemPeer
    }
""",
        """        self.itemPeer = itemPeer
        self.isSeen = isSeen
    }
""",
        "Store story read state",
    )
    replace_once(
        story_content,
        """        if lhs.itemPeer != rhs.itemPeer {
            return false
        }
        return true
""",
        """        if lhs.itemPeer != rhs.itemPeer {
            return false
        }
        if lhs.isSeen != rhs.isSeen {
            return false
        }
        return true
""",
        "Compare story read state",
    )

    story_chat_content = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryChatContent.swift"
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            )
                        }
""" + "                        \n" + """                        self.nextItems = nextItems
""",
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: item.id <= (state?.maxReadId ?? 0)
                            )
                        }
""" + "                        \n" + """                        self.nextItems = nextItems
""",
        "Carry read state for peer story feed items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            ),
                            totalCount: totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: mappedItem.id <= (state?.maxReadId ?? 0)
                            ),
                            totalCount: totalCount,
""",
        "Carry read state for focused peer story",
    )
    replace_once(
        story_chat_content,
        """        self.storyDisposable = (combineLatest(queue: .mainQueue(),
            listContext.state,
            self.focusedIdUpdated.get(),
            preferHighQualityStories
        )
        |> deliverOnMainQueue).startStrict(next: { [weak self] state, _, preferHighQualityStories in
            guard let self else {
                return
            }
""",
        """        let listStateWithReadIds: Signal<(StoryListContext.State, [PeerId: Int32]), NoError> = listContext.state
        |> mapToSignal { state in
            return context.account.postbox.transaction { transaction -> (StoryListContext.State, [PeerId: Int32]) in
                var maxReadIds: [PeerId: Int32] = [:]
                for item in state.items {
                    if maxReadIds[item.id.peerId] == nil {
                        maxReadIds[item.id.peerId] = transaction.getPeerStoryState(peerId: item.id.peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    }
                }
                return (state, maxReadIds)
            }
        }

        self.storyDisposable = (combineLatest(queue: .mainQueue(),
            listStateWithReadIds,
            self.focusedIdUpdated.get(),
            preferHighQualityStories
        )
        |> deliverOnMainQueue).startStrict(next: { [weak self] stateAndMaxReadIds, _, preferHighQualityStories in
            guard let self else {
                return
            }
            let state = stateAndMaxReadIds.0
            let maxReadIds = stateAndMaxReadIds.1
""",
        "Load per-peer read state for story-list items",
    )
    replace_once(
        story_chat_content,
        """                            entityFiles: extractItemEntityFiles(item: stateItem.storyItem, allEntityFiles: state.allEntityFiles),
                            itemPeer: stateItem.peer
                        ))
""",
        """                            entityFiles: extractItemEntityFiles(item: stateItem.storyItem, allEntityFiles: state.allEntityFiles),
                            itemPeer: stateItem.peer,
                            isSeen: stateItem.id.id <= (maxReadIds[stateItem.id.peerId] ?? 0)
                        ))
""",
        "Carry read state for story-list items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item.storyItem, allEntityFiles: state.allEntityFiles),
                                itemPeer: item.peer
                            ),
                            totalCount: state.totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: item.storyItem, allEntityFiles: state.allEntityFiles),
                                itemPeer: item.peer,
                                isSeen: item.id.id <= (maxReadIds[item.id.peerId] ?? 0)
                            ),
                            totalCount: state.totalCount,
""",
        "Carry read state for focused story-list item",
    )
    replace_once(
        story_chat_content,
        """            item |> mapToSignal { item -> Signal<(Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?]), NoError> in
                return context.account.postbox.transaction { transaction -> (Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?]) in
                    guard let item else {
                        return (nil, [:], [:], [:])
                    }
""",
        """            item |> mapToSignal { item -> Signal<(Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Int32), NoError> in
                return context.account.postbox.transaction { transaction -> (Stories.StoredItem?, [PeerId: Peer], [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Int32) in
                    let maxReadId = transaction.getPeerStoryState(peerId: storyId.peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    guard let item else {
                        return (nil, [:], [:], [:], maxReadId)
                    }
""",
        "Load read state for a single deep-linked story",
    )
    replace_once(
        story_chat_content,
        """                    return (item, peers, allEntityFiles, stories)
                }
            },
""",
        """                    return (item, peers, allEntityFiles, stories, maxReadId)
                }
            },
""",
        "Return read state for a single deep-linked story",
    )
    replace_once(
        story_chat_content,
        """            let (item, peers, allEntityFiles, forwardInfoStories) = itemAndPeers
""",
        """            let (item, peers, allEntityFiles, forwardInfoStories, maxReadId) = itemAndPeers
""",
        "Unpack single-story read state",
    )
    replace_once(
        story_chat_content,
        """                    entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                    itemPeer: nil
                )
                let stateValue = StoryContentContextState(
""",
        """                    entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                    itemPeer: nil,
                    isSeen: mappedItem.id <= maxReadId
                )
                let stateValue = StoryContentContextState(
""",
        "Do not reconfirm an already-viewed deep-linked story",
    )
    replace_once(
        story_chat_content,
        """            |> mapToSignal { _, views, data, preferHighQualityStories -> Signal<(CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool), NoError> in
""",
        """            |> mapToSignal { _, views, data, preferHighQualityStories -> Signal<(CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool, Int32), NoError> in
""",
        "Expose repost-chain read state in the signal type",
    )
    replace_once(
        story_chat_content,
        """                return context.account.postbox.transaction { transaction -> (CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool) in
""",
        """                return context.account.postbox.transaction { transaction -> (CombinedView, [PeerId: Peer], (EngineGlobalNotificationSettings, Bool), [MediaId: TelegramMediaFile], [StoryId: EngineStoryItem?], Bool, Int32) in
""",
        "Load read state for repost-chain stories",
    )
    replace_once(
        story_chat_content,
        """                    return (views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories)
                }
            }
            |> deliverOnMainQueue).startStrict(next: { [weak self] views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories in
""",
        """                    let maxReadId = transaction.getPeerStoryState(peerId: peerId)?.entry.get(Stories.PeerState.self)?.maxReadId ?? 0
                    return (views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories, maxReadId)
                }
            }
            |> deliverOnMainQueue).startStrict(next: { [weak self] views, peers, data, allEntityFiles, forwardInfoStories, preferHighQualityStories, maxReadId in
""",
        "Return repost-chain story read state",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            )
                        }
""",
        """                                entityFiles: extractItemEntityFiles(item: item, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: item.id <= maxReadId
                            )
                        }
""",
        "Carry read state for repost-chain items",
    )
    replace_once(
        story_chat_content,
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil
                            ),
                            totalCount: totalCount,
""",
        """                                entityFiles: extractItemEntityFiles(item: mappedItem, allEntityFiles: allEntityFiles),
                                itemPeer: nil,
                                isSeen: mappedItem.id <= maxReadId
                            ),
                            totalCount: totalCount,
""",
        "Carry read state for the focused repost-chain story",
    )

    settings_items = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoSettingsItems.swift"
    replace_once(
        settings_items,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "NagramiX settings localization import",
    )
    replace_once(
        settings_items,
        "    case myProfile\n    case proxy\n",
        "    case nagramix\n    case myProfile\n    case proxy\n",
        "NagramiX settings group order",
    )
    replace_once(
        settings_items,
        """        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
""" + "        \n" + """        if !settings.proxySettings.servers.isEmpty {
""",
        """        items[.nagramix]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.nagramiXSettingsTitle, icon: PresentationResourcesSettings.nagramiXSettings, action: {
            interaction.openSettings(.nagramix)
        }))

        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
""" + "        \n" + """        if !settings.proxySettings.servers.isEmpty {
""",
        "NagramiX settings row",
    )
    replace_once(
        settings_items,
        """    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_Support, icon: PresentationResourcesSettings.support, action: {
        interaction.openSettings(.support)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 1, text: presentationData.strings.Settings_FAQ, icon: PresentationResourcesSettings.faq, action: {
        interaction.openSettings(.faq)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 2, text: presentationData.strings.Settings_Tips, icon: PresentationResourcesSettings.tips, action: {
        interaction.openSettings(.tips)
    }))
""",
        """    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.nagramiXFeatures, icon: PresentationResourcesSettings.nagramiXFeatures, action: {
        interaction.openSettings(.nagramiXFeatures)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 1, text: presentationData.strings.nagramiXUpdates, icon: PresentationResourcesSettings.nagramiXUpdates, action: {
        interaction.openSettings(.nagramiXUpdates)
    }))
    items[.support]!.append(PeerInfoScreenDisclosureItem(id: 2, text: presentationData.strings.nagramiXHelp, icon: PresentationResourcesSettings.messages, action: {
        interaction.openSettings(.nagramiXHelp)
    }))
""",
        "Replace Telegram support rows with the NagramiX information block",
    )

    peer_info_screen = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreen.swift"
    replace_once(
        peer_info_screen,
        "    case profile\n    case premiumManagement\n",
        "    case profile\n    case nagramix\n    case premiumManagement\n",
        "NagramiX settings route",
    )
    replace_once(
        peer_info_screen,
        "    case support\n    case faq\n    case tips\n",
        "    case support\n    case faq\n    case tips\n    case nagramiXFeatures\n    case nagramiXUpdates\n    case nagramiXHelp\n",
        "NagramiX information routes",
    )

    settings_actions = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreenSettingsActions.swift"
    replace_once(
        settings_actions,
        """        case .stories:
            push(PeerInfoStoryGridScreen(context: self.context, peerId: self.context.account.peerId, scope: .saved))
""",
        """        case .nagramix:
            push(nagramiXSettingsController(context: self.context))
        case .stories:
            push(PeerInfoStoryGridScreen(context: self.context, peerId: self.context.account.peerId, scope: .saved))
""",
        "NagramiX settings navigation",
    )
    replace_once(
        settings_actions,
        """        case .watch:
            push(watchSettingsController(context: self.context))
        case .support:
""",
        """        case .watch:
            push(watchSettingsController(context: self.context))
        case .nagramiXFeatures:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://NagramiX.ru", forceExternal: true, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .nagramiXUpdates:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://t.me/NagramiX", forceExternal: false, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .nagramiXHelp:
            self.context.sharedContext.openExternalUrl(context: self.context, urlContext: .generic, url: "https://t.me/NagramiX_bot", forceExternal: false, presentationData: self.presentationData, navigationController: self.controller?.navigationController as? NavigationController, dismissInput: {})
        case .support:
""",
        "NagramiX information navigation",
    )

    root_controller = source / "submodules" / "TelegramUI" / "Sources" / "TelegramRootController.swift"
    replace_once(
        root_controller,
        "import SettingsUI\n",
        "import SettingsUI\nimport NagramiXCore\n",
        "Telegram root NagramiXCore import",
    )
    replace_once(
        root_controller,
        """    private var applicationInFocusDisposable: Disposable?
    private var storyUploadEventsDisposable: Disposable?
""",
        """    private var applicationInFocusDisposable: Disposable?
    private var storyUploadEventsDisposable: Disposable?
    private var nagramiXTabSettingsObserver: NSObjectProtocol?
    private var nagramiXTabInterfaceSoftRestartObserver: NSObjectProtocol?
    private var nagramiXOriginalTabTitles: [ObjectIdentifier: String] = [:]
""",
        "Telegram root tab settings state",
    )
    replace_once(
        root_controller,
        """        super.init(mode: .automaticMasterDetail, theme: NavigationControllerTheme(presentationTheme: self.presentationData.theme))
""" + "        \n" + """        self.presentationDataDisposable = (context.sharedContext.presentationData
""",
        """        super.init(mode: .automaticMasterDetail, theme: NavigationControllerTheme(presentationTheme: self.presentationData.theme))

        self.nagramiXTabSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.applyNagramiXTabSettings()
        })
        self.nagramiXTabInterfaceSoftRestartObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.softRestartRequestedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.softRestartNagramiXTabInterface()
        })
""" + "        \n" + """        self.presentationDataDisposable = (context.sharedContext.presentationData
""",
        "Telegram root tab settings observer",
    )
    replace_once(
        root_controller,
        """        self.storyUploadEventsDisposable?.dispose()
    }
""",
        """        self.storyUploadEventsDisposable?.dispose()
        if let nagramiXTabSettingsObserver = self.nagramiXTabSettingsObserver {
            NotificationCenter.default.removeObserver(nagramiXTabSettingsObserver)
        }
        if let nagramiXTabInterfaceSoftRestartObserver = self.nagramiXTabInterfaceSoftRestartObserver {
            NotificationCenter.default.removeObserver(nagramiXTabInterfaceSoftRestartObserver)
        }
    }
""",
        "Telegram root observer cleanup",
    )
    replace_once(
        root_controller,
        """    public func addRootControllers(showCallsTab: Bool) {
""",
        """    private func nagramiXConfiguredControllers() -> [ViewController] {
        let settings = NagramiXTabSettings.current
        var controllers: [ViewController] = []
        if !settings.hideContacts, let contactsController = self.contactsController {
            controllers.append(contactsController)
        }
        if !settings.hideCalls, let callListController = self.callListController {
            controllers.append(callListController)
        }
        if let chatListController = self.chatListController {
            controllers.append(chatListController)
        }
        if let accountSettingsController = self.accountSettingsController {
            controllers.append(accountSettingsController)
        }
        return controllers
    }

    private func applyNagramiXTabSettings() {
        guard let rootTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }
        rootTabController.setControllers(self.nagramiXConfiguredControllers(), selectedIndex: nil)
        rootTabController.updateLayout(transition: .immediate)
    }

    private func softRestartNagramiXTabInterface() {
        guard let previousTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }

        var navigationControllers = self.viewControllers
        guard let rootIndex = navigationControllers.firstIndex(where: { $0 === previousTabController }) else {
            return
        }

        let selectedController: ViewController?
        if previousTabController.selectedIndex >= 0 && previousTabController.selectedIndex < previousTabController.controllers.count {
            selectedController = previousTabController.controllers[previousTabController.selectedIndex]
        } else {
            selectedController = nil
        }

        let tabBarController = TabBarControllerImpl(theme: self.presentationData.theme, strings: self.presentationData.strings)
        tabBarController.navigationPresentation = .master
        self.rootTabController = tabBarController

        let controllers = self.nagramiXConfiguredControllers()
        let selectedIndex = selectedController.flatMap { selectedController in
            controllers.firstIndex(where: { $0 === selectedController })
        } ?? controllers.firstIndex(where: { $0 === self.accountSettingsController }) ?? 0
        previousTabController.setControllers([], selectedIndex: nil)
        tabBarController.setControllers(controllers, selectedIndex: selectedIndex)

        navigationControllers[rootIndex] = tabBarController
        self.setViewControllers(navigationControllers, animated: false)
        tabBarController.updateLayout(transition: .immediate)
    }

    public func addRootControllers(showCallsTab: Bool) {
""",
        "Telegram root tab settings helpers",
    )
    replace_once(
        root_controller,
        """        var controllers: [ViewController] = []
""" + "        \n" + """        let contactsController = ContactsController(context: self.context)
""",
        """        let contactsController = ContactsController(context: self.context)
""",
        "Telegram root temporary controllers array",
    )
    replace_once(root_controller, "        controllers.append(contactsController)\n        \n", "", "Telegram root contacts default append")
    replace_once(
        root_controller,
        """        if showCallsTab {
            controllers.append(callListController)
        }
        controllers.append(chatListController)
""" + "        \n",
        "",
        "Telegram root calls and chats default append",
    )
    replace_once(
        root_controller,
        """        accountSettingsController.parentController = self
        controllers.append(accountSettingsController)
""" + "                \n" + """        tabBarController.setControllers(controllers, selectedIndex: restoreSettignsController != nil ? (controllers.count - 1) : (controllers.count - 2))
""" + "        \n" + """        self.contactsController = contactsController
        self.callListController = callListController
        self.chatListController = chatListController
        self.accountSettingsController = accountSettingsController
        self.rootTabController = tabBarController
""",
        """        accountSettingsController.parentController = self

        self.contactsController = contactsController
        self.callListController = callListController
        self.chatListController = chatListController
        self.accountSettingsController = accountSettingsController
        self.rootTabController = tabBarController

        let controllers = self.nagramiXConfiguredControllers()
        let selectedController: ViewController = restoreSettignsController != nil ? accountSettingsController : chatListController
        let selectedIndex = controllers.firstIndex(where: { $0 === selectedController }) ?? 0
        tabBarController.setControllers(controllers, selectedIndex: selectedIndex)
""",
        "Telegram root initial NagramiX tabs",
    )
    replace_once(
        root_controller,
        """    public func updateRootControllers(showCallsTab: Bool) {
        guard let rootTabController = self.rootTabController as? TabBarControllerImpl else {
            return
        }
        var controllers: [ViewController] = []
        controllers.append(self.contactsController!)
        if showCallsTab {
            controllers.append(self.callListController!)
        }
        controllers.append(self.chatListController!)
        controllers.append(self.accountSettingsController!)
""" + "        \n" + """        rootTabController.setControllers(controllers, selectedIndex: nil)
    }
""",
        """    public func updateRootControllers(showCallsTab: Bool) {
        self.applyNagramiXTabSettings()
    }
""",
        "Telegram root updates",
    )

    tab_bar_node = source / "submodules" / "TabBarUI" / "Sources" / "TabBarContollerNode.swift"
    replace_once(
        tab_bar_node,
        "import GlassControls\n",
        "import GlassControls\nimport NagramiXCore\n",
        "Tab bar NagramiXCore import",
    )
    replace_once(
        tab_bar_node,
        """                search: self.currentController?.tabBarSearchState.flatMap { tabBarSearchState in
                    return TabBarComponent.Search(
""",
        """                search: self.currentController?.tabBarSearchState.flatMap { tabBarSearchState in
                    guard NagramiXTabSettings.current.showSearchButton else {
                        return nil
                    }
                    return TabBarComponent.Search(
""",
        "Tab bar search visibility",
    )

    video_message_camera = source / "submodules" / "TelegramUI" / "Components" / "VideoMessageCameraScreen" / "Sources" / "VideoMessageCameraScreen.swift"
    replace_once(
        video_message_camera,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Video message camera NagramiXCore import",
    )
    replace_once(
        video_message_camera,
        '            let isFrontPosition = "".isEmpty\n',
        """            let prefersRearCamera = NagramiXTabSettings.current.useRearCameraForVideoMessages
            let isFrontPosition = !prefersRearCamera
            Logger.shared.log("NagramiX", "Round video initial camera preference: rear=\\(prefersRearCamera), position=\\(isFrontPosition ? "front" : "back")")
""",
        "Video messages start on the configured camera",
    )

    chat_text_input_panel = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatTextInputPanelNode" / "Sources" / "ChatTextInputPanelNode.swift"
    replace_unique(
        chat_text_input_panel,
        '''                } else {
//                    interfaceInteraction.finishMediaRecording(.dismiss)
                }
                strongSelf.viewOnce = false
''',
        '''                } else {
                    // A released or interrupted gesture must invalidate the
                    // pending video start, including permission callbacks.
                    if case .video = interfaceState.interfaceState.mediaRecordingMode {
                        interfaceInteraction.finishMediaRecording(.dismiss)
                    }
                }
                strongSelf.viewOnce = false
''',
        "Cancel a pending round-video start before its recording state exists",
    )

    legacy_mic_header = source / "submodules" / "LegacyComponents" / "PublicHeaders" / "LegacyComponents" / "TGModernConversationInputMicButton.h"
    replace_unique(
        legacy_mic_header,
        "@property (nonatomic) bool fadeDisabled;\n",
        "@property (nonatomic) bool fadeDisabled;\n@property (nonatomic) bool cancelOnTrackingInterruption;\n",
        "Opt-in cancellation of interrupted round-video gestures",
    )
    legacy_mic_button = source / "submodules" / "LegacyComponents" / "Sources" / "TGModernConversationInputMicButton.m"
    replace_unique(
        legacy_mic_button,
        """- (void)cancelTrackingWithEvent:(UIEvent *)event
{
    if (_processCurrentTouch)
""",
        """- (void)cancelTrackingWithEvent:(UIEvent *)event
{
    if (self.cancelOnTrackingInterruption)
    {
        bool shouldCancel = _processCurrentTouch && !_locked;
        _processCurrentTouch = false;
        _targetTranslation = 0.0f;
        _cancelTargetTranslation = 0.0f;
        [super cancelTrackingWithEvent:event];
        _yFeedbackOccured = false;
        _xFeedbackOccured = false;
        if (shouldCancel)
        {
            id<TGModernConversationInputMicButtonDelegate> delegate = _delegate;
            if ([delegate respondsToSelector:@selector(micButtonInteractionCancelled:)])
                [delegate micButtonInteractionCancelled:CGPointZero];
        }
        return;
    }
    if (_processCurrentTouch)
""",
        "Cancel interrupted video touch without scheduling a hands-free lock",
    )
    recording_button = source / "submodules" / "TelegramUI" / "Components" / "ChatTextInputMediaRecordingButton" / "Sources" / "ChatTextInputMediaRecordingButton.swift"
    replace_unique(
        recording_button,
        """            self.mode = mode

            self.updateAnimation(previousMode: previousMode)
""",
        """            self.mode = mode
            self.cancelOnTrackingInterruption = mode == .video

            self.updateAnimation(previousMode: previousMode)
""",
        "Use interruption cancellation only for round-video recording",
    )

    camera_output = source / "submodules" / "Camera" / "Sources" / "CameraOutput.swift"
    replace_once(
        camera_output,
        """    private var currentPosition: Camera.Position = .front
    private var lastSwitchTimestamp: Double = 0.0
""",
        """    private var currentPosition: Camera.Position = .front
    private var lastSwitchTimestamp: Double = 0.0

    func setInitialPosition(_ position: Camera.Position) {
        self.currentPosition = position
        self.lastSwitchTimestamp = 0.0
    }
""",
        "Allow the native round-video recorder to start from its configured position",
    )

    camera_context = source / "submodules" / "Camera" / "Sources" / "Camera.swift"
    replace_once(
        camera_context,
        """            self.mainDeviceContext?.output.processCodes = { [weak self] codes in
                self?.detectedCodesPipe.putNext(codes)
            }
        }
        self.session.session.startRunning()
""",
        """            self.mainDeviceContext?.output.processCodes = { [weak self] codes in
                self?.detectedCodesPipe.putNext(codes)
            }
        }

        if self.initialConfiguration.isRoundVideo {
            if self.positionValue == .back && self.mainDeviceContext?.device.videoDevice == nil {
                Logger.shared.log("NagramiX", "Round video rear camera unavailable; falling back to front")
                if enabled {
                    if self.additionalDeviceContext?.device.videoDevice != nil {
                        self.positionValue = .front
                        self._positionPromise.set(.front)
                    }
                } else if let mainDeviceContext = self.mainDeviceContext {
                    self.configure {
                        mainDeviceContext.invalidate(switchAudio: false)
                        mainDeviceContext.configure(position: .front, previewView: self.simplePreviewView, audio: self.initialConfiguration.audio, photo: self.initialConfiguration.photo, metadata: self.initialConfiguration.metadata, preferWide: true, preferLowerFramerate: true, switchAudio: false)
                    }
                    if mainDeviceContext.device.videoDevice != nil {
                        self.positionValue = .front
                        self._positionPromise.set(.front)
                    }
                }
            }

            self.mainDeviceContext?.output.setInitialPosition(self.positionValue)
            let activeDeviceContext = self.positionValue == .front && enabled ? self.additionalDeviceContext : self.mainDeviceContext
            if let device = activeDeviceContext?.device.videoDevice {
                Logger.shared.log("NagramiX", "Round video selected camera: id=\\(device.uniqueID), type=\\(device.deviceType.rawValue), position=\\(self.positionValue == .front ? "front" : "back")")
            } else {
                Logger.shared.log("NagramiX", "Round video camera selection failed for position=\\(self.positionValue == .front ? "front" : "back")")
            }
        }
        self.session.session.startRunning()
""",
        "Initialize round-video output from the native camera position",
    )

    chat_list_entries = source / "submodules" / "ChatListUI" / "Sources" / "Node" / "ChatListNodeEntries.swift"
    replace_once(
        chat_list_entries,
        "import AccountContext\n",
        "import AccountContext\nimport NagramiXCore\n",
        "Chat list entries NagramiXCore import",
    )
    replace_once(
        chat_list_entries,
        """                for item in filteredAdditionalItemEntries.reversed() {
                    guard case let .chatList(index) = item.item.index else {
""",
        """                for item in filteredAdditionalItemEntries.reversed() {
                    if case .proxy = item.promoInfo.content, NagramiXTabSettings.current.hideProxySponsorChannel {
                        continue
                    }
                    guard case let .chatList(index) = item.item.index else {
""",
        "Hide only the proxy sponsor entry when requested",
    )

    chat_list_item = source / "submodules/ChatListUI/Sources/Node/ChatListItem.swift"
    replace_unique(
        chat_list_item,
        "import ItemListUI\n",
        "import ItemListUI\nimport NagramiXCore\n",
        "Chat-list row hold-only actions dependency",
    )
    replace_unique(
        chat_list_item,
        "    public private(set) var item: ChatListItem?\n",
        """    private var nagramiXRevealSettingsObserver: NSObjectProtocol?
    private var nagramiXStockRevealOptions: (left: [ItemListRevealOption], right: [ItemListRevealOption]) = ([], [])
    private var nagramiXRevealAnimationsEnabled = true
    private var nagramiXLastActionsOnHold = true

    override public func didLoad() {
        super.didLoad()
        self.nagramiXLastActionsOnHold = NagramiXTabSettings.current.chatActionsOnHold
        self.nagramiXApplyRevealSettings()
        self.nagramiXRevealSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else { return }
            let actionsOnHold = NagramiXTabSettings.current.chatActionsOnHold
            guard actionsOnHold != self.nagramiXLastActionsOnHold else { return }
            self.nagramiXLastActionsOnHold = actionsOnHold
            self.nagramiXApplyRevealSettings()
        })
    }

    override public func setRevealOptions(_ options: (left: [ItemListRevealOption], right: [ItemListRevealOption]), enableAnimations: Bool = true) {
        self.nagramiXStockRevealOptions = options
        self.nagramiXRevealAnimationsEnabled = enableAnimations
        self.nagramiXApplyRevealSettings()
    }

    private func nagramiXApplyRevealSettings() {
        if NagramiXTabSettings.current.chatActionsOnHold {
            let wasRevealed = !self.revealOffset.isZero
            // Clear native options before cancelling an active full swipe so
            // cancellation cannot select its old extended action.
            super.setRevealOptions((left: [], right: []), enableAnimations: self.nagramiXRevealAnimationsEnabled)
            super.setRevealOptionsOpened(false, animated: false)
            if wasRevealed {
                self.revealOptionsInteractivelyClosed()
            }
        } else {
            super.setRevealOptions(self.nagramiXStockRevealOptions, enableAnimations: self.nagramiXRevealAnimationsEnabled)
        }
    }

    override public func setRevealOptionsOpened(_ value: Bool, animated: Bool) {
        if NagramiXTabSettings.current.chatActionsOnHold {
            self.nagramiXApplyRevealSettings()
            if value {
                self.revealOptionsInteractivelyClosed()
            }
        } else {
            super.setRevealOptionsOpened(value, animated: animated)
        }
    }

    override public func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        if gestureRecognizer is ItemListRevealOptionsGestureRecognizer && NagramiXTabSettings.current.chatActionsOnHold {
            return false
        }
        return super.gestureRecognizerShouldBegin(gestureRecognizer)
    }

    public private(set) var item: ChatListItem?
""",
        "Gate only native row swipe actions; preserve context preview and folder gestures",
    )
    replace_unique(
        chat_list_item,
        """    deinit {
        self.cachedDataDisposable.dispose()
    }""",
        """    deinit {
        if let observer = self.nagramiXRevealSettingsObserver {
            NotificationCenter.default.removeObserver(observer)
        }
        self.cachedDataDisposable.dispose()
    }""",
        "Release the chat-row settings observer",
    )
    apply_chat_hold_routing(source)

    chat_list_node = source / "submodules" / "ChatListUI" / "Sources" / "Node" / "ChatListNode.swift"
    replace_once(
        chat_list_node,
        "    private let statePromise: ValuePromise<ChatListNodeState>\n",
        "    private let statePromise: ValuePromise<ChatListNodeState>\n    private let nagramiXSettingsRevision = ValuePromise<Bool>(false, ignoreRepeated: true)\n    private var nagramiXSettingsRevisionValue = false\n",
        "Chat list settings revision signal",
    )
    replace_once(
        chat_list_node,
        """            contacts,
            chatListFilters,
            accountIsPremium
        )
        |> mapToQueue { (hideArchivedFolderByDefault, displayArchiveIntro, storageInfo, savedMessagesPeer, updateAndFilter, state, contacts, chatListFilters, accountIsPremium) -> Signal<ChatListNodeListViewTransition, NoError> in
""",
        """            contacts,
            chatListFilters,
            accountIsPremium,
            self.nagramiXSettingsRevision.get()
        )
        |> mapToQueue { (hideArchivedFolderByDefault, displayArchiveIntro, storageInfo, savedMessagesPeer, updateAndFilter, state, contacts, chatListFilters, accountIsPremium, _) -> Signal<ChatListNodeListViewTransition, NoError> in
""",
        "Rebuild chat list entries after NagramiX settings changes",
    )
    replace_once(
        chat_list_node,
        """    public func updateState(_ f: (ChatListNodeState) -> ChatListNodeState) {
""",
        """    public func nagramiXRefreshSettings() {
        self.nagramiXSettingsRevisionValue = !self.nagramiXSettingsRevisionValue
        self.nagramiXSettingsRevision.set(self.nagramiXSettingsRevisionValue)
    }

    public func updateState(_ f: (ChatListNodeState) -> ChatListNodeState) {
""",
        "Expose an immediate NagramiX chat-list refresh",
    )

    chat_list_controller = source / "submodules" / "ChatListUI" / "Sources" / "ChatListController.swift"
    replace_once(
        chat_list_controller,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "Chat list NagramiXCore import",
    )
    replace_once(
        chat_list_controller,
        '''                    } else {
                        languageCode = "en"
                    }
                    return languageCode
''',
        '''                    } else {
                        languageCode = "ru"
                    }
                    return languageCode
''',
        "Keep the clean-install localization state consistent with Russian presentation strings",
    )
    replace_once(
        chat_list_controller,
        '''            |> mapToSignal({ value -> Signal<(String, SuggestedLocalizationInfo)?, NoError> in
                guard let suggestedLocalization = value.1, !suggestedLocalization.isSeen && suggestedLocalization.languageCode != "en" && suggestedLocalization.languageCode != value.0 else {
                    return .single(nil)
                }
                return context.engine.localization.suggestedLocalizationInfo(languageCode: suggestedLocalization.languageCode, extractKeys: LanguageSuggestionControllerStrings.keys)
                |> map({ suggestedLocalization -> (String, SuggestedLocalizationInfo)? in
                    return (value.0, suggestedLocalization)
                })
            })
''',
        '''            |> mapToSignal({ _ -> Signal<(String, SuggestedLocalizationInfo)?, NoError> in
                // Язык меняется только пользователем в штатных настройках.
                return .single(nil)
            })
''',
        "Keep language changes in the native settings without automatic suggestions",
    )
    replace_once(
        chat_list_controller,
        """        let hasProxy = context.sharedContext.accountManager.sharedData(keys: [SharedDataKeys.proxySettings])
        |> map { sharedData -> (Bool, Bool) in
            if let settings = sharedData.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) {
                return (!settings.servers.isEmpty, settings.enabled)
            } else {
                return (false, false)
            }
        }
        |> distinctUntilChanged(isEqual: { lhs, rhs in
            return lhs == rhs
        })
""",
        """        let showProxyButton = Signal<Bool, NoError> { subscriber in
            subscriber.putNext(NagramiXTabSettings.current.showProxyButton)
            let observer = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: nil, using: { _ in
                subscriber.putNext(NagramiXTabSettings.current.showProxyButton)
            })
            return ActionDisposable {
                NotificationCenter.default.removeObserver(observer)
            }
        }
        |> distinctUntilChanged
        let hasProxy = combineLatest(context.sharedContext.accountManager.sharedData(keys: [SharedDataKeys.proxySettings]), showProxyButton)
        |> map { sharedData, showProxyButton -> (Bool, Bool) in
            let settings = sharedData.entries[SharedDataKeys.proxySettings]?.get(ProxySettings.self) ?? .defaultSettings
            return (showProxyButton, settings.enabled)
        }
        |> distinctUntilChanged(isEqual: { lhs, rhs in
            return lhs == rhs
        })
""",
        "Keep the Chat proxy button visible independently from saved proxies",
    )
    replace_once(
        chat_list_controller,
        """                        self.leftButton = AnyComponentWithIdentity(id: "edit", component: AnyComponent(NavigationButtonComponent(
                            content: .text(title: presentationData.strings.Common_Edit, isBold: false),
""",
        """                        self.leftButton = AnyComponentWithIdentity(id: "edit", component: AnyComponent(NavigationButtonComponent(
                            content: .text(title: presentationData.strings.nagramiXEdit, isBold: false),
""",
        "Use the full localized Edit title on the root Chat screen",
    )
    replace_once(
        chat_list_controller,
        "    private var displayedStoriesTooltip: Bool = false\n",
        "    private var displayedStoriesTooltip: Bool = false\n    private var nagramiXSettingsObserver: NSObjectProtocol?\n    private var nagramiXLastOrderedStorySubscriptions: EngineStorySubscriptions?\n",
        "Chat list NagramiX settings observer state",
    )
    replace_once(
        chat_list_controller,
        "    public var hasStorySubscriptions: Bool {\n        if let rawStorySubscriptions = self.rawStorySubscriptions, !rawStorySubscriptions.items.isEmpty {\n",
        "    public var hasStorySubscriptions: Bool {\n        if NagramiXTabSettings.current.hideStories {\n            return false\n        }\n        if let rawStorySubscriptions = self.rawStorySubscriptions, !rawStorySubscriptions.items.isEmpty {\n",
        "Hidden stories do not report a visible subscription feed",
    )
    replace_once(
        chat_list_controller,
        "        super.init(context: context, navigationBarPresentationData: nil)\n        \n        self.accessoryPanelContainer = ASDisplayNode()\n",
        """        super.init(context: context, navigationBarPresentationData: nil)

        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else {
                return
            }
            self.orderedStorySubscriptions = NagramiXTabSettings.current.hideStories ? nil : (self.nagramiXLastOrderedStorySubscriptions ?? self.rawStorySubscriptions)
            self.chatListDisplayNode.effectiveContainerNode.currentItemNode.nagramiXRefreshSettings()
            let transition: ContainedViewLayoutTransition = self.didAppear ? .animated(duration: 0.4, curve: .spring) : .immediate
            self.chatListDisplayNode.temporaryContentOffsetChangeTransition = transition
            self.requestLayout(transition: transition)
            self.chatListDisplayNode.temporaryContentOffsetChangeTransition = nil
            if NagramiXTabSettings.current.hideStories {
                self.chatListDisplayNode.scrollToTopIfStoriesAreExpanded()
            }
        })

        self.accessoryPanelContainer = ASDisplayNode()
""",
        "Observe immediate story visibility changes",
    )
    replace_once(
        chat_list_controller,
        "        self.globalControlPanelsContextStateDisposable?.dispose()\n    }\n",
        """        self.globalControlPanelsContextStateDisposable?.dispose()
        if let nagramiXSettingsObserver = self.nagramiXSettingsObserver {
            NotificationCenter.default.removeObserver(nagramiXSettingsObserver)
        }
    }
""",
        "Chat list observer cleanup",
    )
    replace_once(
        chat_list_controller,
        """                    self.orderedStorySubscriptions = EngineStorySubscriptions(
                        accountItem: rawStorySubscriptions.accountItem,
                        items: items,
                        hasMoreToken: rawStorySubscriptions.hasMoreToken
                    )
""",
        """                    let orderedStorySubscriptions = EngineStorySubscriptions(
                        accountItem: rawStorySubscriptions.accountItem,
                        items: items,
                        hasMoreToken: rawStorySubscriptions.hasMoreToken
                    )
                    self.nagramiXLastOrderedStorySubscriptions = orderedStorySubscriptions
                    self.orderedStorySubscriptions = NagramiXTabSettings.current.hideStories ? nil : orderedStorySubscriptions
""",
        "Hide the chat-list story feed without removing story data",
    )
    replace_once(
        chat_list_controller,
        "    func storyCameraPanGestureChanged(transitionFraction: CGFloat) {\n        guard let rootController = self.context.sharedContext.mainWindow?.viewController as? TelegramRootControllerInterface else {\n",
        "    func storyCameraPanGestureChanged(transitionFraction: CGFloat) {\n        if NagramiXTabSettings.current.disableStoryCameraSwipe && self.storyCameraTransitionInCoordinator == nil {\n            return\n        }\n        guard let rootController = self.context.sharedContext.mainWindow?.viewController as? TelegramRootControllerInterface else {\n",
        "Disable only the story-camera swipe gesture",
    )
    replace_once(
        chat_list_controller,
        """            componentView.storyComposeAction = { [weak self] offset in
                guard let self else {
                    return
                }
                self.openStoryCamera(fromList: true, gesturePullOffset: offset)
            }
""",
        """            componentView.storyComposeAction = { [weak self] offset in
                guard let self else {
                    return
                }
                guard !NagramiXTabSettings.current.disableStoryCameraSwipe else {
                    return
                }
                self.openStoryCamera(fromList: true, gesturePullOffset: offset)
            }
""",
        "Disable the story-carousel pull gesture without disabling explicit camera buttons",
    )

    story_container_screen = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryContainerScreen.swift"
    replace_once(
        story_container_screen,
        "import TelegramCore\n",
        "import TelegramCore\nimport TelegramPresentationData\nimport PhotoResources\nimport Postbox\nimport NagramiXCore\n",
        "Story viewer NagramiX imports",
    )
    replace_once(
        story_container_screen,
        "public class StoryContainerScreen: ViewControllerComponentContainer, KeyShortcutResponder {\n",
        """// Never upscale Telegram's already blurred tiny placeholder behind the confirmation.
// Fetch only the photo or the video's preview image; this does not mark a story seen.
private func nagramiXStoryPhotoPreview(context: AccountContext, peer: PeerReference, id: Int32, image: TelegramMediaImage) -> Signal<UIImage?, NoError> {
    return chatMessagePhotoDatas(postbox: context.account.postbox, userLocation: .peer(peer.id), customUserContentType: .story, photoReference: .story(peer: peer, id: id, media: image), autoFetchFullSize: true)
    |> filter { $0._3 && $0._1 != nil }
    |> take(1)
    |> map { value in
        return value._1.flatMap { UIImage(data: $0) }
    }
}

private func nagramiXStoryVideoPreview(context: AccountContext, peer: PeerReference, id: Int32, file: TelegramMediaFile) -> Signal<UIImage?, NoError> {
    guard let representation = largestImageRepresentation(file.previewRepresentations) else {
        return .single(nil)
    }
    let reference = FileMediaReference.story(peer: peer, id: id, media: file)
    return Signal { subscriber in
        let fetched = fetchedMediaResource(mediaBox: context.account.postbox.mediaBox, userLocation: .peer(peer.id), userContentType: .story, reference: reference.resourceReference(representation.resource), statsCategory: .image).start()
        let data = (context.account.postbox.mediaBox.resourceData(representation.resource)
        |> filter { $0.complete }
        |> take(1)).start(next: { resource in
            let image = (try? Data(contentsOf: URL(fileURLWithPath: resource.path), options: .mappedIfSafe)).flatMap { UIImage(data: $0) }
            subscriber.putNext(image)
        }, completed: {
            subscriber.putCompletion()
        })
        return ActionDisposable {
            data.dispose()
            fetched.dispose()
        }
    }
}

private final class NagramiXStoryConfirmationController: ViewController {
    private var theme: PresentationTheme
    private var themeDisposable: Disposable?
    private let previewSignal: Signal<UIImage?, NoError>?
    private let confirmed: () -> Void
    private let cancelled: () -> Void
    private var previewDisposable: Disposable?
    private var finished = false
    private let imageView = UIImageView()
    private let blurView = UIVisualEffectView(effect: UIBlurEffect(style: .dark))
    private let dimView = UIView()
    private let titleLabel = UILabel()
    private let bodyLabel = UILabel()
    private let closeButton = UIButton(type: .system)
    private let actionButton = UIButton(type: .system)

    init(context: AccountContext, previewSignal: Signal<UIImage?, NoError>?, title: String, body: String, action: String, confirmed: @escaping () -> Void, cancelled: @escaping () -> Void) {
        self.theme = context.sharedContext.currentPresentationData.with { $0 }.theme
        self.previewSignal = previewSignal
        self.confirmed = confirmed
        self.cancelled = cancelled
        super.init(navigationBarPresentationData: nil)
        self.navigationPresentation = .flatModal
        self.statusBar.statusBarStyle = .White
        self.titleLabel.text = title
        self.bodyLabel.text = body
        self.actionButton.setTitle(action, for: .normal)
        self.themeDisposable = (context.sharedContext.presentationData |> deliverOnMainQueue).start(next: { [weak self] data in
            guard let self else { return }
            self.theme = data.theme
            if self.isNodeLoaded { self.updateTheme() }
        })
    }

    required init(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    deinit {
        self.previewDisposable?.dispose()
        self.themeDisposable?.dispose()
    }

    private func updateTheme() {
        // Same paired fill/foreground keys as SolidRoundedButtonTheme(theme:).
        self.actionButton.backgroundColor = self.theme.list.itemCheckColors.fillColor
        self.actionButton.setTitleColor(self.theme.list.itemCheckColors.foregroundColor, for: .normal)
    }

    override func loadDisplayNode() {
        self.displayNode = ASDisplayNode()
        self.displayNode.backgroundColor = .black
        self.displayNodeDidLoad()
        self.imageView.contentMode = .scaleAspectFill
        self.imageView.clipsToBounds = true
        self.blurView.alpha = 0.5
        self.blurView.isUserInteractionEnabled = false
        self.dimView.backgroundColor = UIColor(white: 0.0, alpha: 0.18)
        self.titleLabel.textColor = .white
        self.titleLabel.font = UIFont.systemFont(ofSize: 28.0, weight: .bold)
        self.titleLabel.textAlignment = .center
        self.bodyLabel.textColor = UIColor(white: 1.0, alpha: 0.84)
        self.bodyLabel.font = UIFont.systemFont(ofSize: 17.0)
        self.bodyLabel.textAlignment = .center
        self.bodyLabel.numberOfLines = 0
        self.closeButton.setTitle("×", for: .normal)
        self.closeButton.setTitleColor(.white, for: .normal)
        self.closeButton.titleLabel?.font = UIFont.systemFont(ofSize: 36.0)
        self.closeButton.addTarget(self, action: #selector(self.closePressed), for: .touchUpInside)
        self.actionButton.titleLabel?.font = UIFont.systemFont(ofSize: 17.0, weight: .semibold)
        self.updateTheme()
        self.actionButton.layer.cornerRadius = 14.0
        self.actionButton.addTarget(self, action: #selector(self.confirmPressed), for: .touchUpInside)
        [self.imageView, self.blurView, self.dimView, self.titleLabel, self.bodyLabel, self.closeButton, self.actionButton].forEach { self.displayNode.view.addSubview($0) }
        if let previewSignal = self.previewSignal {
            self.previewDisposable = (previewSignal |> deliverOnMainQueue).start(next: { [weak self] image in
                self?.imageView.image = image
            })
        }
    }

    override func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
        let bounds = CGRect(origin: .zero, size: layout.size)
        transition.updateFrame(view: self.imageView, frame: bounds)
        transition.updateFrame(view: self.blurView, frame: bounds)
        transition.updateFrame(view: self.dimView, frame: bounds)
        let inset: CGFloat = 28.0
        transition.updateFrame(view: self.closeButton, frame: CGRect(x: layout.size.width - 60.0, y: layout.safeInsets.top + 8.0, width: 44.0, height: 44.0))
        let titleSize = self.titleLabel.sizeThatFits(CGSize(width: layout.size.width - inset * 2.0, height: 80.0))
        let bodySize = self.bodyLabel.sizeThatFits(CGSize(width: layout.size.width - inset * 2.0, height: 180.0))
        let top = floor((layout.size.height - titleSize.height - bodySize.height - 12.0) * 0.46)
        transition.updateFrame(view: self.titleLabel, frame: CGRect(x: inset, y: top, width: layout.size.width - inset * 2.0, height: titleSize.height))
        transition.updateFrame(view: self.bodyLabel, frame: CGRect(x: inset, y: top + titleSize.height + 12.0, width: layout.size.width - inset * 2.0, height: bodySize.height))
        transition.updateFrame(view: self.actionButton, frame: CGRect(x: inset, y: layout.size.height - layout.safeInsets.bottom - 72.0, width: layout.size.width - inset * 2.0, height: 52.0))
    }

    @objc private func closePressed() {
        guard !self.finished else { return }
        self.finished = true
        self.dismiss(completion: self.cancelled)
    }
    @objc private func confirmPressed() {
        guard !self.finished else { return }
        self.finished = true
        self.dismiss(completion: self.confirmed)
    }
}

public class StoryContainerScreen: ViewControllerComponentContainer, KeyShortcutResponder {
""",
        "Add a full-screen pre-view story confirmation",
    )
    replace_once(
        story_container_screen,
        """    private let context: AccountContext
    private var didAnimateIn: Bool = false
    private var isDismissed: Bool = false
""",
        """    private let context: AccountContext
    private var didAnimateIn: Bool = false
    private var isDismissed: Bool = false
    private let nagramiXContent: StoryContentContext
    private var nagramiXPresentationDisposable: Disposable?
    private var nagramiXIsPresentingConfirmation = false
    private var nagramiXApprovedStoryId: EngineStoryId?
""",
        "Story presentation and settings state",
    )
    replace_once(
        story_container_screen,
        """    ) {
        self.context = context
""" + "        \n" + """        super.init(context: context, component: StoryContainerScreenComponent(
            context: context,
            content: content,
""",
        """    ) {
        self.context = context
        self.nagramiXContent = content

        super.init(context: context, component: StoryContainerScreenComponent(
            context: context,
            content: content,
""",
        "Keep the real story context available while presentation is pending",
    )
    replace_once(
        story_container_screen,
        """    deinit {
        self.context.sharedContext.hasPreloadBlockingContent.set(.single(false))
        self.focusedItemPromise.set(.single(nil))
    }
""",
        """    deinit {
        self.nagramiXPresentationDisposable?.dispose()
        self.context.sharedContext.hasPreloadBlockingContent.set(.single(false))
        self.focusedItemPromise.set(.single(nil))
    }
""",
        "Clean up deferred story presentation state",
    )
    replace_once(
        story_container_screen,
        """    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
    }
""",
        """    override public func containerLayoutUpdated(_ layout: ContainerViewLayout, transition: ContainedViewLayoutTransition) {
        super.containerLayoutUpdated(layout, transition: transition)
    }

    fileprivate func nagramiXUpdateStoryConfirmation(slice: StoryContentContextState.FocusedSlice?) {
        guard NagramiXTabSettings.current.confirmStoryViewing, let slice, slice.peer.id != self.context.account.peerId, !slice.item.isSeen, !self.nagramiXConfirmedStoryIds.contains(slice.item.id) else {
            self.nagramiXPendingConfirmationId = nil
            self.nagramiXConfirmationOverlay?.removeFromSuperview()
            return
        }
        guard self.nagramiXPendingConfirmationId != slice.item.id else { return }
        self.nagramiXPendingConfirmationId = slice.item.id
        self.nagramiXConfirmationOverlay?.removeFromSuperview()

        let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
        let overlay = UIView()
        overlay.translatesAutoresizingMaskIntoConstraints = false
        overlay.backgroundColor = UIColor(white: 0.0, alpha: 0.30)
        let blur = UIVisualEffectView(effect: UIBlurEffect(style: .dark))
        blur.translatesAutoresizingMaskIntoConstraints = false
        blur.isUserInteractionEnabled = false
        overlay.addSubview(blur)
        let closeButton = UIButton(type: .system)
        closeButton.translatesAutoresizingMaskIntoConstraints = false
        closeButton.setTitle("×", for: .normal)
        closeButton.titleLabel?.font = UIFont.systemFont(ofSize: 42.0, weight: .light)
        closeButton.tintColor = .white
        closeButton.addTarget(self, action: #selector(self.nagramiXCancelStoryConfirmation), for: .touchUpInside)
        overlay.addSubview(closeButton)
        let titleLabel = UILabel()
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        titleLabel.text = presentationData.strings.nagramiXStoryConfirmationTitle
        titleLabel.textColor = .white
        titleLabel.font = UIFont.systemFont(ofSize: 23.0, weight: .semibold)
        titleLabel.textAlignment = .center
        overlay.addSubview(titleLabel)
        let bodyLabel = UILabel()
        bodyLabel.translatesAutoresizingMaskIntoConstraints = false
        bodyLabel.text = presentationData.strings.nagramiXStoryConfirmationText(owner: slice.effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder))
        bodyLabel.textColor = UIColor(white: 0.78, alpha: 1.0)
        bodyLabel.font = UIFont.systemFont(ofSize: 17.0)
        bodyLabel.textAlignment = .center
        bodyLabel.numberOfLines = 0
        overlay.addSubview(bodyLabel)
        let viewButton = UIButton(type: .system)
        viewButton.translatesAutoresizingMaskIntoConstraints = false
        viewButton.setTitle(presentationData.strings.nagramiXViewStoryAction, for: .normal)
        viewButton.setTitleColor(.white, for: .normal)
        viewButton.titleLabel?.font = UIFont.systemFont(ofSize: 19.0, weight: .semibold)
        viewButton.backgroundColor = presentationData.theme.list.itemAccentColor
        viewButton.layer.cornerRadius = 14.0
        viewButton.addTarget(self, action: #selector(self.nagramiXAcceptStoryConfirmation), for: .touchUpInside)
        overlay.addSubview(viewButton)
        self.view.addSubview(overlay)
        NSLayoutConstraint.activate([
            overlay.leadingAnchor.constraint(equalTo: self.view.leadingAnchor), overlay.trailingAnchor.constraint(equalTo: self.view.trailingAnchor), overlay.topAnchor.constraint(equalTo: self.view.topAnchor), overlay.bottomAnchor.constraint(equalTo: self.view.bottomAnchor),
            blur.leadingAnchor.constraint(equalTo: overlay.leadingAnchor), blur.trailingAnchor.constraint(equalTo: overlay.trailingAnchor), blur.topAnchor.constraint(equalTo: overlay.topAnchor), blur.bottomAnchor.constraint(equalTo: overlay.bottomAnchor),
            closeButton.trailingAnchor.constraint(equalTo: overlay.safeAreaLayoutGuide.trailingAnchor, constant: -18.0), closeButton.topAnchor.constraint(equalTo: overlay.safeAreaLayoutGuide.topAnchor, constant: 4.0), closeButton.widthAnchor.constraint(equalToConstant: 48.0), closeButton.heightAnchor.constraint(equalToConstant: 48.0),
            titleLabel.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 32.0), titleLabel.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -32.0), titleLabel.centerYAnchor.constraint(equalTo: overlay.centerYAnchor, constant: -52.0),
            bodyLabel.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 44.0), bodyLabel.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -44.0), bodyLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 10.0),
            viewButton.leadingAnchor.constraint(equalTo: overlay.leadingAnchor, constant: 44.0), viewButton.trailingAnchor.constraint(equalTo: overlay.trailingAnchor, constant: -44.0), viewButton.topAnchor.constraint(equalTo: bodyLabel.bottomAnchor, constant: 48.0), viewButton.heightAnchor.constraint(equalToConstant: 58.0)
        ])
        self.nagramiXConfirmationOverlay = overlay
        self.requestLayout(forceUpdate: true, transition: ContainedViewLayoutTransition.immediate)
    }

    @objc private func nagramiXCancelStoryConfirmation() {
        self.dismiss()
    }

    @objc private func nagramiXAcceptStoryConfirmation() {
        guard let id = self.nagramiXPendingConfirmationId else { return }
        self.nagramiXConfirmedStoryIds.insert(id)
        self.nagramiXPendingConfirmationId = nil
        self.nagramiXConfirmationOverlay?.removeFromSuperview()
        self.nagramiXContent.markAsSeen(id: id)
        self.requestLayout(forceUpdate: true, transition: ContainedViewLayoutTransition.immediate)
    }

    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {
        action()
        return
        guard NagramiXTabSettings.current.confirmStoryViewing else {
            action()
            return
        }

        let presentForState: (StoryContentContextState) -> Void = { [weak self, weak parentController] state in
            guard let self, let parentController else {
                return
            }
            guard let slice = state.slice else {
                self.nagramiXTransitionSourceView?.isHidden = false
                return
            }
            if slice.effectivePeer.id == self.context.account.peerId {
                action()
                return
            }

            let parentId = ObjectIdentifier(parentController)
            if StoryContainerScreen.nagramiXConfirmationParentIds.contains(parentId) {
                self.nagramiXTransitionSourceView?.isHidden = false
                return
            }
            StoryContainerScreen.nagramiXConfirmationParentIds.insert(parentId)

            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let actionSheet = ActionSheetController(presentationData: presentationData)
            var didAccept = false
            actionSheet.dismissed = { [weak self] _ in
                StoryContainerScreen.nagramiXConfirmationParentIds.remove(parentId)
                if !didAccept {
                    self?.nagramiXTransitionSourceView?.isHidden = false
                }
            }
            actionSheet.setItemGroups([
                ActionSheetItemGroup(items: [
                    ActionSheetTextItem(title: presentationData.strings.nagramiXStoryConfirmationTitle + "\\n" + presentationData.strings.nagramiXStoryConfirmationText),
                    ActionSheetButtonItem(title: presentationData.strings.nagramiXViewStoryAction, color: .accent, font: .bold, action: { [weak actionSheet] in
                        didAccept = true
                        StoryContainerScreen.nagramiXConfirmationParentIds.remove(parentId)
                        actionSheet?.dismissAnimated()
                        action()
                    }),
                ]),
                ActionSheetItemGroup(items: [
                    ActionSheetButtonItem(title: presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in
                        actionSheet?.dismissAnimated()
                    }),
                ]),
            ])
            parentController.present(actionSheet, in: .window(.root))
        }

        if let state = self.nagramiXContent.stateValue {
            presentForState(state)
        } else {
            self.nagramiXPresentationDisposable = (self.nagramiXContent.state
            |> take(1)
            |> deliverOnMainQueue).start(next: { state in
                presentForState(state)
            })
        }
    }

    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {
        self.nagramiXPresent(from: parentController, action: { [weak self, weak parentController] in
            guard let self, let parentController else {
                return
            }
            parentController.push(self)
            completion()
        })
    }

    public func nagramiXPush(from navigationController: NavigationController, completion: @escaping () -> Void = {}) {
        guard let parentController = navigationController.topViewController as? ViewController else {
            navigationController.pushViewController(self)
            completion()
            return
        }
        self.nagramiXPresent(from: parentController, action: { [weak self, weak navigationController] in
            guard let self, let navigationController else {
                return
            }
            navigationController.pushViewController(self)
            completion()
        })
    }
""",
        "Confirm an external story before it is pushed onto the navigation stack",
    )
    replace_between(
        story_container_screen,
        "    fileprivate func nagramiXUpdateStoryConfirmation(slice: StoryContentContextState.FocusedSlice?) {",
        "    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {",
        "",
        "Remove the unsafe post-open story confirmation overlay",
    )
    replace_between(
        story_container_screen,
        "    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {",
        "    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {",
        """    fileprivate func nagramiXConfirmNavigation(peer: EnginePeer, item: StoryContentItem, action: @escaping () -> Void) {
        guard NagramiXTabSettings.current.confirmStoryViewing, peer.id != self.context.account.peerId else {
            action()
            return
        }
        guard !self.nagramiXIsPresentingConfirmation else { return }
        self.nagramiXIsPresentingConfirmation = true

        let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
        let effectivePeer = item.itemPeer ?? peer
        let owner = effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
        var previewSignal: Signal<UIImage?, NoError>?
        if let peerReference = PeerReference(effectivePeer) {
            switch item.storyItem.media {
            case let .image(image):
                previewSignal = nagramiXStoryPhotoPreview(context: self.context, peer: peerReference, id: item.storyItem.id, image: image)
            case let .file(file):
                previewSignal = nagramiXStoryVideoPreview(context: self.context, peer: peerReference, id: item.storyItem.id, file: file)
            default:
                break
            }
        }
        let confirmationController = NagramiXStoryConfirmationController(
            context: self.context,
            previewSignal: previewSignal,
            title: presentationData.strings.nagramiXStoryConfirmationTitle,
            body: presentationData.strings.nagramiXStoryConfirmationText(owner: owner),
            action: presentationData.strings.nagramiXViewStoryAction,
            confirmed: { [weak self] in
                guard let self else { return }
                self.nagramiXIsPresentingConfirmation = false
                self.nagramiXApprovedStoryId = item.id
                action()
            },
            cancelled: { [weak self] in
                self?.nagramiXIsPresentingConfirmation = false
            }
        )
        self.present(confirmationController, in: .window(.root))
    }

    fileprivate func nagramiXCanMarkStoryAsSeen(_ id: EngineStoryId) -> Bool {
        guard NagramiXTabSettings.current.confirmStoryViewing else { return true }
        guard let slice = self.nagramiXContent.stateValue?.slice else { return false }
        if slice.effectivePeer.id == self.context.account.peerId { return true }
        guard self.nagramiXApprovedStoryId == id else { return false }
        self.nagramiXApprovedStoryId = nil
        return true
    }

    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {
        guard NagramiXTabSettings.current.confirmStoryViewing else {
            action()
            return
        }
        guard !self.nagramiXIsPresentingConfirmation else {
            return
        }

        let presentForState: (StoryContentContextState) -> Void = { [weak self, weak parentController] state in
            guard let self, let parentController else {
                return
            }
            guard let slice = state.slice else {
                action()
                return
            }
            if slice.effectivePeer.id == self.context.account.peerId {
                action()
                return
            }

            self.nagramiXIsPresentingConfirmation = true
            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let owner = slice.effectivePeer.displayTitle(strings: presentationData.strings, displayOrder: presentationData.nameDisplayOrder)
            var previewSignal: Signal<UIImage?, NoError>?
            if let peerReference = PeerReference(slice.effectivePeer) {
                switch slice.item.storyItem.media {
                case let .image(image):
                    previewSignal = nagramiXStoryPhotoPreview(context: self.context, peer: peerReference, id: slice.item.storyItem.id, image: image)
                case let .file(file):
                    previewSignal = nagramiXStoryVideoPreview(context: self.context, peer: peerReference, id: slice.item.storyItem.id, file: file)
                default:
                    break
                }
            }
            let confirmationController = NagramiXStoryConfirmationController(
                context: self.context,
                previewSignal: previewSignal,
                title: presentationData.strings.nagramiXStoryConfirmationTitle,
                body: presentationData.strings.nagramiXStoryConfirmationText(owner: owner),
                action: presentationData.strings.nagramiXViewStoryAction,
                confirmed: { [weak self] in
                    self?.nagramiXIsPresentingConfirmation = false
                    self?.nagramiXApprovedStoryId = slice.item.id
                    action()
                },
                cancelled: { [weak self] in
                    self?.nagramiXIsPresentingConfirmation = false
                }
            )
            parentController.present(confirmationController, in: .window(.root))
        }

        if let state = self.nagramiXContent.stateValue {
            presentForState(state)
        } else {
            self.nagramiXPresentationDisposable?.dispose()
            self.nagramiXPresentationDisposable = (self.nagramiXContent.state
            |> take(1)
            |> deliverOnMainQueue).start(next: { state in
                presentForState(state)
            })
        }
    }

""",
        "Present native confirmation before an unseen external story opens",
    )
    replace_once(
        story_container_screen,
        """                    if let mappedId {
                        self.pendingNavigationToItemId = mappedId
                        component.content.navigate(navigation: .item(.id(mappedId)))
                    }
""",
        """                    if let mappedId, let targetItem = slice.allItems.first(where: { $0.id == mappedId }) {
                        controller.nagramiXConfirmNavigation(peer: targetItem.itemPeer ?? slice.peer, item: targetItem, action: { [weak self] in
                            guard let self, let component = self.component else { return }
                            self.pendingNavigationToItemId = mappedId
                            component.content.navigate(navigation: .item(.id(mappedId)))
                        })
                    }
""",
        "Gate every explicit same-peer story navigation before changing the focused item",
    )
    replace_once(
        story_container_screen,
        "            guard let component = self.component, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen else {\n",
        "            guard let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen else {\n",
        "Remove the now-unused navigation component binding after the per-story gate owns navigation",
    )
    replace_once(
        story_container_screen,
        "                if let component = self.component, let stateValue = self.stateValue, let _ = stateValue.slice {\n",
        "                if let component = self.component, let stateValue = self.stateValue, let _ = stateValue.slice, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen {\n",
        "Access the confirmation controller before committing a peer swipe",
    )
    replace_once(
        story_container_screen,
        "                    if let direction {\n                        component.content.navigate(navigation: .peer(direction))\n                        \n                        if case .previous = direction {\n",
        """                    if let direction {
                        let targetSlice: StoryContentContextState.FocusedSlice?
                        switch direction {
                        case .previous:
                            targetSlice = stateValue.previousSlice
                        case .next:
                            targetSlice = stateValue.nextSlice
                        }
                        if let targetSlice {
                            controller.nagramiXConfirmNavigation(peer: targetSlice.effectivePeer, item: targetSlice.item, action: { [weak self] in
                                guard let self, let component = self.component else { return }
                                component.content.navigate(navigation: .peer(direction))
                            })
                        } else {
                            component.content.navigate(navigation: .peer(direction))
                        }

                        if case .previous = direction {
""",
        "Gate peer swipes before changing to the target peer story",
    )
    replace_once(
        story_container_screen,
        """                                markAsSeen: { [weak self] id in
                                    guard let self, let component = self.component else {
                                        return
                                    }
                                    component.content.markAsSeen(id: id)
                                },
""",
        """                                markAsSeen: { [weak self] id in
                                    guard let self, let component = self.component, let environment = self.environment, let controller = environment.controller() as? StoryContainerScreen, controller.nagramiXCanMarkStoryAsSeen(id) else {
                                        return
                                    }
                                    component.content.markAsSeen(id: id)
                                },
""",
        "Reject native seen registration until the exact target story is approved",
    )

    replace_once(
        chat_list_controller,
        "            self.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: self)\n",
        "Confirm chat-list stories before pushing the viewer",
    )

    message_stats_controller = source / "submodules" / "StatisticsUI" / "Sources" / "MessageStatsController.swift"
    replace_once(
        message_stats_controller,
        "            controller.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm message-stat stories before pushing the viewer",
    )

    channel_stats_controller = source / "submodules" / "StatisticsUI" / "Sources" / "ChannelStatsController.swift"
    replace_once(
        channel_stats_controller,
        "            controller.push(storyContainerScreen)\n",
        "            storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm channel-stat stories before pushing the viewer",
    )

    open_resolved_url = source / "submodules" / "TelegramUI" / "Sources" / "OpenResolvedUrl.swift"
    replace_once(
        open_resolved_url,
        "                        navigationController?.pushViewController(storyContainerScreen)\n",
        "                        if let navigationController {\n                            storyContainerScreen.nagramiXPush(from: navigationController)\n                        }\n",
        "Confirm deep-linked stories before pushing the viewer",
    )

    open_chat_message = source / "submodules" / "TelegramUI" / "Sources" / "OpenChatMessage.swift"
    replace_once(
        open_chat_message,
        "            navigationController?.pushViewController(storyContainerScreen)\n",
        "            if let navigationController {\n                storyContainerScreen.nagramiXPush(from: navigationController)\n            }\n",
        "Confirm message-linked stories before pushing the viewer",
    )

    chat_controller = source / "submodules" / "TelegramUI" / "Sources" / "ChatController.swift"
    replace_once(
        chat_controller,
        "                self.push(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: self)\n",
        "Confirm in-chat stories before pushing the viewer",
    )

    open_stories = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "OpenStories.swift"
    replace_once(
        open_stories,
        "            parentController?.push(storyContainerScreen)\n",
        "            if let parentController {\n                storyContainerScreen.nagramiXPush(from: parentController)\n            }\n",
        "Confirm archived stories before pushing the viewer",
    )
    replace_once(
        open_stories,
        "            parentController?.push(storyContainerScreen)\n            completion(storyContainerScreen)\n",
        "            if let parentController {\n                storyContainerScreen.nagramiXPush(from: parentController, completion: {\n                    completion(storyContainerScreen)\n                })\n            }\n",
        "Confirm peer stories before pushing the viewer",
    )

    story_item_set_component = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerComponent.swift"
    replace_once(
        story_item_set_component,
        "                controller.push(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: controller)\n",
        "Confirm repost-chain stories before pushing the viewer",
    )

    peer_info_story_pane = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoVisualMediaPaneNode" / "Sources" / "PeerInfoStoryPaneNode.swift"
    replace_once(
        peer_info_story_pane,
        "                navigationController.pushViewController(storyContainerScreen)\n",
        "                storyContainerScreen.nagramiXPush(from: navigationController)\n",
        "Confirm media-pane stories before pushing the viewer",
    )

    peer_info_open_stories = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreenOpenStories.swift"
    replace_once(
        peer_info_open_stories,
        "                self.controller?.push(storyContainerScreen)\n",
        "                if let controller = self.controller {\n                    storyContainerScreen.nagramiXPush(from: controller)\n                }\n",
        "Confirm profile-header stories before pushing the viewer",
    )

    peer_info_screen = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoScreen.swift"
    replace_once(
        peer_info_screen,
        "                self.controller?.push(storyContainerScreen)\n",
        "                if let controller = self.controller {\n                    storyContainerScreen.nagramiXPush(from: controller)\n                }\n",
        "Confirm profile stories before pushing the viewer",
    )

    story_footer_panel = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryFooterPanelComponent" / "Sources" / "StoryFooterPanelComponent.swift"
    replace_once(
        story_footer_panel,
        "    public let canShare: Bool\n    public let externalViews: EngineStoryItem.Views?\n",
        "    public let canShare: Bool\n    public let canRepost: Bool\n    public let externalViews: EngineStoryItem.Views?\n",
        "Story footer repost capability state",
    )
    replace_once(
        story_footer_panel,
        "        canShare: Bool,\n        externalViews: EngineStoryItem.Views?,\n",
        "        canShare: Bool,\n        canRepost: Bool,\n        externalViews: EngineStoryItem.Views?,\n",
        "Story footer repost capability argument",
    )
    replace_once(
        story_footer_panel,
        "        self.canShare = canShare\n        self.externalViews = externalViews\n",
        "        self.canShare = canShare\n        self.canRepost = canRepost\n        self.externalViews = externalViews\n",
        "Story footer repost capability assignment",
    )
    replace_once(
        story_footer_panel,
        "        if lhs.externalViews != rhs.externalViews {\n",
        "        if lhs.canRepost != rhs.canRepost {\n            return false\n        }\n        if lhs.externalViews != rhs.externalViews {\n",
        "Story footer repost capability equality",
    )
    replace_once(
        story_footer_panel,
        """                    let repostButton: ComponentView<Empty>
                    if let current = self.repostButton {
                        repostButton = current
                    } else {
                        repostButton = ComponentView()
                        self.repostButton = repostButton
                    }
""" + "                    \n" + """                    let forwardButton: ComponentView<Empty>
""",
        """                    let forwardButton: ComponentView<Empty>
""",
        "Create a repost button only when NagramiX enables it",
    )
    replace_once(
        story_footer_panel,
        """                    let repostButtonSize = repostButton.update(
                        transition: likeStatsTransition,
                        component: AnyComponent(MessageInputActionButtonComponent(
                            mode: .repost,
                            storyId: component.storyItem.id,
                            action: { [weak self] _, action, _ in
                                guard let self, let component = self.component else {
                                    return
                                }
                                guard case .up = action else {
                                    return
                                }
                                component.repostAction()
                            },
                            longPressAction: nil,
                            switchMediaInputMode: {
                            },
                            updateMediaCancelFraction: { _ in
                            },
                            lockMediaRecording: {
                            },
                            stopAndPreviewMediaRecording: {
                            },
                            moreAction: { _, _ in },
                            context: component.context,
                            theme: component.theme,
                            strings: component.strings,
                            presentController: { _ in },
                            audioRecorder: nil,
                            videoRecordingStatus: nil
                        )),
                        environment: {},
                        containerSize: CGSize(width: 33.0, height: 33.0)
                    )
                    if let repostButtonView = repostButton.view as? MessageInputActionButtonComponent.View {
                        if repostButtonView.superview == nil {
                            self.addSubview(repostButtonView)
                        }
                        var repostButtonFrame = CGRect(origin: CGPoint(x: rightContentOffset - repostButtonSize.width, y: floor((size.height - repostButtonSize.height) * 0.5)), size: repostButtonSize)
                        repostButtonFrame.origin.y += component.expandFraction * 45.0
""" + "                        \n" + """                        forwardStatsTransition.setPosition(view: repostButtonView, position: repostButtonFrame.center)
                        forwardStatsTransition.setBounds(view: repostButtonView, bounds: CGRect(origin: CGPoint(), size: repostButtonFrame.size))
                        forwardStatsTransition.setAlpha(view: repostButtonView, alpha: 1.0 - component.expandFraction)
""" + "                        \n" + """                        rightContentOffset -= repostButtonSize.width + 14.0
""" + "                        \n" + """                        if forwardStatsText.superview == nil {
                            repostButtonView.button.view.addSubview(forwardStatsText)
                        }
""" + "                        \n" + """                        forwardStatsFrame.origin.x -= repostButtonFrame.minX
                        forwardStatsFrame.origin.y -= repostButtonFrame.minY
                        forwardStatsTransition.setPosition(view: forwardStatsText, position: forwardStatsFrame.center)
                        forwardStatsTransition.setBounds(view: forwardStatsText, bounds: CGRect(origin: CGPoint(), size: forwardStatsFrame.size))
                    }
""" + "                    \n",
        """                    if component.canRepost {
                        let repostButton: ComponentView<Empty>
                        if let current = self.repostButton {
                            repostButton = current
                        } else {
                            repostButton = ComponentView()
                            self.repostButton = repostButton
                        }

                        let repostButtonSize = repostButton.update(
                            transition: likeStatsTransition,
                            component: AnyComponent(MessageInputActionButtonComponent(
                                mode: .repost,
                                storyId: component.storyItem.id,
                                action: { [weak self] _, action, _ in
                                    guard let self, let component = self.component else {
                                        return
                                    }
                                    guard case .up = action else {
                                        return
                                    }
                                    component.repostAction()
                                },
                                longPressAction: nil,
                                switchMediaInputMode: {
                                },
                                updateMediaCancelFraction: { _ in
                                },
                                lockMediaRecording: {
                                },
                                stopAndPreviewMediaRecording: {
                                },
                                moreAction: { _, _ in },
                                context: component.context,
                                theme: component.theme,
                                strings: component.strings,
                                presentController: { _ in },
                                audioRecorder: nil,
                                videoRecordingStatus: nil
                            )),
                            environment: {},
                            containerSize: CGSize(width: 33.0, height: 33.0)
                        )
                        if let repostButtonView = repostButton.view as? MessageInputActionButtonComponent.View {
                            if repostButtonView.superview == nil {
                                self.addSubview(repostButtonView)
                            }
                            var repostButtonFrame = CGRect(origin: CGPoint(x: rightContentOffset - repostButtonSize.width, y: floor((size.height - repostButtonSize.height) * 0.5)), size: repostButtonSize)
                            repostButtonFrame.origin.y += component.expandFraction * 45.0

                            forwardStatsTransition.setPosition(view: repostButtonView, position: repostButtonFrame.center)
                            forwardStatsTransition.setBounds(view: repostButtonView, bounds: CGRect(origin: CGPoint(), size: repostButtonFrame.size))
                            forwardStatsTransition.setAlpha(view: repostButtonView, alpha: 1.0 - component.expandFraction)

                            rightContentOffset -= repostButtonSize.width + 14.0

                            if forwardStatsText.superview == nil {
                                repostButtonView.button.view.addSubview(forwardStatsText)
                            }

                            forwardStatsFrame.origin.x -= repostButtonFrame.minX
                            forwardStatsFrame.origin.y -= repostButtonFrame.minY
                            forwardStatsTransition.setPosition(view: forwardStatsText, position: forwardStatsFrame.center)
                            forwardStatsTransition.setBounds(view: forwardStatsText, bounds: CGRect(origin: CGPoint(), size: forwardStatsFrame.size))
                        }
                    } else if let repostButton = self.repostButton {
                        self.repostButton = nil
                        repostButton.view?.removeFromSuperview()
                    }

""",
        "Hide the built-in repost action while keeping forwarding available",
    )

    story_item_set_component = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerComponent.swift"
    replace_once(
        story_item_set_component,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Story footer NagramiXCore import",
    )
    replace_once(
        story_item_set_component,
        "                                    canShare: canShare,\n                                    externalViews: nil,\n",
        "                                    canShare: canShare,\n                                    canRepost: canShare && NagramiXTabSettings.current.enableStoryRepost,\n                                    externalViews: nil,\n",
        "Combine NagramiX repost preference with Telegram forwarding restrictions",
    )

    story_send_message = source / "submodules" / "TelegramUI" / "Components" / "Stories" / "StoryContainerScreen" / "Sources" / "StoryItemSetContainerViewSendMessage.swift"
    replace_once(
        story_send_message,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Story share sheet NagramiXCore import",
    )
    replace_once(
        story_send_message,
        """            let shareController = component.context.sharedContext.makeShareController(context: component.context, params: ShareControllerParams(
""",
        """            let shareStory: (() -> Void)?
            if NagramiXTabSettings.current.enableStoryRepost {
                shareStory = { [weak view] in
                    guard let view else {
                        return
                    }
                    view.openStoryEditing(repost: true)
                }
            } else {
                shareStory = nil
            }

            let shareController = component.context.sharedContext.makeShareController(context: component.context, params: ShareControllerParams(
""",
        "Prepare the optional built-in repost-to-story action",
    )
    replace_once(
        story_send_message,
        """                shareStory: { [weak view] in
                    guard let view else {
                        return
                    }
                    view.openStoryEditing(repost: true)
                }
""",
        """                shareStory: shareStory
""",
        "Hide the share-sheet repost action when disabled",
    )

    message_share_menu = source / "submodules" / "TelegramUI" / "Sources" / "ChatControllerOpenMessageShareMenu.swift"
    replace_once(
        message_share_menu,
        "import TelegramCore\n",
        "import TelegramCore\nimport NagramiXCore\n",
        "Message share sheet NagramiXCore import",
    )
    replace_once(
        message_share_menu,
        "        let shareStory: (() -> Void)? = canShareToStory ? { [weak self] in\n",
        "        let shareStory: (() -> Void)? = (canShareToStory && NagramiXTabSettings.current.enableStoryRepost) ? { [weak self] in\n",
        "Gate the built-in public-message repost action with the NagramiX setting",
    )

    app_delegate = source / "submodules" / "TelegramUI" / "Sources" / "AppDelegate.swift"
    replace_once(
        app_delegate,
        """                var icons = [
                    PresentationAppIcon(name: "BlueIcon", imageName: "BlueIcon", isDefault: buildConfig.isAppStoreBuild),
                    PresentationAppIcon(name: "New2", imageName: "New2"),
                    PresentationAppIcon(name: "New1", imageName: "New1"),
                    PresentationAppIcon(name: "BlackIcon", imageName: "BlackIcon"),
                    PresentationAppIcon(name: "BlueClassicIcon", imageName: "BlueClassicIcon"),
                    PresentationAppIcon(name: "BlackClassicIcon", imageName: "BlackClassicIcon"),
                    PresentationAppIcon(name: "BlueFilledIcon", imageName: "BlueFilledIcon"),
                    PresentationAppIcon(name: "BlackFilledIcon", imageName: "BlackFilledIcon")
                ]
                if buildConfig.isInternalBuild {
                    icons.append(PresentationAppIcon(name: "WhiteFilledIcon", imageName: "WhiteFilledIcon"))
                }
""" + "                \n" + """                icons.append(PresentationAppIcon(name: "Premium", imageName: "Premium", isPremium: true))
                icons.append(PresentationAppIcon(name: "PremiumTurbo", imageName: "PremiumTurbo", isPremium: true))
                icons.append(PresentationAppIcon(name: "PremiumBlack", imageName: "PremiumBlack", isPremium: true))
""" + "                \n" + """                return icons
""",
        """                return [
                    PresentationAppIcon(name: "NagramiX1", imageName: "NagramiX1Preview", isDefault: true),
                    PresentationAppIcon(name: "NagramiX2", imageName: "NagramiX2"),
                    PresentationAppIcon(name: "NagramiX3", imageName: "NagramiX3"),
                    PresentationAppIcon(name: "NagramiX4", imageName: "NagramiX4"),
                    PresentationAppIcon(name: "NagramiX5", imageName: "NagramiX5"),
                    PresentationAppIcon(name: "NagramiX6", imageName: "NagramiX6"),
                    PresentationAppIcon(name: "NagramiX7", imageName: "NagramiX7"),
                    PresentationAppIcon(name: "NagramiX8", imageName: "NagramiX8")
                ]
""",
        "NagramiX app icon list",
    )

    icon_item = source / "submodules" / "SettingsUI" / "Sources" / "Themes" / "ThemeSettingsAppIconItem.swift"
    replace_once(
        icon_item,
        "import TelegramPresentationData\n",
        "import TelegramPresentationData\nimport NagramiXCore\n",
        "NagramiX app icon localization import",
    )
    replace_once(
        icon_item,
        """                                case "PremiumTurbo":
                                    name = item.strings.Appearance_AppIconTurbo
                                default:
""",
        """                                case "PremiumTurbo":
                                    name = item.strings.Appearance_AppIconTurbo
                                case "NagramiX1":
                                    name = item.strings.nagramiXIconMain
                                case "NagramiX2":
                                    name = item.strings.nagramiXIconSunset
                                case "NagramiX3":
                                    name = item.strings.nagramiXIconAurora
                                case "NagramiX4":
                                    name = item.strings.nagramiXIconGraphite
                                case "NagramiX5":
                                    name = item.strings.nagramiXIconAmber
                                case "NagramiX6":
                                    name = item.strings.nagramiXIconNeon
                                case "NagramiX7":
                                    name = item.strings.nagramiXIconLime
                                case "NagramiX8":
                                    name = item.strings.nagramiXIconRuby
                                default:
""",
        "NagramiX app icon display names",
    )

    telegram_build = source / "Telegram" / "BUILD"
    replace_once(
        telegram_build,
        """alternate_icon_folders = [
    "BlackIcon",
    "BlackClassicIcon",
    "BlackFilledIcon",
    "BlueIcon",
    "BlueClassicIcon",
    "BlueFilledIcon",
    "WhiteFilledIcon",
    "New1",
    "New2",
    "Premium",
    "PremiumBlack",
    "PremiumTurbo",
]
""",
        """alternate_icon_folders = [
    "NagramiX2",
    "NagramiX3",
    "NagramiX4",
    "NagramiX5",
    "NagramiX6",
    "NagramiX7",
    "NagramiX8",
]
""",
        "NagramiX alternate icon build targets",
    )

    replace_once(
        telegram_build,
        'composer_icon_folders = ["Telegram"]\n',
        'composer_icon_folders = []\n',
        "Disable the differently scaled Icon Composer primary icon",
    )
    replace_once(
        telegram_build,
        '    app_icons = [ ":{}_icon".format(name) for name in composer_icon_folders ],\n',
        '    app_icons = [":NagramiXPrimaryIcon"],\n',
        "Use the NagramiX1 appiconset as the primary icon",
    )
    replace_once(
        telegram_build,
        '''filegroup(
    name = "DefaultIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/BlueIcon.appiconset/*.png",
    ]),
)
''',
        '''filegroup(
    name = "DefaultIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/NagramiX1.appiconset/*.png",
    ]),
)

filegroup(
    name = "NagramiXPrimaryIcon",
    srcs = glob([
        "Telegram-iOS/AppIcons.xcassets/NagramiX1.appiconset/**/*",
    ]),
)
''',
        "Expose the NagramiX1 appiconset to rules_apple",
    )

    chat_panel_interaction = source / "submodules" / "ChatPresentationInterfaceState" / "Sources" / "ChatPanelInterfaceInteraction.swift"
    replace_once(
        chat_panel_interaction,
        "    public let forwardMessages: ([EngineRawMessage]) -> Void\n",
        "    public let forwardMessages: ([EngineRawMessage]) -> Void\n    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n    public let selectMessagesByAuthor: ((EnginePeer.Id) -> Void)?\n",
        "Expose a distinct copy-as-new handler plus author selection",
    )
    replace_once(
        chat_panel_interaction,
        "        forwardMessages: @escaping ([EngineRawMessage]) -> Void,\n        updateForwardOptionsState:",
        "        forwardMessages: @escaping ([EngineRawMessage]) -> Void,\n        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n        selectMessagesByAuthor: ((EnginePeer.Id) -> Void)? = nil,\n        updateForwardOptionsState:",
        "Add optional NagramiX chat interaction callbacks",
    )
    replace_once(
        chat_panel_interaction,
        "        self.forwardMessages = forwardMessages\n        self.updateForwardOptionsState = updateForwardOptionsState\n",
        "        self.forwardMessages = forwardMessages\n        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n        self.selectMessagesByAuthor = selectMessagesByAuthor\n        self.updateForwardOptionsState = updateForwardOptionsState\n",
        "Store the explicit NagramiX copy-as-new callback",
    )

    chat_controller_source = source / "submodules" / "TelegramUI" / "Sources" / "ChatController.swift"
    replace_once(
        chat_controller_source,
        "    let navigationActionDisposable = MetaDisposable()\n    let messageIndexDisposable = MetaDisposable()\n",
        "    let navigationActionDisposable = MetaDisposable()\n    let nagramiXSelectAuthorDisposable = MetaDisposable()\n    var nagramiXSelectedAuthorMessageIds: Set<MessageId>?\n    var nagramiXSelectAuthorGeneration: UInt64 = 0\n    var nagramiXIsSelectingAuthorMessages = false\n    let messageIndexDisposable = MetaDisposable()\n",
        "Own the cancellable Select From Author pagination lifecycle",
    )
    replace_once(
        chat_controller_source,
        "        self.navigationActionDisposable.dispose()\n        self.galleryHiddenMesageAndMediaDisposable.dispose()\n",
        "        self.navigationActionDisposable.dispose()\n        self.nagramiXSelectAuthorDisposable.dispose()\n        self.galleryHiddenMesageAndMediaDisposable.dispose()\n",
        "Cancel Select From Author when leaving the chat",
    )

    author_selection_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXAuthorSelection.swift"
    shutil.copy2(author_selection_overlay, source / "submodules" / "TelegramCore" / "Sources" / "TelegramEngine" / "Messages" / author_selection_overlay.name)

    chat_load_node = source / "submodules" / "TelegramUI" / "Sources" / "Chat" / "ChatControllerLoadDisplayNode.swift"
    replace_once(
        chat_load_node,
        """        }, updateForwardOptionsState: { [weak self] f in
""",
        """        }, copyMessagesWithoutSource: { [weak self] messages in
            guard let self, !messages.isEmpty else {
                return
            }
            guard !self.presentAccountFrozenInfoIfNeeded(delay: true) else {
                return
            }
            self.commitPurposefulAction()
            if messages.contains(where: { $0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) }) {
                self.forwardMessages(messages: messages.sorted(by: { $0.id < $1.id }), resetCurrent: false, transferMode: .copyAsNew)
            } else {
                self.forwardMessages(messageIds: messages.map { $0.id }.sorted(), transferMode: .copyAsNew)
            }
        }, selectMessagesByAuthor: { [weak self] authorId in
            guard let self, self.isNodeLoaded, !self.nagramiXIsSelectingAuthorMessages, let peerId = self.chatLocation.peerId else {
                return
            }
            self.nagramiXIsSelectingAuthorMessages = true
            self.nagramiXSelectAuthorGeneration &+= 1
            let generation = self.nagramiXSelectAuthorGeneration
            let threadId = self.chatLocation.threadId
            let presentationData = self.context.sharedContext.currentPresentationData.with { $0 }
            let progressController = OverlayStatusController(theme: presentationData.theme, type: .loading(cancelled: { [weak self] in
                guard let self else { return }
                self.nagramiXSelectAuthorGeneration &+= 1
                self.nagramiXIsSelectingAuthorMessages = false
                self.nagramiXSelectAuthorDisposable.set(nil)
            }))
            self.present(progressController, in: .window(.root), with: ViewControllerPresentationArguments(presentationAnimation: .modalSheet))

            self.nagramiXSelectAuthorDisposable.set((nagramiXMessagesByAuthor(account: self.context.account, peerId: peerId, authorId: authorId, threadId: threadId)
            |> afterDisposed { [weak progressController] in
                Queue.mainQueue().async {
                    progressController?.dismiss()
                }
            }
            |> deliverOnMainQueue).start(next: { [weak self, weak progressController] cloudIds in
                guard let self, self.nagramiXSelectAuthorGeneration == generation else { return }
                self.nagramiXIsSelectingAuthorMessages = false
                progressController?.dismiss()
                guard self.chatLocation.peerId == peerId, self.chatLocation.threadId == threadId else { return }
                let archivedIds = self.context.account.nagramiXMessageArchive.deletedMessages(peerId: peerId, threadId: threadId, minIndex: nil, maxIndex: nil, limit: Int.max).filter { $0.author?.id == authorId }.map { $0.id }
                let messageIds = Array(Set(cloudIds + archivedIds)).sorted()
                guard !messageIds.isEmpty else {
                    self.present(textAlertController(context: self.context, updatedPresentationData: self.updatedPresentationData, title: nil, text: self.presentationData.strings.nagramiXAuthorSelectionEmpty, actions: [TextAlertAction(type: .defaultAction, title: self.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
                    return
                }
                let _ = self.presentVoiceMessageDiscardAlert(action: { [weak self] in
                    guard let self, self.nagramiXSelectAuthorGeneration == generation, self.chatLocation.peerId == peerId, self.chatLocation.threadId == threadId else { return }
                    self.nagramiXSelectedAuthorMessageIds = Set(messageIds)
                    self.updateChatPresentationInterfaceState(animated: true, interactive: true, { state in
                        state.updatedInterfaceState { $0.withUpdatedSelectedMessages(messageIds) }.updatedShowCommands(false)
                    })
                }, alertAction: {}, delay: true)
            }, error: { [weak self, weak progressController] _ in
                guard let self, self.nagramiXSelectAuthorGeneration == generation else { return }
                self.nagramiXIsSelectingAuthorMessages = false
                progressController?.dismiss()
                guard self.chatLocation.peerId == peerId, self.chatLocation.threadId == threadId else { return }
                self.present(textAlertController(context: self.context, updatedPresentationData: self.updatedPresentationData, title: nil, text: self.presentationData.strings.nagramiXAuthorSelectionFailed, actions: [TextAlertAction(type: .defaultAction, title: self.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
            }))
        }, updateForwardOptionsState: { [weak self] f in
""",
        "Wire copy-as-new and loaded-author selection into ChatController",
    )

    replace_unique(
        chat_load_node,
        """                                    strongSelf.presentClearCacheSuggestion()
""",
        """                                    if strongSelf.nagramiXSelectedAuthorMessageIds == messageIds {
                                        strongSelf.present(textAlertController(context: strongSelf.context, updatedPresentationData: strongSelf.updatedPresentationData, title: nil, text: strongSelf.presentationData.strings.nagramiXAuthorDeleteUnavailable, actions: [
                                            TextAlertAction(type: .defaultAction, title: strongSelf.presentationData.strings.Common_OK, action: {}),
                                            TextAlertAction(type: .genericAction, title: strongSelf.presentationData.strings.ClearCache_FreeSpace, action: { [weak strongSelf] in
                                                strongSelf?.presentClearCacheSuggestion()
                                            })
                                        ], actionLayout: .vertical), in: .window(.root))
                                    } else {
                                        strongSelf.presentClearCacheSuggestion()
                                    }
""",
        "Explain a real deletion restriction only for a Select From Author selection",
    )

    context_menus = source / "submodules" / "TelegramUI" / "Sources" / "ChatInterfaceStateContextMenus.swift"
    replace_once(
        context_menus,
        "import AdsReportScreen\n",
        "import AdsReportScreen\nimport NagramiXCore\n",
        "NagramiX context menu localization import",
    )
    replace_once(
        context_menus,
        """        if (loggingSettings.logToFile || loggingSettings.logToConsole) && !downloadableMediaResourceInfos.isEmpty {
            actions.append(.action(ContextMenuActionItem(text: "Send Logs", icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Message"), color: theme.actionSheet.primaryTextColor)
            }, action: { _, f in
                triggerDebugSendLogsUI(context: context, additionalInfo: "User has requested download logs for \\(downloadableMediaResourceInfos)", pushController: { c in
                    controllerInteraction.navigationController()?.pushViewController(c)
                })
                f(.default)
            })))
        }
""",
        "",
        "Remove Send Logs from the user message context menu",
    )
    replace_once(
        context_menus,
        """                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuForward, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.forwardMessages(selectAll || isImage ? messages : [message])
                    f(.dismissWithoutContent)
                })))
""",
        """                let messagesToForward = selectAll || isImage ? messages : [message]
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.forwardMessages(messagesToForward)
                    f(.dismissWithoutContent)
                })))
                if NagramiXTabSettings.current.showForwardWithoutAuthor {
                    let canForwardWithoutAuthor = interfaceInteraction.copyMessagesWithoutSource != nil
                        && nagramiXCanCopyMessagesAsNew(messagesToForward)
                    actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, textColor: canForwardWithoutAuthor ? .primary : .disabled, icon: { _ in
                        return nil
                    }, iconAnimation: ContextMenuActionItem.IconAnimation(name: "message_preview_person_off"), action: !canForwardWithoutAuthor ? nil : { _, f in
                        interfaceInteraction.copyMessagesWithoutSource?(messagesToForward)
                        f(.dismissWithoutContent)
                    })))
                }
""",
        "Separate standard forwarding from safe copy-as-new sending",
    )

    chat_controller_forward_messages = source / "submodules" / "TelegramUI" / "Sources" / "ChatControllerForwardMessages.swift"
    replace_once(
        chat_controller_forward_messages,
        "extension ChatControllerImpl {\n",
        """enum NagramiXMessageTransferMode: Equatable {
    case forwardWithSource
    case copyAsNew
}

func nagramiXCanCopyMessagesAsNew(_ messages: [EngineRawMessage]) -> Bool {
    return nagramiXCopyMessagesAsNew(messages) != nil
}

private func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage]) -> [EnqueueMessage]? {
    guard !messages.isEmpty else {
        return nil
    }
    var result: [EnqueueMessage] = []
    var copiedGroupingKeys: [Int64: Int64] = [:]
    for message in messages {
        if message.id.peerId.namespace == Namespaces.Peer.SecretChat
            || message.isCopyProtected()
            || message.containsSecretMedia
            || message.media.contains(where: { $0 is TelegramMediaPaidContent || $0 is TelegramMediaExpiredContent }) {
            return nil
        }

        var attributes: [EngineMessage.Attribute] = []
        var inlineStickers: [EngineMedia.Id: EngineRawMedia] = [:]
        if let entities = message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute {
            attributes.append(TextEntitiesMessageAttribute(entities: entities.entities))
            for mediaId in entities.associatedMediaIds {
                if let media = message.associatedMedia[mediaId] {
                    inlineStickers[mediaId] = media
                }
            }
        }
        if message.attributes.contains(where: { $0 is MediaSpoilerMessageAttribute }) {
            attributes.append(MediaSpoilerMessageAttribute())
        }

        var mediaReference: AnyMediaReference?
        for media in message.media {
            if media is TelegramMediaWebpage {
                continue
            } else if mediaReference == nil && (media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaContact || media is TelegramMediaMap) {
                if message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
                    mediaReference = .standalone(media: media)
                } else {
                    mediaReference = .message(message: MessageReference(message), media: media)
                }
            } else {
                return nil
            }
        }
        if message.text.isEmpty && mediaReference == nil {
            return nil
        }

        var localGroupingKey: Int64?
        if let groupingKey = message.groupingKey {
            if let existing = copiedGroupingKeys[groupingKey] {
                localGroupingKey = existing
            } else {
                let generated = Int64.random(in: Int64.min ... Int64.max)
                copiedGroupingKeys[groupingKey] = generated
                localGroupingKey = generated
            }
        }
        result.append(.message(text: message.text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: localGroupingKey, correlationId: nil, bubbleUpEmojiOrStickersets: []))
    }
    return result
}

extension ChatControllerImpl {
""",
        "Add an explicit message transfer mode",
    )
    replace_once(
        chat_controller_forward_messages,
        "    func forwardMessages(messageIds: [EngineMessage.Id], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool = false) {\n",
        "    func forwardMessages(messageIds: [EngineMessage.Id], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool = false, transferMode: NagramiXMessageTransferMode = .forwardWithSource) {\n",
        "Accept the typed transfer mode",
    )
    replace_once(
        chat_controller_forward_messages,
        "            self?.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent)\n",
        "            self?.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent, transferMode: transferMode)\n",
        "Propagate the transfer mode after loading",
    )
    replace_once(
        chat_controller_forward_messages,
        "    func forwardMessages(messages: [EngineRawMessage], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool) {\n",
        "    func forwardMessages(messages: [EngineRawMessage], options: ChatInterfaceForwardOptionsState? = nil, resetCurrent: Bool, transferMode: NagramiXMessageTransferMode = .forwardWithSource) {\n",
        "Keep classic forwarding as the default",
    )
    replace_once(
        chat_controller_forward_messages,
        "            }, multipleSelection: true, forwardedMessageIds: messages.map { $0.id }, selectForumThreads: true))\n",
        "            }, multipleSelection: true, forwardedMessageIds: transferMode == .forwardWithSource ? messages.map { $0.id } : [], selectForumThreads: true))\n",
        "Keep forward-only picker metadata out of copy-as-new mode",
    )
    replace_once(
        chat_controller_forward_messages,
        """            var attemptSelectionImpl: ((EnginePeer, ChatListDisabledPeerReason) -> Void)?
            let controller = self.context.sharedContext.makePeerSelectionController(""",
        """            var attemptSelectionImpl: ((EnginePeer, ChatListDisabledPeerReason) -> Void)?
            var nagramiXCopyThreadIds: [EnginePeer.Id: Int64] = [:]
            let controller = self.context.sharedContext.makePeerSelectionController(""",
        "Preserve selected destination topics in copy-as-new mode",
    )
    replace_once(
        chat_controller_forward_messages,
        """                                for (peer, shouldDivert) in targetPeersShouldDivert {
                                    var peerMessages = result
                                    if shouldDivert {
""",
        """                                for (peer, shouldDivert) in targetPeersShouldDivert {
                                    var peerMessages = result
                                    if transferMode == .copyAsNew, let threadId = nagramiXCopyThreadIds[peer.id] {
                                        peerMessages = peerMessages.map { $0.withUpdatedThreadId(threadId) }
                                    }
                                    if shouldDivert {
""",
        "Apply only the destination thread id without copying any source reply",
    )
    replace_once(
        chat_controller_forward_messages,
        """                        var attributes: [EngineMessage.Attribute] = []
                        attributes.append(ForwardOptionsMessageAttribute(hideNames: forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true))
""" + "                        \n" + """                        result.append(contentsOf: messages.map { message -> EnqueueMessage in
                            return .forward(source: message.id, threadId: nil, grouping: .auto, attributes: attributes, correlationId: nil)
                        })
""",
        """                        switch transferMode {
                        case .forwardWithSource:
                            var attributes: [EngineMessage.Attribute] = []
                            attributes.append(ForwardOptionsMessageAttribute(hideNames: forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true))
                            result.append(contentsOf: messages.map { message -> EnqueueMessage in
                                return .forward(source: message.id, threadId: nil, grouping: .auto, attributes: attributes, correlationId: nil)
                            })
                        case .copyAsNew:
                            guard let copiedMessages = nagramiXCopyMessagesAsNew(messages) else {
                                return
                            }
                            result.append(contentsOf: copiedMessages)
                        }
""",
        "Build fresh messages without forward or reply metadata",
    )
    replace_once(
        chat_controller_forward_messages,
        """                let peerId = peer.id
                let accountPeerId = strongSelf.context.account.peerId
""" + "                \n" + """                if resetCurrent {
""",
        """                let peerId = peer.id
                let accountPeerId = strongSelf.context.account.peerId

                if transferMode == .copyAsNew {
                    if let threadId {
                        nagramiXCopyThreadIds[peer.id] = threadId
                    }
                    strongController.multiplePeersSelected?([peer], [peer.id: peer], NSAttributedString(string: ""), .generic, nil, nil)
                    return
                }

                if resetCurrent {
""",
        "Route single-destination copy mode through the real send-as-new commit path",
    )
    replace_once(
        context_menus,
        """            if messages.count > 1 {
""",
        """            if NagramiXTabSettings.current.showSelectByAuthor, let authorId = message.author?.id, interfaceInteraction.selectMessagesByAuthor != nil {
                if !actions.isEmpty && !didAddSeparator {
                    didAddSeparator = true
                    actions.append(.separator)
                }
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXSelectFromAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/SelectAll"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.selectMessagesByAuthor?(authorId)
                    f(.dismissWithoutContent)
                })))
            }

            if messages.count > 1 {
""",
        "Add Select by Author after the standard Select action",
    )

    peer_info_profile_items = source / "submodules" / "TelegramUI" / "Components" / "PeerInfo" / "PeerInfoScreen" / "Sources" / "PeerInfoProfileItems.swift"
    replace_once(
        peer_info_profile_items,
        "import BoostLevelIconComponent\n",
        "import BoostLevelIconComponent\nimport UndoUI\nimport NagramiXCore\n",
        "NagramiX profile metadata import",
    )
    replace_once(
        peer_info_profile_items,
        """private let enabledPrivateBioEntities: EnabledEntityTypes = [.internalUrl, .mention, .hashtag]
""",
        """private let enabledPrivateBioEntities: EnabledEntityTypes = [.internalUrl, .mention, .hashtag]

private func nagramiXCopyProfileId(_ value: Int64, presentationData: PresentationData, interaction: PeerInfoInteraction) {
    UIPasteboard.general.string = "\\(value)"
    interaction.getController()?.present(
        UndoOverlayController(
            presentationData: presentationData,
            content: .copy(text: presentationData.strings.nagramiXProfileIdCopied),
            elevatedLayout: false,
            animateInAsReplacement: false,
            action: { _ in false }
        ),
        in: .current
    )
}
""",
        "Copy profile IDs through the native Telegram confirmation overlay",
    )
    replace_once(
        peer_info_profile_items,
        "        let ItemCommunity = 10000\n",
        """        let ItemCommunity = 10000
        let ItemNagramiXProfileId = 11000
        let ItemNagramiXRegistration = 11001
        let ItemNagramiXMutualContact = 11002

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showMutualContactIcon,
           user.id != context.account.peerId,
           user.botInfo == nil,
           user.flags.contains(.mutualContact),
           !(user.firstName ?? "").isEmpty || !(user.lastName ?? "").isEmpty {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXMutualContact, label: presentationData.strings.Contacts_Title, text: "⇄ " + presentationData.strings.nagramiXMutualContact, textColor: .accent, action: nil, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(user.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(user.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
        if nagramiXSettings.showRegistrationDate {
            let year = NagramiXPeerMetadata.approximateRegistrationYear(peerId: user.id.id._internalGetInt64Value())
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXRegistration, label: presentationData.strings.nagramiXRegistrationDate, text: presentationData.strings.nagramiXApproximateRegistration(year), textColor: .primary, action: nil, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
""",
        "Show optional NagramiX user metadata",
    )
    replace_once(
        peer_info_profile_items,
        "        let ItemCommunity = 12\n",
        """        let ItemCommunity = 12
        let ItemNagramiXProfileId = 13

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(channel.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(channel.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
""",
        "Show optional NagramiX channel metadata",
    )
    replace_once(
        peer_info_profile_items,
        """    } else if case let .legacyGroup(group) = data.peer {
        if let cachedData = data.cachedData as? CachedGroupData {
""",
        """    } else if case let .legacyGroup(group) = data.peer {
        let ItemNagramiXProfileId = 1

        let nagramiXSettings = NagramiXTabSettings.current
        if nagramiXSettings.showProfileIds {
            items[currentPeerInfoSection]!.append(PeerInfoScreenLabeledValueItem(id: ItemNagramiXProfileId, label: presentationData.strings.nagramiXProfileId, text: "\\(group.id.id._internalGetInt64Value())", textColor: .accent, action: { _, _ in
                nagramiXCopyProfileId(group.id.id._internalGetInt64Value(), presentationData: presentationData, interaction: interaction)
            }, requestLayout: { animated in
                interaction.requestLayout(animated)
            }))
        }
        if let cachedData = data.cachedData as? CachedGroupData {
""",
        "Show optional NagramiX legacy-group metadata",
    )

    contacts_peer_item = source / "submodules" / "ContactsPeerItem" / "Sources" / "ContactsPeerItem.swift"
    contacts_peer_item_build = source / "submodules" / "ContactsPeerItem" / "BUILD"
    replace_once(contacts_peer_item, "import TelegramCore\n", "import TelegramCore\nimport NagramiXCore\n", "Read mutual-contact settings in native contact cells")
    replace_once(
        contacts_peer_item,
        "            let (titleLayout, titleApply) = makeTitleLayout(",
        """            if NagramiXTabSettings.current.showMutualContactIcon,
               case let .peer(peer, _) = item.peer,
               let peer,
               case let .user(user) = peer,
               peer.id != item.context.account.peerId,
               user.botInfo == nil,
               user.flags.contains(.mutualContact),
               !(user.firstName ?? "").isEmpty || !(user.lastName ?? "").isEmpty {
                if let originalStatus = statusAttributedString {
                    let mutualStatus = NSMutableAttributedString(string: "⇄ " + item.presentationData.strings.nagramiXMutualContact, font: statusFont, textColor: item.presentationData.theme.list.itemAccentColor)
                    if originalStatus.length > 0 {
                        mutualStatus.append(NSAttributedString(string: " · ", font: statusFont, textColor: item.presentationData.theme.list.itemSecondaryTextColor))
                        mutualStatus.append(originalStatus)
                    }
                    statusAttributedString = mutualStatus
                } else if let originalTitle = titleAttributedString {
                    // Pickers without a status keep their original row height.
                    let mutualTitle = NSMutableAttributedString(string: "⇄ ", font: titleBoldFont, textColor: item.presentationData.theme.list.itemAccentColor)
                    mutualTitle.append(originalTitle)
                    titleAttributedString = mutualTitle
                }
            }

            let (titleLayout, titleApply) = makeTitleLayout(""",
        "Show a readable mutual-contact status independently of title truncation",
    )
    replace_once(contacts_peer_item, "    private var peerPresenceManager: PeerPresenceStatusManager?\n", "    private var nagramiXMutualObserver: NSObjectProtocol?\n    private var nagramiXLastMutualEnabled = NagramiXTabSettings.current.showMutualContactIcon\n    private var peerPresenceManager: PeerPresenceStatusManager?\n", "Mutual-contact settings observer state")
    replace_once(
        contacts_peer_item,
        "        self.isAccessibilityElement = true\n",
        """        self.nagramiXMutualObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else { return }
            let enabled = NagramiXTabSettings.current.showMutualContactIcon
            guard enabled != self.nagramiXLastMutualEnabled else { return }
            self.nagramiXLastMutualEnabled = enabled
            guard let params = self.layoutParams else { return }
            let (_, apply) = self.asyncLayout()(params.0, params.1, params.2, params.3, params.4, params.5)
            let (_, applyNodes) = apply()
            applyNodes(false, false)
        })
        self.isAccessibilityElement = true
""",
        "Refresh bound contact cells immediately when preferences change",
    )
    replace_once(contacts_peer_item, "    override public func layoutForParams(", """    deinit {
        if let observer = self.nagramiXMutualObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    override public func layoutForParams(""", "Dispose mutual-contact cell observer")
    replace_once(contacts_peer_item_build, '        "//submodules/TelegramCore:TelegramCore",\n', '        "//submodules/TelegramCore:TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",\n', "Link mutual-contact cells with settings")

    replace_once(peer_info_screen, "import TelegramCore\n", "import TelegramCore\nimport NagramiXCore\n", "Read mutual-contact preference in profiles")
    replace_once(peer_info_screen, "    private var validLayout: (layout: ContainerViewLayout, navigationHeight: CGFloat)?\n", "    private var validLayout: (layout: ContainerViewLayout, navigationHeight: CGFloat)?\n    private var nagramiXMutualObserver: NSObjectProtocol?\n    private var nagramiXLastMutualEnabled = NagramiXTabSettings.current.showMutualContactIcon\n", "Profile mutual-contact observer state")
    replace_once(peer_info_screen, "        ), strings: baseNavigationBarPresentationData.strings))\n", """        ), strings: baseNavigationBarPresentationData.strings))
        self.nagramiXMutualObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else { return }
            let enabled = NagramiXTabSettings.current.showMutualContactIcon
            guard enabled != self.nagramiXLastMutualEnabled else { return }
            self.nagramiXLastMutualEnabled = enabled
            guard self.isNodeLoaded, let (layout, navigationHeight) = self.validLayout else { return }
            self.controllerNode.containerLayoutUpdated(layout: layout, navigationHeight: navigationHeight, transition: .immediate)
        })
""", "Refresh profile contact metadata when settings change")
    replace_once(peer_info_screen, "        self.readyInternalDisposable?.dispose()\n", """        if let observer = self.nagramiXMutualObserver {
            NotificationCenter.default.removeObserver(observer)
        }
        self.readyInternalDisposable?.dispose()
""", "Dispose profile mutual-contact observer")

    account_utils = source / "submodules" / "AccountUtils" / "Sources" / "AccountUtils.swift"
    replace_once(
        account_utils,
        "public let maximumNumberOfAccounts = 3\n",
        "public let maximumNumberOfAccounts = 5\n",
        "Allow up to five native Telegram accounts",
    )

    account_context = source / "submodules" / "TelegramUI" / "Sources" / "AccountContext.swift"
    replace_once(
        account_context,
        "import DirectMediaImageCache\n",
        "import DirectMediaImageCache\nimport NagramiXCore\n",
        "Outgoing call confirmation settings import",
    )
    replace_once(
        account_context,
        """    public func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void) {
        guard let callResult = self.sharedContext.callManager?.requestCall(context: self, peerId: peerId, isVideo: isVideo, endCurrentIfAny: false) else {
""",
        """    public func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void) {
        self.requestCall(peerId: peerId, isVideo: isVideo, completion: completion, skipNagramiXConfirmation: false)
    }

    private func requestCall(peerId: PeerId, isVideo: Bool, completion: @escaping () -> Void, skipNagramiXConfirmation: Bool) {
        if NagramiXTabSettings.current.confirmOutgoingCalls && !skipNagramiXConfirmation {
            let presentationData = self.sharedContext.currentPresentationData.with { $0 }
            self.sharedContext.mainWindow?.present(textAlertController(
                context: self,
                title: presentationData.strings.nagramiXCallConfirmationTitle,
                text: presentationData.strings.nagramiXCallConfirmationText,
                actions: [
                    TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_Cancel, action: {}),
                    TextAlertAction(type: .genericAction, title: presentationData.strings.nagramiXCallAction, action: { [weak self] in
                        self?.requestCall(peerId: peerId, isVideo: isVideo, completion: completion, skipNagramiXConfirmation: true)
                    }),
                ]
            ), on: .root)
            return
        }
        guard let callResult = self.sharedContext.callManager?.requestCall(context: self, peerId: peerId, isVideo: isVideo, endCurrentIfAny: false) else {
""",
        "Confirm native outgoing calls before starting them",
    )

    archived_context_source = source / "submodules" / "TelegramUI" / "Sources" / "ChatMessageContextControllerContentSource.swift"
    replace_unique(
        archived_context_source,
        """        if self.message.adAttribute != nil {
            return .single(false)
        }
        if let chatController = self.chatController, case .customChatContents = chatController.subject {
""",
        """        if self.message._asMessage().attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }), let chatController = self.chatController {
            let archive = chatController.context.account.nagramiXMessageArchive
            let messageId = self.message.id
            return archive.updates
            |> map { _ in archive.deletedMessage(id: messageId) == nil }
            |> distinctUntilChanged
        }
        if self.message.adAttribute != nil {
            return .single(false)
        }
        if let chatController = self.chatController, case .customChatContents = chatController.subject {
""",
        "Keep archived-message context extraction alive while its local snapshot exists",
    )

    message_archive_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXMessageArchive.swift"
    message_archive_target = source / "submodules" / "TelegramCore" / "Sources" / "Utils" / message_archive_overlay.name
    shutil.copy2(message_archive_overlay, message_archive_target)
    archived_media_overlay = overlay / "Sources" / "TelegramCore" / "NagramiXArchivedMediaStore.swift"
    shutil.copy2(archived_media_overlay, message_archive_target.with_name(archived_media_overlay.name))

    replace_unique(
        account_source,
        """    public let supplementary: Bool
    public let isSupportUser: Bool
    public let postbox: Postbox
    public let network: Network
""",
        """    public let supplementary: Bool
    public let isSupportUser: Bool
    public let postbox: Postbox
    public let nagramiXMessageArchive: NagramiXMessageArchive
    public let network: Network
""",
        "Account-owned NagramiX message archive",
    )
    replace_unique(
        account_source,
        """        self.networkArguments = networkArguments
        self.peerId = peerId
""" + "        \n" + """        self.auxiliaryMethods = auxiliaryMethods
""",
        """        self.networkArguments = networkArguments
        self.peerId = peerId
        self.nagramiXMessageArchive = NagramiXMessageArchive(postbox: postbox, accountPeerId: peerId, basePath: basePath)
""" + "        \n" + """        self.auxiliaryMethods = auxiliaryMethods
""",
        "Initialize the per-account local message archive",
    )

    state_management = source / "submodules" / "TelegramCore" / "Sources" / "State" / "AccountStateManagementUtils.swift"
    replace_unique(
        state_management,
        """                let _ = transaction.addMessages(messages, location: location)
                if case .UpperHistoryBlock = location {
""",
        """                let _ = transaction.addMessages(messages, location: location)
                if let messageArchive = NagramiXMessageArchive.forPostbox(postbox) {
                    for message in messages {
                        var archivePeers: [PeerId: Peer] = [:]
                        var archivePeerIds = Set<PeerId>([message.id.peerId])
                        if let authorId = message.authorId {
                            archivePeerIds.insert(authorId)
                        }
                        for media in message.media {
                            archivePeerIds.formUnion(media.peerIds)
                        }
                        for peerId in archivePeerIds {
                            if let peer = transaction.getPeer(peerId) {
                                archivePeers[peerId] = peer
                            }
                        }
                        messageArchive.captureIncoming(message, peers: archivePeers)
                    }
                }
                if case .UpperHistoryBlock = location {
""",
        "Capture incoming messages after native Postbox insertion",
    )
    replace_unique(
        state_management,
        """                    let peers: [PeerId:Peer] = previousMessage.peers.reduce([:], { current, value in
                        var current = current
                        current[value.0] = value.1
                        return current
                    })
""" + "                    \n" + """                    if previousMessage.text == message.text {
""",
        """                    let peers: [PeerId:Peer] = previousMessage.peers.reduce([:], { current, value in
                        var current = current
                        current[value.0] = value.1
                        return current
                    })
                    NagramiXMessageArchive.forPostbox(postbox)?.recordIncomingEdit(previousMessage: previousMessage, replacementMessage: message, peers: peers, receivedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
""" + "                    \n" + """                    if previousMessage.text == message.text {
""",
        "Store the previous received content before applying an edit",
    )
    replace_unique(
        state_management,
        """            case let .DeleteMessagesWithGlobalIds(ids):
                var resourceIds: [MediaResourceId] = []
""",
        """            case let .DeleteMessagesWithGlobalIds(ids):
                NagramiXMessageArchive.forPostbox(postbox)?.archiveServerDeletion(globalIds: ids, deletedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
                var resourceIds: [MediaResourceId] = []
""",
        "Archive non-channel server deletions before native removal",
    )
    replace_unique(
        state_management,
        """            case let .DeleteMessages(ids):
                _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
""",
        """            case let .DeleteMessages(ids):
                NagramiXMessageArchive.forPostbox(postbox)?.archiveServerDeletion(messageIds: ids, deletedAt: Int32(CFAbsoluteTimeGetCurrent() + kCFAbsoluteTimeIntervalSince1970))
                _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
""",
        "Archive channel server deletions before native removal",
    )

    interactive_delete = source / "submodules" / "TelegramCore" / "Sources" / "TelegramEngine" / "Messages" / "DeleteMessagesInteractively.swift"
    replace_unique(
        interactive_delete,
        """    _internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: messageIds.map(\\.messageId))
""",
        """    NagramiXMessageArchive.forPostbox(postbox)?.removeLocal(messageIds: messageIds.map(\\.messageId))
    _internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: messageIds.map(\\.messageId))
""",
        "Respect explicit local deletion of every expanded message/group id",
    )
    replace_unique(
        interactive_delete,
        """func _internal_clearHistoryInRangeInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, minTimestamp: Int32, maxTimestamp: Int32, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
""",
        """func _internal_clearHistoryInRangeInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, minTimestamp: Int32, maxTimestamp: Int32, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    NagramiXMessageArchive.forPostbox(postbox)?.clear(peerId: peerId)
    return postbox.transaction { transaction -> Void in
""",
        "Clear the local archive with an interactive range clear",
    )
    replace_unique(
        interactive_delete,
        """func _internal_clearHistoryInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    return postbox.transaction { transaction -> Void in
""",
        """func _internal_clearHistoryInteractively(postbox: Postbox, peerId: PeerId, threadId: Int64?, type: InteractiveHistoryClearingType) -> Signal<Void, NoError> {
    NagramiXMessageArchive.forPostbox(postbox)?.clear(peerId: peerId)
    return postbox.transaction { transaction -> Void in
""",
        "Clear the local archive with an interactive history clear",
    )

    chat_history_list = source / "submodules" / "TelegramUI" / "Sources" / "ChatHistoryListNode.swift"
    replace_unique(
        chat_history_list,
        """        let previousView = self.previousView
        let automaticDownloadNetworkType = context.account.networkType
""",
        """        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates)
        |> map { update, _ in
            return update
        }

        let previousView = self.previousView
        let automaticDownloadNetworkType = context.account.networkType
""",
        "Refresh an open chat when its local archive changes",
    )

    chat_history_entries = source / "submodules" / "TelegramUI" / "Sources" / "ChatHistoryEntriesForView.swift"
    replace_unique(
        chat_history_entries,
        """    var count = 0
    loop: for entry in view.entries {
""",
        """    var sourceEntries = view.entries
    if let peerId = location.peerId {
        let existingIds = Set(sourceEntries.map { $0.message.id })
        let firstIndex = sourceEntries.first?.message.index
        let lastIndex = sourceEntries.last?.message.index
        let archivedMessages = context.account.nagramiXMessageArchive.deletedMessages(
            peerId: peerId,
            threadId: location.threadId,
            minIndex: view.earlierId == nil ? nil : firstIndex,
            maxIndex: view.laterId == nil ? nil : lastIndex
        )
        for message in archivedMessages where !existingIds.contains(message.id) {
            let withinEarlierBoundary = firstIndex.map { message.index >= $0 || view.earlierId == nil } ?? true
            let withinLaterBoundary = lastIndex.map { message.index <= $0 || view.laterId == nil } ?? true
            if withinEarlierBoundary && withinLaterBoundary {
                sourceEntries.append(MessageHistoryEntry(message: message, isRead: true, location: nil, monthLocation: nil, attributes: MutableMessageHistoryEntryAttributes(authorIsContact: false)))
            }
        }
        sourceEntries.sort(by: { $0.message.index < $1.message.index })
    }

    var count = 0
    loop: for entry in sourceEntries {
""",
        "Inject display-only deleted snapshots into the open history range",
    )

    context_menus = source / "submodules" / "TelegramUI" / "Sources" / "ChatInterfaceStateContextMenus.swift"
    replace_unique(
        context_menus,
        "import NagramiXCore\n",
        "import NagramiXCore\nimport AlertUI\nimport TextFormat\nimport ChatInterfaceState\n",
        "Edit-history alert imports",
    )
    replace_unique(
        context_menus,
        """        return ContextController.Items(content: .list(actions), tip: nil)
""",
        """        let currentEntities = message.textEntitiesAttribute?.entities ?? []
        let archivedAttribute = message.attributes.first(where: { $0 is NagramiXArchivedMessageAttribute }) as? NagramiXArchivedMessageAttribute
        let editHistory = context.account.nagramiXMessageArchive.revisions(messageId: message.id, currentText: message.text, currentEntities: currentEntities)
        let editHistoryAction: ContextMenuItem?
        if !editHistory.isEmpty {
            editHistoryAction = .action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXEditHistory, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Edit"), color: theme.actionSheet.primaryTextColor)
            }, action: { c, _ in
                c?.dismiss(completion: {
                    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
                    let title = NSAttributedString(string: presentationData.strings.nagramiXEditHistory, font: Font.semibold(presentationData.listsFontSize.baseDisplaySize), textColor: presentationData.theme.actionSheet.primaryTextColor, paragraphAlignment: .center)
                    let body = NSMutableAttributedString()
                    let formatter = DateFormatter()
                    formatter.locale = Locale.current
                    formatter.dateStyle = .short
                    formatter.timeStyle = .short
                    for i in 0 ..< editHistory.count {
                        if i != 0 {
                            body.append(NSAttributedString(string: "\\n\\n"))
                        }
                        let date = formatter.string(from: Date(timeIntervalSince1970: TimeInterval(editHistory[i].timestamp)))
                        let label = i == 0 ? presentationData.strings.nagramiXOriginalVersion + " · " + date : (i == editHistory.count - 1 ? presentationData.strings.nagramiXCurrentVersion + " · " + date : date)
                        body.append(NSAttributedString(string: label + "\\n", font: Font.semibold(13.0), textColor: presentationData.theme.actionSheet.controlAccentColor))
                        body.append(stringWithAppliedEntities(editHistory[i].text, entities: editHistory[i].entities, baseColor: presentationData.theme.actionSheet.primaryTextColor, linkColor: presentationData.theme.actionSheet.controlAccentColor, baseFont: Font.regular(15.0), linkFont: Font.regular(15.0), boldFont: Font.semibold(15.0), italicFont: Font.italic(15.0), boldItalicFont: Font.semiboldItalic(15.0), fixedFont: Font.monospace(15.0), blockQuoteFont: Font.regular(15.0), message: nil))
                    }
                    controllerInteraction.presentController(richTextAlertController(context: context, title: title, text: body, actions: [TextAlertAction(type: .defaultAction, title: presentationData.strings.Common_OK, action: {})]), nil)
                })
            }))
            if let editHistoryAction {
                actions.append(editHistoryAction)
            }
        } else {
            editHistoryAction = nil
        }
        if archivedAttribute != nil {
            actions.removeAll()
            if !message.text.isEmpty {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuCopy, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Copy"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    storeMessageTextInPasteboard(message.text, entities: currentEntities)
                    f(.default)
                })))
            }
            if data.canReply, !message.text.isEmpty {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXReplyWithQuote, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Reply"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    interfaceInteraction.updateTextInputStateAndMode { inputState, _ in
                        let text = NSMutableAttributedString(string: "«" + message.text + "»\\n\\n")
                        text.append(inputState.inputText)
                        return (ChatTextInputState(inputText: text, selectionRange: text.length ..< text.length), .text)
                    }
                    f(.dismissWithoutContent)
                })))
            }
            actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXEditLocalCopy, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Edit"), color: theme.actionSheet.primaryTextColor)
            }, action: { c, _ in
                c?.dismiss(completion: {
                    nagramiXEditArchivedMessage(context: context, message: message, present: { controller in
                        controllerInteraction.presentController(controller, nil)
                    })
                })
            })))
            if NagramiXTabSettings.current.showForwardWithoutAuthor, nagramiXCanCopyMessagesAsNew([message]), let copyMessagesWithoutSource = interfaceInteraction.copyMessagesWithoutSource {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    copyMessagesWithoutSource(selectAll ? messages : [message])
                    f(.dismissWithoutContent)
                })))
            }
            if let editHistoryAction {
                actions.append(editHistoryAction)
            }
            actions.append(.separator)
            actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuSelect, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Select"), color: theme.actionSheet.primaryTextColor)
            }, action: { _, f in
                interfaceInteraction.beginMessageSelection(selectAll ? messages.map { $0.id } : [message.id], { transition in f(.custom(transition)) })
            })))
            if NagramiXTabSettings.current.showSelectByAuthor, let authorId = message.author?.id, let selectMessagesByAuthor = interfaceInteraction.selectMessagesByAuthor {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXSelectFromAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/SelectAll"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    selectMessagesByAuthor(authorId)
                    f(.dismissWithoutContent)
                })))
            }
            actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuDelete, textColor: .destructive, icon: { theme in
                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Delete"), color: theme.actionSheet.destructiveActionTextColor)
            }, action: { _, f in
                context.account.nagramiXMessageArchive.removeLocal(messageIds: [message.id])
                f(.dismissWithoutContent)
            })))
        }
        return ContextController.Items(content: .list(actions), tip: nil)
""",
        "Expose functional archived-message actions without calling deleted server originals",
    )

    replace_unique(
        chat_controller_forward_messages,
        """            let sortedMessages = messages.values.compactMap { $0?._asMessage() }.sorted { lhs, rhs in
                return lhs.id < rhs.id
            }
            self?.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent, transferMode: transferMode)
""",
        """            guard let self else { return }
            let sortedMessages = messageIds.compactMap { id -> EngineRawMessage? in
                return (messages[id] ?? nil)?._asMessage() ?? self.context.account.nagramiXMessageArchive.deletedMessage(id: id)
            }.sorted { $0.id < $1.id }
            let hasArchivedMessages = sortedMessages.contains(where: { $0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) })
            // Telegram cannot forward IDs that were already deleted remotely.
            self.forwardMessages(messages: sortedMessages, options: options, resetCurrent: resetCurrent, transferMode: hasArchivedMessages ? .copyAsNew : transferMode)
""",
        "Resolve selected archived snapshots locally before copy-as-new transfer",
    )
    replace_unique(
        chat_load_node,
        """                if let messageIds = strongSelf.presentationInterfaceState.interfaceState.selectionState?.selectedIds, !messageIds.isEmpty {
                    strongSelf.messageContextDisposable.set((strongSelf.context.sharedContext.chatAvailableMessageActions""",
        """                if let messageIds = strongSelf.presentationInterfaceState.interfaceState.selectionState?.selectedIds, !messageIds.isEmpty {
                    if messageIds.allSatisfy({ strongSelf.context.account.nagramiXMessageArchive.deletedMessage(id: $0) != nil }) {
                        strongSelf.context.account.nagramiXMessageArchive.removeLocal(messageIds: Array(messageIds))
                        strongSelf.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                        return
                    }
                    strongSelf.messageContextDisposable.set((strongSelf.context.sharedContext.chatAvailableMessageActions""",
        "Delete an archive-only selection from the local archive",
    )

    archived_selection_panel = source / "submodules" / "TelegramUI" / "Components" / "Chat" / "ChatMessageSelectionInputPanelNode" / "Sources" / "ChatMessageSelectionInputPanelNode.swift"
    replace_unique(
        archived_selection_panel,
        """        if let actions = self.actions {
            self.deleteButton.isEnabled = false
""",
        """        let archiveOnlySelection = !self.selectedMessages.isEmpty && self.context.map { context in
            self.selectedMessages.allSatisfy { context.account.nagramiXMessageArchive.deletedMessage(id: $0) != nil }
        } == true
        if let actions = self.actions {
            self.deleteButton.isEnabled = false
""",
        "Recognize local archived selections in the native selection toolbar",
    )
    replace_unique(
        archived_selection_panel,
        "            self.forwardButton.isImplicitlyDisabled = !actions.options.contains(.forward)\n",
        "            self.forwardButton.isImplicitlyDisabled = !archiveOnlySelection && !actions.options.contains(.forward)\n",
        "Enable copy transfer for an archived selection",
    )
    replace_unique(
        archived_selection_panel,
        """            self.shareButton.isImplicitlyDisabled = actions.options.intersection(.forward).isEmpty || actions.options.intersection(.externalShare).isEmpty
""",
        """            if archiveOnlySelection {
                self.deleteButton.isEnabled = true
            }
            self.shareButton.isImplicitlyDisabled = actions.options.intersection(.forward).isEmpty || actions.options.intersection(.externalShare).isEmpty
""",
        "Enable local deletion for an archived selection",
    )

    apply_media_controls(source, overlay)
    apply_compact_chat_list(source)
    apply_archived_media_resources(source)
    apply_archived_media_playback(source)
    apply_copy_send_options(source)
    apply_video_playback_options(source)

    if stock_section not in item_list_controller.read_text(encoding="utf-8"):
        raise SystemExit("NagramiX overlay modified Telegram's stock sectionControl branch")

    for name, original in stock_appearance.items():
        expected = compatible_theme_sources.get(name, original)
        if (source / name).read_bytes() != expected:
            raise SystemExit(f"NagramiX overlay modified protected stock Telegram appearance: {name}")

    print("Applied isolated NagramiX feature overlay; stock palettes preserved, cloud accent/variant compatibility applied")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telegram-dir", required=True, type=Path, help="Path to a clean Telegram-iOS 12.9.2 checkout")
    arguments = parser.parse_args()
    apply_features(arguments.telegram_dir.resolve())

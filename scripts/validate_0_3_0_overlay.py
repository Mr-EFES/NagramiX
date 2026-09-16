#!/usr/bin/env python3
"""Validate the generated source contracts required for the 0.3.0 candidate."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(path: Path, snippets: list[str]) -> None:
    if not path.is_file():
        raise SystemExit(f"required generated source is missing: {path}")
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in text:
            raise SystemExit(f"{path}: required 0.3.0 contract is missing: {snippet!r}")


def forbid(path: Path, snippets: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet in text:
            raise SystemExit(f"{path}: forbidden obsolete 0.3.0 path remains: {snippet!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="post-overlay Telegram-iOS checkout")
    args = parser.parse_args()
    source = args.source.resolve()

    require(
        source / "submodules/AuthorizationUI/Sources/AuthorizationSequenceSplashController.swift",
        ['chooseLanguageString: "Выбрать язык"', 'chooseLanguageOtherString: "Другие языки"', 'englishLanguageNameString: "English"'],
    )
    require(
        source / "submodules/AuthorizationUI/Sources/AuthorizationSequenceSplashController.swift",
        ['self?.activateLocalization("ru")', "downloadAndApplyLocalization", 'return ""'],
    )
    require(
        source / "submodules/TelegramPresentationData/Sources/DefaultPresentationStrings.swift",
        ['languageCode: "ru"', 'localizedName: "Русский"', 'forLocalization: "ru"'],
    )
    require(
        source / "submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift",
        [
            "PresentationThemeSettings(theme: .builtin(.nightAccent)",
            "trigger: .system, theme: .builtin(.nightAccent)",
        ],
    )
    require(
        source / "submodules/TelegramPresentationData/Sources/PresentationData.swift",
        ["theme: defaultDarkTintedPresentationTheme", "chatWallpaper: defaultDarkTintedPresentationTheme.chat.defaultWallpaper"],
    )
    require(
        source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
        ["var selectedMessageIds = Set<EngineMessage.Id>()", "selectedMessageIds.insert(message.id)", "selectedMessageIds.sorted()"],
    )
    copy_flow = source / "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift"
    require(copy_flow, [
        "multipleSelection: transferMode == .forwardWithSource",
        "nagramiXOpenCopyComposer(messages: messages, peer: peer, threadId: threadId, picker: strongController)",
        ".withUpdatedComposeInputState(inputState)",
        "controller.nagramiXCopyMessagesWithoutSource = messages",
        "chatController.ready.get()",
        "proceed(ChatControllerImpl(context: self.context, chatLocation: .peer(id: peer.id), initialTextInputState: inputState))",
    ])
    forbid(copy_flow, [
        "strongController.multiplePeersSelected?([peer]",
    ])
    require(
        source / "submodules/TelegramUI/Sources/ChatControllerNode.swift",
        [
            "if self.chatPresentationInterfaceState.interfaceState.forwardMessageIds != nil, let copyMessages = self.controller?.nagramiXCopyMessagesWithoutSource",
            "nagramiXCopyMessagesAsNew(copyMessages, replacingText: effectiveInputText, threadId: self.chatLocation.threadId)",
            "self.sendMessages(messages, silentPosting, scheduleTime, repeatPeriod",
            "self.controller?.nagramiXCopyMessagesWithoutSource = nil",
            "let isNagramiXCopy = strongSelf.controller?.nagramiXCopyMessagesWithoutSource != nil",
            "state = state.withUpdatedComposeInputState(ChatTextInputState(inputText: NSAttributedString(string: \"\")))",
        ],
    )
    require(
        source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
        [
            "let isNagramiXCopy = self.nagramiXCopyMessagesWithoutSource != nil",
            "self.nagramiXCopyMessagesWithoutSource = nil",
        ],
    )
    require(
        source / "submodules/TelegramUI/Sources/Chat/ChatMessageDisplaySendMessageOptions.swift",
        [
            "canSendWhenOnline: sendWhenOnlineAvailable",
            "case .whenOnline:",
            "scheduleTime: scheduleWhenOnlineTimestamp",
        ],
    )
    story_container = source / "submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/StoryContainerScreen.swift"
    require(story_container, ["UIBlurEffect(style: .dark)", "blurred: true"])
    if story_container.read_text(encoding="utf-8").count("blurred: true") < 2:
        raise SystemExit(f"{story_container}: every story confirmation entry path must request a blurred preview")
    bubble_source = source / "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"
    require(
        bubble_source,
        [
            "firstMessage.peers[firstMessage.id.peerId] as? TelegramChannel",
            "case .broadcast = channel.info",
            "allowFullWidth = true",
            "maxContentWidth = max(maxContentWidth, maximumNodeWidth)",
            "let availableMosaicWidth = maximumContentWidth",
            "maxSize = CGSize(width: availableMosaicWidth",
        ],
    )
    require(
        source / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoProfileItems.swift",
        [
            "user.flags.contains(.mutualContact)",
            "presentationData.strings.nagramiXMutualContact",
            "ItemNagramiXMutualContact",
        ],
    )
    require(
        source / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift",
        ["as? Bool ?? true", "[15, 30, 60].contains"],
    )
    require(
        source / "submodules/TelegramCore/Sources/Network/NagramiXProxyFailoverController.swift",
        ["case .connecting = self.status", "self.checkAvailableCandidate", "MTProxyConnectivity.pingProxy"],
    )

    print("0.3.3 generated overlay contracts validated")


if __name__ == "__main__":
    main()

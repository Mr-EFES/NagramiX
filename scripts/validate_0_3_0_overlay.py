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
        ['self?.activateLocalization("ru")', "downloadAndApplyLocalization", 'return "ru"'],
    )
    require(
        source / "submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift",
        ["PresentationThemeSettings(theme: .builtin(.nightAccent)"],
    )
    require(
        source / "submodules/TelegramPresentationData/Sources/PresentationData.swift",
        ["theme: defaultDarkTintedPresentationTheme", "chatWallpaper: defaultDarkTintedPresentationTheme.chat.defaultWallpaper"],
    )
    require(
        source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
        ["var selectedMessageIds = Set<EngineMessage.Id>()", "selectedMessageIds.insert(message.id)", "selectedMessageIds.sorted()"],
    )
    require(
        source / "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift",
        ["forwardedMessageIds: messages.map { $0.id }", "case .silent:", "case .schedule:", "case .whenOnline:"],
    )
    require(
        source / "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift",
        ["nagramiXWideChannelPost", "allowFullWidth = true", "maxContentWidth = max(maxContentWidth, maximumNodeWidth)"],
    )
    require(
        source / "submodules/NagramiXCore/Sources/NagramiXTabSettings.swift",
        ["as? Bool ?? true", "[15, 30, 60].contains"],
    )
    require(
        source / "submodules/TelegramCore/Sources/Network/NagramiXProxyFailoverController.swift",
        ["case .connecting = self.status", "self.checkAvailableCandidate", "MTProxyConnectivity.pingProxy"],
    )

    print("0.3.0 generated overlay contracts validated")


if __name__ == "__main__":
    main()

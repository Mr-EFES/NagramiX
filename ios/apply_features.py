#!/usr/bin/env python3
"""Apply the isolated NagramiX next-version feature overlay."""

from __future__ import annotations

import json
import hashlib
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



def apply_unread_chats_first(source: Path, overlay: Path) -> None:
    # Telegram 13.0 plus all preceding audited overlays. Validate all inputs
    # and anchors before writing any of this feature's native changes.
    expected = {'submodules/ChatListUI/Sources/Node/ChatListNode.swift': 'daef211e884e4d9528c87915c4ecf6ecfe3966ad7f608322c21cae424dcc46aa', 'submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift': '8a3a081940b253796b6d5676ab57b97a1ca32ebb22c6edc723c6a14f69604a98', 'submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift': '2a4c733b9647c28672e0d81a8d2e80ab6ae3b2fb3a69bac9d478c3d959c76204', 'submodules/ChatListUI/Sources/Node/ChatListViewTransition.swift': '0fd12bfb3b5460f80e623c79dbd7bebb2e788cef8baa8b5f6c65a5b3c45ec561'}
    texts = {}
    for name, digest in expected.items():
        path = source / name
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit(f"Changed unread-chat sorting input or already patched: {name}")
        texts[name] = data.decode("utf-8")

    def patch(name: str, old: str, new: str) -> None:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Unread-chat sorting anchor drift: {name}: {old!r}")
        texts[name] = texts[name].replace(old, new)

    node = "submodules/ChatListUI/Sources/Node/ChatListNode.swift"
    entries = "submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift"
    location = "submodules/ChatListUI/Sources/Node/ChatListNodeLocation.swift"
    transition = "submodules/ChatListUI/Sources/Node/ChatListViewTransition.swift"
    patch(location, '    public let list: EngineChatList\n', '    public let nagramiXUnreadChatsFirst: Bool\n    public let list: EngineChatList\n')
    patch(location, 'scrollPosition: ChatListNodeViewScrollPosition?) {', 'scrollPosition: ChatListNodeViewScrollPosition?, nagramiXUnreadChatsFirst: Bool = false) {')
    patch(location, '        self.list = list\n', '        self.nagramiXUnreadChatsFirst = nagramiXUnreadChatsFirst\n        self.list = list\n')
    patch(entries, '    struct PeerEntryData: Equatable {\n        var index: EngineChatList.Item.Index\n', '    struct PeerEntryData: Equatable {\n        var nagramiXUnreadCount: Int? = nil\n        var index: EngineChatList.Item.Index\n')
    patch(entries, '            if lhs.readState != rhs.readState {', '            if lhs.nagramiXUnreadCount != rhs.nagramiXUnreadCount {\n                return false\n            }\n            if lhs.readState != rhs.readState {')
    patch(entries, '        return lhs.sortIndex < rhs.sortIndex\n', '        if case let .PeerEntry(left) = lhs, case let .PeerEntry(right) = rhs,\n           case let .chatList(leftIndex) = left.index, case let .chatList(rightIndex) = right.index,\n           leftIndex.pinningIndex == nil, rightIndex.pinningIndex == nil,\n           left.promoInfo == nil, right.promoInfo == nil {\n            let leftCount = left.nagramiXUnreadCount ?? 0\n            let rightCount = right.nagramiXUnreadCount ?? 0\n            if leftCount != rightCount {\n                return leftCount < rightCount // UI displays this ascending list in reverse.\n            }\n        }\n        return lhs.sortIndex < rhs.sortIndex\n')
    patch(node, '    private var nagramiXCompactObserver: NSObjectProtocol?\n', '    private var nagramiXUnreadObserver: NSObjectProtocol?\n    private let nagramiXUnreadChatsFirst = ValuePromise<Bool>(NagramiXTabSettings.unreadChatsFirstEnabled, ignoreRepeated: true)\n    private var nagramiXCompactObserver: NSObjectProtocol?\n')
    patch(node, '        self.nagramiXCompactObserver = NotificationCenter.default.addObserver', '        self.nagramiXUnreadObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.unreadChatsFirstChangedNotification, object: nil, queue: .main, using: { [weak self] _ in\n            self?.nagramiXRefreshSettings()\n        })\n        self.nagramiXCompactObserver = NotificationCenter.default.addObserver')
    patch(node, '    public func nagramiXRefreshSettings() {\n', '    public func nagramiXRefreshSettings() {\n        self.nagramiXUnreadChatsFirst.set(NagramiXTabSettings.unreadChatsFirstEnabled)\n')
    patch(node, '        if let observer = self.nagramiXCompactObserver {', '        if let observer = self.nagramiXUnreadObserver {\n            NotificationCenter.default.removeObserver(observer)\n        }\n        if let observer = self.nagramiXCompactObserver {')
    patch(node, '        let chatListViewUpdate = self.chatListLocation.get()\n        |> distinctUntilChanged\n        |> mapToSignal { listLocation -> Signal<(ChatListNodeViewUpdate, ChatListFilter?), NoError> in\n            return chatListViewForLocation(chatListLocation: location, location: listLocation, account: context.account, shouldLoadCanMessagePeer: shouldLoadCanMessagePeer)\n', '        let chatListViewUpdate = combineLatest(self.chatListLocation.get() |> distinctUntilChanged, self.nagramiXUnreadChatsFirst.get())\n        |> mapToSignal { listLocation, unreadFirst -> Signal<(ChatListNodeViewUpdate, ChatListFilter?), NoError> in\n            let signal: Signal<ChatListNodeViewUpdate, NoError>\n            if unreadFirst, case .chatList = mode, case .chatList = location {\n                signal = nagramiXUnreadChatListView(chatListLocation: location, location: listLocation, account: context.account)\n            } else {\n                signal = chatListViewForLocation(chatListLocation: location, location: listLocation, account: context.account, shouldLoadCanMessagePeer: shouldLoadCanMessagePeer)\n            }\n            return signal\n')
    patch(transition, 'struct ChatListNodeView {\n', 'struct ChatListNodeView {\n    var nagramiXUnreadChatsFirst: Bool = false\n')
    patch(node, '            let processedView = ChatListNodeView(originalList:', '            if update.nagramiXUnreadChatsFirst {\n                nagramiXSortUnreadChatListEntries(&entries)\n            }\n            let processedView = ChatListNodeView(originalList:')
    patch(node, 'ChatListNodeView(originalList: update.list, filteredEntries: entries, isLoading: isLoading, filter: filter)', 'ChatListNodeView(nagramiXUnreadChatsFirst: update.nagramiXUnreadChatsFirst, originalList: update.list, filteredEntries: entries, isLoading: isLoading, filter: filter)')
    patch(node, '                    if let location = location, location != strongSelf.currentLocation {', '                    if let location = location, location != strongSelf.currentLocation, !chatListView.nagramiXUnreadChatsFirst {')
    patch(transition, '                var index = toView.filteredEntries.count - 1\n                for entry in toView.filteredEntries {\n                    if entry.sortIndex >= .index(.chatList(scrollIndex)) {', '                if toView.nagramiXUnreadChatsFirst, let exactIndex = toView.filteredEntries.firstIndex(where: { $0.sortIndex == .index(.chatList(scrollIndex)) }) {\n                    scrollToItem = ListViewScrollToItem(index: toView.filteredEntries.count - 1 - exactIndex, position: position, animated: animated, curve: .Default(duration: nil), directionHint: directionHint)\n                }\n                var index = toView.filteredEntries.count - 1\n                for entry in toView.filteredEntries {\n                    if scrollToItem == nil && entry.sortIndex >= .index(.chatList(scrollIndex)) {')

    texts[location] += "\n" + (overlay / "Sources/ChatListUI/NagramiXUnreadChatListView.swift.inc").read_text(encoding="utf-8")
    texts[entries] += "\n" + (overlay / "Sources/ChatListUI/NagramiXUnreadChatListEntries.swift.inc").read_text(encoding="utf-8")
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")

def apply_separate_profile_navigation_buttons(source: Path) -> None:
    path = source / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderNavigationButtonContainerNode.swift"
    data = path.read_bytes()
    expected = "ffe35bf77b9099b5fa835a11e2c7a3327594fcb3"
    if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != expected:
        raise SystemExit("Изменилась проверенная шапка профиля или разделение кнопок уже применено")
    replace_unique(path, "    private let rightButtonsContainer: UIView\n", """    private let rightButtonsContainer: UIView
    private var nagramiXSeparateRightButtons = false
    private var nagramiXRightButtonBackgrounds: [PeerInfoHeaderNavigationButtonSpec: GlassContextExtractableContainer] = [:]

    // Text actions must remain distinct from search and other adjacent actions.
    // Icon-only groups keep Telegram's original capsule.
    private func nagramiXNeedsSeparateButtons(_ buttons: [PeerInfoHeaderNavigationButtonSpec]) -> Bool {
        for expanded in [false, true] {
            let group = buttons.filter { $0.isForExpandedView == expanded }
            if group.count > 1 && group.contains(where: { spec in
                switch spec.key {
                case .edit, .done, .cancel, .select, .selectionDone, .editPhoto, .editVideo:
                    return true
                default:
                    return false
                }
            }) {
                return true
            }
        }
        return false
    }

    private func nagramiXUpdateRightButtonFrame(spec: PeerInfoHeaderNavigationButtonSpec, button: PeerInfoHeaderNavigationButton, frame: CGRect, transition: ContainedViewLayoutTransition) {
        if self.nagramiXSeparateRightButtons {
            let background: GlassContextExtractableContainer
            var backgroundTransition = transition
            if let current = self.nagramiXRightButtonBackgrounds[spec] {
                background = current
            } else {
                background = GlassContextExtractableContainer()
                background.morphsIntoContextMenu = true
                self.nagramiXRightButtonBackgrounds[spec] = background
                self.rightButtonsContainer.addSubview(background)
                background.contentView.addSubview(button.view)
                backgroundTransition = .immediate
            }
            transition.updateFrame(node: button, frame: CGRect(origin: CGPoint(), size: frame.size))
            backgroundTransition.updateFrame(view: background, frame: frame)
        } else {
            if let background = self.nagramiXRightButtonBackgrounds.removeValue(forKey: spec) {
                let previousFrame = background.contentView.convert(button.frame, to: self.rightButtonsContainer)
                button.alpha = background.alpha
                self.rightButtonsContainer.addSubview(button.view)
                button.frame = previousFrame
                background.removeFromSuperview()
            }
            transition.updateFrameAdditiveToCenter(node: button, frame: frame)
        }
    }

    private func nagramiXUpdateRightButtonAlpha(spec: PeerInfoHeaderNavigationButtonSpec, button: PeerInfoHeaderNavigationButton, alpha: CGFloat, transition: ContainedViewLayoutTransition) {
        if let background = self.nagramiXRightButtonBackgrounds[spec] {
            // Fade the whole control once, including its glass and hit area.
            button.alpha = 1.0
            ComponentTransition(transition).setAlpha(view: background, alpha: alpha)
        } else {
            transition.updateAlpha(node: button, alpha: alpha)
        }
    }
""", "Отдельные штатные стеклянные контейнеры для текста и поиска в общей шапке профиля")
    replace_unique(path, """        let sideInset: CGFloat = 16.0
""", """        let sideInset: CGFloat = 16.0
        let separateRightButtons = self.nagramiXNeedsSeparateButtons(rightButtons)
        if self.nagramiXSeparateRightButtons != separateRightButtons {
            self.nagramiXSeparateRightButtons = separateRightButtons
            let targetContainer = separateRightButtons ? self.backgroundContainer.contentView : self.rightButtonsBackground.contentView
            let previousFrame = self.rightButtonsContainer.convert(self.rightButtonsContainer.bounds, to: targetContainer)
            if separateRightButtons {
                self.backgroundContainer.contentView.addSubview(self.rightButtonsContainer)
            } else {
                self.rightButtonsBackground.contentView.addSubview(self.rightButtonsContainer)
            }
            self.rightButtonsContainer.frame = previousFrame
        }
        self.rightButtonsBackground.isHidden = separateRightButtons
        self.rightButtonsContainer.clipsToBounds = !separateRightButtons
        let rightButtonSpacing: CGFloat = separateRightButtons ? 8.0 : 0.0
""", "Разделить фон и области нажатия смешанных групп без изменения иконных групп")
    # Both the creation and cached-layout branches need the same spacing and
    # wrapper coordinates; otherwise scrolling/rotation brings the join back.
    text = path.read_text(encoding="utf-8")
    start = text.index("        var expandedRightButtonsWidth: CGFloat = 0.0")
    end = text.index("        self.presentationData = presentationData", start)
    old = text[start:end]
    new = old
    frame_line = "let buttonFrame = CGRect(origin: CGPoint(x: spec.isForExpandedView ? expandedRightButtonsWidth : normalRightButtonsWidth, y: 0.0), size: buttonSize)"
    assert new.count(frame_line) == 2
    # A gap only precedes an existing button in that presentation set.
    def add_spacing(match: re.Match[str]) -> str:
        indent = match.group(1)
        return "\n".join(indent + line for line in (
            "if spec.isForExpandedView {",
            "    if expandedRightButtonsWidth > 0.0 { expandedRightButtonsWidth += rightButtonSpacing }",
            "} else {",
            "    if normalRightButtonsWidth > 0.0 { normalRightButtonsWidth += rightButtonSpacing }",
            "}",
            frame_line,
        ))
    new = re.sub(r"(?m)^([ \t]*)" + re.escape(frame_line), add_spacing, new)
    assert new.count("buttonNode.frame = buttonFrame") == 1
    new = new.replace("buttonNode.frame = buttonFrame", "self.nagramiXUpdateRightButtonFrame(spec: spec, button: buttonNode, frame: buttonFrame, transition: .immediate)")
    assert new.count("buttonNode.alpha = 0.0") == 1
    new = new.replace("buttonNode.alpha = 0.0", "self.nagramiXUpdateRightButtonAlpha(spec: spec, button: buttonNode, alpha: 0.0, transition: .immediate)")
    assert new.count("transition.updateFrameAdditiveToCenter(node: buttonNode, frame: buttonFrame)") == 2
    new = new.replace("transition.updateFrameAdditiveToCenter(node: buttonNode, frame: buttonFrame)", "self.nagramiXUpdateRightButtonFrame(spec: spec, button: buttonNode, frame: buttonFrame, transition: transition)")
    assert new.count("transition.updateAlpha(node: buttonNode, alpha: alphaFactor * alphaFactor)") == 2
    new = new.replace("transition.updateAlpha(node: buttonNode, alpha: alphaFactor * alphaFactor)", "self.nagramiXUpdateRightButtonAlpha(spec: spec, button: buttonNode, alpha: alphaFactor * alphaFactor, transition: transition)")
    assert new.count("buttonTransition.updateAlpha(node: buttonNode, alpha: alphaFactor * alphaFactor)") == 1
    new = new.replace("buttonTransition.updateAlpha(node: buttonNode, alpha: alphaFactor * alphaFactor)", "self.nagramiXUpdateRightButtonAlpha(spec: spec, button: buttonNode, alpha: alphaFactor * alphaFactor, transition: buttonTransition)")
    remove_anchor = """                if let buttonNode = self.rightButtonNodes.removeValue(forKey: spec) {
"""
    assert new.count(remove_anchor) == 1
    new = new.replace(remove_anchor, remove_anchor + """                    if let background = self.nagramiXRightButtonBackgrounds.removeValue(forKey: spec) {
                        background.layer.animateAlpha(from: background.alpha, to: 0.0, duration: 0.2, removeOnCompletion: false, completion: { [weak background] _ in
                            background?.removeFromSuperview()
                        })
                        background.layer.animateScale(from: 1.0, to: 0.001, duration: 0.2, removeOnCompletion: false)
                        continue
                    }
""")
    replace_unique(path, old, new, "Одинаковые интервалы и независимые переходы кнопок при создании и повторном layout")
    replace_unique(path, "        self.rightButtonsContainer = UIView()", "        self.rightButtonsContainer = SparseContainerView()", "Промежутки между кнопками не перехватывают нажатия")
    replace_unique(path, """        transition.updateFrame(view: self.rightButtonsContainer, frame: CGRect(origin: CGPoint(), size: rightButtonsFrame.size))
        self.rightButtonsContainer.layer.cornerRadius = rightButtonsFrame.height * 0.5
""", """        transition.updateFrame(view: self.rightButtonsContainer, frame: CGRect(origin: self.nagramiXSeparateRightButtons ? rightButtonsFrame.origin : CGPoint(), size: rightButtonsFrame.size))
        self.rightButtonsContainer.layer.cornerRadius = self.nagramiXSeparateRightButtons ? 0.0 : rightButtonsFrame.height * 0.5
""", "Сохранить абсолютное положение и не обрезать самостоятельные круглые кнопки")
    replace_unique(path, """        self.leftButtonsBackground.update(size: leftButtonsSize, cornerRadius: leftButtonsSize.height * 0.5, isDark: tintIsDark, tintColor: tintColor, isInteractive: true, transition: transition)
""", """        self.leftButtonsBackground.update(size: leftButtonsSize, cornerRadius: leftButtonsSize.height * 0.5, isDark: tintIsDark, tintColor: tintColor, isInteractive: true, transition: transition)
        for background in self.nagramiXRightButtonBackgrounds.values {
            let size = background.bounds.size
            background.update(size: size, cornerRadius: size.height * 0.5, isDark: tintIsDark, tintColor: tintColor, isInteractive: true, transition: transition)
        }
""", "Штатная тема, tint и context extraction каждой самостоятельной кнопки")


def apply_anonymous_story_viewing(source: Path) -> None:
    core = source / "submodules/TelegramCore/Sources/TelegramEngine/Messages/Stories.swift"
    data = core.read_bytes()
    expected = "fc104f5fb905819df5bdd013e42756fd4a00c4f4"
    if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != expected:
        raise SystemExit("Изменилась проверенная база регистрации просмотра историй или режим уже применён")
    ui = source / "submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources"
    content = ui / "StoryContent.swift"
    contexts = ui / "StoryChatContent.swift"
    screen = ui / "StoryContainerScreen.swift"
    item = ui / "StoryItemSetContainerComponent.swift"
    send = ui / "StoryItemSetContainerViewSendMessage.swift"
    # These are the audited inputs after existing NagramiX patches, including
    # the protected per-story approval gate. Changes require an explicit audit.
    integrated_inputs = {
        "StoryContent.swift": "a93b06994cecef825e5b5aad02c2a7c8d461df22a1bbdd576319d29db5b11f9b",
        "StoryChatContent.swift": "513e3ff8012d5aba9aa2c73580304345ae1f6859ba1950692eb5980a007582f9",
        "StoryContainerScreen.swift": "8b8d55b3dfffbd60153a0b7e601076e43c45c0f986a40ae1c6ac0bebffee792c",
        "StoryItemSetContainerComponent.swift": "97f64d0daa4d196f06244bfd9fedd0a654938632b54ae84af0b1d8320b194a38",
        "StoryItemSetContainerViewSendMessage.swift": "18d124e507259ea409bcb48ea5ab9b001f60ccd80cfe65b55502ca41e54892b7",
    }
    for name, expected_sha in integrated_inputs.items():
        if hashlib.sha256((ui / name).read_bytes()).hexdigest() != expected_sha:
            raise SystemExit(f"Изменилась проверенная интеграция историй или режим уже применён: {name}")
    patches: list[tuple[Path, str, str, str]] = []

    def patch(path: Path, old: str, new: str, label: str) -> None:
        patches.append((path, old, new, label))

    patch(core, "import Foundation\n", "import Foundation\nimport NagramiXMediaSettings\n", "Независимые от UI настройки просмотра историй")
    patch(core,
        "func _internal_markStoryAsSeen(account: Account, peerId: PeerId, id: Int32, asPinned: Bool) -> Signal<Never, NoError> {\n",
        """func _internal_markStoryAsSeen(account: Account, peerId: PeerId, id: Int32, asPinned: Bool) -> Signal<Never, NoError> {
    guard !NagramiXStorySettings.anonymousViewingEnabled || peerId == account.peerId else {
        return .complete()
    }
""", "Остановить регистрацию до изменения локального состояния и создания очереди")
    patch(core,
        """    if asPinned {
        return account.postbox.transaction { transaction -> Api.InputPeer? in
            return transaction.getPeer(peerId).flatMap(apiInputPeer)
""",
        """    if asPinned {
        return account.postbox.transaction { transaction -> Api.InputPeer? in
            guard !NagramiXStorySettings.anonymousViewingEnabled || peerId == account.peerId else {
                return nil
            }
            return transaction.getPeer(peerId).flatMap(apiInputPeer)
""", "Повторно проверить режим при выполнении отложенной транзакции закреплённой истории")
    patch(core,
        """            return account.network.request(Api.functions.stories.incrementStoryViews(peer: inputPeer, id: [id]))
""",
        """            guard !NagramiXStorySettings.anonymousViewingEnabled || peerId == account.peerId else {
                return .complete()
            }
            return account.network.request(Api.functions.stories.incrementStoryViews(peer: inputPeer, id: [id]))
""", "Не увеличивать серверный счётчик закреплённой истории в инкогнито")
    patch(core,
        """    } else {
        return account.postbox.transaction { transaction -> Api.InputUser? in
            if let peerStoryState = transaction.getPeerStoryState(peerId: peerId)?.entry.get(Stories.PeerState.self) {
""",
        """    } else {
        return account.postbox.transaction { transaction -> Bool in
            guard !NagramiXStorySettings.anonymousViewingEnabled || peerId == account.peerId else {
                return false
            }
            if let peerStoryState = transaction.getPeerStoryState(peerId: peerId)?.entry.get(Stories.PeerState.self) {
""", "Блокировать maxReadId и operation log при включённом режиме")
    patch(core,
        """            return transaction.getPeer(peerId).flatMap(apiInputUser)
        }
        |> mapToSignal { _ -> Signal<Never, NoError> in
            account.stateManager.injectStoryUpdates(updates: [.read(peerId: peerId, maxId: id)])
""",
        """            return true
        }
        |> mapToSignal { didMark -> Signal<Never, NoError> in
            guard didMark else {
                return .complete()
            }
            account.stateManager.injectStoryUpdates(updates: [.read(peerId: peerId, maxId: id)])
""", "Не публиковать read update после отклонённой транзакции")
    patch(content,
        "public protocol StoryContentContext: AnyObject {\n",
        "public protocol StoryContentContext: AnyObject {\n    var nagramiXAnonymousViewing: Bool { get }\n",
        "Передать неизменяемую политику сессии просмотрщика")
    patch(contexts, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Читать настройку при создании контекста историй")
    for name in ["StoryContentContextImpl", "SingleStoryContentContextImpl", "PeerStoryListContentContextImpl", "RepostStoriesContentContextImpl"]:
        anchor = f"public final class {name}: StoryContentContext {{\n"
        patch(contexts, anchor, anchor + "    public let nagramiXAnonymousViewing = NagramiXTabSettings.anonymousStoryViewingEnabled\n", "Зафиксировать политику сессии " + name)
    # All four native contexts use the same public entry point. Validate the
    # exact count before modifying any file, then replace within each class.
    context_text = contexts.read_text(encoding="utf-8")
    mark = "    public func markAsSeen(id: StoryId) {\n"
    if context_text.count(mark) != 4 or "guard !self.nagramiXAnonymousViewing" in context_text:
        raise SystemExit("Изменились четыре штатных контекста регистрации просмотра или режим уже применён")
    guarded_mark = mark + """        guard !self.nagramiXAnonymousViewing || id.peerId == self.context.account.peerId else {
            return
        }
"""
    patch(contexts, context_text, context_text.replace(mark, guarded_mark), "Сохранить инкогнито текущей сессии даже после выключения настройки")
    patch(item,
        "    let stealthModeTimeout: Int32?\n",
        """    let stealthModeTimeout: Int32?
    let nagramiXAnonymousViewing: Bool

    var nagramiXUsesAnonymousViewing: Bool {
        if case .liveStream = self.slice.item.storyItem.media {
            return false
        }
        return self.nagramiXAnonymousViewing && self.slice.effectivePeer.id != self.context.account.peerId
    }
""", "Отделить инкогнито историй от собственных историй и прямых эфиров")
    patch(item,
        "        stealthModeTimeout: Int32?,\n",
        "        stealthModeTimeout: Int32?,\n        nagramiXAnonymousViewing: Bool = false,\n",
        "Передать политику в компонент штатного плеера")
    patch(item,
        "        self.stealthModeTimeout = stealthModeTimeout\n",
        "        self.stealthModeTimeout = stealthModeTimeout\n        self.nagramiXAnonymousViewing = nagramiXAnonymousViewing\n",
        "Сохранить политику компонента")
    patch(item,
        "        if lhs.stealthModeTimeout != rhs.stealthModeTimeout {\n",
        "        if lhs.nagramiXAnonymousViewing != rhs.nagramiXAnonymousViewing {\n            return false\n        }\n        if lhs.stealthModeTimeout != rhs.stealthModeTimeout {\n",
        "Учитывать инкогнито при обновлении компонента")
    patch(screen,
        "                                stealthModeTimeout: stealthModeTimeout,\n",
        "                                stealthModeTimeout: stealthModeTimeout,\n                                nagramiXAnonymousViewing: component.content.nagramiXAnonymousViewing,\n",
        "Передать политику существующего content context без изменения confirmation gate")
    patch(item,
        "        let moreButton = ComponentView<Empty>()\n",
        "        let moreButton = ComponentView<Empty>()\n        private let nagramiXAnonymousIcon = UIImageView()\n",
        "Добавить индикатор в штатный контейнер верхних элементов управления")
    patch(item,
        "            var isSilentVideo = false\n            var isVideo = false\n",
        """            if component.nagramiXUsesAnonymousViewing {
                if self.nagramiXAnonymousIcon.superview == nil {
                    self.nagramiXAnonymousIcon.image = UIImage(systemName: "eye.slash")
                    self.nagramiXAnonymousIcon.tintColor = .white
                    self.nagramiXAnonymousIcon.contentMode = .scaleAspectFit
                    self.nagramiXAnonymousIcon.isUserInteractionEnabled = false
                    self.nagramiXAnonymousIcon.isAccessibilityElement = true
                    self.controlsClippingView.addSubview(self.nagramiXAnonymousIcon)
                }
                self.nagramiXAnonymousIcon.accessibilityLabel = component.strings.nagramiXAnonymousStoryViewing
                transition.setFrame(view: self.nagramiXAnonymousIcon, frame: CGRect(x: headerRightOffset - 22.0, y: 23.0, width: 22.0, height: 22.0))
                headerRightOffset -= 34.0
            } else {
                self.nagramiXAnonymousIcon.removeFromSuperview()
            }

            var isSilentVideo = false
            var isVideo = false
""", "Показать перечёркнутый глаз без перекрытия кнопок и имени автора")
    patch(send,
        "    weak var actionSheet: ViewController?\n",
        "    weak var actionSheet: ViewController?\n    weak var nagramiXAnonymousConfirmation: AlertScreen?\n",
        "Отслеживать отдельное предупреждение без блокировки отложенной отправки")
    patch(item,
        "self.sendMessageContext.actionSheet != nil || self.sendMessageContext.isViewingAttachedStickers",
        "self.sendMessageContext.actionSheet != nil || self.sendMessageContext.nagramiXAnonymousConfirmation != nil || self.sendMessageContext.isViewingAttachedStickers",
        "Приостановить историю до выбора в предупреждении, включая переход из выбора даты")
    patch(send,
        "    func performWithPossibleStealthModeConfirmation(view: StoryItemSetContainerComponent.View, action: @escaping () -> Void) {\n",
        """    func performWithPossibleStealthModeConfirmation(view: StoryItemSetContainerComponent.View, action: @escaping () -> Void) {
        if let component = view.component, component.nagramiXUsesAnonymousViewing {
            guard self.nagramiXAnonymousConfirmation == nil else {
                return
            }
            let storyId = component.slice.item.id
            let updatedPresentationData: (initial: PresentationData, signal: Signal<PresentationData, NoError>) = (component.context.sharedContext.currentPresentationData.with({ $0 }).withUpdated(theme: component.theme), component.context.sharedContext.presentationData |> map { $0.withUpdated(theme: component.theme) })
            let alertController = AlertScreen(
                title: component.strings.nagramiXAnonymousStoryWarningTitle,
                text: component.strings.nagramiXAnonymousStoryWarningText,
                actions: [
                    .init(title: component.strings.Common_Cancel, type: .default),
                    .init(title: component.strings.nagramiXAnonymousStoryContinue, type: .generic, action: { [weak view] in
                        guard let view, view.component?.slice.item.id == storyId else {
                            return
                        }
                        action()
                    })
                ],
                updatedPresentationData: updatedPresentationData
            )
            alertController.dismissed = { [weak self, weak view, weak alertController] _ in
                guard let self else {
                    return
                }
                if self.nagramiXAnonymousConfirmation === alertController {
                    self.nagramiXAnonymousConfirmation = nil
                }
                if self.actionSheet === alertController {
                    self.actionSheet = nil
                }
                view?.updateIsProgressPaused()
            }
            self.nagramiXAnonymousConfirmation = alertController
            self.actionSheet = alertController
            view.updateIsProgressPaused()
            component.controller()?.presentInGlobalOverlay(alertController)
            return
        }
""", "Предупредить перед раскрывающим личность ответом или новой реакцией независимо от Premium")

    # Validate anchors against the same input, including the whole-context
    # replacement. Apply that replacement first so it cannot discard imports.
    for path, old, _, label in patches:
        count = path.read_text(encoding="utf-8").count(old)
        if count != 1:
            raise SystemExit(f"Изменился строгий якорь инкогнито ({label}): {path}, count={count}")
    patches.sort(key=lambda entry: 0 if entry[1] == context_text else 1)
    for path, old, new, label in patches:
        replace_unique(path, old, new, label)


def apply_qr_brightness_restore(source: Path) -> None:
    path = source / "submodules/QrCodeUI/Sources/QrCodeScreen.swift"
    data = path.read_bytes()
    expected = "796e12bfffedb838c2a201f6bfae5df227258a7d"
    if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != expected:
        raise SystemExit("Изменился проверенный stock-экран QR или правка яркости уже применена")
    replace_unique(path,
        "private func shareQrCode(sharedContext: SharedAccountContext, subject: QrCodeScreen.Subject, asImage: Bool, view: UIView) {",
        """private func shareQrCode(sharedContext: SharedAccountContext, subject: QrCodeScreen.Subject, asImage: Bool, view: UIView, restoreBrightness: () -> Void) {
    restoreBrightness()""",
        "Восстановить яркость до открытия отправки QR или ссылки")
    text = path.read_text(encoding="utf-8")
    suffix = "view: view)"
    if text.count(suffix) != 3:
        raise SystemExit("Изменились три штатных действия отправки QR")
    path.write_text(text.replace(suffix, "view: view, restoreBrightness: state.finishBrightness)"), encoding="utf-8")
    replace_unique(path,
        "        private var animator: ConstantDisplayLinkAnimator?\n",
        """        private var animator: ConstantDisplayLinkAnimator?
        private let brightnessActivityDisposable = MetaDisposable()
        private var brightnessIsVisible = false
        private var brightnessApplicationIsActive = false
        private var brightnessFinished = false
""", "Состояние временного повышения яркости принадлежит QR-экрану")
    replace_unique(path,
        """            self.initialBrightness = UIScreen.main.brightness
            self.brightnessArguments = (CACurrentMediaTime(), 0.3, UIScreen.main.brightness, 1.0)
            self.updateBrightness()
""",
        """            self.brightnessActivityDisposable.set((sharedContext.applicationBindings.applicationIsActive
            |> distinctUntilChanged
            |> deliverOnMainQueue).start(next: { [weak self] isActive in
                guard let self else { return }
                self.brightnessApplicationIsActive = isActive
                self.updateBrightnessVisibility(self.brightnessIsVisible)
            }))
""", "Повышать яркость только при видимом QR в активном приложении")
    replace_unique(path,
        """        deinit {
            self.idleTimerExtensionDisposable.dispose()
            self.animator?.invalidate()\n            \n            if UIScreen.main.brightness > 0.99, let initialBrightness = self.initialBrightness {
                self.brightnessArguments = (CACurrentMediaTime(), 0.3, UIScreen.main.brightness, initialBrightness)
                self.updateBrightness()
            }
        }
""",
        """        deinit {
            self.brightnessActivityDisposable.dispose()
            self.restoreBrightness()
            self.idleTimerExtensionDisposable.dispose()
            self.animator?.invalidate()
        }

        func updateBrightnessVisibility(_ isVisible: Bool) {
            self.brightnessIsVisible = isVisible
            guard isVisible, self.brightnessApplicationIsActive, !self.brightnessFinished else {
                self.restoreBrightness()
                return
            }
            if self.initialBrightness == nil {
                let initial = UIScreen.main.brightness
                self.initialBrightness = initial
                self.brightnessArguments = (CACurrentMediaTime(), 0.3, initial, 1.0)
                self.updateBrightness()
            }
        }

        func finishBrightness() {
            self.brightnessFinished = true
            self.restoreBrightness()
        }

        private func restoreBrightness() {
            // Остановить повышение до возврата значения: поздний кадр его не перезапишет.
            self.brightnessArguments = nil
            self.animator?.isPaused = true
            if let initialBrightness = self.initialBrightness {
                self.initialBrightness = nil
                UIScreen.main.brightness = initialBrightness
            }
        }
""", "Точный однократный возврат яркости без анимации на уничтоженном display link")
    replace_unique(path,
        """            let state = context.state

            let effectiveSubject:""",
        """            let state = context.state
            state.updateBrightnessVisibility(environment.value.isVisible)
            if let controller = controller as? QrCodeScreen {
                controller.restoreQrBrightness = { [weak state] in
                    state?.finishBrightness()
                }
            }

            let effectiveSubject:""", "Связать яркость с фактической видимостью и закрытием QR")
    replace_unique(path,
        """                    action: { _ in
                        component.dismiss()
""",
        """                    action: { _ in
                        state.finishBrightness()
                        component.dismiss()
""", "Вернуть исходную яркость при закрытии крестиком")
    replace_unique(path,
        "public final class QrCodeScreen: ViewControllerComponentContainer {\n",
        "public final class QrCodeScreen: ViewControllerComponentContainer {\n    fileprivate var restoreQrBrightness: (() -> Void)?\n",
        "Слабый callback восстановления при закрытии контейнера")
    replace_unique(path,
        """    public func dismissAnimated() {
        if let view = self.node.hostView.findTaggedView""",
        """    override public func dismiss(completion: (() -> Void)? = nil) {
        self.restoreQrBrightness?()
        super.dismiss(completion: completion)
    }

    override public func dismiss(animated flag: Bool, completion: (() -> Void)? = nil) {
        self.restoreQrBrightness?()
        super.dismiss(animated: flag, completion: completion)
    }

    public func dismissAnimated() {
        self.restoreQrBrightness?()
        if let view = self.node.hostView.findTaggedView""",
        "Возврат яркости при свайпе, закрытии вне окна и программном dismiss")


def apply_notification_sound_catalog(source: Path, overlay: Path) -> None:
    settings = source / "submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramPeerNotificationSettings.swift"
    sounds = source / "submodules/TelegramCore/Sources/TelegramEngine/Peers/NotificationSoundList.swift"
    picker = source / "submodules/NotificationSoundSelectionUI/Sources/NotificationSoundSelection.swift"
    extension = source / "Telegram/NotificationService/Sources/NotificationService.swift"
    if "builtinNotificationSounds" in settings.read_text(encoding="utf-8"):
        raise SystemExit("Каталог встроенных звуков уже применён")
    for path, expected in (
        (settings, "78df24b4f2fdcb5edb92f8ec3f993d9725b2c82b"),
        (sounds, "1dd9c607bc3879f0a9394926323df88dcc0cd08c"),
        (picker, "656f3c79387b4c11745fbda83b8af75e6aa6d4da"),
        (extension, "7a7c87bd4815e7ddf964a28e45289d65196f1a51"),
    ):
        data = path.read_bytes()
        if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != expected:
            raise SystemExit(f"Изменился проверенный источник каталога звуков: {path}")

    replace_unique(settings, "public let defaultCloudPeerNotificationSound:", """// Каталог не зависит от набора сохранённых серверных мелодий аккаунта.
public let builtinNotificationSounds: [PeerMessageSound] = (
    Array(Int32(200)...Int32(210)) + Array(Int32(100)...Int32(111)) + Array(Int32(2)...Int32(9))
).compactMap { key in
    cloudSoundMapping[key].map { PeerMessageSound.cloud(fileId: $0) }
}

public func builtinNotificationSoundFileName(id: Int64) -> String? {
    guard let key = cloudSoundMapping.first(where: { $0.value == id })?.key else {
        return nil
    }
    return "\\(key).m4a"
}

public let defaultCloudPeerNotificationSound:""", "Независимый встроенный каталог со штатными серверными ID")
    replace_unique(settings, "return (key - 100, .modern)", "return (key >= 200 ? key - 200 + 12 : key - 100, .modern)", "Названия новых системных мелодий по штатным локализованным ключам")
    replace_unique(sounds, "private func pollNotificationSoundList(postbox: Postbox, network: Network)", "private func pollNotificationSoundList(postbox: Postbox, network: Network, force: Bool = false)", "Принудительное обновление каталога при открытии")
    replace_unique(sounds, "getSavedRingtones(hash: current?.hash ?? 0)", "getSavedRingtones(hash: force ? 0 : (current?.hash ?? 0))", "Свежий список вместо ответа NotModified для неполного кеша")
    replace_unique(sounds, "func managedSynchronizeNotificationSoundList(", """public func refreshNotificationSoundList(postbox: Postbox, network: Network) -> Signal<Never, NoError> {
    return pollNotificationSoundList(postbox: postbox, network: network, force: true)
}

func managedSynchronizeNotificationSoundList(""", "Обновление и штатная загрузка пользовательских мелодий")
    replace_unique(sounds, """    case let .cloud(fileId):
        if let notificationSoundList = notificationSoundList {
""", """    case let .cloud(fileId):
        if builtinNotificationSoundFileName(id: fileId) != nil {
            return sound
        }
        if let notificationSoundList = notificationSoundList {
""", "Сохранить выбранную встроенную мелодию при неполном серверном списке")

    old_entries = picker.read_text(encoding="utf-8").split("    if let notificationSoundList = notificationSoundList {", 1)[1].split("\n    return entries", 1)[0]
    # Проверяем точную stock-структуру до отделения облачного раздела от builtins.
    cloud_end = "        entries.append(.uploadSound(presentationData.strings.Notifications_UploadSound))"
    prefix, tail = old_entries.split(cloud_end, 1)
    expected_filters = """
        let cloudSounds = notificationSoundList.sounds.filter({ CloudSoundBuiltinCategory(id: $0.file.fileId.id) == nil })
        let modernSounds = notificationSoundList.sounds.filter({ CloudSoundBuiltinCategory(id: $0.file.fileId.id) == .modern })
        let classicSounds = notificationSoundList.sounds.filter({ CloudSoundBuiltinCategory(id: $0.file.fileId.id) == .classic })
"""
    if not prefix.startswith(expected_filters) or not tail.endswith("    }\n    "):
        raise SystemExit("Изменилась stock-структура списка звуков")
    prefix = prefix.replace(expected_filters, "\n        let cloudSounds = notificationSoundList.sounds.filter({ CloudSoundBuiltinCategory(id: $0.file.fileId.id) == nil })\n", 1)
    tail = (cloud_end + tail).removesuffix("    }\n    ")
    tail = "\n".join(line[4:] if line.startswith("    ") else line for line in tail.split("\n"))
    tail = tail.replace(".cloud(fileId: modernSounds[i].file.fileId.id)", "modernSounds[i]").replace(".cloud(fileId: classicSounds[i].file.fileId.id)", "classicSounds[i]")
    new_entries = """    let modernSounds = builtinNotificationSounds.filter {
        if case let .cloud(fileId) = $0 { return CloudSoundBuiltinCategory(id: fileId) == .modern }
        return false
    }
    let classicSounds = builtinNotificationSounds.filter {
        if case let .cloud(fileId) = $0 { return CloudSoundBuiltinCategory(id: fileId) == .classic }
        return false
    }
    if let notificationSoundList = notificationSoundList {""" + prefix + "    }\n\n" + tail
    replace_unique(picker, "    if let notificationSoundList = notificationSoundList {" + old_entries, new_entries, "Встроенные разделы и загрузка доступны даже без кеша")
    replace_unique(picker, """    case let .cloud(fileId):
        guard let notificationSoundList = notificationSoundList else {
""", """    case let .cloud(fileId):
        if let fileName = builtinNotificationSoundFileName(id: fileId) {
            return String(fileName.dropLast(4))
        }
        guard let notificationSoundList = notificationSoundList else {
""", "Локальное штатное прослушивание встроенных звуков")
    replace_unique(picker, "    let fetchedSoundsDisposable = ensureDownloadedNotificationSoundList(postbox: context.account.postbox).start()", """    let fetchedSoundsDisposable = ensureDownloadedNotificationSoundList(postbox: context.account.postbox).start()
    let refreshedSoundsDisposable = refreshNotificationSoundList(postbox: context.account.postbox, network: context.account.network).start()""", "Экран обновляет пользовательский каталог без часового ожидания")
    replace_unique(picker, "        fetchedSoundsDisposable.dispose()", "        fetchedSoundsDisposable.dispose()\n        refreshedSoundsDisposable.dispose()", "Отменить загрузку при закрытии экрана")
    replace_unique(extension, """                                content.sound = "0.m4a"
                                if let notificationSoundList = notificationSoundList {""", """                                content.sound = builtinNotificationSoundFileName(id: fileId) ?? "0.m4a"
                                if builtinNotificationSoundFileName(id: fileId) == nil, let notificationSoundList = notificationSoundList {""", "Уведомление воспроизводит выбранную встроенную мелодию без серверного кеша")

    resources = overlay / "Resources/NotificationSounds"
    manifest = json.loads((resources / "manifest.json").read_text(encoding="utf-8"))
    expected_keys = set(range(200, 211)) | set(range(100, 112)) | set(range(2, 10))
    if len(manifest) != 31 or {row["key"] for row in manifest} != expected_keys:
        raise SystemExit("Неполный встроенный каталог звуков")
    destination = source / "Telegram/Telegram-iOS/Resources/notifications"
    destination.mkdir(parents=True, exist_ok=True)
    for row in manifest:
        path = resources / row["file"]
        if row["file"] != f'{row["key"]}.m4a' or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit(f"Повреждена встроенная мелодия: {row['file']}")
        if (destination / path.name).exists():
            raise SystemExit(f"Конфликт встроенной мелодии с pin: {path.name}")
        shutil.copy2(path, destination / path.name)


def apply_channel_bottom_panel(source: Path) -> None:
    # Hide only the ordinary subscribed broadcast-reader panel. Keep the
    # native join, composer, search, selection and pinned-message actions.
    factory = source / "submodules/TelegramUI/Sources/ChatInterfaceStateInputPanels.swift"
    node = source / "submodules/TelegramUI/Sources/ChatControllerNode.swift"
    if (
        "import NagramiXCore\n" in factory.read_text(encoding="utf-8")
        or "NagramiXTabSettings.channelBottomPanelEnabled" in factory.read_text(encoding="utf-8")
        or "nagramiXChannelBottomPanelObserver" in node.read_text(encoding="utf-8")
    ):
        raise SystemExit("Channel bottom panel overlay is already or partially applied")
    replace_unique(factory, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Channel bottom panel settings import")
    replace_unique(
        factory,
        """                } else if !channel.hasPermission(.sendSomething) || !isMember {
                    if let currentPanel = (currentPanel as? ChatChannelSubscriberInputPanelNode) ?? (currentSecondaryPanel as? ChatChannelSubscriberInputPanelNode) {
""",
        """                } else if !channel.hasPermission(.sendSomething) || !isMember {
                    if isMember, case .peer = chatPresentationInterfaceState.chatLocation, !NagramiXTabSettings.channelBottomPanelEnabled {
                        return (nil, nil)
                    }
                    if let currentPanel = (currentPanel as? ChatChannelSubscriberInputPanelNode) ?? (currentSecondaryPanel as? ChatChannelSubscriberInputPanelNode) {
""",
        "Hide the subscribed broadcast bottom panel through native panel selection",
    )

    # TelegramUI already links NagramiXCore; ChatControllerNode imports it in
    # the existing archive/wide-post overlay. Use the native layout callback.
    replace_unique(
        node,
        "    var requestLayout: (ContainedViewLayoutTransition) -> Void = { _ in }\n",
        "    var requestLayout: (ContainedViewLayoutTransition) -> Void = { _ in }\n    private var nagramiXChannelBottomPanelObserver: NSObjectProtocol?\n",
        "Channel bottom panel observer ownership",
    )
    replace_unique(
        node,
        "        self.inputMediaNodeDataDisposable = (self.inputMediaNodeDataPromise.get()\n",
        """        self.nagramiXChannelBottomPanelObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.channelBottomPanelChangedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.requestLayout(.immediate)
        })

        self.inputMediaNodeDataDisposable = (self.inputMediaNodeDataPromise.get()
""",
        "Relayout channel bottom panel after a live preference change",
    )
    replace_unique(
        node,
        "        self.openStickersDisposable?.dispose()\n",
        """        self.openStickersDisposable?.dispose()
        if let observer = self.nagramiXChannelBottomPanelObserver {
            NotificationCenter.default.removeObserver(observer)
        }
""",
        "Remove channel bottom panel observer on chat destruction",
    )


def apply_message_interaction_options(source: Path) -> None:
    interaction = source / "submodules/TelegramUI/Components/ChatControllerInteraction/Sources/ChatControllerInteraction.swift"
    controller = source / "submodules/TelegramUI/Sources/ChatController.swift"
    node = source / "submodules/TelegramUI/Sources/ChatControllerNode.swift"
    bubble = source / "submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift"
    animated = source / "submodules/TelegramUI/Components/Chat/ChatMessageAnimatedStickerItemNode/Sources/ChatMessageAnimatedStickerItemNode.swift"
    if "nagramiXEditMessageOnDoubleTap" in interaction.read_text(encoding="utf-8") or "nagramiXHideReactionsObserver" in node.read_text(encoding="utf-8"):
        raise SystemExit("Message interaction options are already or partially applied")
    for path in (controller, bubble, animated):
        if "nagramiXEditMessageOnDoubleTap" in path.read_text(encoding="utf-8") or "NagramiXTabSettings.hideReactionsEnabled" in path.read_text(encoding="utf-8"):
            raise SystemExit(f"Message interaction options are partially applied: {path}")
    for name in ("ChatMessageStickerItemNode", "ChatMessageAnimatedStickerItemNode", "ChatMessageInstantVideoItemNode", "ChatMessageDateAndStatusNode"):
        directory = source / ("submodules/TelegramUI/Components/Chat/" + name)
        text = (directory / ("Sources/" + name + ".swift")).read_text(encoding="utf-8")
        if "import NagramiXCore\n" in text or "NagramiXTabSettings.hideReactionsEnabled" in text or "//submodules/NagramiXCore:NagramiXCore" in (directory / "BUILD").read_text(encoding="utf-8"):
            raise SystemExit(f"Reaction visibility overlay is partially applied: {name}")
    if "import NagramiXCore\n" in controller.read_text(encoding="utf-8"):
        raise SystemExit("Double-tap edit controller import is already applied")

    replace_unique(interaction, "public final class ChatControllerInteraction: ChatControllerInteractionProtocol {\n", """public final class ChatControllerInteraction: ChatControllerInteractionProtocol {
    public var nagramiXEditMessageOnDoubleTap: (EngineRawMessage) -> Bool = { _ in false }
""", "Bridge native double-tap edit without changing existing interaction initializers")
    replace_unique(controller, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Read double-tap edit preference in native chat controller")
    replace_unique(controller, "        self.controllerInteraction = controllerInteraction\n", """        self.controllerInteraction = controllerInteraction
        controllerInteraction.nagramiXEditMessageOnDoubleTap = { [weak self] message in
            guard let self, NagramiXTabSettings.doubleTapEditEnabled, self.isNodeLoaded,
                  self.presentationInterfaceState.interfaceState.selectionState == nil,
                  !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }),
                  !message.media.contains(where: { $0 is TelegramMediaAction }),
                  let interfaceInteraction = self.interfaceInteraction else {
                return false
            }
            if case .standard(.previewing) = self.presentationInterfaceState.mode {
                return false
            }
            if case .pinnedMessages = self.presentationInterfaceState.subject {
                return false
            }
            if self.presentationInterfaceState.renderedPeer?.peer is TelegramChannel && message.id.peerId.namespace == Namespaces.Peer.CloudGroup {
                return false
            }
            guard canEditMessage(context: self.context, limitsConfiguration: self.context.currentLimitsConfiguration.with { EngineConfiguration.Limits($0) }, message: message) else {
                return false
            }
            if message.media.contains(where: { $0 is TelegramMediaTodo }) {
                interfaceInteraction.editTodoMessage(message.id, nil, false)
            } else {
                interfaceInteraction.setupEditMessage(message.id, { _ in })
            }
            return true
        }
""", "Use native editability and edit setup for double taps")

    # The native hit-test chooses the touched message inside albums. Do not
    # replace that with item.message (the first album member).
    for path in (bubble, animated):
        old = """                    case let .openContextMenu(openContextMenu):
                        if canAddMessageReactions(message: EngineMessage("""
        new = """                    case let .openContextMenu(openContextMenu):
                        if case .doubleTap = gesture, item.controllerInteraction.nagramiXEditMessageOnDoubleTap(openContextMenu.tapMessage) {
                            return
                        }
                        if canAddMessageReactions(message: EngineMessage("""
        replace_unique(path, old, new, "Prefer editable double-tap target before the default reaction")
        old = """                } else if case .doubleTap = gesture {
                    if canAddMessageReactions(message: EngineMessage(item.message)) {
"""
        hit_test = "self.backgroundNode.frame.contains(location) && " if path == bubble else ""
        new = f"""                }} else if case .doubleTap = gesture {{
                    if {hit_test}item.controllerInteraction.nagramiXEditMessageOnDoubleTap(item.message) {{
                        return
                    }}
                    if canAddMessageReactions(message: EngineMessage(item.message)) {{
"""
        replace_unique(path, old, new, "Edit a double-tapped text or large emoji before default reaction fallback")

    replace_unique(bubble,
        "    if !reactionsAreInline && !hideAllAdditionalInfo, let reactionsAttribute = mergedMessageReactions(",
        "    if !NagramiXTabSettings.hideReactionsEnabled && !reactionsAreInline && !hideAllAdditionalInfo, let reactionsAttribute = mergedMessageReactions(",
        "Omit dedicated reaction footers without hiding comments")
    replace_unique(bubble, "        if needReactions || forceReactionsOutside {\n", "        if !NagramiXTabSettings.hideReactionsEnabled && (needReactions || forceReactionsOutside) {\n", "Omit external bubble reactions and their layout space")

    for name in ("ChatMessageStickerItemNode", "ChatMessageAnimatedStickerItemNode", "ChatMessageInstantVideoItemNode", "ChatMessageDateAndStatusNode"):
        directory = source / ("submodules/TelegramUI/Components/Chat/" + name)
        path = directory / ("Sources/" + name + ".swift")
        replace_unique(path, "import Foundation\n", "import Foundation\nimport NagramiXCore\n", "Reaction visibility import for " + name)
        replace_unique(directory / "BUILD", '        "//submodules/TelegramCore",\n', '        "//submodules/TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",\n', "Link reaction visibility preferences for " + name)
        if name != "ChatMessageDateAndStatusNode":
            replace_unique(path,
                "            if shouldDisplayInlineDateReactions(message: EngineMessage(item.message), isPremium: item.associatedData.isPremium, forceInline: item.associatedData.forceInlineReactions) {\n",
                "            if NagramiXTabSettings.hideReactionsEnabled || shouldDisplayInlineDateReactions(message: EngineMessage(item.message), isPremium: item.associatedData.isPremium, forceInline: item.associatedData.forceInlineReactions) {\n",
                "Hide separate sticker and round-video reactions through native empty layout")
        else:
            # Arguments are a local value copy. Stored message attributes and
            # sending/reaction APIs retain the original server data.
            replace_unique(path, "        return { [weak self] arguments in\n", """        return { [weak self] arguments in
            var arguments = arguments
            if NagramiXTabSettings.hideReactionsEnabled {
                arguments.reactions = []
                arguments.reactionPeers = []
            }
""", "Hide all inline date/status reactions through native empty layout")

    replace_unique(node, "    private var nagramiXDeletedLabelObserver: NSObjectProtocol?\n", "    private var nagramiXDeletedLabelObserver: NSObjectProtocol?\n    private var nagramiXHideReactionsObserver: NSObjectProtocol?\n", "Own live reaction visibility observer")
    replace_unique(node, """        self.nagramiXDeletedLabelObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.deletedMessageLabelChangedNotification, object: nil, queue: .main, using: { _ in
            nagramiXRefreshVisibleMessages()
        })
""", """        self.nagramiXDeletedLabelObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.deletedMessageLabelChangedNotification, object: nil, queue: .main, using: { _ in
            nagramiXRefreshVisibleMessages()
        })
        self.nagramiXHideReactionsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.hideReactionsChangedNotification, object: nil, queue: .main, using: { [weak self] _ in
            guard let self else {
                return
            }
            var messageIds = Set<MessageId>()
            self.historyNode.forEachItemNode { itemNode in
                guard let item = (itemNode as? ChatMessageItemView)?.item else {
                    return
                }
                for (message, _) in item.content {
                    messageIds.insert(message.id)
                }
            }
            for messageId in messageIds {
                self.historyNode.requestMessageUpdate(messageId)
            }
        })
""", "Rebind visible messages when reaction visibility changes")
    replace_unique(node, """        if let nagramiXDeletedLabelObserver = self.nagramiXDeletedLabelObserver {
            NotificationCenter.default.removeObserver(nagramiXDeletedLabelObserver)
        }
""", """        if let nagramiXDeletedLabelObserver = self.nagramiXDeletedLabelObserver {
            NotificationCenter.default.removeObserver(nagramiXDeletedLabelObserver)
        }
        if let observer = self.nagramiXHideReactionsObserver {
            NotificationCenter.default.removeObserver(observer)
        }
""", "Remove reaction visibility observer on chat destruction")


def apply_download_acceleration(source: Path) -> None:
    fetch = source / "submodules/TelegramCore/Sources/Network/MultipartFetch.swift"
    manager = source / "submodules/TelegramCore/Sources/Network/MultiplexedRequestManager.swift"
    build = source / "submodules/TelegramCore/BUILD"
    if any("NagramiXDownloadSettings" in path.read_text(encoding="utf-8") or "nagramiXDownloadTuning" in path.read_text(encoding="utf-8") or "import NagramiXMediaSettings\n" in path.read_text(encoding="utf-8") for path in (fetch, manager)) or "//submodules/NagramiXMediaSettings:NagramiXMediaSettings" in build.read_text(encoding="utf-8"):
        raise SystemExit("Download acceleration overlay is already or partially applied")
    for path in (fetch, manager):
        replace_unique(path, "import Foundation\n", "import Foundation\nimport NagramiXMediaSettings\n", "Read download acceleration preferences in " + path.name)
    replace_unique(build, """        "//submodules/WebProxyTransport:WebProxyTransport",
        "//submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit",
""", """        "//submodules/WebProxyTransport:WebProxyTransport",
        "//submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit",
        "//submodules/NagramiXMediaSettings:NagramiXMediaSettings",
""", "Link Foundation-only download preferences without UI dependency cycles")
    replace_unique(fetch, """        if isStory {
            self.defaultPartSize = 512 * 1024
""", """        let nagramiXDownloadTuning = NagramiXDownloadSettings.current.tuning
        if !isStory, encryptionKey == nil, let size = size, size > 512 * 1024,
           case .generic = location, let tuning = nagramiXDownloadTuning {
            // Snapshot once per file; preserve native alignment, CDN hash,
            // revalidation, cancellation and unknown-size/secret/story paths.
            self.defaultPartSize = tuning.partSize
            self.parallelParts = tuning.parallelParts
        } else if isStory {
            self.defaultPartSize = 512 * 1024
""", "Tune only known large ordinary cloud downloads before native scheduling")
    replace_unique(manager, """    private func isTargetSaturated(_ targetKey: MultiplexedRequestTargetKey) -> Bool {
        let (maxRequestsPerWorker, maxWorkersPerTarget) = self.limits(targetKey.target)
""", """    private func nagramiXLimits(_ request: RequestData) -> (requestsPerWorker: Int, workersPerTarget: Int) {
        let native = self.limits(request.target)
        if request.resourceId != nil, request.expectedResponseSize == 1024 * 1024,
           let tuning = NagramiXDownloadSettings.current.tuning {
            return (native.requestsPerWorker, max(native.workersPerTarget, tuning.workersPerTarget))
        }
        return native
    }

    private func isTargetSaturated(_ targetKey: MultiplexedRequestTargetKey, request: RequestData) -> Bool {
        let (maxRequestsPerWorker, maxWorkersPerTarget) = self.nagramiXLimits(request)
""", "Preserve native main/CDN capacity and tune only accelerated parts")
    replace_unique(manager, "!self.isTargetSaturated(targetKey)", "!self.isTargetSaturated(targetKey, request: request)", "Check accelerated capacity before the native saturated-target fast path")
    replace_unique(manager, "            let (maxRequestsPerWorker, maxWorkersPerTarget) = self.limits(request.target)\n", "            let (maxRequestsPerWorker, maxWorkersPerTarget) = self.nagramiXLimits(request)\n", "Use the same native download limits for queue dispatch")
    replace_unique(manager, """            for targetContext in self.targetContexts[targetKey]! {
                if targetContext.requests.count < maxRequestsPerWorker {
""", """            for targetContext in self.targetContexts[targetKey]!.prefix(maxWorkersPerTarget) {
                if targetContext.requests.count < maxRequestsPerWorker {
""", "Keep uploads and native requests within their stock worker pool")


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
        """public func peerMessagesMediaPlaylistAndItemId(_ message: EngineMessage, isRecentActions: Bool, isGlobalSearch: Bool, isDownloadList: Bool, isSavedMusic: Bool, isAttachMusic: Bool, richMessageQueueId: EngineMessage.Id? = nil) -> (SharedMediaPlaylistId, SharedMediaPlaylistItemId)? {
    if let richMessageQueueId {
        // A rich message's audio queue renders synthesized Local-id rows whose id.id IS the
        // InstantPageMedia index. The playing playlist is an InstantPageMediaPlaylist, so its
        // identity — not a PeerMessages one — is what the row must be compared against.
        return (RichMessagePlaylistId(messageId: richMessageQueueId), RichMessagePlaylistItemId(index: Int(message.id.id)))
    }
    if isSavedMusic {
""",
        """public func peerMessagesMediaPlaylistAndItemId(_ message: EngineMessage, isRecentActions: Bool, isGlobalSearch: Bool, isDownloadList: Bool, isSavedMusic: Bool, isAttachMusic: Bool, richMessageQueueId: EngineMessage.Id? = nil) -> (SharedMediaPlaylistId, SharedMediaPlaylistItemId)? {
    if let richMessageQueueId {
        // A rich message's audio queue renders synthesized Local-id rows whose id.id IS the
        // InstantPageMedia index. The playing playlist is an InstantPageMediaPlaylist, so its
        // identity — not a PeerMessages one — is what the row must be compared against.
        return (RichMessagePlaylistId(messageId: richMessageQueueId), RichMessagePlaylistItemId(index: Int(message.id.id)))
    }
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
                    parentGroupId = groupId._asGroup()
                }
                self.context.sharedContext.navigateToChatController(NavigateToChatControllerParams(navigationController: navigationController, chatController: chatController, context: self.context, chatLocation: location, keepStack: .always, useExisting: false, parentGroupId: parentGroupId, chatListFilter: self.chatListDisplayNode.mainContainerNode.currentItemNode.chatListFilter?.id, forceOpenChat: true))
            })
        }

        self.chatListDisplayNode.mainContainerNode.activateChatPreview = { [weak self] item, threadId, node, gesture, location in
""", "Navigate through native age and navigation checks with a dedicated silent full chat")


def apply_chat_actions_readonly_fix(source: Path) -> None:
    """Restore native archive eligibility and make avatar opening read-only."""
    menus = source / "submodules/ChatListUI/Sources/ChatContextMenus.swift"
    row = source / "submodules/ChatListUI/Sources/Node/ChatListItem.swift"
    chat = source / "submodules/TelegramUI/Sources/ChatController.swift"
    node = source / "submodules/TelegramUI/Sources/ChatControllerNode.swift"
    load = source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
    panels = source / "submodules/TelegramUI/Sources/ChatInterfaceStateInputPanels.swift"

    for path, markers in [
        (menus, ["let archiveEnabled = !isSavedMessages && peerId != EnginePeer.Id(namespace: Namespaces.Peer.CloudUser, id: EnginePeer.Id.Id._internalFromInt64Value(777000))\n"]),
        (row, ["if strongSelf.nagramiXHoldBeganOnAvatar && strongSelf.nagramiXCanOpenAvatarWithoutReadReceipts"]),
        (panels, ["nagramiXReadOnly"]),
        (node, ["nagramiXReadOnly: self.controller?", "self.controller?.nagramiXReadHistoryDisabled == true ? nil"]),
        (chat, ["guard !self.nagramiXReadHistoryDisabled else", "guard let self, !self.nagramiXReadHistoryDisabled, NagramiXTabSettings.doubleTapEditEnabled"]),
        (load, ["guard let strongSelf = self, !strongSelf.nagramiXReadHistoryDisabled else", "if strongSelf.nagramiXReadHistoryDisabled {"]),
    ]:
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in markers):
            raise SystemExit(f"Chat avatar/archive overlay is already or partially applied: {path}")

    replace_unique(menus,
        "                        let archiveEnabled = !isSavedMessages && peerId != EnginePeer.Id(namespace: Namespaces.Peer.CloudUser, id: EnginePeer.Id.Id._internalFromInt64Value(777000)) && peerId == context.account.peerId\n",
        "                        let archiveEnabled = !isSavedMessages && peerId != EnginePeer.Id(namespace: Namespaces.Peer.CloudUser, id: EnginePeer.Id.Id._internalFromInt64Value(777000))\n",
        "Remove the contradictory self-peer requirement; retain native archive actions and exclusions")
    replace_unique(row,
        "            if NagramiXTabSettings.current.chatActionsOnHold && !strongSelf.nagramiXHoldBeganOnAvatar {\n",
        """            if strongSelf.nagramiXHoldBeganOnAvatar && strongSelf.nagramiXCanOpenAvatarWithoutReadReceipts {
                // Cancel native extraction and the pending short tap before navigation.
                // The same read-only route applies with the preference on or off.
                strongSelf.contextContainer.cancelGesture()
                strongSelf.avatarTapRecognizer?.isEnabled = false
                strongSelf.avatarTapRecognizer?.isEnabled = true
                item.interaction.nagramiXOpenChatWithoutReadReceipts?(item)
                return
            }
            if NagramiXTabSettings.current.chatActionsOnHold && !strongSelf.nagramiXHoldBeganOnAvatar {
""",
        "Avatar holds open the dedicated full chat instead of preview actions in either mode")

    replace_unique(panels,
        "interfaceInteraction: ChatPanelInterfaceInteraction?) -> (primary: ChatInputPanelNode?, secondary: ChatInputPanelNode?) {\n",
        "interfaceInteraction: ChatPanelInterfaceInteraction?, nagramiXReadOnly: Bool = false) -> (primary: ChatInputPanelNode?, secondary: ChatInputPanelNode?) {\n",
        "Carry the per-controller read-only policy into the native panel factory")
    replace_unique(panels,
        "    if case .pinnedMessages = chatPresentationInterfaceState.subject {\n",
        """    // Selection above uses the same native toolbar for one or many messages.
    // Avatar viewing still cannot create a composer or subscriber action panel.
    if nagramiXReadOnly {
        return (nil, nil)
    }

    if case .pinnedMessages = chatPresentationInterfaceState.subject {
""",
        "Allow selection actions without enabling composition or read receipts in avatar viewing")
    replace_unique(node,
        "        let inputPanelNodes = inputPanelForChatPresentationIntefaceState(self.chatPresentationInterfaceState, context: self.context, currentPanel: self.inputPanelNode, currentSecondaryPanel: self.secondaryInputPanelNode, textInputPanelNode: self.textInputPanelNode, chatControllerInteraction: self.controllerInteraction, interfaceInteraction: self.interfaceInteraction)\n",
        "        let inputPanelNodes = inputPanelForChatPresentationIntefaceState(self.chatPresentationInterfaceState, context: self.context, currentPanel: self.inputPanelNode, currentSecondaryPanel: self.secondaryInputPanelNode, textInputPanelNode: self.textInputPanelNode, chatControllerInteraction: self.controllerInteraction, interfaceInteraction: self.interfaceInteraction, nagramiXReadOnly: self.controller?.nagramiXReadHistoryDisabled == true)\n",
        "Bind panel layout to this avatar controller only")
    replace_unique(node,
        "        let inputNodeForState = inputNodeForChatPresentationIntefaceState(",
        "        let inputNodeForState = self.controller?.nagramiXReadHistoryDisabled == true ? nil : inputNodeForChatPresentationIntefaceState(",
        "Do not create a keyboard/media input node during read-only viewing")
    for variable, factory in [
        ("accessoryPanelNode", "accessoryPanelForChatPresentationIntefaceState"),
        ("inputContextPanelNode", "inputContextPanelForChatPresentationIntefaceState"),
        ("overlayContextPanelNode", "chatOverlayContextPanelForChatPresentationIntefaceState"),
    ]:
        replace_unique(node,
            f"        if let {variable} = {factory}(",
            f"        if let {variable} = self.controller?.nagramiXReadHistoryDisabled == true ? nil : {factory}(",
            f"Keep {variable} out of the dedicated read-only screen")

    replace_unique(chat,
        "    func sendMessages(_ messages: [EnqueueMessage], media: Bool = false, postpone: Bool = false, commit: Bool = false) {\n",
        """    func sendMessages(_ messages: [EnqueueMessage], media: Bool = false, postpone: Bool = false, commit: Bool = false) {
        guard !self.nagramiXReadHistoryDisabled else {
            return
        }
""",
        "Reject outgoing message actions from the read-only chat instance")
    replace_unique(chat,
        "            guard let self, NagramiXTabSettings.doubleTapEditEnabled, self.isNodeLoaded,\n",
        "            guard let self, !self.nagramiXReadHistoryDisabled, NagramiXTabSettings.doubleTapEditEnabled, self.isNodeLoaded,\n",
        "Keep double-tap editing, including Todo editing, out of read-only visits")
    replace_unique(load,
        """        self.chatDisplayNode.sendMessages = { [weak self] messages, silentPosting, scheduleTime, repeatPeriod, isAnyMessageTextPartitioned, postpone in
            guard let strongSelf = self else {
""",
        """        self.chatDisplayNode.sendMessages = { [weak self] messages, silentPosting, scheduleTime, repeatPeriod, isAnyMessageTextPartitioned, postpone in
            guard let strongSelf = self, !strongSelf.nagramiXReadHistoryDisabled else {
""",
        "Gate the native node enqueue callback as well as the controller send path")
    replace_unique(load,
        """        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage: { [weak self] messageId, innerSubject, completion in
            guard let strongSelf = self, strongSelf.isNodeLoaded else {
                return
            }
""",
        """        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage: { [weak self] messageId, innerSubject, completion in
            guard let strongSelf = self, strongSelf.isNodeLoaded else {
                return
            }
            if strongSelf.nagramiXReadHistoryDisabled {
                completion(.immediate, {})
                return
            }
""",
        "Do not enter reply composition from a read-only message context menu")
    replace_unique(load,
        """        }, setupEditMessage: { [weak self] messageId, completion in
            if let strongSelf = self, strongSelf.isNodeLoaded {
""",
        """        }, setupEditMessage: { [weak self] messageId, completion in
            if let strongSelf = self, strongSelf.isNodeLoaded {
                if strongSelf.nagramiXReadHistoryDisabled {
                    completion(.immediate)
                    return
                }
""",
        "Do not enter edit composition during an avatar-only visit")


def apply_copy_broadcast_split(source: Path) -> None:
    """Separate multi-recipient copies from single-recipient anonymous forwarding."""
    forwarding = source / "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift"
    interaction = source / "submodules/ChatPresentationInterfaceState/Sources/ChatPanelInterfaceInteraction.swift"
    load = source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
    menus = source / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"
    picker_node = source / "submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift"
    contacts = source / "submodules/ContactListUI/Sources/ContactListNode.swift"
    for path, markers in [
        (forwarding, ["forwardWithoutSource", "copyToSingleRecipient", "transferMode.copiesAsNew", "transferMode.singleRecipient", "!strongSelf.nagramiXReadHistoryDisabled", "!maybeChat.nagramiXReadHistoryDisabled"]),
        (interaction, ["forwardMessagesWithoutSource:", "self.forwardMessagesWithoutSource"]),
        (load, ["}, forwardMessagesWithoutSource:"]),
        (menus, ["nagramiXBroadcastMessages", "interfaceInteraction.forwardMessagesWithoutSource"]),
        (picker_node, ["Bound the local-copy fallback", "strongSelf.controller?.multipleSelectionLimit == 1, strongSelf.forwardedMessageIds.isEmpty"]),
        (contacts, ["nagramiXSelectionLimit"]),
    ]:
        if any(marker in path.read_text(encoding="utf-8") for marker in markers):
            raise SystemExit(f"Copy/broadcast split is already or partially applied: {path}")

    replace_unique(forwarding, "    case copyAsNew\n", """    case copyAsNew
    case forwardWithoutSource
    case copyToSingleRecipient

    var copiesAsNew: Bool {
        return self == .copyAsNew || self == .copyToSingleRecipient
    }

    var singleRecipient: Bool {
        return self == .forwardWithoutSource || self == .copyToSingleRecipient
    }
""", "Keep the former copy pipeline as broadcast and add explicit single-recipient modes")
    replace_unique(forwarding,
        "transferMode: hasArchivedMessages ? .copyAsNew : transferMode)",
        "transferMode: hasArchivedMessages ? (transferMode.singleRecipient ? .copyToSingleRecipient : .copyAsNew) : transferMode)",
        "Never forward a deleted server ID; preserve single-recipient intent for archived copies")
    replace_unique(forwarding,
        "hasFilters: true, attemptSelection: { peer, _, reason in\n",
        "hasFilters: transferMode != .copyToSingleRecipient, attemptSelection: { peer, _, reason in\n",
        "Use the native bounded flat list for the local-copy fallback")
    replace_unique(forwarding,
        "}, multipleSelection: true, forwardedMessageIds: transferMode == .forwardWithSource ? messages.map { $0.id } : [], selectForumThreads: true))\n",
        "}, multipleSelection: !transferMode.singleRecipient, multipleSelectionLimit: transferMode == .copyToSingleRecipient ? 1 : nil, forwardedMessageIds: transferMode.copiesAsNew ? [] : messages.map { $0.id }, selectForumThreads: true))\n",
        "Single anonymous forwarding has no multi-select; broadcast retains the previous selector")
    replace_unique(forwarding,
        """            controller.multiplePeersSelected = { [weak self, weak controller] peers, peerMap, messageText, mode, forwardOptions, _ in
                let peerIds = peers.map { $0.id }
""",
        """            controller.multiplePeersSelected = { [weak self, weak controller] peers, peerMap, messageText, mode, forwardOptions, _ in
                // Enforce the recipient contract before payments, scheduling or enqueue.
                guard !transferMode.singleRecipient || peers.count == 1 else {
                    return
                }
                let peerIds = peers.map { $0.id }
""", "Reject any multi-recipient callback for a single-recipient action")
    for old, new, label in [
        ("threadId: transferMode == .copyAsNew ? nil : strongSelf.chatLocation.threadId", "threadId: transferMode.copiesAsNew ? nil : strongSelf.chatLocation.threadId", "Keep copy comments detached from the source topic"),
        ("if transferMode == .copyAsNew, let threadId = nagramiXCopyThreadIds[peer.id]", "if transferMode.copiesAsNew, let threadId = nagramiXCopyThreadIds[peer.id]", "Apply destination topics to either copy mode"),
        ("guard transferMode == .copyAsNew else", "guard transferMode.copiesAsNew else", "Preserve copy-safe silent/schedule transformations for the local fallback"),
        ("if transferMode == .copyAsNew {", "if transferMode.copiesAsNew {", "Keep native copy send controls for broadcast and archived single-recipient copies"),
        ("                        case .forwardWithSource:\n", "                        case .forwardWithSource, .forwardWithoutSource:\n", "Use the native forward enqueue type for ordinary anonymous forwarding"),
        ("                        case .copyAsNew:\n", "                        case .copyAsNew, .copyToSingleRecipient:\n", "Preserve the existing snapshot copier in both local-copy modes"),
        ("ForwardOptionsMessageAttribute(hideNames: forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true)", "ForwardOptionsMessageAttribute(hideNames: transferMode == .forwardWithoutSource || forwardOptions?.hideNames == true, hideCaptions: forwardOptions?.hideCaptions == true)", "Hide the author for the explicit anonymous mode only"),
    ]:
        replace_unique(forwarding, old, new, label)
    replace_unique(forwarding,
        """                if case .peer(peerId) = strongSelf.chatLocation, strongSelf.parentController == nil, !isPinnedMessages {
""",
        """                if case .peer(peerId) = strongSelf.chatLocation, strongSelf.parentController == nil, !isPinnedMessages, !strongSelf.nagramiXReadHistoryDisabled, (transferMode != .forwardWithoutSource || threadId == nil) {
""", "Keep anonymous forwards out of read-only views and correctly route destination topics")
    replace_unique(forwarding,
        "                } else if peerId == strongSelf.context.account.peerId {\n",
        "                } else if peerId == strongSelf.context.account.peerId && transferMode != .forwardWithoutSource {\n",
        "Anonymous forwarding to Saved Messages also waits for explicit send")
    for prefix in ["$0.withUpdatedForwardMessageIds(messages.map { $0.id }).withUpdatedForwardOptionsState(", "return currentState.withUpdatedForwardMessageIds(messages.map { $0.id }).withUpdatedForwardOptionsState("]:
        replace_unique(forwarding,
            prefix + "ChatInterfaceForwardOptionsState(hideNames: !hasNotOwnMessages, hideCaptions: false, unhideNamesOnCaptionChange: false))",
            prefix + "ChatInterfaceForwardOptionsState(hideNames: transferMode == .forwardWithoutSource || !hasNotOwnMessages, hideCaptions: false, unhideNamesOnCaptionChange: false))",
            "Prepare the native destination draft with its author hidden for anonymous forwarding")
    replace_unique(forwarding,
        "                                    if !isChatPinnedMessages {\n",
        "                                    if !isChatPinnedMessages, !maybeChat.nagramiXReadHistoryDisabled, (transferMode != .forwardWithoutSource || maybeChat.chatLocation.threadId == threadId) {\n",
        "Only reuse an editable destination with the correct anonymous-forward topic")
    replace_unique(forwarding,
        """                                        maybeChat.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ $0.withUpdatedForwardMessageIds(messages.map { $0.id }).withoutSelectionState() }) })
""",
        """                                        maybeChat.updateChatPresentationInterfaceState(animated: false, interactive: true, { $0.updatedInterfaceState({ state in
                                            var state = state.withUpdatedForwardMessageIds(messages.map { $0.id }).withoutSelectionState()
                                            if transferMode == .forwardWithoutSource {
                                                state = state.withUpdatedForwardOptionsState(ChatInterfaceForwardOptionsState(hideNames: true, hideCaptions: false, unhideNamesOnCaptionChange: false))
                                            }
                                            return state
                                        }) })
""", "Reset stale forwarding author options on a reused anonymous destination")

    replace_unique(interaction, "    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n", "    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n    public let forwardMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n", "Expose the single-recipient action separately from broadcast copies")
    replace_unique(interaction, "        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n", "        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n        forwardMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n", "Keep existing interaction initializers compatible")
    replace_unique(interaction, "        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n", "        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n        self.forwardMessagesWithoutSource = forwardMessagesWithoutSource\n", "Store the single-recipient forwarding callback")
    replace_unique(load, "        }, selectMessagesByAuthor: { [weak self] authorId in\n", """        }, forwardMessagesWithoutSource: { [weak self] messages in
            guard let self, !messages.isEmpty else {
                return
            }
            guard !self.presentAccountFrozenInfoIfNeeded(delay: true) else {
                return
            }
            self.commitPurposefulAction()
            if messages.contains(where: { $0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) }) {
                self.forwardMessages(messages: messages.sorted(by: { $0.id < $1.id }), resetCurrent: false, transferMode: .copyToSingleRecipient)
            } else {
                self.forwardMessages(messageIds: messages.map { $0.id }.sorted(), transferMode: .forwardWithoutSource)
            }
        }, selectMessagesByAuthor: { [weak self] authorId in
""", "Wire the single-recipient action without changing the existing broadcast callback")

    old = """                if NagramiXTabSettings.current.showForwardWithoutAuthor {
                    let canForwardWithoutAuthor = interfaceInteraction.copyMessagesWithoutSource != nil
                        && nagramiXCanCopyMessagesAsNew(messagesToForward)
                    actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, textColor: canForwardWithoutAuthor ? .primary : .disabled, icon: { _ in
                        return nil
                    }, iconAnimation: ContextMenuActionItem.IconAnimation(name: "message_preview_person_off"), action: !canForwardWithoutAuthor ? nil : { _, f in
                        interfaceInteraction.copyMessagesWithoutSource?(messagesToForward)
                        f(.dismissWithoutContent)
                    })))
                }
"""
    single = old.replace("interfaceInteraction.copyMessagesWithoutSource", "interfaceInteraction.forwardMessagesWithoutSource")
    broadcast = old.replace(".showForwardWithoutAuthor", ".showBroadcastMessages").replace("strings.nagramiXForwardWithoutAuthor", "strings.nagramiXBroadcastMessages")
    replace_unique(menus, old, single + broadcast, "Show anonymous forwarding and broadcast as separate native menu actions")
    old = """            if NagramiXTabSettings.current.showForwardWithoutAuthor, nagramiXCanCopyMessagesAsNew([message]), let copyMessagesWithoutSource = interfaceInteraction.copyMessagesWithoutSource {
                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXForwardWithoutAuthor, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
                }, action: { _, f in
                    copyMessagesWithoutSource(selectAll ? messages : [message])
                    f(.dismissWithoutContent)
                })))
            }
"""
    single = old.replace("nagramiXCanCopyMessagesAsNew([message])", "nagramiXCanCopyMessagesAsNew(selectAll ? messages : [message])").replace("copyMessagesWithoutSource", "forwardMessagesWithoutSource")
    broadcast = old.replace(".showForwardWithoutAuthor", ".showBroadcastMessages").replace("strings.nagramiXForwardWithoutAuthor", "strings.nagramiXBroadcastMessages").replace("nagramiXCanCopyMessagesAsNew([message])", "nagramiXCanCopyMessagesAsNew(selectAll ? messages : [message])")
    replace_unique(menus, old, single + broadcast, "Keep both copy actions for archived snapshots without forwarding deleted IDs")

    # Only the archived single-recipient fallback uses this bounded native picker.
    replace_unique(contacts, "    public var multipleSelection = false\n", "    public var multipleSelection = false\n    public var nagramiXSelectionLimit: Int?\n", "Add an opt-in contact selection bound without changing other pickers")
    replace_unique(contacts, "        let updatedSelectionState = f(self.selectionStateValue)\n", """        let updatedSelectionState = f(self.selectionStateValue)
        if let limit = self.nagramiXSelectionLimit, let updatedSelectionState, updatedSelectionState.selectedPeerIndices.count > limit {
            return
        }
""", "Apply the explicit bound to contact taps, search and selection updates")
    replace_unique(picker_node, "    func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {\n", """    func nagramiXSelectCopyRecipient(_ peer: EnginePeer) {
        // Bound the local-copy fallback in both native destination lists.
        if self.controller?.multipleSelectionLimit == 1 {
            self.contactListNode?.nagramiXSelectionLimit = 1
            let chatListNode = self.mainContainerNode?.currentItemNode ?? self.chatListNode
            chatListNode?.selectionLimit = 1
        }
""", "Bound only the single archived-copy recipient picker")
    replace_unique(picker_node, """                                updated = true
                                var state = state
                                var foundPeers = state.foundPeers
""", """                                if strongSelf.controller?.multipleSelectionLimit == 1, strongSelf.forwardedMessageIds.isEmpty,
                                   !state.selectedPeerIds.contains(peer.id), state.selectedPeerIds.count >= 1 {
                                    ignoredSelectionContainer = true
                                    return state
                                }
                                updated = true
                                var state = state
                                var foundPeers = state.foundPeers
""", "Keep global-search insertion inside the single archived-copy bound")


def apply_archived_round_video_fix(source: Path) -> None:
    """Keep one native round-video surface, stable ownership and stock controls."""
    native = source / "submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift"
    decoration = source / "submodules/TelegramUniversalVideoContent/Sources/ChatBubbleInstantVideoDecoration.swift"
    embedded = source / "submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift"
    shared = source / "submodules/TelegramUI/Sources/SharedMediaPlayer.swift"
    for path in (native, decoration, embedded, shared):
        if any(marker in path.read_text(encoding="utf-8") for marker in ("nagramiXArchivedInstantVideo", "NagramiXArchivedInstantVideo", "nagramiXArchivedMessageId", "nagramiXIsArchivedInstantVideo")):
            raise SystemExit(f"Archived round-video overlay is already or partially applied: {path}")

    replace_unique(native, "public final class NativeVideoContent: UniversalVideoContent {\n", """private struct NagramiXArchivedInstantVideoId: Hashable {
    let messageId: MessageId
    let fileId: MediaId
    let resourceId: MediaResourceId
}

public final class NativeVideoContent: UniversalVideoContent {
    private let nagramiXArchivedInstantVideo: Bool
""", "Use the full archive identity shared by embedded video and native playlist")
    replace_unique(native,
        "hasSentFramesToDisplay: (() -> Void)? = nil) {\n        self.id = id\n",
        """hasSentFramesToDisplay: (() -> Void)? = nil, nagramiXArchivedMessageId: MessageId? = nil) {
        if let messageId = nagramiXArchivedMessageId, fileReference.media.isInstantVideo {
            self.nagramiXArchivedInstantVideo = true
            self.id = AnyHashable(NagramiXArchivedInstantVideoId(messageId: messageId, fileId: fileReference.media.fileId, resourceId: fileReference.media.resource.id))
        } else {
            self.nagramiXArchivedInstantVideo = false
            self.id = id
        }
""", "Keep one archive decoder across rerenders without changing ordinary content IDs")
    replace_unique(native,
        "displayImage: self.displayImage, hasSentFramesToDisplay: self.hasSentFramesToDisplay)\n",
        "displayImage: self.displayImage, hasSentFramesToDisplay: self.hasSentFramesToDisplay, nagramiXArchivedInstantVideo: self.nagramiXArchivedInstantVideo)\n",
        "Pass the archive presentation flag to the existing native decoder")
    replace_unique(native,
        "    private let hasSentFramesToDisplay: (() -> Void)?\n",
        "    private let hasSentFramesToDisplay: (() -> Void)?\n    private let nagramiXArchivedInstantVideo: Bool\n    private var nagramiXArchivedInstantVideoHasFrame = false\n",
        "Track archive poster lifetime without creating a player")
    replace_unique(native,
        "displayImage: Bool, hasSentFramesToDisplay: (() -> Void)?) {\n        self.postbox = postbox\n",
        "displayImage: Bool, hasSentFramesToDisplay: (() -> Void)?, nagramiXArchivedInstantVideo: Bool = false) {\n        self.nagramiXArchivedInstantVideo = nagramiXArchivedInstantVideo\n        self.postbox = postbox\n",
        "Leave all existing nonarchive decoder callers on their stock defaults")
    replace_unique(native,
        """            didProcessFramesToDisplay = true
            self.playerNode.isHidden = false
            self.hasSentFramesToDisplay?()
""",
        """            didProcessFramesToDisplay = true
            self.playerNode.isHidden = false
            if self.nagramiXArchivedInstantVideo {
                // The poster must not show through a semi-transparent live frame.
                self.nagramiXArchivedInstantVideoHasFrame = true
                self.imageNode.isHidden = true
            }
            self.hasSentFramesToDisplay?()
""", "Remove the static poster only after an actual archive video frame is ready")
    replace_unique(native,
        "    private func createThumbnailPlayer() {\n        guard let videoThumbnail",
        """    private func createThumbnailPlayer() {
        if self.nagramiXArchivedInstantVideo {
            // Retained full video uses the same main decoder for preview/playback.
            return
        }
        guard let videoThumbnail""", "Prevent an additional moving thumbnail beneath transparent archived video")
    replace_unique(native,
        """    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        self.validLayout = (size, actualSize)
""",
        """    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        let transition: ContainedViewLayoutTransition = self.nagramiXArchivedInstantVideo ? .immediate : transition
        if self.nagramiXArchivedInstantVideo {
            // Animate the outer native circle, not a second inner renderer scale.
            for key in ["transform", "position", "bounds"] {
                self.playerNode.layer.removeAnimation(forKey: key)
                self.imageNode.layer.removeAnimation(forKey: key)
            }
        }
        self.validLayout = (size, actualSize)
""", "Keep archive renderer and poster geometry synchronized during ownership changes")
    replace_unique(native,
        "        self.imageNode.isHidden = value\n",
        "        self.imageNode.isHidden = value || (self.nagramiXArchivedInstantVideo && self.nagramiXArchivedInstantVideoHasFrame)\n",
        "Do not resurrect the archive poster when native PiP state resets")

    replace_unique(decoration,
        "    private let inset: CGFloat\n",
        "    private let inset: CGFloat\n    private let nagramiXArchivedInstantVideo: Bool\n",
        "Keep archived clipping geometry independent of the outer scale animation")
    replace_unique(decoration,
        """    public init(inset: CGFloat, backgroundImage: UIImage?, tapped: @escaping () -> Void) {
        self.inset = inset
""",
        """    public init(inset: CGFloat, backgroundImage: UIImage?, nagramiXArchivedInstantVideo: Bool = false, tapped: @escaping () -> Void) {
        self.nagramiXArchivedInstantVideo = nagramiXArchivedInstantVideo
        self.inset = inset
""", "Preserve stock decoration callers and gestures")
    replace_unique(decoration,
        """    public func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        self.validLayout = (size, actualSize)
""",
        """    public func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        let transition: ContainedViewLayoutTransition = self.nagramiXArchivedInstantVideo ? .immediate : transition
        if self.nagramiXArchivedInstantVideo {
            for key in ["transform", "position", "bounds", "cornerRadius"] {
                self.contentContainerNode.layer.removeAnimation(forKey: key)
                self.contentNode?.layer.removeAnimation(forKey: key)
            }
        }
        self.validLayout = (size, actualSize)
""", "Size the archive clip and content together; keep the stock outer circle animation")

    replace_unique(embedded,
        "    private var videoNode: UniversalVideoNode?\n",
        """    private var videoNode: UniversalVideoNode?
    private var nagramiXIsArchivedInstantVideo: Bool {
        return self.item?.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) == true
    }
""", "Base archived activation on playback state instead of the animated mute badge")
    replace_unique(embedded,
        """            var ignoreForward = false
            var ignoreSource = false
""",
        """            let nagramiXArchivedInstantVideo = item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
            let previouslyArchived = currentItem?.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) == true
            if nagramiXArchivedInstantVideo || previouslyArchived {
                updatedMedia = updatedMedia || updatedMessageId || nagramiXArchivedInstantVideo != previouslyArchived
            }

            var ignoreForward = false
            var ignoreSource = false
""", "Recreate only changed archive ownership and reset flags when a normal row is reused")
    replace_unique(embedded,
        """                            if let videoNode = strongSelf.videoNode {
                                videoNode.layer.allowsGroupOpacity = true
                                videoNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.5, delay: 0.2, removeOnCompletion: false, completion: { [weak videoNode] _ in
                                    videoNode?.removeFromSupernode()
                                })
                            }
""",
        """                            if let videoNode = strongSelf.videoNode {
                                if nagramiXArchivedInstantVideo || previouslyArchived {
                                    // Do not leave the previous moving circle behind the local copy.
                                    videoNode.canAttachContent = false
                                    videoNode.removeFromSupernode()
                                    previousVideoNode = nil
                                } else {
                                    videoNode.layer.allowsGroupOpacity = true
                                    videoNode.layer.animateAlpha(from: 1.0, to: 0.0, duration: 0.5, delay: 0.2, removeOnCompletion: false, completion: { [weak videoNode] _ in
                                        videoNode?.removeFromSupernode()
                                    })
                                }
                            }
""", "Release the old archive renderer before installing its replacement")
    replace_unique(embedded,
        "ChatBubbleInstantVideoDecoration(inset: 2.0, backgroundImage: instantVideoBackgroundImage, tapped: {\n",
        "ChatBubbleInstantVideoDecoration(inset: 2.0, backgroundImage: instantVideoBackgroundImage, nagramiXArchivedInstantVideo: nagramiXArchivedInstantVideo, tapped: {\n",
        "Opt only archived circles into synchronized native clipping")
    replace_unique(embedded,
        """                                    if let item = strongSelf.item {
                                        if strongSelf.infoBackgroundNode.alpha.isZero {
""",
        """                                    if let item = strongSelf.item {
                                        if strongSelf.nagramiXIsArchivedInstantVideo {
                                            strongSelf.activateVideoPlayback()
                                            return
                                        }
                                        if strongSelf.infoBackgroundNode.alpha.isZero {
""", "Route archive decoration taps through the same native playback-state action")
    replace_unique(embedded,
        "storeAfterDownload: nil), priority: item.associatedData.isStandalone ? .overlay : .embedded",
        "storeAfterDownload: nil, nagramiXArchivedMessageId: nagramiXArchivedInstantVideo ? item.message.id : nil), priority: item.associatedData.isStandalone ? .overlay : .embedded",
        "Bind the embedded retained video to the full archive identity")
    replace_unique(embedded,
        """                            strongSelf.videoNode = videoNode
                            strongSelf.insertSubnode(videoNode, belowSubnode: previousVideoNode ?? strongSelf.dateAndStatusNode)
""",
        """                            if nagramiXArchivedInstantVideo || previouslyArchived {
                                // A replacement starts with identity transform; apply the
                                // current outer scale even when imageScale did not change.
                                videoNode.transform = CATransform3DMakeScale(imageScale, imageScale, 1.0)
                                strongSelf.imageScale = imageScale
                            }
                            strongSelf.videoNode = videoNode
                            strongSelf.insertSubnode(videoNode, belowSubnode: previousVideoNode ?? strongSelf.dateAndStatusNode)
""", "Initialize every archive replacement at its actual collapsed or expanded size")
    replace_unique(shared,
        "captureProtected: item.message.isCopyProtected(), storeAfterDownload: nil), close:",
        "captureProtected: item.message.isCopyProtected(), storeAfterDownload: nil, nagramiXArchivedMessageId: item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) ? item.message.id : nil), close:",
        "Use the exact same decoder identity for the stock shared playlist")
    replace_unique(embedded,
        """        guard let item = self.item, self.shouldOpen() else {
            return
        }
        if self.infoBackgroundNode.alpha.isZero {
""",
        """        guard let item = self.item, self.shouldOpen() else {
            return
        }
        if self.nagramiXIsArchivedInstantVideo {
            if let status = self.status, case .playbackStatus = status.mediaStatus {
                item.context.sharedContext.mediaManager.playlistControl(.playback(.togglePlayPause), type: .voice)
            } else {
                // Open the supplied snapshot on the first action, even while the
                // mute badge or local-file status is still updating.
                let _ = item.controllerInteraction.openMessage(item.message, OpenMessageParams(mode: .default))
            }
            return
        }
        if self.infoBackgroundNode.alpha.isZero {
""", "Start or toggle archived video using the native playlist rather than a cosmetic alpha")


def apply_photo_jpeg_compatibility_fix(source: Path) -> None:
    """Keep photo quality while restoring the progressive JPEG cache contract."""
    binding = source / "submodules/MozjpegBinding/Sources/MozjpegBinding.mm"
    header = source / "submodules/MozjpegBinding/Public/MozjpegBinding/MozjpegBinding.h"
    encoder = source / "submodules/ImageCompression/Sources/ImageCompression.swift"
    photos = source / "submodules/PhotoResources/Sources/PhotoResources.swift"
    picker = source / "submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift"
    fetch = source / "submodules/LocalMediaResources/Sources/FetchPhotoLibraryImageResource.swift"
    root = source / "submodules/TelegramUI/Sources/TelegramRootController.swift"
    for path in (binding, header, encoder, photos, picker, fetch, root):
        if any(marker in path.read_text(encoding="utf-8") for marker in ("NagramiXJPEG", "nagramiXCompressImageToJPEG", "nagramiXProgressivePhotoData", "compressJPEGDataWithQuality")):
            raise SystemExit(f"Photo JPEG compatibility overlay is already or partially applied: {path}")
    if binding.read_text(encoding="utf-8").count("#define USE_JPEGLI false\n") != 1:
        raise SystemExit("Photo JPEG compatibility requires the pinned native mozjpeg backend")
    if "#include <setjmp.h>\n" in binding.read_text(encoding="utf-8"):
        raise SystemExit("Photo JPEG compatibility error handling is already or partially applied")

    replace_unique(header,
        "NSData * _Nullable compressJPEGData(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath);\n",
        "NSData * _Nullable compressJPEGData(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath);\nNSData * _Nullable compressJPEGDataWithQuality(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath, int quality);\n",
        "Expose quality without losing native progressive JPEG scans")
    replace_unique(binding, "#include <limits.h>\n", "#include <limits.h>\n#include <setjmp.h>\n#include <stdint.h>\n", "Recover native JPEG errors instead of terminating the process")
    encoder_text = binding.read_text(encoding="utf-8")
    encoder_start = "#else\nNSData * _Nullable compressJPEGData(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath) {"
    if encoder_text.count(encoder_start) != 1:
        raise SystemExit("Pinned mozjpeg encoder range was not found")
    old_encoder = encoder_start + encoder_text.split(encoder_start, 1)[1].split("\n#endif", 1)[0] + "\n#endif"
    if hashlib.sha256(old_encoder.encode("utf-8")).hexdigest() != "54daecabba0ff16a4ac7c0233c535e74fadd9ab415f6eded84f750bc271ccf69":
        raise SystemExit("Pinned mozjpeg encoder bytes have changed")
    replace_unique(binding, old_encoder, """#else
struct NagramiXJPEGError {
    struct jpeg_error_mgr base;
    jmp_buf recovery;
};

struct NagramiXJPEGState {
    struct jpeg_compress_struct compressor;
    struct NagramiXJPEGError error;
    bool compressorCreated;
    FILE *file;
    uint8_t *buffer;
};

static void NagramiXJPEGErrorExit(j_common_ptr info) {
    struct NagramiXJPEGError *error = (struct NagramiXJPEGError *)info->err;
    longjmp(error->recovery, 1);
}

static void NagramiXJPEGDispose(struct NagramiXJPEGState *state) {
    if (state->compressorCreated) {
        jpeg_destroy_compress(&state->compressor);
    }
    if (state->file != NULL) {
        fclose(state->file);
    }
    free(state->buffer);
    free(state);
}

NSData * _Nullable compressJPEGDataWithQuality(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath, int quality) {
    CGImageRef image = sourceImage.CGImage;
    if (image == NULL) {
        return nil;
    }
    size_t width = CGImageGetWidth(image);
    size_t height = CGImageGetHeight(image);
    if (width == 0 || height == 0 || width > JPEG_MAX_DIMENSION || height > JPEG_MAX_DIMENSION) {
        return nil;
    }
    size_t targetBytesPerRow = (4 * width + 31) & ~(size_t)31;
    size_t bufferBytesPerRow = (3 * width + 31) & ~(size_t)31;
    if (height > SIZE_MAX / targetBytesPerRow || height > SIZE_MAX / bufferBytesPerRow) {
        return nil;
    }

    uint8_t *targetMemory = (uint8_t *)calloc(height, targetBytesPerRow);
    if (targetMemory == NULL) {
        return nil;
    }
    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
    CGContextRef targetContext = colorSpace == NULL ? NULL : CGBitmapContextCreate(targetMemory, width, height, 8, targetBytesPerRow, colorSpace, kCGImageAlphaNoneSkipFirst | kCGBitmapByteOrder32Host);
    if (colorSpace != NULL) {
        CGColorSpaceRelease(colorSpace);
    }
    if (targetContext == NULL) {
        free(targetMemory);
        return nil;
    }
    CGContextDrawImage(targetContext, CGRectMake(0, 0, width, height), image);
    CGContextRelease(targetContext);

    struct NagramiXJPEGState *state = (struct NagramiXJPEGState *)calloc(1, sizeof(struct NagramiXJPEGState));
    if (state == NULL) {
        free(targetMemory);
        return nil;
    }
    state->buffer = (uint8_t *)malloc(bufferBytesPerRow * height);
    if (state->buffer == NULL) {
        free(targetMemory);
        NagramiXJPEGDispose(state);
        return nil;
    }
    for (size_t y = 0; y < height; y++) {
        for (size_t x = 0; x < width; x++) {
            uint32_t color = *((uint32_t *)&targetMemory[y * targetBytesPerRow + x * 4]);
            state->buffer[y * bufferBytesPerRow + x * 3] = (color >> 16) & 0xff;
            state->buffer[y * bufferBytesPerRow + x * 3 + 1] = (color >> 8) & 0xff;
            state->buffer[y * bufferBytesPerRow + x * 3 + 2] = color & 0xff;
        }
    }
    free(targetMemory);

    state->file = fopen([tempFilePath fileSystemRepresentation], "wb");
    if (state->file == NULL) {
        NagramiXJPEGDispose(state);
        return nil;
    }
    state->compressor.err = jpeg_std_error(&state->error.base);
    state->error.base.error_exit = NagramiXJPEGErrorExit;
    // Mutable recovery state lives on the heap, so longjmp cannot invalidate it.
    if (setjmp(state->error.recovery)) {
        NagramiXJPEGDispose(state);
        [[NSFileManager defaultManager] removeItemAtPath:tempFilePath error:nil];
        return nil;
    }
    state->compressorCreated = true;
    jpeg_create_compress(&state->compressor);
    jpeg_stdio_dest(&state->compressor, state->file);
    state->compressor.image_width = (JDIMENSION)width;
    state->compressor.image_height = (JDIMENSION)height;
    state->compressor.input_components = 3;
    state->compressor.in_color_space = JCS_RGB;
    jpeg_c_set_int_param(&state->compressor, JINT_COMPRESS_PROFILE, JCP_FASTEST);
    jpeg_set_defaults(&state->compressor);
    state->compressor.arith_code = FALSE;
    state->compressor.dct_method = JDCT_ISLOW;
    state->compressor.optimize_coding = TRUE;
    jpeg_set_quality(&state->compressor, MAX(0, MIN(100, quality)), 1);
    jpeg_simple_progression(&state->compressor);
    jpeg_start_compress(&state->compressor, 1);
    JSAMPROW rowPointer[1];
    while (state->compressor.next_scanline < state->compressor.image_height) {
        rowPointer[0] = (JSAMPROW)(state->buffer + state->compressor.next_scanline * bufferBytesPerRow);
        jpeg_write_scanlines(&state->compressor, rowPointer, 1);
    }
    jpeg_finish_compress(&state->compressor);
    bool fileComplete = fclose(state->file) == 0;
    state->file = NULL;
    NagramiXJPEGDispose(state);
    NSData *result = fileComplete ? [[NSData alloc] initWithContentsOfFile:tempFilePath] : nil;
    [[NSFileManager defaultManager] removeItemAtPath:tempFilePath error:nil];
    return result;
}

NSData * _Nullable compressJPEGData(UIImage * _Nonnull sourceImage, NSString * _Nonnull tempFilePath) {
    // Existing Telegram callers keep the native encoder's original quality.
    return compressJPEGDataWithQuality(sourceImage, tempFilePath, 72);
}
#endif""", "Preserve native progression and safely handle JPEG allocation/file/codec errors")

    replace_unique(encoder, "public func compressImageToJPEGXL(_ image: UIImage, quality: Int) -> Data? {\n", """public func nagramiXCompressImageToJPEG(_ image: UIImage, quality: Float, tempFilePath: String) -> Data? {
    guard quality.isFinite else {
        return nil
    }
    return autoreleasepool {
        let percentage = Int32((min(1.0, max(0.0, quality)) * 100.0).rounded())
        return compressJPEGDataWithQuality(image, tempFilePath, percentage)
    }
}

public func compressImageToJPEGXL(_ image: UIImage, quality: Int) -> Data? {
""", "Encode outgoing photos with native progressive JPEG and selected quality")
    replace_unique(picker, "scaledImage.jpegData(compressionQuality: CGFloat(mediaSettings.jpegQuality))", "nagramiXCompressImageToJPEG(scaledImage, quality: Float(mediaSettings.jpegQuality), tempFilePath: tempFile.path)", "Restore progressive prepared photo encoding")
    replace_unique(picker,
        """                                            let _ = try? scaledImageData.write(to: URL(fileURLWithPath: tempFilePath))

                                            let resource = LocalFileReferenceMediaResource(localFilePath: tempFilePath, randomId: randomId)
""",
        """                                            do {
                                                try scaledImageData.write(to: URL(fileURLWithPath: tempFilePath), options: .atomic)
                                            } catch {
                                                subscriber.putError(Void())
                                                return
                                            }

                                            let resource = LocalFileReferenceMediaResource(localFilePath: tempFilePath, randomId: randomId)
""", "Never enqueue a missing or partially written prepared photo")
    replace_unique(fetch, "scaledImage.jpegData(compressionQuality: CGFloat(mediaSettings.jpegQuality))", "nagramiXCompressImageToJPEG(scaledImage, quality: Float(mediaSettings.jpegQuality), tempFilePath: tempFile.path)", "Restore progressive photo library encoding")
    replace_unique(root, "image.jpegData(compressionQuality: CGFloat(NagramiXMediaSettings.current.jpegQuality))", "nagramiXCompressImageToJPEG(image, quality: Float(NagramiXMediaSettings.current.jpegQuality), tempFilePath: tempFile.path)", "Keep final photo story JPEG compatible with native caches")

    replace_unique(photos,
        """        return Signal { subscriber in
            let signals: [Signal<(SizeSource, Data?), NoError>] = sources.map { source -> Signal<(SizeSource, Data?), NoError> in
""",
        """        let nagramiXProgressivePhotoData = Signal<Tuple4<Data?, Data?, ChatMessagePhotoQuality, Bool>, NoError> { subscriber in
            let signals: [Signal<(SizeSource, Data?), NoError>] = sources.map { source -> Signal<(SizeSource, Data?), NoError> in
""", "Keep stock incremental fetching for actual progressive resources")
    replace_unique(photos,
        """            return ActionDisposable {
                dataDisposable.dispose()
                fetchDisposable?.dispose()
            }
        }
    }
\x20\x20\x20\x20
    if !forceThumbnail || photoReference.media.immediateThumbnailData == nil,""",
        """            return ActionDisposable {
                dataDisposable.dispose()
                fetchDisposable?.dispose()
            }
        }
        // A complete cached upload can differ from the server's JPEG bytes
        // and scan offsets (older uploads are sequential). Always decode the
        // whole cached JPEG; incomplete resources keep native progressive fetch.
        return mediaBox.resourceData(progressiveRepresentation.resource, option: .complete(waitUntilFetchStatus: false), attemptSynchronously: synchronousLoad)
        |> take(1)
        |> mapToSignal { cached -> Signal<Tuple4<Data?, Data?, ChatMessagePhotoQuality, Bool>, NoError> in
            if cached.complete, cached.size > 0,
               let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: cached.path) as CFURL, nil),
               let type = CGImageSourceGetType(source), type as String == "public.jpeg",
               let data = try? Data(contentsOf: URL(fileURLWithPath: cached.path), options: .mappedIfSafe), !data.isEmpty {
                return .single(Tuple4(nil, data, .full, true))
            }
            return nagramiXProgressivePhotoData
        }
    }
\x20\x20\x20\x20
    if !forceThumbnail || photoReference.media.immediateThumbnailData == nil,""", "Decode complete cached JPEG without offsets from a different server byte stream")


def apply_background_video_hierarchy_fix(source: Path) -> None:
    """Keep the existing decoder running without PiP and compose lifecycle owners."""
    universal = source / "submodules/AccountContext/Sources/UniversalVideoNode.swift"
    gallery = source / "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"
    backends = [source / "submodules/TelegramUniversalVideoContent/Sources" / name for name in ("NativeVideoContent.swift", "HLSVideoJSNativeContentNode.swift")]
    for path in [universal, gallery] + backends:
        text = path.read_text(encoding="utf-8")
        if "nagramiXBackgroundPlayback" in text or "setNagramiXBackgroundPlayback" in text:
            raise SystemExit(f"Background hierarchy overlay is already or partially applied: {path}")

    replace_unique(universal,
        "    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool)\n",
        "    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool)\n    func setNagramiXBackgroundPlayback(id: UUID, active: Bool)\n",
        "Expose an independent background owner without changing native PiP callers")
    replace_unique(universal,
        "public protocol UniversalVideoContent {\n",
        """public extension UniversalVideoContentNode {
    // Only ordinary native/HLS videos opt in; other content keeps its stock path.
    func setNagramiXBackgroundPlayback(id: UUID, active: Bool) {
    }
}

public protocol UniversalVideoContent {
""", "Keep every other video content implementation source-compatible")
    replace_unique(universal,
        "    private var contentNodeId: Int32?\n",
        "    private var contentNodeId: Int32?\n    private var nagramiXBackgroundPlaybackOwners = Set<UUID>()\n",
        "Remember only this wrapper's background owner tokens for cleanup")
    replace_unique(universal,
        """    deinit {
        assert(Queue.mainQueue().isCurrent())
""",
        """    deinit {
        assert(Queue.mainQueue().isCurrent())
        let backgroundOwners = self.nagramiXBackgroundPlaybackOwners
        self.manager.withUniversalVideoContent(id: self.content.id, { contentNode in
            for id in backgroundOwners {
                contentNode?.setNagramiXBackgroundPlayback(id: id, active: false)
            }
        })
""", "Release wrapper-owned tokens before detaching a shared decoder")
    replace_unique(universal,
        "    public func enterNativePictureInPicture() -> Bool {\n",
        """    public func setNagramiXBackgroundPlayback(id: UUID, active: Bool) {
        if active {
            self.nagramiXBackgroundPlaybackOwners.insert(id)
        } else {
            self.nagramiXBackgroundPlaybackOwners.remove(id)
        }
        self.manager.withUniversalVideoContent(id: self.content.id, { contentNode in
            contentNode?.setNagramiXBackgroundPlayback(id: id, active: active)
        })
    }

    public func enterNativePictureInPicture() -> Bool {
""", "Forward the gallery claim to its existing shared native decoder")

    for backend in backends:
        replace_unique(backend,
            """    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool) {
        self.playerNode.setCanPlaybackWithoutHierarchy(canPlaybackWithoutHierarchy)
    }
""",
            """    private var nagramiXNativePlaybackWithoutHierarchy = false
    private var nagramiXBackgroundPlaybackOwners = Set<UUID>()

    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool) {
        self.nagramiXNativePlaybackWithoutHierarchy = canPlaybackWithoutHierarchy
        if self.nagramiXBackgroundPlaybackOwners.isEmpty {
            self.playerNode.setCanPlaybackWithoutHierarchy(canPlaybackWithoutHierarchy)
        }
    }

    func setNagramiXBackgroundPlayback(id: UUID, active: Bool) {
        let wasAllowed = self.nagramiXNativePlaybackWithoutHierarchy || !self.nagramiXBackgroundPlaybackOwners.isEmpty
        if active {
            self.nagramiXBackgroundPlaybackOwners.insert(id)
        } else {
            self.nagramiXBackgroundPlaybackOwners.remove(id)
        }
        let isAllowed = self.nagramiXNativePlaybackWithoutHierarchy || !self.nagramiXBackgroundPlaybackOwners.isEmpty
        if isAllowed != wasAllowed {
            self.playerNode.setCanPlaybackWithoutHierarchy(isAllowed)
        }
    }
""", "Combine native PiP and gallery background requests; removing one must not stop the other")

    replace_unique(gallery,
        "    private let nagramiXBackgroundVideoId = UUID()\n",
        """    private let nagramiXBackgroundVideoId = UUID()
    private weak var nagramiXBackgroundPlaybackVideoNode: UniversalVideoNode?
    private var nagramiXBackgroundPlaybackObserver: NSObjectProtocol?
""", "Observe live settings and remember the current decoder without retaining it")
    replace_unique(gallery,
        """    deinit {
        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: false)
""",
        """    deinit {
        if let observer = self.nagramiXBackgroundPlaybackObserver {
            NotificationCenter.default.removeObserver(observer)
        }
        self.nagramiXBackgroundPlaybackVideoNode?.setNagramiXBackgroundPlayback(id: self.nagramiXBackgroundVideoId, active: false)
        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: false)
""", "Remove only this gallery's claim and observer when it closes")
    replace_unique(gallery,
        """    private func nagramiXUpdateBackgroundVideoPlayback() {
        var active = false
""",
        """    private func nagramiXUpdateBackgroundVideoPlayback() {
        if self.nagramiXBackgroundPlaybackObserver == nil {
            self.nagramiXBackgroundPlaybackObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
                self?.nagramiXUpdateBackgroundVideoPlayback()
            })
        }
        if self.nagramiXBackgroundPlaybackVideoNode !== self.videoNode {
            self.nagramiXBackgroundPlaybackVideoNode?.setNagramiXBackgroundPlayback(id: self.nagramiXBackgroundVideoId, active: false)
            self.nagramiXBackgroundPlaybackVideoNode = self.videoNode
        }
        var active = false
""", "Release the previous decoder on replacement and apply preferences without restarting playback")
    replace_unique(gallery,
        "        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: active)\n",
        """        // Keeping the audio session alone does not keep the native video renderer
        // requesting frames outside UIKit hierarchy. PiP's permission is independent.
        self.videoNode?.setNagramiXBackgroundPlayback(id: self.nagramiXBackgroundVideoId, active: active && NagramiXTabSettings.backgroundVideoPlaybackEnabled)
        self.context.sharedContext.mediaManager.setNagramiXBackgroundVideoPlayback(id: self.nagramiXBackgroundVideoId, active: active)
""", "Keep ordinary audible playing/buffering videos running outside the visible hierarchy")


def apply_archived_replay_and_upload_cache_fix(source: Path) -> None:
    """Reconcile retained playback ownership and reuse newly uploaded copies."""
    guards = {
        "submodules/TelegramUI/Components/TelegramAccountAuxiliaryMethods/Sources/TelegramAccountAuxiliaryMethods.swift": "cc62afc1194c96e0f5ada73fcb929d1cd46cb977951451ad9116dc4342cd7154",
        "submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift": "9be382e766609b3f87cb94fdb7776bb4d02086b94c957397399a83eb8f254ac2",
        "submodules/TelegramUniversalVideoContent/Sources/ChatBubbleInstantVideoDecoration.swift": "d18a6377f6cdde228fb97f991ff86550be30416921c9f7c2ce4058e34343c956",
        "submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift": "56b715fc11bb4f9dc22b056d3a1261274642ccce8686d70a1b8a75248f04da4c",
        "submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift": "e92ace342bd0aba4532bd88682c14ecc641174b71e7cb00ceaa480500b82c78f",
        "submodules/AccountContext/BUILD": "5f3668ee2377aa5ed6b17e1584b99110b7b9e84258b345a1ba886470aa4b3d65",
        "submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift": "33af54cb6ff6c8ac2b75797beee1c70296b66f885a89707d7a0469d4590bfd04",
        "submodules/TelegramCore/Sources/State/Fetch.swift": "21d980292238115727ad078a4d3f1eba34f47432d207fe3e403a62fd924c2b2e",
    }
    texts = {}
    for name, expected in guards.items():
        data = (source / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная архивная replay интеграция или правка уже применена: {name}")
        texts[name] = data.decode("utf-8")
    overlay = Path(__file__).resolve().parent
    helper = overlay / "Sources/AccountContext/NagramiXArchivedPlaybackAction.swift"
    target = source / "submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift"
    if target.exists():
        raise SystemExit("Archived playback helper collision")
    helper_data = helper.read_bytes()
    auxiliary, native, decoration, embedded, file, account_build, bubble, fetch = guards
    if '"Sources/**/*.swift"' not in texts[account_build]:
        raise SystemExit("Archived playback helper is outside the native source glob")
    patches = [
        (fetch,
         """    func copyTo(url: URL) -> Bool {
        do {
            try FileManager.default.copyItem(at: URL(fileURLWithPath: self.path), to: url)
""",
         """    func copyTo(url: URL) -> Bool {
        if URL(fileURLWithPath: self.path).deletingLastPathComponent().lastPathComponent == "nagramix-message-media" {
            do {
                // Retained files are immutable. Keep the archive's source alive
                // and attach its bytes to MediaBox without a large disk copy.
                try FileManager.default.linkItem(at: URL(fileURLWithPath: self.path), to: url)
                return true
            } catch {
                let manager = FileManager.default
                if let sourceInfo = try? manager.attributesOfItem(atPath: self.path),
                   let targetInfo = try? manager.attributesOfItem(atPath: url.path),
                   let sourceInode = sourceInfo[.systemFileNumber] as? NSNumber,
                   let targetInode = targetInfo[.systemFileNumber] as? NSNumber,
                   let sourceDevice = sourceInfo[.systemNumber] as? NSNumber,
                   let targetDevice = targetInfo[.systemNumber] as? NSNumber,
                   sourceInode == targetInode, sourceDevice == targetDevice {
                    // A render-time prime may have won the same atomic link race.
                    return true
                }
                // A cross-filesystem fallback publishes only a complete file,
                // never a partially copied "complete" path visible to players.
                let temporary = url.deletingLastPathComponent().appendingPathComponent(".nagramix-cache-" + UUID().uuidString)
                defer { try? manager.removeItem(at: temporary) }
                do {
                    try manager.copyItem(at: URL(fileURLWithPath: self.path), to: temporary)
                    try manager.moveItem(at: temporary, to: url)
                    return true
                } catch {
                    return false
                }
            }
        }
        do {
            try FileManager.default.copyItem(at: URL(fileURLWithPath: self.path), to: url)
"""),
        (bubble,
         """                            strongSelf.bubbleBackgroundNode?.layer.mask = strongSelf.maskLayer
""",
         """                            let nagramiXArchivedMask = item.message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
                            let nagramiXMaskAnimator = nagramiXArchivedMask ? ListViewItemUpdateAnimation.None.animator : animation.animator
                            if nagramiXArchivedMask {
                                strongSelf.maskForeground.removeAllAnimations()
                                strongSelf.backdropMaskForeground.removeAllAnimations()
                            }
                            strongSelf.bubbleBackgroundNode?.layer.mask = strongSelf.maskLayer
"""),
        (bubble,
         "                            animation.animator.updateCornerRadius(layer: strongSelf.maskForeground, cornerRadius: maskCornerRadius, completion: nil)\n",
         "                            nagramiXMaskAnimator.updateCornerRadius(layer: strongSelf.maskForeground, cornerRadius: maskCornerRadius, completion: nil)\n"),
        (bubble,
         "                            animation.animator.updateFrame(layer: strongSelf.maskForeground, frame: maskFrame, completion: nil)\n",
         "                            nagramiXMaskAnimator.updateFrame(layer: strongSelf.maskForeground, frame: maskFrame, completion: nil)\n"),
        (bubble,
         """                                bottomRightCornerRadius: bottomRightCornerRadius,
                                animator: animation.animator
                            )
""",
         """                                bottomRightCornerRadius: bottomRightCornerRadius,
                                animator: nagramiXMaskAnimator
                            )
"""),
        (bubble,
         "                            animation.animator.updateFrame(layer: strongSelf.backdropMaskForeground, frame: backdropMaskFrame, completion: nil)\n",
         "                            nagramiXMaskAnimator.updateFrame(layer: strongSelf.backdropMaskForeground, frame: backdropMaskFrame, completion: nil)\n"),
        (auxiliary,
         """    }, fetchResourceMediaReferenceHash: { resource in
        if let resource = resource as? VideoLibraryMediaResource {
""",
         """    }, fetchResourceMediaReferenceHash: { resource in
        if let hash = NagramiXArchivedMediaCopy.uploadedReferenceHash(resource: resource) {
            return .single(hash)
        }
        if let resource = resource as? VideoLibraryMediaResource {
"""),
        (native,
         """                self.imageNode.layer.removeAnimation(forKey: key)
            }
        }
        self.validLayout = (size, actualSize)
""",
         """                self.imageNode.layer.removeAnimation(forKey: key)
            }
            // An inner renderer may return from an overlay with a model scale,
            // not just a running animation. Only the outer circle is scaled.
            self.playerNode.transform = CATransform3DIdentity
            self.imageNode.transform = CATransform3DIdentity
        }
        self.validLayout = (size, actualSize)
"""),
        (decoration,
         """                self.contentNode?.layer.removeAnimation(forKey: key)
            }
        }
        self.validLayout = (size, actualSize)
""",
         """                self.contentNode?.layer.removeAnimation(forKey: key)
            }
            self.contentContainerNode.transform = CATransform3DIdentity
            self.contentNode?.transform = CATransform3DIdentity
        }
        self.validLayout = (size, actualSize)
"""),
        (embedded,
         "    private var imageScale: CGFloat = 1.0\n",
         "    private var imageScale: CGFloat = 1.0\n    private let nagramiXArchivedPlaybackAction = NagramiXArchivedPlaybackAction()\n"),
        (embedded,
         """                            strongSelf.videoNode = videoNode
                            strongSelf.insertSubnode(videoNode, belowSubnode: previousVideoNode ?? strongSelf.dateAndStatusNode)
""",
         """                            strongSelf.videoNode = videoNode
                            if nagramiXArchivedInstantVideo {
                                videoNode.ownsContentNodeUpdated = { [weak strongSelf, weak videoNode] attached in
                                    guard attached, let strongSelf, let videoNode,
                                          strongSelf.videoNode === videoNode, strongSelf.nagramiXIsArchivedInstantVideo else {
                                        return
                                    }
                                    for key in ["transform", "position", "bounds"] {
                                        videoNode.layer.removeAnimation(forKey: key)
                                    }
                                    videoNode.transform = CATransform3DMakeScale(strongSelf.imageScale, strongSelf.imageScale, 1.0)
                                    videoNode.alpha = 1.0
                                }
                            }
                            strongSelf.insertSubnode(videoNode, belowSubnode: previousVideoNode ?? strongSelf.dateAndStatusNode)
"""),
        (embedded,
         """        if self.nagramiXIsArchivedInstantVideo {
            if let status = self.status, case .playbackStatus = status.mediaStatus {
                item.context.sharedContext.mediaManager.playlistControl(.playback(.togglePlayPause), type: .voice)
            } else {
                // Open the supplied snapshot on the first action, even while the
                // mute badge or local-file status is still updating.
                let _ = item.controllerInteraction.openMessage(item.message, OpenMessageParams(mode: .default))
            }
            return
        }
""",
         """        if self.nagramiXIsArchivedInstantVideo {
            let messageId = item.message.id
            let accountId = item.context.account.id
            let resourceId = self.media?.resource.id
            self.nagramiXArchivedPlaybackAction.activate(context: item.context, message: item.message, isCurrent: { [weak self] in
                guard let self else { return false }
                return self.nagramiXIsArchivedInstantVideo && self.item?.context.account.id == accountId && self.item?.message.id == messageId && self.media?.resource.id == resourceId
            }, open: { [weak self] in
                guard let self, let currentItem = self.item else { return }
                let _ = currentItem.controllerInteraction.openMessage(currentItem.message, OpenMessageParams(mode: .default))
            })
            return
        }
"""),
        (file,
         "    private let statusDisposable = MetaDisposable()\n",
         "    private let statusDisposable = MetaDisposable()\n    private let nagramiXArchivedPlaybackAction = NagramiXArchivedPlaybackAction()\n"),
        (file,
         """    @objc private func progressPressed() {
        if let _ = self.arguments?.attributes.updatingMedia {
""",
         """    @objc private func progressPressed() {
        if self.nagramiXIsArchivedVoice, self.arguments?.attributes.updatingMedia == nil,
           let context = self.context, let message = self.message, !message.flags.isSending,
           let file = self.file, file.resource is LocalFileReferenceMediaResource {
            let messageId = message.id
            let accountId = context.account.id
            let resourceId = file.resource.id
            self.nagramiXArchivedPlaybackAction.activate(context: context, message: message, isCurrent: { [weak self] in
                guard let self else { return false }
                return self.nagramiXIsArchivedVoice && self.context?.account.id == accountId && self.message?.id == messageId && self.file?.resource.id == resourceId
            }, open: { [weak self] in
                self?.activateLocalContent()
            })
            return
        }
        if let _ = self.arguments?.attributes.updatingMedia {
"""),
    ]
    for name, before, after in patches:
        if texts[name].count(before) != 1:
            raise SystemExit(f"Изменился точный якорь архивного replay: {name}")
        texts[name] = texts[name].replace(before, after, 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")
    target.write_bytes(helper_data)


def apply_global_tab_search_fix(source: Path) -> None:
    """Keep the root search action visible on every configured tab.

    Telegram 13's contextual search is nil on Calls, whose activation callback
    begins a call. Bind NagramiX's button to the existing root chat search and
    include its saved visibility in the native layout cache key.
    """
    guards = {
        "submodules/TelegramUI/Sources/TelegramRootController.swift": "ecbbc6199782446a09d626f2b446aab9ed1d003b9c51ab1a18bbe94d3da483f8",
        "submodules/TabBarUI/Sources/TabBarController.swift": "65c528ab7126dd1f84f547cd3173511a815c1988117c676bd31a06c65c874a74",
        "submodules/TabBarUI/Sources/TabBarContollerNode.swift": "55350cd6d1015f137030d1eeaf4ad4761acdb6f698fd71a43b0ae82be8a08fc5",
    }
    texts = {}
    for name, expected in guards.items():
        data = (source / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная интеграция кнопки поиска или правка уже применена: {name}")
        texts[name] = data.decode("utf-8")
    root, controller, node = guards
    patches = [
        (root,
         """    private func nagramiXConfiguredControllers() -> [ViewController] {
        let settings = NagramiXTabSettings.current
""",
         """    private func nagramiXConfiguredControllers() -> [ViewController] {
        if let tabController = self.rootTabController as? TabBarControllerImpl {
            tabController.nagramiXGlobalSearchController = self.chatListController
            tabController.nagramiXActivateGlobalSearch = { [weak self] in
                self?.openChatsController(activateSearch: true)
            }
        }
        let settings = NagramiXTabSettings.current
"""),
        (controller,
         "    public var currentController: ViewController?\n",
         """    public var currentController: ViewController?
    public weak var nagramiXGlobalSearchController: ViewController?
    public var nagramiXActivateGlobalSearch: (() -> Void)?
"""),
        (controller,
         """            self.currentController?.tabBarActivateSearch()
        }, deactivateSearch: { [weak self] in
""",
         """            if self.nagramiXGlobalSearchController != nil, let activateGlobalSearch = self.nagramiXActivateGlobalSearch {
                activateGlobalSearch()
            } else {
                self.currentController?.tabBarActivateSearch()
            }
        }, deactivateSearch: { [weak self] in
"""),
        (controller,
         """            self.currentController?.tabBarDeactivateSearch()
        })
""",
         """            self.currentController?.tabBarDeactivateSearch()
        }, nagramiXGlobalSearchController: { [weak self] in
            return self?.nagramiXGlobalSearchController
        })
"""),
        (node,
         "        let currentControllerSearchState: ViewController.TabBarSearchState?\n",
         """        let currentControllerSearchState: ViewController.TabBarSearchState?
        let nagramiXShowSearchButton: Bool
        let nagramiXHasGlobalSearch: Bool
        let nagramiXIsGlobalSearchController: Bool
"""),
        (node,
         """            currentControllerSearchState: ViewController.TabBarSearchState?
        ) {
""",
         """            currentControllerSearchState: ViewController.TabBarSearchState?,
            nagramiXShowSearchButton: Bool,
            nagramiXHasGlobalSearch: Bool,
            nagramiXIsGlobalSearchController: Bool
        ) {
"""),
        (node,
         "            self.currentControllerSearchState = currentControllerSearchState\n",
         """            self.currentControllerSearchState = currentControllerSearchState
            self.nagramiXShowSearchButton = nagramiXShowSearchButton
            self.nagramiXHasGlobalSearch = nagramiXHasGlobalSearch
            self.nagramiXIsGlobalSearchController = nagramiXIsGlobalSearchController
"""),
        (node,
         "    private let deactivateSearch: () -> Void\n",
         "    private let deactivateSearch: () -> Void\n    private let nagramiXGlobalSearchController: () -> ViewController?\n"),
        (node,
         "deactivateSearch: @escaping () -> Void) {\n",
         "deactivateSearch: @escaping () -> Void, nagramiXGlobalSearchController: @escaping () -> ViewController? = { nil }) {\n"),
        (node,
         "        self.deactivateSearch = deactivateSearch\n",
         "        self.deactivateSearch = deactivateSearch\n        self.nagramiXGlobalSearchController = nagramiXGlobalSearchController\n"),
        (node,
         """        let params = Params(layout: layout, toolbar: toolbar, isTabBarHidden: self.tabBarHidden, currentControllerSearchState: self.currentController?.tabBarSearchState)
""",
         """        let globalSearchController = self.nagramiXGlobalSearchController()
        let params = Params(layout: layout, toolbar: toolbar, isTabBarHidden: self.tabBarHidden, currentControllerSearchState: self.currentController?.tabBarSearchState, nagramiXShowSearchButton: NagramiXTabSettings.current.showSearchButton, nagramiXHasGlobalSearch: globalSearchController != nil, nagramiXIsGlobalSearchController: globalSearchController != nil && self.currentController === globalSearchController)
"""),
        (node,
         """                search: self.currentController?.tabBarSearchState.flatMap { tabBarSearchState in
                    guard NagramiXTabSettings.current.showSearchButton else {
                        return nil
                    }
                    return TabBarComponent.Search(
                        isActive: tabBarSearchState.isActive,
""",
         """                search: { () -> TabBarComponent.Search? in
                    guard params.nagramiXShowSearchButton,
                          params.nagramiXHasGlobalSearch || params.currentControllerSearchState != nil else {
                        return nil
                    }
                    return TabBarComponent.Search(
                        isActive: (params.currentControllerSearchState?.isActive ?? false) && (!params.nagramiXHasGlobalSearch || params.nagramiXIsGlobalSearchController),
"""),
        (node,
         """                },
                selectedId: selectedId,
""",
         """                }(),
                selectedId: selectedId,
"""),
    ]
    for name, before, after in patches:
        if texts[name].count(before) != 1:
            raise SystemExit(f"Изменился точный якорь кнопки поиска: {name}")
        texts[name] = texts[name].replace(before, after, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_mixed_playback_return(source: Path) -> None:
    """Avoid an intermediate mode when restoring playback after mixed recording."""
    name = 'submodules/TelegramAudio/Sources/ManagedAudioSession.swift'
    digest = 'a611655822cdfe0bcf99477973ceae634047ab5e09f6a2256dfc0de462fe34f5'
    path = source / name
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise SystemExit("Mixed playback return input drift")
    text = raw.decode("utf-8")
    patches = [
        ("""        self.deactivateTimer = nil
       \x20
        let wasPlaybackActive = self.currentTypeAndOutputMode?.0.isPlay ?? false
       \x20
        if self.currentTypeAndOutputMode == nil || self.currentTypeAndOutputMode! != (type, outputMode) {
""", """        self.deactivateTimer = nil

        let nagramiXRestoringMixedPlayback: Bool
        if let previousType = self.currentTypeAndOutputMode?.0, case .record(_, false, true) = previousType {
            nagramiXRestoringMixedPlayback = type.isPlay
        } else {
            nagramiXRestoringMixedPlayback = false
        }
        let wasPlaybackActive = self.currentTypeAndOutputMode?.0.isPlay ?? false

        if self.currentTypeAndOutputMode == nil || self.currentTypeAndOutputMode! != (type, outputMode) {
"""),
        ("""                    if case .record(_, _, true) = type {
                        // Avoid rebuilding an identical mixed configuration on the next take.
""", """                    let nagramiXConfigureAtomically: Bool
                    if case .record(_, _, true) = type {
                        nagramiXConfigureAtomically = true
                    } else {
                        nagramiXConfigureAtomically = nagramiXRestoringMixedPlayback
                    }
                    if nagramiXConfigureAtomically {
                        // Configure the final category/mode/options together on both ends
                        // of mixed voice/round recording, including restored in-app playback.
"""),
    ]
    for old, new in patches:
        if text.count(old) != 1:
            raise SystemExit(f"Mixed playback return anchor drift: {old[:80]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def apply_selfie_recording_lifecycle(source: Path) -> None:
    """Cancellable recording preparation, per-record stop, and selfie flip timer."""
    screen = 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'
    neo = 'submodules/Camera/CameraNeo/Sources/CameraNeo.swift'
    guards = {
        screen: '86c3b4adeab32ce1cb2a6ae8301d003eb881c2834bb79ab6695780b56fce50a0',
        neo: '530ef2765c738550268489ff681106038b24a21e656b669c13736a3f33491ebe',
    }
    patches = [
        (screen, """        func startVideoRecording(pressing: Bool) {
            guard !self.nagramiXStoppingRecording else { return }
            guard let controller = self.getController(), let camera = controller.camera else {
                return
            }
            guard case .none = controller.cameraState.recording else {
                return
            }
           \x20
            let currentTimestamp = CACurrentMediaTime()
            if let lastActionTimestamp = controller.lastActionTimestamp, currentTimestamp - lastActionTimestamp < 0.5 {
                return
            }
            controller.lastActionTimestamp = currentTimestamp
       \x20
            self.nagramiXRecordingGeneration &+= 1
            let generation = self.nagramiXRecordingGeneration
            let shouldCountdown = !self.nagramiXDidRequestInitialRecording && controller.cameraState.position == .front && NagramiXTabSettings.current.selfieCountdown
            self.nagramiXDidRequestInitialRecording = true
            if shouldCountdown {
                self.nagramiXArmCountdown(controller: controller)
            }
            let initialDuration = controller.node.previewState?.composition.duration.seconds ?? 0.0
            let isFirstRecording = initialDuration.isZero
            controller.node.resumeCameraCapture()
           \x20
            controller.node.dismissAllTooltips()
            controller.updateCameraState({ $0.updatedRecording(pressing ? .holding : .handsFree).updatedDuration(initialDuration) }, transition: .spring(duration: 0.4))
       \x20
            controller.updatePreviewState({ _ in return nil }, transition: .spring(duration: 0.4))
           \x20
            controller.node.withReadyCamera(isFirstTime: !controller.node.cameraIsActive) { [weak self] in
                let start: () -> Void = { [weak self] in
                    guard let self, let controller = self.getController(), !controller.isDismissed,
                          !self.nagramiXStoppingRecording, self.nagramiXRecordingGeneration == generation else {
                        return
                    }
                    if shouldCountdown && UIApplication.shared.applicationState != .active { return }
                    if controller.recordingStartTime == nil {
                        controller.recordingStartTime = CACurrentMediaTime()
                    }
                    self.resultDisposable.set((camera.startRecording()
                    |> deliverOnMainQueue).startStrict(next: { [weak self] recordingData in
                        let duration = initialDuration + recordingData.duration
                        if let self, let controller = self.getController() {
                            controller.updateCameraState({ $0.updatedDuration(duration) }, transition: .easeInOut(duration: 0.1))
                            if isFirstRecording {
                                controller.node.setupLiveUpload(filePath: recordingData.filePath)
                            }
                            if duration > 59.5 {
                                controller.onStop()
                            }
                        }
                    }, error: { [weak self] _ in
                        if let self, let controller = self.getController() {
                            controller.completion(nil, nil, nil, nil)
                        }
                    }))
                }
                if shouldCountdown {
                    self?.nagramiXBeginCountdown(generation: generation, start: start)
                } else {
                    Queue.mainQueue().after(0.15, start)
                }
            }
           \x20
            if initialDuration > 0.0 {
                controller.onResume()
            }
           \x20
            if controller.cameraState.position == .front && controller.cameraState.flashMode == .on {
                self.updateScreenBrightness()
            }
        }
       \x20
        private var nagramiXDidRequestInitialRecording = false
        private var nagramiXCountdownTimer: SwiftSignalKit.Timer?
        private var nagramiXCountdownPositionDisposable: Disposable?
        private var nagramiXCountdownBackgroundObserver: NSObjectProtocol?

        private func nagramiXArmCountdown(controller: VideoMessageCameraScreen) {
            controller.node.nagramiXCountdownPending = true
            controller.node.nagramiXUpdateCountdown(3)
            controller.camera?.focus(at: CGPoint(x: 0.5, y: 0.5), autoFocus: true)
            self.nagramiXCountdownBackgroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
                guard let controller = self?.getController(), controller.node.nagramiXCountdownPending else { return }
                controller.discardVideo()
                controller.completion(nil, nil, nil, nil)
            }
        }

        private func nagramiXClearCountdown() {
            self.nagramiXCountdownTimer?.invalidate()
            self.nagramiXCountdownTimer = nil
            self.nagramiXCountdownPositionDisposable?.dispose()
            self.nagramiXCountdownPositionDisposable = nil
            if let observer = self.nagramiXCountdownBackgroundObserver {
                NotificationCenter.default.removeObserver(observer)
                self.nagramiXCountdownBackgroundObserver = nil
            }
            if let controller = self.getController() {
                controller.node.nagramiXCountdownPending = false
                controller.node.nagramiXUpdateCountdown(nil)
            }
        }

        private func nagramiXBeginCountdown(generation: UInt64, start: @escaping () -> Void) {
            guard let controller = self.getController(), let camera = controller.camera,
                  !controller.isDismissed, controller.node.nagramiXCountdownPending,
                  self.nagramiXRecordingGeneration == generation else { return }
            guard UIApplication.shared.applicationState == .active else {
                controller.discardVideo()
                controller.completion(nil, nil, nil, nil)
                return
            }
            // Readiness was awaited before the clock starts. Preview/focus frames
            // never reach the writer or live upload during these three seconds.
            let deadline = CACurrentMediaTime() + 3.0
            let finish: () -> Void = { [weak self] in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      controller.node.nagramiXCountdownPending,
                      self.nagramiXRecordingGeneration == generation else { return }
                self.nagramiXClearCountdown()
                start()
            }
            if controller.cameraState.position != .front {
                finish()
                return
            }
            let timer = SwiftSignalKit.Timer(timeout: 0.05, repeat: true, completion: { [weak self] in
                guard let self, let controller = self.getController(), !controller.isDismissed,
                      controller.node.nagramiXCountdownPending,
                      self.nagramiXRecordingGeneration == generation else { return }
                let remaining = Int(ceil(max(0.0, deadline - CACurrentMediaTime())))
                if remaining == 0 {
                    finish()
                } else {
                    controller.node.nagramiXUpdateCountdown(min(3, remaining))
                }
            }, queue: .mainQueue())
            self.nagramiXCountdownTimer = timer
            timer.start()
            self.nagramiXCountdownPositionDisposable = (camera.position
            |> deliverOnMainQueue).startStrict(next: { position in
                if position != .front { finish() }
            })
        }

        private var nagramiXStoppingRecording = false
        private var nagramiXRecordingGeneration: UInt64 = 0

        func stopVideoRecording() {
            guard let controller = self.getController(), let camera = controller.camera else {
                return
            }
            if controller.node.nagramiXCountdownPending {
                self.cancelVideoRecording()
                controller.completion(nil, nil, nil, nil)
                return
            }
            guard !self.nagramiXStoppingRecording else { return }
            self.nagramiXStoppingRecording = true
            self.nagramiXRecordingGeneration &+= 1
            controller.lastActionTimestamp = CACurrentMediaTime()
            var receivedStopResult = false
            self.resultDisposable.set((camera.stopRecording()
            |> timeout(30.0, queue: .mainQueue(), alternate: .single(.failed))
            |> deliverOnMainQueue).startStrict(next: { [weak self] result in
                receivedStopResult = true
                guard let self, let controller = self.getController() else { return }
                self.nagramiXStoppingRecording = false
                if case let .finished(mainResult, _, duration, _, _) = result {
                    self.completion.invoke(
                        .video(VideoMessageCameraScreen.CaptureResult.Video(
                            videoPath: mainResult.path,
                            dimensions: PixelDimensions(mainResult.dimensions),
                            duration: duration,
                            thumbnail: mainResult.thumbnail
                        ))
                    )
                    controller.updateCameraState({ $0.updatedRecording(.none) }, transition: .spring(duration: 0.4))
                } else {
                    controller.completion(nil, nil, nil, nil)
                }
            }, completed: { [weak self] in
                guard !receivedStopResult, let self else { return }
                self.nagramiXStoppingRecording = false
                self.getController()?.completion(nil, nil, nil, nil)
            }))
           \x20
            if let initialBrightness = self.initialBrightness {
                self.initialBrightness = nil
                self.brightnessArguments = (CACurrentMediaTime(), 0.2, UIScreen.main.brightness, initialBrightness)
                self.animateBrightnessChange()
            }
        }
       \x20
        func lockVideoRecording() {
            guard let controller = self.getController() else {
                return
            }
            controller.updateCameraState({ $0.updatedRecording(.handsFree) }, transition: .spring(duration: 0.4))
        }
       \x20
        func cancelVideoRecording() {
            self.nagramiXRecordingGeneration &+= 1
            self.nagramiXClearCountdown()
            if let initialBrightness = self.initialBrightness {
                self.initialBrightness = nil
                self.brightnessArguments = (CACurrentMediaTime(), 0.2, UIScreen.main.brightness, initialBrightness)
                self.animateBrightnessChange()
            }
        }
       \x20
""", """__NAGRAMIX_SELFIE_RECORDING_STATE__"""),
        (screen, """        deinit {
            self.nagramiXCountdownTimer?.invalidate()
""", """        deinit {
            self.nagramiXPreparationTimer?.invalidate()
            self.nagramiXReadyDisposable.dispose()
            self.nagramiXStopDisposable.dispose()
            self.nagramiXCountdownTimer?.invalidate()
"""),
        (screen, """        func togglePosition() {
            guard let controller = self.getController(), let camera = controller.camera else {
""", """        func togglePosition() {
            guard !self.nagramiXStoppingRecording, !self.nagramiXSwitchingCamera, !self.nagramiXCancelled,
                  let controller = self.getController(), let camera = controller.camera, !controller.isDismissed else {
"""),
        (screen, """            let isFrontCamera = controller.cameraState.position == .back
            camera.togglePosition()
""", """            let isFrontCamera = controller.cameraState.position == .back
            if isFrontCamera && NagramiXTabSettings.current.selfieCountdown && self.nagramiXWriterRequested {
                self.nagramiXSwitchToSelfie()
                return
            }
            camera.togglePosition()
"""),
        (screen, """        fileprivate var nagramiXCountdownPending = false
""", """        fileprivate var nagramiXCountdownPending = false
        fileprivate var nagramiXCameraSwitchPending = false
        fileprivate let nagramiXPreviewReadyDisposables = DisposableSet()
"""),
        (screen, """        deinit {
            self.cameraStateDisposable?.dispose()
""", """        deinit {
            self.nagramiXPreviewReadyDisposables.dispose()
            self.cameraStateDisposable?.dispose()
"""),
        (screen, """            let _ = (previewReady
            |> filter { $0 }
            |> take(1)
            |> deliverOnMainQueue).startStandalone(next: { _ in
                f()
            })
""", """            self.nagramiXPreviewReadyDisposables.add((previewReady
            |> filter { $0 }
            |> take(1)
            |> deliverOnMainQueue).start(next: { _ in
                f()
            }))
"""),
        (screen, """        func addCaptureResult(_ result: VideoMessageCameraScreen.CaptureResult) {
""", """        fileprivate func nagramiXAppendSwitchResult(_ result: VideoMessageCameraScreen.CaptureResult) {
            // A sealed fragment in the same outgoing message, without pausing preview.
            if self.results.isEmpty { _ = self.liveUploadInterface?.fileUpdated(true) }
            self.currentLiveUploadData = nil
            self.results.append(result)
        }

        func addCaptureResult(_ result: VideoMessageCameraScreen.CaptureResult) {
"""),
        (screen, """        if self.node.nagramiXCountdownPending {
            self.node.cancelRecording.invoke(Void())
""", """        if self.node.nagramiXCountdownPending && !self.node.nagramiXCameraSwitchPending {
            self.node.cancelRecording.invoke(Void())
"""),
        (screen, """        if self.node.nagramiXCountdownPending {
            self.discardVideo()
""", """        if self.node.nagramiXCountdownPending && !self.node.nagramiXCameraSwitchPending {
            self.discardVideo()
"""),
        (screen, """        self.node.cancelRecording.invoke(Void())
        self.node.camera?.stopCapture(invalidate: true)
""", """        self.node.cancelRecording.invoke(Void())
        self.node.nagramiXPreviewReadyDisposables.dispose()
        self.node.camera?.stopCapture(invalidate: true)
"""),
        (screen, """        private func animatePositionChange() {
            if let snapshotView = self.mainPreviewView.snapshotView(afterScreenUpdates: false) {
                self.previewContainerContentView.insertSubview(snapshotView, belowSubview: self.progressView)
                self.previewSnapshotView = snapshotView
               \x20
                let action = { [weak self] in
                    guard let self else {
                        return
                    }
                    UIView.animate(withDuration: 0.2, animations: {
                        self.previewSnapshotView?.alpha = 0.0
                    }, completion: { [weak self] _ in
                        self?.previewSnapshotView?.removeFromSuperview()
                        self?.previewSnapshotView = nil
                    })
                }
               \x20
                Queue.mainQueue().after(1.0) {
                    action()
                }
               \x20
                self.requestUpdateLayout(transition: .immediate)
            }
        }
       \x20
""", """        private func animatePositionChange() {
            self.previewSnapshotView?.removeFromSuperview()
            self.previewSnapshotView = nil
            guard let snapshot = self.mainPreviewView.snapshotView(afterScreenUpdates: false) else { return }
            self.previewContainerContentView.insertSubview(snapshot, belowSubview: self.progressView)
            self.previewSnapshotView = snapshot
            self.requestUpdateLayout(transition: .immediate)
            Queue.mainQueue().after(0.35) { [weak self, weak snapshot] in
                guard let self, let snapshot, self.previewSnapshotView === snapshot else { return }
                UIView.animate(withDuration: 0.2, animations: {
                    snapshot.alpha = 0.0
                }, completion: { [weak self, weak snapshot] _ in
                    snapshot?.removeFromSuperview()
                    if self?.previewSnapshotView === snapshot { self?.previewSnapshotView = nil }
                })
            }
        }

"""),
        (neo, """    deinit {
        NotificationCenter.default.removeObserver(self)
        let cleanUpSession = {
            self.primaryVideoOutput?.setSampleBufferDelegate(nil, queue: nil)
            self.secondaryVideoOutput?.setSampleBufferDelegate(nil, queue: nil)
            self.audioOutput?.setSampleBufferDelegate(nil, queue: nil)
            if self.session.isRunning {
                self.session.stopRunning()
            }
            self.tearDownSession()
        }
        if DispatchQueue.getSpecific(key: self.sessionQueueKey) != nil {
            cleanUpSession()
        } else {
            self.sessionQueue.sync(execute: cleanUpSession)
        }
        if DispatchQueue.getSpecific(key: self.mediaQueueKey) != nil {
            self.recorder?.cancel()
        } else {
            self.mediaQueue.sync {
                self.recorder?.cancel()
            }
        }
    }

""", """    deinit {
        NotificationCenter.default.removeObserver(self)
        let session = self.session
        let primaryOutput = self.primaryVideoOutput
        let secondaryOutput = self.secondaryVideoOutput
        let audioOutput = self.audioOutput
        let recorder = self.recorder
        let processor = self.frameProcessor
        let mediaQueue = self.mediaQueue
        // AVCaptureSession.stopRunning and GPU/writer cleanup must not block main.
        self.sessionQueue.async {
            primaryOutput?.setSampleBufferDelegate(nil, queue: nil)
            secondaryOutput?.setSampleBufferDelegate(nil, queue: nil)
            audioOutput?.setSampleBufferDelegate(nil, queue: nil)
            if session.isRunning { session.stopRunning() }
            session.beginConfiguration()
            for output in session.outputs { session.removeOutput(output) }
            for input in session.inputs { session.removeInput(input) }
            session.commitConfiguration()
            mediaQueue.async {
                recorder?.cancel()
                withExtendedLifetime(processor) {}
            }
        }
    }

"""),
        (neo, """    private let recordingCompletionPipe = ValuePipe<VideoCaptureResult>()
""", """    private var recordingCompletionPipe = ValuePipe<VideoCaptureResult>()
"""),
        (neo, """        let _ = self.recordingStopRequested.modify { _ in false }

        let outputUrl =""", """        let _ = self.recordingStopRequested.modify { _ in false }
        let recordingCompletionPipe = ValuePipe<VideoCaptureResult>()
        self.recordingCompletionPipe = recordingCompletionPipe

        let outputUrl ="""),
        (neo, """        return Signal { [weak self] subscriber in
            guard let self else {
                subscriber.putCompletion()
                return EmptyDisposable
            }

            let subscriberActive""", """        return Signal { [weak self, recordingCompletionPipe] subscriber in
            guard let self else {
                subscriber.putCompletion()
                return EmptyDisposable
            }

            let subscriberActive"""),
        (neo, """                        let _ = self.recordingStopRequested.modify { _ in false }
                        return
                    }
                    if case let .failed(error)""", """                        let _ = self.recordingStopRequested.modify { _ in false }
                        recordingCompletionPipe.putNext(.failed)
                        return
                    }
                    if case let .failed(error)"""),
        (neo, """                        completion: { [weak self] result in
""", """                        completion: { [weak self, recordingCompletionPipe] result in
"""),
        (neo, """                                self.recordingCompletionPipe.putNext(.finished(
""", """                                recordingCompletionPipe.putNext(.finished(
"""),
        (neo, """                                self.recordingCompletionPipe.putNext(.failed)
""", """                                recordingCompletionPipe.putNext(.failed)
"""),
        (neo, """    func stopRecording() -> Signal<VideoCaptureResult, NoError> {
        guard self.recordingActive.with({ $0 }) else {
            return .complete()
        }
        let _ = self.recordingStopRequested.modify { _ in true }
        self.mediaQueue.async { [weak self] in
            self?.recorder?.stop()
        }
        return self.recordingCompletionPipe.signal()
        |> take(1)
    }

""", """    func stopRecording() -> Signal<VideoCaptureResult, NoError> {
        guard self.recordingActive.with({ $0 }) else { return .complete() }
        let recordingCompletionPipe = self.recordingCompletionPipe
        return Signal { [weak self, recordingCompletionPipe] subscriber in
            let disposable = (recordingCompletionPipe.signal()
            |> take(1)).start(next: { result in
                subscriber.putNext(result)
                subscriber.putCompletion()
            })
            guard let self else {
                subscriber.putNext(.failed)
                subscriber.putCompletion()
                return disposable
            }
            let _ = self.recordingStopRequested.modify { _ in true }
            self.mediaQueue.async { [weak self] in
                self?.recorder?.stop()
            }
            return disposable
        }
    }

"""),
    ]
    methods = (Path(__file__).resolve().parent / "Sources/VideoMessageCameraScreen/NagramiXSelfieRecording.swift.inc").read_text(encoding="utf-8")
    texts = {}
    for name, digest in guards.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Selfie recording lifecycle input drift: {name}")
        texts[name] = raw.decode("utf-8")
    for name, old, new in patches:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Selfie recording lifecycle anchor drift: {name}: {old[:80]!r}")
        if new == "__NAGRAMIX_SELFIE_RECORDING_STATE__":
            new = methods
        texts[name] = texts[name].replace(old, new, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_full_name_deletion_menu(source: Path) -> None:
    """Use native multiline context actions and full names for ordinary deletion."""
    name = 'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift'
    digest = 'c8ba128de1d40b78ef09c125621650a0ce23c7cd6aded0357286eb637496af81'
    path = source / name
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise SystemExit("Full-name deletion menu input drift")
    text = raw.decode("utf-8")
    patches = [
        ("""            let actionSheet = ActionSheetController(presentationData: self.presentationData)
            var items: [ActionSheetItem] = []
            var personalPeerName: String?
""", """            var personalPeerName: String?
"""),
        ("""personalPeerName = EnginePeer(user).compactDisplayTitle
            } else if let peer = self.presentationInterfaceState.renderedPeer?.peer as? TelegramSecretChat""", """personalPeerName = EnginePeer(user).displayTitle(strings: self.presentationData.strings, displayOrder: self.presentationData.nameDisplayOrder)
            } else if let peer = self.presentationInterfaceState.renderedPeer?.peer as? TelegramSecretChat"""),
        ("""personalPeerName = EnginePeer(user).compactDisplayTitle
            } else if let channel = self.presentationInterfaceState.renderedPeer?.peer as? TelegramChannel""", """personalPeerName = EnginePeer(user).displayTitle(strings: self.presentationData.strings, displayOrder: self.presentationData.nameDisplayOrder)
            } else if let channel = self.presentationInterfaceState.renderedPeer?.peer as? TelegramChannel"""),
        ("""            var canDisplayContextMenu = true
""", """"""),
        ("""                // Use the native confirmation sheet and choices, with an exact scope.
                // Cancellation and local undo must not remove archive records early.
                canDisplayContextMenu = false
""", """                // Keep the scope warning in the same rounded menu as ordinary deletion.
                // Cancellation and local undo must not remove archive records early.
"""),
        ("""                items.append(ActionSheetTextItem(title: warning))
""", """                contextItems.append(.action(ContextMenuActionItem(text: warning, textColor: .disabled, textLayout: .multiline, textFont: .small, icon: { _ in nil }, action: nil as ((ContextMenuActionItem.Action) -> Void)?)))
                contextItems.append(.separator)
"""),
        ("""                items.append(ActionSheetButtonItem(title: self.presentationData.strings.Conversation_ContextMenuCancelSending, color: .destructive, action: { [weak self, weak actionSheet] in
                    actionSheet?.dismissAnimated()
                    if let strongSelf = self {
                        strongSelf.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                        strongSelf.beginDeleteMessagesWithUndo(messageIds: messageIds, type: .forEveryone)
                    }
                }))
""", """"""),
        ("""                items.append(ActionSheetButtonItem(title: globalTitle, color: .destructive, action: { [weak self, weak actionSheet] in
                    actionSheet?.dismissAnimated()
                    if let strongSelf = self {
                        strongSelf.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                       \x20
                        strongSelf.beginDeleteMessagesWithUndo(messageIds: messageIds, type: .forEveryone)
                    }
                }))
""", """"""),
        ("""                items.append(ActionSheetButtonItem(title: localOptionText, color: .destructive, action: { [weak self, weak actionSheet] in
                    actionSheet?.dismissAnimated()
                    if let strongSelf = self {
                        strongSelf.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                       \x20
                        strongSelf.beginDeleteMessagesWithUndo(messageIds: messageIds, type: unsendPersonalMessages ? .forEveryone : .forLocalPeer)
                    }
                }))
""", """"""),
        ("""            var unsendPersonalMessages = false
            if options.contains(.unsendPersonal) {
                canDisplayContextMenu = false
                items.append(ActionSheetTextItem(title: self.presentationData.strings.Chat_UnsendMyMessagesAlertTitle(personalPeerName ?? "").string))
                items.append(ActionSheetSwitchItem(title: self.presentationData.strings.Chat_UnsendMyMessages, isOn: false, action: { value in
                    unsendPersonalMessages = value
                }))
            } else if options.contains(.deleteGlobally) {
""", """            if options.contains(.unsendPersonal) {
                // The native option revokes only eligible outgoing messages in a mixed set.
                // Do not label it as revoking every selected message for both participants.
                contextItems.append(.action(ContextMenuActionItem(text: self.presentationData.strings.Chat_UnsendMyMessagesAlertTitle(personalPeerName ?? "").string, textColor: .disabled, textLayout: .multiline, textFont: .small, icon: { _ in nil }, action: nil as ((ContextMenuActionItem.Action) -> Void)?)))
                contextItems.append(.separator)
                contextItems.append(.action(ContextMenuActionItem(text: self.presentationData.strings.Chat_UnsendMyMessages, textColor: .destructive, textLayout: .multiline, icon: { _ in nil }, action: { [weak self] _, f in
                    f(.dismissWithoutContent)
                    guard let self else { return }
                    self.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                    self.beginDeleteMessagesWithUndo(messageIds: messageIds, type: .forEveryone)
                })))
            } else if options.contains(.deleteGlobally) {
"""),
        ("""ContextMenuActionItem(text: self.presentationData.strings.Conversation_ContextMenuCancelSending, textColor: .destructive, icon:""", """ContextMenuActionItem(text: self.presentationData.strings.Conversation_ContextMenuCancelSending, textColor: .destructive, textLayout: .multiline, icon:"""),
        ("""ContextMenuActionItem(text: globalTitle, textColor: .destructive, icon:""", """ContextMenuActionItem(text: globalTitle, textColor: .destructive, textLayout: .multiline, icon:"""),
        ("""ContextMenuActionItem(text: localOptionText, textColor: .destructive, icon:""", """ContextMenuActionItem(text: localOptionText, textColor: .destructive, textLayout: .multiline, icon:"""),
        ("""                            strongSelf.beginDeleteMessagesWithUndo(messageIds: messageIds, type: unsendPersonalMessages ? .forEveryone : .forLocalPeer)
""", """                            strongSelf.beginDeleteMessagesWithUndo(messageIds: messageIds, type: .forLocalPeer)
"""),
        ("""            if canDisplayContextMenu, let contextController = contextController {
""", """            if let contextController = contextController {
"""),
        ("""            } else if canDisplayContextMenu, let sourceView = sourceView {
                let contextController = makeContextController(
""", """            } else {
                let sourceView = sourceView ?? self.chatDisplayNode.view
                let contextController = makeContextController(
"""),
        ("""            } else {
                actionSheet.setItemGroups([ActionSheetItemGroup(items: items), ActionSheetItemGroup(items: [
                    ActionSheetButtonItem(title: self.presentationData.strings.Common_Cancel, color: .accent, font: .bold, action: { [weak actionSheet] in
                        actionSheet?.dismissAnimated()
                    })
                ])])
               \x20
                if let contextController = contextController {
                    contextController.dismiss(completion: { [weak self] in
                        self?.present(actionSheet, in: .window(.root))
                    })
                } else {
                    self.chatDisplayNode.dismissInput()
                    self.present(actionSheet, in: .window(.root))
                    completion(.default)
                }
""", """"""),
        ("""                        localOptionText = self.presentationData.strings.Chat_DeleteMessagesConfirmation(Int32(messageIds.count))
""", """                        localOptionText = self.presentationData.strings.Conversation_DeleteMessagesForMe
"""),
    ]
    for old, new in patches:
        if text.count(old) != 1:
            raise SystemExit(f"Full-name deletion menu anchor drift: {old[:80]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def apply_video_rotation_pip_lifetime_fix(source: Path) -> None:
    """Do not register dormant AVKit adapters during ordinary video playback.

    iOS 27 crash in build 89: AVKit/Pegasus reads the sample-buffer layer's
    player controller while processing a window rotation. Keep PiP lazy and
    disconnect its public content source before releasing the retained layer.
    """
    path = source / "submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift"
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != "f06ec98b6002eb52386eba27c2e756adcf4675d5ad9d357f1062ac0047412114":
        raise SystemExit("Изменилась проверенная интеграция video/PiP или правка уже применена")
    text = original.decode("utf-8")
    patches = [
        (
            """                    if NagramiXTabSettings.videoPiPSwipeEnabled && strongSelf.item?.isSecret == false && strongSelf.hasPictureInPicture && strongSelf.nativePictureInPictureContent == nil {
                        strongSelf.setupNativePictureInPicture()
                    }
""",
            """                    // Prepare AVKit only for an explicit PiP action, not each
                    // playing/paused update or a full-screen orientation change.
""",
        ),
        (
            "    private var pictureInPictureController: AVPictureInPictureController?\n    private var contentDelegate: PlaybackDelegate?\n",
            "    private var pictureInPictureController: AVPictureInPictureController?\n    private var nagramiXPictureInPictureLayer: AVSampleBufferDisplayLayer?\n    private var nagramiXPendingPiPStart: UUID?\n    private var nagramiXPendingPiPStartTimer: SwiftSignalKit.Timer?\n    private var contentDelegate: PlaybackDelegate?\n",
        ),
        (
            "        if let videoLayer = videoNode.getVideoLayer() {\n            let contentDelegate = PlaybackDelegate(node: self.node)\n",
            "        if let videoLayer = videoNode.getVideoLayer() {\n            self.nagramiXPictureInPictureLayer = videoLayer\n            let contentDelegate = PlaybackDelegate(node: self.node)\n",
        ),
        (
            """        self.pictureInPictureTimer?.invalidate()
        self.node.setCanPlaybackWithoutHierarchy(false)
""",
            """        self.pictureInPictureTimer?.invalidate()
        self.nagramiXCancelPendingPiPStart()
        // Detach AVKit while both its playback delegate and display layer are
        // still alive. A shared decoder can outlive this gallery's PiP owner.
        if let controller = self.pictureInPictureController {
            controller.canStartPictureInPictureAutomaticallyFromInline = false
            controller.delegate = nil
            controller.stopPictureInPicture()
            controller.contentSource = nil
        }
        self.contentDelegate?.pictureInPictureController = nil
        self.pictureInPictureController = nil
        self.nagramiXPictureInPictureLayer = nil
        self.node.setCanPlaybackWithoutHierarchy(false)
""",
        ),
        (
            """    var nagramiXCanStartPictureInPicture: Bool {
        return self.pictureInPictureController?.isPictureInPicturePossible == true
    }
""",
            """    var nagramiXCanStartPictureInPicture: Bool {
        guard let sourceLayer = self.nagramiXPictureInPictureLayer,
              self.node.getVideoLayer() === sourceLayer else {
            return false
        }
        return self.pictureInPictureController?.isPictureInPicturePossible == true
    }
""",
        ),
        (
            """    func beginPictureInPicture() {
        guard let pictureInPictureController = self.pictureInPictureController else {
            return
        }
        if pictureInPictureController.isPictureInPicturePossible {
            pictureInPictureController.startPictureInPicture()
        }
    }
""",
            """    func beginPictureInPicture() {
        let _ = self.nagramiXRequestPictureInPicture(unavailable: {})
    }

    private func nagramiXCancelPendingPiPStart() {
        self.nagramiXPendingPiPStart = nil
        self.nagramiXPendingPiPStartTimer?.invalidate()
        self.nagramiXPendingPiPStartTimer = nil
    }

    func nagramiXRequestPictureInPicture(unavailable: @escaping () -> Void) -> Bool {
        guard AVPictureInPictureController.isPictureInPictureSupported(),
              let controller = self.pictureInPictureController,
              let sourceLayer = self.nagramiXPictureInPictureLayer,
              self.node.getVideoLayer() === sourceLayer,
              UIApplication.shared.applicationState == .active else {
            return false
        }
        if self.nagramiXPendingPiPStart != nil {
            return true
        }
        if self.nagramiXCanStartPictureInPicture {
            controller.startPictureInPicture()
            return true
        }
        // AVKit readiness is asynchronous on a cold first request. Consume only
        // this explicit action and wait without blocking the main queue.
        let requestId = UUID()
        let deadline = CACurrentMediaTime() + 2.0
        self.nagramiXPendingPiPStart = requestId
        let timer = SwiftSignalKit.Timer(timeout: 0.05, repeat: true, completion: { [weak self] in
            guard let self, self.nagramiXPendingPiPStart == requestId else {
                return
            }
            guard UIApplication.shared.applicationState == .active,
                  self.node.getVideoLayer() === self.nagramiXPictureInPictureLayer else {
                self.nagramiXCancelPendingPiPStart()
                return
            }
            if self.nagramiXCanStartPictureInPicture {
                self.nagramiXCancelPendingPiPStart()
                self.pictureInPictureController?.startPictureInPicture()
            } else if CACurrentMediaTime() >= deadline {
                self.nagramiXCancelPendingPiPStart()
                unavailable()
            }
        }, queue: Queue.mainQueue())
        self.nagramiXPendingPiPStartTimer = timer
        timer.start()
        return true
    }

""",
        ),
        (
            """    func updateIsCentral(isCentral: Bool) {
        guard let pictureInPictureController = self.pictureInPictureController else {
""",
            """    func updateIsCentral(isCentral: Bool) {
        if !isCentral {
            self.nagramiXCancelPendingPiPStart()
        }
        guard let pictureInPictureController = self.pictureInPictureController else {
""",
        ),
        (
            """        if #available(iOS 15.0, *), let content = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl, content.nagramiXCanStartPictureInPicture {
            self.context.engine.accountData.addAppLogEvent(type: logEvent)
            content.beginPictureInPicture()
            return true
        }
""",
            """        if #available(iOS 15.0, *), self.isCentral == true,
           let content = self.nativePictureInPictureContent as? NativePictureInPictureContentImpl {
            let handled = content.nagramiXRequestPictureInPicture(unavailable: { [weak self, weak content] in
                guard let self, let content, self.nativePictureInPictureContent === content,
                      self.isCentral == true, self.galleryController()?.view.window != nil,
                      UIApplication.shared.applicationState == .active else {
                    return
                }
                // A genuinely unavailable PiP keeps the native close fallback.
                self.dismiss()
            })
            if handled {
                self.context.engine.accountData.addAppLogEvent(type: logEvent)
                return true
            }
        }
""",
        ),
        (
            """    private func setupNativePictureInPicture() {
        guard let item = self.item, let videoNode = self.videoNode else {
""",
            """    private func setupNativePictureInPicture() {
        guard self.nativePictureInPictureContent == nil,
              let item = self.item, let videoNode = self.videoNode else {
""",
        ),
    ]
    for before, after in patches:
        if text.count(before) != 1:
            raise SystemExit("Изменился точный якорь video/PiP lifetime")
        text = text.replace(before, after, 1)
    path.write_text(text, encoding="utf-8")


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


def apply_voice_recording_cancellation_fix(source: Path) -> None:
    # Audited integrated inputs after the existing round-video and chat patches.
    # Validate every file before mutation: recording lifecycle drift needs review.
    inputs = {
        "submodules/TelegramUI/Components/ChatTextInputMediaRecordingButton/Sources/ChatTextInputMediaRecordingButton.swift": "eddc296233905fb8466d99becd428d276b56bf21d24972ebf0bc6d5147893221",
        "submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift": "4f784e6d8452a6c9b25d45ce999a203bf9fd319d8ae7167609437fdab67faf8b",
        "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift": "4f47bfe8fdcd689eacebc86e9961a0696eb2a7d515bb38952318a26a9afac6f8",
        "submodules/TelegramUI/Sources/Chat/ChatControllerMediaRecording.swift": "98cbe0e944c98f3222a013d95243808c1e01a250f8594a1b0d91d29ec60e48e1",
    }
    for name, expected_sha in inputs.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected_sha:
            raise SystemExit(f"Voice recording lifecycle input changed; audit required: {name}")

    button = source / next(iter(inputs))
    replace_unique(
        button,
        "            self.cancelOnTrackingInterruption = mode == .video\n",
        """            // A system interruption ends the held gesture in either mode.
            // Never turn a cancelled first audio touch into a delayed lock.
            self.cancelOnTrackingInterruption = true
""",
        "Cancel interrupted voice holds using the existing video cancellation path",
    )
    replace_unique(
        button,
        """        self.modeTimeoutTimer?.invalidate()
        self.endRecording(false)
""",
        """        self.modeTimeoutTimer?.invalidate()
        self.modeTimeoutTimer = nil
        self.endRecording(false)
""",
        "Clear the cancelled recording-mode timer",
    )
    panel = source / "submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift"
    replace_unique(
        panel,
        """                    // A released or interrupted gesture must invalidate the
                    // pending video start, including permission callbacks.
                    if case .video = interfaceState.interfaceState.mediaRecordingMode {
                        interfaceInteraction.finishMediaRecording(.dismiss)
                    }
""",
        """                    // Invalidate audio/video startup even before a recorder
                    // exists. Permission/readiness callbacks must not restart it.
                    interfaceInteraction.finishMediaRecording(.dismiss)
""",
        "Cancel voice startup before its recording UI exists",
    )
    interaction = source / "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
    replace_unique(
        interaction,
        """            strongSelf.beginMediaRecordingRequestId += 1
            strongSelf.dismissMediaRecorder(action)
""",
        """            strongSelf.beginMediaRecordingRequestId += 1
            if strongSelf.audioRecorderValue == nil {
                // Dispose a cold-start producer before it supplies a recorder.
                strongSelf.audioRecorder.set(.single(nil))
            }
            strongSelf.dismissMediaRecorder(action)
""",
        "Dispose pending audio initialization when the held gesture finishes",
    )
    controller = source / "submodules/TelegramUI/Sources/Chat/ChatControllerMediaRecording.swift"
    replace_unique(
        controller,
        """            self.audioRecorder.set(
                self.context.sharedContext.mediaManager.audioRecorder(
""",
        """            let requestId = self.beginMediaRecordingRequestId
            self.audioRecorder.set(
                self.context.sharedContext.mediaManager.audioRecorder(
""",
        "Capture the audio startup request generation",
    )
    replace_unique(
        controller,
        """                    beganWithTone: { _ in
                    }
                )
            )
""",
        """                    beganWithTone: { _ in
                    }
                )
                |> deliverOnMainQueue
                |> map { [weak self] recorder -> ManagedAudioRecorder? in
                    guard let self, self.beginMediaRecordingRequestId == requestId else {
                        return nil
                    }
                    return recorder
                }
            )
""",
        "Reject late cold-start audio callbacks after cancellation on the UI queue",
    )


def apply_message_selection_transfer_actions(source: Path, overlay: Path) -> None:
    paths = {
        "panel": "submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift",
        "build": "submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/BUILD",
        "interaction": "submodules/ChatPresentationInterfaceState/Sources/ChatPanelInterfaceInteraction.swift",
        "load": "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
        "menus": "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift",
    }
    hashes = {
        "panel": "13b3e7d619a8198a4b985256df045e8677502d1e304d337a8d811ac6a8c574e8",
        "build": "92174f4a6dbcabb2e6ce9423e512f46d728a27d5edbbda8a83b8d0e4b25956ec",
        "interaction": "2a814c3af714f86138a2562ccc4155e407c5645da0cf6fd737e76ca0e58673c3",
        "load": "969dcf72d567ed4aa72d7695cb49debddf79003705f3e22c547a59a41b6ca394",
        "menus": "0dd3c89b89a6e762a8306596610784d4cf309a0aa0ec92204bd3b734f496446d",
    }
    for key, name in paths.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != hashes[key]:
            raise SystemExit(f"Изменилась проверенная интеграция панели выделения: {name}")

    panel = source / paths["panel"]
    replace_unique(source / paths["build"], '        "//submodules/TelegramPresentationData",\n', '        "//submodules/TelegramPresentationData",\n        "//submodules/NagramiXCore:NagramiXCore",\n', "Настройки и подписи панели выделения")
    replace_unique(panel, "import TelegramPresentationData\n", "import TelegramPresentationData\nimport NagramiXCore\n", "Читать настройки действий в панели выделения")
    replace_unique(panel, "    private let shareButton: GlassButtonView\n", """    private let shareButton: GlassButtonView
    private let forwardWithoutSourceButton: GlassButtonView
    private let broadcastButton: GlassButtonView
    private let buttonScrollView = UIScrollView()
    private let nagramiXTransferDisposable = MetaDisposable()
    private var nagramiXCanCopySelection = false
""", "Отдельные кнопки пересылки без автора и рассылки")
    replace_unique(panel, "    override init(frame: CGRect) {\n        self.backgroundView = GlassBackgroundView()\n", """    var systemIcon: String? {
        didSet {
            if self.systemIcon == oldValue { return }
            self.iconView.image = self.systemIcon.flatMap {
                UIImage(systemName: $0, withConfiguration: UIImage.SymbolConfiguration(pointSize: 24.0, weight: .regular))
            }?.withRenderingMode(.alwaysTemplate)
            if let params = self.params {
                self.updateImpl(params: params, transition: .immediate)
            }
        }
    }

    override init(frame: CGRect) {
        self.backgroundView = GlassBackgroundView()
""", "Штатный SF Symbol для пересылки без автора")
    replace_unique(panel, "        self.forwardButton.accessibilityLabel = strings.VoiceOver_MessageContextForward\n", """        self.forwardButton.accessibilityLabel = strings.nagramiXForwardWithAuthor

        self.forwardWithoutSourceButton = GlassButtonView()
        self.forwardWithoutSourceButton.systemIcon = "person.crop.circle.badge.xmark"
        self.forwardWithoutSourceButton.isImplicitlyDisabled = true
        self.forwardWithoutSourceButton.isAccessibilityElement = true
        self.forwardWithoutSourceButton.accessibilityLabel = strings.nagramiXForwardWithoutAuthor

        self.broadcastButton = GlassButtonView()
        self.broadcastButton.icon = "Chat/Context Menu/Groups"
        self.broadcastButton.isImplicitlyDisabled = true
        self.broadcastButton.isAccessibilityElement = true
        self.broadcastButton.accessibilityLabel = strings.nagramiXBroadcastMessages
""", "Различимые иконки и полные подписи действий")
    replace_unique(panel, """        self.view.addSubview(self.deleteButton)
        self.view.addSubview(self.reportButton)
        self.view.addSubview(self.forwardButton)
        self.view.addSubview(self.shareButton)
        self.view.addSubview(self.tagButton)
        self.view.addSubview(self.tagEditButton)
""", """        self.buttonScrollView.contentInsetAdjustmentBehavior = .never
        self.buttonScrollView.showsHorizontalScrollIndicator = false
        self.buttonScrollView.showsVerticalScrollIndicator = false
        self.buttonScrollView.delaysContentTouches = false
        self.buttonScrollView.bounces = false
        self.view.addSubview(self.buttonScrollView)
        for button in [self.deleteButton, self.reportButton, self.forwardButton, self.shareButton, self.tagButton, self.tagEditButton, self.forwardWithoutSourceButton, self.broadcastButton] {
            self.buttonScrollView.addSubview(button)
        }
""", "Предотвратить наложение кнопок на узких экранах")
    replace_unique(panel, "        self.shareButton.button.addTarget(self, action: #selector(self.shareButtonPressed), for: .touchUpInside)\n", """        self.shareButton.button.addTarget(self, action: #selector(self.shareButtonPressed), for: .touchUpInside)
        self.forwardWithoutSourceButton.button.addTarget(self, action: #selector(self.forwardWithoutSourceButtonPressed), for: .touchUpInside)
        self.broadcastButton.button.addTarget(self, action: #selector(self.broadcastButtonPressed), for: .touchUpInside)
""", "Подключить отдельные кнопки к штатным обработчикам")
    replace_unique(panel, "        self.canDeleteMessagesDisposable.dispose()\n", "        self.canDeleteMessagesDisposable.dispose()\n        self.nagramiXTransferDisposable.dispose()\n", "Отменить загрузку выделения при закрытии панели")
    replace_unique(panel, """    private func updateActions() {
        self.forwardButton.isEnabled = self.selectedMessages.count != 0
""", """    private func updateActions() {
        self.forwardButton.isEnabled = self.selectedMessages.count != 0
        self.nagramiXCanCopySelection = false
        self.forwardWithoutSourceButton.isImplicitlyDisabled = true
        self.broadcastButton.isImplicitlyDisabled = true
        self.nagramiXTransferDisposable.set(nil)
""", "Сбросить доступность и старую отправку при изменении выделения")
    replace_unique(panel, """        } else if let context = self.context {
            self.canDeleteMessagesDisposable.set((context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: self.selectedMessages, keepUpdated: true)
            |> deliverOnMainQueue).startStrict(next: { [weak self] actions in
                if let strongSelf = self {
                    strongSelf.actions = actions
""", """        } else if let context = self.context {
            let selectedIds = self.selectedMessages
            self.canDeleteMessagesDisposable.set((context.sharedContext.chatAvailableMessageActions(engine: context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, keepUpdated: true)
            |> deliverOnMainQueue
            |> mapToSignal { [weak self] actions -> Signal<(ChatAvailableMessageActions, Bool), NoError> in
                guard let self else { return .single((actions, false)) }
                return self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds)
                |> deliverOnMainQueue
                |> map { [weak self] messages in
                    let canCopy = messages.count == selectedIds.count && self?.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true
                    return (actions, canCopy)
                }
            }
            |> deliverOnMainQueue).startStrict(next: { [weak self] result in
                if let strongSelf = self, strongSelf.selectedMessages == selectedIds {
                    let (actions, canCopy) = result
                    strongSelf.actions = actions
                    strongSelf.nagramiXCanCopySelection = canCopy
""", "Проверять всё выделение тем же валидатором копирования")
    methods = (overlay / "Sources/ChatMessageSelectionInputPanelNode/NagramiXSelectionTransferMethods.swift.inc").read_text(encoding="utf-8").rstrip("\n") + "\n\n"
    replace_unique(panel, "    private func update(transition: ContainedViewLayoutTransition) {\n", methods + "    private func update(transition: ContainedViewLayoutTransition) {\n", "Пересылать свежее выделение существующими single и broadcast callbacks")
    replace_unique(panel, """        if self.reportButton.isHidden || (self.peerMedia && self.deleteButton.isHidden && self.reportButton.isHidden) {
""", """        let transferSettings = NagramiXTabSettings.current
        let isSecretChat = interfaceState.renderedPeer?.peer is TelegramSecretChat
        self.forwardWithoutSourceButton.isHidden = !transferSettings.showForwardWithoutAuthor || self.interfaceInteraction?.forwardMessagesWithoutSource == nil || isSecretChat
        self.broadcastButton.isHidden = !transferSettings.showBroadcastMessages || self.interfaceInteraction?.copyMessagesWithoutSource == nil || isSecretChat
        let canCopySelection = self.nagramiXCanCopySelection && self.actions?.isCopyProtected != true
        self.forwardWithoutSourceButton.isEnabled = !self.selectedMessages.isEmpty
        self.broadcastButton.isEnabled = !self.selectedMessages.isEmpty
        self.forwardWithoutSourceButton.isImplicitlyDisabled = !canCopySelection
        self.broadcastButton.isImplicitlyDisabled = !canCopySelection

        if self.reportButton.isHidden || (self.peerMedia && self.deleteButton.isHidden && self.reportButton.isHidden) {
""", "Сохранить настройки видимости и запреты секретных и защищённых сообщений")
    replace_unique(panel, "        let buttons: [GlassButtonView]\n", "        var buttons: [GlassButtonView]\n", "Добавить действия к существующей панели")
    replace_unique(panel, """        let buttonSize = CGSize(width: 40.0, height: 40.0)
""", """        if !self.forwardWithoutSourceButton.isHidden {
            buttons.append(self.forwardWithoutSourceButton)
        }
        if !self.broadcastButton.isHidden {
            buttons.append(self.broadcastButton)
        }

        let buttonSize = CGSize(width: 40.0, height: 40.0)
""", "Сохранить удаление, экспорт, жалобу и метки рядом с тремя пересылками")
    replace_unique(panel, """        let availableWidth = width - leftInset - rightInset
        let spacing: CGFloat = floor((availableWidth - buttonSize.width * CGFloat(buttons.count)) / CGFloat(buttons.count - 1))
        var offset: CGFloat = leftInset
""", """        let availableWidth = max(0.0, width - leftInset - rightInset)
        let minimumContentWidth = buttonSize.width * CGFloat(buttons.count) + 8.0 * CGFloat(buttons.count - 1)
        let contentWidth = max(availableWidth, minimumContentWidth)
        transition.updateFrame(view: self.buttonScrollView, frame: CGRect(x: leftInset, y: 0.0, width: availableWidth, height: panelHeight))
        self.buttonScrollView.contentSize = CGSize(width: contentWidth, height: panelHeight)
        self.buttonScrollView.isScrollEnabled = contentWidth > availableWidth
        let maximumOffset = max(0.0, contentWidth - availableWidth)
        if self.buttonScrollView.contentOffset.x > maximumOffset {
            self.buttonScrollView.setContentOffset(CGPoint(x: maximumOffset, y: 0.0), animated: false)
        }
        let spacing: CGFloat = max(8.0, floor((contentWidth - buttonSize.width * CGFloat(buttons.count)) / CGFloat(buttons.count - 1)))
        var offset: CGFloat = 0.0
""", "Равномерные интервалы и прокрутка вместо отрицательных отступов")
    replace_unique(panel, "CGPoint(x: width - rightInset - buttonSize.width, y: 0.0)", "CGPoint(x: contentWidth - buttonSize.width, y: 0.0)", "Правый край последней кнопки в прокручиваемой панели")
    replace_unique(panel, "            let reactionsAnchorRect = tagButton.frame.offsetBy(dx: -54.0, dy: -(panelHeight - size.height) + 14.0)\n", "            let reactionsAnchorRect = self.buttonScrollView.convert(tagButton.frame, to: self.view).offsetBy(dx: -54.0, dy: -(panelHeight - size.height) + 14.0)\n", "Сохранить привязку меток после переноса кнопок")

    interaction = source / paths["interaction"]
    replace_unique(interaction, "    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n", "    public let canCopyMessagesWithoutSource: (([EngineRawMessage]) -> Bool)?\n    public let copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)?\n", "Общий валидатор копирования для независимого модуля панели")
    replace_unique(interaction, "        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n", "        canCopyMessagesWithoutSource: (([EngineRawMessage]) -> Bool)? = nil,\n        copyMessagesWithoutSource: (([EngineRawMessage]) -> Void)? = nil,\n", "Совместимость существующих инициализаторов панели")
    replace_unique(interaction, "        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n", "        self.canCopyMessagesWithoutSource = canCopyMessagesWithoutSource\n        self.copyMessagesWithoutSource = copyMessagesWithoutSource\n", "Сохранить валидатор в интерфейсе панели")
    replace_unique(source / paths["load"], "        }, copyMessagesWithoutSource: { [weak self] messages in\n", "        }, canCopyMessagesWithoutSource: nagramiXCanCopyMessagesAsNew, copyMessagesWithoutSource: { [weak self] messages in\n", "Передать прежний валидатор без новой реализации копирования")

    menus = source / paths["menus"]
    replace_unique(menus, """                    actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXBroadcastMessages, textColor: canForwardWithoutAuthor ? .primary : .disabled, icon: { _ in
                        return nil
                    }, iconAnimation: ContextMenuActionItem.IconAnimation(name: "message_preview_person_off"), action: !canForwardWithoutAuthor ? nil : { _, f in
""", """                    actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXBroadcastMessages, textColor: canForwardWithoutAuthor ? .primary : .disabled, icon: { theme in
                        return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Groups"), color: theme.actionSheet.primaryTextColor)
                    }, action: !canForwardWithoutAuthor ? nil : { _, f in
""", "Отдельная иконка группы людей у рассылки в обычном меню")
    replace_unique(menus, """                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXBroadcastMessages, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Forward"), color: theme.actionSheet.primaryTextColor)
""", """                actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.nagramiXBroadcastMessages, icon: { theme in
                    return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Groups"), color: theme.actionSheet.primaryTextColor)
""", "Та же иконка рассылки у архивных копий")


def apply_deferred_preview_reactions(source: Path, overlay: Path) -> None:
    hashes = {
        "submodules/TelegramCore/Sources/State/MessageReactions.swift": "f4d551a74c7951843309fc472742360fce69348f0ffcf9082fb6ee31270a4cda",
        "submodules/TelegramUI/Sources/NavigateToChatController.swift": "f4705477bf087d0b008227d1e09a1644339253cb320500bcabf56436df329ef9",
        "submodules/TelegramUI/Sources/ChatController.swift": "1b3aab451e58512369aaa3489573e53ca68b19f2fae6d2a44a2a82528ae4aec0",
        "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift": "9c4cb68997799e6493b0cb8b6dc7b0dd0aa34fca6b9b920d30a2de061855e538",
        "submodules/TelegramUI/Sources/Chat/ChatControllerOpenMessageContextMenu.swift": "d04da4daa28b940930c6da334deee233c85b0f9fb251896273491880f0450379",
        "submodules/TelegramUI/Sources/ChatControllerOpenMessageReactionContextMenu.swift": "2c71470a1f15cb19602f121fa0a7f647c648fbb61892c9d566f4a887163514ff",
        "submodules/TelegramUI/Sources/ChatHistoryListNode.swift": "de2554c1823d6885dfeba4f1c8cb291b8c8095d550272e61af4c057b6cc6354a",
        "submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift": "a1bc12e62b07447ba2944fd85fea2f7c6572ac110e5dfc97cffb5940f0c9ed05",
    }
    for name, expected in hashes.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная интеграция реакций предпросмотра: {name}")

    replace_unique(source / "submodules/TelegramCore/Sources/State/MessageReactions.swift", """public func updateMessageReactionsInteractively(account: Account, messageIds: [MessageId], reactions: [UpdateMessageReaction], isLarge: Bool, storeAsRecentlyUsed: Bool, add: Bool = false) -> Signal<Never, NoError> {
    return account.postbox.transaction { transaction -> Void in
""", """public func updateMessageReactionsInteractively(account: Account, messageIds: [MessageId], reactions: [UpdateMessageReaction], isLarge: Bool, storeAsRecentlyUsed: Bool, add: Bool = false, shouldApply: (() -> Bool)? = nil) -> Signal<Never, NoError> {
    return account.postbox.transaction { transaction -> Void in
        if let shouldApply, !shouldApply() { return }
""", "Не записывать устаревшую отложенную реакцию в штатную очередь")
    ui = source / "submodules/TelegramUI/Sources"
    controller = ui / "ChatController.swift"
    menu = ui / "Chat/ChatControllerOpenMessageContextMenu.swift"
    replace_unique(controller, "    let nagramiXReadHistoryDisabled: Bool\n", "    let nagramiXReadHistoryDisabled: Bool\n    var nagramiXVisibleForDeferredReactions = false\n    var nagramiXKeepFullChatForPreviewReply = false\n", "Видимость обычного чата для отправки реакций")
    replace_unique(controller, """            self.hasBrowserOrAppInFront.get()
        ) |> map { inForeground, globallyEnabled, hasBrowserOrWebAppInFront in
""", """            self.hasBrowserOrAppInFront.get(),
            context.account.nagramiXMessageArchive.deferredReactions.updates
        ) |> map { inForeground, globallyEnabled, hasBrowserOrWebAppInFront, _ in
""", "Загрузка очереди и повторная активация обычного чата")
    replace_unique(controller, """                    strongSelf.raiseToListen?.enabled = effectiveValue
                }
""", """                    strongSelf.raiseToListen?.enabled = effectiveValue
                }
                strongSelf.nagramiXFlushDeferredReactionsIfActive()
""", "Отправлять только при foreground/read/visibility gate")
    replace_unique(ui / "NavigateToChatController.swift", "        if (params.chatController as? ChatControllerImpl)?.nagramiXReadHistoryDisabled != true, case let .peer(peer) = params.chatLocation, case let .channel(channel) = peer, channel.flags.contains(.isForum), !viewForumAsMessages {\n", "        if (params.chatController as? ChatControllerImpl)?.nagramiXReadHistoryDisabled != true, (params.chatController as? ChatControllerImpl)?.nagramiXKeepFullChatForPreviewReply != true, case let .peer(peer) = params.chatLocation, case let .channel(channel) = peer, channel.flags.contains(.isForum), !viewForumAsMessages {\n", "Ответ из полного предпросмотра сохраняет полный форум и штатную проверку возраста")
    methods = (overlay / "Sources/TelegramUI/NagramiXDeferredReactionMethods.swift.inc").read_text(encoding="utf-8")
    replace_unique(controller, "    override public func viewDidAppear(_ animated: Bool) {\n", methods + "\n    override public func viewDidAppear(_ animated: Bool) {\n", "Методы локальных реакций")
    replace_unique(controller, "        self.didAppear = true\n", "        self.didAppear = true\n        self.nagramiXVisibleForDeferredReactions = true\n        self.nagramiXFlushDeferredReactionsIfActive()\n", "Обычное появление чата отправляет отложенные реакции")
    replace_unique(controller, """    override public func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
""", """    override public func viewWillDisappear(_ animated: Bool) {
        self.nagramiXVisibleForDeferredReactions = false
        super.viewWillDisappear(animated)
""", "Скрытый чат не отправляет локальную очередь")
    replace_unique(controller, """            guard let messages = strongSelf.chatDisplayNode.historyNode.messageGroupInCurrentHistoryView(initialMessage.id) else {
                return
            }
            guard let message = messages.first else {
                return
            }
""", """            guard let messages = strongSelf.chatDisplayNode.historyNode.messageGroupInCurrentHistoryView(initialMessage.id) else {
                return
            }
            guard let sourceMessage = messages.first else {
                return
            }
            let message = strongSelf.context.account.nagramiXMessageArchive.deferredReactions.displayMessage(sourceMessage)
""", "Quick reaction учитывает локальный выбор")
    replace_unique(controller, """                    if case .stars = chosenReaction {
                        if !canSendReactionsToChat(strongSelf.presentationInterfaceState) {
""", """                    if case .stars = chosenReaction {
                        if strongSelf.nagramiXReadHistoryDisabled {
                            strongSelf.nagramiXExplainPreviewPaidReactions()
                            return
                        }
                        if !canSendReactionsToChat(strongSelf.presentationInterfaceState) {
""", "Не отправлять платную реакцию из предпросмотра")
    replace_unique(controller, "                        let _ = updateMessageReactionsInteractively(account: strongSelf.context.account, messageIds: [message.id], reactions: mappedUpdatedReactions, isLarge: false, storeAsRecentlyUsed: false).startStandalone()\n", "                        strongSelf.nagramiXUpdateMessageReactions(message: message, reactions: mappedUpdatedReactions, isLarge: false, storeAsRecentlyUsed: false)\n", "Quick reaction локальна только в предпросмотре")
    replace_unique(menu, "            var updatedMessages = messages\n", "            var updatedMessages = messages.map { self.context.account.nagramiXMessageArchive.deferredReactions.displayMessage($0) }\n", "Штатная панель выбора показывает локальные реакции")
    replace_unique(menu, """                    guard let message = messages.first else {
                        return
                    }
""", """                    guard let sourceMessage = messages.first else {
                        return
                    }
                    let message = self.context.account.nagramiXMessageArchive.deferredReactions.displayMessage(sourceMessage)
""", "Меню учитывает последнее локальное состояние реакции")
    replace_unique(menu, """                    if case .stars = chosenUpdatedReaction.reaction {
                        if !canSendReactionsToChat(self.presentationInterfaceState) {
""", """                    if case .stars = chosenUpdatedReaction.reaction {
                        if self.nagramiXReadHistoryDisabled {
                            controller?.dismiss(completion: { [weak self] in
                                self?.nagramiXExplainPreviewPaidReactions()
                            })
                            return
                        }
                        if !canSendReactionsToChat(self.presentationInterfaceState) {
""", "Платное меню не отправляет Stars в предпросмотре")
    replace_unique(menu, "                        let _ = updateMessageReactionsInteractively(account: self.context.account, messageIds: [message.id], reactions: mappedUpdatedReactions, isLarge: isLarge, storeAsRecentlyUsed: true).startStandalone()\n", "                        self.nagramiXUpdateMessageReactions(message: message, reactions: mappedUpdatedReactions, isLarge: isLarge, storeAsRecentlyUsed: true)\n", "Реакция меню сохраняется без сетевой операции")
    replace_unique(ui / "ChatControllerOpenMessageReactionContextMenu.swift", """    func openMessageSendStarsScreen(message: EngineMessage) {
        guard canSendReactionsToChat(self.presentationInterfaceState) else {
""", """    func openMessageSendStarsScreen(message: EngineMessage) {
        if self.nagramiXReadHistoryDisabled {
            self.nagramiXExplainPreviewPaidReactions()
            return
        }
        guard canSendReactionsToChat(self.presentationInterfaceState) else {
""", "Прямой вход Stars тоже защищён до forceSend/purchase")
    replace_unique(ui / "ChatHistoryListNode.swift", "        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates)\n", "        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates, context.account.nagramiXMessageArchive.deferredReactions.updates)\n", "Перерисовка локального выбора без Postbox pending action")
    replace_unique(ui / "ChatHistoryListNode.swift", """        |> map { update, _ in
            return update
        }

        let previousView = self.previousView
""", """        |> map { update, _, _ in
            return update
        }

        let previousView = self.previousView
""", "Обновление представления при загрузке или изменении реакции")
    replace_unique(ui / "ChatHistoryEntriesForView.swift", "        var message = entry.message.withAppliedEphemeralReplacementMessage()\n", "        var message = entry.message.withAppliedEphemeralReplacementMessage()\n        message = context.account.nagramiXMessageArchive.deferredReactions.displayMessage(message)\n", "Синтетическая реакция только в отображаемом Message")

    load = ui / "Chat/ChatControllerLoadDisplayNode.swift"
    replace_unique(load, """        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage: { [weak self] messageId, innerSubject, completion in
            guard let strongSelf = self, strongSelf.isNodeLoaded else {
                return
            }
            if strongSelf.nagramiXReadHistoryDisabled {
                completion(.immediate, {})
                return
            }
""", """        let interfaceInteraction = ChatPanelInterfaceInteraction(setupReplyMessage: { [weak self] messageId, innerSubject, completion in
            guard let strongSelf = self, strongSelf.isNodeLoaded else {
                return
            }
            if strongSelf.nagramiXReadHistoryDisabled {
                guard let messageId,
                      canSendMessagesToChat(strongSelf.presentationInterfaceState),
                      !strongSelf.presentAccountFrozenInfoIfNeeded(delay: true),
                      let message = strongSelf.chatDisplayNode.historyNode.messageInCurrentHistoryView(messageId)?._asMessage(),
                      let navigationController = strongSelf.navigationController as? NavigationController else {
                    completion(.immediate, {})
                    return
                }
                let location: NavigateToChatControllerParams.Location
                switch strongSelf.chatLocation {
                case let .peer(peerId):
                    guard let peer = strongSelf.presentationInterfaceState.renderedPeer?.peer, peer.id == peerId else {
                        completion(.immediate, {})
                        return
                    }
                    location = .peer(EnginePeer(peer))
                case let .replyThread(thread):
                    location = .replyThread(thread)
                case .customChatContents:
                    completion(.immediate, {})
                    return
                }
                // Wait for native context-menu dismissal before normal navigation.
                // The readonly controller's immutable policy is never weakened.
                completion(.immediate, { [weak self] in
                    guard let self else { return }
                    let active = ChatControllerImpl(context: self.context, chatLocation: location.asChatLocation,
                        chatLocationContextHolder: self.chatLocationContextHolder, chatListFilter: self.currentChatListFilter)
                    active.nagramiXKeepFullChatForPreviewReply = true
                    self.context.sharedContext.navigateToChatController(NavigateToChatControllerParams(
                        navigationController: navigationController, chatController: active, context: self.context, chatLocation: location,
                        chatLocationContextHolder: self.chatLocationContextHolder,
                        activateInput: .text, keepStack: .always, useExisting: false,
                        chatListFilter: self.currentChatListFilter,
                        completion: { controller in
                            guard let active = controller as? ChatControllerImpl, !active.nagramiXReadHistoryDisabled else { return }
                            _ = active.displayNode
                            active.updateChatPresentationInterfaceState(animated: false, interactive: true, saveInterfaceState: true, {
                                $0.updatedInterfaceState {
                                    $0.withUpdatedReplyMessageSubject(ChatInterfaceState.ReplyMessageSubject(
                                        messageId: message.id, quote: nil, innerSubject: innerSubject
                                    ))
                                }.updatedReplyMessage(message).updatedSearch(nil).updatedShowCommands(false)
                            })
                            active.chatDisplayNode.ensureInputViewFocused()
                        }, forceOpenChat: true
                    ))
                })
                return
            }
""", "Только Ответить открывает новое обычное окно с выбранным сообщением")
    replace_unique(controller, """            apply(self.didAppear ? .animated(duration: 0.4, curve: .spring) : .immediate)
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
            self.currentChatSwitchDirection = nil
            self.isUpdatingChatLocationThread = false
""", """            apply(self.didAppear ? .animated(duration: 0.4, curve: .spring) : .immediate)
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
            self.currentChatSwitchDirection = nil
            self.isUpdatingChatLocationThread = false
            self.nagramiXFlushDeferredReactionsIfActive()
""", "Новая обычная локация отправляет только свою очередь")
    replace_unique(controller, """            apply(.animated(duration: 0.4, curve: .spring))
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
            self.currentChatSwitchDirection = nil
            self.isUpdatingChatLocationThread = false
""", """            apply(.animated(duration: 0.4, curve: .spring))
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
            self.currentChatSwitchDirection = nil
            self.isUpdatingChatLocationThread = false
            self.nagramiXFlushDeferredReactionsIfActive()
""", "Отдельный переход в тему отправляет её отложенные реакции")
    replace_unique(controller, """                self.isUpdatingChatLocationThread = false
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
                self.chatDisplayNode.textInputPanelNode?.ignoreInputStateUpdates = false
""", """                self.isUpdatingChatLocationThread = false
                self.nagramiXFlushDeferredReactionsIfActive()
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
                self.chatDisplayNode.textInputPanelNode?.ignoreInputStateUpdates = false
""", "Активная вкладка форума отправляет очередь после замены истории")
    core = overlay / "Sources/TelegramCore/NagramiXDeferredReactionsStore.swift"
    shutil.copy2(core, source / "submodules/TelegramCore/Sources/Utils" / core.name)


def apply_in_app_notification_sound_default(source: Path) -> None:
    path = source / "submodules/TelegramUIPreferences/Sources/InAppNotificationSettings.swift"
    if hashlib.sha256(path.read_bytes()).hexdigest() != "00fc3fbe70340ed770e091a2c12e60363347992e850e16321e87310741a2d557":
        raise SystemExit(f"Изменился проверенный источник настроек звука в приложении: {path}")
    replace_unique(
        path,
        "return InAppNotificationSettings(playSounds: true, vibrate: false, displayPreviews: true,",
        "return InAppNotificationSettings(playSounds: false, vibrate: false, displayPreviews: true,",
        "Звук в приложении выключен только при отсутствии сохранённых настроек",
    )


def apply_story_viewing_mode_confirmation(source: Path) -> None:
    """Один pre-view экран по фактическому режиму текущей сессии историй."""
    path = source / "submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/StoryContainerScreen.swift"
    original = path.read_text(encoding="utf-8")
    if hashlib.sha256(path.read_bytes()).hexdigest() != "a5372c0d82317ed53197d9801712133888d7e89b7a52f96bde64cdc465a4c6a5":
        raise SystemExit("Изменилась проверенная интеграция подтверждения историй или правка уже применена")
    changes = [
        ("    private var nagramiXApprovedStoryId: EngineStoryId?\n",
         "    private var nagramiXApprovedStoryId: EngineStoryId?\n    private var nagramiXAcknowledgedAnonymousViewing = false\n"),
        ("    fileprivate func nagramiXConfirmNavigation(peer: EnginePeer, item: StoryContentItem, action: @escaping () -> Void) {\n        guard NagramiXTabSettings.current.confirmStoryViewing, peer.id != self.context.account.peerId else {\n",
         """    private func nagramiXUsesAnonymousViewing(peer: EnginePeer, item: StoryContentItem) -> Bool {
        if case .liveStream = item.storyItem.media { return false }
        return self.nagramiXContent.nagramiXAnonymousViewing && (item.itemPeer ?? peer).id != self.context.account.peerId
    }

    fileprivate func nagramiXConfirmNavigation(peer: EnginePeer, item: StoryContentItem, action: @escaping () -> Void) {
        let anonymousViewing = self.nagramiXUsesAnonymousViewing(peer: peer, item: item)
        let needsConfirmation = anonymousViewing ? !self.nagramiXAcknowledgedAnonymousViewing : NagramiXTabSettings.current.confirmStoryViewing
        guard needsConfirmation, peer.id != self.context.account.peerId else {
"""),
        ("    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {\n        guard NagramiXTabSettings.current.confirmStoryViewing else {\n",
         "    public func nagramiXPresent(from parentController: ViewController, action: @escaping () -> Void) {\n        guard NagramiXTabSettings.current.confirmStoryViewing || self.nagramiXContent.nagramiXAnonymousViewing else {\n"),
        ("            if slice.effectivePeer.id == self.context.account.peerId {\n                action()\n                return\n            }\n\n            self.nagramiXIsPresentingConfirmation = true\n",
         """            let anonymousViewing = self.nagramiXUsesAnonymousViewing(peer: slice.effectivePeer, item: slice.item)
            let needsConfirmation = anonymousViewing ? !self.nagramiXAcknowledgedAnonymousViewing : NagramiXTabSettings.current.confirmStoryViewing
            if slice.effectivePeer.id == self.context.account.peerId || !needsConfirmation {
                action()
                return
            }

            self.nagramiXIsPresentingConfirmation = true
"""),
        ("                self.nagramiXApprovedStoryId = item.id\n",
         "                if anonymousViewing { self.nagramiXAcknowledgedAnonymousViewing = true }\n                self.nagramiXApprovedStoryId = item.id\n"),
        ("                    self?.nagramiXApprovedStoryId = slice.item.id\n",
         "                    if anonymousViewing { self?.nagramiXAcknowledgedAnonymousViewing = true }\n                    self?.nagramiXApprovedStoryId = slice.item.id\n"),
        ("        self.titleLabel.textAlignment = .center\n        self.bodyLabel.textColor",
         "        self.titleLabel.textAlignment = .center\n        self.titleLabel.numberOfLines = 0\n        self.bodyLabel.textColor"),
    ]
    for indent in ("            ", "                "):
        changes.append((
            indent + "title: presentationData.strings.nagramiXStoryConfirmationTitle,\n" +
            indent + "body: presentationData.strings.nagramiXStoryConfirmationText(owner: owner),\n" +
            indent + "action: presentationData.strings.nagramiXViewStoryAction,\n",
            indent + "title: anonymousViewing ? presentationData.strings.nagramiXAnonymousStoryPreviewTitle : presentationData.strings.nagramiXStoryConfirmationTitle,\n" +
            indent + "body: anonymousViewing ? presentationData.strings.nagramiXAnonymousStoryPreviewText : presentationData.strings.nagramiXStoryConfirmationText(owner: owner),\n" +
            indent + "action: anonymousViewing ? presentationData.strings.nagramiXAnonymousStoryPreviewAction : presentationData.strings.nagramiXViewStoryAction,\n",
        ))
    result = original
    for old, new in changes:
        if result.count(old) != 1:
            raise SystemExit("Изменился точный якорь выбора режима подтверждения историй")
        result = result.replace(old, new, 1)
    # Approval/read gate, cancellation, preview fetch and all receipt policies
    # intentionally stay unchanged. Only the pre-view presentation is selected.
    path.write_text(result, encoding="utf-8")


def apply_option_selection_sheets(source: Path, overlay: Path) -> None:
    """Общий штатный sheet для выбора режима загрузки и таймера прокси."""
    proxy = source / "submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift"
    if hashlib.sha256(proxy.read_bytes()).hexdigest() != "df0d21843e665276dcdc4da23584ce69df24aa629267234e93c611afdfabe77f":
        raise SystemExit("Изменилась проверенная интеграция таймера прокси или панель уже применена")
    old = """    selectTimeoutImpl = {
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
"""
    new = """    selectTimeoutImpl = {
        let presentationData = sharedContext.currentPresentationData.with { $0 }
        let currentTimeout = NagramiXTabSettings.current.proxyAutoSwitchTimeout
        let values = [15, 30, 60]
        let options = values.map { value in
            NagramiXOptionSheetOption(id: value, title: nagramiXTimeoutTitle(value, strings: presentationData.strings), subtitle: "")
        }
        let actionSheet = nagramiXOptionSheet(presentationData: presentationData, title: presentationData.strings.nagramiXProxySwitchAfter, options: options, selectedId: currentTimeout, footnote: presentationData.strings.nagramiXProxyTimeoutInfo, selected: { value in
            guard values.contains(value) else { return }
            updateNagramiXSettings { $0.proxyAutoSwitchTimeout = value }
        })
        presentControllerImpl?(actionSheet)
    }
"""
    # Validate the durable component before mutating the audited native input.
    component = overlay / "Sources/SettingsUI/NagramiXOptionSheet.swift"
    if not component.is_file():
        raise SystemExit("Отсутствует общий компонент панели выбора")
    replace_unique(proxy, old, new, "Современная панель 15/30/60 с отдельной галочкой")
    shutil.copy2(component, source / "submodules/SettingsUI/Sources/NagramiXOptionSheet.swift")


def apply_proxy_vpn_policy_and_layout(source: Path, overlay: Path) -> None:
    """VPN-политика поверх сохранённого прокси и порядок блоков интерфейса."""
    inputs = {
        "submodules/TelegramCore/Sources/Account/Account.swift": "c79fccdd30ab820d3197f92d248d0d4d91d3c89e3443fd6bf6c548c65a7f2ac5",
        "submodules/TelegramCore/Sources/Network/Network.swift": "28896b98a801591c59af3f5aa234ae56153eaa2635826a5a4ebe3925f1fe9323",
        "submodules/TelegramCore/Sources/SyncCore/SyncCore_ProxySettings.swift": "98c12349e1feaed3072d125cdb114bbc4d8ce241a38fdc559dfdcb133efe11ff",
        "submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift": "54f600977ba21fdff4c4d48bf69e2b2d52a4dabf1674c1264f229744716e8e68",
        "submodules/SettingsUI/Sources/Data and Storage/ProxySettingsActionItem.swift": "2d8546b017e137f5f331ac80b83fca79e2918f42eb94e92a41956af35925cb98",
    }
    for name, expected in inputs.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная VPN/proxy интеграция или правка уже применена: {name}")
    policy = overlay / "Sources/TelegramCore/NagramiXProxyVPNPolicy.swift"
    if not policy.is_file():
        raise SystemExit("Отсутствует компонент политики VPN")
    account, network, settings, proxy, action_item = [source / name for name in inputs]
    changes: list[tuple[Path, str, str]] = []

    def patch(path: Path, old: str, new: str) -> None:
        changes.append((path, old, new))

    patch(settings,
        "    public var effectiveActiveServer: ProxyServerSettings? {\n",
        "    public var effectiveActiveServer: ProxyServerSettings? {\n        guard !NagramiXProxyVPNPolicy.bypassed else { return nil }\n")
    patch(account,
        "        self.proxySettingsDisposable.set((accountManager.sharedData(keys: [SharedDataKeys.proxySettings])\n        |> map { sharedData -> ProxyServerSettings? in\n",
        "        self.proxySettingsDisposable.set((combineLatest(accountManager.sharedData(keys: [SharedDataKeys.proxySettings]), NagramiXProxyVPNPolicy.bypassedSignal())\n        |> map { sharedData, _ -> ProxyServerSettings? in\n")
    patch(account,
        "        self.managedOperationsDisposable.add((accountManager.sharedData(keys: [SharedDataKeys.proxySettings])\n        |> map { sharedData -> ProxyServerSettings? in\n",
        "        self.managedOperationsDisposable.add((combineLatest(accountManager.sharedData(keys: [SharedDataKeys.proxySettings]), NagramiXProxyVPNPolicy.bypassedSignal())\n        |> map { sharedData, _ -> ProxyServerSettings? in\n")
    patch(network,
        "    func updateProxySettings(_ activeServer: ProxyServerSettings?) {\n",
        "    func updateProxySettings(_ activeServer: ProxyServerSettings?) {\n        let activeServer = NagramiXProxyVPNPolicy.bypassed ? nil : activeServer\n")
    patch(action_item,
        "textColor: item.presentationData.theme.list.itemAccentColor), backgroundColor: nil, maximumNumberOfLines: 1,",
        "textColor: item.presentationData.theme.list.itemAccentColor), backgroundColor: nil, maximumNumberOfLines: 0,")

    old_block = (overlay / "Sources/SettingsUI/ProxyListNagramiXBlock.swift.inc").read_text(encoding="utf-8")
    block = old_block

    def edit(old: str, new: str) -> None:
        nonlocal block
        if block.count(old) != 1:
            raise SystemExit("Изменился точный якорь интерфейса VPN/списка прокси")
        block = block.replace(old, new, 1)

    edit("    let toggleAutoSwitch: (Bool) -> Void\n",
         "    let toggleAutoSwitch: (Bool) -> Void\n    let toggleAvoidProxyWithVPN: (Bool) -> Void = { value in NagramiXTabSettings.update { $0.avoidProxyWithVPN = value } }\n")
    # Existing section values and stable IDs survive; ordering is explicit below.
    edit("    case share\n}", "    case share\n    case check\n}")
    edit("    case checkAllProxies(PresentationTheme, String, Bool)\n",
         "    case checkAllProxies(PresentationTheme, String, Bool)\n    case avoidProxyWithVPN(PresentationTheme, String, Bool)\n    case avoidProxyWithVPNInfo(PresentationTheme, String)\n")
    edit("        case .enabled, .dns, .customDoh, .autoSwitch, .autoSwitchTimeout, .checkAllProxies:\n",
         "        case .enabled, .dns, .customDoh, .autoSwitch, .autoSwitchTimeout, .avoidProxyWithVPN, .avoidProxyWithVPNInfo:\n")
    edit("        case .shareProxyList:\n            return ProxySettingsControllerSection.share.rawValue\n",
         "        case .shareProxyList:\n            return ProxySettingsControllerSection.share.rawValue\n        case .checkAllProxies:\n            return ProxySettingsControllerSection.check.rawValue\n")
    edit("        case .checkAllProxies: return 5\n",
         "        case .avoidProxyWithVPN: return 5\n        case .avoidProxyWithVPNInfo: return 6\n        case .checkAllProxies: return 7\n")
    edit("        case .shareProxyList: return 10_000\n", "        case .shareProxyList: return 8\n")
    edit("        case .checkAllProxies: return .index(5)\n",
         "        case .checkAllProxies: return .index(5)\n        case .avoidProxyWithVPN: return .index(15)\n        case .avoidProxyWithVPNInfo: return .index(16)\n")
    edit("        case let (.autoSwitch(lt, ls, lv), .autoSwitch(rt, rs, rv)):\n",
         "        case let (.autoSwitch(lt, ls, lv), .autoSwitch(rt, rs, rv)), let (.avoidProxyWithVPN(lt, ls, lv), .avoidProxyWithVPN(rt, rs, rv)):\n")
    edit("        case let (.serversHeader(lt, ls), .serversHeader(rt, rs)),",
         "        case let (.avoidProxyWithVPNInfo(lt, ls), .avoidProxyWithVPNInfo(rt, rs)), let (.serversHeader(lt, ls), .serversHeader(rt, rs)),")
    edit("        case let .autoSwitchTimeout(_, title, value):\n",
         "        case let .avoidProxyWithVPN(_, title, value):\n            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: title, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.toggleAvoidProxyWithVPN)\n        case let .avoidProxyWithVPNInfo(_, text):\n            return ItemListTextItem(presentationData: presentationData, text: .plain(text), sectionId: self.section)\n        case let .autoSwitchTimeout(_, title, value):\n")
    edit("title: title, icon: .refresh, sectionId: self.section", "title: title, sectionId: self.section")
    edit("statuses: [ProxyServerSettings: ProxyServerStatus], connectionStatus: ConnectionStatus) -> [ProxySettingsControllerEntry] {",
         "statuses: [ProxyServerSettings: ProxyServerStatus], connectionStatus: ConnectionStatus, vpnBypassed: Bool) -> [ProxySettingsControllerEntry] {")
    edit("    entries.append(.checkAllProxies(theme,",
         "    entries.append(.avoidProxyWithVPN(theme, strings.nagramiXAvoidProxyWithVPN, nagramiXSettings.avoidProxyWithVPN))\n    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))\n    entries.append(.checkAllProxies(theme,")
    # Settings are concise: omit help footers while retaining the native controls.
    edit("        entries.append(.useForCallsInfo(theme, strings.SocksProxySetup_UseForCallsHelp))\n", "")
    # ItemList entries must already follow the same order as their comparator.
    edit("    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))\n    entries.append(.checkAllProxies(theme, state.checkingAllProxies ? strings.nagramiXProxyChecking : strings.nagramiXProxyCheckAll, state.checkingAllProxies))\n",
         "    entries.append(.checkAllProxies(theme, state.checkingAllProxies ? strings.nagramiXProxyChecking : strings.nagramiXProxyCheckAll, state.checkingAllProxies))\n    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))\n")
    edit("    }\n    entries.append(.shareProxyList(theme, strings.SocksProxySetup_ShareProxyList))\n    return entries\n",
         "    }\n    return entries\n")
    edit("        if proxySettings.enabled && server == proxySettings.activeServer {\n",
         "        if proxySettings.enabled && !vpnBypassed && server == proxySettings.activeServer {\n")
    edit("revealed: state.revealedServer == server), proxySettings.enabled))\n",
         "revealed: state.revealedServer == server), proxySettings.enabled && !vpnBypassed))\n")
    patch(proxy, old_block, block)
    patch(proxy,
        "    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus, nagramiXSettingsPromise.get())\n    |> map { presentationData, state, proxySettings, statuses, connectionStatus, nagramiXSettings ->",
        "    let signal = combineLatest(updatedPresentationData, statePromise.get(), proxySettings.get(), statusesContext.statuses(), network.connectionStatus, nagramiXSettingsPromise.get(), NagramiXProxyVPNPolicy.bypassedSignal())\n    |> map { presentationData, state, proxySettings, statuses, connectionStatus, nagramiXSettings, vpnBypassed ->")
    patch(proxy,
        "nagramiXSettings: nagramiXSettings, statuses: statuses, connectionStatus: connectionStatus)",
        "nagramiXSettings: nagramiXSettings, statuses: statuses, connectionStatus: connectionStatus, vpnBypassed: vpnBypassed)")
    # All hashes/anchors are checked in memory before any native file is written.
    outputs: dict[Path, str] = {}
    for path, old, new in changes:
        text = outputs.get(path, path.read_text(encoding="utf-8"))
        if text.count(old) != 1:
            raise SystemExit(f"Изменился точный якорь VPN/proxy интеграции: {path.name}")
        outputs[path] = text.replace(old, new, 1)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    shutil.copy2(policy, source / "submodules/TelegramCore/Sources/NagramiXProxyVPNPolicy.swift")


def apply_hide_greeting_sticker(source: Path, overlay: Path) -> None:
    """Штатная пустая надпись без приветствия и его фоновой загрузки."""
    inputs = {
        "submodules/TelegramUI/Components/Chat/ChatEmptyNode/Sources/ChatEmptyNode.swift": "18aca355e109943db9dbb3c4aae62ae7c7f90be29d5ebadbc962db3e492617a2",
        "submodules/TelegramUI/Components/Chat/ChatEmptyNode/BUILD": "42162ecc1707943026008208145cc087f6286638eab45c2828a3344cc450173e",
        "submodules/TelegramUI/Sources/PrefetchManager.swift": "b09db66ae957cab8e1d48738c16f72a0dfb7e5c67a1c38d84828e918604d5dfb",
    }
    for name, expected in inputs.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная интеграция приветствий или правка уже применена: {name}")
    node, build, prefetch = [source / name for name in inputs]
    changes: list[tuple[Path, str, str]] = []

    def patch(path: Path, old: str, new: str) -> None:
        changes.append((path, old, new))

    patch(build, '        "//submodules/TelegramPresentationData",\n',
          '        "//submodules/TelegramPresentationData",\n        "//submodules/NagramiXCore:NagramiXCore",\n')
    patch(node, "import Foundation\n", "import Foundation\nimport NagramiXCore\n")
    patch(node, "                sticker = preloadedSticker\n",
          """                // A greeting hidden earlier may have a nil preload. Restore
                // the native random sticker path when the user enables greetings.
                sticker = preloadedSticker
                |> mapToSignal { [weak self] file -> Signal<TelegramMediaFile?, NoError> in
                    if let file { return .single(file) }
                    guard let self else { return .single(nil) }
                    return self.context.engine.stickers.randomGreetingSticker()
                    |> map { $0?.file }
                }
""")
    patch(node, "    private var attachedDescriptionNode: EmptyAttachedDescriptionNode?\n",
          "    private var attachedDescriptionNode: EmptyAttachedDescriptionNode?\n    private var nagramiXSettingsObserver: NSObjectProtocol?\n    private var nagramiXRefreshGreeting: (() -> Void)?\n")
    patch(node, "        self.addSubnode(self.backgroundNode)\n    }\n    \n    override public func hitTest",
          """        self.addSubnode(self.backgroundNode)
        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { [weak self] _ in
            self?.nagramiXRefreshGreeting?()
        })
    }

    deinit {
        if let observer = self.nagramiXSettingsObserver { NotificationCenter.default.removeObserver(observer) }
    }

    override public func hitTest""")
    patch(node, "        self.wallpaperBackgroundNode = backgroundNode\n",
          """        self.wallpaperBackgroundNode = backgroundNode
        self.nagramiXRefreshGreeting = { [weak self, weak backgroundNode] in
            self?.updateLayout(interfaceState: interfaceState, subject: subject, loadingNode: nil, backgroundNode: backgroundNode, size: size, insets: insets, leftInset: leftInset, rightInset: rightInset, transition: .immediate)
        }
""")
    patch(node, "        var updateGreetingSticker = false\n",
          """        // Preserve the explicit business-intro editor preview. Only replace
        // the greeting selected for an actual empty peer conversation.
        if case .greeting = contentType, NagramiXTabSettings.hideGreetingStickerEnabled {
            if case .emptyChat(.customGreeting) = subject {
                // This subject is an explicitly requested editor preview.
            } else {
                contentType = .regular
                displayAttachedDescription = false
            }
        }

        var updateGreetingSticker = false
""")
    patch(prefetch, "import Foundation\n", "import Foundation\nimport NagramiXCore\n")
    patch(prefetch, "    private let preloadGreetingStickerDisposable = MetaDisposable()\n",
          "    private let preloadGreetingStickerDisposable = MetaDisposable()\n    private var nagramiXSettingsObserver: NSObjectProtocol?\n    private var hideGreetingSticker = NagramiXTabSettings.hideGreetingStickerEnabled\n")
    patch(prefetch, "        self.fetchManager = fetchManager\n",
          """        self.fetchManager = fetchManager
        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async { self?.updateGreetingVisibility() }
        })
""")
    patch(prefetch, "        self.listDisposable?.dispose()\n",
          """        self.listDisposable?.dispose()
        self.preloadGreetingStickerDisposable.dispose()
        if let observer = self.nagramiXSettingsObserver { NotificationCenter.default.removeObserver(observer) }
""")
    patch(prefetch, "    fileprivate func prepareNextGreetingSticker() {\n",
          """    private func updateGreetingVisibility() {
        let hidden = NagramiXTabSettings.hideGreetingStickerEnabled
        guard hidden != self.hideGreetingSticker else { return }
        self.hideGreetingSticker = hidden
        if hidden {
            self.preloadGreetingStickerDisposable.set(nil)
            self.preloadedGreetingStickerPromise.set(.single(nil))
        } else {
            self.prepareNextGreetingSticker()
        }
    }

    fileprivate func prepareNextGreetingSticker() {
        guard !NagramiXTabSettings.hideGreetingStickerEnabled else {
            self.preloadGreetingStickerDisposable.set(nil)
            self.preloadedGreetingStickerPromise.set(.single(nil))
            return
        }
""")
    patch(prefetch, "            if let sticker = sticker {\n",
          "            if let sticker = sticker, !NagramiXTabSettings.hideGreetingStickerEnabled {\n")
    outputs: dict[Path, str] = {}
    for path, old, new in changes:
        text = outputs.get(path, path.read_text(encoding="utf-8"))
        if text.count(old) != 1:
            raise SystemExit(f"Изменился точный якорь приветствий: {path.name}")
        outputs[path] = text.replace(old, new, 1)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")


def apply_recording_music_default(source: Path) -> None:
    """Разрешить штатное смешивание музыки при отсутствии сохранённого выбора."""
    path = source / "submodules/TelegramUIPreferences/Sources/MediaInputSettings.swift"
    text = path.read_text(encoding="utf-8")
    if hashlib.sha256(path.read_bytes()).hexdigest() != "6c6d8c1d137b8408a460816f50666fc104369466fedda18ea36ec933fe9629e1":
        raise SystemExit("Изменились проверенные настройки записи или правка уже применена")
    changes = [
        ("return MediaInputSettings(enableRaiseToSpeak: true, pauseMusicOnRecording: true)",
         "return MediaInputSettings(enableRaiseToSpeak: true, pauseMusicOnRecording: false)"),
        ('forKey: "pauseMusicOnRecording_v2") ?? 1) != 0',
         'forKey: "pauseMusicOnRecording_v2") ?? 0) != 0'),
    ]
    for old, new in changes:
        if text.count(old) != 1:
            raise SystemExit("Изменился точный якорь начального режима записи")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def apply_voice_autoplay_policy(source: Path) -> None:
    """Завершать голосовые и кружки штатно, не открывая следующий элемент."""
    path = source / "submodules/TelegramUI/Sources/SharedMediaPlayer.swift"
    context_source = source / "submodules/TelegramUI/Sources/ChatMessageContextControllerContentSource.swift"
    text = path.read_text(encoding="utf-8")
    if hashlib.sha256(path.read_bytes()).hexdigest() != "73fe67e9d89c15d0789e6f2f28041d63c4f10d0e7e759e29e6969502841b2621":
        raise SystemExit("Изменился проверенный общий плеер или правка уже применена")
    context_text = context_source.read_text(encoding="utf-8")
    if hashlib.sha256(context_source.read_bytes()).hexdigest() != "b849313d4e07fb6baca0b918499d5f1e393be5be24f42ea1001805599e1d8020":
        raise SystemExit("Изменился проверенный экран одноразового сообщения или правка уже применена")
    changes = [
        ("import Foundation\n", "import Foundation\nimport NagramiXCore\n"),
        ("    private var playbackItem: SharedMediaPlaybackItem? {\n",
         "    private var nagramiXPlaybackGeneration: UInt64 = 0\n    private var playbackItem: SharedMediaPlaybackItem? {\n"),
        ("            if playbackItem != oldValue {\n",
         "            if playbackItem != oldValue {\n                self.nagramiXPlaybackGeneration &+= 1\n"),
        ("                        playbackItem.setActionAtEnd({\n",
         "                        let completedPlaybackGeneration = strongSelf.nagramiXPlaybackGeneration\n                        playbackItem.setActionAtEnd({\n"),
        ("                                if let strongSelf = self {\n                                    switch strongSelf.playlist.looping {\n",
         """                                if let strongSelf = self {
                                    if case .voice = type, !NagramiXTabSettings.voiceAutoplayEnabled {
                                        // Capture only a value, never the player owned by this callback.
                                        // Finish once; a late callback cannot close a newly selected message.
                                        guard strongSelf.nagramiXPlaybackGeneration == completedPlaybackGeneration,
                                              !strongSelf.currentPlayedToEnd else { return }
                                        strongSelf.currentPlayedToEnd = true
                                        strongSelf.scheduledPlaybackAction = nil
                                        strongSelf.scheduledStartTime = nil
                                        strongSelf.playbackItem?.pause()
                                        // The native manager clears this player, its panel and video overlay.
                                        // View-once content observes the matching voice player's disappearance.
                                        strongSelf.playedToEnd?()
                                        return
                                    }
                                    switch strongSelf.playlist.looping {
"""),
    ]
    for old, new in changes:
        if text.count(old) != 1:
            raise SystemExit("Изменился точный якорь автовоспроизведения")
        text = text.replace(old, new, 1)
    old_context = """        return self.context.sharedContext.mediaManager.globalMediaPlayerState
        |> filter { playlistStateAndType in
            if let (_, state, _) = playlistStateAndType, case .state = state {
                return true
            } else {
                return false
            }
        }
        |> take(1)
        |> map { _ in
            return false
        }
        |> then(
            self.context.sharedContext.mediaManager.globalMediaPlayerState
            |> filter { playlistStateAndType in
                return playlistStateAndType == nil
            }
            |> take(1)
            |> map { _ in
                return true
            }
        )
"""
    new_context = """        // Observe this voice item, not the global player which may fall back to music.
        let playbackState = self.context.sharedContext.mediaManager.filteredPlaylistState(
            accountId: self.context.account.id,
            playlistId: PeerMessagesPlaylistLocation.singleMessage(self.message.id).playlistId,
            itemId: PeerMessagesMediaPlaylistItemId(messageId: self.message.id, messageIndex: self.message.index),
            type: .voice
        )
        return playbackState
        |> filter { $0 != nil }
        |> take(1)
        |> map { _ in false }
        |> then(
            playbackState
            |> filter { $0 == nil }
            |> take(1)
            |> map { _ in true }
        )
"""
    if context_text.count(old_context) != 1:
        raise SystemExit("Изменился точный якорь закрытия одноразового сообщения")
    context_text = context_text.replace(old_context, new_context, 1)
    path.write_text(text, encoding="utf-8")
    context_source.write_text(context_text, encoding="utf-8")


def apply_authorization_alert_handling(source: Path) -> None:
    """Сохранить серверную причину и не наслаивать предупреждения о сессии."""
    hashes = {
        "submodules/TelegramUI/Sources/ApplicationContext.swift": "09b0c06a1115f5d50b504d21ec5d45bbdc7c1850087509e196a40e288bcee33d",
        "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift": "3891a1cefcd4590cc77d89e71aca9e1ed2add1ae8ffacda625987c6fe73aa4ee",
    }
    for name, expected in hashes.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная обработка авторизации или правка уже применена: {name}")
    changes = {
        "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift": [
            (
                '                    updatedState.addDisplayAlert(text, isDropAuth: type.hasPrefix("AUTH_KEY_DROP_"))\n',
                """                    let isDropAuth = type.hasPrefix("AUTH_KEY_DROP_")
                    if isDropAuth {
                        // Log only a bounded server reason, never the body, account or auth key.
                        let safeType = type.utf8.count <= 80 && type.utf8.allSatisfy { byte in
                            (byte >= 65 && byte <= 90) || (byte >= 48 && byte <= 57) || byte == 95
                        } ? type : "AUTH_KEY_DROP_UNSPECIFIED"
                        Logger.shared.log("State", "authorization service notification: \\(safeType)")
                    }
                    updatedState.addDisplayAlert(text, isDropAuth: isDropAuth)
""",
            ),
        ],
        "submodules/TelegramUI/Sources/ApplicationContext.swift": [
            ("import Foundation\n", "import Foundation\nimport NagramiXCore\n"),
            (
                "    private var displayAlertsDisposable: Disposable?\n",
                """    private var displayAlertsDisposable: Disposable?
    private weak var nagramiXAuthorizationAlert: ViewController?
    private var nagramiXLastAuthorizationAlertText: String?
    private var nagramiXLastAuthorizationAlertTime: TimeInterval = -.infinity
""",
            ),
            (
                """                for (text, isDropAuth) in alerts {
                    let presentationData = strongSelf.context.sharedContext.currentPresentationData.with { $0 }
""",
                """                for (text, isDropAuth) in alerts {
                    guard let presenter = strongSelf.rootController.viewControllers.last as? ViewController else { continue }
                    let now = ProcessInfo.processInfo.systemUptime
                    if isDropAuth {
                        let repeatedRecently = strongSelf.nagramiXLastAuthorizationAlertText == text
                            && now - strongSelf.nagramiXLastAuthorizationAlertTime < 60.0
                        if strongSelf.nagramiXAuthorizationAlert != nil || repeatedRecently {
                            Logger.shared.log("ApplicationContext", "duplicate authorization alert deferred")
                            continue
                        }
                    }
                    let presentationData = strongSelf.context.sharedContext.currentPresentationData.with { $0 }
                    // Translate the known stock notice only; preserve other server instructions.
                    let displayText: String
                    if isDropAuth && text.hasPrefix("Authorization error. Use the \\"Log out\\" button to log out, then log in again with your phone number.") {
                        displayText = presentationData.strings.nagramiXAuthorizationError
                    } else {
                        displayText = text
                    }
""",
            ),
            (
                """                        actions = [TextAlertAction(type: .genericAction, title: presentationData.strings.Common_Cancel, action: {}), TextAlertAction(type: .genericAction, title: presentationData.strings.LogoutOptions_LogOut, action: {
                            if let strongSelf = self {
                                let _ = logoutFromAccount(id: strongSelf.context.account.id, accountManager: strongSelf.context.sharedContext.accountManager, alreadyLoggedOutRemotely: false).start()
""",
                """                        actions = [TextAlertAction(type: .genericAction, title: presentationData.strings.Common_Cancel, action: { [weak self] in
                            self?.nagramiXAuthorizationAlert = nil
                        }), TextAlertAction(type: .genericAction, title: presentationData.strings.LogoutOptions_LogOut, action: { [weak self] in
                            if let strongSelf = self {
                                strongSelf.nagramiXAuthorizationAlert = nil
                                let _ = logoutFromAccount(id: strongSelf.context.account.id, accountManager: strongSelf.context.sharedContext.accountManager, alreadyLoggedOutRemotely: false).start()
""",
            ),
            (
                """                    let controller = textAlertController(context: strongSelf.context, title: nil, text: text, actions: actions)
                    (strongSelf.rootController.viewControllers.last as? ViewController)?.present(controller, in: .window(.root))
""",
                """                    let controller = textAlertController(context: strongSelf.context, title: nil, text: displayText, actions: actions)
                    if isDropAuth {
                        strongSelf.nagramiXAuthorizationAlert = controller
                        strongSelf.nagramiXLastAuthorizationAlertText = text
                        strongSelf.nagramiXLastAuthorizationAlertTime = now
                    }
                    presenter.present(controller, in: .window(.root))
""",
            ),
        ],
    }
    outputs: dict[Path, str] = {}
    for name, substitutions in changes.items():
        path = source / name
        text = path.read_text(encoding="utf-8")
        for old, new in substitutions:
            if text.count(old) != 1:
                raise SystemExit(f"Изменился точный якорь предупреждения авторизации: {name}")
            text = text.replace(old, new, 1)
        outputs[path] = text
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")


def apply_recording_session_continuity(source: Path) -> None:
    """Смешивание без лишней смены маршрута и завершение повторных записей."""
    hashes = {
        "submodules/TelegramAudio/Sources/ManagedAudioSession.swift": "f12f5701d8951d8eb1e148aecd6081320e59b8d500d2f3c88909cc45699c1296",
        "submodules/TelegramUI/Sources/ManagedAudioRecorder.swift": "1ad674a5a2e39d625ad8683b2050f58e5c92ea19749ad86551609248b5729e7a",
        "submodules/Camera/CameraLegacy/Sources/CameraOutput.swift": "8421579cb7b047b43da249d42252b3f12688b51aeeaa9dcd7423b1b9fd6e621b",
        "submodules/Camera/CameraLegacy/Sources/VideoRecorder.swift": "d83cad4d7bfa090fc679d10962ecd7216231da5c1c6f9af5713e33814f342a8f",
        "submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift": "57f469b3e126a36563402d57b8e0752863895ecf86beb30943a48f1bdd9e4e6d",
        "submodules/Camera/CameraLegacy/Sources/LegacyCamera.swift": "d98cb8c945e743e6fa9e34c6fd5ea977481b270d39a358d4304ecc49925dc8a6",
        "submodules/TelegramUI/Sources/Chat/ChatControllerMediaRecording.swift": "fbecdeee7c14632280ff3e09f3a229eaf94d2ea95e8b96865db072b0c06bb53b",
    }
    for name, expected in hashes.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменился проверенный рекордер или правка уже применена: {name}")
    changes = {
        "submodules/TelegramUI/Sources/Chat/ChatControllerMediaRecording.swift": [
            (
                "                let controller = VideoMessageCameraScreen(\n",
                "                weak var nagramiXRecordingController: VideoMessageCameraScreen?\n                let controller = VideoMessageCameraScreen(\n",
            ),
            (
                "                        guard let self, let videoController = self.videoRecorderValue else {\n",
                "                        guard let self, let videoController = self.videoRecorderValue, videoController === nagramiXRecordingController else {\n",
            ),
            (
                """                                guard let self else {
                                    return
                                }
                                self.videoRecorder.set(.single(nil))
""",
                """                                guard let self, let videoController, self.videoRecorderValue === videoController else {
                                    return
                                }
                                self.videoRecorder.set(.single(nil))
""",
            ),
            (
                """                controller.onResume = { [weak self] in
                    guard let self else {
""",
                """                nagramiXRecordingController = controller
                controller.onResume = { [weak self, weak controller] in
                    guard let self, let controller, self.videoRecorderValue === controller else {
""",
            ),
        ],
        "submodules/TelegramAudio/Sources/ManagedAudioSession.swift": [
            (
                """                case let .record(_, video, mixWithOthers):
                    #if canImport(AlarmKit) //Xcode 26
                    options.insert(.allowBluetoothHFP)
                    #else
                    options.insert(.allowBluetooth)
                    #endif
                    if video {
                        options.insert(.allowBluetoothA2DP)
                    }
                    if mixWithOthers {
                        options.insert(.mixWithOthers)
                    }
""",
                """                case let .record(speaker, video, mixWithOthers):
                    let session = AVAudioSession.sharedInstance()
                    let keepStereoOutput = mixWithOthers
                        && session.currentRoute.outputs.contains(where: { $0.portType == .bluetoothA2DP })
                        && session.preferredInput?.portType != .bluetoothHFP
                    // A2DP playback uses the iPhone mic instead of switching to a telephone route.
                    // Keep an explicitly selected HFP input and already active HFP routes available.
                    if !keepStereoOutput {
                        #if canImport(AlarmKit) //Xcode 26
                        options.insert(.allowBluetoothHFP)
                        #else
                        options.insert(.allowBluetooth)
                        #endif
                    }
                    if video || mixWithOthers {
                        options.insert(.allowBluetoothA2DP)
                    }
                    if mixWithOthers {
                        options.insert(.mixWithOthers)
                        if !speaker, !self.isHeadsetPluggedInValue, case .system = outputMode {
                            options.insert(.defaultToSpeaker)
                        }
                    }
""",
            ),
            (
                """                    #else
                    try AVAudioSession.sharedInstance().setCategory(nativeCategory, options: options)
                    try AVAudioSession.sharedInstance().setMode(mode)
                    #endif
""",
                """                    #else
                    if case .record(_, _, true) = type {
                        // Apply mixing/category/mode together, without an intermediate configuration.
                        try AVAudioSession.sharedInstance().setCategory(nativeCategory, mode: mode, options: options)
                    } else {
                        try AVAudioSession.sharedInstance().setCategory(nativeCategory, options: options)
                        try AVAudioSession.sharedInstance().setMode(mode)
                    }
                    #endif
""",
            ),
            (
                """        var resetToBuiltin = false
        switch outputMode {
""",
                """        if case .record(false, false, true) = type, case .system = outputMode {
            // defaultToSpeaker/A2DP follows the existing route; avoid a second port override.
            if ManagedAudioSessionImpl.respectsSystemRecordingInput,
               AVAudioSession.sharedInstance().preferredInput != nil {
                try AVAudioSession.sharedInstance().setPreferredInput(nil)
            }
            return
        }
        var resetToBuiltin = false
        switch outputMode {
""",
            ),
        ],
        "submodules/TelegramUI/Sources/ManagedAudioRecorder.swift": [
            (
                "    private var audioSessionDisposable: Disposable?\n",
                "    private var audioSessionDisposable: Disposable?\n    private var nagramiXAudioSessionGeneration: UInt64 = 0\n",
            ),
            (
                """        if self.audioSessionDisposable == nil {
            let queue = self.queue
""",
                """        if self.audioSessionDisposable == nil {
            self.nagramiXAudioSessionGeneration &+= 1
            let generation = self.nagramiXAudioSessionGeneration
            let queue = self.queue
""",
            ),
            (
                "                    if let strongSelf = self, !strongSelf.paused {\n",
                "                    if let strongSelf = self, !strongSelf.paused, strongSelf.nagramiXAudioSessionGeneration == generation {\n",
            ),
            (
                """                        if let strongSelf = self {
                            strongSelf.hasAudioSession = false
                            strongSelf.stop()
                            strongSelf.recordingState.set(.stopped)
                            subscriber.putCompletion()
                        }
""",
                """                        if let strongSelf = self, strongSelf.nagramiXAudioSessionGeneration == generation {
                            strongSelf.hasAudioSession = false
                            strongSelf.stop()
                            strongSelf.recordingState.set(.stopped)
                        }
                        // A released/stale recorder must still release the managed session holder.
                        subscriber.putCompletion()
""",
            ),
            (
                """        self.paused = true
       \x20
        if let audioUnit = self.audioUnit.swap(nil) {
""",
                """        self.paused = true
        self.hasAudioSession = false
        self.nagramiXAudioSessionGeneration &+= 1
       \x20
        if let audioUnit = self.audioUnit.swap(nil) {
""",
            ),
            (
                """            guard AudioOutputUnitStart(audioUnit) == noErr else {
                self.stop()
                return
            }
        }
""",
                """            guard AudioOutputUnitStart(audioUnit) == noErr else {
                self.stop()
                self.recordingState.set(.stopped)
                return
            }
        } else {
            self.stop()
            self.recordingState.set(.stopped)
        }
""",
            ),
        ],
        "submodules/Camera/CameraLegacy/Sources/CameraOutput.swift": [
            (
                "        let videoRecorder = VideoRecorder(\n",
                "        let recordingCompletionPipe = ValuePipe<VideoCaptureResult>()\n        self.recordingCompletionPipe = recordingCompletionPipe\n        let videoRecorder = VideoRecorder(\n",
            ),
            (
                """            completion: { [weak self] result in
                guard let self else {
                    return
                }
                if case let .success(transitionImage, duration, positionChangeTimestamps) = result {
                    self.recordingCompletionPipe.putNext(
""",
                """            completion: { [recordingCompletionPipe] result in
                if case let .success(transitionImage, duration, positionChangeTimestamps) = result {
                    recordingCompletionPipe.putNext(
""",
            ),
            (
                "                    self.recordingCompletionPipe.putNext(.failed)\n",
                "                    recordingCompletionPipe.putNext(.failed)\n",
            ),
            (
                """        videoRecorder.stop()
       \x20
        return self.recordingCompletionPipe.signal()
        |> take(1)
        |> afterDisposed {
            self.videoRecorder = nil
        }
""",
                """        let recordingCompletionPipe = self.recordingCompletionPipe
        return Signal { subscriber in
            // The completion pipe is hot: subscribe before stopping even on an immediate failure.
            let disposable = (recordingCompletionPipe.signal()
            |> take(1)).start(next: { result in
                subscriber.putNext(result)
                subscriber.putCompletion()
            })
            videoRecorder.stop()
            return ActionDisposable {
                disposable.dispose()
                if self.videoRecorder === videoRecorder {
                    self.videoRecorder = nil
                }
            }
        }
""",
            ),
        ],
        "submodules/Camera/CameraLegacy/Sources/VideoRecorder.swift": [
            (
                """            self.recordingStopSampleTime = stopTime
        }
    }
""",
                """            self.recordingStopSampleTime = stopTime
            // Interrupted capture may never deliver another audio/video buffer past stopTime.
            // Drain the data already recorded instead of waiting for absent buffers forever.
            self.queue.asyncAfter(deadline: .now() + 3.0) { [weak self] in
                guard let self, !self.stopped else { return }
                Logger.shared.log("VideoRecorder", "finishing buffered recording after capture drain timeout")
                let _ = self._stopped.modify { _ in true }
                self.finish()
            }
        }
    }
""",
            ),
        ],
        "submodules/Camera/CameraLegacy/Sources/LegacyCamera.swift": [
            (
                """                    disposable.set(context.stopRecording().start(next: { value in
                        subscriber.putNext(value)
                    }, completed: {
                        subscriber.putCompletion()
                    }))
                }
""",
                """                    disposable.set(context.stopRecording().start(next: { value in
                        subscriber.putNext(value)
                    }, completed: {
                        subscriber.putCompletion()
                    }))
                } else {
                    subscriber.putCompletion()
                }
""",
            ),
        ],
        "submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift": [
            (
                "        func startVideoRecording(pressing: Bool) {\n",
                """        func startVideoRecording(pressing: Bool) {
            guard !self.nagramiXStoppingRecording else { return }
""",
            ),
            (
                """            let initialDuration = controller.node.previewState?.composition.duration.seconds ?? 0.0
""",
                """            self.nagramiXRecordingGeneration &+= 1
            let generation = self.nagramiXRecordingGeneration
            let initialDuration = controller.node.previewState?.composition.duration.seconds ?? 0.0
""",
            ),
            (
                """                    guard let self else {
                        return
                    }
                    self.resultDisposable.set((camera.startRecording()
""",
                """                    guard let self, let controller = self.getController(), !controller.isDismissed,
                          !self.nagramiXStoppingRecording, self.nagramiXRecordingGeneration == generation else {
                        return
                    }
                    self.resultDisposable.set((camera.startRecording()
""",
            ),
            (
                "        func stopVideoRecording() {\n",
                "        private var nagramiXStoppingRecording = false\n        private var nagramiXRecordingGeneration: UInt64 = 0\n\n        func stopVideoRecording() {\n",
            ),
            (
                "    private var isDismissed = false\n",
                "    fileprivate var isDismissed = false\n",
            ),
            (
                """            let currentTimestamp = CACurrentMediaTime()
            if let lastActionTimestamp = controller.lastActionTimestamp, currentTimestamp - lastActionTimestamp < 0.5 {
                return
            }
            controller.lastActionTimestamp = currentTimestamp
           \x20
            self.resultDisposable.set((camera.stopRecording()
            |> deliverOnMainQueue).startStrict(next: { [weak self] result in
                if let self, let controller = self.getController(), case let .finished(mainResult, _, duration, _, _) = result {
""",
                """            guard !self.nagramiXStoppingRecording else { return }
            self.nagramiXStoppingRecording = true
            self.nagramiXRecordingGeneration &+= 1
            controller.lastActionTimestamp = CACurrentMediaTime()
            var receivedStopResult = false
            self.resultDisposable.set((camera.stopRecording()
            |> timeout(30.0, queue: .mainQueue(), alternate: .single(.failed))
            |> deliverOnMainQueue).startStrict(next: { [weak self] result in
                receivedStopResult = true
                guard let self, let controller = self.getController() else { return }
                self.nagramiXStoppingRecording = false
                if case let .finished(mainResult, _, duration, _, _) = result {
""",
            ),
            (
                """                    controller.updateCameraState({ $0.updatedRecording(.none) }, transition: .spring(duration: 0.4))
                }
            }))
""",
                """                    controller.updateCameraState({ $0.updatedRecording(.none) }, transition: .spring(duration: 0.4))
                } else {
                    controller.completion(nil, nil, nil, nil)
                }
            }, completed: { [weak self] in
                guard !receivedStopResult, let self else { return }
                self.nagramiXStoppingRecording = false
                self.getController()?.completion(nil, nil, nil, nil)
            }))
""",
            ),
            (
                """                Queue.mainQueue().after(0.05) {
                    self.node.setupCamera()
                }
""",
                """                Queue.mainQueue().after(0.05) { [weak self] in
                    guard let self, !self.isDismissed else { return }
                    self.node.setupCamera()
                }
""",
            ),
            (
                """        self.node.camera?.stopCapture(invalidate: true)
        self.isDismissed = true
""",
                """        self.isDismissed = true
        self.node.camera?.stopCapture(invalidate: true)
        self.audioSessionDisposable?.dispose()
        self.audioSessionDisposable = nil
""",
            ),
        ],
    }
    outputs: dict[Path, str] = {}
    for name, substitutions in changes.items():
        path = source / name
        text = path.read_text(encoding="utf-8")
        for old, new in substitutions:
            if text.count(old) != 1:
                raise SystemExit(f"Изменился точный якорь повторной записи: {name}")
            text = text.replace(old, new, 1)
        outputs[path] = text
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")


def apply_channel_mute_and_exact_time(source: Path) -> None:
    """Две независимые настройки: новые подписки и точный доступный last seen."""
    hashes = {
        'submodules/TelegramCore/Sources/UpdatePeers.swift': '7d696e770cc3baeaa2dfb079315599c570e900f03fc15ab15778400e8fc3b76f',
        'submodules/TelegramCore/Sources/TelegramEngine/Peers/JoinChannel.swift': '3f1448e540eabb61bbc1fe7ec70074c54a131d06c53170abb3a0032d2a4d3cad',
        'submodules/TelegramCore/Sources/TelegramEngine/Peers/JoinLink.swift': 'c0f570dc3c5089e84cd7c98658200ffdc8f5b3d051a6301bf659e8779928cc6b',
        'submodules/TelegramStringFormatting/Sources/PresenceStrings.swift': '64d55383decfa354a7e93a98c1df339fbe350048c2113e4cff71533f6d94fa82',
        'submodules/TelegramUI/Components/ChatTitleView/Sources/ChatTitleView.swift': '043e8da6f2f626ce913351052f77f5b91f40818cd50bba96e4a13afa48b437fd',
        'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoData.swift': 'a07efec78ca3078ab96ad46f48517f45975bc783935d58e22d258900decca27a',
    }
    changes = {
        'submodules/TelegramCore/Sources/UpdatePeers.swift': [
            (
                'public func updatePeersCustom(transaction: Transaction, peers: [Peer], update: (Peer?, Peer) -> Peer?) {',
                """// Only confirmed new membership invokes this policy; existing dialogs are untouched.
func _internal_nagramiXAutoMuteJoinedChannel(transaction: Transaction, channel: TelegramChannel) {
    guard UserDefaults.standard.object(forKey: "nagramix.messages.autoMuteNewChannels") as? Bool ?? true,
          channel.participationStatus == .member,
          case .broadcast = channel.info,
          !channel.flags.contains(.isCreator) else { return }
    let settings = transaction.getPendingPeerNotificationSettings(channel.id) as? TelegramPeerNotificationSettings
        ?? transaction.getPeerNotificationSettings(id: channel.id) as? TelegramPeerNotificationSettings
        ?? .defaultSettings
    if case let .muted(until) = settings.muteState, until == Int32.max { return }
    // Keep sound, previews and story settings; use Telegram's pending server update.
    transaction.updatePendingPeerNotificationSettings(peerId: channel.id, settings: settings.withUpdatedMuteState(.muted(until: Int32.max)))
}

public func updatePeersCustom(transaction: Transaction, peers: [Peer], update: (Peer?, Peer) -> Peer?) {""",
            ),
            (
                """                let isMember = updated.participationStatus == .member
""",
                """                let isMember = updated.participationStatus == .member
                if previous is TelegramChannel, !wasMember && isMember {
                    _internal_nagramiXAutoMuteJoinedChannel(transaction: transaction, channel: updated)
                }
""",
            ),
        ],
        'submodules/TelegramCore/Sources/TelegramEngine/Peers/JoinChannel.swift': [
            (
                'func _internal_joinChannel(account: Account, peerId: PeerId, hash: String?)',
                """// An imported private channel may not exist in Postbox yet. Initial synchronization
// must never be treated as a new subscription, so only a successful explicit join
// may apply the policy to a previously unknown channel.
func _internal_nagramiXPrepareChannelJoin(account: Account, result: Api.messages.ChatInviteJoinResult) -> Signal<Api.messages.ChatInviteJoinResult, NoError> {
    guard UserDefaults.standard.object(forKey: "nagramix.messages.autoMuteNewChannels") as? Bool ?? true,
          case let .chatInviteJoinResultOk(data) = result else { return .single(result) }
    return account.postbox.transaction { transaction -> Api.messages.ChatInviteJoinResult in
        for chat in data.updates.chats {
            if let channel = parseTelegramGroupOrChannel(chat: chat) as? TelegramChannel,
               transaction.getPeer(channel.id) == nil,
               channel.participationStatus == .member, case .broadcast = channel.info,
               !channel.flags.contains(.isCreator) {
                // Store the input peer in the same transaction as the pending setting.
                // Otherwise the native pending worker could clear it before addUpdates.
                updatePeers(transaction: transaction, accountPeerId: account.peerId, peers: AccumulatedPeers(transaction: transaction, chats: [chat], users: []))
                _internal_nagramiXAutoMuteJoinedChannel(transaction: transaction, channel: channel)
            }
        }
        return result
    }
}

func _internal_joinChannel(account: Account, peerId: PeerId, hash: String?)""",
            ),
            (
                """        return request
        |> mapError""",
                """        return request
        |> mapToSignal { result -> Signal<Api.messages.ChatInviteJoinResult, MTRpcError> in
            return _internal_nagramiXPrepareChannelJoin(account: account, result: result) |> castError(MTRpcError.self)
        }
        |> mapError""",
            ),
        ],
        'submodules/TelegramCore/Sources/TelegramEngine/Peers/JoinLink.swift': [
            (
                """    return account.network.request(Api.functions.messages.importChatInvite(hash: hash), automaticFloodWait: false)
    |> mapError""",
                """    return account.network.request(Api.functions.messages.importChatInvite(hash: hash), automaticFloodWait: false)
    |> mapToSignal { result -> Signal<Api.messages.ChatInviteJoinResult, MTRpcError> in
        return _internal_nagramiXPrepareChannelJoin(account: account, result: result) |> castError(MTRpcError.self)
    }
    |> mapError""",
            ),
        ],
        'submodules/TelegramStringFormatting/Sources/PresenceStrings.swift': [
            (
                'public func stringAndActivityForUserPresence(strings: PresentationStrings, dateTimeFormat: PresentationDateTimeFormat, presence: EnginePeer.Presence, relativeTo timestamp: Int32, expanded: Bool = false) -> (String, Bool) {',
                """public func stringAndActivityForUserPresence(strings: PresentationStrings, dateTimeFormat: PresentationDateTimeFormat, presence: EnginePeer.Presence, relativeTo timestamp: Int32, expanded: Bool = false) -> (String, Bool) {
    let result = nagramiXStockStringAndActivityForUserPresence(strings: strings, dateTimeFormat: dateTimeFormat, presence: presence, relativeTo: timestamp, expanded: expanded)
    guard UserDefaults.standard.object(forKey: "nagramix.profiles.showExactLastSeen") as? Bool ?? false,
          !result.1, case let .present(lastSeen) = presence.status,
          lastSeen > 0, lastSeen < timestamp else { return result }
    var t: time_t = time_t(lastSeen)
    var timeinfo = tm()
    guard localtime_r(&t, &timeinfo) != nil else { return result }
    let time = String(format: "%02d:%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec)
    return (result.0 + " (" + time + ")", result.1)
}

private func nagramiXStockStringAndActivityForUserPresence(strings: PresentationStrings, dateTimeFormat: PresentationDateTimeFormat, presence: EnginePeer.Presence, relativeTo timestamp: Int32, expanded: Bool = false) -> (String, Bool) {""",
            ),
        ],
        'submodules/TelegramUI/Components/ChatTitleView/Sources/ChatTitleView.swift': [
            (
                """    private var presenceManager: PeerPresenceStatusManager?
""",
                """    private var presenceManager: PeerPresenceStatusManager?
    private var nagramiXSettingsObserver: NSObjectProtocol?
    private var nagramiXExactLastSeen = UserDefaults.standard.object(forKey: "nagramix.profiles.showExactLastSeen") as? Bool ?? false
""",
            ),
            (
                """        self.presenceManager = PeerPresenceStatusManager(update: { [weak self] in
            let _ = self?.updateStatus()
        })
""",
                """        self.presenceManager = PeerPresenceStatusManager(update: { [weak self] in
            let _ = self?.updateStatus()
        })
        self.nagramiXSettingsObserver = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXSettingsChanged"), object: nil, queue: .main, using: { [weak self] _ in
            guard let self else { return }
            let enabled = UserDefaults.standard.object(forKey: "nagramix.profiles.showExactLastSeen") as? Bool ?? false
            guard self.nagramiXExactLastSeen != enabled else { return }
            self.nagramiXExactLastSeen = enabled
            let _ = self.updateStatus(enableAnimation: false)
        })
""",
            ),
            (
                """    required public init?(coder aDecoder: NSCoder) {
""",
                """    deinit {
        if let observer = self.nagramiXSettingsObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    required public init?(coder aDecoder: NSCoder) {
""",
            ),
        ],
        'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoData.swift': [
            (
                """                    var currentValue: TelegramUserPresence? = nil
""",
                """                    var currentValue: TelegramUserPresence? = nil
                    var nagramiXHasPresence = false
                    var nagramiXExactLastSeen = UserDefaults.standard.object(forKey: "nagramix.profiles.showExactLastSeen") as? Bool ?? false
""",
            ),
            (
                """                let disposable = (context.account.viewTracker.peerView(userPeerId, updateData: false)
""",
                """                let settingsObserver = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXSettingsChanged"), object: nil, queue: .main, using: { _ in
                    let enabled = UserDefaults.standard.object(forKey: "nagramix.profiles.showExactLastSeen") as? Bool ?? false
                    let refresh = manager.with { manager -> Bool in
                        guard manager.nagramiXExactLastSeen != enabled else { return false }
                        manager.nagramiXExactLastSeen = enabled
                        return manager.nagramiXHasPresence
                    }
                    if refresh { notify() }
                })
                let disposable = (context.account.viewTracker.peerView(userPeerId, updateData: false)
""",
            ),
            (
                """                |> distinctUntilChanged).start(next: { inputData in
                    switch inputData {
""",
                """                |> distinctUntilChanged).start(next: { inputData in
                    let _ = manager.with { manager -> Void in
                        if case .presence = inputData { manager.nagramiXHasPresence = true }
                        else { manager.nagramiXHasPresence = false }
                    }
                    switch inputData {
""",
            ),
            (
                """                return disposable
            }
            |> distinctUntilChanged
""",
                """                return ActionDisposable {
                    NotificationCenter.default.removeObserver(settingsObserver)
                    disposable.dispose()
                }
            }
            |> distinctUntilChanged
""",
            ),
        ],
    }
    prepared = {}
    # Validate the complete audited pin and every unique anchor before any write.
    for name, expected in hashes.items():
        path = source / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменился проверенный источник каналов/статуса или правка уже применена: {name}")
        text = path.read_text(encoding="utf-8")
        for old, new in changes[name]:
            if text.count(old) != 1:
                raise SystemExit(f"Неоднозначный якорь каналов/статуса: {name}")
            text = text.replace(old, new, 1)
        prepared[path] = text
    for path, text in prepared.items():
        path.write_text(text, encoding="utf-8")


def apply_gallery_media_modes(source: Path, overlay: Path) -> None:
    """Standard high-quality photos and original video, with native transport/UI."""
    inputs = {
        "submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift": "40fbb0e9b61397a343ec0fd95ea989a2f283a8f47e7e9b8fc84f432ae0a73abc",
        "submodules/LocalMediaResources/Sources/FetchPhotoLibraryImageResource.swift": "28cc4c366bac47555af73dd6e9ed7ac6854c19f7617b76d00f290a109592a81b",
    }
    for name, expected in inputs.items():
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Изменилась проверенная gallery-media интеграция или правка уже применена: {name}")
    include = overlay / "Sources/LegacyMediaPickerUI/NagramiXOriginalVideos.swift.inc"
    enqueue = overlay / "Sources/LegacyMediaPickerUI/NagramiXOriginalVideoEnqueue.swift.inc"
    if not all(path.is_file() for path in (include, enqueue)):
        raise SystemExit("Отсутствует original-video компонент")
    picker, fetch = [source / name for name in inputs]
    changes = {
        picker: [
            ("import Photos\n", "import Photos\nimport UniformTypeIdentifiers\n"),
            ("private enum LegacyAssetItem {\n", "private enum LegacyAssetItem {\n    case originalVideo(file: TelegramMediaFile, caption: NSAttributedString?)\n"),
            ("        let mediaSettings = NagramiXMediaSettings.current\n", "        let mediaSettings = NagramiXMediaSettings.current\n        let outgoingPhotoQuality = Float(mediaSettings.highQualityPhotos ? 100 : mediaSettings.photoQuality) / 100.0\n        let outgoingPhotoHD = mediaSettings.highQualityPhotos || mediaSettings.sendLargePhotos\n"),
            ("        let disposable = SSignal.combineSignals(signals).start(next: { anyValues in\n", "        let disposable = nagramiXOriginalVideoPickerValues(account: account, signals: signals, enabled: mediaSettings.originalVideos && originalMediaReference == nil).start(next: { anyValues in\n"),
            ("            outer: for item in (anyValues as! NSArray) {\n", "            outer: for item in anyValues {\n"),
            ("                        case let .file(data, thumbnail, mimeType, name, caption):\n", enqueue.read_text(encoding="utf-8") + "                        case let .file(data, thumbnail, mimeType, name, caption):\n"),
            ("            disposable?.dispose()\n        }\n    }\n}\n", "            disposable.dispose()\n        }\n    }\n}\n"),
            ("let maxSize = (item.forceHd || mediaSettings.sendLargePhotos) ?", "let maxSize = (item.forceHd || outgoingPhotoHD) ?"),
            ("let maxSide: CGFloat = (item.forceHd || mediaSettings.sendLargePhotos) ?", "let maxSide: CGFloat = (item.forceHd || outgoingPhotoHD) ?"),
            ("forceHd: item.forceHd || mediaSettings.sendLargePhotos)", "quality: Int32((outgoingPhotoQuality * 100.0).rounded()), forceHd: item.forceHd || outgoingPhotoHD)"),
            ("nagramiXCompressImageToJPEG(scaledImage, quality: Float(mediaSettings.jpegQuality), tempFilePath: tempFile.path)", "nagramiXCompressImageToJPEG(scaledImage, quality: outgoingPhotoQuality, tempFilePath: tempFile.path)"),
        ],
        fetch: [
            ("        let mediaSettings = NagramiXMediaSettings.current\n", "        let mediaSettings = NagramiXMediaSettings.current\n        // New photo resources persist the enqueue-time JPEG quality; old nil-q\n        // resources retain their previous preference fallback. Explicit exports\n        // and JPEG XL continue using their native format-specific paths.\n        let outgoingPhotoQuality = quality.map { Float(min(100, max(0, $0))) / 100.0 } ?? Float(mediaSettings.jpegQuality)\n"),
            ("nagramiXCompressImageToJPEG(scaledImage, quality: Float(mediaSettings.jpegQuality), tempFilePath: tempFile.path)", "nagramiXCompressImageToJPEG(scaledImage, quality: outgoingPhotoQuality, tempFilePath: tempFile.path)"),
        ],
    }
    outputs = {}
    for path, substitutions in changes.items():
        text = path.read_text(encoding="utf-8")
        for old, new in substitutions:
            if text.count(old) != 1:
                raise SystemExit(f"Изменился точный якорь gallery-media интеграции: {path.name}")
            text = text.replace(old, new, 1)
        if path == picker:
            text += "\n" + include.read_text(encoding="utf-8")
        outputs[path] = text
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")


def apply_archived_copy_send_fix(source: Path, overlay: Path) -> None:
    """Stage archived anonymous forwards in the destination; upload retained bytes."""
    paths = {
        "forward": "submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift",
        "node": "submodules/TelegramUI/Sources/ChatControllerNode.swift",
        "options": "submodules/TelegramUI/Sources/Chat/ChatMessageActionOptions.swift",
        "load": "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift",
        "accessory": "submodules/TelegramUI/Sources/ChatInterfaceStateAccessoryPanels.swift",
        "component": "submodules/TelegramUI/Components/Chat/ChatInputMessageAccessoryPanel/Sources/ChatInputMessageAccessoryPanel.swift",
    }
    expected = {
        "forward": "dfb136685d5bd60668fd14d0d5a3ff9b8c5bf46fe1be3b0355a15dac31bfb9ea",
        "node": "862b2de520ef01d702cffb8bad7a08b9806497fee6e6d289350f2dd7fd3a65b8",
        "options": "b0400faa09472f7d5d3f661a056f7ea0e48017397abe45775494cb85a77d5015",
        "load": "fe3bdae315a1d1af2c744ef280aae3e70ce5296a59f6086aaa2c660fa306cb0b",
        "accessory": "3e1894a59faebb4a91ca4bb2444197a695410fb0bd026742ebbfd7a7c3463d16",
        "component": "addad9a8e8eaf32921d3350b1d3b486326e6436874345ee523ec7400fc69d70d",
    }
    values = {}
    for key, relative in paths.items():
        raw = (source / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected[key]:
            raise SystemExit(f"Archived copy input drift: {relative}")
        values[key] = raw.decode("utf-8")
    target = source / "submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift"
    if target.exists():
        raise SystemExit("Archived media copy helper already exists")
    helper = (overlay / "Sources/TelegramCore/NagramiXArchivedMediaCopy.swift").read_bytes()

    def change(key: str, old: str, new: str) -> None:
        if values[key].count(old) != 1:
            raise SystemExit(f"Archived copy anchor drift: {key}: {old[:80]!r}")
        values[key] = values[key].replace(old, new, 1)

    change("forward", "import Foundation\n", "import Foundation\nimport Postbox\nimport NagramiXCore\n")
    change("forward",
        "private func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage]) -> [EnqueueMessage]? {",
        "func nagramiXCopyMessagesAsNew(_ messages: [EngineRawMessage], mediaBox: MediaBox? = nil, hideCaptions: Bool = false) -> [EnqueueMessage]? {")
    change("forward",
        "    var result: [EnqueueMessage] = []\n    var copiedGroupingKeys:",
        "    let archivedMediaCopy = mediaBox.map { NagramiXArchivedMediaCopy(mediaBox: $0) }\n    var result: [EnqueueMessage] = []\n    var copiedGroupingKeys:")
    change("forward",
        """                    mediaReference = .standalone(media: media)
""",
        """                    if let archivedMediaCopy {
                        guard let copiedMedia = archivedMediaCopy.prepare(media) else {
                            return nil
                        }
                        mediaReference = .standalone(media: copiedMedia)
                    } else {
                        // Capability checks do not stage files or mutate the archive.
                        mediaReference = .standalone(media: media)
                    }
""")
    change("forward",
        "        result.append(.message(text: message.text, attributes: attributes,",
        """        let hidesCaption = hideCaptions && mediaReference != nil
        if hidesCaption {
            attributes.removeAll(where: { $0 is TextEntitiesMessageAttribute })
            inlineStickers = [:]
        }
        result.append(.message(text: hidesCaption ? "" : message.text, attributes: attributes,""")
    change("forward",
        """    return result
}

extension ChatControllerImpl {""",
        """    archivedMediaCopy?.commit()
    return result
}

func nagramiXArchivedCopyAlert(context: AccountContext) -> ViewController {
    let strings = context.sharedContext.currentPresentationData.with { $0 }.strings
    return textAlertController(context: context, title: nil, text: strings.nagramiXArchivedCopyUnavailable, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})])
}

extension ChatControllerImpl {""")
    change("forward", "hasFilters: transferMode != .copyToSingleRecipient,", "hasFilters: true,")
    change("forward",
        "multipleSelectionLimit: transferMode == .copyToSingleRecipient ? 1 : nil, forwardedMessageIds: transferMode.copiesAsNew ? [] : messages.map { $0.id }",
        "multipleSelectionLimit: nil, forwardedMessageIds: transferMode == .copyAsNew ? [] : messages.map { $0.id }")
    change("forward",
        """                if transferMode.copiesAsNew {
                    if let threadId {""",
        """                if transferMode == .copyAsNew {
                    if let threadId {""")
    change("forward",
        "guard let copiedMessages = nagramiXCopyMessagesAsNew(messages) else {\n                                return",
        """guard let copiedMessages = nagramiXCopyMessagesAsNew(messages, mediaBox: strongSelf.context.account.postbox.mediaBox, hideCaptions: forwardOptions?.hideCaptions == true) else {
                                strongSelf.present(nagramiXArchivedCopyAlert(context: strongSelf.context), in: .window(.root))
                                return""")
    # Both anonymous modes now share stock single-recipient preparation.
    for old, new in [
        ("(transferMode != .forwardWithoutSource || threadId == nil)", "(!transferMode.singleRecipient || strongSelf.chatLocation.threadId == threadId)"),
        ("peerId == strongSelf.context.account.peerId && transferMode != .forwardWithoutSource", "peerId == strongSelf.context.account.peerId && !transferMode.singleRecipient"),
        ("(transferMode != .forwardWithoutSource || maybeChat.chatLocation.threadId == threadId)", "(!transferMode.singleRecipient || maybeChat.chatLocation.threadId == threadId)"),
        ("if transferMode == .forwardWithoutSource {", "if transferMode.singleRecipient {"),
    ]:
        change("forward", old, new)
    # Two destination-state writers, plus the immediate enqueue options.
    old = "hideNames: transferMode == .forwardWithoutSource ||"
    if values["forward"].count(old) != 3:
        raise SystemExit("Archived copy forward-option writer count drift")
    values["forward"] = values["forward"].replace(old, "hideNames: transferMode.singleRecipient ||")

    change("load",
        "                    strongSelf.forwardMessages(messageIds: forwardMessageIds, options: strongSelf.presentationInterfaceState.interfaceState.forwardOptionsState, resetCurrent: true)",
        """                    let hasArchivedDraft = forwardMessageIds.contains { strongSelf.context.account.nagramiXMessageArchive.deletedMessage(id: $0) != nil }
                    strongSelf.forwardMessages(messageIds: forwardMessageIds, options: strongSelf.presentationInterfaceState.interfaceState.forwardOptionsState, resetCurrent: true, transferMode: hasArchivedDraft ? .copyToSingleRecipient : .forwardWithSource)""")

    change("node",
        """                |> map { messages, accountPeer, options -> ([Message], Int32, Bool) in
                    var messages = messages
""",
        """                |> map { messages, accountPeer, options -> ([Message], Int32, Bool) in
                    let messagesById = Dictionary(uniqueKeysWithValues: messages.map { ($0.id, $0) })
                    var messages = messageIds.compactMap { messagesById[$0] ?? context.account.nagramiXMessageArchive.deletedMessage(id: $0) }
""")
    change("node",
        """                        var hideNames = options.hideNames
                        if message.id.peerId == accountPeer.id""",
        """                        var hideNames = options.hideNames || message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })
                        if message.id.peerId == accountPeer.id""")
    change("node",
        """                        attributes = attributes.filter({ attribute in
                            if attribute is EditedMessageAttribute {""",
        """                        attributes = attributes.filter({ attribute in
                            if attribute is NagramiXArchivedMessageAttribute {
                                return false
                            }
                            if attribute is EditedMessageAttribute {""")
    change("node",
        """                    for id in forwardMessageIds.sorted() {
                        messages.append(.forward(source: id, threadId: replyThreadId, grouping: .auto, attributes: attributes, correlationId: nil))
                    }
""",
        """                    let archivedMessages = forwardMessageIds.sorted().compactMap { self.context.account.nagramiXMessageArchive.deletedMessage(id: $0) }
                    var archivedCopies: [MessageId: EnqueueMessage] = [:]
                    if !archivedMessages.isEmpty {
                        guard let copies = nagramiXCopyMessagesAsNew(archivedMessages, mediaBox: self.context.account.postbox.mediaBox, hideCaptions: self.chatPresentationInterfaceState.interfaceState.forwardOptionsState?.hideCaptions == true) else {
                            self.interfaceInteraction?.presentController(nagramiXArchivedCopyAlert(context: self.context), nil)
                            return
                        }
                        archivedCopies = Dictionary(uniqueKeysWithValues: zip(archivedMessages.map { $0.id }, copies))
                    }
                    for id in forwardMessageIds.sorted() {
                        if let copy = archivedCopies[id] {
                            // The retained snapshot is a new outgoing message, never
                            // a server forward of a deleted source ID.
                            messages.append(copy.withUpdatedThreadId(replyThreadId))
                        } else {
                            messages.append(.forward(source: id, threadId: replyThreadId, grouping: .auto, attributes: attributes, correlationId: nil))
                        }
                    }
""")
    change("options",
        "        var items: [ContextMenuItem] = []\n        \n        var hasCaptions = false",
        "        let messagesById = Dictionary(uniqueKeysWithValues: messages.map { ($0.id, $0) })\n"
        "        let messages = messageIds.compactMap { messagesById[$0] ?? selfController.context.account.nagramiXMessageArchive.deletedMessage(id: $0) }\n"
        "        var items: [ContextMenuItem] = []\n        \n        var hasCaptions = false")
    change("options",
        "        var canHideNames = hasNotOwnMessages && hasOther",
        "        var canHideNames = hasNotOwnMessages && hasOther && !messages.contains(where: { $0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) })")

    change("component",
        "                        self.messages = messages.compactMap { $0 }\n",
        """                        if case .forward = component.contents {
                            self.messages = zip(messageIds, messages).compactMap { id, message -> EngineMessage? in
                                return message ?? component.context.account.nagramiXMessageArchive.deletedMessage(id: id).map { EngineMessage($0) }
                            }
                        } else {
                            self.messages = messages.compactMap { $0 }
                        }
""")
    change("accessory",
        """                        guard let message = await context.engine.data.get(
                            TelegramEngine.EngineData.Item.Messages.Message(id: messageId)
                        ).get() else {
                            return
                        }
""",
        """                        let currentMessage = await context.engine.data.get(
                            TelegramEngine.EngineData.Item.Messages.Message(id: messageId)
                        ).get()
                        guard let message = currentMessage ?? context.account.nagramiXMessageArchive.deletedMessage(id: messageId).map({ EngineMessage($0) }) else {
                            interfaceInteraction?.dismissForwardMessages()
                            return
                        }
""")
    # All exact hashes and anchors are checked before the first mutation.
    for key, relative in paths.items():
        (source / relative).write_text(values[key], encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(helper)

def apply_proxy_settings_sync_fix(source: Path) -> None:
    """Keep proxy switches synchronized and preserve saved manual choices."""
    path = source / "submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "92e295d3eafd75092bc29ce083175b81231d305853e59d689706afd2001542c4":
        raise SystemExit("Proxy preference synchronization input drift")
    text = raw.decode("utf-8")

    def change(old: str, new: str) -> None:
        nonlocal text
        if text.count(old) != 1:
            raise SystemExit(f"Proxy preference synchronization anchor drift: {old[:80]!r}")
        text = text.replace(old, new, 1)

    change("import NagramiXCore\n", "import NagramiXCore\nimport NagramiXMediaSettings\n")
    change(
        "    case .system: return strings.nagramiXDnsSystem\n",
        "    case .system: return strings.nagramiXDnsSystem\n    case .telegram: return strings.nagramiXDnsTelegram\n")
    change(
        "        let providers: [NagramiXDnsProvider] = [.system, .google, .quad9, .adGuard, .mullvad, .cloudflare, .customDoh]\n",
        "        let providers: [NagramiXDnsProvider] = [.system, .telegram, .google, .quad9, .adGuard, .mullvad, .cloudflare, .customDoh]\n")
    change(
        "    let toggleAvoidProxyWithVPN: (Bool) -> Void = { value in NagramiXTabSettings.update { $0.avoidProxyWithVPN = value } }\n",
        "    let toggleAvoidProxyWithVPN: (Bool) -> Void\n")
    change(
        "toggleAutoSwitch: @escaping (Bool) -> Void, selectAutoSwitchTimeout:",
        "toggleAutoSwitch: @escaping (Bool) -> Void, toggleAvoidProxyWithVPN: @escaping (Bool) -> Void, selectAutoSwitchTimeout:")
    change(
        "        self.toggleAutoSwitch = toggleAutoSwitch\n",
        "        self.toggleAutoSwitch = toggleAutoSwitch\n        self.toggleAvoidProxyWithVPN = toggleAvoidProxyWithVPN\n")
    change(
        "    var selectDnsImpl: (() -> Void)?\n",
        """    // Observe external changes only while the controller's state is
    // subscribed. An unpresented controller never installs an observer.
    let nagramiXSettingsSignal = Signal<NagramiXTabSettings, NoError> { subscriber in
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main, using: { _ in
            nagramiXSettingsPromise.set(NagramiXTabSettings.current)
        })
        let disposable = nagramiXSettingsPromise.get().start(next: { value in
            subscriber.putNext(value)
        })
        nagramiXSettingsPromise.set(NagramiXTabSettings.current)
        return ActionDisposable {
            disposable.dispose()
            NotificationCenter.default.removeObserver(observer)
        }
    }
    var selectDnsImpl: (() -> Void)?
""")
    change(
        """        if value {
            updateNagramiXSettings { $0.proxyAutoSwitchEnabled = true }
        }
        let _ = updateProxySettingsInteractively""",
        "        let _ = updateProxySettingsInteractively")
    change(
        """            if value && current.activeServer == nil {
                current.activeServer = current.servers.first
            }
            return current
""",
        """            if value && current.activeServer == nil {
                current.activeServer = current.servers.first
            }
            NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled: current.enabled && current.activeServer != nil, serverCount: Set(current.servers).count)
            return current
""")
    change(
        """    }, toggleAutoSwitch: { value in
        updateNagramiXSettings { $0.proxyAutoSwitchEnabled = value }
    }, selectAutoSwitchTimeout:""",
        """    }, toggleAutoSwitch: { value in
        // Persist even an explicit false matching the absent default.
        NagramiXProxyPreferences.setAutoSwitch(value)
        updateNagramiXSettings { $0.proxyAutoSwitchEnabled = value }
    }, toggleAvoidProxyWithVPN: { value in
        NagramiXProxyPreferences.setAvoidVPN(value)
        updateNagramiXSettings { $0.avoidProxyWithVPN = value }
    }, selectAutoSwitchTimeout:""")
    change(
        "            updateNagramiXSettings { $0.proxyAutoSwitchEnabled = true }\n",
        "")
    change(
        """                    current.activeServer = server
                    current.enabled = true
                }
                return current
""",
        """                    current.activeServer = server
                    current.enabled = true
                    NagramiXProxyPreferences.initializeIfNeeded(proxyEnabled: true, serverCount: Set(current.servers).count)
                }
                return current
""")
    change(
        "network.connectionStatus, nagramiXSettingsPromise.get(), NagramiXProxyVPNPolicy.bypassedSignal()",
        "network.connectionStatus, nagramiXSettingsSignal, NagramiXProxyVPNPolicy.bypassedSignal()")
    path.write_text(text, encoding="utf-8")

def apply_nagramix_onboarding(source: Path, overlay: Path) -> None:
    """Brand only the welcome artwork/copy; preserve native authorization."""
    intro = "submodules/RMIntro/Sources/platform/ios/RMIntroViewController.m"
    header = "submodules/RMIntro/PublicHeaders/RMIntro/RMIntroViewController.h"
    phone = "submodules/AuthorizationUI/Sources/AuthorizationSequencePhoneEntryControllerNode.swift"
    build = "Telegram/BUILD"
    expected = {
        intro: "08fe2f3b8c9eb6caefc17b52b820828fc758706ef72b2f5087e7af5830be9c21",
        header: "1bf4b89a18e8a2db1688c5e7fc4e1652dd030eb35ea5507b74ce0f8cfd30f2c9",
        phone: "24ecdf7b0ed17e157c18d5f27ad269d9f65fb9b6646b04703fcc38dbbeafd944",
        build: "ccaa94f6a450c4943090b863de69101cd682257271507072f2b71276ded2e852",
    }
    texts = {}
    for name, digest in expected.items():
        raw = (source / name).read_bytes()
        guarded = raw
        if name == build:
            # apply_overlay changes exactly these two branding fragments before
            # apply_features; allow both the fixture and the real CI entrypoint.
            guarded = guarded.replace(b"<key>CFBundleDisplayName</key>\n    <string>NagramiX</string>", b"<key>CFBundleDisplayName</key>\n    <string>Telegram</string>")
            guarded = guarded.replace(b"<key>CFBundleAllowMixedLocalizations</key>\n    <true/>\n    <key>CFBundleDevelopmentRegion</key>\n    <string>ru</string>", b"<key>CFBundleAllowMixedLocalizations</key>\n    <true/>\n    <key>CFBundleDevelopmentRegion</key>\n    <string>en</string>")
        if hashlib.sha256(guarded).hexdigest() != digest:
            raise SystemExit(f"NagramiX onboarding input drift: {name}")
        texts[name] = raw.decode("utf-8")

    def patch(name: str, old: str, new: str) -> None:
        if texts[name].count(old) != 1:
            raise SystemExit(f"NagramiX onboarding anchor drift: {name}: {old[:80]!r}")
        texts[name] = texts[name].replace(old, new, 1)

    def block(name: str, start: str, end: str, new: str) -> None:
        if texts[name].count(start) != 1 or texts[name].count(end) != 1:
            raise SystemExit(f"NagramiX onboarding range drift: {name}: {start!r}")
        begin = texts[name].index(start)
        finish = texts[name].index(end, begin)
        patch(name, texts[name][begin:finish], new)

    patch(header, "@interface RMIntroViewController : UIViewController<UIScrollViewDelegate, GLKViewDelegate>", "FOUNDATION_EXPORT UIImage *NagramiXOnboardingImage(NSInteger index);\n\n@interface RMIntroViewController : UIViewController<UIScrollViewDelegate, GLKViewDelegate>")
    patch(intro, '#include "animations.h"\n#include "objects.h"\n#include "texture_helper.h"\n', "")
    patch(intro, "    UIView *_startButton;\n", "    UIView *_startButton;\n    UIView *_nagramiXArtworkView;\n    NSArray<UIImageView *> *_nagramiXArtworkImages;\n")
    block(intro, "- (void)startTimer\n", "- (void)stopTimer\n", "- (void)startTimer {\n    // Artwork follows the native scroll offset; no continuous render timer.\n}\n\n")
    block(intro, "- (void)loadGL\n", "- (void)loadView {", (overlay / "Sources/RMIntro/OnboardingViewMethods.m.inc").read_text(encoding="utf-8").rstrip("\n") + "\n\n")
    patch(intro, "- (void)animateIn {\n", "- (void)animateIn {\n    if (UIAccessibilityIsReduceMotionEnabled()) {\n        return;\n    }\n")
    patch(intro, """    UIImage *image = _glkView.snapshot;
    UIImageView *imageView = [[UIImageView alloc] initWithFrame:_glkView.frame];
    imageView.image = image;
    return imageView;
""", """    UIView *snapshot = [_nagramiXArtworkView snapshotViewAfterScreenUpdates:YES];
    if (snapshot == nil) {
        snapshot = [[UIView alloc] initWithFrame:_nagramiXArtworkView.frame];
    }
    snapshot.frame = _nagramiXArtworkView.frame;
    return snapshot;
""")
    block(intro, "- (void)updateAndRender\n", "- (void)dealloc\n", "")
    block(intro, "- (void)setupGL\n", "static CGFloat x;", """// Preserve GLKViewDelegate conformance for the existing public header.
- (void)glkView:(GLKView *)__unused view drawInRect:(CGRect)__unused rect {
}

""")
    block(intro, "static CGFloat x;", "- (void)alternativeLanguageButtonPressed {", """- (void)scrollViewDidScroll:(UIScrollView *)scrollView {
    CGFloat width = scrollView.bounds.size.width;
    if (width <= 0.0) {
        return;
    }
    CGFloat progress = MAX(0.0, MIN(5.0, scrollView.contentOffset.x / width));
    _currentPage = (NSInteger)floor(progress + 0.5);
    [_pageControl setCurrentPage:_currentPage];
    [self nagramiXUpdateArtwork];
}

""")
    # Preserve the native entrance and layout with the replacement UIView.
    begin = texts[intro].index("- (void)animateIn {\n")
    finish = texts[intro].index("- (void)loadGL {", begin)
    animation = texts[intro][begin:finish]
    patch(intro, animation, animation.replace("_glkView", "_nagramiXArtworkView"))
    patch(intro, "    _glkView.frame = CGRectChangedOriginY(_glkView.frame, glViewY - statusBarHeight);\n", "    _nagramiXArtworkView.frame = CGRectChangedOriginY(_nagramiXArtworkView.frame, glViewY - statusBarHeight);\n")
    if any(value in texts[intro] for value in ["_glkView", "setup_texture(", "on_draw_frame("]):
        raise SystemExit("Unexpected legacy onboarding render path")

    patch(phone, "import UIKit\n", "import UIKit\nimport RMIntro\n")
    patch(phone, "    private let animationNode: AnimatedStickerNode\n    private let managedAnimationNode: ManagedPhoneAnimationNode\n", "    private let animationNode: ASImageNode\n")
    patch(phone, """        self.animationNode = DefaultAnimatedStickerNodeImpl(lottieSettings: .noAccountFallback)
        self.animationNode.setup(source: AnimatedStickerNodeLocalFileSource(name: "IntroPhone"), width: 256, height: 256, playbackMode: .once, mode: .direct(cachePathPrefix: nil))

        self.managedAnimationNode = ManagedPhoneAnimationNode(lottieSettings: .noAccountFallback)
        self.managedAnimationNode.isHidden = true
""".replace("\n\n", "\n        \n"), """        self.animationNode = ASImageNode()
        self.animationNode.image = NagramiXOnboardingImage(6)
        self.animationNode.contentMode = .scaleAspectFit
        self.animationNode.displaysAsynchronously = false
        self.animationNode.displayWithoutProcessing = true
        self.animationNode.isAccessibilityElement = false
""")
    patch(phone, "        self.addSubnode(self.managedAnimationNode)\n", "")
    patch(phone, """        self.phoneAndCountryNode.keyPressed = { [weak self] num in
            if let strongSelf = self, !strongSelf.managedAnimationNode.isHidden {
                strongSelf.managedAnimationNode.animate(num: num)
            }
        }
""", "")
    patch(phone, """        self.animationNode.completed = { [weak self] _ in
            self?.animationNode.removeFromSupernode()
            self?.managedAnimationNode.isHidden = false
        }
""", "")
    patch(phone, "        self.animationNode.layer.animateScale(from: 0.3, to: 1.0, duration: 0.3)\n", "        if !UIAccessibility.isReduceMotionEnabled {\n            self.animationNode.layer.animateScale(from: 0.3, to: 1.0, duration: 0.3)\n        }\n")
    patch(phone, "            self.animationNode.visibility = true\n", "")
    patch(phone, "            self.managedAnimationNode.isHidden = true\n", "")
    patch(phone, "        self.animationNode.updateLayout(size: animationSize)\n", "")
    patch(phone, "        transition.updateFrame(node: self.managedAnimationNode, frame: self.animationNode.frame)\n", "")
    if "managedAnimationNode" in texts[phone] or 'name: "IntroPhone"' in texts[phone]:
        raise SystemExit("Unexpected legacy phone artwork path")

    # Presentation-only production layout; every replacement is validated
    # against the same pinned inputs before any native file is written.
    patch(header, "FOUNDATION_EXPORT UIImage *NagramiXOnboardingImage(NSInteger index);", "FOUNDATION_EXPORT UIImage *NagramiXOnboardingImage(NSInteger index);\nFOUNDATION_EXPORT UIImage *NagramiXOnboardingSymbol(NSInteger index);")
    patch(header, "FOUNDATION_EXPORT UIImage *NagramiXOnboardingSymbol(NSInteger index);", "FOUNDATION_EXPORT UIImage *NagramiXOnboardingSymbol(NSInteger index);\nFOUNDATION_EXPORT UIColor *NagramiXOnboardingBackground(UIColor *nativeColor);")
    patch(intro, "        _backgroundColor = backgroundColor;", "        _backgroundColor = NagramiXOnboardingBackground(backgroundColor);")
    patch(phone, "        self.backgroundColor = theme.list.plainBackgroundColor\n", "        self.backgroundColor = account != nil ? NagramiXOnboardingBackground(theme.list.plainBackgroundColor) : theme.list.plainBackgroundColor\n")
    patch(intro, "NSArray<UIImageView *> *_nagramiXArtworkImages;", "NSArray<UIView *> *_nagramiXArtworkImages;")
    patch(intro, "    bool _loadedView;\n}\n@end", "    bool _loadedView;\n}\n- (void)nagramiXLayoutArtwork;\n- (void)nagramiXUpdateArtwork;\n@end")
    block(intro, "- (void)updateLayout\n", "- (void)viewWillAppear:", (overlay / "Sources/RMIntro/OnboardingLayout.m.inc").read_text(encoding="utf-8") + "\n")
    patch(phone, "    private let animationNode: ASImageNode\n", "    private let animationNode: ASImageNode\n    private let nagramiXContentNode = ASScrollNode()\n    private var nagramiXHadKeyboard = false\n")
    patch(phone, "private final class PhoneAndCountryNode: ASDisplayNode {\n", "private final class PhoneAndCountryNode: ASDisplayNode {\n    private let nagramiXBranded: Bool\n")
    patch(phone, "    init(strings: PresentationStrings, theme: PresentationTheme) {\n        self.strings = strings", "    init(strings: PresentationStrings, theme: PresentationTheme, branded: Bool = false) {\n        self.nagramiXBranded = branded\n        self.strings = strings")
    patch(phone, "        self.phoneAndCountryNode = PhoneAndCountryNode(strings: strings, theme: theme)", "        self.phoneAndCountryNode = PhoneAndCountryNode(strings: strings, theme: theme, branded: account != nil)")
    patch(phone, "    override func layout() {\n        super.layout()\n", (overlay / "Sources/AuthorizationUI/OnboardingPhoneFields.swift.inc").read_text(encoding="utf-8") + "    override func layout() {\n        super.layout()\n        if self.nagramiXBranded {\n            self.nagramiXLayoutFields(self.bounds.size)\n            return\n        }\n")
    patch(phone, "        self.countryButton.titleNode.maximumNumberOfLines = 1\n", "        self.countryButton.titleNode.maximumNumberOfLines = branded ? 0 : 1\n")
    patch(phone, "        self.countryButton.setBackgroundImage(countryButtonHighlightedBackground, for: .highlighted)\n", "        self.countryButton.setBackgroundImage(countryButtonHighlightedBackground, for: .highlighted)\n        if branded {\n            self.countryButton.setBackgroundImage(nil, for: [])\n            self.countryButton.setBackgroundImage(nil, for: .highlighted)\n            self.countryButton.backgroundColor = theme.list.itemBlocksBackgroundColor\n            self.countryButton.cornerRadius = 14.0\n            self.countryButton.borderWidth = UIScreenPixel\n            self.countryButton.borderColor = theme.list.itemPlainSeparatorColor.cgColor\n            self.countryButton.contentEdgeInsets = UIEdgeInsets(top: 10.0, left: 16.0, bottom: 10.0, right: 40.0)\n        }\n")
    patch(phone, "        self.phoneBackground.isLayerBacked = true\n", "        self.phoneBackground.isLayerBacked = true\n        if branded {\n            self.phoneBackground.image = nil\n            self.phoneBackground.backgroundColor = theme.list.itemBlocksBackgroundColor\n            self.phoneBackground.cornerRadius = 14.0\n            self.phoneBackground.borderWidth = UIScreenPixel\n            self.phoneBackground.borderColor = theme.list.itemPlainSeparatorColor.cgColor\n        }\n")
    patch(phone, "        self.addSubnode(self.animationNode)\n", "        self.addSubnode(self.animationNode)\n        if account != nil {\n            self.addSubnode(self.nagramiXContentNode)\n            let contentNodes: [ASDisplayNode] = [self.animationNode, self.titleNode, self.noticeNode, self.titleActivateAreaNode, self.noticeActivateAreaNode, self.phoneAndCountryNode, self.contactSyncNode]\n            for node in contentNodes {\n                self.nagramiXContentNode.addSubnode(node)\n            }\n        }\n")
    layout_anchor = "    func containerLayoutUpdated(_ layout: ContainerViewLayout, navigationBarHeight: CGFloat, transition: ContainedViewLayoutTransition) {\n"
    patch(phone, layout_anchor, (overlay / "Sources/AuthorizationUI/OnboardingPhoneLayout.swift.inc").read_text(encoding="utf-8") + layout_anchor + "        if self.account != nil {\n            self.nagramiXLayoutPhone(layout, navigationBarHeight: navigationBarHeight, transition: transition)\n            return\n        }\n")

    block(intro, "- (void)animateIn {\n", "- (void)loadGL {", """- (void)animateIn {
    if (UIAccessibilityIsReduceMotionEnabled()) {
        return;
    }
    _wrapperView.alpha = 0.0;
    _startButton.alpha = 0.0;
    [UIView animateWithDuration:0.25 animations:^{
        self->_wrapperView.alpha = 1.0;
        self->_startButton.alpha = self->_isEnabled ? 1.0 : 0.6;
    }];
}

""")
    patch(intro, "    snapshot.frame = _nagramiXArtworkView.frame;\n", "    snapshot.frame = [_nagramiXArtworkView convertRect:_nagramiXArtworkView.bounds toView:self.view];\n")
    patch(intro, """    UIView *snapshotView = [_wrapperView snapshotViewAfterScreenUpdates:false];
    snapshotView.frame = _wrapperView.frame;
    return snapshotView;
""", """    BOOL hidden = _nagramiXArtworkView.hidden;
    _nagramiXArtworkView.hidden = YES;
    UIView *snapshotView = [_wrapperView snapshotViewAfterScreenUpdates:YES];
    _nagramiXArtworkView.hidden = hidden;
    snapshotView.frame = _wrapperView.frame;
    return snapshotView;
""")

    manifest = json.loads((overlay / "Resources/Onboarding/manifest.json").read_text(encoding="utf-8"))
    if set(manifest) != {"NagramiXOnboardingLogo.png", "NagramiXOnboardingAtlas.png", "NagramiXOnboardingPhone.png"}:
        raise SystemExit("Unexpected onboarding asset manifest")
    destination = source / "Telegram/Telegram-iOS/Resources/NagramiXOnboarding"
    assets = {}
    for name, entry in manifest.items():
        path = overlay / entry["source"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit(f"Onboarding asset drift: {name}")
        if (destination / name).exists():
            raise SystemExit(f"Onboarding asset conflict: {name}")
        assets[name] = path
    artwork_path = source / "submodules/RMIntro/Sources/platform/ios/NagramiXOnboardingArtwork.m"
    if artwork_path.exists():
        raise SystemExit("Onboarding source conflict")
    # AppResources already supplies this directory through Lib.data. Adding
    # the same PNGs to ios_application.resources duplicates their bundle paths.
    resource_group = '    name = "AppResources",\n    srcs = glob([\n        "Telegram-iOS/Resources/**/*",\n    ], exclude = ["Telegram-iOS/Resources/**/.*"]),\n'
    if texts[build].count(resource_group) != 1 or texts[build].count('        ":AppResources",\n') != 1:
        raise SystemExit("Onboarding native resource ownership drift")
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")
    shutil.copy2(overlay / "Sources/RMIntro/NagramiXOnboardingArtwork.m", artwork_path)
    destination.mkdir(parents=True, exist_ok=True)
    for name, path in assets.items():
        shutil.copy2(path, destination / name)


def apply_archived_media_save(source: Path, overlay: Path) -> None:
    """Restore local export actions without reviving deleted cloud references."""
    menu = "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"
    sounds = "submodules/TelegramCore/Sources/TelegramEngine/Peers/NotificationSoundList.swift"
    expected = {
        menu: "d4b7e9ed1174c77750c7f3bb485cc60431c6d0a1e0b5bdf02ba6ce75e93cec83",
        sounds: "ea7d91461444f8b1e3b64783d29ae02c4a956b9845d138a393d02156419793b4",
    }
    texts = {}
    for name, digest in expected.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Archived media save input drift: {name}")
        texts[name] = raw.decode("utf-8")

    def patch(name: str, old: str, new: str) -> None:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Archived media save anchor drift: {name}: {old[:80]!r}")
        texts[name] = texts[name].replace(old, new, 1)

    patch(menu, """        if archivedAttribute != nil {
            actions.removeAll()
""", """        if archivedAttribute != nil {
            actions.removeAll()
            actions.append(contentsOf: nagramiXArchivedSaveMediaActions(context: context, message: message, isCopyProtected: isCopyProtected, notificationSoundList: notificationSoundList, controllerInteraction: controllerInteraction, strings: chatPresentationInterfaceState.strings))
""")
    # The existing importer keeps its native default. Only the new local-archive
    # upload supplies OGG explicitly; saved voices must not be labelled as MP3.
    patch(sounds,
          "func _internal_uploadNotificationSound(account: Account, title: String, data: Data) -> Signal<NotificationSoundList.NotificationSound, UploadNotificationSoundError> {",
          "func _internal_uploadNotificationSound(account: Account, title: String, data: Data, mimeType: String = \"audio/mpeg\") -> Signal<NotificationSoundList.NotificationSound, UploadNotificationSoundError> {")
    patch(sounds,
          "Api.functions.account.uploadRingtone(file: file, fileName: title, mimeType: \"audio/mpeg\")",
          "Api.functions.account.uploadRingtone(file: file, fileName: title, mimeType: mimeType)")
    helpers = {
        "submodules/TelegramCore/Sources/Utils/NagramiXArchivedSoundSave.swift": "Sources/TelegramCore/NagramiXArchivedSoundSave.swift",
        "submodules/TelegramUI/Sources/Chat/NagramiXArchivedMediaSave.swift": "Sources/TelegramUI/NagramiXArchivedMediaSave.swift",
    }
    for target, origin in helpers.items():
        if (source / target).exists() or not (overlay / origin).is_file():
            raise SystemExit(f"Archived media save helper conflict or missing source: {target}")
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")
    for target, origin in helpers.items():
        path = source / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / origin, path)


def apply_skip_call_rating(source: Path) -> None:
    """Gate automatic rating presentation; leave call state and manual rating native."""
    controller = "submodules/TelegramCallsUI/Sources/CallController.swift"
    node = "submodules/TelegramCallsUI/Sources/CallControllerNodeV2.swift"
    build = "submodules/TelegramCallsUI/BUILD"
    expected = {
        controller: "9c97d83352e6f93dcab4fc769951f54f568cd966b71efe7219f73c3fd10e6ba6",
        node: "a57a5b0b7297d1fefcdd35cbcc632724f262bf922a951d652637fd45521d013e",
        build: "b400ba1e1f8484513d69bc7a1203be34beab7a07d0a24947b41e49a7848f2830",
    }
    texts = {}
    for name, digest in expected.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Call rating preference input drift: {name}")
        texts[name] = raw.decode("utf-8")

    def patch(name: str, old: str, new: str) -> None:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Call rating preference anchor drift: {name}: {old[:80]!r}")
        texts[name] = texts[name].replace(old, new, 1)

    patch(controller, "import Foundation\n", "import Foundation\nimport NagramiXMediaSettings\n")
    patch(controller,
          "            if let strongSelf = self, !strongSelf.presentedCallRating {\n",
          "            if let strongSelf = self, !NagramiXCallSettings.skipRating, !strongSelf.presentedCallRating {\n")
    patch(controller,
          "                Queue.mainQueue().after(0.5, {\n                    let window = strongSelf.window\n",
          "                Queue.mainQueue().after(0.5, {\n                    guard !NagramiXCallSettings.skipRating else { return }\n                    let window = strongSelf.window\n")
    patch(node,
          """        if case let .terminated(_, _, reportRating) = callState.state {
            self.callEnded?(reportRating)
        }
""",
          """        if case let .terminated(callId, _, reportRating) = callState.state {
            self.callEnded?(reportRating)
            if reportRating, let callId {
                self.presentCallRating?(callId, self.call.isVideo)
            }
        }
""")
    patch(build,
          "        \"//submodules/TelegramUIPreferences:TelegramUIPreferences\",\n",
          "        \"//submodules/TelegramUIPreferences:TelegramUIPreferences\",\n        \"//submodules/NagramiXMediaSettings:NagramiXMediaSettings\",\n")
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_recorder_backpressure_fix(source: Path) -> None:
    """Не удерживать очередь рекордера бесконечным ожиданием writer input."""
    path = source / "submodules/Camera/CameraLegacy/Sources/VideoRecorder.swift"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "e0423c8b29486640fec45a21c02e61f0e321ce8f101ab429937a4da7f17def76":
        raise SystemExit("Изменился проверенный рекордер перед исправлением backpressure")
    text = raw.decode("utf-8")
    substitutions = [
        (
            """                    while (!videoInput.isReadyForMoreMediaData)
                    {
                        let maxDate = Date(timeIntervalSinceNow: 0.05)
                        RunLoop.current.run(until: maxDate)
                    }
""",
            """                    guard self.nagramiXWaitUntilReady(videoInput) else {
                        return
                    }
""",
        ),
        (
            """                        let _ = self._duration.modify { _ in return duration }
                    }
""",
            """                        let _ = self._duration.modify { _ in return duration }
                    } else {
                        self.transitionToFailedStatus(error: .generic)
                        return
                    }
""",
        ),
        (
            """            while (!audioInput.isReadyForMoreMediaData)
            {
                let maxDate = Date(timeIntervalSinceNow: 0.05)
                RunLoop.current.run(until: maxDate)
            }
""",
            """            guard self.nagramiXWaitUntilReady(audioInput) else {
                return false
            }
""",
        ),
        (
            """    private func transitionToFailedStatus(error: RecorderError) {
        let _ = self.error.modify({ _ in return error })
    }
""",
            """    private func nagramiXWaitUntilReady(_ input: AVAssetWriterInput) -> Bool {
        dispatchPrecondition(condition: .onQueue(self.queue))
        let deadline = CACurrentMediaTime() + 2.0
        while true {
            guard self.assetWriter.status == .writing, self.hasError() == nil else {
                self.transitionToFailedStatus(error: .generic)
                return false
            }
            if input.isReadyForMoreMediaData {
                return true
            }
            guard CACurrentMediaTime() < deadline else {
                Logger.shared.log("VideoRecorder", "writer input readiness timeout")
                self.transitionToFailedStatus(error: .generic)
                return false
            }
            RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.01))
        }
    }

    private func transitionToFailedStatus(error: RecorderError) {
        let _ = self.error.modify({ _ in return error })
        self.pendingAudioSampleBuffers.removeAll()
        if self.assetWriter.status == .writing {
            self.assetWriter.cancelWriting()
        }
    }
""",
        ),
    ]
    for old, new in substitutions:
        if text.count(old) != 1:
            raise SystemExit("Изменился точный якорь ожидания рекордера")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def apply_login_postbox_handoff(source: Path) -> None:
    """Promote the live login Postbox instead of opening its database a second time."""
    account = "submodules/TelegramCore/Sources/Account/Account.swift"
    context = "submodules/TelegramUI/Sources/SharedAccountContext.swift"
    expected = {
        account: "40237996ae8b1c3eac1b4537a7d7fdb4dbfc26cd0d20b873c69cbf87d993edba",
        context: "c6f74ebc29770a3d6a054d025cf0c48b086f693a6c75d4e237ba2f455bc41109",
    }
    texts = {}
    for name, digest in expected.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Login Postbox handoff input drift: {name}")
        texts[name] = raw.decode("utf-8")

    substitutions = [
        (account,
         "public func accountWithId(accountManager: AccountManager<TelegramAccountManagerTypes>, networkArguments: NetworkInitializationArguments, id: AccountRecordId, encryptionParameters: ValueBoxEncryptionParameters, supplementary: Bool, isSupportUser: Bool, rootPath: String, beginWithTestingEnvironment: Bool, backupData: AccountBackupData?, auxiliaryMethods: AccountAuxiliaryMethods, shouldKeepAutoConnection: Bool = true) -> Signal<AccountResult, NoError> {",
         "public func accountWithId(accountManager: AccountManager<TelegramAccountManagerTypes>, networkArguments: NetworkInitializationArguments, id: AccountRecordId, encryptionParameters: ValueBoxEncryptionParameters, supplementary: Bool, isSupportUser: Bool, rootPath: String, beginWithTestingEnvironment: Bool, backupData: AccountBackupData?, auxiliaryMethods: AccountAuxiliaryMethods, shouldKeepAutoConnection: Bool = true, existingUnauthorizedAccount: UnauthorizedAccount? = nil) -> Signal<AccountResult, NoError> {"),
        (account,
         """    let postbox = openPostbox(
        basePath: path + "/postbox",
        seedConfiguration: telegramPostboxSeedConfiguration,
        encryptionParameters: encryptionParameters,
        timestampForAbsoluteTimeBasedOperations: Int32(CFAbsoluteTimeGetCurrent() + NSTimeIntervalSince1970),
        isMainProcess: !supplementary,
        isTemporary: false,
        isReadOnly: false,
        useCopy: false,
        useCaches: !supplementary,
        removeDatabaseOnError: !supplementary
    )
""",
         """    let postbox: Signal<PostboxResult, NoError>
    if !supplementary, let existingUnauthorizedAccount,
       existingUnauthorizedAccount.id == id,
       existingUnauthorizedAccount.rootPath == rootPath,
       existingUnauthorizedAccount.basePath == path,
       existingUnauthorizedAccount.testingEnvironment == beginWithTestingEnvironment {
        // Authorization has already committed to this Postbox. Keep the same database
        // owner during promotion; opening another connection here races its lifecycle.
        // The native transaction below still reads and validates the account state.
        Logger.shared.log("Account", "Promoting the existing login Postbox")
        postbox = .single(.postbox(existingUnauthorizedAccount.postbox))
    } else {
        postbox = openPostbox(
            basePath: path + "/postbox",
            seedConfiguration: telegramPostboxSeedConfiguration,
            encryptionParameters: encryptionParameters,
            timestampForAbsoluteTimeBasedOperations: Int32(CFAbsoluteTimeGetCurrent() + NSTimeIntervalSince1970),
            isMainProcess: !supplementary,
            isTemporary: false,
            isReadOnly: false,
            useCopy: false,
            useCaches: !supplementary,
            removeDatabaseOnError: !supplementary
        )
    }
"""),
        (context,
         """                    addedSignals.append(accountWithId(accountManager: accountManager, networkArguments: networkArguments, id: id, encryptionParameters: encryptionParameters, supplementary: !applicationBindings.isMainApp, isSupportUser: attributes.isSupportUser, rootPath: rootPath, beginWithTestingEnvironment: attributes.isTestingEnvironment, backupData: attributes.backupData, auxiliaryMethods: makeTelegramAccountAuxiliaryMethods(uploadInBackground: appDelegate?.uploadInBackround))
""",
         """                    // Reuse only the login account that has just left the auth record.
                    // Other accounts, environments and extension processes open normally.
                    let existingUnauthorizedAccount: UnauthorizedAccount?
                    if applicationBindings.isMainApp, authRecord?.0 != id,
                       let currentAuth = self.activeAccountsValue?.currentAuth,
                       currentAuth.id == id {
                        existingUnauthorizedAccount = currentAuth
                    } else {
                        existingUnauthorizedAccount = nil
                    }
                    addedSignals.append(accountWithId(accountManager: accountManager, networkArguments: networkArguments, id: id, encryptionParameters: encryptionParameters, supplementary: !applicationBindings.isMainApp, isSupportUser: attributes.isSupportUser, rootPath: rootPath, beginWithTestingEnvironment: attributes.isTestingEnvironment, backupData: attributes.backupData, auxiliaryMethods: makeTelegramAccountAuxiliaryMethods(uploadInBackground: appDelegate?.uploadInBackround), existingUnauthorizedAccount: existingUnauthorizedAccount)
"""),
    ]
    for name, old, new in substitutions:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Login Postbox handoff anchor drift: {name}")
        texts[name] = texts[name].replace(old, new, 1)
    # Validate both complete inputs and every anchor before changing either file.
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_author_selection_archive_deletion(source: Path) -> None:
    """Separate local snapshots from native permission checks and cloud deletion."""
    load = "submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift"
    admin = "submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift"
    delete = "submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessagesInteractively.swift"
    history = "submodules/TelegramUI/Sources/ChatHistoryListNode.swift"
    expected = {
        load: "03c4bfb58ced48fc945606abd02eab2c93c770abeed4424b9d756b38a647a98c",
        admin: "78dac17422edb37141758646ed55005fba0ad1f43fe99ce9d2b4282a0eae7241",
        delete: "32f3e09a5b8f689d4f3a39339480531b24a265d913ec4916724f14057b1825a9",
        history: "f46f5d505e53048eb573206b4bccc4da409f9a5c33d8f312309ec13f541fa92d",
    }
    texts = {}
    for name, digest in expected.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Author selection deletion input drift: {name}")
        texts[name] = raw.decode("utf-8")

    def patch(name: str, old: str, new: str) -> None:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Author selection deletion anchor drift: {name}: {old[:80]!r}")
        texts[name] = texts[name].replace(old, new, 1)

    start = "        }, deleteSelectedMessages: { [weak self] sourceView in\n"
    end = "        }, reportSelectedMessages: { [weak self] in\n"
    if texts[load].count(start) != 1 or texts[load].count(end) != 1:
        raise SystemExit("Author selection deletion callback drift")
    begin = texts[load].index(start)
    finish = texts[load].index(end, begin)
    block = texts[load][begin:finish]

    def callback_patch(old: str, new: str) -> None:
        nonlocal block
        if block.count(old) != 1:
            raise SystemExit(f"Author selection deletion callback anchor drift: {old[:80]!r}")
        block = block.replace(old, new, 1)

    callback_patch(
        """                    if messageIds.allSatisfy({ strongSelf.context.account.nagramiXMessageArchive.deletedMessage(id: $0) != nil }) {
                        strongSelf.context.account.nagramiXMessageArchive.removeLocal(messageIds: Array(messageIds))
                        strongSelf.updateChatPresentationInterfaceState(animated: true, interactive: true, { $0.updatedInterfaceState { $0.withoutSelectionState() } })
                        return
                    }
""",
        """                    let archivedIds = Set(messageIds.filter { strongSelf.context.account.nagramiXMessageArchive.isLocallyDeletedMessage(id: $0) })
""")
    callback_patch(
        """                    strongSelf.messageContextDisposable.set((strongSelf.context.sharedContext.chatAvailableMessageActions(engine: strongSelf.context.engine, accountPeerId: strongSelf.context.account.peerId, messageIds: messageIds, keepUpdated: false)
                    |> deliverOnMainQueue).startStrict(next: { actions in
""",
        """                    strongSelf.messageContextDisposable.set((strongSelf.context.account.postbox.transaction { transaction -> Set<MessageId> in
                        // An expired media placeholder can still be a real server message.
                        // Only snapshots absent from Postbox are excluded from permissions.
                        return Set(messageIds.filter { !archivedIds.contains($0) || transaction.getMessage($0) != nil })
                    }
                    |> deliverOnMainQueue
                    |> mapToSignal { [weak self] liveIds -> Signal<ChatAvailableMessageActions, NoError> in
                        guard let strongSelf = self, strongSelf.presentationInterfaceState.interfaceState.selectionState?.selectedIds == messageIds else { return .complete() }
                        if liveIds.isEmpty {
                            strongSelf.presentDeleteMessageOptions(messageIds: messageIds, options: [.deleteLocally], contextController: nil, sourceView: sourceView, completion: { _ in })
                            return .complete()
                        }
                        return strongSelf.context.sharedContext.chatAvailableMessageActions(engine: strongSelf.context.engine, accountPeerId: strongSelf.context.account.peerId, messageIds: liveIds, keepUpdated: false)
                    }
                    |> deliverOnMainQueue).startStrict(next: { actions in
""")
    callback_patch("if let strongSelf = self, !actions.options.isEmpty {", """if let strongSelf = self {
                            guard strongSelf.presentationInterfaceState.interfaceState.selectionState?.selectedIds == messageIds else { return }""")
    callback_patch("if let banAuthor = actions.banAuthor {", "if archivedIds.isEmpty, let banAuthor = actions.banAuthor {")
    callback_patch("} else if !actions.banAuthors.isEmpty {", "} else if archivedIds.isEmpty, !actions.banAuthors.isEmpty {")
    callback_patch("if strongSelf.nagramiXSelectedAuthorMessageIds == messageIds {", "if strongSelf.nagramiXSelectedAuthorMessageIds == messageIds || !archivedIds.isEmpty {")
    callback_patch(
        """                                            TextAlertAction(type: .defaultAction, title: strongSelf.presentationData.strings.Common_OK, action: {}),
                                            TextAlertAction(type: .genericAction, title: strongSelf.presentationData.strings.ClearCache_FreeSpace, action: { [weak strongSelf] in
                                                strongSelf?.presentClearCacheSuggestion()
                                            })
""",
        """                                            TextAlertAction(type: .defaultAction, title: strongSelf.presentationData.strings.Common_OK, action: {})
""")
    texts[load] = texts[load][:begin] + block + texts[load][finish:]

    patch(admin, "import Foundation\n", "import Foundation\nimport NagramiXCore\n")
    patch(admin,
        """            var canDisplayContextMenu = true

            if options.contains(.cancelSending) {
""",
        """            var canDisplayContextMenu = true
            let archivedCount = messageIds.filter { self.context.account.nagramiXMessageArchive.isLocallyDeletedMessage(id: $0) }.count
            if archivedCount > 0 || self.nagramiXSelectedAuthorMessageIds == messageIds {
                // Use the native confirmation sheet and choices, with an exact scope.
                // Cancellation and local undo must not remove archive records early.
                canDisplayContextMenu = false
                var warning = self.presentationData.strings.nagramiXSelectedDeletionWarning(messageIds.count)
                if archivedCount > 0 {
                    warning += "\\n" + self.presentationData.strings.nagramiXLocalCopiesDeletionWarning(archivedCount)
                }
                items.append(ActionSheetTextItem(title: warning))
            }

            if options.contains(.cancelSending) {
""")
    patch(delete,
        """    var uniqueIds: [Int64: PeerId] = [:]
""",
        """    // Partition after native album expansion, before creating cloud/secret operations.
    // An archived ID is a local snapshot, not an available server message to revoke.
    if let archive = NagramiXMessageArchive.forPostbox(postbox) {
        let localIds = Set(messageIds.filter { archive.isLocallyDeletedMessage(id: $0.messageId) && transaction.getMessage($0.messageId) == nil }.map { $0.messageId })
        if !localIds.isEmpty {
            archive.removeLocal(messageIds: Array(localIds))
            _internal_deleteMessages(transaction: transaction, mediaBox: postbox.mediaBox, ids: Array(localIds))
            messageIds.removeAll { localIds.contains($0.messageId) }
        }
    }
    var uniqueIds: [Int64: PeerId] = [:]
""")
    patch(history,
        "                    pendingRemovedMessages: pendingRemovedMessages,\n",
        "                    pendingRemovedMessages: pendingRemovedMessages.union(update.4),\n")
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_dns_provider_list(source: Path) -> None:
    """Prune the final picker without weakening previous proxy-stage guards."""
    path = source / "submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "fd93383a35ec83929a5b9a59b55c0c0179384307f6e866e17290133c55dc25ec":
        raise SystemExit("DNS provider list input drift")
    text = raw.decode("utf-8")
    replacements = [
        ("    case .quad9: return strings.nagramiXDnsQuad9\n", ""),
        ("    case .mullvad: return strings.nagramiXDnsMullvad\n", ""),
        ("        let providers: [NagramiXDnsProvider] = [.system, .telegram, .google, .quad9, .adGuard, .mullvad, .cloudflare, .customDoh]\n",
         "        let providers = NagramiXDnsProvider.allCases\n"),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise SystemExit(f"DNS provider list anchor drift: {old!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def apply_selfie_countdown(source: Path) -> None:
    """Отсчёт только перед первой записью на селфи-камеру, до writer/live upload."""
    hashes = {'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift': 'f51f785c1c8662f7453657d63eb14531314f67d9201c35d7b955b6746bd53081'}
    substitutions = [('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '                    if controller.recordingStartTime == nil {\n'
      '                        controller.recordingStartTime = CACurrentMediaTime()\n'
      '                    }\n',
      '                    // Timestamp is set when the writer starts, after any countdown.\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        deinit {\n            self.resultDisposable.dispose()\n        }\n',
      '        deinit {\n'
      '            self.nagramiXCountdownTimer?.invalidate()\n'
      '            self.nagramiXCountdownPositionDisposable?.dispose()\n'
      '            if let observer = self.nagramiXCountdownBackgroundObserver {\n'
      '                NotificationCenter.default.removeObserver(observer)\n'
      '            }\n'
      '            self.resultDisposable.dispose()\n'
      '        }\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '            self.nagramiXRecordingGeneration &+= 1\n'
      '            let generation = self.nagramiXRecordingGeneration\n'
      '            let initialDuration',
      '            self.nagramiXRecordingGeneration &+= 1\n'
      '            let generation = self.nagramiXRecordingGeneration\n'
      '            let shouldCountdown = !self.nagramiXDidRequestInitialRecording && controller.cameraState.position == .front && '
      'NagramiXTabSettings.current.selfieCountdown\n'
      '            self.nagramiXDidRequestInitialRecording = true\n'
      '            if shouldCountdown {\n'
      '                self.nagramiXArmCountdown(controller: controller)\n'
      '            }\n'
      '            let initialDuration'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '            controller.node.withReadyCamera(isFirstTime: !controller.node.cameraIsActive) { [weak self] in\n'
      '                Queue.mainQueue().after(0.15) {\n',
      '            controller.node.withReadyCamera(isFirstTime: !controller.node.cameraIsActive) { [weak self] in\n'
      '                let start: () -> Void = { [weak self] in\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '                    self.resultDisposable.set((camera.startRecording()\n',
      '                    if shouldCountdown && UIApplication.shared.applicationState != .active { return }\n'
      '                    if controller.recordingStartTime == nil {\n'
      '                        controller.recordingStartTime = CACurrentMediaTime()\n'
      '                    }\n'
      '                    self.resultDisposable.set((camera.startRecording()\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '                    }))\n                }\n            }\n            \n            if initialDuration > 0.0 {',
      '                    }))\n'
      '                }\n'
      '                if shouldCountdown {\n'
      '                    self?.nagramiXBeginCountdown(generation: generation, start: start)\n'
      '                } else {\n'
      '                    Queue.mainQueue().after(0.15, start)\n'
      '                }\n'
      '            }\n'
      '            \n'
      '            if initialDuration > 0.0 {'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        private var nagramiXStoppingRecording = false\n',
      '__NAGRAMIX_SELFIE_COUNTDOWN_STATE__'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        func cancelVideoRecording() {\n            if let initialBrightness',
      '        func cancelVideoRecording() {\n'
      '            self.nagramiXRecordingGeneration &+= 1\n'
      '            self.nagramiXClearCountdown()\n'
      '            if let initialBrightness'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        private var progressView: RecordingProgressView\n',
      '        private var progressView: RecordingProgressView\n'
      '        fileprivate var nagramiXCountdownPending = false\n'
      '        private let nagramiXCountdownLabel = UILabel()\n'
      '\n'
      '        fileprivate func nagramiXUpdateCountdown(_ value: Int?) {\n'
      '            let changed = self.nagramiXCountdownLabel.text != value.map(String.init)\n'
      '            self.nagramiXCountdownLabel.text = value.map(String.init)\n'
      '            self.nagramiXCountdownLabel.isHidden = value == nil\n'
      '            if changed, value != nil {\n'
      '                self.nagramiXCountdownLabel.layer.removeAllAnimations()\n'
      '                if !UIAccessibility.isReduceMotionEnabled {\n'
      '                    self.nagramiXCountdownLabel.layer.animateScale(from: 1.12, to: 1.0, duration: 0.2)\n'
      '                }\n'
      '                UIAccessibility.post(notification: .announcement, argument: value.map(String.init))\n'
      '            }\n'
      '        }\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '            self.previewContainerContentView.addSubview(self.loadingView)\n',
      '            self.previewContainerContentView.addSubview(self.loadingView)\n'
      '            self.nagramiXCountdownLabel.font = Font.semibold(88.0)\n'
      '            self.nagramiXCountdownLabel.textColor = .white\n'
      '            self.nagramiXCountdownLabel.textAlignment = .center\n'
      '            self.nagramiXCountdownLabel.isUserInteractionEnabled = false\n'
      '            self.nagramiXCountdownLabel.isHidden = true\n'
      '            self.nagramiXCountdownLabel.layer.shadowColor = UIColor.black.cgColor\n'
      '            self.nagramiXCountdownLabel.layer.shadowOpacity = 0.2\n'
      '            self.nagramiXCountdownLabel.layer.shadowRadius = 3.0\n'
      '            self.nagramiXCountdownLabel.layer.shadowOffset = CGSize(width: 0.0, height: 1.0)\n'
      '            self.previewContainerContentView.addSubview(self.nagramiXCountdownLabel)\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '            self.previewBlurView.frame = previewBounds\n',
      '            self.nagramiXCountdownLabel.frame = previewBounds\n            self.previewBlurView.frame = previewBounds\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        var skipAction = false\n',
      '        if self.node.nagramiXCountdownPending {\n'
      '            self.node.cancelRecording.invoke(Void())\n'
      '            self.completion(nil, nil, nil, nil)\n'
      '            return\n'
      '        }\n'
      '        var skipAction = false\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        self.waitingForNextResult = true\n        self.node.transitioningToPreview = true\n',
      '        if self.node.nagramiXCountdownPending {\n'
      '            self.discardVideo()\n'
      '            self.completion(nil, nil, nil, nil)\n'
      '            return false\n'
      '        }\n'
      '        self.waitingForNextResult = true\n'
      '        self.node.transitioningToPreview = true\n'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '        self.isDismissed = true\n        self.node.camera?.stopCapture(invalidate: true)',
      '        self.isDismissed = true\n'
      '        self.node.cancelRecording.invoke(Void())\n'
      '        self.node.camera?.stopCapture(invalidate: true)'),
     ('submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
      '            guard !self.nagramiXStoppingRecording else { return }\n            self.nagramiXStoppingRecording = true',
      '            if controller.node.nagramiXCountdownPending {\n'
      '                self.cancelVideoRecording()\n'
      '                controller.completion(nil, nil, nil, nil)\n'
      '                return\n'
      '            }\n'
      '            guard !self.nagramiXStoppingRecording else { return }\n'
      '            self.nagramiXStoppingRecording = true')]
    methods = (Path(__file__).resolve().parent / "Sources/VideoMessageCameraScreen/NagramiXSelfieCountdown.swift.inc").read_text(encoding="utf-8").rstrip("\n") + "\n\n        private var nagramiXStoppingRecording = false\n"
    texts = {}
    for name, expected in hashes.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"Изменился вход таймера селфи-камеры: {name}")
        texts[name] = raw.decode("utf-8")
    for name, old, new in substitutions:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Изменился якорь таймера селфи-камеры: {name}")
        if new == "__NAGRAMIX_SELFIE_COUNTDOWN_STATE__":
            new = methods
        texts[name] = texts[name].replace(old, new, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


def apply_archived_selection_actions_fix(source: Path) -> None:
    """Полные архивные объекты для панели, экспорта и пересылки; один адресат один раз."""
    hashes = {'submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift': 'a3d6c137db9599a0c1f8fc4457ec25b39c7bb65623a78c8c9561d8e96630dd82',
 'submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift': 'afd475d35658af538b77bc7ca1da86c3bc3a2188f9429a18c4879e41045ffd72',
 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift': '7eecff949e8eec5731e3253d6283fbfecbd40697ec4a9e73dc644145e724ed2c',
 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift': 'e92b60aea1c36429841f57b79f2567402f0510e56999564a51f207b9b7d33d30',
 'submodules/TelegramUI/Sources/ChatControllerNode.swift': '6a24070bcafb53f03bea1694d93e55d544a058b6572bf3741ceb11435c05d9e7',
 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift': '1dd1b6b865cac3bdb1b34290f62198610393b1ea5dc20a361b64c8db2400c7fc'}
    substitutions = [('submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift',
      '    var foundPeerIds = Set<EnginePeer.Id>()\n',
      '    // «Избранное» уже представлено отдельной закреплённой строкой picker.\n'
      '    let foundPeers = foundPeers.filter { $0.0.id != savedMessagesPeer?.id }\n'
      '    var foundPeerIds = Set<EnginePeer.Id>()\n'),
     ('submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift',
      '                // Enforce the recipient contract before payments, scheduling or enqueue.\n',
      '                var recipientIds = Set<EnginePeer.Id>()\n'
      '                let peers = peers.filter { recipientIds.insert($0.id).inserted }\n'
      '                // Enforce the recipient contract before payments, scheduling or enqueue.\n'),
     ('submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift',
      '                let peerIds = peers.map { $0.id }',
      '                guard !peers.isEmpty else { return }\n                let peerIds = peers.map { $0.id }'),
     ('submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift',
      '                return (messages[id] ?? nil)?._asMessage() ?? '
      'self.context.account.nagramiXMessageArchive.deletedMessage(id: id)',
      '                return self.context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: (messages[id] '
      '?? nil)?._asMessage())'),
     ('submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift',
      '            let hasArchivedMessages = sortedMessages.contains',
      '            guard sortedMessages.count == Set(messageIds).count, !sortedMessages.isEmpty else {\n'
      '                self.present(nagramiXArchivedCopyAlert(context: self.context), in: .window(.root))\n'
      '                return\n'
      '            }\n'
      '            let hasArchivedMessages = sortedMessages.contains'),
     ('submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift',
      'hasArchivedMessages ? (transferMode.singleRecipient ? .copyToSingleRecipient : .copyAsNew) : transferMode',
      'hasArchivedMessages ? (transferMode == .copyAsNew ? .copyAsNew : .copyToSingleRecipient) : transferMode'),
     ('submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift',
      '    private var nagramiXCanCopySelection = false\n',
      '    private var nagramiXCanCopySelection = false\n    private var nagramiXSelectionGeneration: UInt64 = 0\n'),
     ('submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift',
      '    private func updateActions() {\n'
      '        self.forwardButton.isEnabled = self.selectedMessages.count != 0\n'
      '        self.nagramiXCanCopySelection = false\n'
      '        self.forwardWithoutSourceButton.isImplicitlyDisabled = true\n'
      '        self.broadcastButton.isImplicitlyDisabled = true\n'
      '        self.nagramiXTransferDisposable.set(nil)\n'
      '        \n'
      '        if self.selectedMessages.isEmpty {\n'
      '            self.actions = nil\n'
      '            if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, maxOverlayHeight, '
      'metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = self.validLayout, let interfaceState = '
      'self.presentationInterfaceState {\n'
      '                let _ = self.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, bottomInset: '
      'bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: maxOverlayHeight, '
      'isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, deviceMetrics: '
      'deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)\n'
      '            }\n'
      '            self.canDeleteMessagesDisposable.set(nil)\n'
      '        } else if let context = self.context {\n'
      '            let selectedIds = self.selectedMessages\n'
      '            self.canDeleteMessagesDisposable.set((context.sharedContext.chatAvailableMessageActions(engine: '
      'context.engine, accountPeerId: context.account.peerId, messageIds: selectedIds, keepUpdated: true)\n'
      '            |> deliverOnMainQueue\n'
      '            |> mapToSignal { [weak self] actions -> Signal<(ChatAvailableMessageActions, Bool), NoError> in\n'
      '                guard let self else { return .single((actions, false)) }\n'
      '                return self.nagramiXSelectedMessagesSignal(context: context, ids: selectedIds)\n'
      '                |> deliverOnMainQueue\n'
      '                |> map { [weak self] messages in\n'
      '                    let canCopy = messages.count == selectedIds.count && '
      'self?.interfaceInteraction?.canCopyMessagesWithoutSource?(messages) == true\n'
      '                    return (actions, canCopy)\n'
      '                }\n'
      '            }\n'
      '            |> deliverOnMainQueue).startStrict(next: { [weak self] result in\n'
      '                if let strongSelf = self, strongSelf.selectedMessages == selectedIds {\n'
      '                    let (actions, canCopy) = result\n'
      '                    strongSelf.actions = actions\n'
      '                    strongSelf.nagramiXCanCopySelection = canCopy\n'
      '                    if let (width, leftInset, rightInset, bottomInset, additionalSideInsets, maxHeight, '
      'maxOverlayHeight: maxOverlayHeight, metrics, isSecondary, isMediaInputExpanded, deviceMetrics) = strongSelf.validLayout, '
      'let interfaceState = strongSelf.presentationInterfaceState {\n'
      '                        let _ = strongSelf.updateLayout(width: width, leftInset: leftInset, rightInset: rightInset, '
      'bottomInset: bottomInset, additionalSideInsets: additionalSideInsets, maxHeight: maxHeight, maxOverlayHeight: '
      'maxOverlayHeight, isSecondary: isSecondary, transition: .immediate, interfaceState: interfaceState, metrics: metrics, '
      'deviceMetrics: deviceMetrics, isMediaInputExpanded: isMediaInputExpanded)\n'
      '                    }\n'
      '                }\n'
      '            }))\n'
      '        }\n'
      '    }\n'
      '    \n',
      '__NAGRAMIX_ARCHIVE_SELECTION_ACTIONS__'),
     ('submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift',
      '    private func nagramiXSelectedMessagesSignal(context: AccountContext, ids: Set<EngineMessage.Id>) -> '
      'Signal<[EngineRawMessage], NoError> {\n'
      '        let messageIds = ids.sorted()\n'
      '        return context.engine.data.get(EngineDataMap(\n'
      '            messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init)\n'
      '        ))\n'
      '        |> deliverOnMainQueue\n'
      '        |> map { messages in\n'
      '            return messageIds.compactMap { id -> EngineRawMessage? in\n'
      '                return (messages[id] ?? nil)?._asMessage() ?? context.account.nagramiXMessageArchive.deletedMessage(id: '
      'id)\n'
      '            }\n'
      '        }\n'
      '    }\n',
      '    private func nagramiXSelectedMessagesSignal(context: AccountContext, ids: Set<EngineMessage.Id>, keepUpdated: Bool = '
      'false) -> Signal<[EngineRawMessage], NoError> {\n'
      '        let messageIds = ids.sorted()\n'
      '        return combineLatest(\n'
      '            '
      'context.engine.data.subscribe(EngineDataMap(messageIds.map(TelegramEngine.EngineData.Item.Messages.Message.init))),\n'
      '            context.account.nagramiXMessageArchive.updates\n'
      '        )\n'
      '        |> take(keepUpdated ? Int.max : 1)\n'
      '        |> deliverOnMainQueue\n'
      '        |> map { messages, _ in\n'
      '            return messageIds.compactMap { id -> EngineRawMessage? in\n'
      '                return context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: (messages[id] ?? '
      'nil)?._asMessage())\n'
      '            }\n'
      '        }\n'
      '    }\n'),
     ('submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift',
      '        let selectedIds = self.selectedMessages\n        self.nagramiXTransferDisposable.set(',
      '        let selectedIds = self.selectedMessages\n'
      '        let generation = self.nagramiXSelectionGeneration\n'
      '        self.nagramiXTransferDisposable.set('),
     ('submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift',
      'guard let self, let button, self.selectedMessages == selectedIds,',
      'guard let self, let button, self.nagramiXSelectionGeneration == generation, self.selectedMessages == selectedIds,'),
     ('submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift',
      '        func getMessage(_ messageId: EngineMessage.Id) -> EngineRawMessage? {\n'
      '            if let maybeMessage = messageMap[messageId], let message = maybeMessage {\n'
      '                return message._asMessage()\n'
      '            } else if let message = messages[messageId] {\n'
      '                return message\n'
      '            } else {\n'
      '                return nil\n'
      '            }\n'
      '        }\n',
      '        func getMessage(_ messageId: EngineMessage.Id) -> EngineRawMessage? {\n'
      '            let live = (messageMap[messageId] ?? nil)?._asMessage()\n'
      '            if let retained = messages[messageId], retained.attributes.contains(where: { $0 is '
      'NagramiXArchivedMessageAttribute }) {\n'
      '                return NagramiXMessageArchive.interactionMessage(id: messageId, liveMessage: live, retainedMessage: '
      'retained)\n'
      '            }\n'
      '            return live ?? messages[messageId]\n'
      '        }\n'),
     ('submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift',
      '                |> map { messages -> [EngineMessage] in\n'
      '                    return messages.values.compactMap { $0 }\n'
      '                }\n'
      '                |> deliverOnMainQueue).startStandalone(next: { messages in\n'
      '                    if let strongSelf = self, !messages.isEmpty {',
      '                |> map { messages -> [EngineRawMessage] in\n'
      '                    return selectedIds.sorted().compactMap { id in\n'
      '                        return strongSelf.context.account.nagramiXMessageArchive.interactionMessage(id: id, liveMessage: '
      '(messages[id] ?? nil)?._asMessage())\n'
      '                    }\n'
      '                }\n'
      '                |> deliverOnMainQueue).startStandalone(next: { messages in\n'
      '                    if let strongSelf = self, messages.count == selectedIds.count,\n'
      '                       strongSelf.presentationInterfaceState.interfaceState.selectionState?.selectedIds == selectedIds '
      '{'),
     ('submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift',
      '}).map { $0._asMessage() }), externalShare: true, immediateExternalShare: true,',
      '})), externalShare: true, immediateExternalShare: true,'),
     ('submodules/TelegramUI/Sources/ChatControllerNode.swift',
      '                    var messages = messageIds.compactMap { messagesById[$0] ?? '
      'context.account.nagramiXMessageArchive.deletedMessage(id: $0) }',
      '                    var messages = messageIds.compactMap { context.account.nagramiXMessageArchive.interactionMessage(id: '
      '$0, liveMessage: messagesById[$0]) }')]
    overlay = Path(__file__).resolve().parent
    methods = (overlay / "Sources/ChatMessageSelectionInputPanelNode/NagramiXArchiveSelectionActions.swift.inc").read_text(encoding="utf-8").rstrip("\n") + "\n\n"
    texts = {}
    for name, expected in hashes.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"Изменился вход архивных действий/получателей: {name}")
        texts[name] = raw.decode("utf-8")
    copies = {"submodules/TelegramCore/Tests/NagramiXArchiveInteractionTests.swift": "Tests/TelegramCore/NagramiXArchiveInteractionTests.swift"}
    for target, original in copies.items():
        if (source / target).exists() or not (overlay / original).is_file():
            raise SystemExit(f"Изменился состав проверки архивного выделения: {target}")
    for name, old, new in substitutions:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Изменился якорь архивного выделения: {name}")
        if new == "__NAGRAMIX_ARCHIVE_SELECTION_ACTIONS__":
            new = methods
        texts[name] = texts[name].replace(old, new, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")
    for target, original in copies.items():
        (source / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / original, source / target)


def apply_anonymous_stickers_and_blocked_filter(source: Path) -> None:
    """Пак-независимые стикеры и локальное скрытие авторов из чёрного списка."""
    hashes = {
        'submodules/TelegramCore/Sources/Account/Account.swift': '1d952943706f87d70f97a79fba9d2fc6b3b0524a7f6c7d83de0743b332af1ffc',
        'submodules/TelegramCore/Sources/Account/AccountManager.swift': '0bff96b166e668834bc82f5001d83189913749633dad626f20dab13c154a1f7d',
        'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift': 'a0e914dde976f40d7177da7a2a8e5f4c6566d0e884cae6c258244cd5bceab2b8',
        'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift': '74d01ef7ea181c11fcf4e22b8b007eeb9b065333e7100f631b3b5d3e4b36cd2a',
        'submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift': 'b7e11a5c6649c3a2b0afde394d3a8766b1bdb382e4ec0fa85e6bf5bff5641bda',
        'submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeers.swift': '0d8591a16fb67b0bde461c8ce4854911f78d9d372221f1c15ed4baec042da920',
        'submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift': '40fa65c5ebd83df4486dddfe07e7ff5707c2cb61381eb22e1c34f1c7e0fe8492',
        'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift': '5efb0930531c04b74ad8245fe7fe82275db925a3cb25ad263ea63c8054c651bd',
        'submodules/TelegramUI/Sources/ChatHistoryListNode.swift': 'ce569c9e73172b80a5ad15fbe039c6cfdc2a9150572561a7d6b7cff165f80579',
    }
    substitutions = [('submodules/TelegramCore/Sources/Account/AccountManager.swift',
      '    declareEncodable(OutgoingMessageInfoAttribute.self, f: { OutgoingMessageInfoAttribute(decoder: $0) })\n',
      '    declareEncodable(NagramiXAnonymousStickerMessageAttribute.self, f: { NagramiXAnonymousStickerMessageAttribute(decoder: '
      '$0) })\n'
      '    declareEncodable(OutgoingMessageInfoAttribute.self, f: { OutgoingMessageInfoAttribute(decoder: $0) })\n'),
     ('submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift',
      'private func filterMessageAttributesForOutgoingMessage(_ attributes: [MessageAttribute]) -> [MessageAttribute] {\n'
      '    return attributes.filter { attribute in\n'
      '        switch attribute {\n'
      '        case _ as TextEntitiesMessageAttribute:\n'
      '            return true\n'
      '        case _ as RichTextMessageAttribute:',
      'private func filterMessageAttributesForOutgoingMessage(_ attributes: [MessageAttribute]) -> [MessageAttribute] {\n'
      '    return attributes.filter { attribute in\n'
      '        switch attribute {\n'
      '        case _ as NagramiXAnonymousStickerMessageAttribute:\n'
      '            return true\n'
      '        case _ as TextEntitiesMessageAttribute:\n'
      '            return true\n'
      '        case _ as RichTextMessageAttribute:'),
     ('submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift',
      '            let antiCapsEnabled =',
      '            let anonymousStickersEnabled = UserDefaults.standard.object(forKey: "nagramix.stickers.anonymous") as? Bool ?? '
      'true\n'
      '            let antiCapsEnabled ='),
     ('submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift',
      '                let message = nagramiXAntiCapsMessage(originalMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)\n',
      '                let anonymousMessage = nagramiXAnonymousStickerMessage(originalMessage, enabled: anonymousStickersEnabled)\n'
      '                let message = nagramiXAntiCapsMessage(anonymousMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)\n'),
     ('submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift',
      '    } else if let file = media as? TelegramMediaFile {\n'
      '        if let resource = file.resource as? CloudDocumentMediaResource {',
      '    } else if let file = media as? TelegramMediaFile {\n'
      '        if let anonymous = attributes.first(where: { $0 is NagramiXAnonymousStickerMessageAttribute }) as? '
      'NagramiXAnonymousStickerMessageAttribute, file.isSticker {\n'
      '            guard let source = anonymous.source else { return .fail(.generic) }\n'
      '            return uploadedMediaFileContent(network: network, postbox: postbox, auxiliaryMethods: auxiliaryMethods, '
      'transformOutgoingMessageMedia: nil, messageMediaPreuploadManager: messageMediaPreuploadManager, forceReupload: true, '
      'isGrouped: isGrouped, isPaid: false, passFetchProgress: passFetchProgress, forceNoBigParts: forceNoBigParts, peerId: peerId, '
      'messageId: messageId, text: text, attributes: attributes, autoremoveMessageAttribute: autoremoveMessageAttribute, '
      'autoclearMessageAttribute: autoclearMessageAttribute, file: file, anonymousStickerSource: source)\n'
      '        }\n'
      '        if let resource = file.resource as? CloudDocumentMediaResource {'),
     ('submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift',
      'private func uploadedMediaFileContent(network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, '
      'transformOutgoingMessageMedia: TransformOutgoingMessageMedia?, messageMediaPreuploadManager: MessageMediaPreuploadManager, '
      'forceReupload: Bool, isGrouped: Bool, isPaid: Bool, passFetchProgress: Bool, forceNoBigParts: Bool, peerId: PeerId, '
      'messageId: MessageId?, text: String, attributes: [MessageAttribute], autoremoveMessageAttribute: '
      'AutoremoveTimeoutMessageAttribute?, autoclearMessageAttribute: AutoclearTimeoutMessageAttribute?, file: TelegramMediaFile) -> '
      'Signal<PendingMessageUploadedContentResult, PendingMessageUploadError> {\n'
      '    return maybePredownloadedFileResource(postbox: postbox, auxiliaryMethods: auxiliaryMethods, peerId: peerId, resource: '
      'file.resource, autoRemove: autoremoveMessageAttribute != nil || autoclearMessageAttribute != nil, forceRefresh: '
      'forceReupload)',
      'private func uploadedMediaFileContent(network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, '
      'transformOutgoingMessageMedia: TransformOutgoingMessageMedia?, messageMediaPreuploadManager: MessageMediaPreuploadManager, '
      'forceReupload: Bool, isGrouped: Bool, isPaid: Bool, passFetchProgress: Bool, forceNoBigParts: Bool, peerId: PeerId, '
      'messageId: MessageId?, text: String, attributes: [MessageAttribute], autoremoveMessageAttribute: '
      'AutoremoveTimeoutMessageAttribute?, autoclearMessageAttribute: AutoclearTimeoutMessageAttribute?, file: TelegramMediaFile, '
      'anonymousStickerSource: TelegramMediaFile? = nil) -> Signal<PendingMessageUploadedContentResult, PendingMessageUploadError> '
      '{\n'
      '    let cached: Signal<PredownloadedResource, PendingMessageUploadError> = anonymousStickerSource == nil ? '
      'maybePredownloadedFileResource(postbox: postbox, auxiliaryMethods: auxiliaryMethods, peerId: peerId, resource: file.resource, '
      'autoRemove: autoremoveMessageAttribute != nil || autoclearMessageAttribute != nil, forceRefresh: forceReupload) : '
      '.single(.none)\n'
      '    return cached'),
     ('submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift',
      '        let fileReference: AnyMediaReference\n'
      '        if let partialReference = file.partialReference {\n'
      '            fileReference = partialReference.mediaReference(file)\n'
      '        } else {\n'
      '            fileReference = .standalone(media: file)\n'
      '        }\n'
      '        let upload: Signal<MultipartUploadResult?, PendingMessageUploadError> = .single(nil)\n'
      '        |> then(\n'
      '            messageMediaPreuploadManager.upload(network: network, postbox: postbox, source: '
      '.resource(fileReference.resourceReference(file.resource)), encrypt: peerId.namespace == Namespaces.Peer.SecretChat, tag: '
      'TelegramMediaResourceFetchTag(statsCategory: statsCategoryForFileWithAttributes(file.attributes), userContentType: nil), '
      'hintFileSize: hintSize, hintFileIsLarge: hintFileIsLarge, forceNoBigParts: forceNoBigParts)',
      '        let fileReference: AnyMediaReference\n'
      '        if let source = anonymousStickerSource {\n'
      '            if let partialReference = source.partialReference {\n'
      '                fileReference = partialReference.mediaReference(source)\n'
      '            } else {\n'
      '                fileReference = .standalone(media: source)\n'
      '            }\n'
      '        } else if let partialReference = file.partialReference {\n'
      '            fileReference = partialReference.mediaReference(file)\n'
      '        } else {\n'
      '            fileReference = .standalone(media: file)\n'
      '        }\n'
      '        let fileUpload: Signal<MultipartUploadResult, MultipartUploadError>\n'
      '        if anonymousStickerSource != nil {\n'
      '            fileUpload = multipartUpload(network: network, postbox: postbox, source: '
      '.resource(fileReference.resourceReference(file.resource)), encrypt: peerId.namespace == Namespaces.Peer.SecretChat, tag: '
      'TelegramMediaResourceFetchTag(statsCategory: statsCategoryForFileWithAttributes(file.attributes), userContentType: nil), '
      'hintFileSize: hintSize, hintFileIsLarge: hintFileIsLarge, forceNoBigParts: forceNoBigParts)\n'
      '        } else {\n'
      '            fileUpload = messageMediaPreuploadManager.upload(network: network, postbox: postbox, source: '
      '.resource(fileReference.resourceReference(file.resource)), encrypt: peerId.namespace == Namespaces.Peer.SecretChat, tag: '
      'TelegramMediaResourceFetchTag(statsCategory: statsCategoryForFileWithAttributes(file.attributes), userContentType: nil), '
      'hintFileSize: hintSize, hintFileIsLarge: hintFileIsLarge, forceNoBigParts: forceNoBigParts)\n'
      '        }\n'
      '        let upload: Signal<MultipartUploadResult?, PendingMessageUploadError> = .single(nil)\n'
      '        |> then(\n'
      '            fileUpload'),
     ('submodules/TelegramCore/Sources/Account/Account.swift',
      '    public let nagramiXMessageArchive: NagramiXMessageArchive\n',
      '    public let nagramiXMessageArchive: NagramiXMessageArchive\n'
      '    public let nagramiXBlockedMessageFilter: NagramiXBlockedMessageFilter\n'),
     ('submodules/TelegramCore/Sources/Account/Account.swift',
      '        self.nagramiXMessageArchive = NagramiXMessageArchive(postbox: postbox, accountPeerId: peerId, basePath: basePath)\n',
      '        self.nagramiXMessageArchive = NagramiXMessageArchive(postbox: postbox, accountPeerId: peerId, basePath: basePath)\n'
      '        self.nagramiXBlockedMessageFilter = NagramiXBlockedMessageFilter(postbox: postbox, network: network, peerId: peerId, '
      'basePath: basePath)\n'),
     ('submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeers.swift',
      '                                return previous.withUpdatedIsBlocked(isBlocked)',
      '                                account.nagramiXBlockedMessageFilter.setBlocked(peerId, isBlocked)\n'
      '                                return previous.withUpdatedIsBlocked(isBlocked)'),
     ('submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift',
      '        let currentPeers = self._state.peers\n',
      '        let currentPeers = self._state.peers\n        let nagramiXFilter = self.account.nagramiXBlockedMessageFilter\n'),
     ('submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift',
      '            |> mapToSignal { _ -> Signal<Never, BlockedPeersContextAddError> in\n'
      '                return .complete()\n'
      '            }\n',
      '            |> mapToSignal { _ -> Signal<Never, BlockedPeersContextAddError> in\n'
      '                if case .blocked = subject {\n'
      '                    let validIds = Set(peerIds)\n'
      '                    for peer in currentPeers where !validIds.contains(peer.peerId) { nagramiXFilter.setBlocked(peer.peerId, '
      'false) }\n'
      '                    for peerId in validIds { nagramiXFilter.setBlocked(peerId, true) }\n'
      '                }\n'
      '                return .complete()\n'
      '            }\n'),
     ('submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift',
      '            |> mapToSignal { _ -> Signal<Peer?, BlockedPeersContextAddError> in\n'
      '                return postbox.transaction { transaction -> Peer? in',
      '            |> mapToSignal { _ -> Signal<Peer?, BlockedPeersContextAddError> in\n'
      '                if case .blocked = subject { NagramiXBlockedMessageFilter.forPostbox(postbox)?.setBlocked(peerId, true) }\n'
      '                return postbox.transaction { transaction -> Peer? in'),
     ('submodules/TelegramCore/Sources/TelegramEngine/Privacy/BlockedPeersContext.swift',
      '            |> mapToSignal { value in\n                return postbox.transaction { transaction -> Peer? in',
      '            |> mapToSignal { value in\n'
      '                if case .blocked = subject { NagramiXBlockedMessageFilter.forPostbox(postbox)?.setBlocked(peerId, false) }\n'
      '                return postbox.transaction { transaction -> Peer? in'),
     ('submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift',
      '                updatedState.updateCachedPeerData(userPeerId, { current in\n                    let previous: CachedUserData',
      '                updatedState.updateCachedPeerData(userPeerId, { current in\n'
      '                    NagramiXBlockedMessageFilter.forPostbox(postbox)?.setBlocked(userPeerId, (updatePeerBlockedData.flags & '
      '(1 << 0)) != 0)\n'
      '                    let previous: CachedUserData'),
     ('submodules/TelegramUI/Sources/ChatHistoryListNode.swift',
      '        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates, '
      'context.account.nagramiXMessageArchive.deferredReactions.updates)\n'
      '        |> map { update, _, _ in',
      '        historyViewUpdate = combineLatest(historyViewUpdate, context.account.nagramiXMessageArchive.updates, '
      'context.account.nagramiXMessageArchive.deferredReactions.updates, context.account.nagramiXBlockedMessageFilter.updates)\n'
      '        |> map { update, _, _, _ in'),
     ('submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift',
      '    var count = 0\n    loop: for entry in sourceEntries {',
      '    let hideBlockedMessages = NagramiXBlockedMessageFilter.enabled\n'
      '    var count = 0\n'
      '    loop: for entry in sourceEntries {'),
     ('submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift',
      '        message = context.account.nagramiXMessageArchive.deferredReactions.displayMessage(message)\n        var isRead',
      '        message = context.account.nagramiXMessageArchive.deferredReactions.displayMessage(message)\n'
      '        if context.account.nagramiXBlockedMessageFilter.shouldHide(message, enabled: hideBlockedMessages) { continue loop }\n'
      '        var isRead'),
     ('submodules/TelegramUI/Sources/ChatHistoryListNode.swift',
      '                let lastHeaderId = filteredEntries.last.flatMap { listMessageDateHeaderId(timestamp: $0.index.timestamp) } ?? '
      '0\n',
      '                // Пропускаем целиком скрытое окно, чтобы не застрять перед более старой видимой историей.\n'
      '                if case .default = source, mode == .bubbles, NagramiXBlockedMessageFilter.enabled,\n'
      '                   view.earlierId != nil, !view.entries.isEmpty,\n'
      '                   view.entries.allSatisfy({ context.account.nagramiXBlockedMessageFilter.shouldHide($0.message, enabled: '
      'true) }),\n'
      '                   !filteredEntries.contains(where: { entry in\n'
      '                       switch entry { case .MessageEntry, .MessageGroupEntry: return true; default: return false }\n'
      '                   }), let firstEntry = view.entries.first {\n'
      '                    Queue.mainQueue().async { [weak self] in\n'
      '                        guard let self, self.chatHistoryLocationValue == update.2, NagramiXBlockedMessageFilter.enabled else '
      '{ return }\n'
      '                        let location: ChatHistoryLocation = .Navigation(index: .message(firstEntry.message.index), '
      'anchorIndex: .message(firstEntry.message.index), count: historyMessageCount, highlight: false)\n'
      '                        if self.chatHistoryLocationValue?.content != location {\n'
      '                            self.chatHistoryLocationValue = ChatHistoryLocationInput(content: location, id: '
      'self.takeNextHistoryLocationId())\n'
      '                        }\n'
      '                    }\n'
      '                }\n'
      '                let lastHeaderId = filteredEntries.last.flatMap { listMessageDateHeaderId(timestamp: $0.index.timestamp) } ?? '
      '0\n')]
    overlay = Path(__file__).resolve().parent
    texts = {}
    for name, expected in hashes.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"Изменился проверенный вход приватности: {name}")
        texts[name] = raw.decode("utf-8")
    copies = {
        "submodules/TelegramCore/Sources/NagramiXAnonymousStickers.swift": "Sources/TelegramCore/NagramiXAnonymousStickers.swift",
        "submodules/TelegramCore/Sources/NagramiXBlockedMessageFilter.swift": "Sources/TelegramCore/NagramiXBlockedMessageFilter.swift",
        "submodules/TelegramCore/Tests/NagramiXPrivateMessagesTests.swift": "Tests/TelegramCore/NagramiXPrivateMessagesTests.swift",
    }
    for target, original in copies.items():
        if (source / target).exists() or not (overlay / original).is_file():
            raise SystemExit(f"Изменился состав новых файлов приватности: {target}")
    for name, old, new in substitutions:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Изменился точный якорь приватности: {name}")
        texts[name] = texts[name].replace(old, new, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")
    for target, original in copies.items():
        (source / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / original, source / target)


def apply_anti_caps(source: Path) -> None:
    """Анти-капс для новых .message перед штатным enqueue."""
    path = source / "submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift"
    expected = "06b68a873785be5ff84d38e524e186313150d5d6cf8456b5f95efe38ffb6c33c"
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit("Изменился проверенный enqueue или анти-капс уже применён")
    substitutions = [('            var normalMessageIndices: [Int] = []\n'
      '\n'
      '            for i in 0 ..< messages.count {\n'
      '                let (transformedMedia, message) = messages[i]\n',
      '            var normalMessageIndices: [Int] = []\n'
      '            let antiCapsEnabled = UserDefaults.standard.object(forKey: "nagramix.messages.antiCaps") as? Bool ?? false\n'
      '            let antiCapsLimits = antiCapsEnabled ? UserLimitsConfiguration(appConfiguration: '
      'transaction.getPreferencesEntry(key: PreferencesKeys.appConfiguration)?.get(AppConfiguration.self) ?? .defaultValue, '
      'isPremium: (transaction.getPeer(account.peerId) as? TelegramUser)?.isPremium ?? false) : '
      'UserLimitsConfiguration.defaultValue\n'
      '\n'
      '            for i in 0 ..< messages.count {\n'
      '                let (transformedMedia, originalMessage) = messages[i]\n'
      '                let message = nagramiXAntiCapsMessage(originalMessage, enabled: antiCapsEnabled, limits: antiCapsLimits)\n')]
    overlay = Path(__file__).resolve().parent
    copies = {
        source / "submodules/TelegramCore/Sources/NagramiXAntiCaps.swift": overlay / "Sources/TelegramCore/NagramiXAntiCaps.swift",
        source / "submodules/TelegramCore/Tests/NagramiXAntiCapsTests.swift": overlay / "Tests/TelegramCore/NagramiXAntiCapsTests.swift",
    }
    text = path.read_text(encoding="utf-8")
    for target, original in copies.items():
        if target.exists() or not original.is_file():
            raise SystemExit(f"Изменился состав файлов анти-капса: {target.name}")
    for old, new in substitutions:
        if text.count(old) != 1:
            raise SystemExit("Изменился точный якорь анти-капса")
        text = text.replace(old, new, 1)
    for target, original in copies.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    path.write_text(text, encoding="utf-8")


def apply_mixed_recording_transition(source: Path) -> None:
    """Reduce graph/routing churn on mixed voice/round recording, without prewarming a mic."""
    session = "submodules/TelegramAudio/Sources/ManagedAudioSession.swift"
    recorder = "submodules/TelegramUI/Sources/ManagedAudioRecorder.swift"
    camera = "submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift"
    hashes = {
        session: "29c6f4c05cb8accffea8810400e1aee2a74bde8b78e5339898c8c8bda565f55b",
        recorder: "47dd9b4fa58c7371a27f33990d6b20f2345aa888c7cf697b2102da1931df75ad",
        camera: "8adc05fdd3597eecf0daa5f9a5d2dd63b2ea9ed9e66f2a1b3489de31f7a7d78c",
    }
    texts = {}
    for name, digest in hashes.items():
        raw = (source / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SystemExit(f"Mixed recording transition input drift: {name}")
        texts[name] = raw.decode("utf-8")

    substitutions = [
        (session,
         "    private var isActiveValue: Bool = false\n",
         "    private var isActiveValue: Bool = false\n    private var nagramiXMixedReleaseGeneration: UInt64 = 0\n    private var nagramiXMixedReleasePending = false\n"),
        (session,
         """                    let keepStereoOutput = mixWithOthers
                        && session.currentRoute.outputs.contains(where: { $0.portType == .bluetoothA2DP })
                        && session.preferredInput?.portType != .bluetoothHFP
""",
         """                    let hasSelectedHFP = session.preferredInput?.portType == .bluetoothHFP
                        || session.currentRoute.inputs.contains(where: { $0.portType == .bluetoothHFP })
                        || session.currentRoute.outputs.contains(where: { $0.portType == .bluetoothHFP })
                    let keepStereoOutput = mixWithOthers && (video
                        ? session.currentRoute.outputs.contains(where: { $0.portType == .bluetoothA2DP }) && session.preferredInput?.portType != .bluetoothHFP
                        : !hasSelectedHFP)
                    // An inactive app session may not yet report the other app's A2DP
                    // output. Do not opt voice/round recording into HFP opportunistically.
"""),
        (session,
         """                        // Apply mixing/category/mode together, without an intermediate configuration.
                        try AVAudioSession.sharedInstance().setCategory(nativeCategory, mode: mode, options: options)
""",
         """                        // Avoid rebuilding an identical mixed configuration on the next take.
                        let session = AVAudioSession.sharedInstance()
                        if session.category != nativeCategory || session.mode != mode || session.categoryOptions != options {
                            try session.setCategory(nativeCategory, mode: mode, options: options)
                        }
"""),
        (session,
         """    private func setup(type: ManagedAudioSessionType, outputMode: AudioSessionOutputMode, activateNow: Bool) {
        self.deactivateTimer?.invalidate()
""",
         """    private func setup(type: ManagedAudioSessionType, outputMode: AudioSessionOutputMode, activateNow: Bool) {
        // A pending release retry must never deactivate a newly acquired session.
        self.nagramiXMixedReleaseGeneration &+= 1
        self.nagramiXMixedReleasePending = false
        self.deactivateTimer?.invalidate()
"""),
        (session,
         """                try AVAudioSession.sharedInstance().setActive(true, options: [.notifyOthersOnDeactivation])
""",
         """                if case .record(_, false, true) = type {
                    try AVAudioSession.sharedInstance().setActive(true)
                } else {
                    try AVAudioSession.sharedInstance().setActive(true, options: [.notifyOthersOnDeactivation])
                }
"""),
        (session,
         """        let wasPlaybackActive = self.currentTypeAndOutputMode?.0.isPlay ?? false
        self.currentTypeAndOutputMode = nil
""",
         """        let wasPlaybackActive = self.currentTypeAndOutputMode?.0.isPlay ?? false
        if self.currentTypeAndOutputMode == nil && self.nagramiXMixedReleasePending {
            return
        }
        let wasMixedRecording: Bool
        let preserveSystemRoute: Bool
        if let (type, outputMode) = self.currentTypeAndOutputMode, case .record(_, false, true) = type {
            wasMixedRecording = true
            if case .system = outputMode, case .record(false, false, true) = type {
                preserveSystemRoute = true
            } else {
                preserveSystemRoute = false
            }
        } else {
            wasMixedRecording = false
            preserveSystemRoute = false
        }
        self.nagramiXMixedReleaseGeneration &+= 1
        let releaseGeneration = self.nagramiXMixedReleaseGeneration
        self.currentTypeAndOutputMode = nil
        func releaseSession() throws {
            let session = AVAudioSession.sharedInstance()
            // Mixed recording did not interrupt other apps; do not send a resume hint
            // or clear a system route that this recording never explicitly overrode.
            try session.setActive(false, options: wasMixedRecording ? [] : [.notifyOthersOnDeactivation])
            if !preserveSystemRoute {
                try session.overrideOutputAudioPort(.none)
                try session.setPreferredInput(nil)
            }
        }
"""),
        (session,
         """        do {
            try AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
            try AVAudioSession.sharedInstance().overrideOutputAudioPort(.none)
            try AVAudioSession.sharedInstance().setPreferredInput(nil)
        } catch let error {
            managedAudioSessionLog("ManagedAudioSession applyNone error \\(error), waiting")

            Thread.sleep(forTimeInterval: 2.0)

            do {
                try AVAudioSession.sharedInstance().setActive(false, options: [.notifyOthersOnDeactivation])
                try AVAudioSession.sharedInstance().overrideOutputAudioPort(.none)
                try AVAudioSession.sharedInstance().setPreferredInput(nil)
            } catch let error {
                managedAudioSessionLog("ManagedAudioSession applyNone repeated error \\(error), giving up")
            }
        }
""",
         """        do {
            try releaseSession()
        } catch let error {
            managedAudioSessionLog("ManagedAudioSession applyNone error \\(error), waiting")
            if wasMixedRecording {
                // Camera/audio units may still be draining. Keep the native retry delay,
                // but let the next holder acquire the queue immediately.
                self.nagramiXMixedReleasePending = true
                self.queue.after(2.0, { [weak self] in
                    guard let self, self.nagramiXMixedReleaseGeneration == releaseGeneration else { return }
                    self.nagramiXMixedReleasePending = false
                    guard self.currentTypeAndOutputMode == nil, self.holders.isEmpty,
                          !self.callKitAudioSessionIsActive else { return }
                    do {
                        try releaseSession()
                    } catch let error {
                        managedAudioSessionLog("ManagedAudioSession applyNone repeated error \\(error), giving up")
                    }
                })
            } else {
                Thread.sleep(forTimeInterval: 2.0)
                do {
                    try releaseSession()
                } catch let error {
                    managedAudioSessionLog("ManagedAudioSession applyNone repeated error \\(error), giving up")
                }
            }
        }
"""),
        (recorder,
         """        var one: UInt32 = 1
        guard AudioUnitSetProperty(audioUnit, kAudioOutputUnitProperty_EnableIO, kAudioUnitScope_Input, 1, &one, 4) == noErr else {
""",
         """        let inputOnly = !self.pauseMusicOnRecording && !self.beginWithTone
        if inputOnly {
            // RemoteIO enables its output bus by default. A mic-only take must not
            // add a silent mono playback graph alongside another app's music.
            var outputEnabled: UInt32 = 0
            guard AudioUnitSetProperty(audioUnit, kAudioOutputUnitProperty_EnableIO, kAudioUnitScope_Output, 0, &outputEnabled, 4) == noErr else {
                AudioComponentInstanceDispose(audioUnit)
                return
            }
        }
        var one: UInt32 = 1
        guard AudioUnitSetProperty(audioUnit, kAudioOutputUnitProperty_EnableIO, kAudioUnitScope_Input, 1, &one, 4) == noErr else {
"""),
        (recorder,
         """        guard AudioUnitSetProperty(audioUnit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input, 0, &audioStreamDescription, UInt32(MemoryLayout<AudioStreamBasicDescription>.size)) == noErr else {
            AudioComponentInstanceDispose(audioUnit)
            return
        }
""",
         """        if !inputOnly {
            guard AudioUnitSetProperty(audioUnit, kAudioUnitProperty_StreamFormat, kAudioUnitScope_Input, 0, &audioStreamDescription, UInt32(MemoryLayout<AudioStreamBasicDescription>.size)) == noErr else {
                AudioComponentInstanceDispose(audioUnit)
                return
            }
        }
"""),
        (recorder,
         """        var zero: UInt32 = 1
        guard AudioUnitSetProperty(audioUnit, kAudioUnitProperty_ShouldAllocateBuffer, kAudioUnitScope_Output, 0, &zero, 4) == noErr else {
            AudioComponentInstanceDispose(audioUnit)
            return
        }
""" + "        \n" + """        let _ = AudioUnitSetProperty(audioUnit, kAUVoiceIOProperty_MuteOutput, kAudioUnitScope_Global, 0, &zero, 4)
""",
         """        if !inputOnly {
            var zero: UInt32 = 1
            guard AudioUnitSetProperty(audioUnit, kAudioUnitProperty_ShouldAllocateBuffer, kAudioUnitScope_Output, 0, &zero, 4) == noErr else {
                AudioComponentInstanceDispose(audioUnit)
                return
            }
            let _ = AudioUnitSetProperty(audioUnit, kAUVoiceIOProperty_MuteOutput, kAudioUnitScope_Global, 0, &zero, 4)
        }
"""),
        (camera,
         """                Queue.mainQueue().after(0.05) { [weak self] in
                    guard let self, !self.isDismissed else { return }
                    self.node.setupCamera()
                }
""",
         """                let setupCamera = { [weak self] in
                    guard let self, !self.isDismissed else { return }
                    self.node.setupCamera()
                }
                if case .record(_, _, true) = audioSessionType {
                    Queue.mainQueue().async(setupCamera)
                } else {
                    Queue.mainQueue().after(0.05, setupCamera)
                }
"""),
    ]
    for name, old, new in substitutions:
        if texts[name].count(old) != 1:
            raise SystemExit(f"Mixed recording transition anchor drift: {name}: {old[:80]!r}")
        texts[name] = texts[name].replace(old, new, 1)
    for name, text in texts.items():
        (source / name).write_text(text, encoding="utf-8")


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
    onboarding_copy = json.loads((overlay / "Resources/Onboarding/copy.json").read_text(encoding="utf-8"))
    expected_tour_keys = {"Tour.StartButton"} | {f"Tour.{kind}{index}" for kind in ("Title", "Text") for index in range(1, 7)}
    if set(onboarding_copy) != {"ru", "en"} or any(set(values) != expected_tour_keys for values in onboarding_copy.values()):
        raise SystemExit("Incomplete NagramiX welcome localization")
    # .strings resources contain escaped newlines, not JSON's actual newlines.
    russian_tour_strings = {key: value.replace("\n", "\\n") for key, value in onboarding_copy["ru"].items()}
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

    english_strings_text = english_app_strings.read_text(encoding="utf-8")
    for key, value in onboarding_copy["en"].items():
        pattern = re.compile(rf'("{re.escape(key)}"\s*=\s*")([^"\\]*(?:\\.[^"\\]*)*)(";)')
        escaped_value = value.replace("\n", "\\n")
        english_strings_text, replacement_count = pattern.subn(
            lambda match, value=escaped_value: match.group(1) + value + match.group(3), english_strings_text, count=1)
        if replacement_count != 1:
            raise SystemExit(f"Pinned English welcome string anchor must occur exactly once ({key})")
    english_app_strings.write_text(english_strings_text, encoding="utf-8")

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
    replace_unique(
        mt_dns,
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    // This used to race the native lookup against an HTTPS query to
    // https://google.com/resolve, Google's DNS-over-HTTPS reached through a spoofed Host
    // header. That endpoint answers 404 today (verified 2026-09), the status code was
    // never checked, and only successes were cached - so every connection through a
    // hostname proxy paid one dead HTTPS round trip, and an unreachable proxy turned that
    // into hundreds per push in the notification extension (bugs.telegram.org/c/64534).
    // The native lookup below coalesces concurrent callers and retries every 2 s until
    // it succeeds; the 10 s bound keeps the old fallback of eventually handing the socket
    // the bare hostname, so an unresolvable name still fails within the transport's 20 s
    // watchdog rather than stalling it. `take:1` closes a narrow window: `single:` emits
    // its next and its completion as two steps, and a native answer landing in between
    // would reach MTTcpConnection as a second address and make it call connectToHost:
    // again on a socket that is already connecting.
    return [[[self resolveHostnameNative:hostname port:port] timeout:10.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal single:hostname]] take:1];
}
""",
        """+ (MTSignal *)resolveHostnameUniversal:(NSString *)hostname port:(int32_t)port {
    if ([NagramiXDNSResolver usesSystemResolver]) {
        return [[[self resolveHostnameNative:hostname port:port] timeout:10.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal single:hostname]] take:1];
    }
    MTSignal *doh = [[NagramiXDNSResolver resolveHostname:hostname] timeout:12.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal fail:[NSError errorWithDomain:@"org.nagramix.dns" code:5 userInfo:nil]]];
    return [doh catch:^MTSignal *(__unused id error) {
        // Keep DoH primary, but never let an unreachable provider hold app
        // startup hostage by repeatedly closing every MTProto connection.
        if (MTLogEnabled()) {
            MTLog(@"[NagramiXDNS DoH unavailable; falling back to native resolver]");
        }
        return [[[self resolveHostnameNative:hostname port:port] timeout:10.0 onQueue:[MTQueue concurrentDefaultQueue] orSignal:[MTSignal single:hostname]] take:1];
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
    replace_unique(
        network_source,
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }
""",
        """    public func dropConnectionStatus() {
        _connectionStatus.set(.single(.waitingForNetwork))
    }

    public func reconnectForNagramiXDnsChange() {
        let _ = (self.shouldKeepConnection.get()
        |> take(1)
        |> deliverOn(self.queue)).start(next: { [weak self] keepConnection in
            guard let self else { return }
            self.mainSession.setPaused(true)
            self.dropConnectionStatus()
            self.mainSession.setPaused(!keepConnection)
        })
    }
""",
        "Reconnect MTProto after a runtime DNS resolver change",
    )

    account_source = source / "submodules" / "TelegramCore" / "Sources" / "Account" / "Account.swift"
    replace_unique(
        account_source,
        '        if !supplementary {\n            let mediaBox = postbox.mediaBox\n',
        """        let nagramiXDnsObserver = NotificationCenter.default.addObserver(forName: Notification.Name("NagramiXDnsSettingsChanged"), object: nil, queue: nil, using: { _ in
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
        'public final class Network: NSObject {\n',
        'public final class Network: NSObject {\n    public let nagramiXProxyStatuses = Atomic<ProxyServersStatuses?>(value: nil)\n',
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
    replace_unique(
        horizontal_tabs,
        """            let fillSlotWidths: [CGFloat]?
            if case .fill = component.layout {
                // A row up to the border on each side wider than the lens still fills the bar, as it did
                // while the fit was measured against the whole bar.
                fillSlotWidths = horizontalTabsFillSlotWidths(itemWidths: items.map(\\.size.width), availableWidth: availableSize.width - lensInset * 2.0 - sideInset * 2.0, paddingAllowance: lensInset * 2.0)
            } else {
                fillSlotWidths = nil
            }
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
""",
        """            let fillSlotWidths: [CGFloat]?
            switch component.layout {
            case .fill:
                fillSlotWidths = horizontalTabsFillSlotWidths(itemWidths: items.map(\\.size.width), availableWidth: availableSize.width - lensInset * 2.0 - sideInset * 2.0, paddingAllowance: lensInset * 2.0)
            case .equal:
                let width = max(0.0, availableSize.width - lensInset * 2.0 - sideInset * 2.0)
                fillSlotWidths = Array(repeating: width / CGFloat(max(1, items.count)), count: items.count)
            case .fit:
                fillSlotWidths = nil
            }
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
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
    # Telegram 13 adds an internal helper alongside the stock component. The
    # cloned NagramiX component is compiled in the same module: isolate its
    # helper as well, leaving the stock function and its tests unchanged.
    replace_unique(horizontal_tabs,
        "func horizontalTabsFillSlotWidths(",
        "private func nagramiXHorizontalTabsFillSlotWidths(",
        "Isolate the new fill-width helper in the NagramiX tab clone")
    replace_unique(horizontal_tabs,
        "fillSlotWidths = horizontalTabsFillSlotWidths(",
        "fillSlotWidths = nagramiXHorizontalTabsFillSlotWidths(",
        "Use only the private cloned tab-width helper")
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
    replace_unique(
        ongoing_call_context,
        '                #if DEBUG && true\n                if let initialCustomParameters =',
        """                var customParameters = customParameters

                #if DEBUG && true
                if let initialCustomParameters =""",
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
    replace_unique(
        chat_bubble_source,
        '        var tmpWidth: CGFloat\n',
        """        if nagramiXWideChannelPost {
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
    replace_unique(
        settings_items,
        '    case myProfile\n    case wallet\n',
        '    case nagramix\n    case myProfile\n    case wallet\n',
        "NagramiX settings group order",
    )
    replace_unique(
        settings_items,
        """        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
""",
        """        items[.nagramix]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.nagramiXSettingsTitle, icon: PresentationResourcesSettings.nagramiXSettings, action: {
            interaction.openSettings(.nagramix)
        }))

        items[.myProfile]!.append(PeerInfoScreenDisclosureItem(id: 0, text: presentationData.strings.Settings_MyProfile, icon: PresentationResourcesSettings.myProfile, action: {
            interaction.openSettings(.profile)
        }))
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

    camera_output = source / "submodules" / "Camera" / "CameraLegacy" / "Sources" / "CameraOutput.swift"
    replace_unique(
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

    camera_context = source / "submodules" / "Camera" / "CameraLegacy" / "Sources" / "LegacyCamera.swift"
    replace_unique(
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
    apply_channel_bottom_panel(source)
    apply_message_interaction_options(source)
    apply_download_acceleration(source)
    apply_chat_actions_readonly_fix(source)
    apply_copy_broadcast_split(source)
    apply_background_video_hierarchy_fix(source)
    apply_photo_jpeg_compatibility_fix(source)
    apply_archived_round_video_fix(source)
    apply_notification_sound_catalog(source, overlay)
    apply_qr_brightness_restore(source)
    apply_anonymous_story_viewing(source)
    apply_separate_profile_navigation_buttons(source)
    apply_voice_recording_cancellation_fix(source)
    apply_message_selection_transfer_actions(source, overlay)
    apply_deferred_preview_reactions(source, overlay)
    apply_in_app_notification_sound_default(source)
    apply_story_viewing_mode_confirmation(source)
    apply_option_selection_sheets(source, overlay)
    apply_proxy_vpn_policy_and_layout(source, overlay)
    apply_hide_greeting_sticker(source, overlay)
    apply_recording_music_default(source)
    apply_voice_autoplay_policy(source)
    apply_channel_mute_and_exact_time(source)
    apply_authorization_alert_handling(source)
    apply_recording_session_continuity(source)
    apply_gallery_media_modes(source, overlay)
    apply_unread_chats_first(source, overlay)
    apply_archived_copy_send_fix(source, overlay)
    apply_proxy_settings_sync_fix(source)
    apply_nagramix_onboarding(source, overlay)
    apply_archived_media_save(source, overlay)
    apply_skip_call_rating(source)
    apply_recorder_backpressure_fix(source)
    apply_login_postbox_handoff(source)
    apply_author_selection_archive_deletion(source)
    apply_dns_provider_list(source)
    apply_mixed_recording_transition(source)
    apply_anti_caps(source)
    apply_anonymous_stickers_and_blocked_filter(source)
    apply_archived_selection_actions_fix(source)
    apply_selfie_countdown(source)
    apply_video_rotation_pip_lifetime_fix(source)
    apply_global_tab_search_fix(source)
    apply_archived_replay_and_upload_cache_fix(source)
    apply_full_name_deletion_menu(source)
    apply_selfie_recording_lifecycle(source)
    apply_mixed_playback_return(source)
    replace_unique(
        source / "submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift",
        "title: text, value: value, enableInteractiveChanges: true, enabled: true, sectionId: self.section, style: .blocks, updated: arguments.toggleUseForCalls, tag: ProxySettingsEntryTag.useForCalls)",
        "title: text, value: value, enableInteractiveChanges: true, enabled: true, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.toggleUseForCalls, tag: ProxySettingsEntryTag.useForCalls)",
        "Перенос полного названия настройки прокси для звонков",
    )

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
    parser.add_argument("--telegram-dir", required=True, type=Path, help="Path to a clean Telegram-iOS 13.0 checkout")
    arguments = parser.parse_args()
    apply_features(arguments.telegram_dir.resolve())

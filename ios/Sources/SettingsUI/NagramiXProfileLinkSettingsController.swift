import Foundation
import UIKit
import Display
import Postbox
import SwiftSignalKit
import TelegramCore
import TelegramPresentationData
import PresentationDataUtils
import ItemListUI
import AccountContext
import AlertUI
import ComponentFlow
import AlertComponent
import AlertInputFieldComponent
import NagramiXCore

private struct NagramiXProfileLinkArguments {
    let setEnabled: (Bool) -> Void
    let editId: () -> Void
    let useMine: () -> Void
    let openProfile: () -> Void
}

private enum NagramiXProfileLinkEntry: ItemListNodeEntry {
    case enabled(Bool)
    case info
    case targetHeader
    case target(String)
    case id(String)
    case useMine
    case unavailable
    case open
    case hint

    var stableId: Int32 {
        switch self {
        case .enabled: return 0
        case .info: return 1
        case .targetHeader: return 2
        case .target: return 3
        case .id: return 4
        case .useMine: return 5
        case .unavailable: return 6
        case .open: return 7
        case .hint: return 8
        }
    }
    var section: ItemListSectionId {
        switch self {
        case .enabled, .info: return 0
        case .targetHeader, .target, .id, .useMine, .unavailable: return 1
        case .open, .hint: return 2
        }
    }
    static func < (lhs: Self, rhs: Self) -> Bool { lhs.stableId < rhs.stableId }
    func item(presentationData: ItemListPresentationData, arguments: Any) -> ListViewItem {
        let arguments = arguments as! NagramiXProfileLinkArguments
        let strings = presentationData.strings
        switch self {
        case let .enabled(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: strings.nagramiXProfileLinkEnabled, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.setEnabled)
        case .info:
            return ItemListTextItem(presentationData: presentationData, text: .plain(strings.nagramiXProfileLinkInfo), sectionId: self.section)
        case .targetHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: strings.nagramiXProfileLinkTargetHeader.uppercased(), sectionId: self.section)
        case let .target(name):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: strings.nagramiXProfileLinkTarget, label: name, sectionId: self.section, style: .blocks, action: arguments.editId)
        case let .id(value):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: strings.nagramiXProfileLinkId, label: value, sectionId: self.section, style: .blocks, action: arguments.editId)
        case .useMine:
            return ItemListActionItem(presentationData: presentationData, systemStyle: .glass, title: strings.nagramiXProfileLinkUseMine, kind: .generic, alignment: .natural, sectionId: self.section, style: .blocks, action: arguments.useMine)
        case .unavailable:
            return ItemListTextItem(presentationData: presentationData, text: .plain(strings.nagramiXProfileLinkNotFound), sectionId: self.section)
        case .open:
            return ItemListActionItem(presentationData: presentationData, systemStyle: .glass, title: strings.nagramiXProfileLinkOpen, kind: .generic, alignment: .natural, sectionId: self.section, style: .blocks, action: arguments.openProfile)
        case .hint:
            return ItemListTextItem(presentationData: presentationData, text: .plain(strings.nagramiXProfileLinkPreviewInfo), sectionId: self.section)
        }
    }
}

private func nagramiXProfileLinkPeerId(context: AccountContext, settings: NagramiXTabSettings) -> EnginePeer.Id? {
    if settings.profileLinkUserId.isEmpty { return context.account.peerId }
    guard let value = NagramiXTabSettings.normalizedProfileLinkUserId(settings.profileLinkUserId), let id = Int64(value) else { return nil }
    return EnginePeer.Id(namespace: Namespaces.Peer.CloudUser, id: EnginePeer.Id.Id._internalFromInt64Value(id))
}

private func nagramiXProfileLinkIdEditor(context: AccountContext, apply: @escaping (String) -> Void) -> ViewController {
    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
    let strings = presentationData.strings
    let input = AlertInputFieldComponent.ExternalState()
    let initial = NagramiXTabSettings.current.profileLinkUserId
    let progress = ValuePromise<Bool>(false)
    let validation = MetaDisposable()
    var applyImpl: (() -> Void)?
    let controller = AlertScreen(configuration: .init(allowInputInset: true), content: [
        AnyComponentWithIdentity(id: "title", component: AnyComponent(AlertTitleComponent(title: strings.nagramiXProfileLinkEditor))),
        AnyComponentWithIdentity(id: "text", component: AnyComponent(AlertTextComponent(content: .plain(strings.nagramiXProfileLinkIdHint)))),
        AnyComponentWithIdentity(id: "input", component: AnyComponent(AlertInputFieldComponent(context: context, initialValue: initial.isEmpty ? String(context.account.peerId.id._internalGetInt64Value()) : initial, placeholder: strings.nagramiXProfileLinkId, characterLimit: 17, hasClearButton: true, keyboardType: .numberPad, autocapitalizationType: .none, autocorrectionType: .no, isInitiallyFocused: true, externalState: input, shouldChangeText: { _ in true }, returnKeyAction: { applyImpl?() })))
    ], actions: [
        .init(title: strings.Common_Cancel),
        .init(title: strings.nagramiXSave, type: .default, action: { applyImpl?() }, autoDismiss: false, isEnabled: input.valueSignal |> map { NagramiXTabSettings.normalizedProfileLinkUserId($0) != nil }, progress: progress.get())
    ], updatedPresentationData: (presentationData, context.sharedContext.presentationData))
    applyImpl = { [weak controller] in
        guard let value = NagramiXTabSettings.normalizedProfileLinkUserId(input.value), let id = Int64(value) else {
            input.animateError()
            return
        }
        let peerId = EnginePeer.Id(namespace: Namespaces.Peer.CloudUser, id: EnginePeer.Id.Id._internalFromInt64Value(id))
        progress.set(true)
        validation.set((context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: peerId)) |> deliverOnMainQueue).start(next: { [weak controller] peer in
            progress.set(false)
            guard let controller else { return }
            guard let peer, case let .user(user) = peer, let accessHash = user.accessHash, case .personal = accessHash else {
                input.animateError()
                controller.present(textAlertController(context: context, title: strings.nagramiXProfileLinkUnavailable, text: strings.nagramiXProfileLinkNotFound, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})]), in: .window(.root))
                return
            }
            apply(peer.id == context.account.peerId ? "" : value)
            controller.dismiss()
        }))
    }
    controller.dismissed = { _ in validation.dispose() }
    return controller
}

func nagramiXProfileLinkSettingsController(context: AccountContext, updated: @escaping () -> Void) -> ViewController {
    let settings = Signal<NagramiXTabSettings, NoError> { subscriber in
        subscriber.putNext(.current)
        let observer = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main) { _ in
            subscriber.putNext(.current)
        }
        return ActionDisposable { NotificationCenter.default.removeObserver(observer) }
    }
    let target = settings |> mapToSignal { value -> Signal<(NagramiXTabSettings, EnginePeer?), NoError> in
        guard let peerId = nagramiXProfileLinkPeerId(context: context, settings: value) else { return .single((value, nil)) }
        return context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: peerId)) |> map { peer in
            guard let peer, case let .user(user) = peer, let accessHash = user.accessHash, case .personal = accessHash else { return (value, nil) }
            return (value, peer)
        }
    }
    var pushImpl: ((ViewController) -> Void)?
    var presentImpl: ((ViewController) -> Void)?
    let update: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        updated()
    }
    let unavailable = {
        let strings = context.sharedContext.currentPresentationData.with { $0.strings }
        presentImpl?(textAlertController(context: context, title: strings.nagramiXProfileLinkUnavailable, text: strings.nagramiXProfileLinkNotFound, actions: [TextAlertAction(type: .defaultAction, title: strings.Common_OK, action: {})]))
    }
    let openDisposable = MetaDisposable()
    let arguments = NagramiXProfileLinkArguments(setEnabled: { enabled in
        update { $0.profileLinkEnabled = enabled }
    }, editId: {
        presentImpl?(nagramiXProfileLinkIdEditor(context: context, apply: { id in update { $0.profileLinkUserId = id } }))
    }, useMine: {
        update { $0.profileLinkUserId = "" }
    }, openProfile: {
        guard let id = nagramiXProfileLinkPeerId(context: context, settings: .current) else { unavailable(); return }
        openDisposable.set((context.engine.data.get(TelegramEngine.EngineData.Item.Peer.Peer(id: id)) |> deliverOnMainQueue).start(next: { peer in
            guard let peer, case .user = peer, let controller = context.sharedContext.makePeerInfoController(context: context, updatedPresentationData: nil, peer: peer, mode: .generic, avatarInitiallyExpanded: false, fromChat: false, requestsContext: nil) else { unavailable(); return }
            pushImpl?(controller)
        }))
    })
    let signal = combineLatest(queue: .mainQueue(), context.sharedContext.presentationData, target) |> map { presentationData, value -> (ItemListControllerState, (ItemListNodeState, Any)) in
        let (settings, peer) = value
        let strings = presentationData.strings
        let name: String
        if settings.profileLinkUserId.isEmpty { name = strings.nagramiXProfileLinkMine }
        else if let peer, case .user = peer { name = peer.displayTitle(strings: strings, displayOrder: presentationData.nameDisplayOrder) }
        else { name = strings.nagramiXProfileLinkUnavailable }
        let id = settings.profileLinkUserId.isEmpty ? String(context.account.peerId.id._internalGetInt64Value()) : settings.profileLinkUserId
        var entries: [NagramiXProfileLinkEntry] = [.enabled(settings.profileLinkEnabled), .targetHeader, .target(name), .id(id)]
        if !settings.profileLinkUserId.isEmpty { entries.append(.useMine) }
        if !settings.profileLinkUserId.isEmpty, peer == nil { entries.append(.unavailable) }
        entries.append(.open)
        let state = ItemListControllerState(presentationData: ItemListPresentationData(presentationData), title: .text(strings.nagramiXProfileLinkTitle), leftNavigationButton: nil, rightNavigationButton: nil, backNavigationButton: ItemListBackButton(title: strings.Common_Back))
        let list = ItemListNodeState(presentationData: ItemListPresentationData(presentationData), entries: entries, style: .blocks, emptyStateItem: nil, animateChanges: true)
        return (state, (list, arguments))
    }
    let controller = ItemListController(context: context, state: signal |> afterDisposed { openDisposable.dispose() })
    pushImpl = { [weak controller] value in (controller?.navigationController as? NavigationController)?.pushViewController(value) }
    presentImpl = { [weak controller] value in controller?.present(value, in: .window(.root)) }
    return controller
}

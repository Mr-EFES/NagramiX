import Foundation
import UIKit
import Display
import SwiftSignalKit
import TelegramPresentationData
import PresentationDataUtils
import ItemListUI
import AccountContext
import NagramiXCore

private struct NagramiXSettingsControllerArguments {
    let openProxySettings: () -> Void
    let updateHideContacts: (Bool) -> Void
    let updateHideCalls: (Bool) -> Void
    let updateShowSearchButton: (Bool) -> Void
    let updateShowProxyButton: (Bool) -> Void
    let updateHideProxySponsorChannel: (Bool) -> Void
    let updateUseRearCameraForVideoMessages: (Bool) -> Void
    let updateHideStories: (Bool) -> Void
    let updateDisableStoryCameraSwipe: (Bool) -> Void
    let updateConfirmStoryViewing: (Bool) -> Void
    let updateEnableStoryRepost: (Bool) -> Void
    let updateShowProfileIds: (Bool) -> Void
    let updateShowRegistrationDate: (Bool) -> Void
    let updateShowChatCreationDate: (Bool) -> Void
    let updateConfirmOutgoingCalls: (Bool) -> Void
}

private enum NagramiXSettingsCategory: Int, CaseIterable {
    case interface
    case features
    case other
}

private enum NagramiXSettingsSection: Int32 {
    case tabs
    case videoMessages
    case stories
    case profiles
    case calls
    case other
}

private enum NagramiXSettingsEntry: ItemListNodeEntry {
    case tabsHeader
    case hideContacts(Bool)
    case hideCalls(Bool)
    case showSearchButton(Bool)
    case showProxyButton(Bool)
    case hideProxySponsorChannel(Bool)
    case videoMessagesHeader
    case useRearCameraForVideoMessages(Bool)
    case interfaceStoriesHeader
    case featureStoriesHeader
    case hideStories(Bool)
    case disableStoryCameraSwipe(Bool)
    case confirmStoryViewing(Bool)
    case enableStoryRepost(Bool)
    case profilesHeader
    case showProfileIds(Bool)
    case showRegistrationDate(Bool)
    case showChatCreationDate(Bool)
    case callsHeader
    case confirmOutgoingCalls(Bool)
    case proxySettings

    var category: NagramiXSettingsCategory {
        switch self {
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel,
                .interfaceStoriesHeader, .hideStories, .profilesHeader, .showProfileIds, .showRegistrationDate, .showChatCreationDate:
            return .interface
        case .videoMessagesHeader, .useRearCameraForVideoMessages, .featureStoriesHeader, .disableStoryCameraSwipe,
                .confirmStoryViewing, .enableStoryRepost, .callsHeader, .confirmOutgoingCalls:
            return .features
        case .proxySettings:
            return .other
        }
    }

    var section: ItemListSectionId {
        switch self {
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel:
            return NagramiXSettingsSection.tabs.rawValue
        case .videoMessagesHeader, .useRearCameraForVideoMessages:
            return NagramiXSettingsSection.videoMessages.rawValue
        case .interfaceStoriesHeader, .featureStoriesHeader, .hideStories, .disableStoryCameraSwipe, .confirmStoryViewing, .enableStoryRepost:
            return NagramiXSettingsSection.stories.rawValue
        case .profilesHeader, .showProfileIds, .showRegistrationDate, .showChatCreationDate:
            return NagramiXSettingsSection.profiles.rawValue
        case .callsHeader, .confirmOutgoingCalls:
            return NagramiXSettingsSection.calls.rawValue
        case .proxySettings:
            return NagramiXSettingsSection.other.rawValue
        }
    }

    var stableId: Int32 {
        switch self {
        case .tabsHeader: return 0
        case .hideContacts: return 1
        case .hideCalls: return 2
        case .showSearchButton: return 3
        case .showProxyButton: return 4
        case .hideProxySponsorChannel: return 5
        case .videoMessagesHeader: return 10
        case .useRearCameraForVideoMessages: return 11
        case .interfaceStoriesHeader: return 20
        case .hideStories: return 21
        case .featureStoriesHeader: return 25
        case .disableStoryCameraSwipe: return 26
        case .confirmStoryViewing: return 27
        case .enableStoryRepost: return 28
        case .profilesHeader: return 30
        case .showProfileIds: return 31
        case .showRegistrationDate: return 32
        case .showChatCreationDate: return 33
        case .callsHeader: return 40
        case .confirmOutgoingCalls: return 41
        case .proxySettings: return 50
        }
    }

    static func < (lhs: NagramiXSettingsEntry, rhs: NagramiXSettingsEntry) -> Bool {
        return lhs.stableId < rhs.stableId
    }

    func item(presentationData: ItemListPresentationData, arguments: Any) -> ListViewItem {
        let arguments = arguments as! NagramiXSettingsControllerArguments
        switch self {
        case .tabsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXTabsHeader, sectionId: self.section)
        case let .hideContacts(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideContactsTab, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateHideContacts)
        case let .hideCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideCallsTab, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateHideCalls)
        case let .showSearchButton(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowSearchButton, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowSearchButton)
        case let .showProxyButton(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowProxyButton, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowProxyButton)
        case let .hideProxySponsorChannel(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideProxySponsorChannel, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateHideProxySponsorChannel)
        case .videoMessagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoMessagesHeader, sectionId: self.section)
        case let .useRearCameraForVideoMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUseRearCamera, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateUseRearCameraForVideoMessages)
        case .interfaceStoriesHeader, .featureStoriesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXStoriesHeader, sectionId: self.section)
        case let .hideStories(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideStories, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateHideStories)
        case let .disableStoryCameraSwipe(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDisableStoryCameraSwipe, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateDisableStoryCameraSwipe)
        case let .confirmStoryViewing(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmStoryViewing, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmStoryViewing)
        case let .enableStoryRepost(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXEnableStoryRepost, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateEnableStoryRepost)
        case .profilesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXProfilesHeader, sectionId: self.section)
        case let .showProfileIds(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowProfileIds, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowProfileIds)
        case let .showRegistrationDate(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowRegistrationDate, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowRegistrationDate)
        case let .showChatCreationDate(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowChatCreationDate, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowChatCreationDate)
        case .callsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXCallsHeader, sectionId: self.section)
        case let .confirmOutgoingCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmOutgoingCalls, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmOutgoingCalls)
        case .proxySettings:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXProxySettings, label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
        }
    }
}

private func nagramiXSettingsEntries(settings: NagramiXTabSettings, category: NagramiXSettingsCategory) -> [NagramiXSettingsEntry] {
    let entries: [NagramiXSettingsEntry] = [
        .tabsHeader, .hideContacts(settings.hideContacts), .hideCalls(settings.hideCalls),
        .showSearchButton(settings.showSearchButton), .showProxyButton(settings.showProxyButton),
        .hideProxySponsorChannel(settings.hideProxySponsorChannel),
        .videoMessagesHeader, .useRearCameraForVideoMessages(settings.useRearCameraForVideoMessages),
        .interfaceStoriesHeader, .featureStoriesHeader, .hideStories(settings.hideStories),
        .disableStoryCameraSwipe(settings.disableStoryCameraSwipe),
        .confirmStoryViewing(settings.confirmStoryViewing), .enableStoryRepost(settings.enableStoryRepost),
        .profilesHeader, .showProfileIds(settings.showProfileIds),
        .showRegistrationDate(settings.showRegistrationDate),
        .showChatCreationDate(settings.showChatCreationDate),
        .callsHeader, .confirmOutgoingCalls(settings.confirmOutgoingCalls),
        .proxySettings,
    ]
    return entries.filter { $0.category == category }
}

public func nagramiXSettingsController(context: AccountContext) -> ViewController {
    let settingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let categoryPromise = ValuePromise<NagramiXSettingsCategory>(.interface, ignoreRepeated: true)
    let update: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        settingsPromise.set(NagramiXTabSettings.current)
    }
    var pushControllerImpl: ((ViewController) -> Void)?
    let arguments = NagramiXSettingsControllerArguments(
        openProxySettings: {
            pushControllerImpl?(proxySettingsController(context: context))
        },
        updateHideContacts: { value in update { $0.hideContacts = value } },
        updateHideCalls: { value in update { $0.hideCalls = value } },
        updateShowSearchButton: { value in update { $0.showSearchButton = value } },
        updateShowProxyButton: { value in update { $0.showProxyButton = value } },
        updateHideProxySponsorChannel: { value in update { $0.hideProxySponsorChannel = value } },
        updateUseRearCameraForVideoMessages: { value in update { $0.useRearCameraForVideoMessages = value } },
        updateHideStories: { value in update { $0.hideStories = value } },
        updateDisableStoryCameraSwipe: { value in update { $0.disableStoryCameraSwipe = value } },
        updateConfirmStoryViewing: { value in update { $0.confirmStoryViewing = value } },
        updateEnableStoryRepost: { value in update { $0.enableStoryRepost = value } },
        updateShowProfileIds: { value in update { $0.showProfileIds = value } },
        updateShowRegistrationDate: { value in update { $0.showRegistrationDate = value } },
        updateShowChatCreationDate: { value in update { $0.showChatCreationDate = value } },
        updateConfirmOutgoingCalls: { value in update { $0.confirmOutgoingCalls = value } }
    )
    let signal = combineLatest(queue: .mainQueue(), context.sharedContext.presentationData, settingsPromise.get(), categoryPromise.get())
    |> map { presentationData, settings, category -> (ItemListControllerState, (ItemListNodeState, Any)) in
        var presentationData = presentationData
        presentationData = presentationData.withUpdated(theme: presentationData.theme.withModalBlocksBackground())
        let controllerState = ItemListControllerState(
            presentationData: ItemListPresentationData(presentationData),
            title: .equalSectionControl([
                presentationData.strings.nagramiXSettingsInterface,
                presentationData.strings.nagramiXSettingsFeatures,
                presentationData.strings.nagramiXSettingsOther,
            ], category.rawValue),
            leftNavigationButton: nil,
            rightNavigationButton: nil,
            backNavigationButton: ItemListBackButton(title: presentationData.strings.Common_Back)
        )
        let listState = ItemListNodeState(
            presentationData: ItemListPresentationData(presentationData),
            entries: nagramiXSettingsEntries(settings: settings, category: category),
            style: .blocks,
            animateChanges: true
        )
        return (controllerState, (listState, arguments))
    }
    let controller = ItemListController(context: context, state: signal)
    pushControllerImpl = { [weak controller] pushedController in
        (controller?.navigationController as? NavigationController)?.pushViewController(pushedController)
    }
    controller.titleControlValueChanged = { index in
        if let category = NagramiXSettingsCategory(rawValue: index) {
            categoryPromise.set(category)
        }
    }
    return controller
}

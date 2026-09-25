import Foundation
import UIKit
import Display
import SwiftSignalKit
import TelegramPresentationData
import PresentationDataUtils
import ItemListUI
import AccountContext
import TelegramCore
import AlertUI
import NagramiXCore

private struct NagramiXSettingsControllerArguments {
    let openProxySettings: () -> Void
    let updateHideContacts: (Bool) -> Void
    let updateHideCalls: (Bool) -> Void
    let updateShowSearchButton: (Bool) -> Void
    let updateWideChannelPosts: (Bool) -> Void
    let updateShowProxyButton: (Bool) -> Void
    let updateHideProxySponsorChannel: (Bool) -> Void
    let updateUseRearCameraForVideoMessages: (Bool) -> Void
    let updateHideStories: (Bool) -> Void
    let updateDisableStoryCameraSwipe: (Bool) -> Void
    let updateConfirmStoryViewing: (Bool) -> Void
    let updateEnableStoryRepost: (Bool) -> Void
    let updateShowProfileIds: (Bool) -> Void
    let updateShowRegistrationDate: (Bool) -> Void
    let updateShowMutualContactIcon: (Bool) -> Void
    let updateConfirmOutgoingCalls: (Bool) -> Void
    let updateForceTcpCalls: (Bool) -> Void
    let updateShowDeletedMessages: (Bool) -> Void
    let updateMessageEditHistory: (Bool) -> Void
    let clearMessageArchive: () -> Void
}

private enum NagramiXSettingsCategory: Int, CaseIterable {
    case interface
    case features
    case other
}

private enum NagramiXSettingsSection: Int32 {
    case tabs
    case chats
    case videoMessages
    case stories
    case profiles
    case messages
    case calls
    case other
}

private enum NagramiXSettingsEntry: ItemListNodeEntry {
    case searchHeader(Int32, String)
    case tabsHeader
    case hideContacts(Bool)
    case hideCalls(Bool)
    case showSearchButton(Bool)
    case showProxyButton(Bool)
    case hideProxySponsorChannel(Bool)
    case chatsHeader
    case wideChannelPosts(Bool)
    case videoMessagesHeader
    case useRearCameraForVideoMessages(Bool)
    case featureStoriesHeader
    case hideStories(Bool)
    case disableStoryCameraSwipe(Bool)
    case confirmStoryViewing(Bool)
    case enableStoryRepost(Bool)
    case profilesHeader
    case showProfileIds(Bool)
    case showRegistrationDate(Bool)
    case showMutualContactIcon(Bool)
    case callsHeader
    case confirmOutgoingCalls(Bool)
    case forceTcpCalls(Bool)
    case forceTcpCallsInfo
    case messagesHeader
    case showDeletedMessages(Bool)
    case showDeletedMessagesInfo
    case messageEditHistory(Bool)
    case messageEditHistoryInfo
    case clearMessageArchive
    case messageArchiveInfo
    case proxySettings
    case proxyDns
    case proxyAutoSwitch
    case proxyCheckAll

    var category: NagramiXSettingsCategory {
        switch self {
        case .searchHeader:
            return .interface
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel, .chatsHeader, .wideChannelPosts,
                .profilesHeader, .showProfileIds, .showRegistrationDate, .showMutualContactIcon:
            return .interface
        case .videoMessagesHeader, .useRearCameraForVideoMessages, .featureStoriesHeader, .hideStories, .disableStoryCameraSwipe,
                .confirmStoryViewing, .enableStoryRepost, .callsHeader, .confirmOutgoingCalls:
            return .features
        case .messagesHeader, .showDeletedMessages, .showDeletedMessagesInfo, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return .features
        case .forceTcpCalls, .forceTcpCallsInfo, .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return .other
        }
    }

    var section: ItemListSectionId {
        switch self {
        case let .searchHeader(sectionId, _):
            return sectionId
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel:
            return NagramiXSettingsSection.tabs.rawValue
        case .chatsHeader, .wideChannelPosts:
            return NagramiXSettingsSection.chats.rawValue
        case .videoMessagesHeader, .useRearCameraForVideoMessages:
            return NagramiXSettingsSection.videoMessages.rawValue
        case .featureStoriesHeader, .hideStories, .disableStoryCameraSwipe, .confirmStoryViewing, .enableStoryRepost:
            return NagramiXSettingsSection.stories.rawValue
        case .profilesHeader, .showProfileIds, .showRegistrationDate, .showMutualContactIcon:
            return NagramiXSettingsSection.profiles.rawValue
        case .callsHeader, .confirmOutgoingCalls, .forceTcpCalls, .forceTcpCallsInfo:
            return NagramiXSettingsSection.calls.rawValue
        case .messagesHeader, .showDeletedMessages, .showDeletedMessagesInfo, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return NagramiXSettingsSection.messages.rawValue
        case .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return NagramiXSettingsSection.other.rawValue
        }
    }

    var stableId: Int32 {
        switch self {
        case let .searchHeader(id, _): return 1000 + id
        case .tabsHeader: return 0
        case .hideContacts: return 1
        case .hideCalls: return 2
        case .showSearchButton: return 3
        case .showProxyButton: return 4
        case .hideProxySponsorChannel: return 5
        case .chatsHeader: return 6
        case .wideChannelPosts: return 7
        case .videoMessagesHeader: return 10
        case .useRearCameraForVideoMessages: return 11
        case .hideStories: return 21
        case .featureStoriesHeader: return 25
        case .disableStoryCameraSwipe: return 26
        case .confirmStoryViewing: return 27
        case .enableStoryRepost: return 28
        case .profilesHeader: return 30
        case .showProfileIds: return 31
        case .showRegistrationDate: return 32
        case .showMutualContactIcon: return 33
        case .messagesHeader: return 34
        case .showDeletedMessages: return 35
        case .showDeletedMessagesInfo: return 36
        case .messageEditHistory: return 37
        case .messageEditHistoryInfo: return 38
        case .clearMessageArchive: return 39
        case .messageArchiveInfo: return 40
        case .callsHeader: return 50
        case .confirmOutgoingCalls: return 51
        case .forceTcpCalls: return 52
        case .forceTcpCallsInfo: return 53
        case .proxySettings: return 60
        case .proxyDns: return 61
        case .proxyAutoSwitch: return 62
        case .proxyCheckAll: return 63
        }
    }

    static func < (lhs: NagramiXSettingsEntry, rhs: NagramiXSettingsEntry) -> Bool {
        return lhs.stableId < rhs.stableId
    }

    func item(presentationData: ItemListPresentationData, arguments: Any) -> ListViewItem {
        let arguments = arguments as! NagramiXSettingsControllerArguments
        switch self {
        case let .searchHeader(_, title):
            return ItemListSectionHeaderItem(presentationData: presentationData, text: title, sectionId: self.section)
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
        case .chatsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXChatsHeader, sectionId: self.section)
        case let .wideChannelPosts(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXWideChannelPosts, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateWideChannelPosts)
        case .videoMessagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoMessagesHeader, sectionId: self.section)
        case let .useRearCameraForVideoMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUseRearCamera, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateUseRearCameraForVideoMessages)
        case .featureStoriesHeader:
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
        case let .showMutualContactIcon(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowMutualContactIcon, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowMutualContactIcon)
        case .callsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXCallsHeader, sectionId: self.section)
        case let .confirmOutgoingCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmOutgoingCalls, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmOutgoingCalls)
        case let .forceTcpCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXForceTcpCalls, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateForceTcpCalls)
        case .forceTcpCallsInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXForceTcpCallsInfo), sectionId: self.section)
        case .messagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXMessagesHeader, sectionId: self.section)
        case let .showDeletedMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletedMessages, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowDeletedMessages)
        case .showDeletedMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXDeletedMessagesInfo), sectionId: self.section)
        case let .messageEditHistory(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXMessageEditHistory, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateMessageEditHistory)
        case .messageEditHistoryInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXMessageEditHistoryInfo), sectionId: self.section)
        case .clearMessageArchive:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXClearMessageArchive, label: "", sectionId: self.section, style: .blocks, action: arguments.clearMessageArchive)
        case .messageArchiveInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXLocalArchiveInfo), sectionId: self.section)
        case .proxySettings:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXProxySettings, label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
        case .proxyDns:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDns, label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
        case .proxyAutoSwitch:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXProxyAutoSwitch, label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
        case .proxyCheckAll:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXProxyCheckAll, label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
        }
    }
}

private extension NagramiXSettingsCategory {
    func title(strings: PresentationStrings) -> String {
        switch self {
        case .interface:
            return strings.nagramiXSettingsInterface
        case .features:
            return strings.nagramiXSettingsFeatures
        case .other:
            return strings.nagramiXSettingsOther
        }
    }
}

private extension NagramiXSettingsEntry {
    var isSearchOnly: Bool {
        switch self {
        case .searchHeader, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return true
        default:
            return false
        }
    }

    var isSearchableSetting: Bool {
        switch self {
        case .searchHeader, .tabsHeader, .chatsHeader, .videoMessagesHeader, .featureStoriesHeader, .profilesHeader, .callsHeader, .messagesHeader,
                .forceTcpCallsInfo, .showDeletedMessagesInfo, .messageEditHistoryInfo, .messageArchiveInfo:
            return false
        default:
            return true
        }
    }

    func title(strings: PresentationStrings) -> String {
        switch self {
        case let .searchHeader(_, title): return title
        case .tabsHeader: return strings.nagramiXTabsHeader
        case .hideContacts: return strings.nagramiXHideContactsTab
        case .hideCalls: return strings.nagramiXHideCallsTab
        case .showSearchButton: return strings.nagramiXShowSearchButton
        case .showProxyButton: return strings.nagramiXShowProxyButton
        case .hideProxySponsorChannel: return strings.nagramiXHideProxySponsorChannel
        case .chatsHeader: return strings.nagramiXChatsHeader
        case .wideChannelPosts: return strings.nagramiXWideChannelPosts
        case .videoMessagesHeader: return strings.nagramiXVideoMessagesHeader
        case .useRearCameraForVideoMessages: return strings.nagramiXUseRearCamera
        case .featureStoriesHeader: return strings.nagramiXStoriesHeader
        case .hideStories: return strings.nagramiXHideStories
        case .disableStoryCameraSwipe: return strings.nagramiXDisableStoryCameraSwipe
        case .confirmStoryViewing: return strings.nagramiXConfirmStoryViewing
        case .enableStoryRepost: return strings.nagramiXEnableStoryRepost
        case .profilesHeader: return strings.nagramiXProfilesHeader
        case .showProfileIds: return strings.nagramiXShowProfileIds
        case .showRegistrationDate: return strings.nagramiXShowRegistrationDate
        case .showMutualContactIcon: return strings.nagramiXShowMutualContactIcon
        case .callsHeader: return strings.nagramiXCallsHeader
        case .confirmOutgoingCalls: return strings.nagramiXConfirmOutgoingCalls
        case .forceTcpCalls: return strings.nagramiXForceTcpCalls
        case .forceTcpCallsInfo: return strings.nagramiXForceTcpCallsInfo
        case .messagesHeader: return strings.nagramiXMessagesHeader
        case .showDeletedMessages: return strings.nagramiXDeletedMessages
        case .showDeletedMessagesInfo: return strings.nagramiXDeletedMessagesInfo
        case .messageEditHistory: return strings.nagramiXMessageEditHistory
        case .messageEditHistoryInfo: return strings.nagramiXMessageEditHistoryInfo
        case .clearMessageArchive: return strings.nagramiXClearMessageArchive
        case .messageArchiveInfo: return strings.nagramiXLocalArchiveInfo
        case .proxySettings: return strings.nagramiXProxySettings
        case .proxyDns: return strings.nagramiXDns
        case .proxyAutoSwitch: return strings.nagramiXProxyAutoSwitch
        case .proxyCheckAll: return strings.nagramiXProxyCheckAll
        }
    }

    func description(strings: PresentationStrings) -> String {
        switch self {
        case .forceTcpCalls:
            return strings.nagramiXForceTcpCallsInfo
        case .showDeletedMessages:
            return strings.nagramiXDeletedMessagesInfo
        case .messageEditHistory:
            return strings.nagramiXMessageEditHistoryInfo
        case .clearMessageArchive:
            return strings.nagramiXLocalArchiveInfo
        case .proxySettings:
            return [strings.nagramiXDns, strings.nagramiXProxyAutoSwitch, strings.nagramiXProxyCheckAll].joined(separator: " ")
        case .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return strings.nagramiXProxySettings
        default:
            return ""
        }
    }

    func sectionTitle(strings: PresentationStrings) -> String {
        switch self.section {
        case NagramiXSettingsSection.tabs.rawValue: return strings.nagramiXTabsHeader
        case NagramiXSettingsSection.chats.rawValue: return strings.nagramiXChatsHeader
        case NagramiXSettingsSection.videoMessages.rawValue: return strings.nagramiXVideoMessagesHeader
        case NagramiXSettingsSection.stories.rawValue: return strings.nagramiXStoriesHeader
        case NagramiXSettingsSection.profiles.rawValue: return strings.nagramiXProfilesHeader
        case NagramiXSettingsSection.messages.rawValue: return strings.nagramiXMessagesHeader
        case NagramiXSettingsSection.calls.rawValue: return strings.nagramiXCallsHeader
        default: return strings.nagramiXSettingsOther
        }
    }
}

private func nagramiXNormalizedSearchText(_ value: String) -> String {
    return value.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: Locale.current)
        .trimmingCharacters(in: .whitespacesAndNewlines)
}

private func nagramiXSearchEntries(settings: NagramiXTabSettings, strings: PresentationStrings, query: String) -> [NagramiXSettingsEntry] {
    let normalizedQuery = nagramiXNormalizedSearchText(query)
    guard !normalizedQuery.isEmpty else {
        return []
    }

    let matches = nagramiXAllSettingsEntries(settings: settings).filter { entry in
        guard entry.isSearchableSetting else {
            return false
        }
        let searchableText = [
            entry.title(strings: strings),
            entry.description(strings: strings),
            entry.sectionTitle(strings: strings),
            entry.category.title(strings: strings),
        ].joined(separator: " ")
        return nagramiXNormalizedSearchText(searchableText).contains(normalizedQuery)
    }

    var result: [NagramiXSettingsEntry] = []
    var previousGroup: String?
    for entry in matches {
        let groupTitle = "\(entry.category.title(strings: strings)) · \(entry.sectionTitle(strings: strings))"
        if groupTitle != previousGroup {
            result.append(.searchHeader(entry.section, groupTitle))
            previousGroup = groupTitle
        }
        result.append(entry)
    }
    return result
}

private func nagramiXAllSettingsEntries(settings: NagramiXTabSettings) -> [NagramiXSettingsEntry] {
    return [
        .tabsHeader, .hideContacts(settings.hideContacts), .hideCalls(settings.hideCalls),
        .showSearchButton(settings.showSearchButton), .showProxyButton(settings.showProxyButton),
        .hideProxySponsorChannel(settings.hideProxySponsorChannel),
        .chatsHeader, .wideChannelPosts(settings.wideChannelPosts),
        .videoMessagesHeader, .useRearCameraForVideoMessages(settings.useRearCameraForVideoMessages),
        .featureStoriesHeader, .hideStories(settings.hideStories),
        .disableStoryCameraSwipe(settings.disableStoryCameraSwipe),
        .confirmStoryViewing(settings.confirmStoryViewing), .enableStoryRepost(settings.enableStoryRepost),
        .profilesHeader, .showProfileIds(settings.showProfileIds),
        .showRegistrationDate(settings.showRegistrationDate),
        .showMutualContactIcon(settings.showMutualContactIcon),
        .messagesHeader, .showDeletedMessages(settings.showDeletedMessages), .showDeletedMessagesInfo,
        .messageEditHistory(settings.messageEditHistory), .messageEditHistoryInfo,
        .clearMessageArchive, .messageArchiveInfo,
        .callsHeader, .confirmOutgoingCalls(settings.confirmOutgoingCalls),
        .forceTcpCalls(settings.forceTcpCalls), .forceTcpCallsInfo,
        .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll,
    ]
}

private func nagramiXSettingsEntries(settings: NagramiXTabSettings, category: NagramiXSettingsCategory) -> [NagramiXSettingsEntry] {
    return nagramiXAllSettingsEntries(settings: settings).filter { $0.category == category && !$0.isSearchOnly }
}

public func nagramiXSettingsController(context: AccountContext) -> ViewController {
    let settingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let categoryPromise = ValuePromise<NagramiXSettingsCategory>(.interface, ignoreRepeated: true)
    let searchQueryPromise = ValuePromise<String>("", ignoreRepeated: true)
    let searchQueryValue = Atomic<String>(value: "")
    let update: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        settingsPromise.set(NagramiXTabSettings.current)
    }
    var pushControllerImpl: ((ViewController) -> Void)?
    var presentControllerImpl: ((ViewController) -> Void)?
    let arguments = NagramiXSettingsControllerArguments(
        openProxySettings: {
            pushControllerImpl?(proxySettingsController(context: context))
        },
        updateHideContacts: { value in update { $0.hideContacts = value } },
        updateHideCalls: { value in update { $0.hideCalls = value } },
        updateShowSearchButton: { value in update { $0.showSearchButton = value } },
        updateWideChannelPosts: { value in update { $0.wideChannelPosts = value } },
        updateShowProxyButton: { value in update { $0.showProxyButton = value } },
        updateHideProxySponsorChannel: { value in update { $0.hideProxySponsorChannel = value } },
        updateUseRearCameraForVideoMessages: { value in update { $0.useRearCameraForVideoMessages = value } },
        updateHideStories: { value in update { $0.hideStories = value } },
        updateDisableStoryCameraSwipe: { value in update { $0.disableStoryCameraSwipe = value } },
        updateConfirmStoryViewing: { value in update { $0.confirmStoryViewing = value } },
        updateEnableStoryRepost: { value in update { $0.enableStoryRepost = value } },
        updateShowProfileIds: { value in update { $0.showProfileIds = value } },
        updateShowRegistrationDate: { value in update { $0.showRegistrationDate = value } },
        updateShowMutualContactIcon: { value in update { $0.showMutualContactIcon = value } },
        updateConfirmOutgoingCalls: { value in update { $0.confirmOutgoingCalls = value } },
        updateForceTcpCalls: { value in update { $0.forceTcpCalls = value } },
        updateShowDeletedMessages: { value in update { $0.showDeletedMessages = value } },
        updateMessageEditHistory: { value in update { $0.messageEditHistory = value } },
        clearMessageArchive: {
            let strings = context.sharedContext.currentPresentationData.with { $0 }.strings
            presentControllerImpl?(textAlertController(
                context: context,
                title: strings.nagramiXClearMessageArchive,
                text: strings.nagramiXClearMessageArchiveConfirm,
                actions: [
                    TextAlertAction(type: .genericAction, title: strings.nagramiXCancel, action: {}),
                    TextAlertAction(type: .defaultDestructiveAction, title: strings.nagramiXClear, action: {
                        context.account.nagramiXMessageArchive.clearAll()
                    })
                ]
            ))
        }
    )
    let signal = combineLatest(queue: .mainQueue(), context.sharedContext.presentationData, settingsPromise.get(), categoryPromise.get(), searchQueryPromise.get())
    |> map { presentationData, settings, category, searchQuery -> (ItemListControllerState, (ItemListNodeState, Any)) in
        var presentationData = presentationData
        presentationData = presentationData.withUpdated(theme: presentationData.theme.withModalBlocksBackground())
        let normalizedQuery = nagramiXNormalizedSearchText(searchQuery)
        let entries: [NagramiXSettingsEntry]
        if normalizedQuery.isEmpty {
            entries = nagramiXSettingsEntries(settings: settings, category: category)
        } else {
            entries = nagramiXSearchEntries(settings: settings, strings: presentationData.strings, query: normalizedQuery)
        }
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
            entries: entries,
            style: .blocks,
            emptyStateItem: !normalizedQuery.isEmpty && entries.isEmpty ? ItemListTextEmptyStateItem(text: presentationData.strings.nagramiXSettingsSearchNoResults) : nil,
            headerItem: NagramiXSettingsSearchHeaderItem(presentationData: presentationData, query: searchQuery, queryUpdated: { query in
                let _ = searchQueryValue.swap(query)
                searchQueryPromise.set(query)
            }),
            animateChanges: true
        )
        return (controllerState, (listState, arguments))
    }
    let controller = ItemListController(context: context, state: signal)
    pushControllerImpl = { [weak controller] pushedController in
        (controller?.navigationController as? NavigationController)?.pushViewController(pushedController)
    }
    presentControllerImpl = { [weak controller] presentedController in
        controller?.present(presentedController, in: .window(.root))
    }
    controller.attemptNavigation = { [weak controller] _ in
        if !nagramiXNormalizedSearchText(searchQueryValue.with { $0 }).isEmpty {
            let _ = searchQueryValue.swap("")
            searchQueryPromise.set("")
            controller?.view.endEditing(true)
            return false
        }
        return true
    }
    controller.titleControlValueChanged = { index in
        if let category = NagramiXSettingsCategory(rawValue: index) {
            categoryPromise.set(category)
        }
    }
    return controller
}

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
import ComponentFlow
import AlertComponent
import AlertInputFieldComponent
import NagramiXCore
import NagramiXMediaSettings

private struct NagramiXSettingsControllerArguments {
    let openProxySettings: () -> Void
    let updateSearchQuery: (String) -> Void
    let updatePhotoQuality: (Int) -> Void
    let updateSendLargePhotos: (Bool) -> Void
    let updateStickerSize: (Int) -> Void
    let updateShowStickerTime: (Bool) -> Void
    let updateHideContacts: (Bool) -> Void
    let updateHideCalls: (Bool) -> Void
    let updateShowSearchButton: (Bool) -> Void
    let updateWideChannelPosts: (Bool) -> Void
    let updateShowChannelBottomPanel: (Bool) -> Void
    let updateDoubleTapEdit: (Bool) -> Void
    let updateHideReactions: (Bool) -> Void
    let updateCompactChatList: (Bool) -> Void
    let updateChatActionsOnHold: (Bool) -> Void
    let updateShowForwardWithoutAuthor: (Bool) -> Void
    let updateShowBroadcastMessages: (Bool) -> Void
    let updateShowSelectByAuthor: (Bool) -> Void
    let updateShowProxyButton: (Bool) -> Void
    let updateHideProxySponsorChannel: (Bool) -> Void
    let updateVideoPiPSwipe: (Bool) -> Void
    let updateBackgroundVideoPlayback: (Bool) -> Void
    let updateUseRearCameraForVideoMessages: (Bool) -> Void
    let updateHideStories: (Bool) -> Void
    let updateDisableStoryCameraSwipe: (Bool) -> Void
    let updateConfirmStoryViewing: (Bool) -> Void
    let updateEnableStoryRepost: (Bool) -> Void
    let updateAnonymousStoryViewing: (Bool) -> Void
    let updateShowProfileIds: (Bool) -> Void
    let updateShowRegistrationDate: (Bool) -> Void
    let updateShowMutualContactIcon: (Bool) -> Void
    let updateConfirmOutgoingCalls: (Bool) -> Void
    let updateForceTcpCalls: (Bool) -> Void
    let updateShowDeletedMessages: (Bool) -> Void
    let updateSaveTemporaryMessages: (Bool) -> Void
    let editDeletedMessageLabel: () -> Void
    let updateMessageEditHistory: (Bool) -> Void
    let updateDownloadAcceleration: (Bool) -> Void
    let openDownloadAccelerationMode: () -> Void
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
    case contextMenu
    case photos
    case stickers
    case videoPlayback
    case otherVideo
    case downloads
}

private enum NagramiXSettingsEntry: ItemListNodeEntry {
    case search(String, sectionId: ItemListSectionId)
    case noSearchResults
    case searchHeader(Int32, String)
    case tabsHeader
    case hideContacts(Bool)
    case hideCalls(Bool)
    case showSearchButton(Bool)
    case showProxyButton(Bool)
    case hideProxySponsorChannel(Bool)
    case chatsHeader
    case wideChannelPosts(Bool)
    case showChannelBottomPanel(Bool)
    case channelBottomPanelInfo
    case doubleTapEdit(Bool)
    case doubleTapEditInfo
    case hideReactions(Bool)
    case hideReactionsInfo
    case chatActionsOnHold(Bool)
    case chatActionsOnHoldInfo
    case compactChatList(Bool)
    case compactChatListInfo
    case contextMenuHeader
    case showForwardWithoutAuthor(Bool)
    case forwardWithoutAuthorInfo
    case showBroadcastMessages(Bool)
    case broadcastMessagesInfo
    case showSelectByAuthor(Bool)
    case selectByAuthorInfo
    case videoMessagesHeader
    case useRearCameraForVideoMessages(Bool)
    case videoPlaybackHeader
    case backgroundVideoPlayback(Bool)
    case backgroundVideoPlaybackInfo
    case otherVideoHeader
    case videoPiPSwipe(Bool)
    case videoPiPSwipeInfo
    case downloadsHeader
    case downloadAcceleration(Bool)
    case downloadAccelerationMode(NagramiXDownloadAcceleration)
    case downloadAccelerationInfo
    case featureStoriesHeader
    case hideStories(Bool)
    case disableStoryCameraSwipe(Bool)
    case confirmStoryViewing(Bool)
    case enableStoryRepost(Bool)
    case anonymousStoryViewing(Bool)
    case anonymousStoryViewingInfo
    case profilesHeader
    case showProfileIds(Bool)
    case showRegistrationDate(Bool)
    case showMutualContactIcon(Bool)
    case callsHeader
    case confirmOutgoingCalls(Bool)
    case otherCallsHeader
    case forceTcpCalls(Bool)
    case forceTcpCallsInfo
    case messagesHeader
    case showDeletedMessages(Bool)
    case showDeletedMessagesInfo
    case saveTemporaryMessages(Bool)
    case saveTemporaryMessagesInfo
    case deletedMessageLabel(String)
    case messageEditHistory(Bool)
    case messageEditHistoryInfo
    case clearMessageArchive
    case messageArchiveInfo
    case proxySettings
    case proxyDns
    case proxyAutoSwitch
    case proxyCheckAll
    case photosHeader
    case photoQualityHeader
    case photoQuality(Int)
    case photoQualityInfo
    case sendLargePhotos(Bool)
    case sendLargePhotosInfo
    case stickersHeader
    case stickerSizeHeader
    case stickerSize(Int)
    case showStickerTime(Bool)
    case stickerSizeInfo

    var category: NagramiXSettingsCategory {
        switch self {
        case .search, .noSearchResults, .searchHeader:
            return .interface
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel, .chatsHeader, .wideChannelPosts, .showChannelBottomPanel, .channelBottomPanelInfo, .hideReactions, .hideReactionsInfo, .chatActionsOnHold, .chatActionsOnHoldInfo, .compactChatList, .compactChatListInfo,
                .profilesHeader, .showProfileIds, .showRegistrationDate, .showMutualContactIcon,
                .contextMenuHeader, .showForwardWithoutAuthor, .forwardWithoutAuthorInfo, .showBroadcastMessages, .broadcastMessagesInfo, .showSelectByAuthor, .selectByAuthorInfo:
            return .interface
        case .videoMessagesHeader, .useRearCameraForVideoMessages, .featureStoriesHeader, .hideStories, .disableStoryCameraSwipe,
                .confirmStoryViewing, .enableStoryRepost, .anonymousStoryViewing, .anonymousStoryViewingInfo, .callsHeader, .confirmOutgoingCalls:
            return .features
        case .photosHeader, .photoQualityHeader, .photoQuality, .photoQualityInfo, .sendLargePhotos, .sendLargePhotosInfo,
                .stickersHeader, .stickerSizeHeader, .stickerSize, .showStickerTime, .stickerSizeInfo:
            return .features
        case .doubleTapEdit, .doubleTapEditInfo, .messagesHeader, .showDeletedMessages, .showDeletedMessagesInfo, .saveTemporaryMessages, .saveTemporaryMessagesInfo, .deletedMessageLabel, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return .features
        case .videoPlaybackHeader, .backgroundVideoPlayback, .backgroundVideoPlaybackInfo:
            return .features
        case .downloadsHeader, .downloadAcceleration, .downloadAccelerationMode, .downloadAccelerationInfo, .otherVideoHeader, .videoPiPSwipe, .videoPiPSwipeInfo, .otherCallsHeader, .forceTcpCalls, .forceTcpCallsInfo, .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return .other
        }
    }

    var section: ItemListSectionId {
        switch self {
        case let .search(_, sectionId):
            return sectionId
        case .noSearchResults:
            return -1
        case let .searchHeader(sectionId, _):
            return sectionId
        case .tabsHeader, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .hideProxySponsorChannel:
            return NagramiXSettingsSection.tabs.rawValue
        case .chatsHeader, .wideChannelPosts, .showChannelBottomPanel, .channelBottomPanelInfo, .hideReactions, .hideReactionsInfo, .chatActionsOnHold, .chatActionsOnHoldInfo, .compactChatList, .compactChatListInfo:
            return NagramiXSettingsSection.chats.rawValue
        case .contextMenuHeader, .showForwardWithoutAuthor, .forwardWithoutAuthorInfo, .showBroadcastMessages, .broadcastMessagesInfo, .showSelectByAuthor, .selectByAuthorInfo:
            return NagramiXSettingsSection.contextMenu.rawValue
        case .videoMessagesHeader, .useRearCameraForVideoMessages:
            return NagramiXSettingsSection.videoMessages.rawValue
        case .featureStoriesHeader, .hideStories, .disableStoryCameraSwipe, .confirmStoryViewing, .enableStoryRepost, .anonymousStoryViewing, .anonymousStoryViewingInfo:
            return NagramiXSettingsSection.stories.rawValue
        case .profilesHeader, .showProfileIds, .showRegistrationDate, .showMutualContactIcon:
            return NagramiXSettingsSection.profiles.rawValue
        case .callsHeader, .otherCallsHeader, .confirmOutgoingCalls, .forceTcpCalls, .forceTcpCallsInfo:
            return NagramiXSettingsSection.calls.rawValue
        case .doubleTapEdit, .doubleTapEditInfo, .messagesHeader, .showDeletedMessages, .showDeletedMessagesInfo, .saveTemporaryMessages, .saveTemporaryMessagesInfo, .deletedMessageLabel, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return NagramiXSettingsSection.messages.rawValue
        case .photosHeader, .photoQualityHeader, .photoQuality, .photoQualityInfo, .sendLargePhotos, .sendLargePhotosInfo:
            return NagramiXSettingsSection.photos.rawValue
        case .stickersHeader, .stickerSizeHeader, .stickerSize, .showStickerTime, .stickerSizeInfo:
            return NagramiXSettingsSection.stickers.rawValue
        case .videoPlaybackHeader, .backgroundVideoPlayback, .backgroundVideoPlaybackInfo:
            return NagramiXSettingsSection.videoPlayback.rawValue
        case .otherVideoHeader, .videoPiPSwipe, .videoPiPSwipeInfo:
            return NagramiXSettingsSection.otherVideo.rawValue
        case .downloadsHeader, .downloadAcceleration, .downloadAccelerationMode, .downloadAccelerationInfo:
            return NagramiXSettingsSection.downloads.rawValue
        case .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return NagramiXSettingsSection.other.rawValue
        }
    }

    var stableId: Int32 {
        switch self {
        case .search: return -100
        case .noSearchResults: return -99
        case let .searchHeader(id, _): return 1000 + id
        case .tabsHeader: return 0
        case .hideContacts: return 1
        case .hideCalls: return 2
        case .showSearchButton: return 3
        case .showProxyButton: return 4
        case .hideProxySponsorChannel: return 5
        case .chatsHeader: return 6
        case .wideChannelPosts: return 7
        case .showChannelBottomPanel: return 111
        case .channelBottomPanelInfo: return 112
        case .doubleTapEdit: return 113
        case .doubleTapEditInfo: return 114
        case .hideReactions: return 115
        case .hideReactionsInfo: return 116
        case .downloadsHeader: return 117
        case .downloadAcceleration: return 118
        case .downloadAccelerationMode: return 119
        case .downloadAccelerationInfo: return 120
        case .chatActionsOnHold: return 8
        case .chatActionsOnHoldInfo: return 9
        case .compactChatList: return 101
        case .compactChatListInfo: return 102
        case .contextMenuHeader: return 80
        case .showForwardWithoutAuthor: return 81
        case .forwardWithoutAuthorInfo: return 82
        case .showBroadcastMessages: return 121
        case .broadcastMessagesInfo: return 122
        case .showSelectByAuthor: return 83
        case .selectByAuthorInfo: return 84
        case .videoPlaybackHeader: return 105
        case .backgroundVideoPlayback: return 106
        case .backgroundVideoPlaybackInfo: return 107
        case .otherVideoHeader: return 108
        case .videoPiPSwipe: return 109
        case .videoPiPSwipeInfo: return 110
        case .videoMessagesHeader: return 10
        case .useRearCameraForVideoMessages: return 11
        case .hideStories: return 21
        case .featureStoriesHeader: return 25
        case .disableStoryCameraSwipe: return 26
        case .confirmStoryViewing: return 27
        case .enableStoryRepost: return 28
        case .anonymousStoryViewing: return 123
        case .anonymousStoryViewingInfo: return 124
        case .profilesHeader: return 30
        case .showProfileIds: return 31
        case .showRegistrationDate: return 32
        case .showMutualContactIcon: return 33
        case .messagesHeader: return 34
        case .showDeletedMessages: return 35
        case .showDeletedMessagesInfo: return 36
        case .saveTemporaryMessages: return 103
        case .saveTemporaryMessagesInfo: return 104
        case .deletedMessageLabel: return 37
        case .messageEditHistory: return 38
        case .messageEditHistoryInfo: return 39
        case .clearMessageArchive: return 40
        case .messageArchiveInfo: return 41
        case .otherCallsHeader: return 49
        case .callsHeader: return 50
        case .confirmOutgoingCalls: return 51
        case .forceTcpCalls: return 52
        case .forceTcpCallsInfo: return 53
        case .proxySettings: return 60
        case .proxyDns: return 61
        case .proxyAutoSwitch: return 62
        case .proxyCheckAll: return 63
        case .photosHeader: return 90
        case .photoQualityHeader: return 91
        case .photoQuality: return 92
        case .photoQualityInfo: return 93
        case .sendLargePhotos: return 94
        case .sendLargePhotosInfo: return 95
        case .stickersHeader: return 96
        case .stickerSizeHeader: return 97
        case .stickerSize: return 98
        case .showStickerTime: return 99
        case .stickerSizeInfo: return 100
        }
    }

    static func < (lhs: NagramiXSettingsEntry, rhs: NagramiXSettingsEntry) -> Bool {
        // Keep persisted identities unchanged while placing the new rows
        // immediately after the deleted-message option in native list diffs.
        func position(_ entry: NagramiXSettingsEntry) -> Int32 {
            switch entry {
            case .showChannelBottomPanel: return 71
            case .channelBottomPanelInfo: return 72
            case .hideReactions: return 73
            case .hideReactionsInfo: return 74
            case .doubleTapEdit: return 341
            case .doubleTapEditInfo: return 342
            case .videoPlaybackHeader: return 111
            case .backgroundVideoPlayback: return 112
            case .backgroundVideoPlaybackInfo: return 113
            case .otherVideoHeader: return 540
            case .videoPiPSwipe: return 550
            case .videoPiPSwipeInfo: return 560
            case .anonymousStoryViewing: return 281
            case .anonymousStoryViewingInfo: return 282
            case .saveTemporaryMessages: return 365
            case .saveTemporaryMessagesInfo: return 366
            default: return entry.stableId * 10
            }
        }
        return position(lhs) < position(rhs)
    }

    func item(presentationData: ItemListPresentationData, arguments: Any) -> ListViewItem {
        let arguments = arguments as! NagramiXSettingsControllerArguments
        switch self {
        case let .search(query, _):
            return NagramiXSettingsSearchItem(presentationData: presentationData, query: query, sectionId: self.section, queryUpdated: arguments.updateSearchQuery)
        case .noSearchResults:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXSettingsSearchNoResults), sectionId: self.section)
        case let .searchHeader(_, title):
            return ItemListSectionHeaderItem(presentationData: presentationData, text: title.uppercased(), sectionId: self.section)
        case .tabsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXTabsHeader.uppercased(), sectionId: self.section)
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
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXChatsHeader.uppercased(), sectionId: self.section)
        case let .wideChannelPosts(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXWideChannelPosts, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateWideChannelPosts)
        case let .showChannelBottomPanel(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXChannelBottomPanel, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowChannelBottomPanel)
        case .channelBottomPanelInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXChannelBottomPanelInfo), sectionId: self.section)
        case let .doubleTapEdit(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDoubleTapEdit, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateDoubleTapEdit)
        case .doubleTapEditInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXDoubleTapEditInfo), sectionId: self.section)
        case let .hideReactions(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideReactions, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideReactions)
        case .hideReactionsInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXHideReactionsInfo), sectionId: self.section)
        case let .chatActionsOnHold(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXChatActionsOnHold, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateChatActionsOnHold)
        case .chatActionsOnHoldInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXChatActionsOnHoldInfo), sectionId: self.section)
        case let .compactChatList(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXCompactChatList, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateCompactChatList)
        case .compactChatListInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXCompactChatListInfo), sectionId: self.section)
        case .contextMenuHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXContextMenuHeader.uppercased(), sectionId: self.section)
        case let .showForwardWithoutAuthor(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXForwardWithoutAuthor, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowForwardWithoutAuthor)
        case .forwardWithoutAuthorInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXForwardWithoutAuthorInfo), sectionId: self.section)
        case let .showBroadcastMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXBroadcastMessages, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowBroadcastMessages)
        case .broadcastMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXBroadcastMessagesInfo), sectionId: self.section)
        case let .showSelectByAuthor(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSelectFromAuthor, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowSelectByAuthor)
        case .selectByAuthorInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXSelectByAuthorInfo), sectionId: self.section)
        case .videoMessagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoMessagesHeader.uppercased(), sectionId: self.section)
        case let .useRearCameraForVideoMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUseRearCamera, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateUseRearCameraForVideoMessages)
        case .videoPlaybackHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoPlaybackHeader.uppercased(), sectionId: self.section)
        case let .backgroundVideoPlayback(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXBackgroundVideoPlayback, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateBackgroundVideoPlayback)
        case .backgroundVideoPlaybackInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXBackgroundVideoPlaybackInfo), sectionId: self.section)
        case .downloadsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXDownloadsHeader.uppercased(), sectionId: self.section)
        case let .downloadAcceleration(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDownloadAcceleration, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateDownloadAcceleration)
        case let .downloadAccelerationMode(mode):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDownloadAccelerationMode, label: nagramiXDownloadModeTitle(mode, strings: presentationData.strings), sectionId: self.section, style: .blocks, action: arguments.openDownloadAccelerationMode)
        case .downloadAccelerationInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXDownloadAccelerationInfo), sectionId: self.section)
        case .otherVideoHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXSettingsOther.uppercased(), sectionId: self.section)
        case let .videoPiPSwipe(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXVideoPiPSwipe, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateVideoPiPSwipe)
        case .videoPiPSwipeInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXVideoPiPSwipeInfo), sectionId: self.section)
        case let .anonymousStoryViewing(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAnonymousStoryViewing, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateAnonymousStoryViewing)
        case .anonymousStoryViewingInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXAnonymousStoryViewingInfo), sectionId: self.section)
        case .featureStoriesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXStoriesHeader.uppercased(), sectionId: self.section)
        case let .hideStories(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideStories, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateHideStories)
        case let .disableStoryCameraSwipe(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDisableStoryCameraSwipe, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateDisableStoryCameraSwipe)
        case let .confirmStoryViewing(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmStoryViewing, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmStoryViewing)
        case let .enableStoryRepost(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXEnableStoryRepost, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateEnableStoryRepost)
        case .profilesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXProfilesHeader.uppercased(), sectionId: self.section)
        case let .showProfileIds(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowProfileIds, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowProfileIds)
        case let .showRegistrationDate(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowRegistrationDate, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowRegistrationDate)
        case let .showMutualContactIcon(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowMutualContactIcon, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowMutualContactIcon)
        case .callsHeader, .otherCallsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXCallsHeader.uppercased(), sectionId: self.section)
        case let .confirmOutgoingCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmOutgoingCalls, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmOutgoingCalls)
        case let .forceTcpCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXForceTcpCalls, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateForceTcpCalls)
        case .forceTcpCallsInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXForceTcpCallsInfo), sectionId: self.section)
        case .messagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXMessagesHeader.uppercased(), sectionId: self.section)
        case let .showDeletedMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletedMessages, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateShowDeletedMessages)
        case .showDeletedMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXDeletedMessagesInfo), sectionId: self.section)
        case let .saveTemporaryMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXTemporaryMessages, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSaveTemporaryMessages)
        case .saveTemporaryMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXTemporaryMessagesInfo), sectionId: self.section)
        case let .deletedMessageLabel(label):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletedMessageLabel, label: label.isEmpty ? presentationData.strings.nagramiXDeleted : label, sectionId: self.section, style: .blocks, action: arguments.editDeletedMessageLabel)
        case let .messageEditHistory(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXMessageEditHistory, value: value, sectionId: self.section, style: .blocks, updated: arguments.updateMessageEditHistory)
        case .messageEditHistoryInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXMessageEditHistoryInfo), sectionId: self.section)
        case .clearMessageArchive:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXClearMessageArchive, label: "", sectionId: self.section, style: .blocks, action: arguments.clearMessageArchive)
        case .messageArchiveInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXLocalArchiveInfo), sectionId: self.section)
        case .photosHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXPhotosHeader.uppercased(), sectionId: self.section)
        case .photoQualityHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXPhotoQuality.uppercased(), sectionId: self.section)
        case let .photoQuality(value):
            return NagramiXPercentageItem(presentationData: presentationData, title: presentationData.strings.nagramiXPhotoQuality, value: value, sectionId: self.section, updated: arguments.updatePhotoQuality)
        case .photoQualityInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXPhotoQualityInfo), sectionId: self.section)
        case let .sendLargePhotos(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSendLargePhotos, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSendLargePhotos)
        case .sendLargePhotosInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXSendLargePhotosInfo), sectionId: self.section)
        case .stickersHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXStickersHeader.uppercased(), sectionId: self.section)
        case .stickerSizeHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXStickerSize.uppercased(), sectionId: self.section)
        case let .stickerSize(value):
            return NagramiXPercentageItem(presentationData: presentationData, title: presentationData.strings.nagramiXStickerSize, value: value, sectionId: self.section, updated: arguments.updateStickerSize)
        case let .showStickerTime(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowStickerTime, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowStickerTime)
        case .stickerSizeInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXStickerSizeInfo), sectionId: self.section)
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
        case .search, .noSearchResults, .searchHeader, .proxyDns, .proxyAutoSwitch, .proxyCheckAll:
            return true
        default:
            return false
        }
    }

    var isSearchableSetting: Bool {
        switch self {
        case .search, .noSearchResults, .searchHeader, .tabsHeader, .chatsHeader, .videoMessagesHeader, .featureStoriesHeader, .profilesHeader, .callsHeader, .otherCallsHeader, .messagesHeader,
                .anonymousStoryViewingInfo, .forceTcpCallsInfo, .showDeletedMessagesInfo, .saveTemporaryMessagesInfo, .messageEditHistoryInfo, .messageArchiveInfo,
                .doubleTapEditInfo, .hideReactionsInfo, .channelBottomPanelInfo, .contextMenuHeader, .forwardWithoutAuthorInfo, .broadcastMessagesInfo, .selectByAuthorInfo, .chatActionsOnHoldInfo, .compactChatListInfo,
                .photosHeader, .photoQualityHeader, .photoQualityInfo, .sendLargePhotosInfo,
                .stickersHeader, .stickerSizeHeader, .stickerSizeInfo,
                .downloadsHeader, .downloadAccelerationInfo, .videoPlaybackHeader, .backgroundVideoPlaybackInfo, .otherVideoHeader, .videoPiPSwipeInfo:
            return false
        default:
            return true
        }
    }

    func title(strings: PresentationStrings) -> String {
        switch self {
        case .search: return strings.nagramiXSettingsSearch
        case .noSearchResults: return strings.nagramiXSettingsSearchNoResults
        case let .searchHeader(_, title): return title
        case .tabsHeader: return strings.nagramiXTabsHeader
        case .hideContacts: return strings.nagramiXHideContactsTab
        case .hideCalls: return strings.nagramiXHideCallsTab
        case .showSearchButton: return strings.nagramiXShowSearchButton
        case .showProxyButton: return strings.nagramiXShowProxyButton
        case .hideProxySponsorChannel: return strings.nagramiXHideProxySponsorChannel
        case .chatsHeader: return strings.nagramiXChatsHeader
        case .wideChannelPosts: return strings.nagramiXWideChannelPosts
        case .showChannelBottomPanel: return strings.nagramiXChannelBottomPanel
        case .channelBottomPanelInfo: return strings.nagramiXChannelBottomPanelInfo
        case .doubleTapEdit: return strings.nagramiXDoubleTapEdit
        case .doubleTapEditInfo: return strings.nagramiXDoubleTapEditInfo
        case .hideReactions: return strings.nagramiXHideReactions
        case .hideReactionsInfo: return strings.nagramiXHideReactionsInfo
        case .downloadsHeader: return strings.nagramiXDownloadsHeader
        case .downloadAcceleration: return strings.nagramiXDownloadAcceleration
        case .downloadAccelerationMode: return strings.nagramiXDownloadAccelerationMode
        case .downloadAccelerationInfo: return strings.nagramiXDownloadAccelerationInfo
        case .chatActionsOnHold: return strings.nagramiXChatActionsOnHold
        case .chatActionsOnHoldInfo: return strings.nagramiXChatActionsOnHoldInfo
        case .compactChatList: return strings.nagramiXCompactChatList
        case .compactChatListInfo: return strings.nagramiXCompactChatListInfo
        case .contextMenuHeader: return strings.nagramiXContextMenuHeader
        case .showForwardWithoutAuthor: return strings.nagramiXForwardWithoutAuthor
        case .forwardWithoutAuthorInfo: return strings.nagramiXForwardWithoutAuthorInfo
        case .showBroadcastMessages: return strings.nagramiXBroadcastMessages
        case .broadcastMessagesInfo: return strings.nagramiXBroadcastMessagesInfo
        case .showSelectByAuthor: return strings.nagramiXSelectFromAuthor
        case .selectByAuthorInfo: return strings.nagramiXSelectByAuthorInfo
        case .videoMessagesHeader: return strings.nagramiXVideoMessagesHeader
        case .useRearCameraForVideoMessages: return strings.nagramiXUseRearCamera
        case .videoPlaybackHeader: return strings.nagramiXVideoPlaybackHeader
        case .backgroundVideoPlayback: return strings.nagramiXBackgroundVideoPlayback
        case .backgroundVideoPlaybackInfo: return strings.nagramiXBackgroundVideoPlaybackInfo
        case .otherVideoHeader: return strings.nagramiXSettingsOther
        case .videoPiPSwipe: return strings.nagramiXVideoPiPSwipe
        case .videoPiPSwipeInfo: return strings.nagramiXVideoPiPSwipeInfo
        case .featureStoriesHeader: return strings.nagramiXStoriesHeader
        case .hideStories: return strings.nagramiXHideStories
        case .disableStoryCameraSwipe: return strings.nagramiXDisableStoryCameraSwipe
        case .confirmStoryViewing: return strings.nagramiXConfirmStoryViewing
        case .enableStoryRepost: return strings.nagramiXEnableStoryRepost
        case .anonymousStoryViewing: return strings.nagramiXAnonymousStoryViewing
        case .anonymousStoryViewingInfo: return strings.nagramiXAnonymousStoryViewingInfo
        case .profilesHeader: return strings.nagramiXProfilesHeader
        case .showProfileIds: return strings.nagramiXShowProfileIds
        case .showRegistrationDate: return strings.nagramiXShowRegistrationDate
        case .showMutualContactIcon: return strings.nagramiXShowMutualContactIcon
        case .callsHeader, .otherCallsHeader: return strings.nagramiXCallsHeader
        case .confirmOutgoingCalls: return strings.nagramiXConfirmOutgoingCalls
        case .forceTcpCalls: return strings.nagramiXForceTcpCalls
        case .forceTcpCallsInfo: return strings.nagramiXForceTcpCallsInfo
        case .messagesHeader: return strings.nagramiXMessagesHeader
        case .showDeletedMessages: return strings.nagramiXDeletedMessages
        case .showDeletedMessagesInfo: return strings.nagramiXDeletedMessagesInfo
        case .saveTemporaryMessages: return strings.nagramiXTemporaryMessages
        case .saveTemporaryMessagesInfo: return strings.nagramiXTemporaryMessagesInfo
        case .deletedMessageLabel: return strings.nagramiXDeletedMessageLabel
        case .messageEditHistory: return strings.nagramiXMessageEditHistory
        case .messageEditHistoryInfo: return strings.nagramiXMessageEditHistoryInfo
        case .clearMessageArchive: return strings.nagramiXClearMessageArchive
        case .messageArchiveInfo: return strings.nagramiXLocalArchiveInfo
        case .proxySettings: return strings.nagramiXProxySettings
        case .proxyDns: return strings.nagramiXDns
        case .proxyAutoSwitch: return strings.nagramiXProxyAutoSwitch
        case .proxyCheckAll: return strings.nagramiXProxyCheckAll
        case .photosHeader: return strings.nagramiXPhotosHeader
        case .photoQualityHeader: return strings.nagramiXPhotoQuality
        case .photoQuality: return strings.nagramiXPhotoQuality
        case .photoQualityInfo: return strings.nagramiXPhotoQualityInfo
        case .sendLargePhotos: return strings.nagramiXSendLargePhotos
        case .sendLargePhotosInfo: return strings.nagramiXSendLargePhotosInfo
        case .stickersHeader: return strings.nagramiXStickersHeader
        case .stickerSizeHeader: return strings.nagramiXStickerSize
        case .stickerSize: return strings.nagramiXStickerSize
        case .showStickerTime: return strings.nagramiXShowStickerTime
        case .stickerSizeInfo: return strings.nagramiXStickerSizeInfo
        }
    }

    func description(strings: PresentationStrings) -> String {
        switch self {
        case .downloadAcceleration, .downloadAccelerationMode:
            return strings.nagramiXDownloadAccelerationInfo
        case .doubleTapEdit:
            return strings.nagramiXDoubleTapEditInfo
        case .hideReactions:
            return strings.nagramiXHideReactionsInfo
        case .showChannelBottomPanel:
            return strings.nagramiXChannelBottomPanelInfo
        case .backgroundVideoPlayback:
            return strings.nagramiXBackgroundVideoPlaybackInfo
        case .videoPiPSwipe:
            return strings.nagramiXVideoPiPSwipeInfo
        case .photoQuality:
            return strings.nagramiXPhotoQualityInfo
        case .sendLargePhotos:
            return strings.nagramiXSendLargePhotosInfo
        case .stickerSize, .showStickerTime:
            return strings.nagramiXStickerSizeInfo
        case .compactChatList:
            return strings.nagramiXCompactChatListInfo
        case .chatActionsOnHold:
            return strings.nagramiXChatActionsOnHoldInfo
        case .showForwardWithoutAuthor:
            return strings.nagramiXForwardWithoutAuthorInfo
        case .showBroadcastMessages:
            return strings.nagramiXBroadcastMessagesInfo
        case .showSelectByAuthor:
            return strings.nagramiXSelectByAuthorInfo
        case .anonymousStoryViewing:
            return strings.nagramiXAnonymousStoryViewingInfo
        case .forceTcpCalls:
            return strings.nagramiXForceTcpCallsInfo
        case .showDeletedMessages:
            return strings.nagramiXDeletedMessagesInfo
        case .saveTemporaryMessages:
            return strings.nagramiXTemporaryMessagesInfo
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
        case NagramiXSettingsSection.contextMenu.rawValue: return strings.nagramiXContextMenuHeader
        case NagramiXSettingsSection.videoMessages.rawValue: return strings.nagramiXVideoMessagesHeader
        case NagramiXSettingsSection.stories.rawValue: return strings.nagramiXStoriesHeader
        case NagramiXSettingsSection.profiles.rawValue: return strings.nagramiXProfilesHeader
        case NagramiXSettingsSection.messages.rawValue: return strings.nagramiXMessagesHeader
        case NagramiXSettingsSection.calls.rawValue: return strings.nagramiXCallsHeader
        case NagramiXSettingsSection.photos.rawValue: return strings.nagramiXPhotosHeader
        case NagramiXSettingsSection.videoPlayback.rawValue: return strings.nagramiXVideoPlaybackHeader
        case NagramiXSettingsSection.otherVideo.rawValue: return strings.nagramiXSettingsOther
        case NagramiXSettingsSection.stickers.rawValue: return strings.nagramiXStickersHeader
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

private func nagramiXDownloadModeTitle(_ mode: NagramiXDownloadAcceleration, strings: PresentationStrings) -> String {
    switch mode {
    case .standard, .medium: return strings.nagramiXDownloadMedium
    case .maximum: return strings.nagramiXDownloadMaximum
    }
}

private func nagramiXAllSettingsEntries(settings: NagramiXTabSettings) -> [NagramiXSettingsEntry] {
    var downloadEntries: [NagramiXSettingsEntry] = [.downloadsHeader, .downloadAcceleration(settings.downloads.enabled)]
    if settings.downloads.enabled {
        downloadEntries.append(.downloadAccelerationMode(settings.downloads.mode))
    }
    downloadEntries.append(.downloadAccelerationInfo)
    return [
        .tabsHeader, .hideContacts(settings.hideContacts), .hideCalls(settings.hideCalls),
        .showSearchButton(settings.showSearchButton), .showProxyButton(settings.showProxyButton),
        .hideProxySponsorChannel(settings.hideProxySponsorChannel),
        .chatsHeader, .wideChannelPosts(settings.wideChannelPosts),
        .showChannelBottomPanel(settings.showChannelBottomPanel), .channelBottomPanelInfo,
        .hideReactions(settings.hideReactions), .hideReactionsInfo,
        .chatActionsOnHold(settings.chatActionsOnHold), .chatActionsOnHoldInfo,
        .compactChatList(settings.compactChatList), .compactChatListInfo,
        .videoMessagesHeader, .useRearCameraForVideoMessages(settings.useRearCameraForVideoMessages),
        .videoPlaybackHeader, .backgroundVideoPlayback(settings.backgroundVideoPlayback), .backgroundVideoPlaybackInfo,
        .featureStoriesHeader, .hideStories(settings.hideStories),
        .disableStoryCameraSwipe(settings.disableStoryCameraSwipe),
        .confirmStoryViewing(settings.confirmStoryViewing), .enableStoryRepost(settings.enableStoryRepost),
        .anonymousStoryViewing(settings.anonymousStoryViewing), .anonymousStoryViewingInfo,
        .profilesHeader, .showProfileIds(settings.showProfileIds),
        .showRegistrationDate(settings.showRegistrationDate),
        .showMutualContactIcon(settings.showMutualContactIcon),
        .contextMenuHeader, .showForwardWithoutAuthor(settings.showForwardWithoutAuthor), .forwardWithoutAuthorInfo,
        .showBroadcastMessages(settings.showBroadcastMessages), .broadcastMessagesInfo,
        .showSelectByAuthor(settings.showSelectByAuthor), .selectByAuthorInfo,
        .messagesHeader, .doubleTapEdit(settings.doubleTapEdit), .doubleTapEditInfo,
        .showDeletedMessages(settings.showDeletedMessages), .showDeletedMessagesInfo,
        .saveTemporaryMessages(settings.saveTemporaryMessages), .saveTemporaryMessagesInfo,
        .deletedMessageLabel(settings.deletedMessageLabel),
        .messageEditHistory(settings.messageEditHistory), .messageEditHistoryInfo,
        .clearMessageArchive, .messageArchiveInfo,
        .callsHeader, .confirmOutgoingCalls(settings.confirmOutgoingCalls),
        .photosHeader, .photoQualityHeader, .photoQuality(settings.media.photoQuality), .photoQualityInfo,
        .sendLargePhotos(settings.media.sendLargePhotos), .sendLargePhotosInfo,
        .stickersHeader, .stickerSizeHeader, .stickerSize(settings.media.stickerSize),
        .showStickerTime(settings.media.showStickerTime), .stickerSizeInfo,
        .otherCallsHeader, .forceTcpCalls(settings.forceTcpCalls), .forceTcpCallsInfo,
        .otherVideoHeader, .videoPiPSwipe(settings.videoPiPSwipe), .videoPiPSwipeInfo,
        .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll,
    ] + downloadEntries
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
        updateSearchQuery: { query in
            let _ = searchQueryValue.swap(query)
            searchQueryPromise.set(query)
        },
        updatePhotoQuality: { value in update { $0.media.photoQuality = value } },
        updateSendLargePhotos: { value in update { $0.media.sendLargePhotos = value } },
        updateStickerSize: { value in update { $0.media.stickerSize = value } },
        updateShowStickerTime: { value in update { $0.media.showStickerTime = value } },
        updateHideContacts: { value in update { $0.hideContacts = value } },
        updateHideCalls: { value in update { $0.hideCalls = value } },
        updateShowSearchButton: { value in update { $0.showSearchButton = value } },
        updateWideChannelPosts: { value in update { $0.wideChannelPosts = value } },
        updateShowChannelBottomPanel: { value in update { $0.showChannelBottomPanel = value } },
        updateDoubleTapEdit: { value in update { $0.doubleTapEdit = value } },
        updateHideReactions: { value in update { $0.hideReactions = value } },
        updateCompactChatList: { value in update { $0.compactChatList = value } },
        updateChatActionsOnHold: { value in update { $0.chatActionsOnHold = value } },
        updateShowForwardWithoutAuthor: { value in update { $0.showForwardWithoutAuthor = value } },
        updateShowBroadcastMessages: { value in update { $0.showBroadcastMessages = value } },
        updateShowSelectByAuthor: { value in update { $0.showSelectByAuthor = value } },
        updateShowProxyButton: { value in update { $0.showProxyButton = value } },
        updateHideProxySponsorChannel: { value in update { $0.hideProxySponsorChannel = value } },
        updateVideoPiPSwipe: { value in update { $0.videoPiPSwipe = value } },
        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },
        updateUseRearCameraForVideoMessages: { value in update { $0.useRearCameraForVideoMessages = value } },
        updateHideStories: { value in update { $0.hideStories = value } },
        updateDisableStoryCameraSwipe: { value in update { $0.disableStoryCameraSwipe = value } },
        updateConfirmStoryViewing: { value in update { $0.confirmStoryViewing = value } },
        updateEnableStoryRepost: { value in update { $0.enableStoryRepost = value } },
        updateAnonymousStoryViewing: { value in update { $0.anonymousStoryViewing = value } },
        updateShowProfileIds: { value in update { $0.showProfileIds = value } },
        updateShowRegistrationDate: { value in update { $0.showRegistrationDate = value } },
        updateShowMutualContactIcon: { value in update { $0.showMutualContactIcon = value } },
        updateConfirmOutgoingCalls: { value in update { $0.confirmOutgoingCalls = value } },
        updateForceTcpCalls: { value in update { $0.forceTcpCalls = value } },
        updateShowDeletedMessages: { value in update { $0.showDeletedMessages = value } },
        updateSaveTemporaryMessages: { value in update { $0.saveTemporaryMessages = value } },
        editDeletedMessageLabel: {
            let presentationData = context.sharedContext.currentPresentationData.with { $0 }
            let inputState = AlertInputFieldComponent.ExternalState()
            var applyImpl: (() -> Void)?
            let content: [AnyComponentWithIdentity<AlertComponentEnvironment>] = [
                AnyComponentWithIdentity(id: "title", component: AnyComponent(AlertTitleComponent(title: presentationData.strings.nagramiXDeletedMessageLabelEditor))),
                AnyComponentWithIdentity(id: "input", component: AnyComponent(AlertInputFieldComponent(
                    context: context,
                    initialValue: NagramiXTabSettings.current.deletedMessageLabel.isEmpty ? presentationData.strings.nagramiXDeleted : NagramiXTabSettings.current.deletedMessageLabel,
                    placeholder: presentationData.strings.nagramiXDeleted,
                    characterLimit: 64,
                    hasClearButton: true,
                    keyboardType: .default,
                    autocapitalizationType: .sentences,
                    autocorrectionType: .yes,
                    isInitiallyFocused: true,
                    externalState: inputState,
                    shouldChangeText: { value in
                        return !value.contains("\n") && !value.contains("\r")
                    },
                    returnKeyAction: {
                        applyImpl?()
                    }
                )))
            ]
            let alertController = AlertScreen(
                configuration: AlertScreen.Configuration(allowInputInset: true),
                content: content,
                actions: [
                    .init(title: presentationData.strings.Common_Cancel),
                    .init(title: presentationData.strings.nagramiXSave, type: .default, action: {
                        applyImpl?()
                    }, autoDismiss: false)
                ],
                updatedPresentationData: (presentationData, context.sharedContext.presentationData)
            )
            applyImpl = {
                update { settings in
                    let normalized = NagramiXTabSettings.normalizedDeletedMessageLabel(inputState.value)
                    settings.deletedMessageLabel = normalized == presentationData.strings.nagramiXDeleted ? "" : normalized
                }
                alertController.dismiss()
            }
            presentControllerImpl?(alertController)
        },
        updateMessageEditHistory: { value in update { $0.messageEditHistory = value } },
        updateDownloadAcceleration: { value in update { $0.downloads.enabled = value } },
        openDownloadAccelerationMode: {
            let current = NagramiXTabSettings.current.downloads
            guard current.enabled else {
                return
            }
            let presentationData = context.sharedContext.currentPresentationData.with { $0 }
            let actionSheet = ActionSheetController(presentationData: presentationData)
            let modes: [NagramiXDownloadAcceleration] = [.medium, .maximum]
            let items: [ActionSheetItem] = modes.map { mode in
                ActionSheetCheckboxItem(title: nagramiXDownloadModeTitle(mode, strings: presentationData.strings), label: "", value: current.mode == mode, style: .alignRight, action: { [weak actionSheet] _ in
                    actionSheet?.dismissAnimated()
                    update { $0.downloads.mode = mode }
                })
            }
            actionSheet.setItemGroups([ActionSheetItemGroup(items: items)])
            presentControllerImpl?(actionSheet)
        },
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
        let normalizedQuery = nagramiXNormalizedSearchText(searchQuery)
        var resultEntries: [NagramiXSettingsEntry]
        if normalizedQuery.isEmpty {
            resultEntries = nagramiXSettingsEntries(settings: settings, category: category)
        } else {
            resultEntries = nagramiXSearchEntries(settings: settings, strings: presentationData.strings, query: normalizedQuery)
            if resultEntries.isEmpty {
                resultEntries = [.noSearchResults]
            }
        }
        // Share the first section to avoid the native 28 pt inter-section gap
        // between the search field and its first heading.
        let searchSectionId = resultEntries.first?.section ?? -1
        let entries: [NagramiXSettingsEntry] = [.search(searchQuery, sectionId: searchSectionId)] + resultEntries
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
            emptyStateItem: nil,
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

// Editing an archived snapshot never invokes Telegram's server edit operation.
public func nagramiXEditArchivedMessage(context: AccountContext, message: EngineRawMessage, present: @escaping (ViewController) -> Void) {
    let presentationData = context.sharedContext.currentPresentationData.with { $0 }
    let inputState = AlertInputFieldComponent.ExternalState()
    var applyImpl: (() -> Void)?
    let content: [AnyComponentWithIdentity<AlertComponentEnvironment>] = [
        AnyComponentWithIdentity(id: "title", component: AnyComponent(AlertTitleComponent(title: presentationData.strings.nagramiXEditLocalCopy))),
        AnyComponentWithIdentity(id: "input", component: AnyComponent(AlertInputFieldComponent(
            context: context,
            initialValue: message.text,
            placeholder: "",
            characterLimit: 4096,
            hasClearButton: true,
            keyboardType: .default,
            autocapitalizationType: .sentences,
            autocorrectionType: .yes,
            isInitiallyFocused: true,
            externalState: inputState,
            shouldChangeText: { _ in true },
            returnKeyAction: { applyImpl?() }
        )))
    ]
    let alertController = AlertScreen(
        configuration: AlertScreen.Configuration(allowInputInset: true),
        content: content,
        actions: [
            .init(title: presentationData.strings.Common_Cancel),
            .init(title: presentationData.strings.nagramiXSave, type: .default, action: { applyImpl?() }, autoDismiss: false)
        ],
        updatedPresentationData: (presentationData, context.sharedContext.presentationData)
    )
    applyImpl = {
        context.account.nagramiXMessageArchive.updateDeletedMessageText(id: message.id, text: inputState.value)
        alertController.dismiss()
    }
    present(alertController)
}

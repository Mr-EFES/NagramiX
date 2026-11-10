import Foundation
import UIKit
import Display
import SwiftSignalKit
import TelegramPresentationData
import TelegramUIPreferences
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
import TranslateUI
import NagramiXTranscription

private struct NagramiXSettingsControllerArguments {
    let updateTranscription: (Bool) -> Void
    let openTranscription: () -> Void
    let updateTranslation: (Bool) -> Void
    let openTranslation: () -> Void
    let roundQualityChanged: (Bool) -> Void
    let openRoundQuality: () -> Void
    let openProxySettings: () -> Void
    let updateReadMode: (NagramiXReadMode, Bool) -> Void
    let updateSearchQuery: (String) -> Void
    let updatePhotoQuality: (Int) -> Void
    let updateHighQualityPhotos: (Bool) -> Void
    let updateOriginalVideos: (Bool) -> Void
    let updateStickerSize: (Int) -> Void
    let updateShowStickerTime: (Bool) -> Void
    let updateWideTabBar: (Bool) -> Void
    let updateHideContacts: (Bool) -> Void
    let updateHideCalls: (Bool) -> Void
    let updateShowSearchButton: (Bool) -> Void
    let updateWideChannelPosts: (Bool) -> Void
    let updateShowChannelBottomPanel: (Bool) -> Void
    let updateDoubleTapEdit: (Bool) -> Void
    let updateHideReactions: (Bool) -> Void
    let updateHideGreetingSticker: (Bool) -> Void
    let updateHidePremiumOffers: (Bool) -> Void
    let updateUnreadChatsFirst: (Bool) -> Void
    let updateCompactChatList: (Bool) -> Void
    let updateNumberRounding: (Bool) -> Void
    let updateDeletionEffect: (Bool) -> Void
    let updateDisableNextSwipe: (Bool) -> Void
    let updateChatActionsOnHold: (Bool) -> Void
    let updateShowForwardWithoutAuthor: (Bool) -> Void
    let updateShowBroadcastMessages: (Bool) -> Void
    let updateShowSelectByAuthor: (Bool) -> Void
    let updateContextTranscribe: (Bool) -> Void
    let updateContextTranslate: (Bool) -> Void
    let updateShowProxyButton: (Bool) -> Void
    let updateShowAdvertising: (Bool) -> Void
    let updateVideoPiPSwipe: (Bool) -> Void
    let updateBackgroundVideoPlayback: (Bool) -> Void
    let updateRoundVideo: (Bool) -> Void
    let updateSelfieCountdown: (Bool) -> Void
    let updateUseRearCameraForVideoMessages: (Bool) -> Void
    let updateViewOnceRecording: (Bool) -> Void
    let updateKeepMusicPlayingWhileRecording: (Bool) -> Void
    let updateHideStories: (Bool) -> Void
    let updateStoryCameraSwipeEnabled: (Bool) -> Void
    let updateConfirmStoryViewing: (Bool) -> Void
    let updateEnableStoryRepost: (Bool) -> Void
    let updateDownloadStories: (Bool) -> Void
    let updatePrivacyOption: (NagramiXPrivacySettings.Option, Bool) -> Void
    let updateShowProfileIds: (Bool) -> Void
    let updateShowExactLastSeen: (Bool) -> Void
    let updateShowRegistrationDate: (Bool) -> Void
    let updateShowMutualContactIcon: (Bool) -> Void
    let updateConfirmOutgoingCalls: (Bool) -> Void
    let updateSkipCallRating: (Bool) -> Void
    let updateForceTcpCalls: (Bool) -> Void
    let updateShowDeletedMessages: (Bool) -> Void
    let updateAnonymousStickers: (Bool) -> Void
    let updateHideBlockedMessages: (Bool) -> Void
    let updateAutoRevealSpoilers: (Bool) -> Void
    let updateQuickFormatting: (Bool) -> Void
    let updateSendSilently: (Bool) -> Void
    let updateAntiCaps: (Bool) -> Void
    let updateVoiceAutoplay: (Bool) -> Void
    let updateAutoMuteNewChannels: (Bool) -> Void
    let updateSaveTemporaryMessages: (Bool) -> Void
    let updateReplayViewOnce: (Bool) -> Void
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

    func adjacent(isNext: Bool) -> NagramiXSettingsCategory? {
        return NagramiXSettingsCategory(rawValue: self.rawValue + (isNext ? 1 : -1))
    }
}

private final class NagramiXSettingsSwipeController: ItemListController, UIGestureRecognizerDelegate {
    var categorySwipeAllowedDirections: (() -> InteractiveTransitionGestureRecognizerDirections)?
    var categorySwiped: ((Bool) -> Void)?

    override func loadDisplayNode() {
        super.loadDisplayNode()

        // Use the same directional filtering and horizontal-control exclusions
        // as Telegram's interactive transitions, scoped to this settings screen.
        let gesture = InteractiveTransitionGestureRecognizer(target: self, action: #selector(self.categorySwipe(_:)), allowedDirections: { [weak self] point in
            guard let self, point.x >= 24.0 else {
                return []
            }
            return self.categorySwipeAllowedDirections?() ?? []
        }, edgeWidth: .constant(24.0))
        gesture.delegate = self
        gesture.cancelsTouchesInView = true
        self.displayNode.view.addGestureRecognizer(gesture)
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
        // Switches, sliders and editable search text keep their own gestures.
        var view = touch.view
        while let current = view {
            if current is UIControl || current is UITextView {
                return false
            }
            if current === self.displayNode.view {
                break
            }
            view = current.superview
        }
        return true
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        // Central swipes belong to categories. At the left edge this recognizer
        // fails immediately, leaving the native back gesture available.
        return otherGestureRecognizer is InteractiveTransitionGestureRecognizer
    }

    @objc private func categorySwipe(_ gesture: UIPanGestureRecognizer) {
        guard gesture.state == .ended else {
            return
        }
        let translation = gesture.translation(in: self.displayNode.view)
        guard abs(translation.x) > abs(translation.y) * 1.5 else {
            return
        }
        let velocity = gesture.velocity(in: self.displayNode.view).x
        let distance = max(44.0, min(80.0, self.displayNode.bounds.width * 0.16))
        let isQuickSwipe = abs(translation.x) >= 16.0 && abs(velocity) >= 550.0 && translation.x * velocity > 0.0
        guard abs(translation.x) >= distance || isQuickSwipe else {
            return
        }
        self.categorySwiped?(translation.x < 0.0)
    }
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
    case privacy
    case roundQualitySettings
    case translationSettings
    case transcriptionSettings
}

private enum NagramiXSettingsEntry: ItemListNodeEntry {
    case search(String, sectionId: ItemListSectionId)
    case noSearchResults
    case privacyHeader
    case privacyToggle(NagramiXPrivacySettings.Option, Bool)
    case readLocally(Bool)
    case searchHeader(Int32, String)
    case tabsHeader
    case wideTabBar(Bool)
    case hideContacts(Bool)
    case hideCalls(Bool)
    case showSearchButton(Bool)
    case showProxyButton(Bool)
    case showAdvertising(Bool)
    case chatsHeader
    case wideChannelPosts(Bool)
    case showChannelBottomPanel(Bool)
    case channelBottomPanelInfo
    case doubleTapEdit(Bool)
    case doubleTapEditInfo
    case hideReactions(Bool)
    case hideReactionsInfo
    case hideGreetingSticker(Bool)
    case hideGreetingStickerInfo
    case hidePremiumOffers(Bool)
    case deletionEffect(Bool)
    case disableNextSwipe(Bool)
    case chatActionsOnHold(Bool)
    case chatActionsOnHoldInfo
    case unreadChatsFirst(Bool)
    case compactChatList(Bool)
    case numberRounding(Bool)
    case compactChatListInfo
    case contextMenuHeader
    case showForwardWithoutAuthor(Bool)
    case forwardWithoutAuthorInfo
    case showBroadcastMessages(Bool)
    case broadcastMessagesInfo
    case showSelectByAuthor(Bool)
    case contextTranscribe(Bool)
    case contextTranslate(Bool)
    case selectByAuthorInfo
    case videoMessagesHeader
    case selfieCountdown(Bool)
    case transcriptionHeader
    case transcriptionEnabled(Bool)
    case transcriptionOptions(NagramiXTranscriptionProvider)
    case translationHeader
    case translationEnabled(Bool)
    case translationOptions(NagramiXTranslationProvider)
    case roundQualityHeader
    case roundQuality(Bool)
    case roundQualityOptions(NagramiXRoundVideoSettings.Quality)
    case useRearCameraForVideoMessages(Bool)
    case keepMusicPlayingWhileRecording(Bool)
    case viewOnceRecording(Bool)
    case keepMusicPlayingWhileRecordingInfo
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
    case storyCameraSwipeEnabled(Bool)
    case confirmStoryViewing(Bool)
    case enableStoryRepost(Bool)
    case downloadStories(Bool)
    case profilesHeader
    case showProfileIds(Bool)
    case showExactLastSeen(Bool)
    case showExactLastSeenInfo
    case showRegistrationDate(Bool)
    case showMutualContactIcon(Bool)
    case callsHeader
    case confirmOutgoingCalls(Bool)
    case skipCallRating(Bool)
    case otherCallsHeader
    case forceTcpCalls(Bool)
    case forceTcpCallsInfo
    case messagesHeader
    case anonymousStickers(Bool)
    case hideBlockedMessages(Bool)
    case autoRevealSpoilers(Bool)
    case quickFormatting(Bool)
    case sendSilently(Bool)
    case antiCaps(Bool)
    case voiceAutoplay(Bool)
    case autoMuteNewChannels(Bool)
    case autoMuteNewChannelsInfo
    case voiceAutoplayInfo
    case showDeletedMessages(Bool)
    case showDeletedMessagesInfo
    case saveTemporaryMessages(Bool)
    case replayViewOnce(Bool)
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
    case proxyAvoidVPN
    case photosHeader
    case photoQualityHeader
    case photoQuality(Int)
    case photoQualityInfo
    case highQualityPhotos(Bool)
    case originalVideos(Bool)
    case roundVideo(Bool)
    case stickersHeader
    case stickerSizeHeader
    case stickerSize(Int)
    case showStickerTime(Bool)
    case stickerSizeInfo

    var category: NagramiXSettingsCategory {
        switch self {
        case .privacyHeader, .privacyToggle, .readLocally: return .features
        case .search, .noSearchResults, .searchHeader:
            return .interface
        case .tabsHeader, .wideTabBar, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .showAdvertising, .chatsHeader, .wideChannelPosts, .deletionEffect, .disableNextSwipe, .showChannelBottomPanel, .channelBottomPanelInfo, .hideReactions, .hideReactionsInfo, .hideGreetingSticker, .hideGreetingStickerInfo, .hidePremiumOffers, .chatActionsOnHold, .chatActionsOnHoldInfo, .unreadChatsFirst, .compactChatList, .numberRounding, .compactChatListInfo,
                .profilesHeader, .showExactLastSeen, .showExactLastSeenInfo, .showProfileIds, .showRegistrationDate, .showMutualContactIcon,
                .contextMenuHeader, .showForwardWithoutAuthor, .forwardWithoutAuthorInfo, .showBroadcastMessages, .broadcastMessagesInfo, .showSelectByAuthor, .selectByAuthorInfo, .contextTranscribe, .contextTranslate:
            return .interface
        case .videoMessagesHeader, .selfieCountdown, .useRearCameraForVideoMessages, .keepMusicPlayingWhileRecording, .viewOnceRecording, .keepMusicPlayingWhileRecordingInfo, .featureStoriesHeader, .hideStories, .storyCameraSwipeEnabled,
                .confirmStoryViewing, .enableStoryRepost, .downloadStories, .callsHeader, .confirmOutgoingCalls, .skipCallRating:
            return .features
        case .photosHeader, .highQualityPhotos, .photoQualityHeader, .photoQuality, .photoQualityInfo,
                .anonymousStickers, .stickersHeader, .stickerSizeHeader, .stickerSize, .showStickerTime, .stickerSizeInfo:
            return .features
        case .sendSilently, .quickFormatting, .autoRevealSpoilers, .hideBlockedMessages, .antiCaps, .doubleTapEdit, .doubleTapEditInfo, .messagesHeader, .autoMuteNewChannels, .autoMuteNewChannelsInfo, .voiceAutoplay, .voiceAutoplayInfo, .showDeletedMessages, .showDeletedMessagesInfo, .saveTemporaryMessages, .saveTemporaryMessagesInfo, .replayViewOnce, .deletedMessageLabel, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return .features
        case .videoPlaybackHeader, .backgroundVideoPlayback, .backgroundVideoPlaybackInfo, .originalVideos, .roundVideo:
            return .features
        case .transcriptionHeader, .transcriptionEnabled, .transcriptionOptions, .translationHeader, .translationEnabled, .translationOptions, .roundQualityHeader, .roundQuality, .roundQualityOptions, .downloadsHeader, .downloadAcceleration, .downloadAccelerationMode, .downloadAccelerationInfo, .otherVideoHeader, .videoPiPSwipe, .videoPiPSwipeInfo, .otherCallsHeader, .forceTcpCalls, .forceTcpCallsInfo, .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll, .proxyAvoidVPN:
            return .other
        }
    }

    var section: ItemListSectionId {
        switch self {
        case .transcriptionHeader, .transcriptionEnabled, .transcriptionOptions: return NagramiXSettingsSection.transcriptionSettings.rawValue
        case .translationHeader, .translationEnabled, .translationOptions: return NagramiXSettingsSection.translationSettings.rawValue
        case .privacyHeader, .privacyToggle, .readLocally: return NagramiXSettingsSection.privacy.rawValue
        case let .search(_, sectionId):
            return sectionId
        case .noSearchResults:
            return -1
        case let .searchHeader(sectionId, _):
            return sectionId
        case .tabsHeader, .wideTabBar, .hideContacts, .hideCalls, .showSearchButton, .showProxyButton, .showAdvertising:
            return NagramiXSettingsSection.tabs.rawValue
        case .chatsHeader, .wideChannelPosts, .deletionEffect, .disableNextSwipe, .showChannelBottomPanel, .channelBottomPanelInfo, .hideReactions, .hideReactionsInfo, .hideGreetingSticker, .hideGreetingStickerInfo, .hidePremiumOffers, .chatActionsOnHold, .chatActionsOnHoldInfo, .unreadChatsFirst, .compactChatList, .numberRounding, .compactChatListInfo:
            return NagramiXSettingsSection.chats.rawValue
        case .contextMenuHeader, .showForwardWithoutAuthor, .forwardWithoutAuthorInfo, .showBroadcastMessages, .broadcastMessagesInfo, .showSelectByAuthor, .selectByAuthorInfo, .contextTranscribe, .contextTranslate:
            return NagramiXSettingsSection.contextMenu.rawValue
        case .videoMessagesHeader, .selfieCountdown, .useRearCameraForVideoMessages, .keepMusicPlayingWhileRecording, .viewOnceRecording, .keepMusicPlayingWhileRecordingInfo:
            return NagramiXSettingsSection.videoMessages.rawValue
        case .featureStoriesHeader, .hideStories, .storyCameraSwipeEnabled, .confirmStoryViewing, .enableStoryRepost, .downloadStories:
            return NagramiXSettingsSection.stories.rawValue
        case .profilesHeader, .showExactLastSeen, .showExactLastSeenInfo, .showProfileIds, .showRegistrationDate, .showMutualContactIcon:
            return NagramiXSettingsSection.profiles.rawValue
        case .callsHeader, .otherCallsHeader, .confirmOutgoingCalls, .skipCallRating, .forceTcpCalls, .forceTcpCallsInfo:
            return NagramiXSettingsSection.calls.rawValue
        case .sendSilently, .quickFormatting, .autoRevealSpoilers, .hideBlockedMessages, .antiCaps, .doubleTapEdit, .doubleTapEditInfo, .messagesHeader, .autoMuteNewChannels, .autoMuteNewChannelsInfo, .voiceAutoplay, .voiceAutoplayInfo, .showDeletedMessages, .showDeletedMessagesInfo, .saveTemporaryMessages, .saveTemporaryMessagesInfo, .replayViewOnce, .deletedMessageLabel, .messageEditHistory, .messageEditHistoryInfo, .clearMessageArchive, .messageArchiveInfo:
            return NagramiXSettingsSection.messages.rawValue
        case .photosHeader, .highQualityPhotos, .photoQualityHeader, .photoQuality, .photoQualityInfo:
            return NagramiXSettingsSection.photos.rawValue
        case .anonymousStickers, .stickersHeader, .stickerSizeHeader, .stickerSize, .showStickerTime, .stickerSizeInfo:
            return NagramiXSettingsSection.stickers.rawValue
        case .videoPlaybackHeader, .backgroundVideoPlayback, .backgroundVideoPlaybackInfo, .originalVideos, .roundVideo:
            return NagramiXSettingsSection.videoPlayback.rawValue
        case .otherVideoHeader, .videoPiPSwipe, .videoPiPSwipeInfo:
            return NagramiXSettingsSection.otherVideo.rawValue
        case .roundQualityHeader, .roundQuality, .roundQualityOptions:
            return NagramiXSettingsSection.roundQualitySettings.rawValue
        case .downloadsHeader, .downloadAcceleration, .downloadAccelerationMode, .downloadAccelerationInfo:
            return NagramiXSettingsSection.downloads.rawValue
        case .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll, .proxyAvoidVPN:
            return NagramiXSettingsSection.other.rawValue
        }
    }

    var stableId: Int32 {
        switch self {
        case .transcriptionHeader: return 5020
        case .transcriptionEnabled: return 5021
        case .transcriptionOptions: return 5022
        case .translationHeader: return 5010
        case .translationEnabled: return 5011
        case .translationOptions: return 5012
        case .privacyHeader: return 146
        case let .privacyToggle(option, _):
            switch option {
            case .storyReads: return 123
            case .online: return 150
            case .typing: return 151
            case .readOnAction: return 153
            case .screenshotBypass: return 154
            }
        case .readLocally: return 148
        case .search: return -100
        case .noSearchResults: return -99
        case let .searchHeader(id, _): return 1000 + id
        case .tabsHeader: return 0
        case .wideTabBar: return 165
        case .hideContacts: return 1
        case .hideCalls: return 2
        case .showSearchButton: return 3
        case .showProxyButton: return 4
        case .showAdvertising: return 5
        case .chatsHeader: return 6
        case .wideChannelPosts: return 7
        case .disableNextSwipe: return 163
        case .deletionEffect: return 164
        case .showChannelBottomPanel: return 111
        case .channelBottomPanelInfo: return 112
        case .doubleTapEdit: return 113
        case .doubleTapEditInfo: return 114
        case .hideReactions: return 115
        case .hideReactionsInfo: return 116
        case .hideGreetingSticker: return 126
        case .hideGreetingStickerInfo: return 127
        case .hidePremiumOffers: return 5031
        case .downloadsHeader: return 117
        case .downloadAcceleration: return 118
        case .downloadAccelerationMode: return 119
        case .downloadAccelerationInfo: return 120
        case .chatActionsOnHold: return 8
        case .chatActionsOnHoldInfo: return 9
        case .unreadChatsFirst: return 139
        case .compactChatList: return 101
        case .numberRounding: return 156
        case .compactChatListInfo: return 102
        case .contextMenuHeader: return 80
        case .showForwardWithoutAuthor: return 81
        case .forwardWithoutAuthorInfo: return 82
        case .showBroadcastMessages: return 121
        case .broadcastMessagesInfo: return 122
        case .showSelectByAuthor: return 83
        case .contextTranscribe: return 161
        case .contextTranslate: return 162
        case .selectByAuthorInfo: return 84
        case .videoPlaybackHeader: return 105
        case .backgroundVideoPlayback: return 106
        case .backgroundVideoPlaybackInfo: return 107
        case .otherVideoHeader: return 108
        case .videoPiPSwipe: return 109
        case .videoPiPSwipeInfo: return 110
        case .videoMessagesHeader: return 10
        case .selfieCountdown: return 144
        case .roundQualityHeader: return 5002
        case .roundQuality: return 5000
        case .roundQualityOptions: return 5001
        case .useRearCameraForVideoMessages: return 11
        case .keepMusicPlayingWhileRecording: return 128
        case .viewOnceRecording: return 155
        case .keepMusicPlayingWhileRecordingInfo: return 129
        case .hideStories: return 21
        case .featureStoriesHeader: return 25
        case .storyCameraSwipeEnabled: return 26
        case .confirmStoryViewing: return 27
        case .enableStoryRepost: return 28
        case .downloadStories: return 159
        case .profilesHeader: return 30
        case .showProfileIds: return 31
        case .showExactLastSeen: return 134
        case .showExactLastSeenInfo: return 135
        case .showRegistrationDate: return 32
        case .showMutualContactIcon: return 33
        case .messagesHeader: return 34
        case .anonymousStickers: return 142
        case .hideBlockedMessages: return 143
        case .autoRevealSpoilers: return 145
        case .quickFormatting: return 157
        case .sendSilently: return 158
        case .antiCaps: return 141
        case .voiceAutoplay: return 130
        case .autoMuteNewChannels: return 132
        case .autoMuteNewChannelsInfo: return 133
        case .voiceAutoplayInfo: return 131
        case .showDeletedMessages: return 35
        case .showDeletedMessagesInfo: return 36
        case .replayViewOnce: return 160
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
        case .skipCallRating: return 140
        case .forceTcpCalls: return 52
        case .forceTcpCallsInfo: return 53
        case .proxySettings: return 60
        case .proxyDns: return 61
        case .proxyAutoSwitch: return 62
        case .proxyCheckAll: return 63
        case .proxyAvoidVPN: return 125
        case .photosHeader: return 90
        case .photoQualityHeader: return 91
        case .photoQuality: return 92
        case .photoQualityInfo: return 93
        case .highQualityPhotos: return 137
        case .originalVideos: return 138
        case .roundVideo: return 5030
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
            case .wideTabBar: return 5
            case .contextTranscribe: return 1230
            case .contextTranslate: return 1240
            case .skipCallRating: return 515
            case .showChannelBottomPanel: return 71
            case .highQualityPhotos: return 901
            case .privacyHeader: return 490
            case .readLocally: return 491
            case let .privacyToggle(option, _):
                switch option {
                case .storyReads: return 493
                case .online: return 494
                case .typing: return 495
                case .readOnAction: return 497
                case .screenshotBypass: return 498
                }
            case .originalVideos: return 116
            case .roundVideo: return 117
            case .channelBottomPanelInfo: return 72
            case .hideReactions: return 73
            case .hideReactionsInfo: return 74
            case .hideGreetingSticker: return 75
            case .unreadChatsFirst: return 1009
            case .numberRounding: return 1011
            case .showExactLastSeen: return 301
            case .showExactLastSeenInfo: return 302
            case .hideGreetingStickerInfo: return 76
            case .hidePremiumOffers: return 77
            case .disableNextSwipe: return 78
            case .deletionEffect: return 79
            case .doubleTapEdit: return 341
            case .doubleTapEditInfo: return 342
            case .anonymousStickers: return 965
            case .hideBlockedMessages: return 349
            case .autoRevealSpoilers: return 347
            case .quickFormatting: return 348
            case .sendSilently: return 351
            case .antiCaps: return 348
            case .voiceAutoplay: return 343
            case .autoMuteNewChannels: return 345
            case .autoMuteNewChannelsInfo: return 346
            case .voiceAutoplayInfo: return 344
            case .downloadStories: return 285
            case .roundQualityHeader: return 121
            case .roundQuality: return 122
            case .roundQualityOptions: return 123
            case .selfieCountdown: return 110
            case .keepMusicPlayingWhileRecording: return 111
            case .viewOnceRecording: return 112
            case .keepMusicPlayingWhileRecordingInfo: return 112
            case .videoPlaybackHeader: return 113
            case .backgroundVideoPlayback: return 114
            case .backgroundVideoPlaybackInfo: return 115
            case .otherVideoHeader: return 540
            case .videoPiPSwipe: return 550
            case .videoPiPSwipeInfo: return 560
            case .replayViewOnce: return 367
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
        case .privacyHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXPrivacyText("Title").uppercased(), sectionId: self.section)
        case let .privacyToggle(option, value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXPrivacyText(option.rawValue), value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: { arguments.updatePrivacyOption(option, $0) })
        case let .readLocally(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXReadModeText("Local"), value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: { arguments.updateReadMode(.local, $0) })
        case let .search(query, _):
            return NagramiXSettingsSearchItem(presentationData: presentationData, query: query, sectionId: self.section, queryUpdated: arguments.updateSearchQuery)
        case .noSearchResults:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXSettingsSearchNoResults), sectionId: self.section)
        case let .searchHeader(_, title):
            return ItemListSectionHeaderItem(presentationData: presentationData, text: title.uppercased(), sectionId: self.section)
        case .tabsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXTabsHeader.uppercased(), sectionId: self.section)
        case let .wideTabBar(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXWideTabBar, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateWideTabBar)
        case let .hideContacts(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideContactsTab, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideContacts)
        case let .hideCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideCallsTab, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideCalls)
        case let .showSearchButton(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowSearchButton, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowSearchButton)
        case let .showProxyButton(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowProxyButton, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowProxyButton)
        case let .showAdvertising(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowAdvertising, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowAdvertising)
        case .chatsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXChatsHeader.uppercased(), sectionId: self.section)
        case let .wideChannelPosts(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXWideChannelPosts, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateWideChannelPosts)
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
        case let .hideGreetingSticker(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideGreetingSticker, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideGreetingSticker)
        case let .hidePremiumOffers(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHidePremiumOffers, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHidePremiumOffers)
        case .hideGreetingStickerInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXHideGreetingStickerInfo), sectionId: self.section)
        case let .deletionEffect(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletionEffect, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateDeletionEffect)
        case let .disableNextSwipe(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDisableNextSwipe, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateDisableNextSwipe)
        case let .chatActionsOnHold(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXChatActionsOnHold, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateChatActionsOnHold)
        case .chatActionsOnHoldInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXChatActionsOnHoldInfo), sectionId: self.section)
        case let .unreadChatsFirst(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUnreadChatsFirst, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateUnreadChatsFirst)
        case let .compactChatList(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXCompactChatList, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateCompactChatList)
        case let .numberRounding(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXNumberRounding, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateNumberRounding)
        case .compactChatListInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXCompactChatListInfo), sectionId: self.section)
        case .contextMenuHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXContextMenuHeader.uppercased(), sectionId: self.section)
        case let .showForwardWithoutAuthor(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXForwardWithoutAuthorSetting, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowForwardWithoutAuthor)
        case .forwardWithoutAuthorInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXForwardWithoutAuthorInfo), sectionId: self.section)
        case let .showBroadcastMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXBroadcastMessagesSetting, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowBroadcastMessages)
        case .broadcastMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXBroadcastMessagesInfo), sectionId: self.section)
        case let .contextTranscribe(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Расшифровать"), value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateContextTranscribe)
        case let .contextTranslate(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.Conversation_ContextMenuTranslate, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateContextTranslate)
        case let .showSelectByAuthor(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSelectFromAuthorSetting, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowSelectByAuthor)
        case .selectByAuthorInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXSelectByAuthorInfo), sectionId: self.section)
        case .videoMessagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoMessagesHeader.uppercased(), sectionId: self.section)
        case let .selfieCountdown(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSelfieCountdown, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSelfieCountdown)
        case .transcriptionHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXUILocalized("РАСШИФРОВКА ГОЛОСОВЫХ"), sectionId: self.section)
        case let .transcriptionEnabled(enabled):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Расшифровка сообщений"), value: enabled, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateTranscription)
        case let .transcriptionOptions(provider):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Настройки расшифровки"), label: presentationData.strings.nagramiXUILocalized(provider.title), sectionId: self.section, style: .blocks, action: arguments.openTranscription)
        case .translationHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXUILocalized("ПЕРЕВОДЧИК"), sectionId: self.section)
        case let .translationEnabled(enabled):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Перевод сообщений"), value: enabled, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateTranslation)
        case let .translationOptions(provider):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Настройки перевода"), label: presentationData.strings.nagramiXUILocalized(provider.title), sectionId: self.section, style: .blocks, action: arguments.openTranslation)
        case .roundQualityHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXUILocalized("КАЧЕСТВЕННЫЕ КРУЖКИ"), sectionId: self.section)
        case let .roundQuality(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Качественные кружки"), value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.roundQualityChanged)
        case let .roundQualityOptions(quality):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUILocalized("Настройка кружков"), label: nagramiXRoundQualityTitle(quality, strings: presentationData.strings), labelStyle: .detailText, sectionId: self.section, style: .blocks, action: arguments.openRoundQuality)
        case let .useRearCameraForVideoMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXUseRearCamera, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateUseRearCameraForVideoMessages)
        case let .keepMusicPlayingWhileRecording(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXKeepMusicPlayingWhileRecording, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateKeepMusicPlayingWhileRecording)
        case let .viewOnceRecording(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXViewOnceRecording, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateViewOnceRecording)
        case .keepMusicPlayingWhileRecordingInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXKeepMusicPlayingWhileRecordingInfo), sectionId: self.section)
        case .videoPlaybackHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXVideoPlaybackHeader.uppercased(), sectionId: self.section)
        case let .backgroundVideoPlayback(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXBackgroundVideoPlayback, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateBackgroundVideoPlayback)
        case let .roundVideo(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXRoundVideoTitle, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateRoundVideo)
        case let .originalVideos(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXOriginalVideos, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateOriginalVideos)
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
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXVideoPiPSwipe, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateVideoPiPSwipe)
        case .videoPiPSwipeInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXVideoPiPSwipeInfo), sectionId: self.section)
        case .featureStoriesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXStoriesHeader.uppercased(), sectionId: self.section)
        case let .hideStories(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideStories, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideStories)
        case let .storyCameraSwipeEnabled(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXStoryCameraSwipeEnabled, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateStoryCameraSwipeEnabled)
        case let .confirmStoryViewing(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmStoryViewing, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmStoryViewing)
        case let .downloadStories(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDownloadStories, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateDownloadStories)
        case let .enableStoryRepost(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXEnableStoryRepost, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateEnableStoryRepost)
        case .profilesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXProfilesHeader.uppercased(), sectionId: self.section)
        case let .showExactLastSeen(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowExactLastSeen, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowExactLastSeen)
        case .showExactLastSeenInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXShowExactLastSeenInfo), sectionId: self.section)
        case let .showProfileIds(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowProfileIds, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowProfileIds)
        case let .showRegistrationDate(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowRegistrationDate, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowRegistrationDate)
        case let .showMutualContactIcon(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXShowMutualContactIcon, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowMutualContactIcon)
        case .callsHeader, .otherCallsHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXCallsHeader.uppercased(), sectionId: self.section)
        case let .confirmOutgoingCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXConfirmOutgoingCalls, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateConfirmOutgoingCalls)
        case let .skipCallRating(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSkipCallRating, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSkipCallRating)
        case let .forceTcpCalls(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXForceTcpCalls, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateForceTcpCalls)
        case .forceTcpCallsInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXForceTcpCallsInfo), sectionId: self.section)
        case .messagesHeader:
            return ItemListSectionHeaderItem(presentationData: presentationData, text: presentationData.strings.nagramiXMessagesHeader.uppercased(), sectionId: self.section)
        case let .autoMuteNewChannels(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAutoMuteNewChannels, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateAutoMuteNewChannels)
        case .autoMuteNewChannelsInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXAutoMuteNewChannelsInfo), sectionId: self.section)
        case let .anonymousStickers(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAnonymousStickers, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateAnonymousStickers)
        case let .hideBlockedMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHideBlockedMessages, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHideBlockedMessages)
        case let .sendSilently(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXSendSilently, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSendSilently)
        case let .quickFormatting(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXQuickFormatting, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateQuickFormatting)
        case let .autoRevealSpoilers(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAutoRevealSpoilers, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateAutoRevealSpoilers)
        case let .antiCaps(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAntiCaps, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateAntiCaps)
        case let .voiceAutoplay(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXVoiceAutoplay, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateVoiceAutoplay)
        case .voiceAutoplayInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXVoiceAutoplayInfo), sectionId: self.section)
        case let .showDeletedMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletedMessages, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateShowDeletedMessages)
        case .showDeletedMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXDeletedMessagesInfo), sectionId: self.section)
        case let .saveTemporaryMessages(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXTemporaryMessages, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateSaveTemporaryMessages)
        case let .replayViewOnce(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXReplayViewOnce, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateReplayViewOnce)
        case .saveTemporaryMessagesInfo:
            return ItemListTextItem(presentationData: presentationData, text: .plain(presentationData.strings.nagramiXTemporaryMessagesInfo), sectionId: self.section)
        case let .deletedMessageLabel(label):
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXDeletedMessageLabel, label: label.isEmpty ? presentationData.strings.nagramiXDeleted : label, sectionId: self.section, style: .blocks, action: arguments.editDeletedMessageLabel)
        case let .messageEditHistory(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXMessageEditHistory, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateMessageEditHistory)
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
        case let .highQualityPhotos(value):
            return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXHighQualityPhotos, value: value, maximumNumberOfLines: 0, sectionId: self.section, style: .blocks, updated: arguments.updateHighQualityPhotos)
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
        case .proxyAvoidVPN:
            return ItemListDisclosureItem(presentationData: presentationData, systemStyle: .glass, title: presentationData.strings.nagramiXAvoidProxyWithVPN, attributedTitle: NSAttributedString(string: presentationData.strings.nagramiXAvoidProxyWithVPN, font: Font.regular(presentationData.fontSize.itemListBaseFontSize), textColor: presentationData.theme.list.itemPrimaryTextColor), label: "", sectionId: self.section, style: .blocks, action: arguments.openProxySettings)
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
        case .search, .noSearchResults, .searchHeader, .proxyDns, .proxyAutoSwitch, .proxyCheckAll, .proxyAvoidVPN:
            return true
        default:
            return false
        }
    }

    var isSearchableSetting: Bool {
        switch self {
        case .privacyHeader, .search, .noSearchResults, .searchHeader, .tabsHeader, .chatsHeader, .videoMessagesHeader, .featureStoriesHeader, .profilesHeader, .callsHeader, .otherCallsHeader, .messagesHeader,
                .forceTcpCallsInfo, .voiceAutoplayInfo, .autoMuteNewChannelsInfo, .showExactLastSeenInfo, .showDeletedMessagesInfo, .saveTemporaryMessagesInfo, .messageEditHistoryInfo, .messageArchiveInfo,
                .doubleTapEditInfo, .hideReactionsInfo, .hideGreetingStickerInfo, .channelBottomPanelInfo, .contextMenuHeader, .forwardWithoutAuthorInfo, .broadcastMessagesInfo, .selectByAuthorInfo, .chatActionsOnHoldInfo, .compactChatListInfo,
                .photosHeader, .photoQualityHeader, .photoQualityInfo,
                .stickersHeader, .stickerSizeHeader, .stickerSizeInfo,
                .transcriptionHeader, .translationHeader, .roundQualityHeader, .downloadsHeader, .downloadAccelerationInfo, .keepMusicPlayingWhileRecordingInfo, .videoPlaybackHeader, .backgroundVideoPlaybackInfo, .otherVideoHeader, .videoPiPSwipeInfo:
            return false
        default:
            return true
        }
    }

    func title(strings: PresentationStrings) -> String {
        switch self {
        case .transcriptionHeader: return strings.nagramiXUILocalized("Расшифровка голосовых")
        case .transcriptionEnabled: return strings.nagramiXUILocalized("Расшифровка сообщений")
        case .transcriptionOptions: return strings.nagramiXUILocalized("Настройки расшифровки")
        case .translationHeader: return strings.nagramiXUILocalized("Переводчик")
        case .translationEnabled: return strings.nagramiXUILocalized("Перевод сообщений")
        case .translationOptions: return strings.nagramiXUILocalized("Настройки перевода")
        case .privacyHeader: return strings.nagramiXPrivacyText("Title")
        case let .privacyToggle(option, _): return strings.nagramiXPrivacyText(option.rawValue)
        case .readLocally: return strings.nagramiXReadModeText("Local")
        case .search: return strings.nagramiXSettingsSearch
        case .noSearchResults: return strings.nagramiXSettingsSearchNoResults
        case let .searchHeader(_, title): return title
        case .tabsHeader: return strings.nagramiXTabsHeader
        case .wideTabBar: return strings.nagramiXWideTabBar
        case .hideContacts: return strings.nagramiXHideContactsTab
        case .hideCalls: return strings.nagramiXHideCallsTab
        case .showSearchButton: return strings.nagramiXShowSearchButton
        case .showProxyButton: return strings.nagramiXShowProxyButton
        case .showAdvertising: return strings.nagramiXShowAdvertising
        case .chatsHeader: return strings.nagramiXChatsHeader
        case .wideChannelPosts: return strings.nagramiXWideChannelPosts
        case .showChannelBottomPanel: return strings.nagramiXChannelBottomPanel
        case .channelBottomPanelInfo: return strings.nagramiXChannelBottomPanelInfo
        case .doubleTapEdit: return strings.nagramiXDoubleTapEdit
        case .doubleTapEditInfo: return strings.nagramiXDoubleTapEditInfo
        case .hideReactions: return strings.nagramiXHideReactions
        case .hideReactionsInfo: return strings.nagramiXHideReactionsInfo
        case .hideGreetingSticker: return strings.nagramiXHideGreetingSticker
        case .hideGreetingStickerInfo: return strings.nagramiXHideGreetingStickerInfo
        case .hidePremiumOffers: return strings.nagramiXHidePremiumOffers
        case .downloadsHeader: return strings.nagramiXDownloadsHeader
        case .downloadAcceleration: return strings.nagramiXDownloadAcceleration
        case .downloadAccelerationMode: return strings.nagramiXDownloadAccelerationMode
        case .downloadAccelerationInfo: return strings.nagramiXDownloadAccelerationInfo
        case .deletionEffect: return strings.nagramiXDeletionEffect
        case .disableNextSwipe: return strings.nagramiXDisableNextSwipe
        case .chatActionsOnHold: return strings.nagramiXChatActionsOnHold
        case .chatActionsOnHoldInfo: return strings.nagramiXChatActionsOnHoldInfo
        case .unreadChatsFirst: return strings.nagramiXUnreadChatsFirst
        case .compactChatList: return strings.nagramiXCompactChatList
        case .numberRounding: return strings.nagramiXNumberRounding
        case .compactChatListInfo: return strings.nagramiXCompactChatListInfo
        case .contextMenuHeader: return strings.nagramiXContextMenuHeader
        case .showForwardWithoutAuthor: return strings.nagramiXForwardWithoutAuthorSetting
        case .forwardWithoutAuthorInfo: return strings.nagramiXForwardWithoutAuthorInfo
        case .showBroadcastMessages: return strings.nagramiXBroadcastMessagesSetting
        case .broadcastMessagesInfo: return strings.nagramiXBroadcastMessagesInfo
        case .contextTranscribe: return strings.nagramiXUILocalized("Расшифровать")
        case .contextTranslate: return strings.Conversation_ContextMenuTranslate
        case .showSelectByAuthor: return strings.nagramiXSelectFromAuthorSetting
        case .selectByAuthorInfo: return strings.nagramiXSelectByAuthorInfo
        case .videoMessagesHeader: return strings.nagramiXVideoMessagesHeader
        case .selfieCountdown: return strings.nagramiXSelfieCountdown
        case .roundQualityHeader, .roundQuality: return strings.nagramiXUILocalized("Качественные кружки")
        case .roundQualityOptions: return strings.nagramiXUILocalized("Настройка кружков")
        case .useRearCameraForVideoMessages: return strings.nagramiXUseRearCamera
        case .keepMusicPlayingWhileRecording: return strings.nagramiXKeepMusicPlayingWhileRecording
        case .viewOnceRecording: return strings.nagramiXViewOnceRecording
        case .keepMusicPlayingWhileRecordingInfo: return strings.nagramiXKeepMusicPlayingWhileRecordingInfo
        case .videoPlaybackHeader: return strings.nagramiXVideoPlaybackHeader
        case .backgroundVideoPlayback: return strings.nagramiXBackgroundVideoPlayback
        case .backgroundVideoPlaybackInfo: return strings.nagramiXBackgroundVideoPlaybackInfo
        case .otherVideoHeader: return strings.nagramiXSettingsOther
        case .videoPiPSwipe: return strings.nagramiXVideoPiPSwipe
        case .videoPiPSwipeInfo: return strings.nagramiXVideoPiPSwipeInfo
        case .featureStoriesHeader: return strings.nagramiXStoriesHeader
        case .hideStories: return strings.nagramiXHideStories
        case .storyCameraSwipeEnabled: return strings.nagramiXStoryCameraSwipeEnabled
        case .confirmStoryViewing: return strings.nagramiXConfirmStoryViewing
        case .enableStoryRepost: return strings.nagramiXEnableStoryRepost
        case .downloadStories: return strings.nagramiXDownloadStories
        case .profilesHeader: return strings.nagramiXProfilesHeader
        case .showProfileIds: return strings.nagramiXShowProfileIds
        case .showExactLastSeen: return strings.nagramiXShowExactLastSeen
        case .showExactLastSeenInfo: return strings.nagramiXShowExactLastSeenInfo
        case .showRegistrationDate: return strings.nagramiXShowRegistrationDate
        case .showMutualContactIcon: return strings.nagramiXShowMutualContactIcon
        case .callsHeader, .otherCallsHeader: return strings.nagramiXCallsHeader
        case .confirmOutgoingCalls: return strings.nagramiXConfirmOutgoingCalls
        case .skipCallRating: return strings.nagramiXSkipCallRating
        case .forceTcpCalls: return strings.nagramiXForceTcpCalls
        case .forceTcpCallsInfo: return strings.nagramiXForceTcpCallsInfo
        case .messagesHeader: return strings.nagramiXMessagesHeader
        case .anonymousStickers: return strings.nagramiXAnonymousStickers
        case .hideBlockedMessages: return strings.nagramiXHideBlockedMessages
        case .autoRevealSpoilers: return strings.nagramiXAutoRevealSpoilers
        case .quickFormatting: return strings.nagramiXQuickFormatting
        case .sendSilently: return strings.nagramiXSendSilently
        case .antiCaps: return strings.nagramiXAntiCaps
        case .voiceAutoplay: return strings.nagramiXVoiceAutoplay
        case .autoMuteNewChannels: return strings.nagramiXAutoMuteNewChannels
        case .autoMuteNewChannelsInfo: return strings.nagramiXAutoMuteNewChannelsInfo
        case .voiceAutoplayInfo: return strings.nagramiXVoiceAutoplayInfo
        case .showDeletedMessages: return strings.nagramiXDeletedMessages
        case .showDeletedMessagesInfo: return strings.nagramiXDeletedMessagesInfo
        case .replayViewOnce: return strings.nagramiXReplayViewOnce
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
        case .proxyAvoidVPN: return strings.nagramiXAvoidProxyWithVPN
        case .photosHeader: return strings.nagramiXPhotosHeader
        case .photoQualityHeader: return strings.nagramiXPhotoQuality
        case .photoQuality: return strings.nagramiXPhotoQuality
        case .photoQualityInfo: return strings.nagramiXPhotoQualityInfo
        case .highQualityPhotos: return strings.nagramiXHighQualityPhotos
        case .originalVideos: return strings.nagramiXOriginalVideos
        case .roundVideo: return strings.nagramiXRoundVideoTitle
        case .stickersHeader: return strings.nagramiXStickersHeader
        case .stickerSizeHeader: return strings.nagramiXStickerSize
        case .stickerSize: return strings.nagramiXStickerSize
        case .showStickerTime: return strings.nagramiXShowStickerTime
        case .stickerSizeInfo: return strings.nagramiXStickerSizeInfo
        }
    }

    func description(strings: PresentationStrings) -> String {
        switch self {
        case .transcriptionEnabled, .transcriptionOptions: return strings.nagramiXUILocalized("Расшифровка голосовых сообщений кружков Apple Whisper Vosk Gemini ChatGPT Telegram аудио речь API модели")
        case .translationEnabled, .translationOptions: return strings.nagramiXUILocalized("Перевод чатов, групп и каналов Telegram Premium Apple Google Яндекс Gemini ChatGPT DeepSeek язык API температура")
        case let .privacyToggle(option, _): return strings.nagramiXPrivacyText(option.rawValue + ".Search")
        case .readLocally: return strings.nagramiXReadModeText("Local.Search")
        case .selfieCountdown:
            return strings.nagramiXSelfieCountdownSearchTerms
        case .viewOnceRecording:
            return strings.nagramiXViewOnceRecordingSearchTerms
        case .skipCallRating:
            return strings.nagramiXCallRatingSearchTerms
        case .downloadAcceleration, .downloadAccelerationMode:
            return strings.nagramiXDownloadAccelerationInfo
        case .anonymousStickers:
            return strings.nagramiXAnonymousStickersSearchTerms
        case .hideBlockedMessages:
            return strings.nagramiXHideBlockedMessagesSearchTerms
        case .autoRevealSpoilers:
            return strings.nagramiXAutoRevealSpoilersSearchTerms
        case .quickFormatting:
            return strings.nagramiXQuickFormattingSearchTerms
        case .sendSilently:
            return strings.nagramiXSendSilentlySearchTerms
        case .antiCaps:
            return strings.nagramiXAntiCapsSearchTerms
        case .voiceAutoplay:
            return strings.nagramiXVoiceAutoplayInfo
        case .autoMuteNewChannels:
            return strings.nagramiXAutoMuteNewChannelsInfo
        case .doubleTapEdit:
            return strings.nagramiXDoubleTapEditInfo
        case .hideReactions:
            return strings.nagramiXHideReactionsInfo
        case .hideGreetingSticker:
            return strings.nagramiXHideGreetingStickerInfo
        case .hidePremiumOffers:
            return strings.nagramiXHidePremiumOffersInfo
        case .showExactLastSeen:
            return strings.nagramiXShowExactLastSeenInfo
        case .showChannelBottomPanel:
            return strings.nagramiXChannelBottomPanelInfo
        case .keepMusicPlayingWhileRecording:
            return strings.nagramiXKeepMusicPlayingWhileRecordingInfo
        case .backgroundVideoPlayback:
            return strings.nagramiXBackgroundVideoPlaybackInfo
        case .videoPiPSwipe:
            return strings.nagramiXVideoPiPSwipeInfo
        case .photoQuality:
            return strings.nagramiXPhotoQualityInfo
        case .highQualityPhotos:
            return strings.nagramiXHighQualityPhotosSearch
        case .originalVideos:
            return strings.nagramiXOriginalVideosSearch
        case .stickerSize, .showStickerTime:
            return strings.nagramiXStickerSizeInfo
        case .unreadChatsFirst:
            return strings.nagramiXUnreadChatsFirstSearch
        case .compactChatList:
            return strings.nagramiXCompactChatListInfo
        case .numberRounding:
            return strings.nagramiXNumberRoundingSearchTerms
        case .deletionEffect:
            return strings.nagramiXDeletionEffectSearch
        case .disableNextSwipe:
            return strings.nagramiXDisableNextSwipeSearch
        case .chatActionsOnHold:
            return strings.nagramiXChatActionsOnHoldInfo
        case .showForwardWithoutAuthor:
            return strings.nagramiXForwardWithoutAuthorInfo
        case .showBroadcastMessages:
            return strings.nagramiXBroadcastMessagesInfo
        case .showSelectByAuthor:
            return strings.nagramiXSelectByAuthorInfo
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
            return [strings.nagramiXDns, strings.nagramiXProxyAutoSwitch, strings.nagramiXProxyCheckAll, strings.nagramiXAvoidProxyWithVPN].joined(separator: " ")
        case .proxyDns, .proxyAutoSwitch, .proxyCheckAll, .proxyAvoidVPN:
            return strings.nagramiXProxySettings
        default:
            return ""
        }
    }

    func sectionTitle(strings: PresentationStrings) -> String {
        switch self.section {
        case NagramiXSettingsSection.transcriptionSettings.rawValue: return strings.nagramiXUILocalized("Расшифровка")
        case NagramiXSettingsSection.translationSettings.rawValue: return strings.nagramiXUILocalized("Переводчик")
        case NagramiXSettingsSection.roundQualitySettings.rawValue: return strings.nagramiXUILocalized("Качественные кружки")
        case NagramiXSettingsSection.privacy.rawValue: return strings.nagramiXPrivacyText("Title")
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

private func nagramiXSearchEntries(settings: NagramiXTabSettings, privacy: NagramiXPrivacySettings, keepMusicPlaying: Bool, strings: PresentationStrings, query: String, transcription: NagramiXTranscriptionConfiguration = NagramiXTranscriptionSettings.current) -> [NagramiXSettingsEntry] {
    let normalizedQuery = nagramiXNormalizedSearchText(query)
    guard !normalizedQuery.isEmpty else {
        return []
    }

    let matches = nagramiXAllSettingsEntries(settings: settings, privacy: privacy, keepMusicPlaying: keepMusicPlaying, transcription: transcription).filter { entry in
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

private func nagramiXAllSettingsEntries(settings: NagramiXTabSettings, privacy: NagramiXPrivacySettings, keepMusicPlaying: Bool, transcription: NagramiXTranscriptionConfiguration = NagramiXTranscriptionSettings.current) -> [NagramiXSettingsEntry] {
    var downloadEntries: [NagramiXSettingsEntry] = [.downloadsHeader, .downloadAcceleration(settings.downloads.enabled)]
    if settings.downloads.enabled {
        downloadEntries.append(.downloadAccelerationMode(settings.downloads.mode))
    }
    var photoEntries: [NagramiXSettingsEntry] = [.photosHeader, .highQualityPhotos(settings.media.highQualityPhotos)]
    if !settings.media.highQualityPhotos {
        photoEntries += [.photoQualityHeader, .photoQuality(settings.media.photoQuality)]
    }
    // Keep explanatory strings for search, but do not add footer rows to settings.
    return [
        .tabsHeader, .wideTabBar(settings.wideTabBar), .hideContacts(settings.hideContacts), .hideCalls(settings.hideCalls),
        .showSearchButton(settings.showSearchButton), .showProxyButton(settings.showProxyButton),
        .showAdvertising(settings.showAdvertising),
        .chatsHeader, .wideChannelPosts(settings.wideChannelPosts),
        .showChannelBottomPanel(settings.showChannelBottomPanel),
        .hideReactions(settings.hideReactions),
        .hideGreetingSticker(settings.hideGreetingSticker),
        .hidePremiumOffers(NagramiXPremiumOfferSettings.isHidden()),
        .chatActionsOnHold(settings.chatActionsOnHold),
        .disableNextSwipe(NagramiXNextSwipeSettings.isDisabled()),
        .deletionEffect(NagramiXDeletionEffectSettings.isEnabled()),
        .unreadChatsFirst(settings.unreadChatsFirst),
        .compactChatList(settings.compactChatList),
        .numberRounding(NagramiXNumberSettings.roundingEnabled),
        .videoMessagesHeader, .useRearCameraForVideoMessages(settings.useRearCameraForVideoMessages), .selfieCountdown(settings.selfieCountdown),
        .keepMusicPlayingWhileRecording(keepMusicPlaying),
        .viewOnceRecording(NagramiXRecordingSettings.viewOnceEnabled),
        .videoPlaybackHeader, .backgroundVideoPlayback(settings.backgroundVideoPlayback), .originalVideos(settings.media.originalVideos), .roundVideo(settings.media.roundVideo),
        .featureStoriesHeader, .hideStories(settings.hideStories),
        .storyCameraSwipeEnabled(!settings.disableStoryCameraSwipe),
        .confirmStoryViewing(settings.confirmStoryViewing), .enableStoryRepost(settings.enableStoryRepost),
        .downloadStories(NagramiXStoryDownloadSettings.enabled),
        .profilesHeader, .showExactLastSeen(settings.showExactLastSeen), .showProfileIds(settings.showProfileIds),
        .showRegistrationDate(settings.showRegistrationDate),
        .showMutualContactIcon(settings.showMutualContactIcon),
        .contextMenuHeader, .showForwardWithoutAuthor(settings.showForwardWithoutAuthor),
        .showBroadcastMessages(settings.showBroadcastMessages),
        .showSelectByAuthor(settings.showSelectByAuthor),
        .contextTranscribe(UserDefaults.standard.object(forKey: "nagramix.context.transcribe") as? Bool ?? true),
        .contextTranslate(UserDefaults.standard.object(forKey: "nagramix.context.translate") as? Bool ?? true),
        .messagesHeader, .doubleTapEdit(settings.doubleTapEdit),
        .voiceAutoplay(settings.voiceAutoplay),
        .autoMuteNewChannels(settings.autoMuteNewChannels),
        .autoRevealSpoilers(settings.media.autoRevealSpoilers),
        .quickFormatting(NagramiXFormattingSettings.enabled),
        .sendSilently(NagramiXSendSettings.sendSilently),
        .antiCaps(settings.antiCaps),
        .hideBlockedMessages(settings.hideBlockedMessages),
        .showDeletedMessages(settings.showDeletedMessages),
        .saveTemporaryMessages(settings.saveTemporaryMessages),
        .deletedMessageLabel(settings.deletedMessageLabel),
        .messageEditHistory(settings.messageEditHistory),
        .clearMessageArchive,
        .privacyHeader, .readLocally(privacy.readMode == .local),
        .privacyToggle(.storyReads, privacy[.storyReads]),
        .privacyToggle(.online, privacy[.online]),
        .privacyToggle(.typing, privacy[.typing]),
        .privacyToggle(.readOnAction, privacy[.readOnAction]),
        .privacyToggle(.screenshotBypass, privacy[.screenshotBypass]),
        .callsHeader, .confirmOutgoingCalls(settings.confirmOutgoingCalls),
        .skipCallRating(settings.skipCallRating),
    ] + photoEntries + [
        .stickersHeader, .anonymousStickers(settings.anonymousStickers), .stickerSizeHeader, .stickerSize(settings.media.stickerSize),
        .showStickerTime(settings.media.showStickerTime),
        .otherCallsHeader, .forceTcpCalls(settings.forceTcpCalls),
        .otherVideoHeader, .videoPiPSwipe(settings.videoPiPSwipe),
        .proxySettings, .proxyDns, .proxyAutoSwitch, .proxyCheckAll, .proxyAvoidVPN,
    ] + downloadEntries + [.roundQualityHeader, .roundQuality(NagramiXRoundVideoSettings.current.enabled)] + (NagramiXRoundVideoSettings.current.enabled ? [.roundQualityOptions(NagramiXRoundVideoSettings.current.quality)] : []) + [.translationHeader, .translationEnabled(NagramiXTranslationSettings.current.enabled)] + (NagramiXTranslationSettings.current.enabled ? [.translationOptions(NagramiXTranslationSettings.current.provider)] : []) + [.transcriptionHeader, .transcriptionEnabled(transcription.enabled)] + (transcription.enabled ? [.transcriptionOptions(transcription.provider)] : [])
}

private func nagramiXSettingsEntries(settings: NagramiXTabSettings, privacy: NagramiXPrivacySettings, keepMusicPlaying: Bool, category: NagramiXSettingsCategory, transcription: NagramiXTranscriptionConfiguration = NagramiXTranscriptionSettings.current) -> [NagramiXSettingsEntry] {
    return nagramiXAllSettingsEntries(settings: settings, privacy: privacy, keepMusicPlaying: keepMusicPlaying, transcription: transcription).filter { $0.category == category && !$0.isSearchOnly }
}

public func nagramiXSettingsController(context: AccountContext) -> ViewController {
    let settingsPromise = ValuePromise(NagramiXTabSettings.current, ignoreRepeated: false)
    let categoryPromise = ValuePromise<NagramiXSettingsCategory>(.interface, ignoreRepeated: true)
    let categoryValue = Atomic<NagramiXSettingsCategory>(value: .interface)
    let searchQueryPromise = ValuePromise<String>("", ignoreRepeated: true)
    let searchQueryValue = Atomic<String>(value: "")
    let selectCategory: (NagramiXSettingsCategory) -> Void = { category in
        let _ = categoryValue.swap(category)
        categoryPromise.set(category)
    }
    let update: ((inout NagramiXTabSettings) -> Void) -> Void = { transform in
        NagramiXTabSettings.update(transform)
        settingsPromise.set(NagramiXTabSettings.current)
    }
    var pushControllerImpl: ((ViewController) -> Void)?
    var presentControllerImpl: ((ViewController) -> Void)?
    let arguments = NagramiXSettingsControllerArguments(
        updateTranscription: { enabled in NagramiXTranscriptionSettings.update { $0.enabled = enabled } },
        openTranscription: { pushControllerImpl?(NagramiXTranscriptionSettingsController(context: context)) },
        updateTranslation: { enabled in NagramiXTranslationSettings.update { $0.enabled = enabled } },
        openTranslation: { pushControllerImpl?(NagramiXTranslationSettingsController(context: context)) },
        roundQualityChanged: { enabled in
            var value = NagramiXRoundVideoSettings.current
            value.enabled = enabled
            NagramiXRoundVideoSettings.update(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        openRoundQuality: {
            pushControllerImpl?(NagramiXRoundQualityController(context: context, changed: {
                settingsPromise.set(NagramiXTabSettings.current)
            }))
        },
        openProxySettings: {
            pushControllerImpl?(proxySettingsController(context: context))
        },
        updateReadMode: { mode, enabled in NagramiXReadModeSettings.set(mode, enabled: enabled) },
        updateSearchQuery: { query in
            let _ = searchQueryValue.swap(query)
            searchQueryPromise.set(query)
        },
        updatePhotoQuality: { value in update { $0.media.photoQuality = value } },
        updateHighQualityPhotos: { value in update { $0.media.highQualityPhotos = value } },
        updateOriginalVideos: { value in update { $0.media.originalVideos = value } },
        updateStickerSize: { value in update { $0.media.stickerSize = value } },
        updateShowStickerTime: { value in update { $0.media.showStickerTime = value } },
        updateWideTabBar: { value in update { $0.wideTabBar = value } },
        updateHideContacts: { value in update { $0.hideContacts = value } },
        updateHideCalls: { value in update { $0.hideCalls = value } },
        updateShowSearchButton: { value in update { $0.showSearchButton = value } },
        updateWideChannelPosts: { value in update { $0.wideChannelPosts = value } },
        updateShowChannelBottomPanel: { value in update { $0.showChannelBottomPanel = value } },
        updateDoubleTapEdit: { value in update { $0.doubleTapEdit = value } },
        updateHideReactions: { value in update { $0.hideReactions = value } },
        updateHideGreetingSticker: { value in update { $0.hideGreetingSticker = value } },
        updateHidePremiumOffers: { value in
            NagramiXPremiumOfferSettings.setHidden(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateUnreadChatsFirst: { value in update { $0.unreadChatsFirst = value } },
        updateCompactChatList: { value in update { $0.compactChatList = value } },
        updateNumberRounding: { value in
            NagramiXNumberSettings.setRoundingEnabled(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateDeletionEffect: { value in
            NagramiXDeletionEffectSettings.setEnabled(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateDisableNextSwipe: { value in
            NagramiXNextSwipeSettings.setDisabled(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateChatActionsOnHold: { value in update { $0.chatActionsOnHold = value } },
        updateShowForwardWithoutAuthor: { value in update { $0.showForwardWithoutAuthor = value } },
        updateShowBroadcastMessages: { value in update { $0.showBroadcastMessages = value } },
        updateShowSelectByAuthor: { value in update { $0.showSelectByAuthor = value } },
        updateContextTranscribe: { value in UserDefaults.standard.set(value, forKey: "nagramix.context.transcribe"); settingsPromise.set(NagramiXTabSettings.current) },
        updateContextTranslate: { value in UserDefaults.standard.set(value, forKey: "nagramix.context.translate"); settingsPromise.set(NagramiXTabSettings.current) },
        updateShowProxyButton: { value in update { $0.showProxyButton = value } },
        updateShowAdvertising: { value in update { $0.showAdvertising = value } },
        updateVideoPiPSwipe: { value in update { $0.videoPiPSwipe = value } },
        updateBackgroundVideoPlayback: { value in update { $0.backgroundVideoPlayback = value } },
        updateRoundVideo: { value in update { $0.media.roundVideo = value } },
        updateSelfieCountdown: { value in update { $0.selfieCountdown = value } },
        updateUseRearCameraForVideoMessages: { value in update { $0.useRearCameraForVideoMessages = value } },
        updateViewOnceRecording: { value in
            NagramiXRecordingSettings.setViewOnceEnabled(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateKeepMusicPlayingWhileRecording: { value in
            let _ = updateMediaInputSettingsInteractively(accountManager: context.sharedContext.accountManager, { current in
                return current.withUpdatedPauseMusicOnRecording(!value)
            }).start()
        },
        updateHideStories: { value in update { $0.hideStories = value } },
        // Legacy preference stores the inverse: enabled swipe means disableCameraSwipe=false.
        updateStoryCameraSwipeEnabled: { value in update { $0.disableStoryCameraSwipe = !value } },
        updateConfirmStoryViewing: { value in update { $0.confirmStoryViewing = value } },
        updateEnableStoryRepost: { value in update { $0.enableStoryRepost = value } },
        updateDownloadStories: { value in
            NagramiXStoryDownloadSettings.setEnabled(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updatePrivacyOption: { option, value in NagramiXPrivacySettings.update { $0[option] = value } },
        updateShowProfileIds: { value in update { $0.showProfileIds = value } },
        updateShowExactLastSeen: { value in update { $0.showExactLastSeen = value } },
        updateShowRegistrationDate: { value in update { $0.showRegistrationDate = value } },
        updateShowMutualContactIcon: { value in update { $0.showMutualContactIcon = value } },
        updateConfirmOutgoingCalls: { value in update { $0.confirmOutgoingCalls = value } },
        updateSkipCallRating: { value in update { $0.skipCallRating = value } },
        updateForceTcpCalls: { value in update { $0.forceTcpCalls = value } },
        updateShowDeletedMessages: { value in update { $0.showDeletedMessages = value } },
        updateAnonymousStickers: { value in update { $0.anonymousStickers = value } },
        updateHideBlockedMessages: { value in update { $0.hideBlockedMessages = value } },
        updateAutoRevealSpoilers: { value in update { $0.media.autoRevealSpoilers = value } },
        updateQuickFormatting: { value in NagramiXFormattingSettings.setEnabled(value) },
        updateSendSilently: { value in
            NagramiXSendSettings.setSendSilently(value)
            settingsPromise.set(NagramiXTabSettings.current)
        },
        updateAntiCaps: { value in update { $0.antiCaps = value } },
        updateVoiceAutoplay: { value in update { $0.voiceAutoplay = value } },
        updateAutoMuteNewChannels: { value in update { $0.autoMuteNewChannels = value } },
        updateSaveTemporaryMessages: { value in update { $0.saveTemporaryMessages = value; $0.replayViewOnce = value } },
        updateReplayViewOnce: { value in update { $0.replayViewOnce = value } },
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
            let modes: [NagramiXDownloadAcceleration] = [.medium, .maximum]
            let options = modes.map { mode in
                NagramiXOptionSheetOption(id: mode.rawValue, title: nagramiXDownloadModeTitle(mode, strings: presentationData.strings), subtitle: mode == .maximum ? presentationData.strings.nagramiXDownloadMaximumInfo : presentationData.strings.nagramiXDownloadMediumInfo)
            }
            let actionSheet = nagramiXOptionSheet(presentationData: presentationData, title: presentationData.strings.nagramiXDownloadAccelerationMode, options: options, selectedId: current.mode.rawValue, footnote: presentationData.strings.nagramiXDownloadModeFootnote, bottomAttached: true, selected: { id in
                guard let mode = NagramiXDownloadAcceleration(rawValue: id), modes.contains(mode), NagramiXTabSettings.current.downloads.enabled else { return }
                update { $0.downloads.mode = mode }
            })
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
    let mediaInputSettings = context.sharedContext.accountManager.sharedData(keys: [ApplicationSpecificSharedDataKeys.mediaInputSettings])
    |> map { sharedData in
        return sharedData.entries[ApplicationSpecificSharedDataKeys.mediaInputSettings]?.get(MediaInputSettings.self) ?? .defaultSettings
    }
    |> distinctUntilChanged
    let signal = combineLatest(queue: .mainQueue(), context.sharedContext.presentationData, combineLatest(settingsPromise.get(), nagramiXPrivacySettingsSignal(), nagramiXTranslationSettingsSignal(), nagramiXTranscriptionSettingsSignal()), categoryPromise.get(), searchQueryPromise.get(), mediaInputSettings)
    |> map { presentationData, settingsAndPrivacy, category, searchQuery, mediaInputSettings -> (ItemListControllerState, (ItemListNodeState, Any)) in
        let (settings, privacy, _, _) = settingsAndPrivacy
        let transcription = NagramiXTranscriptionSettings.configuration(accountId: context.account.id.int64)
        let normalizedQuery = nagramiXNormalizedSearchText(searchQuery)
        var resultEntries: [NagramiXSettingsEntry]
        if normalizedQuery.isEmpty {
            resultEntries = nagramiXSettingsEntries(settings: settings, privacy: privacy, keepMusicPlaying: !mediaInputSettings.pauseMusicOnRecording, category: category, transcription: transcription)
        } else {
            resultEntries = nagramiXSearchEntries(settings: settings, privacy: privacy, keepMusicPlaying: !mediaInputSettings.pauseMusicOnRecording, strings: presentationData.strings, query: normalizedQuery, transcription: transcription)
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
    let controller = NagramiXSettingsSwipeController(context: context, state: signal)
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
            selectCategory(category)
        }
    }
    controller.categorySwipeAllowedDirections = {
        guard nagramiXNormalizedSearchText(searchQueryValue.with { $0 }).isEmpty else {
            return []
        }
        // Consume central swipes even at a category boundary: a right swipe on
        // Interface should stay here, rather than become navigation back.
        return [.leftCenter, .rightCenter]
    }
    controller.categorySwiped = { [weak controller] isNext in
        guard nagramiXNormalizedSearchText(searchQueryValue.with { $0 }).isEmpty,
              let category = categoryValue.with({ $0 }).adjacent(isNext: isNext) else {
            return
        }
        controller?.view.endEditing(true)
        selectCategory(category)
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

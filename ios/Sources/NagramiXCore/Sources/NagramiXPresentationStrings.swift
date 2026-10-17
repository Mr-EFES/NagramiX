import Foundation
import TelegramPresentationData

private final class NagramiXLocalizationMarker {
}

private extension PresentationStrings {
    var nagramiXUsesRussian: Bool {
        return self.primaryComponent.languageCode.lowercased().hasPrefix("ru")
    }

    func nagramiXLocalized(_ key: String) -> String {
        let containingBundle = Bundle(for: NagramiXLocalizationMarker.self)
        guard let resourcePath = containingBundle.path(forResource: "NagramiXLocalization", ofType: "bundle"), let resourceBundle = Bundle(path: resourcePath) else {
            return key
        }
        let languageCode = self.nagramiXUsesRussian ? "ru" : "en"
        guard let languagePath = resourceBundle.path(forResource: languageCode, ofType: "lproj"), let languageBundle = Bundle(path: languagePath) else {
            return resourceBundle.localizedString(forKey: key, value: key, table: nil)
        }
        return languageBundle.localizedString(forKey: key, value: key, table: nil)
    }
}

public extension PresentationStrings {
    var nagramiXAutoRevealSpoilers: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AutoRevealSpoilers") }
    var nagramiXAutoRevealSpoilersSearchTerms: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AutoRevealSpoilers.SearchTerms") }
    var nagramiXSelfieCountdown: String { self.nagramiXLocalized("NagramiX.SelfieCountdown.Title") }
    var nagramiXSelfieCountdownSearchTerms: String { self.nagramiXLocalized("NagramiX.SelfieCountdown.SearchTerms") }
    var nagramiXArchivedCopyUnavailable: String { self.nagramiXLocalized("NagramiX.Archive.CopyUnavailable") }
    var nagramiXArchiveSaveUnavailable: String { self.nagramiXLocalized("NagramiX.Archive.SaveUnavailable") }
    var nagramiXArchiveSaveFailed: String { self.nagramiXLocalized("NagramiX.Archive.SaveFailed") }

    func nagramiXDebugLocalized(_ english: String) -> String {
        let key = "NagramiX.Debug." + english
        let value = self.nagramiXLocalized(key)
        return value == key ? english : value
    }
    var nagramiXSettingsTitle: String { self.nagramiXLocalized("NagramiX.Settings.Title") }
    var nagramiXSettingsInterface: String { self.nagramiXLocalized("NagramiX.Settings.Page.Interface") }
    var nagramiXSettingsFeatures: String { self.nagramiXLocalized("NagramiX.Settings.Page.Features") }
    var nagramiXSettingsOther: String { self.nagramiXLocalized("NagramiX.Settings.Page.Other") }
    var nagramiXSettingsSearch: String { self.nagramiXLocalized("NagramiX.Settings.Search") }
    var nagramiXSettingsSearchNoResults: String { self.nagramiXLocalized("NagramiX.Settings.Search.NoResults") }
    var nagramiXProxySettings: String { self.nagramiXLocalized("NagramiX.Settings.Proxy") }
    var nagramiXTabsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.Header") }
    var nagramiXHideContactsTab: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideContacts") }
    var nagramiXHideCallsTab: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideCalls") }
    var nagramiXHideTabTitles: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.HideTitles") }
    var nagramiXShowSearchButton: String { self.nagramiXLocalized("NagramiX.Settings.Tabs.ShowSearch") }
    var nagramiXForwardWithoutAuthorSetting: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.ForwardWithoutAuthor") }
    var nagramiXBroadcastMessagesSetting: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.BroadcastMessages") }
    var nagramiXSelectFromAuthorSetting: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.SelectByAuthor") }
    var nagramiXContextMenuHeader: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.Header") }
    var nagramiXForwardWithoutAuthorInfo: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.ForwardWithoutAuthor.Info") }
    var nagramiXSelectByAuthorInfo: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.SelectByAuthor.Info") }
    var nagramiXChatsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Chats.Header") }
    var nagramiXDownloadsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Header") }
    var nagramiXDownloadAcceleration: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Enabled") }
    var nagramiXDownloadAccelerationMode: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Mode") }
    var nagramiXDownloadAccelerationInfo: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Info") }
    var nagramiXDownloadMediumInfo: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Medium.Info") }
    var nagramiXDownloadMaximumInfo: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Maximum.Info") }
    var nagramiXDownloadModeFootnote: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Mode.Footnote") }
    var nagramiXProxyTimeoutInfo: String { self.nagramiXLocalized("NagramiX.Network.Proxy.Timeout.Info") }
    var nagramiXOptionSheetClose: String { self.nagramiXLocalized("NagramiX.Common.Close") }
    var nagramiXDownloadStandard: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Standard") }
    var nagramiXDownloadMedium: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Medium") }
    var nagramiXDownloadMaximum: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Maximum") }
    var nagramiXDownloadDisable: String { self.nagramiXLocalized("NagramiX.Settings.Downloads.Disable") }
    var nagramiXDoubleTapEdit: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DoubleTapEdit") }
    var nagramiXDoubleTapEditInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DoubleTapEdit.Info") }
    var nagramiXHideGreetingSticker: String { self.nagramiXLocalized("NagramiX.Settings.Chats.HideGreetingSticker") }
    var nagramiXHideGreetingStickerInfo: String { self.nagramiXLocalized("NagramiX.Settings.Chats.HideGreetingSticker.Info") }
    var nagramiXHideReactions: String { self.nagramiXLocalized("NagramiX.Settings.Chats.HideReactions") }
    var nagramiXHideReactionsInfo: String { self.nagramiXLocalized("NagramiX.Settings.Chats.HideReactions.Info") }
    var nagramiXChannelBottomPanel: String { self.nagramiXLocalized("NagramiX.Settings.Chats.ChannelBottomPanel") }
    var nagramiXChannelBottomPanelInfo: String { self.nagramiXLocalized("NagramiX.Settings.Chats.ChannelBottomPanel.Info") }
    var nagramiXWideChannelPosts: String { self.nagramiXLocalized("NagramiX.Settings.Chats.WideChannelPosts") }
    var nagramiXChatActionsOnHold: String { self.nagramiXLocalized("NagramiX.Settings.Chats.ActionsOnHold") }
    var nagramiXUnreadChatsFirst: String { self.nagramiXLocalized("NagramiX.Settings.Chats.UnreadFirst") }
    var nagramiXUnreadChatsFirstSearch: String { self.nagramiXLocalized("NagramiX.Settings.Chats.UnreadFirst.Search") }
    var nagramiXCompactChatList: String { self.nagramiXLocalized("NagramiX.Settings.Chats.Compact") }
    var nagramiXCompactChatListInfo: String { self.nagramiXLocalized("NagramiX.Settings.Chats.Compact.Info") }
    var nagramiXChatActionsOnHoldInfo: String { self.nagramiXLocalized("NagramiX.Settings.Chats.ActionsOnHold.Info") }
    var nagramiXPhotosHeader: String { self.nagramiXLocalized("NagramiX.Settings.Photos.Header") }
    var nagramiXPhotoQuality: String { self.nagramiXLocalized("NagramiX.Settings.Photos.Quality") }
    var nagramiXPhotoQualityInfo: String { self.nagramiXLocalized("NagramiX.Settings.Photos.Quality.Info") }
    var nagramiXHighQualityPhotos: String { self.nagramiXLocalized("NagramiX.Settings.Photos.HighQuality") }
    var nagramiXHighQualityPhotosSearch: String { self.nagramiXLocalized("NagramiX.Settings.Photos.HighQuality.Search") }
    var nagramiXOriginalVideos: String { self.nagramiXLocalized("NagramiX.Settings.Videos.Original") }
    var nagramiXOriginalVideosSearch: String { self.nagramiXLocalized("NagramiX.Settings.Videos.Original.Search") }
    var nagramiXStickersHeader: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.Header") }
    var nagramiXStickerSize: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.Size") }
    var nagramiXShowStickerTime: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.ShowTime") }
    var nagramiXStickerSizeInfo: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.Size.Info") }
    var nagramiXVideoPlaybackHeader: String { self.nagramiXLocalized("NagramiX.Settings.Video.Header") }
    var nagramiXVideoPiPSwipe: String { self.nagramiXLocalized("NagramiX.Settings.Video.PiPSwipe") }
    var nagramiXVideoPiPSwipeInfo: String { self.nagramiXLocalized("NagramiX.Settings.Video.PiPSwipe.Info") }
    var nagramiXBackgroundVideoPlayback: String { self.nagramiXLocalized("NagramiX.Settings.Video.BackgroundPlayback") }
    var nagramiXBackgroundVideoPlaybackInfo: String { self.nagramiXLocalized("NagramiX.Settings.Video.BackgroundPlayback.Info") }
    var nagramiXVideoMessagesHeader: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.Header") }
    var nagramiXKeepMusicPlayingWhileRecording: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.KeepMusicPlaying") }
    var nagramiXKeepMusicPlayingWhileRecordingInfo: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.KeepMusicPlaying.Info") }
    var nagramiXUseRearCamera: String { self.nagramiXLocalized("NagramiX.Settings.VideoMessages.UseRearCamera") }
    var nagramiXStoriesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Header") }
    var nagramiXHideStories: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Hide") }
    var nagramiXStoryCameraSwipeEnabled: String { self.nagramiXLocalized("NagramiX.Settings.Stories.DisableSwipe") }
    var nagramiXConfirmStoryViewing: String { self.nagramiXLocalized("NagramiX.Settings.Stories.ConfirmViewing") }
    var nagramiXAnonymousStoryViewing: String { self.nagramiXLocalized("NagramiX.Settings.Stories.AnonymousViewing") }
    var nagramiXAnonymousStoryViewingInfo: String { self.nagramiXLocalized("NagramiX.Settings.Stories.AnonymousViewing.Info") }
    var nagramiXAnonymousStoryWarningTitle: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Warning.Title") }
    var nagramiXAnonymousStoryWarningText: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Warning.Text") }
    var nagramiXAnonymousStoryContinue: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Continue") }
    var nagramiXAnonymousStoryPreviewTitle: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Preview.Title") }
    var nagramiXAnonymousStoryPreviewText: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Preview.Text") }
    var nagramiXAnonymousStoryPreviewAction: String { self.nagramiXLocalized("NagramiX.Stories.Anonymous.Preview.Action") }
    var nagramiXEnableStoryRepost: String { self.nagramiXLocalized("NagramiX.Settings.Stories.Repost") }
    var nagramiXRestartRequiredTitle: String { self.nagramiXLocalized("NagramiX.Restart.Title") }
    var nagramiXRestartRequiredText: String { self.nagramiXLocalized("NagramiX.Restart.Text") }
    var nagramiXRestartAction: String { self.nagramiXLocalized("NagramiX.Restart.Action") }
    var nagramiXStoryConfirmationTitle: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Title") }
    var nagramiXStoryConfirmationText: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Text") }
    func nagramiXStoryConfirmationText(owner: String) -> String {
        return String(format: self.nagramiXStoryConfirmationText, owner)
    }
    var nagramiXViewStoryAction: String { self.nagramiXLocalized("NagramiX.StoryConfirmation.Action") }
    var nagramiXIconMain: String { self.nagramiXLocalized("NagramiX.Icon.Main") }
    var nagramiXIconSunset: String { self.nagramiXLocalized("NagramiX.Icon.Sunset") }
    var nagramiXIconAurora: String { self.nagramiXLocalized("NagramiX.Icon.Aurora") }
    var nagramiXIconGraphite: String { self.nagramiXLocalized("NagramiX.Icon.Graphite") }
    var nagramiXIconAmber: String { self.nagramiXLocalized("NagramiX.Icon.Amber") }
    var nagramiXIconNeon: String { self.nagramiXLocalized("NagramiX.Icon.Neon") }
    var nagramiXIconLime: String { self.nagramiXLocalized("NagramiX.Icon.Lime") }
    var nagramiXIconRuby: String { self.nagramiXLocalized("NagramiX.Icon.Ruby") }
    var nagramiXDns: String { self.nagramiXLocalized("NagramiX.Network.DNS") }
    var nagramiXDnsSystem: String { self.nagramiXLocalized("NagramiX.Network.DNS.System") }
    var nagramiXDnsTelegram: String { self.nagramiXLocalized("NagramiX.Network.DNS.Telegram") }
    var nagramiXDnsGoogle: String { self.nagramiXLocalized("NagramiX.Network.DNS.Google") }
    var nagramiXDnsAdGuard: String { self.nagramiXLocalized("NagramiX.Network.DNS.AdGuard") }
    var nagramiXDnsCloudflare: String { self.nagramiXLocalized("NagramiX.Network.DNS.Cloudflare") }
    var nagramiXDnsCustom: String { self.nagramiXLocalized("NagramiX.Network.DNS.Custom") }
    var nagramiXCustomDohUrl: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomURL") }
    var nagramiXCustomDohPlaceholder: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomPlaceholder") }
    var nagramiXCustomDohInvalid: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomInvalid") }
    var nagramiXCustomDohUnavailable: String { self.nagramiXLocalized("NagramiX.Network.DNS.CustomUnavailable") }
    var nagramiXProxyAutoSwitch: String { self.nagramiXLocalized("NagramiX.Network.Proxy.AutoSwitch") }
    var nagramiXProxySwitchAfter: String { self.nagramiXLocalized("NagramiX.Network.Proxy.SwitchAfter") }
    var nagramiXAvoidProxyWithVPN: String { self.nagramiXLocalized("NagramiX.Network.Proxy.AvoidVPN") }
    var nagramiXAvoidProxyWithVPNInfo: String { self.nagramiXLocalized("NagramiX.Network.Proxy.AvoidVPN.Info") }
    var nagramiXProxyBypassedForVPN: String { self.nagramiXLocalized("NagramiX.Network.Proxy.AvoidVPN.Active") }
    var nagramiXProxyCheckAll: String { self.nagramiXLocalized("NagramiX.Network.Proxy.CheckAll") }
    var nagramiXProxyChecking: String { self.nagramiXLocalized("NagramiX.Network.Proxy.Checking") }
    var nagramiXProxyNoneToCheck: String { self.nagramiXLocalized("NagramiX.Network.Proxy.NoneToCheck") }
    func nagramiXProxyCheckSummary(total: Int, available: Int, unavailable: Int) -> String {
        return String(format: self.nagramiXLocalized("NagramiX.Network.Proxy.CheckSummary"), total, available, unavailable)
    }
    var nagramiXSeconds15: String { self.nagramiXLocalized("NagramiX.Time.15Seconds") }
    var nagramiXSeconds30: String { self.nagramiXLocalized("NagramiX.Time.30Seconds") }
    var nagramiXSeconds60: String { self.nagramiXLocalized("NagramiX.Time.60Seconds") }
    var nagramiXShowProxyButton: String { self.nagramiXLocalized("NagramiX.Interface.ShowProxyButton") }
    var nagramiXShowAdvertising: String { self.nagramiXLocalized("NagramiX.Interface.HideProxySponsorChannel") }
    var nagramiXEdit: String { self.nagramiXLocalized("NagramiX.Common.Edit") }
    var nagramiXSave: String { self.nagramiXLocalized("NagramiX.Common.Save") }
    var nagramiXFeatures: String { self.nagramiXLocalized("NagramiX.Info.Features") }
    var nagramiXUpdates: String { self.nagramiXLocalized("NagramiX.Info.Updates") }
    var nagramiXHelp: String { self.nagramiXLocalized("NagramiX.Info.Help") }
    var nagramiXProfilesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.Header") }
    var nagramiXShowProfileIds: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowIds") }
    var nagramiXShowRegistrationDate: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowRegistrationDate") }
    var nagramiXMutualContact: String { self.nagramiXLocalized("NagramiX.Profiles.MutualContact") }
    var nagramiXShowMutualContactIcon: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowMutualContactIcon") }
    var nagramiXCallsHeader: String { self.nagramiXLocalized("NagramiX.Settings.Calls.Header") }
    var nagramiXConfirmOutgoingCalls: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ConfirmOutgoing") }
    var nagramiXSkipCallRating: String { self.nagramiXLocalized("NagramiX.Settings.Calls.SkipRating") }
    var nagramiXCallRatingSearchTerms: String { self.nagramiXLocalized("NagramiX.Settings.Calls.SkipRating.Search") }
    var nagramiXForceTcpCalls: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ForceTcp") }
    var nagramiXForceTcpCallsInfo: String { self.nagramiXLocalized("NagramiX.Settings.Calls.ForceTcpInfo") }
    var nagramiXAnonymousStickers: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.Anonymous") }
    var nagramiXAnonymousStickersSearchTerms: String { self.nagramiXLocalized("NagramiX.Settings.Stickers.Anonymous.SearchTerms") }
    var nagramiXHideBlockedMessages: String { self.nagramiXLocalized("NagramiX.Settings.Messages.HideBlocked") }
    var nagramiXHideBlockedMessagesSearchTerms: String { self.nagramiXLocalized("NagramiX.Settings.Messages.HideBlocked.SearchTerms") }
    var nagramiXAntiCaps: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AntiCaps") }
    var nagramiXAntiCapsSearchTerms: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AntiCaps.SearchTerms") }
    var nagramiXVoiceAutoplay: String { self.nagramiXLocalized("NagramiX.Settings.Messages.VoiceAutoplay") }
    var nagramiXVoiceAutoplayInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.VoiceAutoplay.Info") }
    var nagramiXMessagesHeader: String { self.nagramiXLocalized("NagramiX.Settings.Messages.Header") }
    var nagramiXDeletedMessages: String { self.nagramiXLocalized("NagramiX.Settings.Messages.Deleted") }
    var nagramiXDeletedMessagesInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DeletedInfo") }
    var nagramiXTemporaryMessages: String { self.nagramiXLocalized("NagramiX.Settings.Messages.Temporary") }
    var nagramiXTemporaryMessagesInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.TemporaryInfo") }
    var nagramiXDeletedMessageLabel: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DeletedLabel") }
    var nagramiXDeletedMessageLabelEditor: String { self.nagramiXLocalized("NagramiX.Settings.Messages.DeletedLabelEditor") }
    var nagramiXMessageEditHistory: String { self.nagramiXLocalized("NagramiX.Settings.Messages.EditHistory") }
    var nagramiXMessageEditHistoryInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.EditHistoryInfo") }
    var nagramiXReplyWithQuote: String { self.nagramiXLocalized("NagramiX.Messages.ReplyWithQuote") }
    var nagramiXEditLocalCopy: String { self.nagramiXLocalized("NagramiX.Messages.EditLocalCopy") }
    var nagramiXDeleted: String { self.nagramiXLocalized("NagramiX.Messages.Deleted") }
    var nagramiXEditHistory: String { self.nagramiXLocalized("NagramiX.Messages.EditHistory") }
    var nagramiXSavedVersion: String { self.nagramiXLocalized("NagramiX.Messages.SavedVersion") }
    var nagramiXRevisionWithoutText: String { self.nagramiXLocalized("NagramiX.Messages.RevisionWithoutText") }
    var nagramiXRevisionArchiveInfo: String { self.nagramiXLocalized("NagramiX.Messages.RevisionArchiveInfo") }
    var nagramiXOriginalVersion: String { self.nagramiXLocalized("NagramiX.Messages.OriginalVersion") }
    var nagramiXCurrentVersion: String { self.nagramiXLocalized("NagramiX.Messages.CurrentVersion") }
    var nagramiXNoPreviousVersions: String { self.nagramiXLocalized("NagramiX.Messages.NoPreviousVersions") }
    var nagramiXClearMessageArchive: String { self.nagramiXLocalized("NagramiX.Messages.ClearArchive") }
    var nagramiXClearMessageArchiveConfirm: String { self.nagramiXLocalized("NagramiX.Messages.ClearArchiveConfirm") }
    var nagramiXClear: String { self.nagramiXLocalized("NagramiX.Common.Clear") }
    var nagramiXCancel: String { self.nagramiXLocalized("NagramiX.Common.Cancel") }
    var nagramiXLocalArchiveInfo: String { self.nagramiXLocalized("NagramiX.Messages.ArchiveInfo") }
    var nagramiXCallConfirmationTitle: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Title") }
    var nagramiXCallConfirmationText: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Text") }
    var nagramiXCallAction: String { self.nagramiXLocalized("NagramiX.CallConfirmation.Action") }
    var nagramiXForwardWithAuthor: String { self.nagramiXLocalized("NagramiX.Context.ForwardWithAuthor") }
    var nagramiXPreviewPaidReactions: String { self.nagramiXLocalized("NagramiX.Preview.PaidReactions") }
    var nagramiXForwardWithoutAuthor: String { self.nagramiXLocalized("NagramiX.Context.ForwardWithoutAuthor") }
    var nagramiXBroadcastMessages: String { self.nagramiXLocalized("NagramiX.Context.BroadcastMessages") }
    var nagramiXBroadcastMessagesInfo: String { self.nagramiXLocalized("NagramiX.Settings.ContextMenu.BroadcastMessages.Info") }
    var nagramiXSelectFromAuthor: String { self.nagramiXLocalized("NagramiX.Context.SelectFromAuthor") }
    var nagramiXAuthorSelectionEmpty: String { self.nagramiXLocalized("NagramiX.Context.AuthorSelectionEmpty") }
    var nagramiXAuthorSelectionFailed: String { self.nagramiXLocalized("NagramiX.Context.AuthorSelectionFailed") }
    var nagramiXAuthorDeleteUnavailable: String { self.nagramiXLocalized("NagramiX.Context.AuthorDeleteUnavailable") }
    func nagramiXSelectedDeletionWarning(_ count: Int) -> String {
        return self.nagramiXLocalized("NagramiX.Context.SelectedDeletionWarning").replacingOccurrences(of: "%@", with: String(count))
    }
    func nagramiXLocalCopiesDeletionWarning(_ count: Int) -> String {
        return self.nagramiXLocalized("NagramiX.Context.LocalCopiesDeletionWarning").replacingOccurrences(of: "%@", with: String(count))
    }
    var nagramiXDataCenters: String { self.nagramiXLocalized("NagramiX.Network.DataCenters") }
    var nagramiXProfileId: String { self.nagramiXLocalized("NagramiX.Profile.Id") }
    var nagramiXProfileIdCopied: String { self.nagramiXLocalized("NagramiX.Profile.IdCopied") }
    var nagramiXRegistrationDate: String { self.nagramiXLocalized("NagramiX.Profile.RegistrationDate") }
    func nagramiXApproximateRegistration(_ year: Int) -> String {
        return self.nagramiXLocalized("NagramiX.Profile.RegistrationApproximate").replacingOccurrences(of: "%@", with: "\(year)")
    }
    var nagramiXUnknown: String { self.nagramiXLocalized("NagramiX.Common.Unknown") }
    var nagramiXAutoMuteNewChannels: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AutoMuteNewChannels") }
    var nagramiXAutoMuteNewChannelsInfo: String { self.nagramiXLocalized("NagramiX.Settings.Messages.AutoMuteNewChannels.Info") }
    var nagramiXShowExactLastSeen: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowExactLastSeen") }
    var nagramiXShowExactLastSeenInfo: String { self.nagramiXLocalized("NagramiX.Settings.Profiles.ShowExactLastSeen.Info") }
    var nagramiXAuthorizationError: String { self.nagramiXLocalized("NagramiX.Authorization.Error") }

}

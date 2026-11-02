import Foundation

@main struct ProtectedStoryTests {
    static func main() {
        let args = CommandLine.arguments
        if args.count == 4 {
            let download = args[2] == "true", capture = args[3] == "true"
            if args[1] == "set" {
                NagramiXStoryDownloadSettings.setEnabled(download)
                NagramiXPrivacySettings.update { $0[.screenshotBypass] = capture }
                _ = UserDefaults.standard.synchronize()
            }
            precondition(NagramiXStoryDownloadSettings.enabled == download)
            precondition(NagramiXPrivacySettings.current.bypassScreenshots == capture)
            return
        }
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ message: String) {
            precondition(value(), message)
            checks += 1
        }
        check(!NagramiXStoryDownloadSettings.enabled && !NagramiXPrivacySettings.current.bypassScreenshots,
              "both new-install defaults remain OFF")
        for capture in [false, true] {
            NagramiXPrivacySettings.update { $0[.screenshotBypass] = capture }
            for download in [false, true] {
                NagramiXStoryDownloadSettings.setEnabled(download)
                for protected in [false, true] {
                    for media in [EngineMedia.image(ImageMedia()), .file(FileMedia())] {
                        let view = StoryActions()
                        view.component = StoryComponent()
                        view.component!.slice.item.storyItem.isForwardingDisabled = protected
                        view.component!.slice.item.storyItem.media = media
                        check(view.canDownload == download, "available image/video, independent of author protection and capture switch")
                        if protected && download { check(!view.legacyCanDownload, "baseline reproduces missing protected-story download") }
                        check(view.showSaveItem() == (!protected || download), "native menu and header agree for protected stories")
                        view.pressDownload()
                        check(view.downloads.count == (download ? 1 : 0), "header only saves with opt-in")
                        view.menuAction(premium: false)()
                        check(view.downloads.count == (download ? 2 : 0), "menu uses the same opt-in saver")
                        check(view.upgrades == (!protected && !download ? 1 : 0), "stock non-premium path retained only without opt-in")
                        check(view.nativeSaves == 0, "protected non-premium opt-in does not fall through to native save")
                    }
                }
                for media in [EngineMedia.liveStream, .unsupported, .image(ImageMedia(representations: [])),
                              .file(FileMedia(isVideo: false, mimeType: "audio/ogg"))] {
                    let view = StoryActions(); view.component = StoryComponent()
                    view.component!.slice.item.storyItem.media = media
                    view.component!.slice.item.storyItem.isForwardingDisabled = true
                    check(!view.canDownload && !view.showSaveItem(), "no new save for live/unavailable/unsupported media")
                }
            }
        }
        NagramiXStoryDownloadSettings.setEnabled(true)
        let stale = StoryActions(); stale.component = StoryComponent()
        stale.component!.slice.item.storyItem.isForwardingDisabled = true
        let protectedMenu = stale.menuAction(premium: true)
        NagramiXStoryDownloadSettings.setEnabled(false); protectedMenu()
        check(stale.downloads.isEmpty && stale.nativeSaves == 0, "OFF invalidates an already open protected save menu")
        NagramiXStoryDownloadSettings.setEnabled(true)
        let oldMenu = stale.menuAction(premium: true)
        stale.component!.slice.item.storyItem.id += 1; oldMenu()
        check(stale.downloads.isEmpty && stale.nativeSaves == 0, "old menu cannot save another story")
        let oldPeer = stale.menuAction(premium: true)
        stale.component!.slice.effectivePeer = EnginePeer(id: 3); oldPeer()
        check(stale.downloads.isEmpty && stale.nativeSaves == 0, "old menu cannot save another peer's story")

        NagramiXPrivacySettings.update { $0[.screenshotBypass] = false }
        let video = AVSampleBufferDisplayLayer(), mandatory = AVSampleBufferDisplayLayer()
        nagramiXSetVideoCaptureProtection(video, true, allowsBypass: storyVideoAllowsScreenshotBypass())
        nagramiXSetVideoCaptureProtection(mandatory, true, allowsBypass: false)
        check(video.preventsCapture && mandatory.preventsCapture, "OFF retains original video protection")
        let photo = UIImage()
        var image: StoryImage? = StoryImage(frame: .zero)
        image!.update(context: AccountContext(), strings: PresentationStrings(), peer: EnginePeer(id: 2), storyId: 9,
            media: .image(ImageMedia()), size: CGSize(width: 390, height: 600), isCaptureProtected: true,
            attemptSynchronous: false, transition: .immediate)
        image!.deliver(photo, required: true)
        check(image!.hasSecureWrapper && image!.infoProtected, "OFF retains native secure image wrapper")
        let imageWrites = image!.imageWrites
        image!.update(context: AccountContext(), strings: PresentationStrings(), peer: EnginePeer(id: 2), storyId: 9,
            media: .image(ImageMedia()), size: CGSize(width: 390, height: 600), isCaptureProtected: true,
            attemptSynchronous: false, transition: .immediate)
        check(image!.imageWrites == imageWrites, "ordinary layout does not reassign the decoded image")
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = true }
        check(!video.preventsCapture && mandatory.preventsCapture, "existing story video bypasses, mandatory media remains protected")
        check(!image!.hasSecureWrapper && !image!.infoProtected && image!.displayedImage === photo,
              "ON reuses decoded image and removes the secure wrapper/blocked state")
        let legacy = LegacyStoryImage(); legacy.deliver(photo, required: true)
        check(legacy.hasSecureWrapper, "baseline story image ignores the screenshot opt-in")
        let updates = image!.updates
        NagramiXPrivacySettings.update { $0[.typing].toggle() }
        check(image!.updates == updates, "unrelated privacy changes do not refresh image rendering")
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = false }
        check(video.preventsCapture && image!.hasSecureWrapper && image!.infoProtected, "OFF restores already open story protection")
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = true }
        let decodedLate = UIImage(); image!.deliver(decodedLate, required: true)
        check(!image!.hasSecureWrapper && image!.displayedImage === decodedLate, "late decode reads current capture preference")
        weak var released = image; image = nil
        check(released == nil, "observer and refresh closure do not retain a dismissed image view")
        NagramiXPrivacySettings.update { $0[.screenshotBypass] = false }

        for options in 0..<4 {
            NagramiXTabSettings.current.showForwardWithoutAuthor = options & 1 != 0
            NagramiXTabSettings.current.showBroadcastMessages = options & 2 != 0
            check(nagramiXCanSaveGalleryMedia(Message(), peerIsCopyProtected: false), "ordinary unprotected gallery path unchanged")
            check(nagramiXCanSaveGalleryMedia(Message(protected: true), peerIsCopyProtected: false) == (options != 0), "message protection follows existing export options")
            check(nagramiXCanSaveGalleryMedia(Message(), peerIsCopyProtected: true) == (options != 0), "peer protection follows the same export options")
            check(!nagramiXCanSaveGalleryMedia(Message(paidContent: 1), peerIsCopyProtected: false), "paid media keeps its original save boundary")
        }
        NagramiXTabSettings.current.showBroadcastMessages = true
        var excluded: [Message] = []
        var message = Message(protected: true); message.id.peerId.namespace = Namespaces.Peer.SecretChat; excluded.append(message)
        message = Message(protected: true); message.id.peerId.isVerificationCodes = true; excluded.append(message)
        message = Message(containsSecretMedia: true, protected: true); excluded.append(message)
        message = Message(minAutoremoveOrClearTimeout: viewOnceTimeout, protected: true); excluded.append(message)
        for flags in [MessageFlags.Sending, .Failed] { excluded.append(Message(flags: flags, protected: true)) }
        for media in [TelegramMediaPaidContent() as Any, TelegramMediaExpiredContent(), TelegramMediaAction()] {
            excluded.append(Message(media: [media], protected: true))
        }
        for message in excluded { check(!nagramiXCanSaveGalleryMedia(message, peerIsCopyProtected: false), "no expansion to excluded message classes") }
        print("PASS \(checks) protected story/menu/live-capture/gallery-policy checks; no UIKit/Photos/network execution")
    }
}

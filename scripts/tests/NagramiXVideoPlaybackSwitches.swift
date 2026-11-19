class NativeVideoContent {}
class HLSVideoContent {}
class WebEmbedVideoContent {}
class SystemVideoContent {}
class PlatformVideoContent {}
struct Message {
    var paidContent: Int?
    var adAttribute: Int?
}
enum ContentInfo {
    case message(Message, Int?)
    case webPage
}
struct UniversalVideoGalleryItem {
    let content: AnyObject
    var isSecret = false
    var contentInfo: ContentInfo?
}

private enum ButtonStyle { case plain }
private final class UIBarButtonItem {
    var accessibilityLabel: String?
    init(image: Int, style: ButtonStyle, target: AnyObject?, action: String) {}
}
private struct ButtonList {
    let items: [UIBarButtonItem]
    static func single(_ items: [UIBarButtonItem]) -> Self { Self(items: items) }
}
private final class GalleryControls {
    var item: UniversalVideoGalleryItem?
    var isLivePhoto = false
    var isCentral: Bool? = true
    struct Strings { let Gallery_VoiceOver_PictureInPicture = "PiP" }
    struct Data { let strings = Strings() }
    let presentationData = Data()
    let pictureInPictureButtonImage = 0
    var pictureInPictureButton: UIBarButtonItem?
    let nagramiXOtherBarButtons = [UIBarButtonItem(image: 0, style: .plain, target: nil, action: "more")]
    let _rightBarButtonItems = ValuePromise<ButtonList>(.single([]), ignoreRepeated: false)
    // GALLERY CONTROLS
}

@main private enum PlaybackSwitchTests {
    static func main() {
        let gallery = GalleryControls()
        for pip in [false, true, false] {
            NagramiXTabSettings.videoPictureInPictureEnabled = pip
            for background in [false, true] {
                NagramiXTabSettings.backgroundVideoPlaybackEnabled = background
                let sources: [AnyObject] = [NativeVideoContent(), HLSVideoContent(), PlatformVideoContent(),
                                            SystemVideoContent(), WebEmbedVideoContent()]
                for source in sources {
                    for info: ContentInfo? in [.message(Message(), nil), .webPage, nil] {
                        let item = UniversalVideoGalleryItem(content: source, contentInfo: info)
                        gallery.item = item
                        gallery.nagramiXRefreshPiPControls()
                        precondition(gallery.hasPictureInPicture == pip && gallery.usesNativePictureInPictureSwipe == pip)
                        if case .message = info {
                            precondition(gallery.pictureInPictureButton == nil)
                        } else {
                            precondition((gallery.pictureInPictureButton != nil) == pip)
                        }
                        precondition(gallery._rightBarButtonItems.value.items.last === gallery.nagramiXOtherBarButtons.last)
                    }
                }
                let av = AVPlayer()
                let bridge = NagramiXAVPlayerPictureInPicture(player: av, layer: AVPlayerLayer(player: av))
                let owner = UUID()
                bridge.setBackground(id: owner, active: background)
                precondition(bridge.begin() == pip)
                if pip, let controller = AVPictureInPictureController.last {
                    controller.isPictureInPictureActive = true
                    bridge.pictureInPictureControllerDidStartPictureInPicture(controller)
                }
                NotificationCenter.default.post(name: UIApplication.didEnterBackgroundNotification, object: nil)
                precondition((av.pauses > 0) == !background)
                precondition((av.audiovisualBackgroundPlaybackPolicy == .continuesIfPossible) == background)
                NotificationCenter.default.post(name: UIApplication.willEnterForegroundNotification, object: nil)
                for youtube in [true, false] {
                    let web = WebPolicy(youtube: youtube)
                    let player = web.playerNode
                    let helper = player.nagramiXSystemPiP
                    helper.setYouTubePolicy(youtube, pipEnabled: pip, backgroundEnabled: background)
                    web.play()
                    web.audioSessionManager.acquire(0)
                    web.setNagramiXBackgroundPlayback(id: owner, active: background)
                    precondition(helper.begin() == pip)
                    if pip {
                        let frame = WKFrameInfo(3)
                        let probe = player.view.calls.last { $0.0["command"] as? String == "probe" }!.0
                        var reply = probe
                        reply["kind"] = "candidate"
                        reply["frameKey"] = "3"
                        reply["video"] = "1"
                        reply["playing"] = true
                        reply["area"] = 100.0
                        helper.userContentController(player.controller, didReceive: WKScriptMessage(body: reply, frameInfo: frame))
                        DispatchQueue.main.run()
                        reply["kind"] = "state"
                        reply["active"] = true
                        helper.userContentController(player.controller, didReceive: WKScriptMessage(body: reply, frameInfo: frame))
                        precondition(helper.isActive)
                    }
                    NotificationCenter.default.post(name: UIApplication.didEnterBackgroundNotification, object: nil)
                    precondition(web.nagramiXHasManagedAudio == background)
                    precondition((player.impl.pauses > 0) == !background)
                    precondition(helper.isActive == pip)
                    NotificationCenter.default.post(name: UIApplication.didBecomeActiveNotification, object: nil)
                    NotificationCenter.default.post(name: UIApplication.willEnterForegroundNotification, object: nil)
                    precondition(player.impl.plays == 1)
                    helper.setYouTubePolicy(youtube, pipEnabled: false, backgroundEnabled: background)
                    precondition(!helper.keepsPlaybackActive && !helper.begin())
                }
            }
        }
        NagramiXTabSettings.videoPictureInPictureEnabled = true
        AVPictureInPictureController.supported = false
        precondition(!nagramiXCanOfferPictureInPicture(.init(content: NativeVideoContent())))
        print("PASS: five source families, gallery and preview entry, WebKit and AVKit background pause, four preference combinations")
    }
}

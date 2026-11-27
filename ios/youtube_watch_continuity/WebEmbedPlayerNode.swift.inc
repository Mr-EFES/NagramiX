import Foundation
import UIKit
import AsyncDisplayKit
import SwiftSignalKit
@preconcurrency import WebKit
import TelegramCore
import NagramiXCore
import UniversalMediaPlayer

protocol WebEmbedImplementation {
    func setup(_ webView: WKWebView, userContentController: WKUserContentController, evaluateJavaScript: @escaping (String, ((Any?) -> Void)?) -> Void, updateStatus: @escaping (MediaPlayerStatus) -> Void, onPlaybackStarted: @escaping () -> Void)
    
    func play()
    func pause()
    func togglePlayPause()
    func seek(timestamp: Double)
    func setBaseRate(_ baseRate: Double)
    
    func pageReady()
    func callback(url: URL)
}

public enum WebEmbedType {
    case youtube(videoId: String, timestamp: Int)
    case vimeo(videoId: String, timestamp: Int)
    case twitch(url: String)
    case iframe(url: String)
    
    public var supportsSeeking: Bool {
        switch self {
        case .youtube, .vimeo:
            return true
        default:
            return false
        }
    }
}

public func webEmbedType(content: TelegramMediaWebpageLoadedContent, forcedTimestamp: Int? = nil) -> WebEmbedType {
    if let (videoId, timestamp) = extractYoutubeVideoIdAndTimestamp(url: content.url) {
        return .youtube(videoId: videoId, timestamp: forcedTimestamp ?? timestamp)
    } else if let embedUrl = content.embedUrl, let (videoId, timestamp) = extractYoutubeVideoIdAndTimestamp(url: embedUrl) {
        return .youtube(videoId: videoId, timestamp: forcedTimestamp ?? timestamp)
    } else if let (videoId, timestamp) = extractVimeoVideoIdAndTimestamp(url: content.url) {
        return .vimeo(videoId: videoId, timestamp: forcedTimestamp ?? timestamp)
    } else if let embedUrl = content.embedUrl, isTwitchVideoUrl(embedUrl) && false {
        return .twitch(url: embedUrl)
    } else {
        return .iframe(url: content.embedUrl ?? content.url)
    }
}

func webEmbedImplementation(for type: WebEmbedType) -> WebEmbedImplementation {
    switch type {
        case let .youtube(videoId, timestamp):
            return YoutubeEmbedImplementation(videoId: videoId, timestamp: timestamp)
        case let .vimeo(videoId, timestamp):
            return VimeoEmbedImplementation(videoId: videoId, timestamp: timestamp)
        case let .twitch(url):
            return TwitchEmbedImplementation(url: url)
        case let .iframe(url):
            return GenericEmbedImplementation(url: url)
    }
}

// WebKit commands and their captured completion values belong to the main queue.
// Do not hold a player on a worker while waiting for a WebKit callback: that
// worker may become its last owner and run UIKit/WebKit teardown off-main.
private final class NagramiXWebJavaScriptQueue {
    private struct Command {
        let id = UUID()
        let script: String
        let completion: ((Any?) -> Void)?
    }

    private let evaluate: (String, @escaping (Any?) -> Void) -> Void
    private var pending: [Command] = []
    private var running: UUID?
    private var invalidated = false

    init(evaluate: @escaping (String, @escaping (Any?) -> Void) -> Void) {
        self.evaluate = evaluate
    }

    func enqueue(_ script: String, completion: ((Any?) -> Void)?) {
        precondition(Queue.mainQueue().isCurrent())
        guard !self.invalidated else { return }
        self.pending.append(Command(script: script, completion: completion))
        self.drain()
    }

    private func drain() {
        precondition(Queue.mainQueue().isCurrent())
        guard !self.invalidated, self.running == nil, !self.pending.isEmpty else { return }
        let command = self.pending.removeFirst()
        self.running = command.id
        self.evaluate(command.script) { [weak self] result in
            precondition(Queue.mainQueue().isCurrent())
            guard let self, !self.invalidated, self.running == command.id else { return }
            // A completion can enqueue another command or close the player.
            // Keep this command running until that callback has returned.
            command.completion?(result)
            guard !self.invalidated, self.running == command.id else { return }
            self.running = nil
            self.drain()
        }
    }

    func invalidate() {
        precondition(Queue.mainQueue().isCurrent())
        self.invalidated = true
        self.pending.removeAll()
        self.running = nil
    }
}

// QueueLocalObject owns this graph through its unmanaged reference. Its release
// is performed on main even when Texture/SignalKit releases the node on a worker.
// Keeping ordinary node properties plus an async cleanup copy would still allow
// the worker to become the last owner if main ran that cleanup before deinit ended.
private final class NagramiXWebPlayerResources {
    let webView: WKWebView
    let systemPiP: NagramiXWebSystemPictureInPicture
    let commands: NagramiXWebJavaScriptQueue
    var policyObserver: NSObjectProtocol?

    init(webView: WKWebView, systemPiP: NagramiXWebSystemPictureInPicture) {
        precondition(Queue.mainQueue().isCurrent())
        self.webView = webView
        self.systemPiP = systemPiP
        self.commands = NagramiXWebJavaScriptQueue(evaluate: { [weak webView] script, completion in
            guard let webView else { completion(nil); return }
            webView.evaluateJavaScript(script, completionHandler: { result, _ in completion(result) })
        })
    }

    deinit {
        precondition(Queue.mainQueue().isCurrent())
        if let observer = self.policyObserver { NotificationCenter.default.removeObserver(observer) }
        self.commands.invalidate()
        self.systemPiP.actualMediaChanged = nil
        self.systemPiP.restore = nil
        self.systemPiP.stop()
        self.systemPiP.webView = nil
        self.webView.navigationDelegate = nil
        self.webView.configuration.userContentController.removeScriptMessageHandler(forName: "nagramiXSystemPiP")
        self.webView.configuration.userContentController.removeScriptMessageHandler(forName: "nagramiXSystemPiP", contentWorld: .defaultClient)
        self.webView.stopLoading()
        func disableGestures(view: UIView) {
            if let recognizers = view.gestureRecognizers {
                for recognizer in recognizers { recognizer.isEnabled = false }
            }
            for subview in view.subviews { disableGestures(view: subview) }
        }
        disableGestures(view: self.webView)
    }
}

final class WebEmbedPlayerNode: ASDisplayNode, WKNavigationDelegate {
    private let statusValue = ValuePromise<MediaPlayerStatus>(MediaPlayerStatus(generationTimestamp: 0.0, duration: 0.0, dimensions: CGSize(), timestamp: 0.0, baseRate: 1.0, seekId: 0, status: .paused, soundEnabled: true), ignoreRepeated: true)
    
    var status: Signal<MediaPlayerStatus, NoError> {
        return self.statusValue.get()
    }
    
    private var readyValue: ValuePromise<Bool> = ValuePromise<Bool>(false)
    
    var ready: Signal<Bool, NoError> {
        return self.readyValue.get()
    }
    
    let impl: WebEmbedImplementation
    
    private let openUrl: (URL) -> Void
    private let intrinsicDimensions: CGSize
    private let nagramiXWebResources: QueueLocalObject<NagramiXWebPlayerResources>
    private var nagramiXSystemPiP: NagramiXWebSystemPictureInPicture { self.nagramiXWebResources.unsafeGet()!.systemPiP }
    private var webView: WKWebView { self.nagramiXWebResources.unsafeGet()!.webView }
    private var nagramiXJavaScriptQueue: NagramiXWebJavaScriptQueue { self.nagramiXWebResources.unsafeGet()!.commands }
    private var nagramiXPolicyObserver: NSObjectProtocol? {
        get { self.nagramiXWebResources.unsafeGet()!.policyObserver }
        set { self.nagramiXWebResources.unsafeGet()!.policyObserver = newValue }
    }

    init(impl: WebEmbedImplementation, intrinsicDimensions: CGSize, openUrl: @escaping (URL) -> Void) {
        self.impl = impl
        self.intrinsicDimensions = intrinsicDimensions
        self.openUrl = openUrl
        
        let userContentController = WKUserContentController()
        let systemPiP = NagramiXWebSystemPictureInPicture(controller: userContentController, isYouTube: impl is YoutubeEmbedImplementation, pipEnabled: NagramiXTabSettings.videoPictureInPictureEnabled, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
        if impl is YoutubeEmbedImplementation {
            
        } else {
            userContentController.addUserScript(WKUserScript(source: "var meta = document.createElement('meta'); meta.setAttribute('name', 'viewport'); meta.setAttribute('content', 'width=device-width'); document.getElementsByTagName('head')[0].appendChild(meta)", injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        }
        
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.userContentController = userContentController
        
        if #available(iOSApplicationExtension 10.0, iOS 10.0, *) {
            configuration.mediaTypesRequiringUserActionForPlayback = []
        } else {
            configuration.mediaPlaybackRequiresUserAction = false
        }
        
        if #available(iOSApplicationExtension 9.0, iOS 9.0, *) {
            configuration.allowsPictureInPictureMediaPlayback = true
        }

        let frame = CGRect(origin: CGPoint.zero, size: intrinsicDimensions)
        let webView = WKWebView(frame: frame, configuration: configuration)
        systemPiP.webView = webView
        self.nagramiXWebResources = QueueLocalObject(queue: Queue.mainQueue(), generate: {
            NagramiXWebPlayerResources(webView: webView, systemPiP: systemPiP)
        })
        
        super.init()
        self.frame = frame

        self.nagramiXSystemPiP.setYouTubePolicy(self.impl is YoutubeEmbedImplementation, pipEnabled: NagramiXTabSettings.videoPictureInPictureEnabled, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.nagramiXSystemPiP.setYouTubePolicy(self.impl is YoutubeEmbedImplementation, pipEnabled: NagramiXTabSettings.videoPictureInPictureEnabled, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
        }
        
        self.webView.navigationDelegate = self
        self.webView.scrollView.isScrollEnabled = false
        self.webView.allowsLinkPreview = false
        self.webView.allowsBackForwardNavigationGestures = false
        if #available(iOSApplicationExtension 11.0, iOS 11.0, *) {
            self.webView.accessibilityIgnoresInvertColors = true
            self.webView.scrollView.contentInsetAdjustmentBehavior = .never
        }
        self.view.addSubview(self.webView)
        
        self.nagramiXSystemPiP.actualMediaChanged = { [weak self] paused in
            guard let self else { return }
            if paused { self.nagramiXActualPlaybackPaused?() }
            if let status = self.nagramiXLastImplementationStatus { self.nagramiXPublishPlaybackStatus(status) }
        }
        if let youtube = self.impl as? YoutubeEmbedImplementation {
            youtube.openWatchPage = { [weak self] id, position in
                guard let self else { return }
                self.watchNavigation = self.nagramiXSystemPiP.loadWatchPage(id: id, position: position)
                if self.watchNavigation == nil { (self.impl as? YoutubeEmbedImplementation)?.startupFailed() }
            }
            youtube.sendWatchCommand = { [weak self] command, value, revision in
                self?.nagramiXSystemPiP.watchControl(command, value: value, revision: revision)
            }
            self.nagramiXSystemPiP.watchEvent = { [weak youtube] event, position, duration, revision, canUsePiP in
                youtube?.watchEvent(event, position: position, duration: duration, revision: revision, canUsePiP: canUsePiP)
            }
            youtube.pageVisible = { [weak self] in self?.readyValue.set(true) }
            self.nagramiXSystemPiP.requiresPlayingSource = { [weak youtube] in youtube?.wantsPlayingPictureInPicture == true }
        }
        self.impl.setup(self.webView, userContentController: userContentController, evaluateJavaScript: { [weak self] js, completion in
            self?.evaluateJavaScript(js: js, completion: completion)
        }, updateStatus: { [weak self] status in
            self?.nagramiXPublishPlaybackStatus(status)
        }, onPlaybackStarted: { [weak self] in
            self?.readyValue.set(true)
        })
    }
    
    
    private var nagramiXLastImplementationStatus: MediaPlayerStatus?

    private func nagramiXPublishPlaybackStatus(_ status: MediaPlayerStatus) {
        self.nagramiXLastImplementationStatus = status
        guard let actual = self.nagramiXSystemPiP.actualMediaPlaying else { self.statusValue.set(status); return }
        let playback: MediaPlayerPlaybackStatus
        switch status.status {
        case .playing where !actual && self.nagramiXSystemPiP.playbackAllowed && (self.impl as? YoutubeEmbedImplementation)?.wantsPlayingPictureInPicture == true:
            playback = .buffering(initial: false, whilePlaying: true, progress: 0.0, display: false)
        case .playing where !actual || !self.nagramiXSystemPiP.playbackAllowed:
            playback = .paused
        case .paused where status.soundEnabled && actual && self.nagramiXSystemPiP.preservesWebPlayback:
            playback = .playing
        case let .buffering(initial, _, progress, display) where !actual || !self.nagramiXSystemPiP.playbackAllowed:
            playback = .buffering(initial: initial, whilePlaying: false, progress: progress, display: display)
        case let .buffering(initial, false, progress, display) where actual && self.nagramiXSystemPiP.preservesWebPlayback:
            playback = .buffering(initial: initial, whilePlaying: true, progress: progress, display: display)
        default:
            playback = status.status
        }
        self.statusValue.set(MediaPlayerStatus(generationTimestamp: status.generationTimestamp, duration: status.duration,
            dimensions: status.dimensions, timestamp: status.timestamp, baseRate: status.baseRate,
            seekId: status.seekId, status: playback, soundEnabled: status.soundEnabled))
    }

    var nagramiXActualPlaybackPaused: (() -> Void)?

    func setNagramiXApplicationActive(_ active: Bool) {
        self.nagramiXSystemPiP.setApplicationActive(active)
    }

    func play() {
        self.nagramiXSystemPiP.setPlaybackAllowed(true)
        self.impl.play()
    }
    
    func pause() {
        self.nagramiXSystemPiP.setPlaybackAllowed(false)
        self.impl.pause()
        if self.impl is GenericEmbedImplementation || !NagramiXTabSettings.backgroundVideoPlaybackEnabled {
            self.webView.pauseAllMediaPlayback(completionHandler: nil)
        }
    }
    
    func togglePlayPause() {
        self.impl.togglePlayPause()
    }
    
    func seek(timestamp: Double) {
        self.impl.seek(timestamp: timestamp)
    }
    
    func setBaseRate(_ baseRate: Double) {
        self.impl.setBaseRate(baseRate)
    }
    
    private var watchNavigation: WKNavigation?
    private var committedDocumentURL: URL?

    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        let continuing = self.committedDocumentURL == nil || self.committedDocumentURL == webView.url
        self.committedDocumentURL = webView.url
        self.nagramiXSystemPiP.documentDidChange(continuingPlayback: continuing)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        (self.impl as? YoutubeEmbedImplementation)?.webProcessEnded()
        self.nagramiXSystemPiP.resetMediaObservation()
        self.nagramiXSystemPiP.stop()
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        self.impl.pageReady()
    }

    private func youtubeNavigationFailed(_ navigation: WKNavigation?, error: Error) {
        let failure = error as NSError
        guard !(failure.domain == NSURLErrorDomain && failure.code == NSURLErrorCancelled),
              !(failure.domain == "WebKitErrorDomain" && failure.code == 204), let youtube = self.impl as? YoutubeEmbedImplementation,
              !youtube.usesWatchPage || (navigation != nil && self.watchNavigation === navigation) else { return }
        youtube.startupFailed()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        self.youtubeNavigationFailed(navigation, error: error)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        self.youtubeNavigationFailed(navigation, error: error)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let youtube = self.impl as? YoutubeEmbedImplementation, youtube.usesWatchPage {
            guard let frame = navigationAction.targetFrame, let url = navigationAction.request.url else { decisionHandler(.cancel); return }
            let allowed = url.scheme == "https" && (!frame.isMainFrame || self.nagramiXSystemPiP.matchesWatchPage(url))
            decisionHandler(allowed ? .allow : .cancel)
            return
        }
        if let url = navigationAction.request.url, url.scheme == "embed" {
            self.impl.callback(url: url)
            decisionHandler(.cancel)
        } else if let _ = navigationAction.targetFrame {
            decisionHandler(.allow)
        } else {
            if let url = navigationAction.request.url, url.absoluteString.contains("youtube") {
                self.openUrl(url)
            }
            decisionHandler(.cancel)
        }
    }
    
    private func evaluateJavaScript(js: String, completion: ((Any?) -> Void)?) {
        Queue.mainQueue().async { [weak self] in
            self?.nagramiXJavaScriptQueue.enqueue(js, completion: completion)
        }
    }
    
    func updateYoutubeSurface(_ availability: NagramiXYoutubeAvailability) {
        self.webView.isHidden = availability == .unavailable
    }

    func notifyPlaybackControlsHidden(_ hidden: Bool) {
        if impl is YoutubeEmbedImplementation {
            self.webView.isUserInteractionEnabled = (self.impl as? YoutubeEmbedImplementation)?.usesWatchPage == true || !hidden
        }
    }

    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool) {
    }
    
    var nagramiXIsSystemPiPActive: Bool { self.nagramiXSystemPiP.keepsPlaybackActive }
    var nagramiXSystemPiPActive: Signal<Bool, NoError> { self.nagramiXSystemPiP.active.get() }

    func setNagramiXBackgroundPlayback(_ enabled: Bool) { self.nagramiXSystemPiP.setBackground(enabled) }
    func checkWatchPictureInPicture(_ completion: @escaping (Bool) -> Void) {
        self.nagramiXSystemPiP.checkWatchPictureInPicture(completion)
    }
    func setNagramiXNativePiPRestore(_ restore: ((@escaping (Bool) -> Void) -> Void)?) { self.nagramiXSystemPiP.restore = restore }

    func enterNativePictureInPicture() -> Bool {
        if let youtube = self.impl as? YoutubeEmbedImplementation, !youtube.availability.canPlayInPiP { return false }
        return self.nagramiXSystemPiP.begin()
    }
    
    func exitNativePictureInPicture() {
        self.nagramiXSystemPiP.requestExit()
    }
    
    func setNativePictureInPictureIsActive(_ value: Bool) {
    }
}

// WebKit owns the system iOS PiP window for the already loaded HTML video.
// A frame probe selects exactly one live video; no URL extraction or new player.
private final class NagramiXWebSystemPictureInPicture: NSObject, WKScriptMessageHandler {
    weak var webView: WKWebView?
    let active = ValuePromise<Bool>(false, ignoreRepeated: true)
    var restore: ((@escaping (Bool) -> Void) -> Void)?
    private(set) var isActive = false
    var requiresPlayingSource: (() -> Bool)?
    private let token = UUID().uuidString
    private var request: String?
    private var frame: WKFrameInfo?
    private var frameKey: String?
    private var candidates: [(WKFrameInfo, String, String, Bool, Double)] = []
    private var background = false
    private(set) var playbackAllowed = true
    private var backgroundFeatureEnabled = false
    private var applicationActive = true
    private(set) var actualMediaPlaying: Bool?
    private var mediaFrameKey: String?
    private var mediaArea: Double = 0.0
    private var mediaReplacement: UUID?
    var actualMediaChanged: ((Bool) -> Void)?
    var preservesWebPlayback: Bool {
        self.playbackAllowed && self.actualMediaPlaying == true
            && (self.applicationActive ? self.backgroundFeatureEnabled : self.background)
    }
    private var youtube = false
    private var pipEnabled: Bool
    private var overrideYouTube = false
    private var selecting = false
    private var presentationCheckGeneration = 0
    private var searchDeadline = DispatchTime.now()
    private weak var inlineParent: UIView?
    private var windowHost: UIView?
    var keepsPlaybackActive: Bool { self.isActive || self.request != nil }

    init(controller: WKUserContentController, isYouTube: Bool = false, pipEnabled: Bool = false, backgroundEnabled: Bool = false) {
        self.youtube = isYouTube
        self.pipEnabled = pipEnabled
        self.overrideYouTube = isYouTube && pipEnabled
        self.backgroundFeatureEnabled = backgroundEnabled
        super.init()
        controller.add(self, name: "nagramiXSystemPiP")
        let script = Self.script.replacingOccurrences(of: "__TOKEN__", with: self.token)
            .replacingOccurrences(of: "__PIP_ENABLED__", with: pipEnabled ? "true" : "false")
            .replacingOccurrences(of: "__YOUTUBE__", with: isYouTube ? "true" : "false")
            .replacingOccurrences(of: "__PAUSE_GUARD__", with: isYouTube && (pipEnabled || backgroundEnabled) ? "true" : "false")
        controller.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
    }
    private var watchId: String?
    var watchEvent: ((String, Double, Double, Int, Bool) -> Void)?

    func checkWatchPictureInPicture(_ completion: @escaping (Bool) -> Void) {
        guard self.watchId != nil, self.pipEnabled, self.webView != nil else { completion(false); return }
        self.dispatch(["command": "canEnter", "requiresPlaying": self.requiresPlayingSource?() == true]) { result in
            if case let .success(value) = result { completion(value as? Bool == true) } else { completion(false) }
        }
    }

    func matchesWatchPage(_ url: URL) -> Bool {
        guard let watchId, url.scheme == "https", url.user == nil, url.password == nil, url.port == nil || url.port == 443, let host = url.host?.lowercased(),
              ["www.youtube.com", "youtube.com", "m.youtube.com"].contains(host), url.path == "/watch" else { return false }
        return URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "v" })?.value == watchId
    }

    func loadWatchPage(id: String, position: Double) -> WKNavigation? {
        guard self.watchId == nil, let webView = self.webView, id.utf8.count == 11,
              id.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95 }) else { return nil }
        var page = URLComponents(string: "https://m.youtube.com/watch")
        var query = [URLQueryItem(name: "v", value: id)]
        if position.isFinite, position >= 1, position < Double(Int.max) {
            query.append(URLQueryItem(name: "t", value: String(Int(position))))
        }
        page?.queryItems = query
        guard let url = page?.url else { return nil }
        self.stop()
        self.resetMediaObservation()
        self.watchId = id
        let controller = webView.configuration.userContentController
        controller.removeAllUserScripts()
        controller.removeScriptMessageHandler(forName: "nagramiXSystemPiP")
        controller.add(self, contentWorld: .defaultClient, name: "nagramiXSystemPiP")
        let script = Self.watchScript.replacingOccurrences(of: "__VIDEO_ID__", with: id)
            .replacingOccurrences(of: "__TOKEN__", with: self.token)
            .replacingOccurrences(of: "__PIP_ENABLED__", with: self.pipEnabled ? "true" : "false")
        controller.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentEnd, forMainFrameOnly: true, in: .defaultClient))
        webView.isUserInteractionEnabled = true
        return webView.load(URLRequest(url: url))
    }

    func watchControl(_ command: String, value: Double?, revision: Int) {
        var data: [String: Any] = ["command": "watchControl", "action": command, "revision": revision]
        if let value, value.isFinite { data["value"] = value }
        self.dispatch(data)
    }
    private func dispatch(_ payload: [String: Any], frame: WKFrameInfo? = nil, completion: ((Result<Any, Error>) -> Void)? = nil) {
        var payload = payload
        payload["token"] = self.token
        guard let data = try? JSONSerialization.data(withJSONObject: payload), let json = String(data: data, encoding: .utf8) else { return }
        let script = "window.nagramiXNativePiPDispatch && window.nagramiXNativePiPDispatch(\(json))"
        if let completion {
            self.webView?.evaluateJavaScript(script, in: frame, in: self.watchId == nil ? .page : .defaultClient) { result in completion(result) }
        } else {
            self.webView?.evaluateJavaScript(script, in: frame, in: self.watchId == nil ? .page : .defaultClient, completionHandler: nil)
        }
    }
    func setYouTubePolicy(_ youtube: Bool, pipEnabled: Bool, backgroundEnabled: Bool) {
        guard self.youtube != youtube || self.pipEnabled != pipEnabled || self.backgroundFeatureEnabled != backgroundEnabled else { return }
        self.youtube = youtube
        self.pipEnabled = pipEnabled
        self.overrideYouTube = youtube && pipEnabled
        self.backgroundFeatureEnabled = backgroundEnabled
        if !pipEnabled && self.keepsPlaybackActive { self.stop() }
        self.updatePolicy()
    }
    private func updatePolicy(frame: WKFrameInfo? = nil) {
        self.dispatch(["command": "policy", "youtube": self.youtube, "pipEnabled": self.pipEnabled,
            "enabled": self.overrideYouTube && self.keepsPlaybackActive,
            "backgroundEnabled": self.youtube && self.background,
            "pauseGuardEnabled": self.youtube && (self.overrideYouTube || self.backgroundFeatureEnabled || self.keepsPlaybackActive)], frame: frame)
    }

    func setApplicationActive(_ active: Bool) {
        guard self.applicationActive != active else { return }
        self.applicationActive = active
        self.dispatch(["command": "application", "active": active])
        self.schedulePresentationCheck()
    }

    func resetMediaObservation() {
        self.actualMediaPlaying = nil
        self.mediaFrameKey = nil
        self.mediaArea = 0.0
        self.mediaReplacement = nil
    }

    // A DOM replacement is not a pause. Keep the existing audio owner across a short
    // gap, then release it if there is no new playing element. Never start playback here.
    private func mediaWasDetached(in key: String) {
        guard key == self.mediaFrameKey, self.mediaReplacement == nil else { return }
        self.mediaFrameKey = nil
        self.mediaArea = 0.0
        guard self.preservesWebPlayback else {
            self.actualMediaPlaying = false
            self.actualMediaChanged?(false)
            return
        }
        let generation = UUID()
        self.mediaReplacement = generation
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            guard let self, self.mediaReplacement == generation else { return }
            self.mediaReplacement = nil
            self.actualMediaPlaying = false
            self.actualMediaChanged?(false)
        }
    }

    func documentDidChange(continuingPlayback: Bool) {
        if continuingPlayback, let key = self.mediaFrameKey {
            self.mediaWasDetached(in: key)
        } else if !continuingPlayback {
            self.resetMediaObservation()
        }
        if continuingPlayback, self.request != nil, !self.isActive {
            self.findReplacement()
        } else {
            self.stop()
        }
    }

    func setPlaybackAllowed(_ allowed: Bool) {
        if self.youtube, allowed, !self.playbackAllowed, self.actualMediaPlaying == false {
            self.resetMediaObservation()
        }
        self.playbackAllowed = allowed
        if !allowed, self.mediaReplacement != nil {
            self.mediaReplacement = nil
            self.actualMediaPlaying = false
            self.actualMediaChanged?(false)
        }
        self.dispatch(["command": "playback", "enabled": allowed])
    }
    func setBackground(_ enabled: Bool) {
        guard self.background != enabled else { return }
        self.background = enabled
        self.updatePolicy()
        self.dispatch(["command": "background", "enabled": enabled])
    }
    func begin() -> Bool {
        guard self.pipEnabled, self.webView != nil, self.request == nil, !self.isActive else { return false }
        let request = UUID().uuidString
        self.request = request
        self.updatePolicy()
        self.searchDeadline = .now() + 5.0
        self.probe(request)
        return true
    }

    private func probe(_ request: String) {
        self.selecting = true
        self.candidates.removeAll()
        self.dispatch(["command": "probe", "request": request])
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            guard let self, self.request == request, self.selecting else { return }
            self.selecting = false
            let needsPlaying = self.requiresPlayingSource?() == true
            let eligible = self.candidates.filter { !needsPlaying || $0.3 }
            guard let candidate = eligible.max(by: { lhs, rhs in
                if lhs.3 != rhs.3 { return !lhs.3 }
                return lhs.4 < rhs.4
            }) else {
                if DispatchTime.now() < self.searchDeadline {
                    self.probe(request)
                } else {
                    self.request = nil
                    self.updatePolicy()
                }
                return
            }
            self.frame = candidate.0
            self.frameKey = candidate.1
            self.candidates.removeAll()
            let frameKey = candidate.1
            self.dispatch(["command": "enter", "request": request, "frameKey": frameKey, "video": candidate.2, "requiresPlaying": needsPlaying], frame: candidate.0) { [weak self] result in
                guard let self, self.request == request, self.frame === candidate.0 else { return }
                if case let .success(value) = result, value as? Bool == true {
                    if !self.isActive { self.schedulePresentationCheck() }
                } else {
                    self.retryUnavailableFrame(request: request, frameKey: frameKey)
                }
            }
        }
    }

    // WebKit can replace an iframe or change presentation mode without delivering
    // the final DOM event. Reconcile only the selected document and live request.
    private func schedulePresentationCheck() {
        self.presentationCheckGeneration &+= 1
        let generation = self.presentationCheckGeneration
        guard self.applicationActive, let request = self.request, let frame = self.frame, let key = self.frameKey else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + (self.isActive ? 1.0 : 0.2)) { [weak self] in
            guard let self, self.presentationCheckGeneration == generation, self.request == request, self.frame === frame else { return }
            self.dispatch(["command": "status", "request": request, "frameKey": key], frame: frame) { [weak self] result in
                guard let self, self.presentationCheckGeneration == generation, self.request == request, self.frame === frame else { return }
                let missing: Bool
                switch result {
                case let .success(value): missing = value as? Bool != true
                case let .failure(error): missing = (error as? WKError)?.code == .javaScriptInvalidFrameTarget
                }
                if missing {
                    if self.isActive { self.stop() }
                    else { self.retryUnavailableFrame(request: request, frameKey: key) }
                } else {
                    self.schedulePresentationCheck()
                }
            }
        }
    }

    private func retryUnavailableFrame(request: String, frameKey: String) {
        guard !self.isActive, self.request == request, self.frameKey == frameKey else { return }
        self.findReplacement()
    }

    private func findReplacement() {
        guard DispatchTime.now() < self.searchDeadline else { self.stop(); return }
        self.frame = nil
        self.frameKey = nil
        // A late completion from the old element (even in the same iframe) cannot
        // acknowledge or cancel the replacement. The original deadline still applies.
        let request = UUID().uuidString
        self.request = request
        self.probe(request)
    }

    // The gallery dismisses its view after WebKit confirms PiP. Keep the live
    // WKWebView in its own scene for that interval, including after chat reappears.
    private func keepSourceInWindow() {
        guard self.windowHost == nil, let webView = self.webView,
              let parent = webView.superview, let window = webView.window else { return }
        let inlineFrame = webView.frame
        let windowFrame = parent.convert(inlineFrame, to: window)
        let host = UIView(frame: windowFrame)
        if inlineFrame.width > 0.0, inlineFrame.height > 0.0, !windowFrame.isEmpty {
            // The gallery scales its player node. Preserve the inline viewport and its
            // visible size when moving the same WKWebView into window coordinates.
            host.bounds = inlineFrame
            host.transform = CGAffineTransform(scaleX: windowFrame.width / inlineFrame.width,
                                               y: windowFrame.height / inlineFrame.height)
        }
        host.isUserInteractionEnabled = false
        host.accessibilityElementsHidden = true
        host.clipsToBounds = true
        window.insertSubview(host, at: 0)
        self.inlineParent = parent
        self.windowHost = host
        host.addSubview(webView)
    }

    private func returnSourceToPlayer() {
        guard let host = self.windowHost else { return }
        if let webView = self.webView, webView.superview === host {
            if let parent = self.inlineParent {
                parent.addSubview(webView)
            } else {
                webView.removeFromSuperview()
            }
        }
        host.removeFromSuperview()
        self.windowHost = nil
        self.inlineParent = nil
    }

    func requestExit() {
        guard self.isActive, let request = self.request, let frame = self.frame, let key = self.frameKey else {
            self.stop()
            return
        }
        // Keep the source and listener until WebKit reports inline presentation.
        self.dispatch(["command": "stop", "request": request, "frameKey": key], frame: frame)
        self.schedulePresentationCheck()
    }

    func stop() {
        if let request = self.request, let frameKey = self.frameKey {
            self.dispatch(["command": "stop", "request": request, "frameKey": frameKey], frame: self.frame)
        }
        self.request = nil
        self.frame = nil
        self.frameKey = nil
        self.selecting = false
        self.candidates.removeAll()
        self.isActive = false
        self.returnSourceToPlayer()
        self.active.set(false)
        self.updatePolicy()
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "nagramiXSystemPiP", let body = message.body as? [String: Any], body["token"] as? String == self.token,
              let kind = body["kind"] as? String else { return }
        if self.watchId != nil {
            guard message.world == .defaultClient, message.frameInfo.isMainFrame, let url = message.frameInfo.request.url,
                  self.matchesWatchPage(url) else { return }
            if kind == "watch", let event = body["event"] as? String,
               let position = body["position"] as? Double, let duration = body["duration"] as? Double,
               let revision = body["revision"] as? Int {
                self.watchEvent?(event, position, duration, revision, body["canUsePiP"] as? Bool == true)
                return
            }
        }
        if kind == "media",
           let key = body["frameKey"] as? String, let playing = body["playing"] as? Bool,
           let ended = body["ended"] as? Bool, let area = body["area"] as? Double, area.isFinite, area >= 0.0 {
            if body["reason"] as? String == "detached" {
                self.mediaWasDetached(in: key)
                return
            }
            if let selected = self.frameKey, selected != key { return }
            // Watching a newly inserted, paused element is not a pause of the current video.
            if self.youtube, !playing, !ended,
               let reason = body["reason"] as? String, reason == "watch" || reason == "loadedmetadata" {
                return
            }
            if self.mediaReplacement != nil {
                guard playing || ended || body["reason"] as? String == "pause" else { return }
                self.mediaReplacement = nil
            }
            guard self.frameKey == key || self.mediaFrameKey == nil || self.mediaFrameKey == key || (playing && (self.actualMediaPlaying != true || area >= self.mediaArea)) else { return }
            let changed = self.actualMediaPlaying != (playing && !ended) || self.mediaFrameKey != key
            self.mediaFrameKey = key
            self.mediaArea = area
            self.actualMediaPlaying = playing && !ended
            let paused = !playing && body["reason"] as? String == "pause" || ended
            if paused { self.playbackAllowed = false }
            else if playing, body["allowed"] as? Bool == true { self.playbackAllowed = true }
            if changed || paused { self.actualMediaChanged?(paused) }
            return
        }
        if kind == "ready" {
            self.dispatch(["command": "application", "active": self.applicationActive], frame: message.frameInfo)
            self.updatePolicy(frame: message.frameInfo)
            self.dispatch(["command": "playback", "enabled": self.playbackAllowed], frame: message.frameInfo)
            self.dispatch(["command": "background", "enabled": self.background], frame: message.frameInfo)
            return
        }
        guard let request = body["request"] as? String, request == self.request,
              let frameKey = body["frameKey"] as? String else { return }
        if kind == "candidate", self.selecting, let video = body["video"] as? String,
           let playing = body["playing"] as? Bool, let area = body["area"] as? Double, area.isFinite {
            self.candidates.append((message.frameInfo, frameKey, video, playing, area))
        } else if kind == "unavailable" {
            self.retryUnavailableFrame(request: request, frameKey: frameKey)
        } else if kind == "state", frameKey == self.frameKey, let active = body["active"] as? Bool {
            if active {
                guard !self.isActive else { return }
                self.keepSourceInWindow()
                self.isActive = true
                self.schedulePresentationCheck()
                self.active.set(true)
            } else {
                let wasActive = self.isActive
                self.isActive = false
                self.frame = nil
                self.frameKey = nil
                if wasActive, body["restore"] as? Bool == true, let restore = self.restore {
                    restore { [weak self] _ in
                        guard let self, self.request == request else { return }
                        self.stop()
                    }
                } else {
                    self.stop()
                }
            }
        }
    }

    private static let watchScript = #"""
(() => {
    'use strict';
    const videoId = '__VIDEO_ID__';
    const token = '__TOKEN__';
    const frameKey = String(Math.random());
    const isWatch = () => location.protocol === 'https:' &&
        ['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(location.hostname) &&
        location.pathname === '/watch' && new URLSearchParams(location.search).get('v') === videoId;
    if (!isWatch()) return;
    const send = data => window.webkit.messageHandlers.nagramiXSystemPiP.postMessage({...data, token, frameKey});
    let video = null, sequence = 0, revision = 0, request = null, sessionVideo = null;
    let activated = false, stopping = false, pipEnabled = __PIP_ENABLED__;
    let exitTimer = null, applicationActive = null, returnedAt = null;
    let playIntent = 0;
    let previousAudioType = null;
    let reportedPageError = false;
    function pageHasError() {
        const panel = document.querySelector('.ytp-error-content-wrap, yt-playability-error-supported-renderers, ytm-player-error-message-renderer, ytd-player-error-message-renderer');
        if (!panel?.textContent.trim() || !panel.getClientRects().length || window.getComputedStyle(panel).visibility === 'hidden') return false;
        if (!reportedPageError) {
            reportedPageError = true;
            send({kind: 'watch', event: 'pageError', revision, position: 0, duration: 0});
        }
        return true;
    }
    let policyDisabledVideo = null, startWithSound = true, explicitlyPaused = false;
    const mainVideo = () => document.querySelector('#movie_player video, #player video, ytm-player video');
    let removePlaybackListeners = null, sawPlaying = false, pauseRequestedOnPage = false;
    let pointerToggle = null;
    let lastCapability = false;
    const inPiP = v => !!v && (v.webkitPresentationMode === 'picture-in-picture' || document.pictureInPictureElement === v);
    // WebKit may keep displaying an element which YouTube has removed from the page.
    const pipOwnsPlayback = () => sessionVideo && (activated || inPiP(sessionVideo));
    const playbackVideo = () => pipOwnsPlayback() ? sessionVideo : mainVideo();
    const supported = v => v && !v.disablePictureInPicture && !v.hasAttribute('disablepictureinpicture') &&
        (typeof v.webkitSupportsPresentationMode === 'function' ? v.webkitSupportsPresentationMode('picture-in-picture') :
            typeof v.requestPictureInPicture === 'function' && document.pictureInPictureEnabled);
    function canUsePiP() {
        return !!(pipEnabled && video && video === playbackVideo() && supported(video) && video.readyState >= 2 && !video.ended);
    }
    function canEnter(requiresPlaying) {
        if (pipOwnsPlayback() || !canUsePiP() || pageHasError() || (requiresPlaying && video.paused)) return false;
        const rect = video.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }
    function state(event, eventRevision = revision) {
        if (!video || video !== playbackVideo() || !isWatch()) return;
        lastCapability = canUsePiP();
        send({kind: 'watch', event, revision: eventRevision, canUsePiP: lastCapability, position: Number.isFinite(video.currentTime) ? video.currentTime : 0,
            duration: Number.isFinite(video.duration) ? video.duration : 0});
    }
    function reportPresentation() {
        if (!sessionVideo || !request) return;
        if (inPiP(sessionVideo)) {
            clearTimeout(exitTimer);
            exitTimer = null;
            if (activated) return;
            activated = true;
            if (stopping) { leave(); return; }
            send({kind: 'state', request, active: true, restore: false});
        } else if (activated) {
            if (stopping) finishPresentation();
            else if (exitTimer === null) {
                // A system close can deliver the inline notification before the media pause.
                exitTimer = setTimeout(finishPresentation, 300);
            }
        }
    }
    function finishPresentation() {
        const returnedToApp = returnedAt !== null && Date.now() - returnedAt < 1500;
        const restore = !stopping && !sessionVideo.ended && (sessionVideo.webkitPresentationMode === 'fullscreen' ||
            (applicationActive !== false && (!sessionVideo.paused || returnedToApp)));
        if (!restore && !stopping) {
            explicitlyPaused = true;
            ++playIntent;
            sessionVideo.pause();
            state('paused');
        }
        send({kind: 'state', request, active: false, restore});
        clearSession();
        bind();
    }
    const presentationEvents = ['webkitpresentationmodechanged','enterpictureinpicture','leavepictureinpicture'];
    function clearSession() {
        clearTimeout(exitTimer);
        exitTimer = null;
        returnedAt = null;
        for (const name of presentationEvents) sessionVideo?.removeEventListener(name, reportPresentation);
        request = null;
        sessionVideo = null;
        activated = false;
    }
    function leave() {
        stopping = true;
        if (!inPiP(sessionVideo)) return;
        if (sessionVideo.webkitSetPresentationMode) sessionVideo.webkitSetPresentationMode('inline');
        else document.exitPictureInPicture().catch(() => {});
    }
    function applySetting() {
        if (!video) return;
        if (!pipEnabled && !video.disablePictureInPicture) {
            video.setAttribute('disablepictureinpicture', 'nagramix-off');
            policyDisabledVideo = video;
        } else if (pipEnabled && policyDisabledVideo === video) {
            if (video.getAttribute('disablepictureinpicture') === 'nagramix-off') video.removeAttribute('disablepictureinpicture');
            policyDisabledVideo = null;
        }
    }
    function bind() {
        if (!isWatch()) return;
        // YouTube may replace the main element during buffering. Exclude recommendation thumbnails.
        const next = mainVideo();
        if (pipOwnsPlayback()) {
            if (next && next !== sessionVideo && !next.paused) next.pause();
            return;
        }
        if (pageHasError()) {
            if (video && video !== next && !video.paused) video.pause();
            return;
        }
        if (next === video) {
            if (video && lastCapability !== canUsePiP()) state('capability');
            return;
        }
        if (removePlaybackListeners) { removePlaybackListeners(); removePlaybackListeners = null; }
        if (video && !video.paused) video.pause();
        if (sessionVideo && !inPiP(sessionVideo) && !activated) {
            send({kind: 'unavailable', request});
            clearSession();
        }
        if (policyDisabledVideo && policyDisabledVideo.getAttribute('disablepictureinpicture') === 'nagramix-off') {
            policyDisabledVideo.removeAttribute('disablepictureinpicture');
        }
        policyDisabledVideo = null;
        video = next;
        sequence++;
        if (!next) {
            send({kind: 'watch', event: 'detached', revision, position: 0, duration: 0, canUsePiP: false});
            return;
        }
        next.playsInline = true;
        startWithSound = true;
        sawPlaying = false;
        pauseRequestedOnPage = false;
        pointerToggle = null;
        applySetting();
        const listeners = [];
        for (const [name, event] of [['playing','playing'], ['timeupdate','playing'], ['waiting','waiting'],
                                    ['pause','paused'], ['ended','ended'], ['error','failed'], ['seeked','seeked'],
                                    ['loadedmetadata','metadata'], ['stalled','waiting']]) {
            const listener = () => {
                if (next !== video || next !== playbackVideo() || !isWatch()) return;
                if (event === 'playing' && (next.paused || next.ended || next.seeking || next.readyState < 2)) return;
                if (event === 'playing' && explicitlyPaused && !inPiP(next)) { next.pause(); return; }
                if (event === 'playing') {
                    sawPlaying = true;
                    if (name === 'playing' && inPiP(next)) explicitlyPaused = false;
                }
                if (event === 'paused') {
                    if (!next.paused || (!sawPlaying && !pauseRequestedOnPage && !explicitlyPaused)) return;
                    ++playIntent;
                    pauseRequestedOnPage = false;
                    sawPlaying = false;
                }
                if (event === 'seeked' && next.seeking) return;
                state(event);
            };
            next.addEventListener(name, listener);
            listeners.push([name, listener]);
        }
        removePlaybackListeners = () => listeners.forEach(([name, listener]) => next.removeEventListener(name, listener));
        state('ready');
    }
    window.nagramiXNativePiPDispatch = data => {
        if (!isWatch() || data.token !== token) return false;
        if (data.command === 'application') {
            if (data.active && applicationActive === false && activated) returnedAt = Date.now();
            applicationActive = data.active === true;
            return true;
        }
        if (data.command === 'policy') {
            pipEnabled = data.pipEnabled === true;
            const audio = window.navigator?.audioSession;
            if (audio) {
                try {
                    if (data.backgroundEnabled && previousAudioType === null) {
                        previousAudioType = audio.type;
                        audio.type = 'playback';
                    } else if (!data.backgroundEnabled && previousAudioType !== null) {
                        if (audio.type === 'playback') audio.type = previousAudioType;
                        previousAudioType = null;
                    }
                } catch (_) { previousAudioType = null; }
            }
            applySetting();
            if (lastCapability !== canUsePiP()) state('capability');
            if (!pipEnabled) leave();
            return true;
        }
        if (data.command === 'watchControl' && video && video === playbackVideo()) {
            if (data.revision <= revision) return false;
            revision = data.revision;
            const element = video, operation = revision, binding = sequence;
            switch (data.action) {
            case 'recover':
            case 'play': {
                if (data.action === 'recover' && (explicitlyPaused || element.paused || element.ended)) {
                    state(element.ended ? 'ended' : 'paused');
                    break;
                }
                const intent = ++playIntent;
                explicitlyPaused = false;
                pauseRequestedOnPage = false;
                if (startWithSound) { startWithSound = false; element.muted = false; }
                if (data.action === 'recover' && !element.seeking) {
                    // Re-request the current range without replacing the MediaSource or exiting PiP.
                    const ranges = element.seekable, time = element.currentTime;
                    for (let index = 0; ranges && index < ranges.length; index++) {
                        if (ranges.start(index) <= time && time < ranges.end(index)) {
                            try { element.currentTime = time; } catch (_) { /* WebKit may evict this range. */ }
                            break;
                        }
                    }
                }
                element.play().catch(error => {
                    if (binding !== sequence || element !== playbackVideo() || intent !== playIntent || error.name === 'AbortError') return;
                    if (pipOwnsPlayback() || !pageHasError()) state(error.name === 'NotAllowedError' ? 'gesture' : 'playFailed', operation);
                });
                break;
            }
            case 'pause': ++playIntent; explicitlyPaused = true; element.pause(); break;
            case 'seek': if (Number.isFinite(data.value)) element.currentTime = data.value; break;
            case 'rate': if (Number.isFinite(data.value)) element.playbackRate = data.value; break;
            }
            return true;
        }
        if (request && request === data.request && data.frameKey === frameKey) {
            if (data.command === 'stop') { leave(); reportPresentation(); return true; }
            if (data.command === 'status') {
                // If polling first notices the return to inline, let the state message restore the gallery.
                const presenting = activated || inPiP(sessionVideo) || (!stopping && sessionVideo === mainVideo());
                reportPresentation();
                return presenting;
            }
        }
        if (data.command === 'canEnter') return canEnter(data.requiresPlaying);
        if (data.command === 'probe') {
            if (!canEnter(false)) return false;
            const rect = video.getBoundingClientRect();
            send({kind: 'candidate', request: data.request, video: String(sequence), playing: !video.paused, area: rect.width * rect.height});
            return true;
        }
        if (data.frameKey !== frameKey) return false;
        if (data.command === 'enter') {
            if (data.video !== String(sequence) || !canEnter(data.requiresPlaying)) return false;
            if (request) {
                if (!stopping || activated || inPiP(sessionVideo)) return false;
                clearSession();
            }
            request = data.request; sessionVideo = video; activated = false; stopping = false;
            for (const name of presentationEvents) sessionVideo.addEventListener(name, reportPresentation);
            const failed = () => {
                if (request !== data.request) return;
                send({kind: 'unavailable', request}); clearSession();
            };
            try {
                if (video.webkitSetPresentationMode) video.webkitSetPresentationMode('picture-in-picture');
                else video.requestPictureInPicture().then(reportPresentation, failed);
                reportPresentation();
            } catch (_) { failed(); return false; }
            return true;
        }
        return false;
    };
    // Fit the official player, including its controls, to the existing gallery viewport.
    // Other pages and consent dialogs keep their own layout.
    const style = document.createElement('style');
    style.textContent = '#movie_player.nagramix-watch-player {position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;background:black}';
    document.head?.appendChild(style);
    const isPlayControl = target => target === video || !!target?.closest?.('.ytp-play-button, .ytp-large-play-button, .ytp-cued-thumbnail-overlay, .player-control-play-pause-icon, .ytPlayerOverlayPlayButton');
    document.addEventListener('pointerdown', event => {
        if (!event.isTrusted) return;
        explicitlyPaused = false;
        pointerToggle = video && isPlayControl(event.target) ? {video, play: video.paused} : null;
        pauseRequestedOnPage = pointerToggle?.play === false;
    }, true);
    for (const name of ['touchend', 'keydown']) {
        document.addEventListener(name, event => { if (event.isTrusted) explicitlyPaused = false; }, true);
    }
    document.addEventListener('click', event => {
        if (!event.isTrusted || !video || !isWatch() || !event.target?.closest) return;
        if (isPlayControl(event.target)) {
            const play = event.detail > 0 && pointerToggle?.video === video ? pointerToggle.play : video.paused;
            pointerToggle = null;
            pauseRequestedOnPage = !play;
            if (play && video.paused) { ++playIntent; state('attempt'); }
        }
    }, true);
    document.addEventListener('keydown', event => {
        if (!event.isTrusted || !video || !event.target?.closest?.('#movie_player, #player, ytm-player')) return;
        if ([' ', 'k', 'K', 'MediaPlayPause', 'MediaPause'].includes(event.key)) pauseRequestedOnPage = !video.paused;
    }, true);
    document.addEventListener('playing', event => {
        if (event.target === video && isWatch()) video.closest('#movie_player')?.classList.add('nagramix-watch-player');
    }, true);
    function silenceInlineReplacement(event) {
        if (pipOwnsPlayback() && event.target !== sessionVideo && event.target === mainVideo()) event.target.pause();
    }
    document.addEventListener('play', silenceInlineReplacement, true);
    document.addEventListener('playing', silenceInlineReplacement, true);
    window.addEventListener('online', () => state('online'));
    new MutationObserver(bind).observe(document.documentElement, {childList:true, subtree:true, attributes:true, attributeFilter:['disablepictureinpicture']});
    send({kind: 'ready'});
    bind();
})();
"""#

    private static let script = #"""
(() => {
    const token = '__TOKEN__';
    const frameKey = String(Date.now()) + ':' + String(Math.random());
    const videos = new Map();
    const videoKeys = new WeakMap();
    let nextVideoKey = 0;
    const wired = new WeakSet();
    const playWired = new WeakSet();
    const videoPolicies = new Map();
    const framePolicies = new Map();
    const videoPrototype = typeof HTMLVideoElement !== 'undefined' ? HTMLVideoElement.prototype : null;
    const nativeSetMode = videoPrototype && videoPrototype.webkitSetPresentationMode;
    const nativeDisabled = videoPrototype && Object.getOwnPropertyDescriptor(videoPrototype, 'disablePictureInPicture');
    let current = null;
    let latestRequest = null;
    let wasActive = false;
    let background = false;
    let youtube = __YOUTUBE__;
    let pipEnabled = __PIP_ENABLED__;
    let override = false;
    let pauseGuardEnabled = __PAUSE_GUARD__;
    let backgroundProtection = false;
    let applicationInactive = false;
    let playbackAllowed = true;
    let trustedInput = false;
    const active = video => video.webkitPresentationMode === 'picture-in-picture' || document.pictureInPictureElement === video;
    const presentationSetter = video => override && typeof nativeSetMode === 'function' ? nativeSetMode : video.webkitSetPresentationMode;
    const setMode = (video, mode) => {
        const setter = presentationSetter(video);
        if (typeof setter === 'function') return setter.call(video, mode);
        return mode === 'picture-in-picture' ? video.requestPictureInPicture() : document.exitPictureInPicture();
    };
    const leave = video => {
        try {
            const result = setMode(video, 'inline');
            if (result && typeof result.catch === 'function') result.catch(() => {});
        } catch (_) {}
    };
    const playing = () => Array.from(document.querySelectorAll('video')).some(video => !video.paused && !video.ended);
    const preserveVisibility = () => background && (!youtube || playing() || (current && active(current.video)));
    const nativeHasFocus = document.hasFocus;
    try {
        if (typeof nativeHasFocus === 'function') Object.defineProperty(document, 'hasFocus', { configurable: true, value: () => youtube && backgroundProtection && preserveVisibility() ? true : nativeHasFocus.call(document) });
    } catch (_) {}
    // A trusted gesture may deliberately pause in the site's own controls. Native
    // PiP/audio-interruption pauses do not call the page's JavaScript pause method.
    const userInput = event => {
        if (!event.isTrusted) return;
        trustedInput = true;
        setTimeout(() => { trustedInput = false; }, 0);
    };
    for (const name of ['pointerdown', 'touchstart', 'keydown', 'click']) window.addEventListener(name, userInput, true);
    const hidden = Object.getOwnPropertyDescriptor(Document.prototype, 'hidden');
    const visibility = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
    try {
        if (hidden && hidden.get) Object.defineProperty(document, 'hidden', { configurable: true, get: () => preserveVisibility() ? false : hidden.get.call(document) });
        if (visibility && visibility.get) Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => preserveVisibility() ? 'visible' : visibility.get.call(document) });
    } catch (_) {}
    // Install before the site's handlers. Never call play/seek from lifecycle events.
    const lifecycle = event => {
        const nativeHidden = hidden && hidden.get ? hidden.get.call(document) : false;
        if (youtube && backgroundProtection && preserveVisibility() && (event.type !== 'blur' || nativeHidden || applicationInactive || (current && active(current.video)))) event.stopImmediatePropagation();
    };
    // Window capture runs before a document listener installed by the site.
    for (const name of ['visibilitychange', 'webkitvisibilitychange']) {
        window.addEventListener(name, lifecycle, true);
        document.addEventListener(name, lifecycle, true);
    }
    window.addEventListener('pagehide', lifecycle, true);
    window.addEventListener('blur', lifecycle, true);
    const send = data => window.webkit.messageHandlers.nagramiXSystemPiP.postMessage(Object.assign({ token, frameKey }, data));
    const mediaPrototype = typeof HTMLMediaElement !== 'undefined' ? HTMLMediaElement.prototype : videoPrototype;
    const originalPause = mediaPrototype && Object.getOwnPropertyDescriptor(mediaPrototype, 'pause');
    let pauseWrapper = null;
    let mediaVideo = null;
    const mediaWired = new WeakSet();
    const disabledBySetting = new WeakSet();
    const syncPiPSetting = video => {
        const attribute = 'disablepictureinpicture';
        if (!pipEnabled) {
            if (!video.hasAttribute(attribute)) {
                disabledBySetting.add(video);
                video.setAttribute(attribute, 'nagramix-off');
            }
            if (active(video)) leave(video);
        } else if (disabledBySetting.delete(video) && video.getAttribute(attribute) === 'nagramix-off') {
            video.removeAttribute(attribute);
        }
    };
    const videoArea = video => { const r = video.getBoundingClientRect(); return Math.max(0, r.width * r.height); };
    const selectedMedia = () => {
        if (current && current.video.isConnected && (active(current.video) || !current.video.paused && !current.video.ended)) return current.video;
        if (mediaVideo && mediaVideo.isConnected && !mediaVideo.paused && !mediaVideo.ended) return mediaVideo;
        const candidates = Array.from(document.querySelectorAll('video')).filter(v => v.readyState >= 1);
        candidates.sort((a, b) => Number(!b.paused && !b.ended) - Number(!a.paused && !a.ended) || videoArea(b) - videoArea(a));
        return candidates[0] || null;
    };
    // Ask WebKit for its playback audio session while the selected video is playing.
    // Leave a session explicitly configured by the page alone.
    let usesPlaybackAudioSession = false;
    const updateAudioSession = () => {
        try {
            const session = typeof navigator !== 'undefined' && navigator.audioSession;
            if (!session) return;
            const media = selectedMedia();
            // Keep our playback category while the same YouTube player buffers or swaps its element.
            // Native ownership, an explicit pause or an interruption still releases the session.
            const preparingYouTube = youtube && (usesPlaybackAudioSession || document.querySelectorAll('video').length > 0);
            if (background && playbackAllowed && (preparingYouTube || (media && !media.paused && !media.ended))) {
                if (session.type === 'auto') {
                    session.type = 'playback';
                    usesPlaybackAudioSession = true;
                }
            } else if (usesPlaybackAudioSession) {
                usesPlaybackAudioSession = false;
                if (session.type === 'playback') session.type = 'auto';
            }
        } catch (_) {}
    };
    const publishMedia = (video, reason) => {
        if (selectedMedia() !== video) return;
        mediaVideo = video;
        if ((reason === 'pause' && video.paused) || video.ended) playbackAllowed = false;
        updateAudioSession();
        send({ kind: 'media', playing: !video.paused && !video.ended, ended: !!video.ended,
            area: videoArea(video), reason, allowed: playbackAllowed });
    };
    const shouldBlockPause = video => {
        const nativeHidden = hidden && hidden.get ? hidden.get.call(document) : false;
        return youtube && pauseGuardEnabled && backgroundProtection && background && playbackAllowed && !trustedInput
            && !video.paused && !video.ended && selectedMedia() === video
            && (nativeHidden || applicationInactive || active(video));
    };
    const updatePrototypePause = () => {
        if (!mediaPrototype || !originalPause || typeof originalPause.value !== 'function') return;
        if (youtube && pauseGuardEnabled) {
            if (!pauseWrapper) pauseWrapper = function(...args) {
                if (shouldBlockPause(this)) { publishMedia(this, 'protected-site-pause'); return; }
                return originalPause.value.apply(this, args);
            };
            try {
                Object.defineProperty(mediaPrototype, 'pause', Object.assign({}, originalPause, { value: pauseWrapper }));
            } catch (_) {}
        } else if (pauseWrapper && mediaPrototype.pause === pauseWrapper) {
            try { Object.defineProperty(mediaPrototype, 'pause', originalPause); } catch (_) {}
        }
    };
    const watchMedia = video => {
        syncPiPSetting(video);
        if (mediaWired.has(video)) return;
        mediaWired.add(video);
        const enforcePiPSetting = () => { if (!pipEnabled && active(video)) leave(video); };
        video.addEventListener('enterpictureinpicture', enforcePiPSetting);
        video.addEventListener('webkitpresentationmodechanged', enforcePiPSetting);
        for (const name of ['play', 'playing', 'pause', 'ended', 'loadedmetadata']) {
            video.addEventListener(name, () => {
                if ((name === 'play' || name === 'playing') && (trustedInput || active(video))) playbackAllowed = true;
                publishMedia(video, name);
            });
        }
        publishMedia(video, 'watch');
    };
    const relay = data => {
        for (let i = 0; i < window.frames.length; i++) {
            try { window.frames[i].postMessage(data, '*'); } catch (_) {}
        }
    };
    const restoreVideo = (video, saved) => {
        if (saved.pauseWrapped) {
            try {
                if (saved.pauseOwn) Object.defineProperty(video, 'pause', saved.pauseOwn);
                else delete video.pause;
            } catch (_) {}
        }
        if (video.hasAttribute('disablepictureinpicture')) {
            saved.attribute = video.getAttribute('disablepictureinpicture');
            saved.disabled = true;
        }
        if (current && current.video === video) {
            current.disabled = saved.disabled;
            current.attribute = saved.attribute;
        }
        if (saved.shadowed) {
            try {
                if (saved.own) Object.defineProperty(video, 'disablePictureInPicture', Object.prototype.hasOwnProperty.call(saved.own, 'value') && saved.own.writable ? Object.assign({}, saved.own, { value: saved.disabled }) : saved.own);
                else delete video.disablePictureInPicture;
            } catch (_) {}
        }
        try {
            if (nativeDisabled && nativeDisabled.set) nativeDisabled.set.call(video, saved.disabled);
            else video.disablePictureInPicture = saved.disabled;
        } catch (_) {}
        if (saved.attribute !== null) video.setAttribute('disablepictureinpicture', saved.attribute);
        else video.removeAttribute('disablepictureinpicture');
    };
    const restoreFrame = (frame, saved) => {
        const value = frame.getAttribute('allow');
        if (saved.forced !== null && value !== saved.forced) saved.original = value;
        if (saved.original === null) frame.removeAttribute('allow');
        else frame.setAttribute('allow', saved.original);
    };
    const allowFrame = frame => {
        let saved = framePolicies.get(frame);
        const value = frame.getAttribute('allow');
        if (!saved) { saved = { original: value, forced: null }; framePolicies.set(frame, saved); }
        else if (value !== saved.forced) saved.original = value;
        const parts = (value || '').split(';').map(part => part.trim()).filter(part => part && !/^picture-in-picture(?:\s|$)/i.test(part));
        parts.push('picture-in-picture *');
        saved.forced = parts.join('; ');
        if (value !== saved.forced) frame.setAttribute('allow', saved.forced);
    };
    const allowVideo = video => {
        let saved = videoPolicies.get(video);
        if (!saved) {
            saved = { disabled: video.disablePictureInPicture, attribute: video.getAttribute('disablepictureinpicture'), own: Object.getOwnPropertyDescriptor(video, 'disablePictureInPicture'), shadowed: false };
            videoPolicies.set(video, saved);
            if (!playWired.has(video)) {
                playWired.add(video);
                video.addEventListener('play', event => { if (event.isTrusted) playbackAllowed = true; });
            }
            const pause = video.pause;
            if (typeof pause === 'function') {
                saved.pauseOwn = Object.getOwnPropertyDescriptor(video, 'pause');
                try {
                    Object.defineProperty(video, 'pause', { configurable: true, writable: true, value: function(...args) {
                        if (this === video && shouldBlockPause(video)) { publishMedia(video, 'protected-site-pause'); return; }
                        return pause.apply(this, args);
                    } });
                    saved.pauseWrapped = true;
                } catch (_) {}
            }
            try {
                Object.defineProperty(video, 'disablePictureInPicture', {
                    configurable: true,
                    get: () => false,
                    set: value => { saved.disabled = !!value; saved.attribute = value ? '' : null; video.removeAttribute('disablepictureinpicture'); }
                });
                saved.shadowed = true;
            } catch (_) {}
        } else if (video.hasAttribute('disablepictureinpicture')) {
            saved.attribute = video.getAttribute('disablepictureinpicture');
            saved.disabled = true;
        }
        video.removeAttribute('disablepictureinpicture');
    };
    const refreshOverrides = () => {
        updatePrototypePause();
        if (mediaVideo && !mediaVideo.isConnected) {
            const detached = mediaVideo;
            mediaVideo = null;
            updateAudioSession();
            send({ kind: 'media', playing: false, ended: false, area: videoArea(detached), reason: 'detached', allowed: playbackAllowed });
        }
        for (const [video, saved] of videoPolicies) {
            if (!override || (!video.isConnected && (!current || current.video !== video))) {
                restoreVideo(video, saved);
                videoPolicies.delete(video);
            }
        }
        for (const [frame, saved] of framePolicies) {
            if (!override || !frame.isConnected) { restoreFrame(frame, saved); framePolicies.delete(frame); }
        }
        document.querySelectorAll('video').forEach(watchMedia);
        if (override) {
            document.querySelectorAll('video').forEach(allowVideo);
            document.querySelectorAll('iframe').forEach(allowFrame);
        }
    };
    if (typeof MutationObserver !== 'undefined') {
        new MutationObserver(records => {
            for (const record of records) {
                if (record.type === 'attributes') {
                    if (record.attributeName === 'disablepictureinpicture') {
                        if (!pipEnabled) syncPiPSetting(record.target);
                        else if (videoPolicies.has(record.target)) allowVideo(record.target);
                    }
                    else if (record.attributeName === 'allow' && framePolicies.has(record.target)) allowFrame(record.target);
                }
            }
            const relevantNode = node => node.nodeType === 1 && (node.matches('video,iframe') || node.querySelector('video,iframe'));
            if (records.some(record => record.type === 'childList' && [...record.addedNodes, ...record.removedNodes].some(relevantNode))) refreshOverrides();
        }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ['disablepictureinpicture', 'allow'] });
    }
    const report = (video, unavailable = false) => {
        if (!current || current.video !== video) {
            if (active(video)) leave(video);
            return;
        }
        const lostBeforePresentation = !wasActive && !video.isConnected;
        if (lostBeforePresentation && active(video)) leave(video);
        const on = !lostBeforePresentation && active(video);
        if (on && wasActive) return;
        const request = current.request;
        const restore = !on && wasActive && !current.stopping && !video.paused && !video.ended;
        wasActive = on;
        if (!on) {
            if (!videoPolicies.has(video)) {
                video.disablePictureInPicture = current.disabled;
                if (current.attribute !== null) video.setAttribute('disablepictureinpicture', current.attribute);
                else video.removeAttribute('disablepictureinpicture');
            }
            current = null;
            latestRequest = null;
            refreshOverrides();
        }
        send({ kind: (unavailable || lostBeforePresentation) && !on ? 'unavailable' : 'state', request, active: on, restore });
    };
    window.nagramiXNativePiPDispatch = data => {
        if (!data || data.token !== token) return false;
        if (data.command === 'policy') {
            const nextPiP = data.pipEnabled === true;
            const nextYouTube = data.youtube === true;
            const nextOverride = nextYouTube && data.enabled === true;
            const nextGuard = nextYouTube && data.pauseGuardEnabled === true;
            const changed = pipEnabled !== nextPiP || youtube !== nextYouTube || override !== nextOverride || pauseGuardEnabled !== nextGuard;
            pipEnabled = nextPiP;
            youtube = nextYouTube;
            override = nextOverride;
            pauseGuardEnabled = nextGuard;
            backgroundProtection = nextYouTube && data.backgroundEnabled === true;
            if (changed) refreshOverrides();
            relay(data);
            return true;
        }
        if (data.command === 'application') {
            applicationInactive = data.active !== true;
            relay(data);
            return true;
        }
        if (data.command === 'playback') {
            playbackAllowed = data.enabled === true;
            updateAudioSession();
            relay(data);
            return true;
        }
        if (data.command === 'background') {
            background = data.enabled === true;
            updateAudioSession();
            relay(data);
            return true;
        }
        if (data.command === 'probe') {
            if (!pipEnabled) return false;
            if (current && (wasActive || current.stopping) && !active(current.video)) report(current.video);
            if (!current) {
                latestRequest = data.request;
                videos.clear();
                document.querySelectorAll('video').forEach(video => {
                    if (video.ended || video.readyState < 2 || videoArea(video) <= 0 || (typeof presentationSetter(video) !== 'function' &&
                        (typeof video.requestPictureInPicture !== 'function' || typeof document.exitPictureInPicture !== 'function'))) return;
                    if (!videoKeys.has(video)) videoKeys.set(video, String(nextVideoKey++));
                    const key = videoKeys.get(video);
                    videos.set(key, video);
                    const rect = video.getBoundingClientRect();
                    send({ kind: 'candidate', request: data.request, video: key, playing: !video.paused && !video.ended, area: Math.max(0, rect.width * rect.height) });
                });
            }
            relay(data);
            return true;
        }
        if (data.frameKey !== frameKey) return false;
        if (data.command === 'status') {
            if (!current || current.request !== data.request) return false;
            const video = current.video;
            if (active(video) || wasActive) report(video);
            else if (!video.isConnected || video.ended || (video.paused && playing() && selectedMedia() !== video)) report(video, true);
            return true;
        }
        if (data.command === 'enter') {
            if (!pipEnabled || current || data.request !== latestRequest) return false;
            const video = videos.get(data.video);
            if (!video || !video.isConnected || video.ended || video.readyState < 2 || videoArea(video) <= 0 || (data.requiresPlaying && video.paused)) {
                send({ kind: 'unavailable', request: data.request });
                return false;
            }
            if (youtube && !override && video.disablePictureInPicture) return false;
            current = { video, request: data.request, disabled: video.disablePictureInPicture, attribute: video.getAttribute('disablepictureinpicture') };
            if (!videoPolicies.has(video)) {
                if (video.getAttribute('disablepictureinpicture') === 'nagramix-off') video.removeAttribute('disablepictureinpicture');
                video.removeAttribute('disablepictureinpicture');
            }
            if (!wired.has(video)) {
                wired.add(video);
                const changed = () => setTimeout(() => {
                    if (active(video) || (current && current.video === video && (wasActive || current.stopping))) report(video);
                }, 0);
                for (const event of ['webkitpresentationmodechanged', 'enterpictureinpicture', 'leavepictureinpicture'])
                    video.addEventListener(event, changed);
            }
            const session = current;
            try {
                const started = setMode(video, 'picture-in-picture');
                if (started && typeof started.then === 'function') {
                    started.then(() => {
                        if (current === session && active(video)) report(video);
                    }, error => {
                        if (current === session) report(video, !video.isConnected || error?.name === 'InvalidStateError' || error?.name === 'AbortError');
                    });
                }
            }
            catch (error) {
                report(video, !video.isConnected || error?.name === 'InvalidStateError' || error?.name === 'AbortError');
            }
            return true;
        }
        if (data.command === 'stop') {
            if (latestRequest === data.request) latestRequest = null;
            if (!current || current.request !== data.request) return false;
            const video = current.video;
            current.stopping = true;
            leave(video);
            report(video);
            return true;
        }
        return false;
    };
    window.addEventListener('message', event => window.nagramiXNativePiPDispatch(event.data));
    // Install before page scripts can cache HTMLMediaElement.prototype.pause.
    // The wrapper forwards unchanged until an authorized source needs protection.
    refreshOverrides();
    send({ kind: 'ready' });
})();
"""#
}

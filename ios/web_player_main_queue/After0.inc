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
        let systemPiP = NagramiXWebSystemPictureInPicture(controller: userContentController, isYouTube: impl is YoutubeEmbedImplementation, pipEnabled: true, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
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

        self.nagramiXSystemPiP.setYouTubePolicy(self.impl is YoutubeEmbedImplementation, pipEnabled: true, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.nagramiXSystemPiP.setYouTubePolicy(self.impl is YoutubeEmbedImplementation, pipEnabled: true, backgroundEnabled: NagramiXTabSettings.backgroundVideoPlaybackEnabled)
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
        guard self.impl is YoutubeEmbedImplementation,
              let actual = self.nagramiXSystemPiP.actualMediaPlaying else { self.statusValue.set(status); return }
        let playback: MediaPlayerPlaybackStatus
        switch status.status {
        case .playing where !actual || !self.nagramiXSystemPiP.playbackAllowed:
            playback = .paused
        case .paused where actual && self.nagramiXSystemPiP.preservesYouTubePlayback:
            playback = .playing
        case let .buffering(initial, _, progress, display) where !actual || !self.nagramiXSystemPiP.playbackAllowed:
            playback = .buffering(initial: initial, whilePlaying: false, progress: progress, display: display)
        case let .buffering(initial, false, progress, display) where actual && self.nagramiXSystemPiP.preservesYouTubePlayback:
            playback = .buffering(initial: initial, whilePlaying: true, progress: progress, display: display)
        default:
            playback = status.status
        }
        self.statusValue.set(MediaPlayerStatus(generationTimestamp: status.generationTimestamp, duration: status.duration,
            dimensions: status.dimensions, timestamp: status.timestamp, baseRate: status.baseRate,
            seekId: status.seekId, status: playback, soundEnabled: status.soundEnabled))
    }

    var isYouTube: Bool { self.impl is YoutubeEmbedImplementation }

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
    
    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        self.nagramiXSystemPiP.resetMediaObservation()
        self.nagramiXSystemPiP.stop()
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        self.nagramiXSystemPiP.resetMediaObservation()
        self.nagramiXSystemPiP.stop()
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        self.impl.pageReady()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        if let error = error as? WKError, error.code.rawValue == 204 {
            return
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
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
    
    func notifyPlaybackControlsHidden(_ hidden: Bool) {
        if impl is YoutubeEmbedImplementation {
            self.webView.isUserInteractionEnabled = !hidden
        }
    }

    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool) {
    }
    
    var nagramiXIsSystemPiPActive: Bool { self.nagramiXSystemPiP.keepsPlaybackActive }
    var nagramiXSystemPiPActive: Signal<Bool, NoError> { self.nagramiXSystemPiP.active.get() }

    func setNagramiXBackgroundPlayback(_ enabled: Bool) { self.nagramiXSystemPiP.setBackground(enabled) }
    func setNagramiXNativePiPRestore(_ restore: ((@escaping (Bool) -> Void) -> Void)?) { self.nagramiXSystemPiP.restore = restore }

    func enterNativePictureInPicture() -> Bool {
        return self.nagramiXSystemPiP.begin()
    }
    
    func exitNativePictureInPicture() {
        self.nagramiXSystemPiP.stop()
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
    var actualMediaChanged: ((Bool) -> Void)?
    var preservesYouTubePlayback: Bool { self.youtube && self.background && !self.applicationActive && self.playbackAllowed && self.actualMediaPlaying == true }
    private var youtube = false
    private var overrideYouTube = false
    private var selecting = false
    var keepsPlaybackActive: Bool { self.isActive || self.request != nil }

    init(controller: WKUserContentController, isYouTube: Bool = false, pipEnabled: Bool = false, backgroundEnabled: Bool = false) {
        self.youtube = isYouTube
        self.overrideYouTube = isYouTube && pipEnabled
        self.backgroundFeatureEnabled = backgroundEnabled
        super.init()
        controller.add(self, name: "nagramiXSystemPiP")
        let script = Self.script.replacingOccurrences(of: "__TOKEN__", with: self.token)
            .replacingOccurrences(of: "__YOUTUBE__", with: isYouTube ? "true" : "false")
            .replacingOccurrences(of: "__PAUSE_GUARD__", with: isYouTube && (pipEnabled || backgroundEnabled) ? "true" : "false")
        controller.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
    }
    private func dispatch(_ payload: [String: Any], frame: WKFrameInfo? = nil) {
        var payload = payload
        payload["token"] = self.token
        guard let data = try? JSONSerialization.data(withJSONObject: payload), let json = String(data: data, encoding: .utf8) else { return }
        self.webView?.evaluateJavaScript("window.nagramiXNativePiPDispatch && window.nagramiXNativePiPDispatch(\(json))", in: frame, in: .page, completionHandler: nil)
    }
    func setYouTubePolicy(_ youtube: Bool, pipEnabled: Bool, backgroundEnabled: Bool) {
        guard self.youtube != youtube || self.overrideYouTube != (youtube && pipEnabled) || self.backgroundFeatureEnabled != backgroundEnabled else { return }
        self.youtube = youtube
        self.overrideYouTube = youtube && pipEnabled
        self.backgroundFeatureEnabled = backgroundEnabled
        self.updatePolicy()
    }
    private func updatePolicy(frame: WKFrameInfo? = nil) {
        self.dispatch(["command": "policy", "youtube": self.youtube,
            "enabled": self.overrideYouTube && (self.background || self.keepsPlaybackActive),
            "backgroundEnabled": self.youtube && self.background,
            "pauseGuardEnabled": self.youtube && (self.overrideYouTube || self.backgroundFeatureEnabled || self.keepsPlaybackActive)], frame: frame)
    }

    func setApplicationActive(_ active: Bool) {
        guard self.applicationActive != active else { return }
        self.applicationActive = active
        self.dispatch(["command": "application", "active": active])
    }

    func resetMediaObservation() {
        self.actualMediaPlaying = nil
        self.mediaFrameKey = nil
        self.mediaArea = 0.0
    }
    func setPlaybackAllowed(_ allowed: Bool) {
        self.playbackAllowed = allowed
        self.dispatch(["command": "playback", "enabled": allowed])
    }
    func setBackground(_ enabled: Bool) {
        guard self.background != enabled else { return }
        self.background = enabled
        self.updatePolicy()
        self.dispatch(["command": "background", "enabled": enabled])
    }
    func begin() -> Bool {
        guard self.webView != nil, self.request == nil, !self.isActive else { return false }
        let request = UUID().uuidString
        self.request = request
        self.updatePolicy()
        self.selecting = true
        self.candidates.removeAll()
        self.dispatch(["command": "probe", "request": request])
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            guard let self, self.request == request, self.selecting else { return }
            self.selecting = false
            guard let candidate = self.candidates.max(by: { lhs, rhs in
                if lhs.3 != rhs.3 { return !lhs.3 }
                return lhs.4 < rhs.4
            }) else { self.request = nil; self.updatePolicy(); return }
            self.frame = candidate.0
            self.frameKey = candidate.1
            self.candidates.removeAll()
            self.dispatch(["command": "enter", "request": request, "frameKey": candidate.1, "video": candidate.2], frame: candidate.0)
        }
        return true
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
        self.active.set(false)
        self.updatePolicy()
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "nagramiXSystemPiP", let body = message.body as? [String: Any], body["token"] as? String == self.token,
              let kind = body["kind"] as? String else { return }
        if kind == "media", self.youtube,
           let key = body["frameKey"] as? String, let playing = body["playing"] as? Bool,
           let ended = body["ended"] as? Bool, let area = body["area"] as? Double, area.isFinite, area >= 0.0 {
            if let selected = self.frameKey, selected != key { return }
            guard self.mediaFrameKey == nil || self.mediaFrameKey == key || (playing && (self.actualMediaPlaying != true || area >= self.mediaArea)) else { return }
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
        } else if kind == "state", frameKey == self.frameKey, let active = body["active"] as? Bool {
            if active {
                self.isActive = true
                self.active.set(true)
            } else {
                let wasActive = self.isActive
                self.isActive = false
                self.request = nil
                self.frame = nil
                self.frameKey = nil
                self.updatePolicy()
                if wasActive, body["restore"] as? Bool == true, let restore = self.restore {
                    restore { [weak self] _ in self?.active.set(false) }
                } else {
                    self.active.set(false)
                }
            }
        }
    }

    private static let script = #"""
(() => {
    const token = '__TOKEN__';
    const frameKey = String(Date.now()) + ':' + String(Math.random());
    const videos = new Map();
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
    let override = false;
    let pauseGuardEnabled = __PAUSE_GUARD__;
    let backgroundProtection = false;
    let applicationInactive = false;
    let playbackAllowed = true;
    let trustedInput = false;
    const active = video => video.webkitPresentationMode === 'picture-in-picture' || document.pictureInPictureElement === video;
    const presentationSetter = video => override && typeof nativeSetMode === 'function' ? nativeSetMode : video.webkitSetPresentationMode;
    const setMode = (video, mode) => presentationSetter(video).call(video, mode);
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
    const videoArea = video => { const r = video.getBoundingClientRect(); return Math.max(0, r.width * r.height); };
    const selectedMedia = () => {
        if (current) return current.video;
        if (mediaVideo && mediaVideo.isConnected && !mediaVideo.paused && !mediaVideo.ended) return mediaVideo;
        const candidates = Array.from(document.querySelectorAll('video')).filter(v => v.readyState >= 1);
        candidates.sort((a, b) => Number(!b.paused && !b.ended) - Number(!a.paused && !a.ended) || videoArea(b) - videoArea(a));
        return candidates[0] || null;
    };
    const publishMedia = (video, reason) => {
        if (!youtube || selectedMedia() !== video) return;
        mediaVideo = video;
        if ((reason === 'pause' && video.paused) || video.ended) playbackAllowed = false;
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
        if (!youtube || mediaWired.has(video)) return;
        mediaWired.add(video);
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
        if (youtube && mediaVideo && !selectedMedia()) {
            const detached = mediaVideo;
            mediaVideo = null;
            playbackAllowed = false;
            send({ kind: 'media', playing: false, ended: true, area: videoArea(detached), reason: 'detached', allowed: false });
        }
        if (youtube) document.querySelectorAll('video').forEach(watchMedia);
        for (const [video, saved] of videoPolicies) {
            if (!override || (!video.isConnected && (!current || current.video !== video))) {
                restoreVideo(video, saved);
                videoPolicies.delete(video);
            }
        }
        for (const [frame, saved] of framePolicies) {
            if (!override || !frame.isConnected) { restoreFrame(frame, saved); framePolicies.delete(frame); }
        }
        if (override) {
            document.querySelectorAll('video').forEach(allowVideo);
            document.querySelectorAll('iframe').forEach(allowFrame);
        }
    };
    if (typeof MutationObserver !== 'undefined') {
        new MutationObserver(records => {
            if (!youtube && !override) return;
            for (const record of records) {
                if (record.type === 'attributes') {
                    if (record.attributeName === 'disablepictureinpicture' && videoPolicies.has(record.target)) allowVideo(record.target);
                    else if (record.attributeName === 'allow' && framePolicies.has(record.target)) allowFrame(record.target);
                }
            }
            const relevantNode = node => node.nodeType === 1 && (node.matches('video,iframe') || node.querySelector('video,iframe'));
            if (records.some(record => record.type === 'childList' && [...record.addedNodes, ...record.removedNodes].some(relevantNode))) refreshOverrides();
        }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ['disablepictureinpicture', 'allow'] });
    }
    const report = video => {
        if (!current || current.video !== video) {
            if (active(video)) { try { setMode(video, 'inline'); } catch (_) {} }
            return;
        }
        const on = active(video);
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
        send({ kind: 'state', request, active: on, restore });
    };
    window.nagramiXNativePiPDispatch = data => {
        if (!data || data.token !== token) return false;
        if (data.command === 'policy') {
            const nextYouTube = data.youtube === true;
            const nextOverride = nextYouTube && data.enabled === true;
            const nextGuard = nextYouTube && data.pauseGuardEnabled === true;
            const changed = youtube !== nextYouTube || override !== nextOverride || pauseGuardEnabled !== nextGuard;
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
            relay(data);
            return true;
        }
        if (data.command === 'background') {
            background = data.enabled === true;
            relay(data);
            return true;
        }
        if (data.command === 'probe') {
            if (!current) {
                latestRequest = data.request;
                videos.clear();
                Array.from(document.querySelectorAll('video')).forEach((video, index) => {
                    if (typeof presentationSetter(video) !== 'function' || video.readyState < 1) return;
                    const key = String(index);
                    videos.set(key, video);
                    const rect = video.getBoundingClientRect();
                    send({ kind: 'candidate', request: data.request, video: key, playing: !video.paused && !video.ended, area: Math.max(0, rect.width * rect.height) });
                });
            }
            relay(data);
            return true;
        }
        if (data.frameKey !== frameKey) return false;
        if (data.command === 'enter') {
            if (current || data.request !== latestRequest) return false;
            const video = videos.get(data.video);
            if (!video || (youtube && !override && video.disablePictureInPicture)) return false;
            current = { video, request: data.request, disabled: video.disablePictureInPicture, attribute: video.getAttribute('disablepictureinpicture') };
            if (!videoPolicies.has(video)) {
                video.disablePictureInPicture = false;
                video.removeAttribute('disablepictureinpicture');
            }
            if (!wired.has(video)) {
                wired.add(video);
                video.addEventListener('webkitpresentationmodechanged', () => setTimeout(() => report(video), 0));
            }
            try { setMode(video, 'picture-in-picture'); }
            catch (_) { report(video); return false; }
            return true;
        }
        if (data.command === 'stop') {
            if (latestRequest === data.request) latestRequest = null;
            if (!current || current.request !== data.request) return false;
            const video = current.video;
            current.stopping = true;
            try { setMode(video, 'inline'); } catch (_) {}
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

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
    private let nagramiXSystemPiP: NagramiXWebSystemPictureInPicture
    private var nagramiXPolicyObserver: NSObjectProtocol?
    private let webView: WKWebView
    
    private let semaphore = DispatchSemaphore(value: 0)
    private let queue = Queue()
    
    init(impl: WebEmbedImplementation, intrinsicDimensions: CGSize, openUrl: @escaping (URL) -> Void) {
        self.impl = impl
        self.intrinsicDimensions = intrinsicDimensions
        self.openUrl = openUrl
        
        let userContentController = WKUserContentController()
        self.nagramiXSystemPiP = NagramiXWebSystemPictureInPicture(controller: userContentController)
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
        self.webView = WKWebView(frame: frame, configuration: configuration)
        self.nagramiXSystemPiP.webView = self.webView
        
        super.init()
        self.frame = frame

        self.nagramiXSystemPiP.setYouTubeOverride(self.impl is YoutubeEmbedImplementation, enabled: NagramiXTabSettings.videoPiPSwipeEnabled)
        self.nagramiXPolicyObserver = NotificationCenter.default.addObserver(forName: NagramiXTabSettings.changedNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.nagramiXSystemPiP.setYouTubeOverride(self.impl is YoutubeEmbedImplementation, enabled: NagramiXTabSettings.videoPiPSwipeEnabled)
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
        
        self.impl.setup(self.webView, userContentController: userContentController, evaluateJavaScript: { [weak self] js, completion in
            self?.evaluateJavaScript(js: js, completion: completion)
        }, updateStatus: { [weak self] status in
            self?.statusValue.set(status)
        }, onPlaybackStarted: { [weak self] in
            self?.readyValue.set(true)
        })
    }
    
    deinit {
        if let observer = self.nagramiXPolicyObserver { NotificationCenter.default.removeObserver(observer) }
        self.nagramiXSystemPiP.stop()
        self.webView.configuration.userContentController.removeScriptMessageHandler(forName: "nagramiXSystemPiP")
        let webView = self.webView
        Queue.mainQueue().after(1.0) {
            print(webView.debugDescription)
        }
        func disableGestures(view: UIView) {
            if let recognizers = view.gestureRecognizers {
                for recognizer in recognizers {
                    recognizer.isEnabled = false
                }
            }
            for subview in view.subviews {
                disableGestures(view: subview)
            }
        }
        
        disableGestures(view: self.webView)
    }
    
    func play() {
        self.impl.play()
    }
    
    func pause() {
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
        self.nagramiXSystemPiP.stop()
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
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
        self.queue.async { [weak self] in
            if let strongSelf = self {
                let impl = {
                    strongSelf.webView.evaluateJavaScript(js, completionHandler: { (result, _) in
                        strongSelf.semaphore.signal()
                        if let completion = completion {
                            completion(result)
                        }
                    })
                }
                
                Queue.mainQueue().async(impl)
                strongSelf.semaphore.wait()
            }
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
    private var youtube = false
    private var overrideYouTube = false
    private var selecting = false
    var keepsPlaybackActive: Bool { self.isActive || self.request != nil }

    init(controller: WKUserContentController) {
        super.init()
        controller.add(self, name: "nagramiXSystemPiP")
        let script = Self.script.replacingOccurrences(of: "__TOKEN__", with: self.token)
        controller.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
    }
    private func dispatch(_ payload: [String: Any], frame: WKFrameInfo? = nil) {
        var payload = payload
        payload["token"] = self.token
        guard let data = try? JSONSerialization.data(withJSONObject: payload), let json = String(data: data, encoding: .utf8) else { return }
        self.webView?.evaluateJavaScript("window.nagramiXNativePiPDispatch && window.nagramiXNativePiPDispatch(\(json))", in: frame, in: .page, completionHandler: nil)
    }
    func setYouTubeOverride(_ youtube: Bool, enabled: Bool) {
        guard self.youtube != youtube || self.overrideYouTube != (youtube && enabled) else { return }
        self.youtube = youtube
        self.overrideYouTube = youtube && enabled
        self.updatePolicy()
    }
    private func updatePolicy(frame: WKFrameInfo? = nil) {
        self.dispatch(["command": "policy", "youtube": self.youtube, "enabled": self.overrideYouTube && (self.background || self.keepsPlaybackActive)], frame: frame)
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
        if kind == "ready" {
            self.updatePolicy(frame: message.frameInfo)
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
    const videoPolicies = new Map();
    const framePolicies = new Map();
    const videoPrototype = typeof HTMLVideoElement !== 'undefined' ? HTMLVideoElement.prototype : null;
    const nativeSetMode = videoPrototype && videoPrototype.webkitSetPresentationMode;
    const nativeDisabled = videoPrototype && Object.getOwnPropertyDescriptor(videoPrototype, 'disablePictureInPicture');
    let current = null;
    let latestRequest = null;
    let wasActive = false;
    let background = false;
    let youtube = false;
    let override = false;
    const active = video => video.webkitPresentationMode === 'picture-in-picture' || document.pictureInPictureElement === video;
    const presentationSetter = video => override && typeof nativeSetMode === 'function' ? nativeSetMode : video.webkitSetPresentationMode;
    const setMode = (video, mode) => presentationSetter(video).call(video, mode);
    const playing = () => Array.from(document.querySelectorAll('video')).some(video => !video.paused && !video.ended);
    const preserveVisibility = () => background && (!youtube || playing() || (current && active(current.video)));
    const hidden = Object.getOwnPropertyDescriptor(Document.prototype, 'hidden');
    const visibility = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
    try {
        if (hidden && hidden.get) Object.defineProperty(document, 'hidden', { configurable: true, get: () => preserveVisibility() ? false : hidden.get.call(document) });
        if (visibility && visibility.get) Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => preserveVisibility() ? 'visible' : visibility.get.call(document) });
    } catch (_) {}
    // Install before the site's handlers. Never call play/seek from lifecycle events.
    const lifecycle = event => {
        const nativeHidden = hidden && hidden.get ? hidden.get.call(document) : false;
        if (youtube && override && preserveVisibility() && (event.type !== 'blur' || nativeHidden || (current && active(current.video)))) event.stopImmediatePropagation();
    };
    document.addEventListener('visibilitychange', lifecycle, true);
    window.addEventListener('pagehide', lifecycle, true);
    window.addEventListener('blur', lifecycle, true);
    const send = data => window.webkit.messageHandlers.nagramiXSystemPiP.postMessage(Object.assign({ token, frameKey }, data));
    const relay = data => {
        for (let i = 0; i < window.frames.length; i++) {
            try { window.frames[i].postMessage(data, '*'); } catch (_) {}
        }
    };
    const restoreVideo = (video, saved) => {
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
            if (!override) return;
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
            const changed = youtube !== nextYouTube || override !== nextOverride;
            youtube = nextYouTube;
            override = nextOverride;
            if (changed) refreshOverrides();
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
    send({ kind: 'ready' });
})();
"""#
}

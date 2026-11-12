import Foundation
import UIKit
import AsyncDisplayKit
import SwiftSignalKit
@preconcurrency import WebKit
import TelegramCore
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
    private var selecting = false
    var keepsPlaybackActive: Bool { self.isActive || self.request != nil }

    init(controller: WKUserContentController) {
        super.init()
        controller.add(self, name: "nagramiXSystemPiP")
        let script = Self.script.replacingOccurrences(of: "__TOKEN__", with: self.token)
        controller.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentEnd, forMainFrameOnly: false))
    }
    private func dispatch(_ payload: [String: Any], frame: WKFrameInfo? = nil) {
        var payload = payload
        payload["token"] = self.token
        guard let data = try? JSONSerialization.data(withJSONObject: payload), let json = String(data: data, encoding: .utf8) else { return }
        self.webView?.evaluateJavaScript("window.nagramiXNativePiPDispatch && window.nagramiXNativePiPDispatch(\(json))", in: frame, in: .page, completionHandler: nil)
    }
    func setBackground(_ enabled: Bool) {
        self.background = enabled
        self.dispatch(["command": "background", "enabled": enabled])
    }
    func begin() -> Bool {
        guard self.webView != nil, self.request == nil, !self.isActive else { return false }
        let request = UUID().uuidString
        self.request = request
        self.selecting = true
        self.candidates.removeAll()
        self.dispatch(["command": "probe", "request": request])
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            guard let self, self.request == request, self.selecting else { return }
            self.selecting = false
            guard let candidate = self.candidates.max(by: { lhs, rhs in
                if lhs.3 != rhs.3 { return !lhs.3 }
                return lhs.4 < rhs.4
            }) else { self.request = nil; return }
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
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "nagramiXSystemPiP", let body = message.body as? [String: Any], body["token"] as? String == self.token,
              let kind = body["kind"] as? String else { return }
        if kind == "ready" {
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
    let current = null;
    let latestRequest = null;
    let wasActive = false;
    let background = false;
    const hidden = Object.getOwnPropertyDescriptor(Document.prototype, 'hidden');
    const visibility = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
    try {
        if (hidden && hidden.get) Object.defineProperty(document, 'hidden', { configurable: true, get: () => background ? false : hidden.get.call(document) });
        if (visibility && visibility.get) Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => background ? 'visible' : visibility.get.call(document) });
    } catch (_) {}
    const send = data => window.webkit.messageHandlers.nagramiXSystemPiP.postMessage(Object.assign({ token, frameKey }, data));
    const relay = data => {
        for (let i = 0; i < window.frames.length; i++) {
            try { window.frames[i].postMessage(data, '*'); } catch (_) {}
        }
    };
    const active = video => video.webkitPresentationMode === 'picture-in-picture' || document.pictureInPictureElement === video;
    const report = video => {
        if (!current || current.video !== video) {
            if (active(video)) { try { video.webkitSetPresentationMode('inline'); } catch (_) {} }
            return;
        }
        const on = active(video);
        const request = current.request;
        const restore = !on && wasActive && !current.stopping && !video.paused && !video.ended;
        wasActive = on;
        if (!on) {
            video.disablePictureInPicture = current.disabled;
            if (current.hadAttribute) video.setAttribute('disablepictureinpicture', '');
            current = null;
            latestRequest = null;
        }
        send({ kind: 'state', request, active: on, restore });
    };
    window.nagramiXNativePiPDispatch = data => {
        if (!data || data.token !== token) return false;
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
                    if (typeof video.webkitSetPresentationMode !== 'function' || video.readyState < 1) return;
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
            if (!video) return false;
            current = { video, request: data.request, disabled: video.disablePictureInPicture, hadAttribute: video.hasAttribute('disablepictureinpicture') };
            video.disablePictureInPicture = false;
            video.removeAttribute('disablepictureinpicture');
            if (!wired.has(video)) {
                wired.add(video);
                video.addEventListener('webkitpresentationmodechanged', () => setTimeout(() => report(video), 0));
            }
            try {
                video.webkitSetPresentationMode('picture-in-picture');
            } catch (_) {
                report(video);
                return false;
            }
            return true;
        }
        if (data.command === 'stop') {
            if (latestRequest === data.request) latestRequest = null;
            if (!current || current.request !== data.request) return false;
            const video = current.video;
            current.stopping = true;
            try { video.webkitSetPresentationMode('inline'); } catch (_) {}
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

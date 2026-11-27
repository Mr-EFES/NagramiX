import Foundation
import Display
import TelegramCore
import AccountContext
import WebKit
import SwiftSignalKit
import UniversalMediaPlayer
import AppBundle

private func accumulateTimecode(_ base: Int, _ value: Int, times multiplier: Int) -> Int {
    let (product, productOverflow) = value.multipliedReportingOverflow(by: multiplier)
    if productOverflow {
        return Int.max
    }
    let (sum, sumOverflow) = base.addingReportingOverflow(product)
    if sumOverflow {
        return Int.max
    }
    return sum
}

func extractYoutubeVideoIdAndTimestamp(url: String) -> (String, Int)? {
    guard let url = URL(string: url), let host = url.host?.lowercased() else {
        return nil
    }
    
    let shortLink = host == "youtu.be" || host.hasSuffix(".youtu.be")
    let match = shortLink || ["youtube.com", "youtube-nocookie.com"].contains {
        host == $0 || host.hasSuffix("." + $0)
    }
    
    guard match else {
        return nil
    }
    
    var videoId: String?
    var timestamp = 0
    
    if let components = URLComponents(url: url, resolvingAgainstBaseURL: false) {
        if let queryItems = components.queryItems {
            for queryItem in queryItems {
                if let value = queryItem.value {
                    if queryItem.name == "v" && !value.isEmpty {
                        videoId = value
                    } else if queryItem.name == "t" || queryItem.name == "time_continue" {
                        if value.contains("s") {
                            var range = value.startIndex..<value.endIndex
                            if let hoursRange = value.range(of: "h", options: .caseInsensitive, range: range, locale: nil) {
                                let subvalue = String(value[range.lowerBound ..< hoursRange.lowerBound])
                                if let hours = Int(subvalue) {
                                    timestamp = accumulateTimecode(timestamp, hours, times: 3600)
                                }
                                range = hoursRange.upperBound..<value.endIndex
                            }
                            
                            if let minutesRange = value.range(of: "m", options: .caseInsensitive, range: range, locale: nil) {
                                let subvalue = String(value[range.lowerBound ..< minutesRange.lowerBound])
                                if let minutes = Int(subvalue) {
                                    timestamp = accumulateTimecode(timestamp, minutes, times: 60)
                                }
                                range = minutesRange.upperBound..<value.endIndex
                            }
                            
                            if let secondsRange = value.range(of: "s", options: .caseInsensitive, range: range, locale: nil) {
                                let subvalue = String(value[range.lowerBound ..< secondsRange.lowerBound])
                                if let seconds = Int(subvalue) {
                                    timestamp = accumulateTimecode(timestamp, seconds, times: 1)
                                }
                            }
                        } else {
                            if let seconds = Int(value) {
                                timestamp = seconds
                            }
                        }
                    }
                }
            }
        }
        
        if videoId == nil {
            let path = components.path.split(separator: "/")
            if shortLink, let first = path.first {
                videoId = String(first)
            } else if path.count >= 2, ["embed", "shorts", "live", "v"].contains(String(path[0])), path[1] != "videoseries" {
                videoId = String(path[1])
            }
        }
    }
    
    if let videoId = videoId {
        return (videoId, timestamp)
    }
    
    return nil
}

public enum NagramiXYoutubeAvailability: Equatable {
    case loading
    case playable
    case watchLoading
    case watchInteractive
    case watchInlineOnly
    case watchPlayable
    case unavailable

    public var canPlayInPiP: Bool { self == .playable || self == .watchPlayable }
    public var hasPlayableVideo: Bool { self.canPlayInPiP || self == .watchInlineOnly }
    public var showsWatchControls: Bool {
        self == .watchLoading || self == .watchInteractive || self == .watchInlineOnly || self == .watchPlayable || self == .unavailable
    }
}

final class YoutubeEmbedImplementation: WebEmbedImplementation {
    private var evalImpl: ((String, ((Any?) -> Void)?) -> Void)?
    private var updateStatus: ((MediaPlayerStatus) -> Void)?
    private var onPlaybackStarted: (() -> Void)?
    
    fileprivate let videoId: String
    fileprivate var storyboardSpec: String?
    fileprivate var duration: Double {
        return self.status.duration
    }
    
    private var timestamp: Int
    private var baseRate: Double = 1.0
    private var ignoreEarlierTimestamps = false
    private var status: MediaPlayerStatus
    
    private(set) var availability: NagramiXYoutubeAvailability = .loading {
        didSet {
            if self.availability != oldValue { self.availabilityChanged?(self.availability) }
        }
    }
    var availabilityChanged: ((NagramiXYoutubeAvailability) -> Void)?
    var pageVisible: (() -> Void)?
    private var loadDocument: ((String) -> Void)?
    private var documentId = UUID().uuidString
    private var transportRevision = 0
    private var pendingTransport: Bool?
    private var startupDeadline: DispatchWorkItem?
    var wantsPlayingPictureInPicture: Bool { self.isPlaying }

    private func sendCommand(_ command: String) {
        self.evalImpl?("if (window.nagramiXYoutubeDocument === '\(self.documentId)') { \(command) }", nil)
    }

    private func cancelStartupDeadline() {
        self.deadlineRevision &+= 1
        self.startupDeadline?.cancel()
        self.startupDeadline = nil
    }

    private(set) var usesWatchPage = false
    private var ready = false
    private var started = false
    private var embedFailed = false
    private var firstPosition: Double?
    private var hasAdvanced = false
    private var deadlineRevision = 0
    private var watchReady = false
    private var watchRevision = 0
    private var watchPlayRevision: Int?
    private var watchResumePoint: (position: Double, duration: Double)?
    private var stallPosition: Double?
    private var stallRetried = false
    private var stallDeadline: DispatchWorkItem?
    private var stallRevision = 0
    var openWatchPage: ((String, Double) -> Void)?
    var sendWatchCommand: ((String, Double?, Int) -> Void)?

    private func observeProgress(_ position: Double) {
        guard position.isFinite, !self.hasAdvanced else { return }
        if let first = self.firstPosition, position > first + 0.05 {
            self.hasAdvanced = true
            self.cancelStartupDeadline()
        } else {
            self.firstPosition = min(self.firstPosition ?? position, position)
        }
    }

    private func watchForFirstFrame() {
        guard self.isPlaying, !self.hasAdvanced, self.startupDeadline == nil else { return }
        self.deadlineRevision &+= 1
        let revision = self.deadlineRevision
        let deadline = DispatchWorkItem { [weak self] in
            guard let self, self.deadlineRevision == revision, self.isPlaying, !self.hasAdvanced else { return }
            self.startupDeadline = nil
            self.startupFailed()
        }
        self.startupDeadline = deadline
        DispatchQueue.main.asyncAfter(deadline: .now() + (self.usesWatchPage ? 15.0 : 8.0), execute: deadline)
    }

    func startupFailed() {
        self.cancelStartupDeadline()
        self.clearWatchStall()
        if self.usesWatchPage {
            self.isPlaying = false
            self.firstPosition = nil
            self.hasAdvanced = false
            self.started = false
            self.availability = .unavailable
            self.publishPlayback(.paused, soundEnabled: false)
            self.issueWatchCommand("pause")
            self.pageVisible?()
            return
        }
        self.embedFailed = true
        guard self.isPlaying else { return }
        self.usesWatchPage = true
        self.documentId = UUID().uuidString
        self.pendingTransport = nil
        self.started = false
        self.firstPosition = nil
        self.hasAdvanced = false
        self.availability = .watchLoading
        self.publishPlayback(.buffering(initial: true, whilePlaying: true, progress: 0, display: true))
        self.watchForFirstFrame()
        self.openWatchPage?(self.videoId, self.pendingSeek ?? self.status.timestamp)
    }

    func webProcessEnded() {
        self.documentId = UUID().uuidString
        self.ready = false
        self.watchReady = false
        self.startupFailed()
    }

    private func issueWatchCommand(_ command: String, value: Double? = nil) {
        guard self.watchReady else { return }
        self.watchRevision &+= 1
        switch command {
        case "play", "recover": self.watchPlayRevision = self.watchRevision
        case "pause": self.watchPlayRevision = nil
        default: break
        }
        self.sendWatchCommand?(command, value, self.watchRevision)
    }

    private func rememberWatchPosition() {
        guard self.watchReady, self.watchResumePoint == nil, self.status.timestamp > 0,
              self.status.timestamp < self.status.duration else { return }
        self.watchResumePoint = (self.status.timestamp, self.status.duration)
    }

    @discardableResult
    private func restoreWatchPosition(_ position: Double, duration: Double) -> Bool {
        guard let saved = self.watchResumePoint, duration > 0 else { return false }
        self.watchResumePoint = nil
        // Check the duration before transferring a position; a watch URL can contain multiple timelines.
        guard abs(duration - saved.duration) < 1, saved.position < duration, abs(position - saved.position) > 0.25 else { return false }
        self.issueWatchCommand("seek", value: saved.position)
        return true
    }

    private func clearWatchStall() {
        self.stallRevision &+= 1
        self.stallDeadline?.cancel()
        self.stallDeadline = nil
        self.stallPosition = nil
        self.stallRetried = false
    }

    private func armWatchStallDeadline() {
        self.stallRevision &+= 1
        self.stallDeadline?.cancel()
        let revision = self.stallRevision
        let deadline = DispatchWorkItem { [weak self] in
            guard let self, revision == self.stallRevision, self.watchReady, self.isPlaying else { return }
            if self.stallRetried {
                // Keep the official controls available for a later, explicit Play.
                self.clearWatchStall()
                self.hasAdvanced = false
                self.firstPosition = nil
                self.availability = .watchInteractive
                self.isPlaying = false
                self.issueWatchCommand("pause")
                self.publishPlayback(.paused, soundEnabled: false)
            } else {
                self.retryWatchStall()
            }
        }
        self.stallDeadline = deadline
        DispatchQueue.main.asyncAfter(deadline: .now() + (self.stallRetried ? 15.0 : 8.0), execute: deadline)
    }

    private func retryWatchStall() {
        guard self.isPlaying, self.stallPosition != nil, !self.stallRetried else { return }
        self.stallRetried = true
        self.armWatchStallDeadline()
        self.issueWatchCommand("recover")
    }

    func watchEvent(_ event: String, position: Double, duration: Double, revision: Int, canUsePiP: Bool) {
        guard self.usesWatchPage, position.isFinite, duration.isFinite else { return }
        // The official page can display an error instead of creating a media element.
        if event == "pageError" {
            if self.availability != .unavailable { self.startupFailed() }
            return
        }
        guard self.availability != .unavailable else { return }
        if event == "detached" {
            self.rememberWatchPosition()
            self.clearWatchStall()
            self.watchReady = false
            self.firstPosition = nil
            self.hasAdvanced = false
            self.availability = .watchLoading
            if self.isPlaying {
                self.publishPlayback(.buffering(initial: !self.started, whilePlaying: true, progress: 0, display: true))
                self.watchForFirstFrame()
            }
            return
        }
        if event == "ready" {
            self.rememberWatchPosition()
            self.clearWatchStall()
            self.watchReady = true
            self.pageVisible?()
            self.hasAdvanced = false
            self.firstPosition = nil
            self.availability = .watchInteractive
            self.watchForFirstFrame()
            if let seek = self.pendingSeek {
                self.pendingSeek = nil
                self.watchResumePoint = nil
                self.issueWatchCommand("seek", value: seek)
            } else {
                self.restoreWatchPosition(position, duration: duration)
            }
            if self.baseRate != 1 { self.issueWatchCommand("rate", value: self.baseRate) }
            self.issueWatchCommand(self.isPlaying ? "play" : "pause")
            return
        }
        guard self.watchReady else { return }
        if event == "gesture" || event == "playFailed" {
            guard self.isPlaying, revision == self.watchPlayRevision else { return }
        } else if revision != self.watchRevision {
            return
        }
        if self.hasAdvanced {
            self.availability = canUsePiP ? .watchPlayable : .watchInlineOnly
        }
        let playback: MediaPlayerPlaybackStatus
        switch event {
        case "metadata":
            self.restoreWatchPosition(position, duration: duration)
            return
        case "online":
            self.retryWatchStall()
            return
        case "seeked":
            self.firstPosition = nil
            if self.stallPosition != nil { self.stallPosition = position }
            self.updateWatchPosition(max(0, position), duration: max(0, duration), newSeek: self.status.timestamp != position)
            return
        case "failed", "playFailed":
            self.startupFailed()
            return
        case "attempt":
            self.watchPlayRevision = nil
            self.isPlaying = true
            self.watchForFirstFrame()
            return
        case "gesture":
            self.cancelStartupDeadline()
            self.clearWatchStall()
            self.isPlaying = false
            self.availability = .watchInteractive
            self.publishPlayback(.paused, soundEnabled: false)
            return
        case "playing":
            self.isPlaying = true
            if self.restoreWatchPosition(position, duration: duration) { return }
            if let anchor = self.stallPosition {
                guard position > anchor + 0.05 else { return }
                self.clearWatchStall()
            }
            self.observeProgress(position)
            self.watchForFirstFrame()
            if self.hasAdvanced {
                self.availability = canUsePiP ? .watchPlayable : .watchInlineOnly
                if !self.started { self.started = true; self.onPlaybackStarted?() }
                playback = .playing
            } else {
                playback = .buffering(initial: true, whilePlaying: true, progress: 0, display: true)
            }
        case "waiting":
            guard self.isPlaying else { return }
            if self.hasAdvanced && self.stallPosition == nil {
                self.stallPosition = position
                self.armWatchStallDeadline()
            }
            playback = .buffering(initial: !self.started, whilePlaying: true, progress: 0, display: true)
        case "paused", "ended":
            self.watchPlayRevision = nil
            self.clearWatchStall()
            self.cancelStartupDeadline()
            self.isPlaying = false
            if event == "ended" {
                self.watchResumePoint = nil
                self.started = false
                self.firstPosition = nil
                self.hasAdvanced = false
                self.availability = .watchInteractive
            }
            playback = .paused
        default: return
        }
        self.status = MediaPlayerStatus(generationTimestamp: ProcessInfo.processInfo.systemUptime, duration: max(0, duration),
            dimensions: self.status.dimensions, timestamp: max(0, position), baseRate: self.baseRate,
            seekId: self.status.seekId, status: playback, soundEnabled: event != "paused" || self.hasAdvanced)
        self.updateStatus?(self.status)
    }

    private var lastProviderErrorCode: Int?
    private var ignorePosition: Int?
    
    private var isPlaying = false
    private var pendingSeek: Double?

    private let benchmarkStartTime: CFAbsoluteTime
    
    init(videoId: String, timestamp: Int = 0) {
        self.videoId = videoId
        self.timestamp = timestamp
        if self.timestamp > 0 {
            self.ignoreEarlierTimestamps = true
        }
        self.status = MediaPlayerStatus(generationTimestamp: 0.0, duration: 0.0, dimensions: CGSize(), timestamp: Double(timestamp), baseRate: 1.0, seekId: 0, status: .paused, soundEnabled: true)
        
        self.benchmarkStartTime = CFAbsoluteTimeGetCurrent()
    }
    
    func setup(_ webView: WKWebView, userContentController: WKUserContentController, evaluateJavaScript: @escaping (String, ((Any?) -> Void)?) -> Void, updateStatus: @escaping (MediaPlayerStatus) -> Void, onPlaybackStarted: @escaping () -> Void) {
        let bundle = getAppBundle()
        guard let userScriptPath = bundle.path(forResource: "YoutubeUserScript", ofType: "js") else {
            return
        }
        guard let userScriptData = try? Data(contentsOf: URL(fileURLWithPath: userScriptPath)) else {
            return
        }
        guard let userScript = String(data: userScriptData, encoding: .utf8) else {
            return
        }
        guard let htmlTemplatePath = bundle.path(forResource: "Youtube", ofType: "html") else {
            return
        }
        guard let htmlTemplateData = try? Data(contentsOf: URL(fileURLWithPath: htmlTemplatePath)) else {
            return
        }
        guard let htmlTemplate = String(data: htmlTemplateData, encoding: .utf8) else {
            return
        }
        
        // YouTube uses the iOS bundle identity and origin to identify its embedding client.
        let origin = Bundle.main.bundleIdentifier.flatMap { URL(string: "https://\($0.lowercased())") }
        var playerVars: [String: Any] = [
            "cc_load_policy": 1, "iv_load_policy": 3, "controls": 0, "playsinline": 1,
            "autohide": 1, "showinfo": 0, "rel": 0, "modestbranding": 1, "start": self.timestamp
        ]
        if let origin { playerVars["origin"] = origin.absoluteString }

        let params: [String : Any] = [ "videoId": self.videoId,
                                       "width": "100%",
                                       "height": "100%",
                                       "playerVars": playerVars ]

        guard let paramsJsonData = try? JSONSerialization.data(withJSONObject: params, options: .prettyPrinted), let paramsJson = String(data: paramsJsonData, encoding: .utf8) else {
            return
        }
        
        self.evalImpl = evaluateJavaScript
        self.updateStatus = updateStatus
        self.onPlaybackStarted = onPlaybackStarted
        updateStatus(self.status)
        
        userContentController.addUserScript(WKUserScript(source: userScript, injectionTime: .atDocumentEnd, forMainFrameOnly: false))
        let html = String(format: htmlTemplate, paramsJson)
        self.loadDocument = { [weak webView] document in
            webView?.loadHTMLString(html.replacingOccurrences(of: "__NAGRAMIX_DOCUMENT__", with: document), baseURL: origin)
        }
        self.loadDocument?(self.documentId)
    }
    
    func play() {
        self.isPlaying = true
        if self.usesWatchPage {
            if self.availability == .unavailable { self.isPlaying = false; return }
            self.watchForFirstFrame()
            self.issueWatchCommand("play")
            return
        }
        if self.embedFailed { self.startupFailed(); return }
        self.watchForFirstFrame()
        if !self.started {
            self.publishPlayback(.buffering(initial: true, whilePlaying: true, progress: 0.0, display: true))
        }
        guard self.ready else { return }
        if let timestamp = self.pendingSeek {
            self.pendingSeek = nil
            self.sendCommand("seek(\(timestamp));")
        }

        self.transportRevision += 1
        self.pendingTransport = true
        self.sendCommand("play(\(self.transportRevision));")
        
        self.ignorePosition = 2
    }
    
    func pause() {
        self.isPlaying = false
        self.clearWatchStall()
        self.cancelStartupDeadline()
        if self.usesWatchPage {
            self.issueWatchCommand("pause")
            self.publishPlayback(.paused, soundEnabled: self.availability != .unavailable)
            return
        }
        if !self.ready { self.publishPlayback(.paused) }
        if self.ready {
            self.transportRevision += 1
            self.pendingTransport = false
            self.sendCommand("pause(\(self.transportRevision));")
        }
    }
    
    func togglePlayPause() {
        if case .playing = self.status.status {
            self.pause()
        } else {
            self.play()
        }
    }
    
    func seek(timestamp: Double) {
        guard timestamp.isFinite, timestamp >= 0, timestamp < Double(Int.max) else { return }
        self.firstPosition = nil
        if self.usesWatchPage {
            self.watchResumePoint = nil
            if self.stallPosition != nil {
                self.clearWatchStall()
                if self.isPlaying {
                    self.stallPosition = timestamp
                    self.armWatchStallDeadline()
                }
            }
            if self.watchReady { self.issueWatchCommand("seek", value: timestamp) } else { self.pendingSeek = timestamp }
            self.updateWatchPosition(timestamp, duration: self.status.duration, newSeek: true)
            return
        }
        if !self.ready {
            self.pendingSeek = timestamp
            self.timestamp = Int(timestamp)
            self.ignoreEarlierTimestamps = true
        } else {
            self.sendCommand("seek(\(timestamp));")
        }
        
        self.status = MediaPlayerStatus(generationTimestamp: self.status.generationTimestamp, duration: self.status.duration, dimensions: self.status.dimensions, timestamp: timestamp, baseRate: self.status.baseRate, seekId: self.status.seekId + 1, status: self.status.status, soundEnabled: true)
        self.updateStatus?(self.status)
        
        self.ignorePosition = 2
    }
    
    private func updateWatchPosition(_ position: Double, duration: Double, newSeek: Bool) {
        self.status = MediaPlayerStatus(generationTimestamp: ProcessInfo.processInfo.systemUptime, duration: duration,
            dimensions: self.status.dimensions, timestamp: position, baseRate: self.status.baseRate,
            seekId: self.status.seekId + (newSeek ? 1 : 0), status: self.status.status, soundEnabled: self.status.soundEnabled)
        self.updateStatus?(self.status)
    }

    func setBaseRate(_ baseRate: Double) {
        var baseRate = baseRate
        if baseRate < 0.5 {
            baseRate = 0.5
        }
        if baseRate > 2.0 {
            baseRate = 2.0
        }
        self.baseRate = baseRate
        if self.usesWatchPage { self.issueWatchCommand("rate", value: baseRate); return }
        if self.ready {
            self.sendCommand("setRate(\(baseRate));")
        }
        
        self.status = MediaPlayerStatus(generationTimestamp: self.status.generationTimestamp, duration: self.status.duration, dimensions: self.status.dimensions, timestamp: self.status.timestamp, baseRate: baseRate, seekId: self.status.seekId + 1, status: self.status.status, soundEnabled: true)
        self.updateStatus?(self.status)
    }
    
    private func publishPlayback(_ playback: MediaPlayerPlaybackStatus, soundEnabled: Bool = true) {
        self.status = MediaPlayerStatus(generationTimestamp: self.status.generationTimestamp,
            duration: self.status.duration, dimensions: self.status.dimensions, timestamp: self.status.timestamp,
            baseRate: self.status.baseRate, seekId: self.status.seekId, status: playback, soundEnabled: soundEnabled)
        self.updateStatus?(self.status)
    }

    private func iframeReady() {
        guard !self.ready else { return }
        self.ready = true
        if self.baseRate != 1.0 { self.sendCommand("setRate(\(self.baseRate));") }
        // The real iframe can now accept a tap, including when automatic playback is blocked.
        self.pageVisible?()
        if self.isPlaying { self.play() }
    }

    func pageReady() {
    }
    
    func callback(url: URL) {
        guard !self.usesWatchPage, let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              components.queryItems?.first(where: { $0.name == "document" })?.value == self.documentId else { return }
        switch url.host {
            case "onState":
                let acknowledgedRevision = components.queryItems?.first(where: { $0.name == "transport" })?.value.flatMap(Int.init)
                guard acknowledgedRevision == self.transportRevision else { return }
                var newTimestamp = self.status.timestamp
                
                var playback: Int?
                var position: Double?
                var duration: Double?
                var download: Float?
                var iframeReady = false
                var autoplayBlocked = false
                var failed: Bool?
                var providerErrorCode: Int?

                if let queryItems = components.queryItems {
                    for queryItem in queryItems {
                        if let value = queryItem.value {
                            if queryItem.name == "playback" {
                                playback = Int(value)
                            } else if queryItem.name == "position" {
                                position = Double(value)
                            } else if queryItem.name == "duration" {
                                if let seconds = Double(value), seconds.isFinite, seconds >= 0 {
                                    duration = seconds
                                }
                            } else if queryItem.name == "download" {
                                download = Float(value)
                            } else if queryItem.name == "ready" {
                                iframeReady = value == "true"
                            } else if queryItem.name == "blocked" {
                                autoplayBlocked = value == "true"
                            } else if queryItem.name == "failed" {
                                failed = Bool(value)
                            } else if queryItem.name == "errorCode" {
                                providerErrorCode = Int(value)
                            } else if queryItem.name == "storyboard" {
                                let urlString = url.absoluteString
                                if value.count > 10, let range = urlString.range(of: "storyboard=") {
                                    self.storyboardSpec = String(urlString[range.upperBound..<urlString.endIndex]).removingPercentEncoding
                                }
                            }
                        }
                    }
                }

                let _ = download

                if let position = position {
                    if self.ignoreEarlierTimestamps {
                        if position >= Double(self.timestamp) {
                            self.ignoreEarlierTimestamps = false
                            newTimestamp = Double(position)
                        }
                    } else if let ticksToIgnore = self.ignorePosition {
                        if ticksToIgnore > 1 {
                            self.ignorePosition = ticksToIgnore - 1
                        } else {
                            self.ignorePosition = nil
                        }
                    } else {
                        newTimestamp = Double(position)
                    }
                }

                if failed == true || autoplayBlocked {
                    self.pendingTransport = nil
                    if let code = providerErrorCode, self.lastProviderErrorCode != code {
                        self.lastProviderErrorCode = code
                        Logger.shared.log("YouTubeEmbed", "IFrame player error \(code)")
                    }
                    self.startupFailed()
                    return
                }
                if iframeReady { self.iframeReady() }
                guard acknowledgedRevision == self.transportRevision else { return }
                if let updateStatus = self.updateStatus, let playback = playback, let duration = duration {
                    // The iframe can still report the previous run's ENDED state
                    // after accepting Play, before this run has started.
                    if playback == 0 && !self.started && self.pendingTransport == true { return }
                    if let wanted = self.pendingTransport {
                        if wanted && playback != 1 && playback != 0 {
                            self.publishPlayback(.buffering(initial: !self.started, whilePlaying: true, progress: 0.0, display: false))
                            return
                        }
                        if !wanted && (playback == 1 || playback == 3) {
                            self.publishPlayback(.paused)
                            return
                        }
                        self.pendingTransport = nil
                    }
                    // Polling continues after a startup timeout. Keep Retry available
                    // and its seek position intact until playback actually recovers.
                    if self.availability == .unavailable && playback != 1 { return }
                    let playbackStatus: MediaPlayerPlaybackStatus
                    switch playback {
                    case 0:
                        self.hasAdvanced = false
                        self.firstPosition = nil
                        self.cancelStartupDeadline()
                        self.started = false
                        self.availability = .loading
                        self.isPlaying = false
                        playbackStatus = .paused
                        newTimestamp = 0.0
                    case 1:
                        if let position { self.observeProgress(position) }
                        if self.hasAdvanced { self.availability = .playable }
                        self.lastProviderErrorCode = nil
                        self.isPlaying = true
                        self.watchForFirstFrame()
                        playbackStatus = self.hasAdvanced ? .playing : .buffering(initial: true, whilePlaying: true, progress: 0, display: true)
                    case 2:
                        if self.started { self.isPlaying = false; self.cancelStartupDeadline() }
                        playbackStatus = .paused
                    case 3:
                        playbackStatus = .buffering(initial: !self.started, whilePlaying: self.isPlaying, progress: 0.0, display: false)
                    default:
                        playbackStatus = self.isPlaying ? .buffering(initial: true, whilePlaying: true, progress: 0.0, display: false) : .paused
                    }

                    if case .playing = playbackStatus, !self.started {
                        self.started = true
                        print("YT started in \(CFAbsoluteTimeGetCurrent() - self.benchmarkStartTime)")

                        self.onPlaybackStarted?()
                    }

                    self.status = MediaPlayerStatus(generationTimestamp: self.status.generationTimestamp, duration: duration, dimensions: self.status.dimensions, timestamp: newTimestamp, baseRate: self.status.baseRate, seekId: self.status.seekId, status: playbackStatus, soundEnabled: true)
                    updateStatus(self.status)
                }
                
            case "onReady":
                self.iframeReady()
            default:
                break
        }
    }
}

public struct YoutubeEmbedStoryboardMediaResourceId {
    public let videoId: String
    public let storyboardId: Int32

    public var uniqueId: String {
        return "youtube-storyboard-\(self.videoId)-\(self.storyboardId)"
    }
    
    public var hashValue: Int {
        return self.uniqueId.hashValue
    }
}

public class YoutubeEmbedStoryboardMediaResource: TelegramMediaResource {
    public let videoId: String
    public let storyboardId: Int32
    public let url: String
    
    public var size: Int64? {
        return nil
    }
    
    public init(videoId: String, storyboardId: Int32, url: String) {
        self.videoId = videoId
        self.storyboardId = storyboardId
        self.url = url
    }
    
    public required init(decoder: EnginePostboxDecoder) {
        self.videoId = decoder.decodeStringForKey("v", orElse: "")
        self.storyboardId = decoder.decodeInt32ForKey("i", orElse: 0)
        self.url = decoder.decodeStringForKey("u", orElse: "")
    }

    public func encode(_ encoder: EnginePostboxEncoder) {
        encoder.encodeString(self.videoId, forKey: "v")
        encoder.encodeInt32(self.storyboardId, forKey: "i")
        encoder.encodeString(self.url, forKey: "u")
    }

    public var id: EngineRawMediaResourceId {
        return EngineRawMediaResourceId(YoutubeEmbedStoryboardMediaResourceId(videoId: self.videoId, storyboardId: self.storyboardId).uniqueId)
    }

    public func isEqual(to: EngineRawMediaResource) -> Bool {
        if let to = to as? YoutubeEmbedStoryboardMediaResource {
            return self.videoId == to.videoId && self.storyboardId == to.storyboardId && self.url == to.url
        } else {
            return false
        }
    }
}

public final class YoutubeEmbedStoryboardMediaResourceRepresentation: EngineMediaResourceRepresentation {
    public let keepDuration: EngineCachedMediaRepresentationKeepDuration = .shortLived

    public var uniqueId: String {
        return "cached"
    }

    public init() {
    }

    public func isEqual(to: EngineRawCachedMediaResourceRepresentation) -> Bool {
        if to is YoutubeEmbedStoryboardMediaResourceRepresentation {
            return true
        } else {
            return false
        }
    }
}

public func fetchYoutubeEmbedStoryboardResource(resource: YoutubeEmbedStoryboardMediaResource) -> Signal<EngineCachedMediaResourceRepresentationResult, NoError> {
    return Signal { subscriber in
        subscriber.putNext(.reset)
                
        let disposable = MetaDisposable()
        disposable.set(fetchHttpResource(url: resource.url).start(next: { next in
            if case let .dataPart(_, data, _, complete) = next, complete {
                let tempFile = EngineTempBox.shared.tempFile(fileName: "image.jpg")
                if let _ = try? data.write(to: URL(fileURLWithPath: tempFile.path), options: .atomic) {
                    subscriber.putNext(.tempFile(tempFile))
                    subscriber.putCompletion()
                }
            }
        }))
        
        return ActionDisposable {
            disposable.dispose()
        }
    }
}

private func youtubeEmbedStoryboardData(account: Account, resource: YoutubeEmbedStoryboardMediaResource) -> Signal<Data?, NoError> {
    return Signal<Data?, NoError> { subscriber in
        let dataDisposable = TelegramEngine(account: account).resources.cachedRepresentation(resource: EngineMediaResource(resource), representation: YoutubeEmbedStoryboardMediaResourceRepresentation(), complete: true).start(next: { next in
            if next.availableSize != 0 {
                subscriber.putNext(next.availableSize == 0 ? nil : try? Data(contentsOf: URL(fileURLWithPath: next.path), options: []))
            }
        }, error: subscriber.putError, completed: subscriber.putCompletion)
        
        return ActionDisposable {
            dataDisposable.dispose()
        }
    }
}

private func youtubeEmbedStoryboardImage(account: Account, resource: YoutubeEmbedStoryboardMediaResource, frame: Int32, size: YoutubeEmbedFramePreview.StoryboardSpec.StoryboardSize) -> Signal<UIImage?, NoError> {
    let signal = youtubeEmbedStoryboardData(account: account, resource: resource)
    
    return signal |> map { fullSizeData in
        let drawingSize = CGSize(width: CGFloat(size.width), height: CGFloat(size.height))
        guard let context = DrawingContext(size: drawingSize, clear: true) else {
            return nil
        }
        
        var fullSizeImage: CGImage?
        if let fullSizeData = fullSizeData {
            let options = NSMutableDictionary()
            options[kCGImageSourceShouldCache as NSString] = false as NSNumber
            if let imageSource = CGImageSourceCreateWithData(fullSizeData as CFData, nil), let image = CGImageSourceCreateImageAtIndex(imageSource, 0, options as CFDictionary) {
                fullSizeImage = image
            }
            
            if let fullSizeImage = fullSizeImage {
                let rect: CGRect
                let imageSize = CGSize(width: CGFloat(fullSizeImage.width), height: CGFloat(fullSizeImage.height))
                
                let row = floor(CGFloat(frame) / CGFloat(size.cols))
                let col = CGFloat(frame % size.cols)
                
                rect = CGRect(origin: CGPoint(x: -drawingSize.width * col, y: -drawingSize.height * row), size: imageSize)
                
                context.withFlippedContext { c in
                    c.setBlendMode(.copy)
                    c.interpolationQuality = .medium
                    c.draw(fullSizeImage, in: rect)
                }
                return context.generateImage()
            }
        }
        return nil
    }
}

public final class YoutubeEmbedFramePreview: FramePreview {
    fileprivate struct StoryboardSpec {
        struct StoryboardSize {
            let width: Int32
            let height: Int32
            let quality: Int32
            let cols: Int32
            let rows: Int32
            let duration: Int32
            let imageName: String
            let sigh: String
        }
        
        let baseUrl: String
        let sizes: [StoryboardSize]
        
        init?(specString: String) {
            let sections = specString.components(separatedBy: "|")
            if sections.count < 2 {
                return nil
            }
            guard let baseUrl = sections.first else {
                return nil
            }
            self.baseUrl = baseUrl
            
            var sizes: [StoryboardSize] = []
            for i in 1 ..< sections.count - 1 {
                let section = sections[i]
                let data = section.components(separatedBy: "#")
                
                if data.count >= 8, let width = Int32(data[0]), let height = Int32(data[1]), let quality = Int32(data[2]), let cols = Int32(data[3]), let rows = Int32(data[4]), let duration = Int32(data[5]) {
                    let size = StoryboardSize(width: width, height: height, quality: quality, cols: cols, rows: rows, duration: duration, imageName: data[6], sigh: data[7])
                    sizes.append(size)
                }
            }
            
            self.sizes = sizes
        }
        
        var bestSize: (Int, StoryboardSize)? {
            var best: (Int, StoryboardSize)?
            for i in 0 ..< self.sizes.count {
                let size = self.sizes[i]
                if let (_, currentBest) = best {
                    if currentBest.width < size.width || (currentBest.width == size.width && currentBest.cols < size.cols) {
                        best = (i, size)
                    }
                } else {
                    best = (i, size)
                }
            }
            return best
        }
    }
    
    private func storyboardUrl(spec: StoryboardSpec, sizeIndex: Int, num: Int32) -> String {
        let size = spec.sizes[sizeIndex]
        
        var url = spec.baseUrl
        url = url.replacingOccurrences(of: "$L", with: "\(sizeIndex)")
        url = url.replacingOccurrences(of: "$N", with: size.imageName)
        url = url.replacingOccurrences(of: "$M", with: "\(num)")
        url += "&sigh=\(size.sigh)"
        
        return url
    }
    
    private let context: AccountContext
    private weak var content: WebEmbedVideoContent?
    
    private let currentFrameDisposable = MetaDisposable()
    private var currentFrameTimestamp: Double?
    private var nextFrameTimestamp: Double?
    fileprivate let framePipe = ValuePipe<FramePreviewResult>()
    
    public init(context: AccountContext, content: WebEmbedVideoContent) {
        self.context = context
        self.content = content
    }
    
    deinit {
        self.currentFrameDisposable.dispose()
    }
    
    public var generatedFrames: Signal<FramePreviewResult, NoError> {
        return self.framePipe.signal()
    }
    
    public func generateFrame(at timestamp: Double) {
        guard let content = self.content else {
            return
        }
        
        if self.currentFrameTimestamp != nil {
            self.nextFrameTimestamp = timestamp
            return
        }
        self.currentFrameTimestamp = timestamp
        
        self.context.sharedContext.mediaManager.universalVideoManager.withUniversalVideoContent(id: content.id) { [weak self] node in
            guard let strongSelf = self, let node = node as? WebEmbedVideoContentNode, let youtubeImpl = node.impl as? YoutubeEmbedImplementation, youtubeImpl.duration > 0.0, let specString = youtubeImpl.storyboardSpec, let storyboardSpec = StoryboardSpec(specString: specString), let bestSize = storyboardSpec.bestSize else {
                return
            }
            
            var duration: Double = Double(bestSize.1.duration) / 1000.0
            var totalFrames: Int32 = 1
            let framesOnStoryboard: Int32 = bestSize.1.cols * bestSize.1.rows
            
            if duration > 0.0 {
                totalFrames = Int32(ceil(youtubeImpl.duration / duration))
            } else {
                duration = youtubeImpl.duration / Double(framesOnStoryboard)
            }
            
            let globalFrame = Int32(floor(timestamp / youtubeImpl.duration * Double(totalFrames)))
            let frame: Int32 = globalFrame % framesOnStoryboard

            let num: Int32 = Int32(floor(Double(globalFrame) / Double(framesOnStoryboard)))
            let url = strongSelf.storyboardUrl(spec: storyboardSpec, sizeIndex: bestSize.0, num: num)
            
            strongSelf.framePipe.putNext(.waitingForData)
            strongSelf.currentFrameDisposable.set(youtubeEmbedStoryboardImage(account: strongSelf.context.account, resource: YoutubeEmbedStoryboardMediaResource(videoId: youtubeImpl.videoId, storyboardId: num, url: url), frame: frame, size: bestSize.1).start(next: { image in
                if let strongSelf = self {
                    if let image = image {
                        strongSelf.framePipe.putNext(.image(image))
                    }
                    strongSelf.currentFrameTimestamp = nil
                    if let nextFrameTimestamp = strongSelf.nextFrameTimestamp {
                        strongSelf.nextFrameTimestamp = nil
                        strongSelf.generateFrame(at: nextFrameTimestamp)
                    }
                }
            }))
        }
    }
    
    public func cancelPendingFrames() {
        self.nextFrameTimestamp = nil
        self.currentFrameTimestamp = nil
        self.currentFrameDisposable.set(nil)
    }
}

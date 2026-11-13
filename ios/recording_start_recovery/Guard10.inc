import Foundation
import UIKit
import AsyncDisplayKit
import Display
import SwiftSignalKit
import Postbox
import TelegramCore
import TelegramAudio
import UniversalMediaPlayer
import LegacyComponents
import AccountContext
import PhotoResources
import RangeSet
import NagramiXCore

public final class WebEmbedVideoContent: UniversalVideoContent {
    public let id: AnyHashable
    let userLocation: MediaResourceUserLocation
    let webPage: TelegramMediaWebpage
    public let webpageContent: TelegramMediaWebpageLoadedContent
    public let dimensions: CGSize
    public let duration: Double
    let forcedTimestamp: Int?
    let openUrl: (URL) -> Void
    
    public init?(userLocation: MediaResourceUserLocation, webPage: TelegramMediaWebpage, webpageContent: TelegramMediaWebpageLoadedContent, forcedTimestamp: Int? = nil, openUrl: @escaping (URL) -> Void) {
        guard let embedUrl = webpageContent.embedUrl else {
            return nil
        }
        self.id = AnyHashable(embedUrl)
        self.userLocation = userLocation
        self.webPage = webPage
        self.webpageContent = webpageContent
        self.dimensions = webpageContent.embedSize?.cgSize ?? CGSize(width: 128.0, height: 128.0)
        self.duration = webpageContent.duration.flatMap(Double.init) ?? 0.0
        self.forcedTimestamp = forcedTimestamp
        self.openUrl = openUrl
    }
    
    public func makeContentNode(context: AccountContext, postbox: Postbox, audioSession: ManagedAudioSession) -> UniversalVideoContentNode & ASDisplayNode {
        return WebEmbedVideoContentNode(postbox: postbox, audioSessionManager: audioSession, userLocation: self.userLocation, webPage: self.webPage, webpageContent: self.webpageContent, forcedTimestamp: self.forcedTimestamp, openUrl: self.openUrl)
    }
}
 
final class WebEmbedVideoContentNode: ASDisplayNode, UniversalVideoContentNode {
    private let webpageContent: TelegramMediaWebpageLoadedContent
    private let intrinsicDimensions: CGSize
    
    private let playbackCompletedListeners = Bag<() -> Void>()
    
    private var initializedStatus = false
    private let _status = Promise<MediaPlayerStatus>()
    var status: Signal<MediaPlayerStatus, NoError> {
        return self._status.get()
    }
    
    private let _bufferingStatus = Promise<(RangeSet<Int64>, Int64)?>()
    var bufferingStatus: Signal<(RangeSet<Int64>, Int64)?, NoError> {
        return self._bufferingStatus.get()
    }
    
    var isNativePictureInPictureActive: Signal<Bool, NoError> {
        return self.playerNode.nagramiXSystemPiPActive
    }
    
    private var seekId: Int = 0
    
    private let _ready = Promise<Void>()
    var ready: Signal<Void, NoError> {
        return self._ready.get()
    }
    
    private let imageNode: TransformImageNode
    private let playerNode: WebEmbedPlayerNode
    
    var impl: WebEmbedImplementation {
        return playerNode.impl
    }
        
    private let audioSessionManager: ManagedAudioSession
    private let audioSessionDisposable = MetaDisposable()
    private let nagramiXPipDisposable = MetaDisposable()
    private let nagramiXStatusDisposable = MetaDisposable()
    private var nagramiXPlaybackRequested = false
    private var nagramiXBackgroundOwners = Set<UUID>()
    private var nagramiXHasManagedAudio = false
    private var nagramiXAudioReady = false
    private var nagramiXPendingPlay = false
    private var nagramiXPlayCommandSent = false
    private var nagramiXAudioSuspended = false
    private var nagramiXInterruptionPauseConfirmed = false
    private var nagramiXAudioGeneration: UInt64 = 0
    private var nagramiXBackgroundObserver: NSObjectProtocol?
    private var nagramiXForegroundObserver: NSObjectProtocol?
    private var nagramiXInForeground = true
    private var readyDisposable = MetaDisposable()
    
    init(postbox: Postbox, audioSessionManager: ManagedAudioSession, userLocation: MediaResourceUserLocation, webPage: TelegramMediaWebpage, webpageContent: TelegramMediaWebpageLoadedContent, forcedTimestamp: Int? = nil, openUrl: @escaping (URL) -> Void) {
        self.audioSessionManager = audioSessionManager
        self.webpageContent = webpageContent
        
        if let embedSize = webpageContent.embedSize {
            self.intrinsicDimensions = embedSize.cgSize
        } else {
            self.intrinsicDimensions = CGSize(width: 480.0, height: 320.0)
        }
    
        self.imageNode = TransformImageNode()
        
        let embedType = webEmbedType(content: webpageContent, forcedTimestamp: forcedTimestamp)
        let embedImpl = webEmbedImplementation(for: embedType)
        self.playerNode = WebEmbedPlayerNode(impl: embedImpl, intrinsicDimensions: self.intrinsicDimensions, openUrl: openUrl)
        
        super.init()
        
        self.addSubnode(self.playerNode)
        self.addSubnode(self.imageNode)
        
        if let image = webpageContent.image {
            self.imageNode.setSignal(chatMessagePhoto(postbox: postbox, userLocation: userLocation, photoReference: .webPage(webPage: WebpageReference(webPage), media: image)))
            self.imageNode.imageUpdated = { [weak self] _ in
                self?._ready.set(.single(Void()))
            }
        } else {
            self._ready.set(.single(Void()))
        }
        self.nagramiXStatusDisposable.set((self.playerNode.status |> deliverOnMainQueue).start(next: { [weak self] status in
            guard let self else { return }
            switch status.status {
            case .playing:
                if self.nagramiXAudioSuspended && self.nagramiXInterruptionPauseConfirmed {
                    self.nagramiXAudioSuspended = false
                    self.nagramiXInterruptionPauseConfirmed = false
                }
                self.nagramiXPlaybackRequested = true
                self.nagramiXPendingPlay = false
                self.nagramiXPlayCommandSent = false
            case .paused:
                if self.nagramiXAudioSuspended { self.nagramiXInterruptionPauseConfirmed = true }
                if !self.nagramiXPendingPlay { self.nagramiXPlaybackRequested = false }
            case let .buffering(_, whilePlaying, _, _): if !self.nagramiXPendingPlay { self.nagramiXPlaybackRequested = self.nagramiXPlaybackRequested && whilePlaying }

            }
            self.nagramiXUpdateManagedPlayback()
        }))
        self.nagramiXPipDisposable.set((self.playerNode.nagramiXSystemPiPActive |> deliverOnMainQueue).start(next: { [weak self] _ in
            self?.nagramiXUpdateManagedPlayback()
        }))
        self.nagramiXBackgroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            self?.nagramiXInForeground = false
            self?.nagramiXUpdateManagedPlayback()
        }
        self.nagramiXForegroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.willEnterForegroundNotification, object: nil, queue: .main) { [weak self] _ in
            self?.nagramiXInForeground = true
            self?.nagramiXUpdateManagedPlayback()
        }
        self._status.set(self.playerNode.status)
        self._bufferingStatus.set(.single(nil))
        
        self.readyDisposable.set(self.playerNode.ready.start(next: { [weak self] ready in
            if ready {
                self?.imageNode.isHidden = true
            }
        }, error: { _ in }, completed: {}))
    }
    
    deinit {
        self.readyDisposable.dispose()
        self.nagramiXPipDisposable.dispose()
        self.nagramiXStatusDisposable.dispose()
        self.audioSessionDisposable.dispose()
        if let observer = self.nagramiXForegroundObserver { NotificationCenter.default.removeObserver(observer) }
        if let observer = self.nagramiXBackgroundObserver { NotificationCenter.default.removeObserver(observer) }
    }
    
    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        transition.updatePosition(node: self.playerNode, position: CGPoint(x: size.width / 2.0, y: size.height / 2.0))
        transition.updateTransformScale(node: self.playerNode, scale: size.width / self.intrinsicDimensions.width)

        transition.updateFrame(node: self.imageNode, frame: CGRect(origin: CGPoint(), size: size))
        
        if let image = webpageContent.image, let representation = image.representationForDisplayAtSize(PixelDimensions(self.intrinsicDimensions)) {
            let makeImageLayout = self.imageNode.asyncLayout()
            let applyImageLayout = makeImageLayout(TransformImageArguments(corners: ImageCorners(), imageSize: representation.dimensions.cgSize.aspectFilled(size), boundingSize: size, intrinsicInsets: UIEdgeInsets()))
            applyImageLayout()
        }
    }
    
    func play() {
        assert(Queue.mainQueue().isCurrent())

        self.nagramiXPlaybackRequested = true
        self.nagramiXPendingPlay = true
        self.nagramiXPlayCommandSent = false
        self.nagramiXAudioSuspended = false
        self.nagramiXUpdateManagedPlayback()
    }
    
    func pause() {
        assert(Queue.mainQueue().isCurrent())

        self.nagramiXPlaybackRequested = false
        self.nagramiXPendingPlay = false
        self.playerNode.pause()
        self.nagramiXUpdateManagedPlayback()
    }
    
    func togglePlayPause() {
        assert(Queue.mainQueue().isCurrent())
        if self.nagramiXPlaybackRequested { self.pause() } else { self.play() }
    }
    
    func setSoundEnabled(_ value: Bool) {
        assert(Queue.mainQueue().isCurrent())
    }
    
    func seek(_ timestamp: Double) {
        assert(Queue.mainQueue().isCurrent())
        self.seekId += 1
        self.playerNode.seek(timestamp: timestamp)
    }
    
    func playOnceWithSound(playAndRecord: Bool, seek: MediaPlayerSeek, actionAtEnd: MediaPlayerPlayOnceWithSoundActionAtEnd) {
        if case let .timecode(time) = seek {
            self.playerNode.seek(timestamp: time)
        }
        self.play()
    }
    
    func setSoundMuted(soundMuted: Bool) {
    }
    
    func continueWithOverridingAmbientMode(isAmbient: Bool) {
    }
    
    func setForceAudioToSpeaker(_ forceAudioToSpeaker: Bool) {
    }
    
    func continuePlayingWithoutSound(actionAtEnd: MediaPlayerPlayOnceWithSoundActionAtEnd) {
    }
    
    func setContinuePlayingWithoutSoundOnLostAudioSession(_ value: Bool) {   
    }
    
    func setBaseRate(_ baseRate: Double) {
        self.playerNode.setBaseRate(baseRate)
    }
    
    func setVideoQuality(_ videoQuality: UniversalVideoContentVideoQuality) {
    }
    
    func videoQualityState() -> (current: Int, preferred: UniversalVideoContentVideoQuality, available: [Int])? {
        return nil
    }
    
    func videoQualityStateSignal() -> Signal<(current: Int, preferred: UniversalVideoContentVideoQuality, available: [Int])?, NoError> {
        return .single(nil)
    }
    
    func addPlaybackCompleted(_ f: @escaping () -> Void) -> Int {
        return self.playbackCompletedListeners.add(f)
    }
    
    func removePlaybackCompleted(_ index: Int) {
        self.playbackCompletedListeners.remove(index)
    }
    
    func fetchControl(_ control: UniversalVideoNodeFetchControl) {
    }
    
    func notifyPlaybackControlsHidden(_ hidden: Bool) {
        self.playerNode.notifyPlaybackControlsHidden(hidden)
    }

    func setCanPlaybackWithoutHierarchy(_ canPlaybackWithoutHierarchy: Bool) {
    }
    
    func setNagramiXBackgroundPlayback(id: UUID, active: Bool) {
        if active { self.nagramiXBackgroundOwners.insert(id) } else { self.nagramiXBackgroundOwners.remove(id) }
        self.nagramiXUpdateManagedPlayback()
    }

    private func nagramiXUpdateManagedPlayback() {
        let permitted = !self.nagramiXAudioSuspended && (self.playerNode.nagramiXIsSystemPiPActive || (!self.nagramiXBackgroundOwners.isEmpty && NagramiXTabSettings.backgroundVideoPlaybackEnabled))
        self.playerNode.setNagramiXBackgroundPlayback(permitted)
        let needsAudio = !self.nagramiXAudioSuspended && (permitted || (self.nagramiXInForeground && self.nagramiXPlaybackRequested))
        if needsAudio && !self.nagramiXHasManagedAudio {
            self.nagramiXHasManagedAudio = true
            self.nagramiXAudioGeneration &+= 1
            let generation = self.nagramiXAudioGeneration
            self.audioSessionDisposable.set(self.audioSessionManager.push(audioSessionType: .play(mixWithOthers: false), once: true, activate: { [weak self] _ in
                Queue.mainQueue().async {
                    guard let self, self.nagramiXAudioGeneration == generation, self.nagramiXHasManagedAudio else { return }
                    self.nagramiXAudioReady = true
                    self.nagramiXUpdateManagedPlayback()
                }
            }, deactivate: { [weak self] _ in
                return Signal { subscriber in
                    if let self, self.nagramiXAudioGeneration == generation {
                        self.nagramiXAudioGeneration &+= 1
                        self.nagramiXHasManagedAudio = false
                        self.nagramiXAudioReady = false
                        self.nagramiXPendingPlay = false
                        self.nagramiXPlaybackRequested = false
                        self.nagramiXAudioSuspended = true
                        self.nagramiXInterruptionPauseConfirmed = false
                        self.playerNode.setNagramiXBackgroundPlayback(false)
                        self.playerNode.pause()
                    }
                    subscriber.putCompletion()
                    return EmptyDisposable
                } |> runOn(.mainQueue())
            }))
        } else if !needsAudio {
            self.nagramiXAudioGeneration &+= 1
            self.nagramiXHasManagedAudio = false
            self.nagramiXAudioReady = false
            self.audioSessionDisposable.set(nil)
            if !self.nagramiXInForeground {
                self.nagramiXPendingPlay = false
                self.playerNode.pause()
            }
        }
        if needsAudio && self.nagramiXAudioReady && self.nagramiXPendingPlay && !self.nagramiXPlayCommandSent {
            self.nagramiXPlayCommandSent = true
            self.playerNode.play()
        }
    }

    func setNagramiXNativePiPRestore(_ restore: ((@escaping (Bool) -> Void) -> Void)?) {
        self.playerNode.setNagramiXNativePiPRestore(restore)
    }

    func enterNativePictureInPicture() -> Bool {
        let accepted = self.playerNode.enterNativePictureInPicture()
        self.nagramiXUpdateManagedPlayback()
        return accepted
    }
    
    func exitNativePictureInPicture() {
        self.playerNode.exitNativePictureInPicture()
    }
    
    func setNativePictureInPictureIsActive(_ value: Bool) {
    }
}

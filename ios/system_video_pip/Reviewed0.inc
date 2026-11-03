private final class NativePictureInPictureContentImpl: NSObject, AVPictureInPictureControllerDelegate {
    private final class PlaybackDelegate: NSObject, AVPictureInPictureSampleBufferPlaybackDelegate {
        private let node: UniversalVideoNode
        private var statusDisposable: Disposable?
        private var status: MediaPlayerStatus?
        weak var pictureInPictureController: AVPictureInPictureController?
        
        private var previousIsPlaying = false
        init(node: UniversalVideoNode) {
            self.node = node

            super.init()

            var invalidatedStateOnce = false
            self.statusDisposable = (self.node.status
            |> deliverOnMainQueue).start(next: { [weak self] status in
                guard let strongSelf = self else {
                    return
                }
                strongSelf.status = status
                if let status {
                    let isPlaying = status.status == .playing
                    if !invalidatedStateOnce {
                        invalidatedStateOnce = true
                        strongSelf.pictureInPictureController?.invalidatePlaybackState()
                    } else if strongSelf.previousIsPlaying != isPlaying {
                        strongSelf.previousIsPlaying = isPlaying
                        strongSelf.pictureInPictureController?.invalidatePlaybackState()
                    }
                }
            }).strict()
        }

        deinit {
            self.statusDisposable?.dispose()
        }
        
        public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, setPlaying playing: Bool) {
            self.node.togglePlayPause()
        }

        public func pictureInPictureControllerTimeRangeForPlayback(_ pictureInPictureController: AVPictureInPictureController) -> CMTimeRange {
            guard let status = self.status else {
                return CMTimeRange(start: CMTime(seconds: 0.0, preferredTimescale: CMTimeScale(30.0)), duration: CMTime(seconds: 0.0, preferredTimescale: CMTimeScale(30.0)))
            }
            return CMTimeRange(start: CMTime(seconds: 0.0, preferredTimescale: CMTimeScale(30.0)), duration: CMTime(seconds: status.duration, preferredTimescale: CMTimeScale(30.0)))
        }

        public func pictureInPictureControllerIsPlaybackPaused(_ pictureInPictureController: AVPictureInPictureController) -> Bool {
            guard let status = self.status else {
                return false
            }
            switch status.status {
            case .playing:
                return false
            case .buffering, .paused:
                return true
            }
        }

        public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, didTransitionToRenderSize newRenderSize: CMVideoDimensions) {
        }

        public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, skipByInterval skipInterval: CMTime, completion completionHandler: @escaping () -> Void) {
            let node = self.node
            let _ = (self.node.status
            |> take(1)
            |> deliverOnMainQueue).start(next: { [weak node] status in
                if let node = node, let timestamp = status?.timestamp, let duration = status?.duration {
                    let nextTimestamp = timestamp + skipInterval.seconds
                    if nextTimestamp > duration {
                        node.seek(0.0)
                        node.pause()
                    } else {
                        node.seek(min(duration, nextTimestamp))
                    }
                }

                completionHandler()
            })
        }

        public func pictureInPictureControllerShouldProhibitBackgroundAudioPlayback(_ pictureInPictureController: AVPictureInPictureController) -> Bool {
            return false
        }
    }

    private let context: AccountContext
    private let accountId: AccountRecordId
    private let hiddenMedia: (MessageId, Media)?
    private weak var mediaManager: MediaManager?
    private var pictureInPictureController: AVPictureInPictureController?
    private var contentDelegate: PlaybackDelegate?
    private let node: UniversalVideoNode
    private let willBegin: (NativePictureInPictureContentImpl) -> Void
    private let didBegin: (NativePictureInPictureContentImpl) -> Void
    private let didEnd: (NativePictureInPictureContentImpl) -> Void
    private let expand: (@escaping () -> Void) -> Void
    private var pictureInPictureTimer: SwiftSignalKit.Timer?
    private var didExpand: Bool = false
    private var isCentral = false
    private var pictureInPicturePossibleObservation: NSKeyValueObservation?

    private var hiddenMediaManagerIndex: Int?

    private var messageRemovedDisposable: Disposable?
    
    private var isNativePictureInPictureActiveDisposable: Disposable?

    init(context: AccountContext, mediaManager: MediaManager, accountId: AccountRecordId, hiddenMedia: (MessageId, Media)?, videoNode: UniversalVideoNode, canSkip: Bool, willBegin: @escaping (NativePictureInPictureContentImpl) -> Void, didBegin: @escaping (NativePictureInPictureContentImpl) -> Void, didEnd: @escaping (NativePictureInPictureContentImpl) -> Void, expand: @escaping (@escaping () -> Void) -> Void) {
        self.context = context
        self.mediaManager = mediaManager
        self.accountId = accountId
        self.hiddenMedia = hiddenMedia
        self.node = videoNode
        self.willBegin = willBegin
        self.didBegin = didBegin
        self.didEnd = didEnd
        self.expand = expand

        super.init()

        if let videoLayer = videoNode.getVideoLayer() {
            let contentDelegate = PlaybackDelegate(node: self.node)
            self.contentDelegate = contentDelegate
            
            let pictureInPictureController = AVPictureInPictureController(contentSource: AVPictureInPictureController.ContentSource(sampleBufferDisplayLayer: videoLayer, playbackDelegate: contentDelegate))
            self.pictureInPictureController = pictureInPictureController
            contentDelegate.pictureInPictureController = pictureInPictureController
            
            pictureInPictureController.canStartPictureInPictureAutomaticallyFromInline = false
            pictureInPictureController.requiresLinearPlayback = !canSkip
            pictureInPictureController.delegate = self
            self.pictureInPictureController = pictureInPictureController
            self.pictureInPicturePossibleObservation = pictureInPictureController.observe(\.isPictureInPicturePossible, options: [.new]) { [weak self] pictureInPictureController, _ in
                guard let self, pictureInPictureController.isPictureInPicturePossible else {
                    return
                }
                pictureInPictureController.canStartPictureInPictureAutomaticallyFromInline = self.isCentral
            }
        }

        if let (messageId, _) = hiddenMedia {
            var hadMessage: Bool?
            self.messageRemovedDisposable = (context.engine.data.subscribe(TelegramEngine.EngineData.Item.Messages.Message(id: messageId))
            |> map { message -> Bool in
                if let _ = message {
                    return true
                } else {
                    return false
                }
            }
            |> deliverOnMainQueue).start(next: { [weak self] value in
                guard let self else {
                    return
                }
                if let hadMessage, hadMessage {
                    if value {
                    } else {
                        if let pictureInPictureController = self.pictureInPictureController {
                            pictureInPictureController.stopPictureInPicture()
                        }
                    }
                    
                    return
                }
                hadMessage = value
            })
        }
    }

    deinit {
        self.pictureInPicturePossibleObservation?.invalidate()
        self.pictureInPictureController?.canStartPictureInPictureAutomaticallyFromInline = false
        self.pictureInPictureController?.delegate = nil
        self.pictureInPictureController?.contentSource = nil
        self.contentDelegate?.pictureInPictureController = nil
        self.pictureInPictureController = nil
        self.messageRemovedDisposable?.dispose()
        self.isNativePictureInPictureActiveDisposable?.dispose()
        self.pictureInPictureTimer?.invalidate()
        self.node.setCanPlaybackWithoutHierarchy(false)

        if let hiddenMediaManagerIndex = self.hiddenMediaManagerIndex, let mediaManager = self.mediaManager {
            mediaManager.galleryHiddenMediaManager.removeSource(hiddenMediaManagerIndex)
        }
    }
    
    func updateIsCentral(isCentral: Bool) {
        self.isCentral = isCentral
        guard let pictureInPictureController = self.pictureInPictureController else {
            return
        }
        
        if isCentral {
            pictureInPictureController.canStartPictureInPictureAutomaticallyFromInline = true
        } else {
            pictureInPictureController.canStartPictureInPictureAutomaticallyFromInline = false
        }
    }
    
    func beginPictureInPicture() {
        guard let pictureInPictureController = self.pictureInPictureController else {
            return
        }
        if pictureInPictureController.isPictureInPicturePossible {
            pictureInPictureController.startPictureInPicture()
        }
    }
    
    func invalidatePlaybackState() {
        guard let pictureInPictureController = self.pictureInPictureController else {
            return
        }
        if pictureInPictureController.isPictureInPictureActive {
            pictureInPictureController.invalidatePlaybackState()
        }
    }

    public func pictureInPictureControllerWillStartPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        self.node.setCanPlaybackWithoutHierarchy(true)
        
        if let hiddenMedia = self.hiddenMedia, let mediaManager = self.mediaManager, !"".isEmpty {
            let accountId = self.accountId
            self.hiddenMediaManagerIndex = mediaManager.galleryHiddenMediaManager.addSource(Signal<(MessageId, Media)?, NoError>.single(hiddenMedia)
            |> map { messageIdAndMedia in
                if let (messageId, media) = messageIdAndMedia {
                    return .chat(accountId, messageId, media)
                } else {
                    return nil
                }
            })
        }
        
        self.willBegin(self)
    }

    public func pictureInPictureControllerDidStartPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        self.didBegin(self)
    }

    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, failedToStartPictureInPictureWithError error: Error) {
        print(error)
    }

    public func pictureInPictureControllerWillStopPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
    }

    public func pictureInPictureControllerDidStopPictureInPicture(_ pictureInPictureController: AVPictureInPictureController) {
        self.node.setCanPlaybackWithoutHierarchy(false)
        if let hiddenMediaManagerIndex = self.hiddenMediaManagerIndex, let mediaManager = self.mediaManager {
            mediaManager.galleryHiddenMediaManager.removeSource(hiddenMediaManagerIndex)
            self.hiddenMediaManagerIndex = nil
        }
        self.didEnd(self)
    }

    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler completionHandler: @escaping (Bool) -> Void) {
        self.expand { [weak self] in
            guard let strongSelf = self else {
                return
            }

            strongSelf.didExpand = true

            completionHandler(true)
        }
    }
    
    public func requestExpand() {
        self.pictureInPictureController?.stopPictureInPicture()
    }
    
    public func stop() {
        self.pictureInPictureController?.stopPictureInPicture()
    }
}

import Foundation

// AVKit/KVO, UIKit, account data and scheduling are explicit test boundaries.
// Full production controller/delegate, setup, button, swipe and restore bodies run.
struct NoError: Error {}
final class Disposable {
    private var cancel: (() -> Void)?
    init(_ cancel: @escaping () -> Void = {}) { self.cancel = cancel }
    func dispose() { cancel?(); cancel = nil }
    func strict() -> Disposable { self }
}
final class Signal<T, E> {
    var value: T
    var handlers: [UUID: (T) -> Void] = [:]
    init(_ value: T) { self.value = value }
    static func single(_ value: T) -> Signal<T,E> { Signal(value) }
    func start(next: @escaping (T) -> Void) -> Disposable {
        let id = UUID(); handlers[id] = next; next(value)
        return Disposable { [weak self] in self?.handlers.removeValue(forKey: id) }
    }
    func emit(_ value: T) { self.value = value; for f in Array(handlers.values) { f(value) } }
}
infix operator |> : AdditionPrecedence
func |> <T,U>(lhs: T, rhs: (T) -> U) -> U { rhs(lhs) }
func map<T,U,E>(_ f: @escaping (T) -> U) -> (Signal<T,E>) -> Signal<U,E> {
    { source in
        let result = Signal<U,E>(f(source.value))
        _ = source.start { [weak result] in result?.emit(f($0)) }
        return result
    }
}
func deliverOnMainQueue<T,E>(_ signal: Signal<T,E>) -> Signal<T,E> { signal }
func take<T,E>(_ count: Int) -> (Signal<T,E>) -> Signal<T,E> { { Signal<T,E>.single($0.value) } }
enum SwiftSignalKit { final class Timer { func invalidate() {} } }
final class ImmediateQueue { func async(_ f: @escaping () -> Void) { f() } }
enum Queue { static func mainQueue() -> ImmediateQueue { ImmediateQueue() } }
enum DispatchQueue { static let main = ImmediateQueue() }
typealias CMTimeScale = Int32
struct CMTime { let seconds: Double; init(seconds: Double, preferredTimescale: CMTimeScale) { self.seconds = seconds } }
struct CMTimeRange { let start: CMTime; let duration: CMTime }
struct CMVideoDimensions {}
enum Playback { case playing, paused, buffering }
struct MediaPlayerStatus { var status: Playback = .playing; var duration = 100.0; var timestamp = 30.0 }
protocol AVPictureInPictureControllerDelegate: AnyObject {
    func pictureInPictureControllerWillStartPictureInPicture(_ controller: AVPictureInPictureController)
    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController)
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController)
}
protocol AVPictureInPictureSampleBufferPlaybackDelegate: AnyObject {
    func pictureInPictureController(_ controller: AVPictureInPictureController, setPlaying: Bool)
}
final class NSKeyValueObservation {
    var action: (() -> Void)?
    init(_ action: @escaping () -> Void) { self.action = action }
    func invalidate() { action?(); action = nil }
    deinit { invalidate() }
}
struct ObservationOptions: OptionSet { let rawValue: Int; static let new = Self(rawValue: 1) }
final class VideoLayer {}
final class AVPictureInPictureController: NSObject {
    static var instances: [AVPictureInPictureController] = []
    final class ContentSource {
        let sampleBufferDisplayLayer: VideoLayer
        weak var playbackDelegate: AVPictureInPictureSampleBufferPlaybackDelegate?
        init(sampleBufferDisplayLayer: VideoLayer, playbackDelegate: AVPictureInPictureSampleBufferPlaybackDelegate) {
            self.sampleBufferDisplayLayer = sampleBufferDisplayLayer; self.playbackDelegate = playbackDelegate
        }
    }
    weak var delegate: AVPictureInPictureControllerDelegate?
    var contentSource: ContentSource?
    var canStartPictureInPictureAutomaticallyFromInline = false
    var requiresLinearPlayback = false
    var isPictureInPictureActive = false
    var isPictureInPicturePossible = false { didSet { for f in Array(observers.values) { f(self,nil) } } }
    var observers: [UUID:(AVPictureInPictureController, Int?) -> Void] = [:]
    var starts = 0, stops = 0, invalidations = 0
    init(contentSource: ContentSource) { self.contentSource = contentSource; super.init(); Self.instances.append(self) }
    func observe(_ key: KeyPath<AVPictureInPictureController,Bool>, options: ObservationOptions, changeHandler: @escaping (AVPictureInPictureController, Int?) -> Void) -> NSKeyValueObservation {
        let id = UUID(); observers[id] = changeHandler
        return NSKeyValueObservation { [weak self] in self?.observers.removeValue(forKey: id) }
    }
    func startPictureInPicture() {
        starts += 1; isPictureInPictureActive = true
        delegate?.pictureInPictureControllerWillStartPictureInPicture(self)
        delegate?.pictureInPictureControllerDidStartPictureInPicture(self)
    }
    func stopPictureInPicture() {
        stops += 1
        if isPictureInPictureActive { isPictureInPictureActive = false; delegate?.pictureInPictureControllerDidStopPictureInPicture(self) }
    }
    func invalidatePlaybackState() { invalidations += 1 }
}
final class UniversalVideoNode {
    let layer = VideoLayer()
    var hasLayer = true, ownsContentNode = true, withoutHierarchy = false
    var toggles = 0, pauses = 0
    var seeks: [Double] = []
    let status = Signal<MediaPlayerStatus?,NoError>(MediaPlayerStatus())
    func getVideoLayer() -> VideoLayer? { hasLayer ? layer : nil }
    func togglePlayPause() { toggles += 1 }
    func seek(_ value: Double) { seeks.append(value) }
    func pause() { pauses += 1 }
    func setCanPlaybackWithoutHierarchy(_ value: Bool) { withoutHierarchy = value }
    func setNativePictureInPictureIsActive(_ value: Bool) {}
}
typealias MessageId = Int
typealias AccountRecordId = Int
class Media {}
final class TelegramMediaImage: Media {}
final class TelegramMediaFile: Media { var isVideo = true; var isAnimated = false }
struct Message { var id = 1; var adAttribute: Int?; var effectiveMedia: [Media] = [] }
enum HiddenSource { case chat(AccountRecordId,MessageId,Media) }
final class HiddenMediaManager {
    var removals: [Int] = []
    func addSource(_ source: Signal<HiddenSource?,NoError>) -> Int { 1 }
    func removeSource(_ index: Int) { removals.append(index) }
}
final class MediaManager {
    var currentPictureInPictureNode: AnyObject?
    let galleryHiddenMediaManager = HiddenMediaManager()
}
enum TelegramEngine { enum EngineData { enum Item { enum Messages { struct Message { let id: Int } } } } }
final class EngineData {
    let messages = Signal<Message?,NoError>(Message())
    func subscribe(_ request: TelegramEngine.EngineData.Item.Messages.Message) -> Signal<Message?,NoError> { messages }
}
final class AccountData { var logs: [String] = []; func addAppLogEvent(type: String) { logs.append(type) } }
final class Engine { let data = EngineData(); let accountData = AccountData() }
struct AppConfiguration { var data: [String:Any]? }
final class Configuration { var value = AppConfiguration(); func with<T>(_ f: (AppConfiguration) -> T) -> T { f(value) } }
final class SharedContext { let mediaManager = MediaManager() }
struct Account { let id = 1 }
final class AccountContext { let engine = Engine(); let sharedContext = SharedContext(); let account = Account(); let currentAppConfiguration = Configuration() }
final class NativeVideoContent { let fileReference = Reference() }
final class Reference { let media = TelegramMediaFile() }
enum ContentInfo { case message(Message,Int), webPage(Int,Int,Int) }
final class Item {
    var content: AnyObject = NativeVideoContent()
    var contentInfo: ContentInfo? = .message(Message(),0)
    var displayInfoOnTop = false, peerIsCopyProtected = false
}
final class Footer {
    func setMessage(_ message: Message, mediaSubject: Int, displayInfo: Bool, peerIsCopyProtected: Bool, displayPictureInPictureButton: Bool, settingsButtonState: Int, displayStickersButton: Bool) {}
    func setWebPage(_ page: Int, media: Int) {}
}
final class Layer { func animateAlpha(from: Double, to: Double, duration: Double, completion: @escaping (Bool) -> Void) { completion(true) } }
final class UIView { var alpha = 1.0; let layer = Layer() }
class BaseController { let view = UIView(); var presentationArguments: Int? = 7 }
final class GalleryController: BaseController { var dismissals = 0; func dismiss(forceAway: Bool) { dismissals += 1 } }
enum Surface { case root }
final class Window {
    var presentations = 0
    func present(_ controller: BaseController, on: Surface, blockInteraction: Bool, completion: @escaping () -> Void) { presentations += 1; completion() }
}
final class NavigationController { let currentWindow: Window? = Window() }
enum NagramiXTabSettings { static var videoPiPSwipeEnabled = true }
class GalleryBase {
    func maybePerformActionForSwipeDismiss() -> Bool { false }
    func maybePerformActionForSwipeDownDismiss() -> Bool { false }
}
enum Dismiss { case pip }

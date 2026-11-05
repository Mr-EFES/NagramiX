import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

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

struct DispatchTime {
    let value: Double
    static func now() -> DispatchTime { DispatchTime(value: TestScheduler.now) }
    static func + (lhs: DispatchTime, rhs: Double) -> DispatchTime { DispatchTime(value: lhs.value + rhs) }
}
final class DispatchWorkItem {
    private let body: () -> Void
    private(set) var cancelled = false
    init(block: @escaping () -> Void) { self.body = block }
    func cancel() { cancelled = true }
    func perform() { if !cancelled { body() } }
}
enum TestScheduler {
    static var now = 0.0
    static var entries: [(Double, Int, () -> Void)] = []
    static var next = 0
    static func enqueue(_ time: Double, _ body: @escaping () -> Void) { next += 1; entries.append((time,next,body)) }
    static func advance(_ interval: Double = 0) {
        let target = now + interval
        var delivered = 0
        while let first = entries.indices.filter({ entries[$0].0 <= target }).min(by: {
            entries[$0].0 == entries[$1].0 ? entries[$0].1 < entries[$1].1 : entries[$0].0 < entries[$1].0
        }) {
            let entry = entries.remove(at: first); now = entry.0; entry.2(); delivered += 1
            precondition(delivered < 10000, "unbounded scheduling")
        }
        now = target
    }
}
final class TestMainQueue {
    func async(_ body: @escaping () -> Void) { TestScheduler.enqueue(TestScheduler.now, body) }
    func asyncAfter(deadline: DispatchTime, execute item: DispatchWorkItem) { TestScheduler.enqueue(deadline.value, { item.perform() }) }
}
enum DispatchQueue { static let main = TestMainQueue() }

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
struct ObservationOptions: OptionSet { let rawValue: Int; static let new = Self(rawValue: 1); static let initial = Self(rawValue: 2) }

final class CGColor {}
enum CALayerCornerCurve { case circular, continuous }
struct CACornerMask: OptionSet {
    let rawValue: Int
    static let layerMinXMinYCorner = Self(rawValue: 1)
    static let layerMaxXMinYCorner = Self(rawValue: 2)
    static let layerMinXMaxYCorner = Self(rawValue: 4)
    static let layerMaxXMaxYCorner = Self(rawValue: 8)
}
class CALayer {
    var cornerRadius: CGFloat = 0
    var cornerCurve = CALayerCornerCurve.circular
    var maskedCorners = CACornerMask.layerMinXMinYCorner
    var masksToBounds = false
    var isOpaque = true
    var backgroundColor: CGColor? = CGColor()
    var bounds = CGRect(x: 0, y: 0, width: 1920, height: 1080)
    var animations: [String: CABasicAnimation] = [:]
    var presented: CALayer?
    func presentation() -> CALayer? { presented }
    func add(_ animation: CABasicAnimation, forKey key: String) { animations[key] = animation }
    func removeAnimation(forKey key: String) { animations.removeValue(forKey: key) }
}
final class AVSampleBufferDisplayLayer: CALayer {
    // MediaPlayerNodeLayer does not implement init(layer:). Core Animation
    // presentation copies trap in that initializer on the real video layer.
    override func presentation() -> CALayer? {
        fatalError("first PiP regression: sample-buffer presentation copy invokes unsupported init(layer:)")
    }
    override func add(_ animation: CABasicAnimation, forKey key: String) {
        fatalError("first PiP regression: custom sample-buffer animation requires an unsupported presentation copy")
    }
}
typealias VideoLayer = AVSampleBufferDisplayLayer
enum UIAccessibility { static var isReduceMotionEnabled = false }
enum CATransaction {
    static var depth = 0
    static func begin() { depth += 1 }
    static func setDisableActions(_ value: Bool) { precondition(value && depth > 0) }
    static func commit() { depth -= 1 }
}
final class CABasicAnimation {
    let keyPath: String
    var fromValue: Any?, toValue: Any?
    var duration = 0.0
    var timingFunction: CAMediaTimingFunction?
    init(keyPath: String) { self.keyPath = keyPath }
}
struct CAMediaTimingFunctionName { static let easeInEaseOut = Self() }
final class CAMediaTimingFunction { init(name: CAMediaTimingFunctionName) {} }

final class AVPictureInPictureController: NSObject {
    static var instances: [AVPictureInPictureController] = []
    static var supported = true
    static func isPictureInPictureSupported() -> Bool { supported }
    var completesStart = true

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
        if options.contains(.initial) { changeHandler(self,nil) }
        return NSKeyValueObservation { [weak self] in self?.observers.removeValue(forKey: id) }
    }
    func startPictureInPicture() {
        starts += 1
        delegate?.pictureInPictureControllerWillStartPictureInPicture(self)
        if completesStart { finishStart() }
    }
    func finishStart() {
        isPictureInPictureActive = true
        delegate?.pictureInPictureControllerDidStartPictureInPicture(self)
    }
    func stopPictureInPicture() {
        stops += 1
        if isPictureInPictureActive { isPictureInPictureActive = false; delegate?.pictureInPictureControllerDidStopPictureInPicture(self) }
    }
    func invalidatePlaybackState() { invalidations += 1 }
}
final class UniversalVideoNode {
    var layer = VideoLayer()
    var hasLayer = true, ownsContentNode = true, withoutHierarchy = false, nativePictureInPictureActive = false
    var toggles = 0, pauses = 0
    var seeks: [Double] = []
    let status = Signal<MediaPlayerStatus?,NoError>(MediaPlayerStatus())
    func getVideoLayer() -> VideoLayer? { hasLayer ? layer : nil }
    func togglePlayPause() { toggles += 1 }
    func seek(_ value: Double) { seeks.append(value) }
    func pause() { pauses += 1 }
    func setCanPlaybackWithoutHierarchy(_ value: Bool) { withoutHierarchy = value }
    func setNativePictureInPictureIsActive(_ value: Bool) { nativePictureInPictureActive = value }
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

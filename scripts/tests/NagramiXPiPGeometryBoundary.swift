import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

// AVKit/KVO, UIKit rendering/window presentation and account IO are explicit
// boundaries. Production native control, gesture rollback and restore code runs.
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
    func get() -> Signal<T,E> { self }
    func set(_ signal: Signal<T,E>) { emit(signal.value) }
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
struct CMVideoDimensions { var width: Int32; var height: Int32 }
enum Playback { case playing, paused, buffering }
struct MediaPlayerStatus { var status: Playback = .playing; var duration = 100.0; var timestamp = 30.0 }
protocol AVPictureInPictureControllerDelegate: AnyObject {
    func pictureInPictureControllerWillStartPictureInPicture(_ controller: AVPictureInPictureController)
    func pictureInPictureControllerDidStartPictureInPicture(_ controller: AVPictureInPictureController)
    func pictureInPictureControllerWillStopPictureInPicture(_ controller: AVPictureInPictureController)
    func pictureInPictureControllerDidStopPictureInPicture(_ controller: AVPictureInPictureController)
}
protocol AVPictureInPictureSampleBufferPlaybackDelegate: AnyObject {
    func pictureInPictureController(_ controller: AVPictureInPictureController, setPlaying: Bool)
    func pictureInPictureController(_ controller: AVPictureInPictureController, didTransitionToRenderSize: CMVideoDimensions)
    func pictureInPictureController(_ controller: AVPictureInPictureController, skipByInterval: CMTime, completion: @escaping () -> Void)
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
    var isHidden = false
    var superlayer: CALayer?
    var alphaAnimations = 0
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
    func animation(forKey key: String) -> CABasicAnimation? { animations[key] }
    func removeAnimation(forKey key: String) { animations.removeValue(forKey: key) }
    func animateAlpha(from: CGFloat, to: CGFloat, duration: Double, completion: ((Bool) -> Void)? = nil) { alphaAnimations += 1; completion?(true) }
    func animate(from: Any, to: Any, keyPath: String, timingFunction: String, duration: Double, removeOnCompletion: Bool = true) {}
    func animateBounds(from: CGRect, to: CGRect, duration: Double, timingFunction: String, removeOnCompletion: Bool, completion: (Bool) -> Void) { completion(true) }
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
struct CAMediaTimingFunctionName { static let easeInEaseOut = Self(); static let linear = Self(); let rawValue = "linear" }
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
        if isPictureInPictureActive { delegate?.pictureInPictureControllerWillStopPictureInPicture(self); isPictureInPictureActive = false; delegate?.pictureInPictureControllerDidStopPictureInPicture(self) }
    }
    func invalidatePlaybackState() { invalidations += 1 }
}

final class UIColor {
    let opacity: CGFloat
    init(white: CGFloat = 0, alpha: CGFloat = 1) { opacity = alpha }
    static var clear: UIColor { UIColor(alpha: 0) }
    static var black: UIColor { UIColor() }
    var cgColor: CGColor { CGColor() }
    func withAlphaComponent(_ value: CGFloat) -> UIColor { UIColor(alpha: value) }
}
class UIView {
    var alpha: CGFloat = 1
    let layer = CALayer()
    var window: Window? = Window.shared
    var isUserInteractionEnabled = true
    var layoutPasses = 0
    var layoutAction: (() -> Void)?
    var convertedRect: CGRect?
    func convert(_ rect: CGRect, to window: Window?) -> CGRect { convertedRect ?? rect }
    var bounds: CGRect { layer.bounds }
    func layoutIfNeeded() { layoutPasses += 1; layoutAction?() }
    static var durations: [Double] = []
    static func animate(withDuration: Double, animations: () -> Void, completion: ((Bool) -> Void)? = nil) { durations.append(withDuration); animations(); completion?(true) }
}
final class PanGesture {
    var offset = CGPoint.zero
    func translation(in view: UIScrollView?) -> CGPoint { offset }
}
final class UIScrollView: UIView {
    let panGestureRecognizer = PanGesture()
    var isDecelerating = false
    var isScrollEnabled = true
    var isDragging = false
    var contentSize = CGSize(width: 384, height: 2496)
    var contentOffset = CGPoint(x: 0, y: 832)
    func setContentOffset(_ point: CGPoint, animated: Bool) { contentOffset = point }
}
class VisualNode {
    var isHidden = false
    let view = UIView()
    var layer: CALayer { view.layer }
    var alpha: CGFloat { get { view.alpha } set { view.alpha = newValue } }
    var backgroundColor: UIColor? = .black
}
final class StatusBar: VisualNode {
    enum Style { case White, Ignore }
    var statusBarStyle = Style.White
}
final class FooterNode: VisualNode {
    var visibilityAlpha: CGFloat = 1
    func setVisibilityAlpha(_ value: CGFloat, animated: Bool) { visibilityAlpha = value }
}
enum Curve { case easeInOut, linear, customSpring(damping: Double, initialVelocity: Double) }
enum ContainedViewLayoutTransition { case immediate, animated(duration: Double, curve: Curve) }
struct ContainerViewLayout { var size = CGSize(width: 384, height: 832) }
final class Sink {
    func set<T>(_ value: T) {}
}
final class UniversalVideoNode {
    let view = UIView()
    let frameContainer = CALayer()
    var layer = VideoLayer()
    var hasLayer = true, ownsContentNode = true, withoutHierarchy = false, nativePictureInPictureActive = false
    var canAttachContent = true
    var toggles = 0, pauses = 0, plays = 0, mutedContinuations = 0
    var seeks: [Double] = []
    var backgroundColor: UIColor? = .black
    var bounds: CGRect { view.bounds }
    let status = Signal<MediaPlayerStatus?,NoError>(MediaPlayerStatus())
    init() { frameContainer.superlayer = view.layer; layer.superlayer = frameContainer }
    func getVideoLayer() -> VideoLayer? { hasLayer ? layer : nil }
    func play() { plays += 1; if var value = status.value { value.status = .playing; status.emit(value) } }
    func pause() { pauses += 1; if var value = status.value { value.status = .paused; status.emit(value) } }
    func togglePlayPause() { toggles += 1; if status.value?.status == .playing { pause() } else { play() } }
    func seek(_ value: Double) { seeks.append(value); if var current = status.value { current.timestamp = value; status.emit(current) } }
    func setCanPlaybackWithoutHierarchy(_ value: Bool) { withoutHierarchy = value }
    func setNativePictureInPictureIsActive(_ value: Bool) { nativePictureInPictureActive = value }
    func setBaseRate(_ value: Double) {}
    func playOnceWithSound(playAndRecord: Bool, actionAtEnd: Int) { play() }
    func continuePlayingWithoutSound() { mutedContinuations += 1 }
}
typealias MessageId = Int
typealias AccountRecordId = Int
class Media {}
final class TelegramMediaImage: Media {}
final class TelegramMediaFile: Media { var isVideo = true; var isAnimated = false }
struct Message { var id = 1; var adAttribute: Int?; var effectiveMedia: [Media] = [TelegramMediaFile()] }
enum HiddenSource { case chat(AccountRecordId,MessageId,Media) }
final class HiddenMediaManager {
    var nextIndex = 0
    var removals: [Int] = []
    var sources: [Int:Signal<HiddenSource?,NoError>] = [:]
    func addSource(_ source: Signal<HiddenSource?,NoError>) -> Int { nextIndex += 1; sources[nextIndex] = source; return nextIndex }
    func removeSource(_ index: Int) { removals.append(index); sources.removeValue(forKey: index) }
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
struct PresentationStrings { let MediaGallery_ToastVideoPip_Title = "PiP"; let MediaGallery_ToastVideoPip_Text = "Started" }
struct PresentationData { let strings = PresentationStrings() }
final class PresentationValue { func with<T>(_ f: (PresentationData) -> T) -> T { f(PresentationData()) } }
final class SharedContext {
    let mediaManager = MediaManager()
    let currentPresentationData = PresentationValue()
    func setAccountUserInterfaceInUse(_ id: Int) -> Int { 0 }
}
struct Account { let id = 1 }
final class AccountContext { let engine = Engine(); let sharedContext = SharedContext(); let account = Account(); let currentAppConfiguration = Configuration() }
class NativeVideoContent { let fileReference = Reference() }
final class HLSVideoContent: NativeVideoContent {}
final class Reference { let media = TelegramMediaFile() }
enum ContentInfo { case message(Message,Int), webPage(Int,Int,Int) }
final class Item {
    var content: AnyObject = NativeVideoContent()
    var contentInfo: ContentInfo? = .message(Message(),0)
    var displayInfoOnTop = false, peerIsCopyProtected = false
    var fromPlayingVideo = false
}
final class Footer {
    func setMessage(_ message: Message, mediaSubject: Int, displayInfo: Bool, peerIsCopyProtected: Bool, displayPictureInPictureButton: Bool, settingsButtonState: Int, displayStickersButton: Bool) {}
    func setWebPage(_ page: Int, media: Int) {}
}
class BaseController {
    let view = UIView()
    var presentationArguments: Any? = 7
    var topViewController: BaseController?
    var presentingViewController: ParentController?
    func viewDidAppear(_ animated: Bool) {}
}
final class ParentController {
    var onDismiss: (() -> Void)?
    func dismiss(animated: Bool, completion: (() -> Void)?) { onDismiss?(); completion?() }
}
final class ChatController: BaseController {
    var pushed: CGFloat = 1
    var toasts = 0
    var transitions: [ContainedViewLayoutTransition] = []
    func updatePushedTransition(_ value: CGFloat, transition: ContainedViewLayoutTransition) { pushed = value; transitions.append(transition) }
    func present(_ controller: UndoOverlayController, in location: Location) { toasts += 1 }
}
enum Location { case current }
final class UndoOverlayController {
    enum Content { case hidArchive(title: String, text: String, undo: Bool) }
    init(presentationData: PresentationData, content: Content, elevatedLayout: Bool, action: (Int) -> Bool) {}
}
enum Surface { case root }
final class Window {
    static let shared = Window()
    var bounds = CGRect(x: 0, y: 0, width: 384, height: 832)
    var presentations = 0
    var pending: GalleryController?
    func present(_ controller: BaseController, on: Surface, blockInteraction: Bool, completion: @escaping () -> Void) {
        presentations += 1
        pending = controller as? GalleryController
        // Window1's NavigationController route does not deliver completion.
        // Appearance/layout are deliberately delivered separately by each test.
    }
    func finishPresentation(layout: Bool = true) {
        guard let gallery = pending else { return }
        pending = nil
        gallery.attach(to: self)
        if layout { gallery.galleryNode.containerLayout = (44,ContainerViewLayout()) }
        gallery.viewDidAppear(false)
    }
}
final class NavigationController: BaseController { var currentWindow: Window? = .shared }
enum NagramiXTabSettings { static var videoPiPSwipeEnabled = true }
class GalleryBase: VisualNode {
    var index = 0
    var activations = 0
    func maybePerformActionForSwipeDismiss() -> Bool { false }
    func maybePerformActionForSwipeDownDismiss() -> Bool { false }
    func centralityUpdated(isCentral: Bool) {}
    func visibilityUpdated(isVisible: Bool) {}
    var isReadyForNativePictureInPictureRestore: Bool { false }
    var nativePictureInPictureRestoreRect: CGRect? { nil }
    var usesNativePictureInPictureSwipe: Bool { false }
    func title() -> Int { 0 }
    func titleContent() -> Int { 0 }
    func rightBarButtonItem() -> Int { 0 }
    func rightBarButtonItems() -> Int { 0 }
    func navigationStyle() -> Int { 0 }
    func footerContent() -> Int { 0 }
    func isPagingEnabled() -> Int { 0 }
    func activateAsInitial() { activations += 1 }
    func animateIn(from: Int, addToTransitionSurface: Int, completion: () -> Void) { completion() }
    func animateOut(to: (VisualNode,CGRect,Int), addToTransitionSurface: Int, completion: () -> Void) { completion() }
}
final class Pager {
    var isScrollEnabled = true
    var isUserInteractionEnabled = true
    let pagingEnabledPromise = Sink()
    weak var central: GalleryBase?
    func centralItemNode() -> GalleryBase? { central }
}
final class GalleryThumbnailContainerNode: VisualNode {}
final class GalleryControllerPresentationArguments {
    var animated = true
    func transitionArguments(_ id: MessageId, _ media: Media) -> GalleryTransitionArguments? { nil }
}
struct GalleryTransitionArguments { let transitionNode = 0; let addToTransitionSurface = 0 }
final class ActionInteraction { func updateCanReadHistory(_ value: Bool) {} }
struct GalleryEntry { let message = Message() }
struct Entry { let entry = GalleryEntry(); let mediaSubject = 0 }
func selectedMediaForMessage(message: Message, mediaSubject: Int) -> Media? { message.effectiveMedia.first }
enum Dismiss { case pip, `default`, simpleAnimation }
final class Controls { var view: UIView? = UIView() }
struct ValidLayout { var layout = ContainerViewLayout(); var navigationBarHeight: CGFloat = 44 }

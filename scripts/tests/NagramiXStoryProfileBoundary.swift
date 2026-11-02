import Foundation

// OS scheduling, Photos and Telegram engine boundaries. Signal/Disposable/Atomic,
// the production save function, settings, and presentation bodies are real.
public final class Queue {
    static var pending: [() -> Void] = []
    public static func mainQueue() -> Queue { Queue() }
    public static func concurrentDefaultQueue() -> Queue { Queue() }
    public func async(_ action: @escaping () -> Void) { Self.pending.append(action) }
    static func drain() { while !pending.isEmpty { pending.removeFirst()() } }
}
public final class Timer {
    static var timers: [Timer] = []
    let seconds: Double
    let completion: () -> Void
    var valid = false
    public init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) {
        self.seconds = timeout; self.completion = completion
    }
    public func start() { valid = true; Self.timers.append(self) }
    public func invalidate() { valid = false }
    static func fire(_ seconds: Double) {
        let selected = timers.filter { $0.valid && $0.seconds == seconds }
        for timer in selected { timer.valid = false; timer.completion() }
    }
}
public func deliverOn<T,E>(_ queue: Queue) -> (Signal<T,E>) -> Signal<T,E> { { $0 } }
func deliverOnMainQueue<T,E>(_ signal: Signal<T,E>) -> Signal<T,E> { signal }
struct NagramiXTabSettings {
    static let changedNotification = Notification.Name("NativeSettingsChanged")
    static var current = NagramiXTabSettings()
    var confirmStoryViewing = true
}
public protocol TelegramMediaResource {}
struct Resource: TelegramMediaResource {}
struct Representation { let resource: TelegramMediaResource }
public final class TelegramMediaImage { let representations: [Representation]; init(_ present: Bool = true) { representations = present ? [Representation(resource: Resource())] : [] } }
public final class TelegramMediaFile {
    let resource: TelegramMediaResource = Resource()
    var isVideo: Bool
    var mimeType: String
    init(_ video: Bool = true) { isVideo = video; mimeType = video ? "video/mp4" : "audio/ogg" }
}
func largestImageRepresentation(_ items: [Representation]) -> Representation? { items.last }
public struct AnyMediaReference {
    let media: Any
    func resourceReference(_ resource: TelegramMediaResource) -> Int { 0 }
}
public enum MediaResourceUserLocation { case peer(Int) }
enum ContentType { case story }
struct EngineMediaResource {
    init(_ resource: TelegramMediaResource) {}
    struct ResourceData { let path: String; let isComplete: Bool }
}
enum ResourceStatus { case Fetching(Bool, Float) }
enum FetchError: Error { case failed }
final class Resources {
    var path = ""
    var deferData = false
    var failFetch = false
    var fetches = 0
    var dataSubscriber: Subscriber<EngineMediaResource.ResourceData, NoError>?
    func fetch(reference: Int, userLocation: MediaResourceUserLocation, userContentType: ContentType, reportResultStatus: Bool) -> Signal<Bool, FetchError> {
        fetches += 1
        return failFetch ? .fail(.failed) : .never()
    }
    func status(resource: EngineMediaResource) -> Signal<ResourceStatus, NoError> { .single(.Fetching(false, 0.5)) }
    func data(resource: EngineMediaResource, pathExtension: String, waitUntilFetchStatus: Bool) -> Signal<EngineMediaResource.ResourceData, NoError> {
        return Signal { subscriber in
            self.dataSubscriber = subscriber
            if !self.deferData { subscriber.putNext(.init(path: self.path, isComplete: true)) }
            return ActionDisposable {}
        }
    }
    func emitData() { dataSubscriber?.putNext(.init(path: path, isComplete: true)) }
}
struct Account { let peerId = 1 }
func nagramiXKeepMediaResource(account: Account, resource: TelegramMediaResource) -> Disposable { ActionDisposable {} }
final class Engine { let resources = Resources() }
struct Bindings { let openSettings: () -> Void = {} }
struct PresentationStrings {
    var nagramiXAnonymousStoryPreviewTitle: String { "Incognito" }
    var nagramiXStoryConfirmationTitle: String { "Confirm" }
    var nagramiXAnonymousStoryPreviewText: String { "Local only" }
    func nagramiXStoryConfirmationText(owner: String) -> String { owner }
    var nagramiXAnonymousStoryPreviewAction: String { "View" }
    var nagramiXViewStoryAction: String { "View" }
}
struct PresentationData { let strings = PresentationStrings(); let nameDisplayOrder = 0 }
struct CurrentData { func with<T>(_ f: (PresentationData) -> T) -> T { f(PresentationData()) } }
final class SharedContext {
    let currentPresentationData = CurrentData()
    let applicationBindings = Bindings()
    func presentGlobalController(_ controller: Int, _ arguments: Int) {}
}
public final class AccountContext { let sharedContext = SharedContext(); let engine = Engine(); let account = Account() }
enum MediaAccess { case save }
enum Access { case mediaLibrary(MediaAccess) }
enum DeviceAccess {
    static var allowed = true
    static var deferred = false
    static var pending: ((Bool) -> Void)?
    static func authorizeAccess(to: Access, presentationData: PresentationData, present: (Int, Int) -> Void, openSettings: () -> Void, _ callback: @escaping (Bool) -> Void) {
        if deferred { pending = callback } else { callback(allowed) }
    }
}
final class EngineTempBox {
    struct File { let path: String }
    static let shared = EngineTempBox()
    var files: [String] = []
    func tempFile(fileName: String) -> File {
        let file = File(path: NSTemporaryDirectory() + UUID().uuidString + "-" + fileName)
        files.append(file.path); return file
    }
    func dispose(_ file: File) { try? FileManager.default.removeItem(atPath: file.path) }
}
enum AssetType { case photo, video }
final class PHAssetCreationRequest {
    static var resource: (AssetType, URL)?
    static func forAsset() -> PHAssetCreationRequest { PHAssetCreationRequest() }
    func addResource(with type: AssetType, fileURL: URL, options: Int?) { Self.resource = (type, fileURL) }
}
final class PHPhotoLibrary {
    static let instance = PHPhotoLibrary()
    static func shared() -> PHPhotoLibrary { instance }
    var pending: ((Bool, Error?) -> Void)?
    var calls = 0
    func performChanges(_ changes: () -> Void, completionHandler: @escaping (Bool, Error?) -> Void) {
        calls += 1; changes(); pending = completionHandler
    }
    func finish(_ success: Bool, error: Error? = nil) { let callback = pending; pending = nil; callback?(success, error) }
}

struct UIImage {}
struct EnginePeer {
    let id: Int
    func displayTitle(strings: PresentationStrings, displayOrder: Int) -> String { "Owner" }
}
struct PeerReference { init?(_ peer: EnginePeer) {} }
enum StoryMedia { case image(TelegramMediaImage), file(TelegramMediaFile), liveStream }
struct StoryItem { let id: Int; let media: StoryMedia }
struct StoryContentItem { let id: Int; let storyItem: StoryItem; var itemPeer: EnginePeer? = nil }
typealias EngineStoryId = Int
struct StoryContentContextState {
    struct FocusedSlice { let effectivePeer: EnginePeer; let item: StoryContentItem }
    var slice: FocusedSlice?
}
final class StoryContentContext {
    var stateValue: StoryContentContextState?
    var nagramiXAnonymousViewing = false
    var subscriber: Subscriber<StoryContentContextState, NoError>?
    var state: Signal<StoryContentContextState, NoError> {
        Signal { subscriber in self.subscriber = subscriber; return ActionDisposable {} }
    }
}
class ViewController {
    var pushed: StoryContainerScreen?
    var confirmation: NagramiXStoryConfirmationController?
    func present(_ controller: NagramiXStoryConfirmationController, in location: Location) { confirmation = controller }
    func push(_ controller: StoryContainerScreen) { pushed = controller }
}
enum Location { case window(Root); enum Root { case root } }
class NavigationController { var topViewController: Any?; func pushViewController(_ screen: StoryContainerScreen) {} }
final class NagramiXStoryConfirmationController {
    let confirmed: () -> Void
    let cancelled: () -> Void
    init(context: AccountContext, previewSignal: Signal<UIImage?, NoError>?, title: String, body: String, action: String, confirmed: @escaping () -> Void, cancelled: @escaping () -> Void) {
        self.confirmed = confirmed; self.cancelled = cancelled
    }
}
func nagramiXStoryPhotoPreview(context: AccountContext, peer: PeerReference, id: Int, image: TelegramMediaImage) -> Signal<UIImage?, NoError> { .single(nil) }
func nagramiXStoryVideoPreview(context: AccountContext, peer: PeerReference, id: Int, file: TelegramMediaFile) -> Signal<UIImage?, NoError> { .single(nil) }
final class StoryContainerScreen: ViewController {
    let context = AccountContext()
    let nagramiXContent: StoryContentContext
    var nagramiXIsPresentingConfirmation = false
    var nagramiXAcknowledgedAnonymousViewing = false
    var nagramiXApprovedStoryId: Int?
    var nagramiXPresentationDisposable: Disposable?
    init(_ content: StoryContentContext) { nagramiXContent = content; super.init() }
    deinit { nagramiXPresentationDisposable?.dispose() }
    // NATIVE_PRESENTATION_METHODS
}

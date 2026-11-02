import Foundation

// Native UI, TempBox and download interfaces. Production preparation/export
// code is compiled unchanged against these doubles; this is not UIKit testing.
final class MetaDisposable: Disposable {
    private var current: Disposable?; private var stopped = false
    func set(_ value: Disposable?) { let old = current; current = nil; old?.dispose(); if stopped { value?.dispose() } else { current = value } }
    func dispose() { stopped = true; let old = current; current = nil; old?.dispose() }
}
func deliverOnMainQueue<T, E>(_ source: Signal<T, E>) -> Signal<T, E> { source }
func afterDisposed<T, E>(_ action: @escaping () -> Void) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { out in let operation = source.start(next: out.putNext, error: out.putError, completed: out.putCompletion); return ActionDisposable { operation.dispose(); action() } } }
}
extension Signal {
    @discardableResult func startStrict(next: @escaping (T) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable { start(next: next, completed: completed) }
}
final class Queue {
    static var timers: [() -> Void] = []
    static func mainQueue() -> Queue { Queue() }
    static func concurrentDefaultQueue() -> Queue { Queue() }
    func async(_ body: @escaping () -> Void) { body() }
    func after(_ delay: Double, _ body: @escaping () -> Void) { Queue.timers.append(body) }
    static func flush() { let timers = self.timers; self.timers = []; timers.forEach { $0() } }
}
class ViewController { var dismissed = false; func dismiss() { dismissed = true } }
enum OverlayType { case loading(cancelled: () -> Void) }
final class OverlayStatusController: ViewController {
    let cancel: () -> Void
    init(theme: Int, type: OverlayType) { switch type { case let .loading(cancelled): cancel = cancelled } }
}
struct Strings { let nagramiXArchiveSaveFailed = "save failed"; let Common_OK = "OK" }
struct PresentationData { let theme = 1; let strings = Strings() }
final class PresentationValue { func with<T>(_ body: (PresentationData) -> T) -> T { body(PresentationData()) } }
final class SharedContext { let currentPresentationData = PresentationValue() }
final class Postbox { let mediaBox: MediaBox; init(_ mediaBox: MediaBox) { self.mediaBox = mediaBox } }
final class Account { let peerId = PeerId(value: 100); let postbox: Postbox; init(_ mediaBox: MediaBox) { postbox = Postbox(mediaBox) } }
final class AccountContext {
    let sharedContext = SharedContext(); let account: Account
    var presented: [ViewController] = []; var musicExports = 0
    var downloadObservers: [UUID: Subscriber<(FetchMediaDataState, Bool), NoError>] = [:]
    init(_ mediaBox: MediaBox = MediaBox()) { account = Account(mediaBox) }
    func emit(_ state: FetchMediaDataState) { Array(downloadObservers.values).forEach { $0.putNext((state, false)) } }
    func finish() { Array(downloadObservers.values).forEach { $0.putCompletion() } }
}
enum Surface { case window(Position); enum Position { case root } }
final class ChatControllerImpl {
    let context: AccountContext; let presentationData = PresentationData(); let nagramiXContentCopyDisposable = MetaDisposable()
    init(_ context: AccountContext) { self.context = context }
    func present(_ controller: ViewController, in surface: Surface) { context.presented.append(controller) }
    deinit { nagramiXContentCopyDisposable.dispose() }
}
final class TestAlert: ViewController {}
struct TextAlertAction {
    enum Kind { case defaultAction }
    init(type: Kind, title: String, action: @escaping () -> Void) {}
}
func textAlertController(context: AccountContext, title: String?, text: String, actions: [TextAlertAction]) -> ViewController { TestAlert() }
func nagramiXArchivedCopyAlert(context: AccountContext) -> ViewController { TestAlert() }
struct FileMediaReference { let media: TelegramMediaFile; var abstract: AnyMediaReference { .standalone(media: media) } }
struct DownloadData { let path: String; let isComplete: Bool }
enum FetchMediaDataState { case progress; case data(DownloadData) }
func fetchMediaData(context: AccountContext, userLocation: UserLocation, mediaReference: AnyMediaReference) -> Signal<(FetchMediaDataState, Bool), NoError> {
    Signal { out in let id = UUID(); context.downloadObservers[id] = out; return ActionDisposable { context.downloadObservers.removeValue(forKey: id) } }
}
func saveMediaToFiles(context: AccountContext, fileReference: FileMediaReference, present: @escaping (ViewController, Any?) -> Void) -> Disposable {
    context.musicExports += 1; return ActionDisposable {}
}
struct TempFile { let path: String }
final class EngineTempBox {
    static let shared = EngineTempBox()
    var active: Set<String> = []
    func tempFile(fileName: String) -> TempFile {
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try! FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let file = TempFile(path: root.appendingPathComponent(fileName).path); active.insert(file.path); return file
    }
    func dispose(_ file: TempFile) { active.remove(file.path); try? FileManager.default.removeItem(at: URL(fileURLWithPath: file.path).deletingLastPathComponent()) }
}
enum PickerMode { case export }
final class TestFilePicker: ViewController {
    let url: URL; let didDismiss: () -> Void; let complete: ([URL]) -> Void
    init(_ url: URL, _ dismissed: @escaping () -> Void, _ completion: @escaping ([URL]) -> Void) { self.url = url; didDismiss = dismissed; complete = completion }
}
func legacyICloudFilePicker(theme: Int, mode: PickerMode, url: URL, documentTypes: [String], forceDarkTheme: Bool, dismissed: @escaping () -> Void, completion: @escaping ([URL]) -> Void) -> ViewController { TestFilePicker(url, dismissed, completion) }

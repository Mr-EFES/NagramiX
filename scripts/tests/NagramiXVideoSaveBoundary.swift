import Foundation

// Boundary doubles for signals and media resources. The validator executes
// the real quality selector and export orchestration; Apple APIs are doubled.
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    private var action: (() -> Void)?
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { let action = self.action; self.action = nil; action?() }
}
final class DisposableSet: Disposable {
    private var items: [Disposable] = []; private var disposed = false
    func add(_ item: Disposable) { if disposed { item.dispose() } else { items.append(item) } }
    func dispose() { disposed = true; let items = self.items; self.items = []; items.forEach { $0.dispose() } }
}
final class Subscriber<T, E> {
    private var stopped = false
    private var cleanup: Disposable?
    private let next: (T) -> Void; private let error: (E) -> Void; private let completed: () -> Void
    init(_ next: @escaping (T) -> Void, _ error: @escaping (E) -> Void, _ completed: @escaping () -> Void) { self.next = next; self.error = error; self.completed = completed }
    func putNext(_ value: T) { if !stopped { next(value) } }
    func putError(_ value: E) { if !stopped { stopped = true; error(value); cleanup?.dispose() } }
    func putCompletion() { if !stopped { stopped = true; completed(); cleanup?.dispose() } }
    func attach(_ value: Disposable) { if stopped { value.dispose() } else { cleanup = value } }
    func dispose() { stopped = true; cleanup?.dispose(); cleanup = nil }
}
final class Signal<T, E> {
    let generate: (Subscriber<T, E>) -> Disposable
    init(_ generate: @escaping (Subscriber<T, E>) -> Disposable) { self.generate = generate }
    @discardableResult func start(next: @escaping (T) -> Void = { _ in }, error: @escaping (E) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable {
        let subscriber = Subscriber(next, error, completed); subscriber.attach(generate(subscriber)); return ActionDisposable { subscriber.dispose() }
    }
    static func single(_ value: T) -> Signal { Signal { $0.putNext(value); $0.putCompletion(); return ActionDisposable {} } }
}
enum NoError {}
final class Atomic<T> {
    private var value: T; private let lock = NSLock()
    init(value: T) { self.value = value }
    func with<U>(_ body: (T) -> U) -> U { lock.lock(); defer { lock.unlock() }; return body(value) }
    func swap(_ value: T) -> T { lock.lock(); defer { lock.unlock() }; let old = self.value; self.value = value; return old }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <A, B>(value: A, transform: (A) -> B) -> B { transform(value) }
func map<A, B, E>(_ transform: @escaping (A) -> B) -> (Signal<A, E>) -> Signal<B, E> {
    { source in Signal { out in source.start(next: { out.putNext(transform($0)) }, error: out.putError, completed: out.putCompletion) } }
}
func filter<T, E>(_ test: @escaping (T) -> Bool) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { out in source.start(next: { if test($0) { out.putNext($0) } }, error: out.putError, completed: out.putCompletion) } }
}
func take<T, E>(_ count: Int) -> (Signal<T, E>) -> Signal<T, E> {
    { source in Signal { out in var remaining = count; return source.start(next: { if remaining > 0 { remaining -= 1; out.putNext($0); if remaining == 0 { out.putCompletion() } } }, error: out.putError, completed: out.putCompletion) } }
}
func `catch`<T, E, F>(_ recovery: @escaping (E) -> Signal<T, F>) -> (Signal<T, E>) -> Signal<T, F> {
    { source in Signal { out in let set = DisposableSet(); set.add(source.start(next: out.putNext, error: { set.add(recovery($0).start(next: out.putNext, error: out.putError, completed: out.putCompletion)) }, completed: out.putCompletion)); return set } }
}
func combineLatest<T, E>(_ sources: [Signal<T, E>]) -> Signal<[T], E> {
    Signal { out in
        let set = DisposableSet(); var values: [T?] = Array(repeating: nil, count: sources.count); var failed = false
        for (index, source) in sources.enumerated() where !failed {
            set.add(source.start(next: { values[index] = $0; if values.allSatisfy({ $0 != nil }) { out.putNext(values.map { $0! }) } }, error: { failed = true; out.putError($0); set.dispose() }))
        }
        return set
    }
}

// AVFoundation/Photos/Postbox boundaries for executing the real save pipeline
// on Linux. These doubles do not test Apple's codecs, permissions UI or Photos.
struct PixelDimensions { let width: Int32; let height: Int32 }
enum TelegramMediaFileAttribute { case Video(Double, PixelDimensions, Int, Int?, Double?, String?); case other }
struct ResourceId: Hashable { let value: Int }
struct MediaResource { let id: ResourceId; let path: String }
struct TelegramMediaFile { let fileId: Int; var resource: MediaResource; var attributes: [TelegramMediaFileAttribute] = []; var alternativeRepresentations: [TelegramMediaFile] = [] }
struct FileMediaReference { let media: TelegramMediaFile; func withMedia(_ file: TelegramMediaFile) -> Self { Self(media: file) }; func resourceReference(_ resource: MediaResource) -> MediaResource { resource } }
struct MediaResourceUserLocation {}
struct MediaResourceUserContentType { init(file: TelegramMediaFile) {} }
enum MediaResourceStatus { case Fetching(Bool, Float); case Local; case Remote }
struct MediaData { let path: String; let complete: Bool; let offset: Int64; let size: Int64 }
final class MediaBox {
    var reads: [Int] = []; var keeps = 0
    func keepResource(id: ResourceId) -> Signal<Void, NoError> { Signal { _ in self.keeps += 1; return ActionDisposable { self.keeps -= 1 } } }
    func resourceStatus(_ resource: MediaResource) -> Signal<MediaResourceStatus, NoError> { .single(.Local) }
    func resourceData(_ resource: MediaResource) -> Signal<MediaData, NoError> { reads.append(resource.id.value); let size = ((try? FileManager.default.attributesOfItem(atPath: resource.path)[.size]) as? NSNumber)?.int64Value ?? 0; return .single(MediaData(path: resource.path, complete: true, offset: 0, size: size)) }
}
enum FetchError { case failed }
func fetchedMediaResource(mediaBox: MediaBox, userLocation: MediaResourceUserLocation, userContentType: MediaResourceUserContentType, reference: MediaResource, reportResultStatus: Bool) -> Signal<Int, FetchError> { .single(0) }
struct PresentationData {}
final class PresentationValue { func with<T>(_ f: (PresentationData) -> T) -> T { f(PresentationData()) } }
final class SharedContext { let currentPresentationData = PresentationValue(); let applicationBindings = Bindings(); func presentGlobalController(_ controller: Int, _ arguments: Int?) {} }
final class Bindings { func openSettings() {} }
final class Postbox { let mediaBox = MediaBox() }
final class Account { let postbox = Postbox() }
final class AccountContext { let account = Account(); let sharedContext = SharedContext() }
final class Queue {
    static func mainQueue() -> Queue { Queue() }
    func async(_ f: @escaping () -> Void) { DispatchQueue.global().async(execute: DispatchWorkItem(block: f)) }
}
func deliverOnMainQueue<T, E>(_ source: Signal<T, E>) -> Signal<T, E> { source }
final class MockTimer { init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) {}; func start() {}; func invalidate() {} }
enum Access { case mediaLibrary(MediaAccess); enum MediaAccess { case save } }
enum DeviceAccess {
    static var allowed = true
    static func authorizeAccess(to: Access, presentationData: PresentationData, present: @escaping (Int, Int?) -> Void, openSettings: @escaping () -> Void, _ completion: @escaping (Bool) -> Void) { completion(allowed) }
}
struct TempFile { let path: String }
final class EngineTempBox {
    static let shared = EngineTempBox(); private let lock = NSLock(); private var values: Set<String> = []
    var active: Set<String> { lock.lock(); defer { lock.unlock() }; return values }
    func tempFile(fileName: String) -> TempFile { let folder = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString); try! FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true); let file = TempFile(path: folder.appendingPathComponent(fileName).path); lock.lock(); values.insert(file.path); lock.unlock(); return file }
    func dispose(_ file: TempFile) { lock.lock(); values.remove(file.path); lock.unlock(); try? FileManager.default.removeItem(at: URL(fileURLWithPath: file.path).deletingLastPathComponent()) }
}
struct CGAffineTransform: Codable {
    var a: Double = 1; var b: Double = 0; var c: Double = 0; var d: Double = 1; var tx: Double = 0; var ty: Double = 0
    init() {}
    init(translationX: Double, y: Double) { tx = translationX; ty = y }
    init(scaleX: Double, y: Double) { a = scaleX; d = y }
    func concatenating(_ n: Self) -> Self { var t = Self(); t.a = n.a*a+n.c*b; t.b = n.b*a+n.d*b; t.c = n.a*c+n.c*d; t.d = n.b*c+n.d*d; t.tx = n.a*tx+n.c*ty+n.tx; t.ty = n.b*tx+n.d*ty+n.ty; return t }
}
extension CGRect {
    func applying(_ t: CGAffineTransform) -> CGRect { let points = [(minX,minY),(minX,maxY),(maxX,minY),(maxX,maxY)].map { x,y in (t.a*x+t.c*y+t.tx,t.b*x+t.d*y+t.ty) }; let xs = points.map(\.0), ys = points.map(\.1); return CGRect(x: xs.min()!, y: ys.min()!, width: xs.max()!-xs.min()!, height: ys.max()!-ys.min()!) }
}
struct CMTime {
    var seconds: Double; var isNumeric: Bool { seconds.isFinite }; static let zero = CMTime(seconds: 0)
    init(seconds: Double) { self.seconds = seconds }
    init(value: Int64, timescale: Int32) { seconds = Double(value)/Double(timescale) }
}
struct CMTimeRange { let start: CMTime; let duration: CMTime }
struct Movie: Codable {
    var width: Double = 1920; var height: Double = 1080; var duration = 3.0; var fps = 30.0; var audio = true; var rotation = false; var unreadable = false; var failPassthrough = false; var failExport = false
}
struct AVAsyncProperty<Root, Value> { let read: (Root) -> Value }
extension AVAsyncProperty where Root == AVAssetTrack, Value == CGSize { static var naturalSize: Self { Self { CGSize(width: $0.movie.width, height: $0.movie.height) } } }
extension AVAsyncProperty where Root == AVAssetTrack, Value == CGAffineTransform { static var preferredTransform: Self { Self { track in var result = CGAffineTransform(); if track.movie.rotation { result.a = 0; result.b = 1; result.c = -1; result.d = 0 }; return result } } }
extension AVAsyncProperty where Root == AVAssetTrack, Value == CMTime { static var minFrameDuration: Self { Self { CMTime(seconds: 1/$0.movie.fps) } } }
extension AVAsyncProperty where Root == AVAsset, Value == CMTime { static var duration: Self { Self { CMTime(seconds: $0.movie.duration) } } }
enum MediaType { case video; case audio }
class AVAsset {
    let movie: Movie
    init(movie: Movie) { self.movie = movie }
    func loadTracks(withMediaType type: MediaType) async throws -> [AVAssetTrack] { if movie.unreadable { throw NagramiXGalleryVideoSaveError.conversion }; switch type { case .video: return [AVAssetTrack(movie)]; case .audio: return movie.audio ? [AVAssetTrack(movie)] : [] } }
    func load<T>(_ property: AVAsyncProperty<AVAsset,T>) async throws -> T { property.read(self) }
}
final class AVURLAsset: AVAsset { init(url: URL) { let movie = (try? JSONDecoder().decode(Movie.self, from: Data(contentsOf: url))) ?? Movie(unreadable: true); super.init(movie: movie) } }
final class AVAssetTrack { let movie: Movie; init(_ movie: Movie) { self.movie = movie }; func load<T>(_ property: AVAsyncProperty<AVAssetTrack,T>) async throws -> T { property.read(self) } }
final class AVMutableVideoCompositionLayerInstruction { let track: AVAssetTrack; var transform = CGAffineTransform(); init(assetTrack: AVAssetTrack) { track = assetTrack }; func setTransform(_ value: CGAffineTransform, at: CMTime) { transform = value } }
final class AVMutableVideoCompositionInstruction { var timeRange = CMTimeRange(start: .zero, duration: .zero); var layerInstructions: [AVMutableVideoCompositionLayerInstruction] = [] }
final class AVMutableVideoComposition { var renderSize = CGSize.zero; var frameDuration = CMTime.zero; var instructions: [AVMutableVideoCompositionInstruction] = [] }
let AVAssetExportPresetPassthrough = "passthrough", AVAssetExportPresetHighestQuality = "h264-highest"
enum FileType { case mp4 }
enum ExportStatus { case waiting; case completed; case failed; case cancelled }
final class AVAssetExportSession {
    let asset: AVAsset; let preset: String; var supportedFileTypes: [FileType] = [.mp4]; var outputURL: URL?; var outputFileType: FileType?; var shouldOptimizeForNetworkUse = false; var videoComposition: AVMutableVideoComposition?; var progress: Float = 0; var status = ExportStatus.waiting
    init?(asset: AVAsset, presetName: String) { self.asset = asset; preset = presetName }
    func exportAsynchronously(completion: @escaping () -> Void) {
        if asset.movie.failExport || (preset == AVAssetExportPresetPassthrough && asset.movie.failPassthrough) { status = .failed; completion(); return }
        var result = asset.movie
        if let composition = videoComposition {
            if let layer = composition.instructions.first?.layerInstructions.first {
                let rect = CGRect(x: 0, y: 0, width: asset.movie.width, height: asset.movie.height).applying(layer.transform)
                TestExports.transformsFit = TestExports.transformsFit && abs(rect.minX) < 0.01 && abs(rect.minY) < 0.01 && abs(rect.width-composition.renderSize.width) < 0.01 && abs(rect.height-composition.renderSize.height) < 0.01
            }
            result.width = composition.renderSize.width; result.height = composition.renderSize.height; result.rotation = false
        }
        do { try JSONEncoder().encode(result).write(to: outputURL!); status = .completed; progress = 1 } catch { status = .failed }
        completion()
    }
    func cancelExport() { status = .cancelled }
}
enum TestExports { static var transformsFit = true }
enum PhotoResourceType { case video }
final class PHAssetCreationRequest {
    static func forAsset() -> PHAssetCreationRequest { PHAssetCreationRequest() }
    func addResource(with: PhotoResourceType, fileURL: URL, options: Int?) { PHPhotoLibrary.shared().record(fileURL) }
}
final class PHPhotoLibrary {
    static let library = PHPhotoLibrary(); static func shared() -> PHPhotoLibrary { library }
    private let lock = NSLock(); private var urls: [URL] = []; private var results: [Movie] = []; private var pending: ((Bool, Error?) -> Void)?
    var success = true; var hold = false
    var imported: [Movie] { lock.lock(); defer { lock.unlock() }; return results }
    var hasPending: Bool { lock.lock(); defer { lock.unlock() }; return pending != nil }
    var latestURL: URL? { lock.lock(); defer { lock.unlock() }; return urls.last }
    func record(_ url: URL) { lock.lock(); urls.append(url); if let data = try? Data(contentsOf: url), let movie = try? JSONDecoder().decode(Movie.self, from: data) { results.append(movie) }; lock.unlock() }
    func performChanges(_ changes: () -> Void, completionHandler: @escaping (Bool, Error?) -> Void) { changes(); lock.lock(); let deferred = hold; if deferred { pending = completionHandler }; lock.unlock(); if !deferred { completionHandler(success, nil) } }
    func release() { lock.lock(); let callback = pending; pending = nil; lock.unlock(); callback?(success,nil) }
    func reset() { lock.lock(); urls = []; results = []; pending = nil; success = true; hold = false; lock.unlock() }
}

extension Atomic {
    func modify(_ f: (T) -> T) -> T { lock.lock(); defer { lock.unlock() }; value = f(value); return value }
}
extension Signal {
    static func fail(_ error: E) -> Signal<T,E> { Signal { $0.putError(error); return ActionDisposable {} } }
}

// Run on macOS with the production resource-loader appended to this file.
// Real AVFoundation reads a generated movie through delayed, in-memory ranges;
// Telegram transport is the only substituted boundary. No credentials/network.
import Foundation
import AVFoundation
import CoreVideo

protocol Disposable: AnyObject { func dispose() }
final class ProbeDisposable: Disposable {
    private let lock = NSLock()
    private var cancelled = false
    func dispose() { self.lock.lock(); self.cancelled = true; self.lock.unlock() }
    var active: Bool { self.lock.lock(); defer { self.lock.unlock() }; return !self.cancelled }
}
final class DisposableSet: Disposable {
    private var values: [Disposable] = []
    private var disposed = false
    func add(_ value: Disposable) { if self.disposed { value.dispose() } else { self.values.append(value) } }
    func dispose() { self.disposed = true; self.values.forEach { $0.dispose() }; self.values.removeAll() }
}
enum ProbeError: Error { case failure }
final class ProbeSignal<Value> {
    let generate: (@escaping (Value) -> Void) -> Disposable
    init(_ generate: @escaping (@escaping (Value) -> Void) -> Disposable) { self.generate = generate }
    func start(next: ((Value) -> Void)? = nil, error: ((ProbeError) -> Void)? = nil) -> Disposable {
        return self.generate(next ?? { _ in })
    }
}
precedencegroup PipePrecedence {
    associativity: left
    higherThan: AssignmentPrecedence
}
infix operator |> : PipePrecedence
func |> <A, B>(value: A, transform: (A) -> B) -> B { return transform(value) }
func filter<T>(_ predicate: @escaping (T) -> Bool) -> (ProbeSignal<T>) -> ProbeSignal<T> {
    return { signal in ProbeSignal { next in signal.start(next: { if predicate($0) { next($0) } }) } }
}
func take<T>(_ count: Int) -> (ProbeSignal<T>) -> ProbeSignal<T> {
    return { signal in ProbeSignal { next in
        var remaining = count
        return signal.start(next: { value in if remaining > 0 { remaining -= 1; next(value) } })
    } }
}
struct ProbeResource {}
struct MediaResourceReference { let resource = ProbeResource() }
enum MediaResourceUserLocation { case other }
enum MediaResourceUserContentType { case video }
enum ProbePriority { case elevated }
enum ProbeMode { case complete }
final class MediaBox {
    let bytes: Data
    let delay: Double
    private let lock = NSLock()
    private var ranges: [Range<Int64>] = []
    init(bytes: Data, delay: Double) { self.bytes = bytes; self.delay = delay }
    var readRanges: [Range<Int64>] { self.lock.lock(); defer { self.lock.unlock() }; return self.ranges }
    func resourceData(_ resource: ProbeResource, size: Int64, in range: Range<Int64>, mode: ProbeMode) -> ProbeSignal<(Data, Bool)> {
        self.lock.lock(); self.ranges.append(range); self.lock.unlock()
        return ProbeSignal { next in
            let operation = ProbeDisposable()
            DispatchQueue.global().asyncAfter(deadline: .now() + self.delay) {
                if operation.active { next((self.bytes.subdata(in: Int(range.lowerBound)..<Int(range.upperBound)), true)) }
            }
            return operation
        }
    }
}
func fetchedMediaResource(mediaBox: MediaBox, userLocation: MediaResourceUserLocation, userContentType: MediaResourceUserContentType, reference: MediaResourceReference, range: (Range<Int64>, ProbePriority), reportResultStatus: Bool, continueInBackground: Bool) -> ProbeSignal<Int> {
    return ProbeSignal { _ in ProbeDisposable() }
}
func require(_ value: Bool, _ text: String) { if !value { fatalError(text) } }

func makeMovie(_ url: URL) throws -> Data {
    let writer = try AVAssetWriter(outputURL: url, fileType: .mov)
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: 64, AVVideoHeightKey: 64])
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB, kCVPixelBufferWidthKey as String: 64, kCVPixelBufferHeightKey as String: 64])
    writer.add(input)
    require(writer.startWriting(), "writer start")
    writer.startSession(atSourceTime: .zero)
    var buffer: CVPixelBuffer?
    require(CVPixelBufferCreate(kCFAllocatorDefault, 64, 64, kCVPixelFormatType_32ARGB, nil, &buffer) == kCVReturnSuccess, "pixel buffer")
    guard let pixel = buffer else { fatalError("pixel allocation") }
    CVPixelBufferLockBaseAddress(pixel, [])
    memset(CVPixelBufferGetBaseAddress(pixel), 0, CVPixelBufferGetDataSize(pixel))
    CVPixelBufferUnlockBaseAddress(pixel, [])
    for frame in 0..<5 {
        let deadline = Date().addingTimeInterval(5)
        while !input.isReadyForMoreMediaData && Date() < deadline { Thread.sleep(forTimeInterval: 0.01) }
        require(adaptor.append(pixel, withPresentationTime: CMTime(value: Int64(frame), timescale: 5)), "append frame")
    }
    input.markAsFinished()
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    require(finished.wait(timeout: .now() + 10) == .success && writer.status == .completed, "finish movie")
    return try Data(contentsOf: url)
}

func probeResourceLoader() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: folder) }
    let bytes = try makeMovie(folder.appendingPathComponent("sample.mov"))
    // Both immediate cache reads and delayed delivery must prepare a playable
    // asset through the real resource-loader delegate and metadata probe.
    for delay in [0.0, 0.02] {
        let box = MediaBox(bytes: bytes, delay: delay)
        let loader = NagramiXPiPResourceLoader(mediaBox: box, reference: MediaResourceReference(), location: .other, contentType: .video, length: Int64(bytes.count), mimeType: "video/quicktime")
        let loaded = DispatchSemaphore(value: 0)
        loader.asset.loadValuesAsynchronously(forKeys: ["tracks", "playable"]) { loaded.signal() }
        require(loaded.wait(timeout: .now() + 10) == .success, "AVAsset range delivery timed out: " + loader.diagnostic)
        var error: NSError?
        require(loader.asset.statusOfValue(forKey: "tracks", error: &error) == .loaded, "tracks failed: \(String(describing: error)) / \(loader.diagnostic)")
        require(loader.asset.isPlayable && !loader.asset.tracks(withMediaType: .video).isEmpty, "movie is not playable")
        require(!box.readRanges.isEmpty && box.readRanges.allSatisfy { $0.count <= 64 * 1024 }, "range bounds")
        loader.cancelAll()
        loader.asset.cancelLoading()
    }
    print("AVFoundation PiP resource probe: OK")
}
try probeResourceLoader()

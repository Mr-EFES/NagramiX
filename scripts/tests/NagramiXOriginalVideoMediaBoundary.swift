// Explicit OS/data edges. FileHandle writes, deferred move/pin ownership,
// SignalKit, the complete producer and native classification are production.
public final class UIImage {
    public let size = CGSize(width: 96, height: 64)
    public func jpegData(compressionQuality: CGFloat) -> Data? { Data([0xff, 0xd8, 0xff, 0xd9]) }
}
func TGScaleImageToPixelSize(_ image: UIImage, _ size: CGSize) -> UIImage? { image }
extension CGSize {
    func aspectFitted(_ max: CGSize) -> CGSize { let f = min(max.width / width, max.height / height); return CGSize(width: width * f, height: height * f) }
    func aspectFittedOrSmaller(_ max: CGSize) -> CGSize { width <= max.width && height <= max.height ? self : aspectFitted(max) }
}
public struct PixelDimensions {
    let width: Int32; let height: Int32
    init(width: Int32, height: Int32) { self.width = width; self.height = height }
    init(_ size: CGSize) { self.init(width: Int32(size.width), height: Int32(size.height)) }
}
public final class PHAssetResource {
    enum Kind { case video, fullSizeVideo }
    let type: Kind; let originalFilename: String; let uniformTypeIdentifier: String; let bytes: Data
    init(_ name: String, mime: String, bytes: Data, full: Bool = false) {
        self.type = full ? .fullSizeVideo : .video; self.originalFilename = name; self.uniformTypeIdentifier = mime; self.bytes = bytes
    }
    static func assetResources(for asset: PHAsset) -> [PHAssetResource] { asset.resources }
}
public final class PHAsset {
    enum Kind { case video, image }
    var mediaType = Kind.video
    var pixelWidth = 96; var pixelHeight = 64; var duration = 0.5
    var resources: [PHAssetResource]
    init(_ resources: [PHAssetResource]) { self.resources = resources }
}
final class PHAssetResourceRequestOptions { var isNetworkAccessAllowed = false }
final class PHAssetResourceManager {
    static let shared = PHAssetResourceManager()
    static func `default`() -> PHAssetResourceManager { shared }
    struct Request {
        let resource: PHAssetResource; let data: (Data) -> Void; let completion: (Error?) -> Void
    }
    var pending: [Int: Request] = [:]; var nextId = 0; var cancelled = Set<Int>(); var requests = 0
    func requestData(for resource: PHAssetResource, options: PHAssetResourceRequestOptions, dataReceivedHandler: @escaping (Data) -> Void, completionHandler: @escaping (Error?) -> Void) -> Int {
        precondition(options.isNetworkAccessAllowed)
        nextId += 1; requests += 1; pending[nextId] = Request(resource: resource, data: dataReceivedHandler, completion: completionHandler); return nextId
    }
    func cancelDataRequest(_ id: Int) { cancelled.insert(id); pending.removeValue(forKey: id) }
    func finish(_ error: Error? = nil) {
        let items = pending; pending.removeAll()
        for (id, request) in items where !cancelled.contains(id) {
            let bytes = request.resource.bytes
            for offset in stride(from: 0, to: bytes.count, by: 137) { request.data(bytes.subdata(in: offset..<min(offset + 137, bytes.count))) }
            request.completion(error)
        }
    }
}
struct UTType {
    let preferredMIMEType: String?
    init?(_ identifier: String) { self.preferredMIMEType = identifier == "unknown" ? nil : identifier }
}
func guessMimeTypeByFileExtension(_ ext: String) -> String { ext == "m4v" ? "video/m4v" : "application/binary" }
func engineFileSize(_ path: String) -> Int64? { ((try? FileManager.default.attributesOfItem(atPath: path))?[.size] as? NSNumber)?.int64Value }
final class EngineTempBox {
    struct File { let path: String }
    static let shared = EngineTempBox()
    func tempFile(fileName: String) -> File { File(path: NSTemporaryDirectory() + "original-media-fixture-" + UUID().uuidString) }
    func dispose(_ file: File) { try? FileManager.default.removeItem(atPath: file.path) }
}
protocol Resource { var id: String { get } }
struct LocalFileMediaResource: Resource {
    let fileId: Int64; let size: Int64?
    init(fileId: Int64, size: Int64? = nil) { self.fileId = fileId; self.size = size }
    var id: String { String(fileId) }
}
struct EngineMediaResource { struct Id { let value: String; init(_ id: String) { value = id } } }
struct EngineMedia { struct Id { let namespace: Int32; let id: Int64 } }
enum Namespaces { enum Media { static let LocalFile: Int32 = 1 } }
public enum TelegramMediaFileAttribute {
    case FileName(fileName: String)
    case Video(duration: Double, size: PixelDimensions, flags: TelegramMediaVideoFlags, preloadSize: Int32?, coverTime: Double?, videoCodec: String?)
    case hintFileIsLarge
}
struct TelegramMediaImageRepresentation {
    let dimensions: PixelDimensions; let resource: LocalFileMediaResource; let progressiveSizes: [Int32]; let immediateThumbnailData: Data?; let hasVideo: Bool; let isPersonal: Bool
}
struct TelegramMediaImage: Equatable {
    let imageId: EngineMedia.Id; let representations: [TelegramMediaImageRepresentation]; let immediateThumbnailData: Data?; let reference: Int?; let partialReference: Int?; let flags: [Int]
    static func == (a: Self, b: Self) -> Bool { a.imageId.id == b.imageId.id }
}
public struct TelegramMediaFile {
    let fileId: EngineMedia.Id; let partialReference: Int?; let resource: LocalFileMediaResource
    let previewRepresentations: [TelegramMediaImageRepresentation]; let videoThumbnails: [Int]; let videoCover: TelegramMediaImage?; let immediateThumbnailData: Data?
    let mimeType: String; let size: Int64?; let attributes: [TelegramMediaFileAttribute]; let alternativeRepresentations: [Int]
    // NATIVE_FILE_CLASSIFICATION
}
final class Resources {
    let folder = NSTemporaryDirectory() + "original-media-box-" + UUID().uuidString
    var moves: [(String, String)] = []; var paths: [String: String] = [:]
    init() { try! FileManager.default.createDirectory(atPath: folder, withIntermediateDirectories: true) }
    deinit { try? FileManager.default.removeItem(atPath: folder) }
    func moveResourceData(id: EngineMediaResource.Id, fromTempPath: String) { moves.append((id.value, fromTempPath)) }
    func storeResourceData(id: EngineMediaResource.Id, data: Data) {
        let path = folder + "/" + id.value; try! data.write(to: URL(fileURLWithPath: path)); paths[id.value] = path
    }
    func flushMoves() {
        for (id, path) in moves { let target = folder + "/" + id; try! FileManager.default.moveItem(atPath: path, toPath: target); paths[id] = target }
        moves.removeAll()
    }
}
public final class Account { let resources = Resources() }
struct TelegramEngine {
    let resources: Resources
    init(account: Account) { self.resources = account.resources }
}
final class ExportResult {
    private let lock = NSLock(); private var result: TelegramMediaFile?; private var failed = false
    let completed = DispatchSemaphore(value: 0)
    func next(_ file: TelegramMediaFile) { lock.lock(); result = file; lock.unlock() }
    func error() { lock.lock(); failed = true; lock.unlock(); completed.signal() }
    func done() { completed.signal() }
    var value: TelegramMediaFile? { lock.lock(); defer { lock.unlock() }; return result }
    var hasError: Bool { lock.lock(); defer { lock.unlock() }; return failed }
}

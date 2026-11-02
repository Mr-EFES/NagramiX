import Foundation

// Boundary doubles for Postbox media, the native resource fetcher and signals.
// The validator compiles the real copy builder, file staging, fetch and policies.
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
enum Namespaces { enum Peer { static let CloudUser: Int32 = 0; static let SecretChat: Int32 = 3 }; enum Message { static let Cloud: Int32 = 0 }; enum Media { static let LocalImage: Int32 = 1; static let LocalFile: Int32 = 2 } }
struct PeerId: Hashable { var namespace: Int32 = 0; var isVerificationCodes = false; var value = 1 }
struct MessageId: Hashable { var peerId = PeerId(); var value = 1; var namespace: Int32 = Namespaces.Message.Cloud }
struct MessageFlags: OptionSet { let rawValue: Int; static let Failed = Self(rawValue: 1); static let sending = Self(rawValue: 2); static let Incoming = Self(rawValue: 4); var isSending: Bool { contains(.sending) } }
struct TestUser { var id: PeerId; var botInfo: Int? = nil }
enum EnginePeer { case user(TestUser); case group; case channel; case secretChat }
let viewOnceTimeout: Int32 = .max
protocol Media {}
struct MediaId: Hashable { let namespace: Int32; let id: Int64 }
struct MediaResourceId { let stringRepresentation: String }
protocol MediaResource { var id: MediaResourceId { get } }
typealias TelegramMediaResource = MediaResource
struct CloudResource: MediaResource { let id: MediaResourceId; init(_ name: String) { id = MediaResourceId(stringRepresentation: name) } }
final class LocalFileReferenceMediaResource: MediaResource {
    let localFilePath: String; let randomId: Int64; let isUniquelyReferencedTemporaryFile: Bool; let size: Int64?
    var id: MediaResourceId { MediaResourceId(stringRepresentation: String(randomId)) }
    init(localFilePath: String, randomId: Int64, isUniquelyReferencedTemporaryFile: Bool, size: Int64?) { self.localFilePath = localFilePath; self.randomId = randomId; self.isUniquelyReferencedTemporaryFile = isUniquelyReferencedTemporaryFile; self.size = size }
}
struct Dimensions { let width: Int32; let height: Int32 }
struct TelegramMediaImageRepresentation {
    let dimensions: Dimensions; let resource: TelegramMediaResource; var progressiveSizes: [Int32] = []; var immediateThumbnailData: Data? = nil; var hasVideo = false; var isPersonal = false; var typeHint: Int? = nil
}
final class TelegramMediaImage: Media {
    let imageId: MediaId; let representations: [TelegramMediaImageRepresentation]; let videoRepresentations: [Int]; let immediateThumbnailData: Data?; let emojiMarkup: Int?; let reference: Int?; let partialReference: Int?; let flags: Int; let video: TelegramMediaFile?
    init(imageId: MediaId = MediaId(namespace: 0, id: 4), representations: [TelegramMediaImageRepresentation], videoRepresentations: [Int] = [], immediateThumbnailData: Data? = nil, emojiMarkup: Int? = nil, reference: Int? = 1, partialReference: Int? = 1, flags: Int = 0, video: TelegramMediaFile? = nil) { self.imageId = imageId; self.representations = representations; self.videoRepresentations = videoRepresentations; self.immediateThumbnailData = immediateThumbnailData; self.emojiMarkup = emojiMarkup; self.reference = reference; self.partialReference = partialReference; self.flags = flags; self.video = video }
}
struct TelegramMediaFile: Media {
    var isMusic: Bool { attributes.contains("music") }
    var isVoice: Bool { attributes.contains("voice") }
    var isInstantVideo: Bool { attributes.contains("round") }
    struct VideoThumbnail { let dimensions: Dimensions; let resource: TelegramMediaResource }
    var fileId = MediaId(namespace: 0, id: 3); var partialReference: Int? = 1; var resource: TelegramMediaResource; var previewRepresentations: [TelegramMediaImageRepresentation] = []; var videoThumbnails: [VideoThumbnail] = []; var videoCover: TelegramMediaImage? = nil; var immediateThumbnailData: Data? = nil; var mimeType = "video/mp4"; var size: Int64? = nil; var attributes: [String] = []; var fileName: String? = nil; var alternativeRepresentations: [Int] = []
}
struct TelegramMediaWebpage: Media {}
struct TelegramMediaContact: Media {}
struct TelegramMediaMap: Media {}
struct TelegramMediaPaidContent: Media {}
struct TelegramMediaExpiredContent: Media {}
struct TelegramMediaAction: Media {}
struct UnsupportedMedia: Media {}
protocol MessageAttribute {}
struct Entity { let value: String; var associatedMediaIds: [MediaId] = [] }
struct TextEntitiesMessageAttribute: MessageAttribute { let entities: [Entity]; var associatedMediaIds: [MediaId] { entities.flatMap(\.associatedMediaIds) } }
struct MediaSpoilerMessageAttribute: MessageAttribute {}
struct NagramiXArchivedMessageAttribute: MessageAttribute {}
struct UnrelatedAttribute: MessageAttribute {}
struct AutoremoveTimeoutMessageAttribute: MessageAttribute { let timeout: Int32; let countdownBeginTime: Int32? }
struct AutoclearTimeoutMessageAttribute: MessageAttribute { let timeout: Int32; let countdownBeginTime: Int32? }
struct Message {
    var id = MessageId(); var text = "Текст 😀"; var media: [Media] = []; var protected = false; var containsSecretMedia = false; var minAutoremoveOrClearTimeout: Int32? = nil; var flags: MessageFlags = []; var attributes: [MessageAttribute] = []; var associatedMedia: [MediaId: Media] = [:]; var groupingKey: Int64? = nil; var author: TestUser? = nil; var forwardInfo: Int? = nil
    func isCopyProtected() -> Bool { protected }
}
typealias EngineRawMessage = Message
typealias EngineRawMedia = Media
enum EngineMessage { typealias Attribute = MessageAttribute }
enum EngineMedia { typealias Id = MediaId }
struct MessageReference { let id: MessageId; init(_ message: Message) { id = message.id } }
enum AnyMediaReference {
    case standalone(media: Media)
    case message(message: MessageReference, media: Media)
    func resourceReference(_ resource: MediaResource) -> MediaResourceReference { switch self { case let .message(message, _): return MediaResourceReference(resource: resource, source: message.id); case .standalone: return MediaResourceReference(resource: resource, source: nil) } }
}
struct MediaResourceReference { let resource: MediaResource; let source: MessageId? }
struct EnqueueMessage {
    let text: String; let attributes: [MessageAttribute]; let inlineStickers: [MediaId: Media]; let mediaReference: AnyMediaReference?; let threadId: Int64?; let replyToMessageId: Int?; let replyToStoryId: Int?; let localGroupingKey: Int64?; let correlationId: Int64?; let bubbleUpEmojiOrStickersets: [Int]
    static func message(text: String, attributes: [MessageAttribute], inlineStickers: [MediaId: Media], mediaReference: AnyMediaReference?, threadId: Int64?, replyToMessageId: Int?, replyToStoryId: Int?, localGroupingKey: Int64?, correlationId: Int64?, bubbleUpEmojiOrStickersets: [Int]) -> Self { Self(text: text, attributes: attributes, inlineStickers: inlineStickers, mediaReference: mediaReference, threadId: threadId, replyToMessageId: replyToMessageId, replyToStoryId: replyToStoryId, localGroupingKey: localGroupingKey, correlationId: correlationId, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets) }
}
struct ResourceData { let complete: Bool; var offset: Int64 = 0; var size: Int64 = 4 }
enum FetchError { case failed }
enum UserLocation { case peer(PeerId); case other }
enum UserContentType { case other }
final class MediaBox {
    var paths: [String: String] = [:]; var complete: Set<String> = []; var fetched: [String] = []; var references: [MediaResourceReference] = []; var activeFetches = 0; var activeKeeps = 0
    var dataObservers: [String: [UUID: (ResourceData) -> Void]] = [:]; var errors: [String: (FetchError) -> Void] = [:]
    func completedResourcePath(_ resource: MediaResource) -> String? { paths[resource.id.stringRepresentation] }
    func keepResource(id: MediaResourceId) -> Signal<Void, NoError> { Signal { _ in self.activeKeeps += 1; return ActionDisposable { self.activeKeeps -= 1 } } }
    func resourceData(_ resource: MediaResource) -> Signal<ResourceData, NoError> {
        let name = resource.id.stringRepresentation
        return Signal { out in let id = UUID(); self.dataObservers[name, default: [:]][id] = out.putNext; if self.complete.contains(name) { out.putNext(ResourceData(complete: true)) }; return ActionDisposable { self.dataObservers[name]?.removeValue(forKey: id) } }
    }
    func emit(_ name: String, _ value: ResourceData) { let callbacks = Array(dataObservers[name, default: [:]].values); callbacks.forEach { $0(value) } }
}
func fetchedMediaResource(mediaBox: MediaBox, userLocation: UserLocation, userContentType: UserContentType, reference: MediaResourceReference, reportResultStatus: Bool) -> Signal<Int, FetchError> {
    Signal { out in let name = reference.resource.id.stringRepresentation; mediaBox.fetched.append(name); mediaBox.references.append(reference); mediaBox.activeFetches += 1; mediaBox.errors[name] = out.putError; return ActionDisposable { mediaBox.activeFetches -= 1; mediaBox.errors.removeValue(forKey: name) } }
}
struct NagramiXTabSettings { var showForwardWithoutAuthor = true; var showBroadcastMessages = true; static var current = Self() }

@main struct ContentCopyTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(), label); checks += 1 }
        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString); try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var staged: [String] = []
        defer { try? FileManager.default.removeItem(at: root); staged.forEach { try? FileManager.default.removeItem(atPath: $0) } }
        let payload = Data([0, 1, 2, 255]); let source = root.appendingPathComponent("source.mp4"); try payload.write(to: source)
        let box = MediaBox(); box.paths["full"] = source.path
        var text = Message(); text.protected = true
        let copiedText = nagramiXCopyMessagesAsNew([text])!
        check(copiedText.count == 1 && copiedText[0].text == text.text && copiedText[0].mediaReference == nil, "protected text becomes a new message")
        check(copiedText[0].replyToMessageId == nil && copiedText[0].threadId == nil && copiedText[0].correlationId == nil, "source metadata is not copied")
        var failures: [Message] = []
        var sample = text; sample.id.peerId.namespace = Namespaces.Peer.SecretChat; failures.append(sample)
        sample = text; sample.id.peerId.isVerificationCodes = true; failures.append(sample)
        sample = text; sample.containsSecretMedia = true; failures.append(sample)
        sample = text; sample.minAutoremoveOrClearTimeout = viewOnceTimeout; failures.append(sample)
        let forbiddenMedia: [Media] = [TelegramMediaPaidContent(), TelegramMediaExpiredContent(), TelegramMediaAction(), UnsupportedMedia()]
        for media in forbiddenMedia { sample = text; sample.media = [media]; failures.append(sample) }
        for flag in [MessageFlags.sending, MessageFlags.Failed] { sample = text; sample.flags = flag; failures.append(sample) }
        for forbidden in failures { check(nagramiXCopyMessagesAsNew([text, forbidden], mediaBox: box) == nil, "reject whole mixed batch; never export a permitted subset") }
        check(nagramiXCopyMessagesAsNew([]) == nil, "empty batch rejected")
        let emojiId = MediaId(namespace: 0, id: 99)
        text.attributes = [TextEntitiesMessageAttribute(entities: [Entity(value: "bold+emoji", associatedMediaIds: [emojiId])]), MediaSpoilerMessageAttribute(), UnrelatedAttribute()]
        text.associatedMedia[emojiId] = TelegramMediaContact(); text.groupingKey = 123
        let grouped = nagramiXCopyMessagesAsNew([text, text])!
        check(grouped[0].attributes.count == 2 && grouped[0].inlineStickers.count == 1, "entities, custom emoji and spoiler preserved; unrelated attributes stripped")
        check(grouped[0].localGroupingKey != nil && grouped[0].localGroupingKey == grouped[1].localGroupingKey, "album grouping stays together")
        var fileMessage = text; fileMessage.media = [TelegramMediaFile(resource: CloudResource("full"), attributes: ["round", "duration=3", "size=1080"])]
        let copies = nagramiXCopyMessagesAsNew([fileMessage], mediaBox: box)!
        guard case let .standalone(media)? = copies[0].mediaReference, let file = media as? TelegramMediaFile, let resource = file.resource as? LocalFileReferenceMediaResource else { fatalError("must stage independent local media") }
        staged.append(resource.localFilePath)
        check(file.fileId.namespace == Namespaces.Media.LocalFile && file.partialReference == nil && file.attributes == ["round", "duration=3", "size=1080"], "new local file identity with native media attributes")
        let retainedBytes = try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
        check(retainedBytes == payload, "full bytes are unchanged")
        let captionless = nagramiXCopyMessagesAsNew([fileMessage], mediaBox: box, hideCaptions: true)!
        if case let .standalone(media)? = captionless[0].mediaReference, let f = media as? TelegramMediaFile, let r = f.resource as? LocalFileReferenceMediaResource { staged.append(r.localFilePath) }
        check(captionless[0].text.isEmpty && captionless[0].inlineStickers.isEmpty && captionless[0].attributes.count == 1, "hide captions retains spoiler while removing caption entities")
        var ordinary = fileMessage; ordinary.protected = false
        let normal = nagramiXCopyMessagesAsNew([ordinary], mediaBox: box)!
        if case .message? = normal[0].mediaReference { check(true, "ordinary cloud media keeps native reuse") } else { fatalError("ordinary semantics changed") }
        let forced = nagramiXCopyMessagesAsNew([ordinary], mediaBox: box, forceLocalMedia: true)!
        if case let .standalone(media)? = forced[0].mediaReference, let f = media as? TelegramMediaFile, let r = f.resource as? LocalFileReferenceMediaResource { staged.append(r.localFilePath); check(true, "peer-level protection forces local upload") } else { fatalError("peer protection ignored") }
        var photo = text
        photo.media = [TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 32, height: 32), resource: CloudResource("missing-thumb")), TelegramMediaImageRepresentation(dimensions: Dimensions(width: 1080, height: 1920), resource: CloudResource("full"))])]
        let photoCopies = nagramiXCopyMessagesAsNew([photo], mediaBox: box)!
        if case let .standalone(media)? = photoCopies[0].mediaReference, let image = media as? TelegramMediaImage, let r = image.representations.first?.resource as? LocalFileReferenceMediaResource {
            staged.append(r.localFilePath)
            check(image.imageId.namespace == Namespaces.Media.LocalImage && image.representations.count == 1 && image.reference == nil && image.partialReference == nil, "full photo gets a new local identity; missing optional thumbnail is omitted")
        } else { fatalError("photo did not become a local upload") }
        check(productionProtectedCopy(.forwardWithoutSource, [ordinary], true, ordinary.id.peerId), "per-chat protection forces copies even without the individual message flag")
        check(!productionProtectedCopy(.forwardWithoutSource, [ordinary], true, PeerId(namespace: 9)), "unrelated source chat does not inherit current-chat protection")
        var missing = fileMessage; missing.media = [TelegramMediaFile(resource: CloudResource("partial"))]
        let before = Set(try FileManager.default.contentsOfDirectory(atPath: NSTemporaryDirectory()).filter { $0.hasPrefix("nagramix-archive-copy-") })
        check(nagramiXCopyMessagesAsNew([fileMessage, missing], mediaBox: box) == nil, "missing complete attachment rejects whole batch")
        let after = Set(try FileManager.default.contentsOfDirectory(atPath: NSTemporaryDirectory()).filter { $0.hasPrefix("nagramix-archive-copy-") })
        check(before == after, "staging rolls back earlier files on a later failure")
        var archived = ordinary; archived.attributes.append(NagramiXArchivedMessageAttribute())
        let archiveCopies = nagramiXCopyMessagesAsNew([archived], mediaBox: box)!
        if case let .standalone(media)? = archiveCopies[0].mediaReference, let f = media as? TelegramMediaFile, let r = f.resource as? LocalFileReferenceMediaResource { staged.append(r.localFilePath); check(true, "existing archive local upload preserved") } else { fatalError("archive regression") }
        try FileManager.default.removeItem(at: source)
        let retainedAfterRemoval = try Data(contentsOf: URL(fileURLWithPath: resource.localFilePath))
        check(retainedAfterRemoval == payload, "staged bytes survive original removal")
        for forward in [false, true] { for broadcast in [false, true] {
            NagramiXTabSettings.current = Self.settings(forward, broadcast)
            check(nagramiXAllowsProtectedContentExport(text) == (forward || broadcast), "no new checkbox; existing switches control protected exports")
            check(!nagramiXAllowsProtectedContentExport(failures[0]), "switches cannot enable secret media export")
        } }
        for mode in [NagramiXMessageTransferMode.forwardWithSource, .forwardWithoutSource, .copyAsNew, .copyToSingleRecipient] {
            let protectedCopy = productionProtectedCopy(mode, [fileMessage], false, fileMessage.id.peerId)
            check(protectedCopy == (mode != .forwardWithSource), "Repost keeps native semantics; custom actions route to copies")
            let effective = productionEffectiveMode(mode, protectedCopy)
            check(effective.singleRecipient == mode.singleRecipient, "protected fallback preserves recipient count")
            check(productionPickerLimit(effective, protectedCopy) == (protectedCopy && mode.singleRecipient ? 1 : nil), "single protected copy is bounded")
            check(productionPickerHasSourceIds(effective, protectedCopy) == (!protectedCopy && mode != .copyAsNew), "protected copy picker does not forward source IDs")
        }
        let fetchBox = MediaBox(); var outputs: [Bool] = []
        var imageMessage = text
        imageMessage.media = [TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 32, height: 32), resource: CloudResource("thumb")), TelegramMediaImageRepresentation(dimensions: Dimensions(width: 1080, height: 1920), resource: CloudResource("photo"))])]
        let operation = nagramiXFetchContentCopyMedia(mediaBox: fetchBox, messages: [fileMessage, fileMessage, imageMessage]).start(next: { outputs.append($0) })
        check(Set(fetchBox.fetched) == ["full", "photo"] && fetchBox.fetched.count == 2, "only primary full attachments; duplicate resource fetched once")
        check(fetchBox.references.allSatisfy { $0.source != nil }, "native fetch keeps authorized source reference")
        fetchBox.emit("full", ResourceData(complete: false)); check(outputs.isEmpty, "partial download cannot complete preparation")
        fetchBox.emit("full", ResourceData(complete: true)); check(outputs.isEmpty, "wait for every primary attachment")
        fetchBox.emit("photo", ResourceData(complete: true)); check(outputs == [true], "full batch completes once")
        check(fetchBox.activeFetches == 0 && fetchBox.activeKeeps == 0, "completion releases native fetch and keep leases")
        operation.dispose()
        let cached = MediaBox(); cached.complete = ["full"]
        outputs = []; _ = nagramiXFetchContentCopyMedia(mediaBox: cached, messages: [fileMessage]).start(next: { outputs.append($0) })
        check(outputs == [true] && cached.fetched.isEmpty, "cached complete media does not start another download")
        let failing = MediaBox(); outputs = []
        _ = nagramiXFetchContentCopyMedia(mediaBox: failing, messages: [fileMessage, imageMessage]).start(next: { outputs.append($0) })
        failing.errors["full"]?(.failed)
        check(outputs == [false] && failing.activeFetches == 0 && failing.activeKeeps == 0, "one fetch error cancels the whole batch and releases resources")
        let cancelled = MediaBox(); outputs = []
        let pending = nagramiXFetchContentCopyMedia(mediaBox: cancelled, messages: [fileMessage]).start(next: { outputs.append($0) }); pending.dispose()
        cancelled.emit("full", ResourceData(complete: true))
        check(outputs.isEmpty && cancelled.activeFetches == 0 && cancelled.activeKeeps == 0, "cancel cannot deliver a stale prepared callback")
        let invalid = MediaBox(); outputs = []
        _ = nagramiXFetchContentCopyMedia(mediaBox: invalid, messages: [fileMessage]).start(next: { outputs.append($0) }); invalid.emit("full", ResourceData(complete: true, offset: 1))
        check(outputs == [false], "invalid complete range rejected")
        let special = MediaBox(); outputs = []
        _ = nagramiXFetchContentCopyMedia(mediaBox: special, messages: [failures[0]]).start(next: { outputs.append($0) })
        check(outputs == [false] && special.fetched.isEmpty, "special messages are rejected before fetching")
        let instant = AccountContext(); let instantChat = ChatControllerImpl(instant); var ready = 0
        instantChat.nagramiXPrepareProtectedCopy(messages: [text]) { ready += 1 }; Queue.flush()
        check(ready == 1 && instant.presented.isEmpty, "text preparation does not flash a loading overlay")
        let pendingContext = AccountContext(); let pendingChat = ChatControllerImpl(pendingContext)
        pendingChat.nagramiXPrepareProtectedCopy(messages: [fileMessage]) { ready += 100 }; Queue.flush()
        let loader = pendingContext.presented.last as! OverlayStatusController; loader.cancel()
        pendingContext.account.postbox.mediaBox.emit("full", ResourceData(complete: true))
        check(ready == 1 && loader.dismissed && pendingContext.account.postbox.mediaBox.activeFetches == 0, "native preparation cancel dismisses the overlay and cannot open a picker later")
        let saveSource = root.appendingPathComponent("document.bin"); try payload.write(to: saveSource)
        var document = TelegramMediaFile(resource: CloudResource("document"), mimeType: "application/pdf"); document.fileName = "../../Report.pdf"
        let exportContext = AccountContext()
        let export = nagramiXSaveCopiedMediaToFiles(context: exportContext, fileReference: FileMediaReference(media: document), present: { view, _ in exportContext.presented.append(view) })
        Queue.flush(); exportContext.emit(.data(DownloadData(path: saveSource.path, isComplete: false)))
        check(!exportContext.presented.contains(where: { $0 is TestFilePicker }), "partial media cannot open the Files exporter")
        exportContext.emit(.data(DownloadData(path: saveSource.path, isComplete: true))); exportContext.finish()
        let filePicker = exportContext.presented.last as! TestFilePicker
        let exportedBytes = try Data(contentsOf: filePicker.url)
        check(filePicker.url.lastPathComponent == "Report.pdf" && exportedBytes == payload, "generic Files export keeps bytes and a sanitized filename, without mp3 fallback")
        export.dispose(); try FileManager.default.removeItem(at: saveSource)
        check(FileManager.default.fileExists(atPath: filePicker.url.path), "document picker keeps its file after fetch disposal and source removal")
        filePicker.didDismiss(); filePicker.complete([])
        check(!FileManager.default.fileExists(atPath: filePicker.url.path) && EngineTempBox.shared.active.isEmpty, "dismiss and completion clean the export exactly once")
        let cancelContext = AccountContext()
        let cancelExport = nagramiXSaveCopiedMediaToFiles(context: cancelContext, fileReference: FileMediaReference(media: document), present: { view, _ in cancelContext.presented.append(view) })
        Queue.flush(); (cancelContext.presented.last as! OverlayStatusController).cancel(); cancelContext.emit(.data(DownloadData(path: source.path, isComplete: true))); cancelExport.dispose()
        check(!cancelContext.presented.contains(where: { $0 is TestFilePicker }), "cancelled export cannot present a stale Files picker")
        let errorContext = AccountContext()
        let unavailableExport = nagramiXSaveCopiedMediaToFiles(context: errorContext, fileReference: FileMediaReference(media: document), present: { view, _ in errorContext.presented.append(view) })
        errorContext.finish()
        check(errorContext.presented.last is TestAlert && !errorContext.presented.contains(where: { $0 is TestFilePicker }), "fetch completion without full data shows a save error")
        unavailableExport.dispose()
        let musicContext = AccountContext(); var music = document; music.attributes = ["music"]
        let musicExport = nagramiXSaveCopiedMediaToFiles(context: musicContext, fileReference: FileMediaReference(media: music), present: { view, _ in musicContext.presented.append(view) })
        check(musicContext.musicExports == 1 && musicContext.presented.isEmpty, "ordinary music keeps the native exporter")
        musicExport.dispose()
        let namedSource = root.appendingPathComponent("named.bin"); try payload.write(to: namedSource)
        for (name, expected) in [(Optional("/"), "_"), (Optional(".."), "Document.pdf"), (nil, "Document.pdf")] {
            let namedContext = AccountContext(); var named = document; named.fileName = name
            let namedExport = nagramiXSaveCopiedMediaToFiles(context: namedContext, fileReference: FileMediaReference(media: named), present: { view, _ in namedContext.presented.append(view) })
            namedContext.emit(.data(DownloadData(path: namedSource.path, isComplete: true))); namedContext.finish()
            let namedPicker = namedContext.presented.last as! TestFilePicker
            check(namedPicker.url.lastPathComponent == expected, "unsafe/absent basename stays inside TempBox and gets an appropriate name")
            namedExport.dispose(); namedPicker.didDismiss()
        }
        let badPathContext = AccountContext()
        let badPathExport = nagramiXSaveCopiedMediaToFiles(context: badPathContext, fileReference: FileMediaReference(media: document), present: { view, _ in badPathContext.presented.append(view) })
        badPathContext.emit(.data(DownloadData(path: root.appendingPathComponent("missing").path, isComplete: true))); badPathContext.finish()
        check(badPathContext.presented.last is TestAlert && EngineTempBox.shared.active.isEmpty, "export staging error reports failure and removes the temporary file")
        badPathExport.dispose()
        print("PASS: \(checks) actual protected copy/content/file lifetime/fetch/cancellation/recipient checks")
    }
    static func settings(_ forward: Bool, _ broadcast: Bool) -> NagramiXTabSettings { NagramiXTabSettings(showForwardWithoutAuthor: forward, showBroadcastMessages: broadcast) }
}

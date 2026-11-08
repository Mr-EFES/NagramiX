import Foundation
import Postbox
import SwiftSignalKit

/// The archive lives in TelegramCore, below the NagramiXCore presentation
/// module in the Bazel dependency graph. Read the persisted switches from
/// the same UserDefaults keys used by NagramiXTabSettings without introducing
/// a TelegramCore -> NagramiXCore dependency cycle.
private struct NagramiXMessageArchiveSettings {
    static let changedNotification = Notification.Name("NagramiXSettingsChanged")

    let showDeletedMessages: Bool
    let saveTemporaryMessages: Bool
    let replayViewOnce: Bool
    let messageEditHistory: Bool

    static var current: NagramiXMessageArchiveSettings {
        let defaults = UserDefaults.standard
        return NagramiXMessageArchiveSettings(
            showDeletedMessages: defaults.object(forKey: "nagramix.messages.showDeletedMessages") as? Bool ?? false,
            saveTemporaryMessages: (defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce")),
            replayViewOnce: (defaults.bool(forKey: "nagramix.messages.saveTemporaryMessages") || defaults.bool(forKey: "nagramix.messages.replayViewOnce")),
            messageEditHistory: defaults.object(forKey: "nagramix.messages.editHistory") as? Bool ?? false
        )
    }
}

public struct NagramiXMessageRevision: Codable, Equatable {
    public let text: String
    public let entities: [MessageTextEntity]
    public let timestamp: Int32

    public init(text: String, entities: [MessageTextEntity], timestamp: Int32) {
        self.text = text
        self.entities = entities
        self.timestamp = timestamp
    }

    /// Only consecutive equal text/entities are duplicates. A → B → A is three
    /// versions, even when several edits arrive during the same second.
    static func appendIfChanged(_ revision: NagramiXMessageRevision, to revisions: inout [NagramiXMessageRevision]) {
        if revisions.last?.text != revision.text || revisions.last?.entities != revision.entities {
            revisions.append(revision)
        }
    }
}

/// Marks a synthetic, display-only message supplied by NagramiXMessageArchive.
/// These messages never enter Postbox and must not be used for server actions.
public final class NagramiXArchivedMessageAttribute: MessageAttribute {
    public let deletedAt: Int32
    public let revisions: [NagramiXMessageRevision]
    public let isTemporary: Bool
    public let isViewOnceReplay: Bool

    public init(deletedAt: Int32, revisions: [NagramiXMessageRevision], isTemporary: Bool = false, isViewOnceReplay: Bool = false) {
        self.deletedAt = deletedAt
        self.revisions = revisions
        self.isTemporary = isTemporary
        self.isViewOnceReplay = isViewOnceReplay
    }

    public required init(decoder: PostboxDecoder) {
        self.deletedAt = decoder.decodeInt32ForKey("d", orElse: 0)
        self.revisions = []
        self.isTemporary = decoder.decodeBoolForKey("t", orElse: false)
        self.isViewOnceReplay = decoder.decodeBoolForKey("v", orElse: false)
    }

    public func encode(_ encoder: PostboxEncoder) {
        encoder.encodeInt32(self.deletedAt, forKey: "d")
        encoder.encodeBool(self.isTemporary, forKey: "t")
        encoder.encodeBool(self.isViewOnceReplay, forKey: "v")
    }
}

public extension Message {
    var nagramiXIsViewOnceReplay: Bool {
        return self.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isViewOnceReplay == true }
    }
    var nagramiXShowsArchiveNotice: Bool {
        return self.attributes.contains { attribute in
            guard let archived = attribute as? NagramiXArchivedMessageAttribute else { return false }
            return !archived.isTemporary || archived.isViewOnceReplay
        }
    }
}

private struct NagramiXArchivePostKey: Hashable {
    let peerId: PeerId
    let namespace: Int32
    let threadId: Int64?
    let groupingKey: Int64
}

public struct NagramiXArchivePostDeletionPlan {
    public let nativeMessageIds: Set<MessageId>
    public let localMessageIds: Set<MessageId>
    public let liveMessageIds: Set<MessageId>
    public init(nativeMessageIds: Set<MessageId>, localMessageIds: Set<MessageId>, liveMessageIds: Set<MessageId>? = nil) {
        self.nativeMessageIds = nativeMessageIds
        self.localMessageIds = localMessageIds
        self.liveMessageIds = liveMessageIds ?? nativeMessageIds
    }
}

private struct NagramiXArchivedForwardInfo: Codable, Equatable {
    let authorId: Int64?
    let sourceId: Int64?
    let sourceMessageId: MessageId?
    let date: Int32
    let authorSignature: String?
    let psaType: String?
    let flags: Int32
    init(_ info: StoreMessageForwardInfo) {
        self.authorId = info.authorId?.toInt64()
        self.sourceId = info.sourceId?.toInt64()
        self.sourceMessageId = info.sourceMessageId
        self.date = info.date
        self.authorSignature = info.authorSignature
        self.psaType = info.psaType
        self.flags = info.flags.rawValue
    }
    var storeInfo: StoreMessageForwardInfo {
        StoreMessageForwardInfo(authorId: self.authorId.map(PeerId.init), sourceId: self.sourceId.map(PeerId.init), sourceMessageId: self.sourceMessageId, date: self.date, authorSignature: self.authorSignature, psaType: self.psaType, flags: MessageForwardInfo.Flags(rawValue: self.flags))
    }
}

private struct NagramiXArchivedContent: Codable, Equatable {
    let text: String
    let entities: [MessageTextEntity]
    let media: [Data]
}

private struct NagramiXArchivedRecord: Codable, Equatable {
    let peerId: Int64
    let namespace: Int32
    let id: Int32
    let authorId: Int64?
    let timestamp: Int32
    let threadId: Int64?
    let groupingKey: Int64?
    let incoming: Bool
    var temporary: Bool?
    var viewOnceReplay: Bool?
    var peerData: [String: Data]
    var content: NagramiXArchivedContent
    var contentTimestamp: Int32?
    var revisions: [NagramiXMessageRevision]
    var deletedAt: Int32?
    var transcriptionAttributes: [Data]? = nil
    var forwardInfo: NagramiXArchivedForwardInfo? = nil
    var globallyUniqueId: Int64? = nil
    var contentAttributes: [Data]? = nil

    // Older clients erased the two flags on a server delete. Only temporary
    // records owned this optional ASR field (including an empty array).
    var wasTemporary: Bool { self.temporary == true || self.viewOnceReplay == true || self.transcriptionAttributes != nil }

    var messageId: MessageId {
        return MessageId(peerId: PeerId(self.peerId), namespace: self.namespace, id: self.id)
    }
}

private struct NagramiXMessageArchiveState: Codable, Equatable {
    var records: [String: NagramiXArchivedRecord] = [:]
    var purgedMessageKeys: Set<String>? = nil
}

private final class NagramiXWeakMessageArchive {
    weak var value: NagramiXMessageArchive?

    init(_ value: NagramiXMessageArchive) {
        self.value = value
    }
}

public final class NagramiXMessageArchive {
    private static let registry = Atomic<[ObjectIdentifier: NagramiXWeakMessageArchive]>(value: [:])

    public static func forPostbox(_ postbox: Postbox) -> NagramiXMessageArchive? {
        return self.registry.with { $0[ObjectIdentifier(postbox)]?.value }
    }

    public static func forMediaBox(_ mediaBox: MediaBox) -> NagramiXMessageArchive? {
        return self.registry.with { values in
            values.values.compactMap { $0.value }.first { $0.postbox.mediaBox === mediaBox }
        }
    }

    private let postbox: Postbox
    private let accountPeerId: PeerId
    public let deferredReactions: NagramiXDeferredReactionsStore
    private let path: String
    private let basePath: String
    private let queue: Queue
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    private let replayCapturePending = Atomic<Set<MessageId>>(value: [])
    private let revisionValue = ValuePromise<Int>(0, ignoreRepeated: false)
    private var revision: Int = 0
    private var settingsObserver: NSObjectProtocol?
    private var lifecycleObservers: [NSObjectProtocol] = []
    private var readyForMediaDownloads = false
    private var inForeground = true
    private var mediaDownloadSettings: (Bool, Bool, Bool)?
    private let renderVersion = Atomic<UInt32>(value: 0)
    private let storageStatusValue = ValuePromise<NagramiXArchiveStorageStatus>(.ready, ignoreRepeated: true)
    private var loadBlocked = false
    private var publishAfterRetry = false
    private var removalTickets: [String: Int64] = [:]
    private var clearTicket: Int64?
    private let captureClearBarrier = Atomic<Int64>(value: 0)
    private var captureTickets: [String: Int64] = [:]
    private let purgedKeys = Atomic<Set<String>>(value: [])
    private lazy var persistence = NagramiXArchivePersistence<NagramiXMessageArchiveState>(write: { [weak self] state in
        guard let self else { throw NagramiXArchiveStorageFailure.writeFailed }
        try JSONEncoder().encode(state).write(to: URL(fileURLWithPath: self.path), options: [.atomic])
    }, schedule: { [weak self] delay, action in
        guard let self else { return {} }
        let timer = SwiftSignalKit.Timer(timeout: delay, repeat: false, completion: action, queue: self.queue)
        timer.start()
        return { timer.invalidate() }
    }, committed: { [weak self] state in
        self?.didPersist(state)
    }, status: { [weak self] status in
        guard let self else { return }
        if case .failed = status { self.publishAfterRetry = true }
        self.storageStatusValue.set(status)
    })

    public var storageStatus: Signal<NagramiXArchiveStorageStatus, NoError> { self.storageStatusValue.get() }

    private var mutationState: NagramiXMessageArchiveState {
        return self.persistence.pending ?? self.state.with { $0 }
    }

    private lazy var mediaStore = NagramiXArchivedMediaStore(mediaBox: self.postbox.mediaBox, queue: self.queue, basePath: self.basePath, changed: { [weak self] in
        self?.publishUpdate()
    })

    public var updates: Signal<Int, NoError> {
        return self.revisionValue.get()
    }

    var capturesMessageEdits: Bool {
        let settings = NagramiXMessageArchiveSettings.current
        return settings.showDeletedMessages || settings.messageEditHistory || settings.saveTemporaryMessages
    }

    public init(postbox: Postbox, accountPeerId: PeerId, basePath: String) {
        self.postbox = postbox
        self.accountPeerId = accountPeerId
        self.deferredReactions = NagramiXDeferredReactionsStore(accountPeerId: accountPeerId, basePath: basePath)
        self.path = basePath + "/nagramix-message-archive.json"
        self.basePath = basePath
        self.queue = Queue(name: "org.nagramix.message-archive", qos: .utility)
        _ = self.mediaStore

        _ = Self.registry.modify { value in
            var value = value
            value[ObjectIdentifier(postbox)] = NagramiXWeakMessageArchive(self)
            return value
        }
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            _ = self.loadPersistedState()
            self.mediaStore.load()
            self.restoreMediaOwnership()
            self.publishUpdate()
        }

        self.settingsObserver = NotificationCenter.default.addObserver(forName: NagramiXMessageArchiveSettings.changedNotification, object: nil, queue: nil, using: { [weak self] _ in
            self?.queue.async {
                self?.refreshMediaDownloads()
                self?.publishUpdate()
            }
        })
        for (name, foreground) in [("UIApplicationDidEnterBackgroundNotification", false), ("UIApplicationWillEnterForegroundNotification", true)] {
            self.lifecycleObservers.append(NotificationCenter.default.addObserver(forName: Notification.Name(name), object: nil, queue: nil, using: { [weak self] _ in
                self?.queue.async {
                    guard let self else { return }
                    self.inForeground = foreground
                    self.refreshMediaDownloads()
                    if foreground { self.retryStorage() }
                }
            }))
        }
    }

    deinit {
        if let settingsObserver = self.settingsObserver {
            NotificationCenter.default.removeObserver(settingsObserver)
        }
        for observer in self.lifecycleObservers { NotificationCenter.default.removeObserver(observer) }
        _ = Self.registry.modify { value in
            var value = value
            value.removeValue(forKey: ObjectIdentifier(self.postbox))
            return value
        }
    }

    public func startMediaDownloads() {
        self.queue.async { [weak self] in
            guard let self else { return }
            self.readyForMediaDownloads = true
            self.refreshMediaDownloads()
        }
    }

    private func refreshMediaDownloads() {
        let settings = NagramiXMessageArchiveSettings.current
        let enabled = self.readyForMediaDownloads && self.inForeground && settings.showDeletedMessages
        let temporary = settings.saveTemporaryMessages
        let replay = self.readyForMediaDownloads && self.inForeground && settings.replayViewOnce
        if let current = self.mediaDownloadSettings, current.0 == enabled, current.1 == temporary, current.2 == replay { return }
        self.mediaDownloadSettings = (enabled, temporary, replay)
        self.mediaStore.configure(enabled: enabled, temporaryEnabled: temporary, replayEnabled: replay)
    }

    public func cacheResourcesToRemove(_ ids: [MediaResourceId]) -> [MediaResourceId] {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.replayViewOnce else { return ids }
        return self.mediaStore.resourcesToRemove(ids, includeTemporary: settings.showDeletedMessages && settings.saveTemporaryMessages, includeOrdinary: settings.showDeletedMessages, includeReplay: settings.replayViewOnce)
    }

    private func publishUpdate() {
        self.revision += 1
        _ = self.renderVersion.modify { $0 &+ 1 }
        self.revisionValue.set(self.revision)
    }

    private func restoreMediaOwnership() {
        for (key, record) in self.state.with({ $0.records }) {
            let requests = self.mediaRequests(record)
            if let ticket = self.mediaStore.reserveRestored(key: key, requests: requests) {
                // Restoration is an old producer even if its reservation raced
                // a clear barrier. Keep bytes until that clear is durable.
                if self.captureClearBarrier.with({ $0 > 0 }) {
                    self.removalTickets[key] = max(self.removalTickets[key] ?? ticket, ticket)
                }
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            }
        }
    }

    private func loadPersistedState() -> Bool {
        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: self.path))
            let loaded = try JSONDecoder().decode(NagramiXMessageArchiveState.self, from: data)
            _ = self.state.swap(loaded)
            _ = self.purgedKeys.modify { $0.union(loaded.purgedMessageKeys ?? []) }
            self.loadBlocked = false
            self.storageStatusValue.set(.ready)
            return true
        } catch {
            let error = error as NSError
            if error.domain == NSCocoaErrorDomain && error.code == NSFileReadNoSuchFileError {
                self.loadBlocked = false
                self.storageStatusValue.set(.ready)
                return true
            }
            // Never overwrite an existing unreadable archive with an empty one.
            self.loadBlocked = true
            self.storageStatusValue.set(.failed(.unreadable))
            return false
        }
    }

    public func retryPersistence() {
        self.queue.async { [weak self] in self?.retryStorage() }
    }

    private func retryStorage() {
        if self.loadBlocked {
            self.storageStatusValue.set(.retrying)
            guard self.loadPersistedState() else { return }
            self.publishUpdate()
        }
        _ = self.persistence.retry()
    }

    @discardableResult
    private func persist(_ state: NagramiXMessageArchiveState, retryNow: Bool = false) -> Bool {
        guard !self.loadBlocked else {
            self.storageStatusValue.set(.failed(.unreadable))
            return false
        }
        return self.persistence.submit(state, retryNow: retryNow)
    }

    private func didPersist(_ updated: NagramiXMessageArchiveState) {
        _ = self.state.swap(updated)
        if let ticket = self.clearTicket {
            self.mediaStore.clear(before: ticket)
            self.captureTickets = self.captureTickets.filter { $0.value > ticket }
        }
        for (key, ticket) in self.removalTickets where updated.records[key] == nil {
            self.mediaStore.remove(keys: Set([key]), before: ticket)
        }
        // A clear may have published its barrier without enqueueing yet.
        // Another record's commit must not forget deferred old ownership.
        self.removalTickets = self.removalTickets.filter { updated.records[$0.key] != nil }
        self.clearTicket = nil
        if self.publishAfterRetry {
            self.publishAfterRetry = false
            self.publishUpdate()
        }
    }

    private static func key(_ id: MessageId) -> String {
        return "\(id.peerId.toInt64()):\(id.namespace):\(id.id)"
    }

    private static func encodedRootObject(_ object: PostboxCoding) -> Data {
        let encoder = PostboxEncoder()
        encoder.encodeRootObject(object)
        return encoder.makeData()
    }

    private static func decodedRootObject(_ data: Data) -> PostboxCoding? {
        return PostboxDecoder(buffer: MemoryBuffer(data: data)).decodeRootObject()
    }

    private func mediaRequests(_ record: NagramiXArchivedRecord) -> [NagramiXArchiveMediaRequest] {
        var peers: [PeerId: Peer] = [:]
        for data in record.peerData.values {
            if let peer = Self.decodedRootObject(data) as? Peer { peers[peer.id] = peer }
        }
        guard let peer = peers[record.messageId.peerId] else { return [] }
        let reference = MessageReference(peer: peer, author: record.authorId.flatMap { peers[PeerId($0)] }, id: record.messageId, timestamp: record.timestamp, incoming: record.incoming, secret: record.wasTemporary, threadId: record.threadId)
        var result: [NagramiXArchiveMediaRequest] = []
        var seen = Set<MediaResourceId>()
        var mediaToRetain = record.content.media.compactMap { Self.decodedRootObject($0) as? Media }
        for data in record.contentAttributes ?? [] {
            if let rich = Self.decodedRootObject(data) as? RichTextMessageAttribute {
                mediaToRetain.append(contentsOf: rich.instantPage.rawMedia.values)
                if let page = rich.fullInstantPage { mediaToRetain.append(contentsOf: page.rawMedia.values) }
            }
        }
        for media in mediaToRetain {
            var mediaReference = AnyMediaReference.message(message: reference, media: media)
            func append(_ resource: TelegramMediaResource, primary: Bool) {
                guard !(resource is EmptyMediaResource), seen.insert(resource.id).inserted else { return }
                result.append(NagramiXArchiveMediaRequest(reference: mediaReference.resourceReference(resource), temporary: record.wasTemporary, primary: primary, replay: record.wasTemporary))
            }
            func appendImage(_ image: TelegramMediaImage) {
                let largest = image.representations.max { lhs, rhs in
                    Int64(lhs.dimensions.width) * Int64(lhs.dimensions.height) < Int64(rhs.dimensions.width) * Int64(rhs.dimensions.height)
                }
                for representation in image.representations { append(representation.resource, primary: representation === largest) }
                for video in image.videoRepresentations { append(video.resource, primary: true) }
                if let video = image.video { appendFile(video) }
            }
            func appendFile(_ file: TelegramMediaFile) {
                append(file.resource, primary: true)
                for representation in file.previewRepresentations { append(representation.resource, primary: false) }
                for thumbnail in file.videoThumbnails { append(thumbnail.resource, primary: false) }
                if let cover = file.videoCover { appendImage(cover) }
                for alternative in file.alternativeRepresentations { appendFile(alternative) }
            }
            func appendMedia(_ item: Media, depth: Int = 0) {
                guard depth <= 8 else { return }
                mediaReference = AnyMediaReference.message(message: reference, media: item)
                if let image = item as? TelegramMediaImage { appendImage(image) }
                if let file = item as? TelegramMediaFile { appendFile(file) }
                if let webFile = item as? TelegramMediaWebFile { append(webFile.resource, primary: true) }
                if let poll = item as? TelegramMediaPoll {
                    for attachment in nagramiXPollMediaAttachments(poll) { appendMedia(attachment, depth: depth + 1) }
                }
                if let game = item as? TelegramMediaGame {
                    if let image = game.image { appendMedia(image, depth: depth + 1) }
                    if let file = game.file { appendMedia(file, depth: depth + 1) }
                }
                if let webpage = item as? TelegramMediaWebpage, case let .Loaded(content) = webpage.content {
                    if let image = content.image { appendMedia(image, depth: depth + 1) }
                    if let file = content.file { appendMedia(file, depth: depth + 1) }
                    for file in self.retainedWebpageFiles(content.attributes) { appendMedia(file, depth: depth + 1) }
                    if let page = content.instantPage?._parse() {
                        for nested in page.rawMedia.values { appendMedia(nested, depth: depth + 1) }
                    }
                }
                if let invoice = item as? TelegramMediaInvoice {
                    if let photo = invoice.photo { appendMedia(photo, depth: depth + 1) }
                    if let extended = invoice.extendedMedia, case let .full(media) = extended { appendMedia(media, depth: depth + 1) }
                }
            }
            appendMedia(media)
        }
        return result
    }

    private func localRepresentation(_ representation: TelegramMediaImageRepresentation) -> TelegramMediaImageRepresentation {
        return TelegramMediaImageRepresentation(dimensions: representation.dimensions, resource: self.mediaStore.localResource(for: representation.resource), progressiveSizes: representation.progressiveSizes, immediateThumbnailData: representation.immediateThumbnailData, hasVideo: representation.hasVideo, isPersonal: representation.isPersonal, typeHint: representation.typeHint)
    }

    private func localImage(_ image: TelegramMediaImage) -> TelegramMediaImage {
        return TelegramMediaImage(imageId: image.imageId, representations: image.representations.map(self.localRepresentation), videoRepresentations: image.videoRepresentations.map { TelegramMediaImage.VideoRepresentation(dimensions: $0.dimensions, resource: self.mediaStore.localResource(for: $0.resource), startTimestamp: $0.startTimestamp) }, immediateThumbnailData: image.immediateThumbnailData, emojiMarkup: image.emojiMarkup, reference: image.reference, partialReference: nil, flags: image.flags, video: image.video.map(self.localFile))
    }

    private func localFile(_ file: TelegramMediaFile) -> TelegramMediaFile {
        return TelegramMediaFile(fileId: file.fileId, partialReference: nil, resource: self.mediaStore.localResource(for: file.resource), previewRepresentations: file.previewRepresentations.map(self.localRepresentation), videoThumbnails: file.videoThumbnails.map { TelegramMediaFile.VideoThumbnail(dimensions: $0.dimensions, resource: self.mediaStore.localResource(for: $0.resource)) }, videoCover: file.videoCover.map(self.localImage), immediateThumbnailData: file.immediateThumbnailData, mimeType: file.mimeType, size: file.size, attributes: file.attributes, alternativeRepresentations: file.alternativeRepresentations.map(self.localFile))
    }

    private func retainedGiftFiles(_ gift: StarGift) -> [TelegramMediaFile] {
        switch gift {
        case let .generic(value): return [value.file]
        case let .unique(value):
            return value.attributes.compactMap { attribute in
                switch attribute {
                case let .model(_, file, _, _), let .pattern(_, file, _): return file
                default: return nil
                }
            }
        }
    }

    private func localGift(_ gift: StarGift) -> StarGift {
        switch gift {
        case let .generic(value):
            return .generic(StarGift.Gift(id: value.id, title: value.title, file: self.localFile(value.file), price: value.price, convertStars: value.convertStars, availability: value.availability, soldOut: value.soldOut, flags: value.flags, upgradeStars: value.upgradeStars, releasedBy: value.releasedBy, perUserLimit: value.perUserLimit, lockedUntilDate: value.lockedUntilDate, auctionSlug: value.auctionSlug, auctionGiftsPerRound: value.auctionGiftsPerRound, auctionStartDate: value.auctionStartDate, upgradeVariantsCount: value.upgradeVariantsCount, background: value.background))
        case let .unique(value):
            let attributes = value.attributes.map { attribute -> StarGift.UniqueGift.Attribute in
                switch attribute {
                case let .model(name, file, rarity, crafted): return .model(name: name, file: self.localFile(file), rarity: rarity, crafted: crafted)
                case let .pattern(name, file, rarity): return .pattern(name: name, file: self.localFile(file), rarity: rarity)
                default: return attribute
                }
            }
            return .unique(StarGift.UniqueGift(id: value.id, giftId: value.giftId, title: value.title, number: value.number, slug: value.slug, owner: value.owner, attributes: attributes, availability: value.availability, giftAddress: value.giftAddress, resellAmounts: value.resellAmounts, resellForTonOnly: value.resellForTonOnly, releasedBy: value.releasedBy, valueAmount: value.valueAmount, valueCurrency: value.valueCurrency, valueUsdAmount: value.valueUsdAmount, flags: value.flags, themePeerId: value.themePeerId, peerColor: value.peerColor, hostPeerId: value.hostPeerId, minOfferStars: value.minOfferStars, craftChancePermille: value.craftChancePermille))
        }
    }

    private func retainedWebpageFiles(_ attributes: [TelegramMediaWebpageAttribute]) -> [TelegramMediaFile] {
        return attributes.flatMap { attribute -> [TelegramMediaFile] in
            switch attribute {
            case let .theme(value): return value.files
            case let .stickerPack(value): return value.files
            case let .giftCollection(value): return value.files
            case let .starGift(value): return self.retainedGiftFiles(value.gift)
            case let .giftAuction(value): return self.retainedGiftFiles(value.gift)
            default: return []
            }
        }
    }

    private func localWebpageAttribute(_ attribute: TelegramMediaWebpageAttribute) -> TelegramMediaWebpageAttribute {
        switch attribute {
        case let .theme(value): return .theme(TelegraMediaWebpageThemeAttribute(files: value.files.map(self.localFile), settings: value.settings))
        case let .stickerPack(value): return .stickerPack(TelegramMediaWebpageStickerPackAttribute(flags: value.flags, files: value.files.map(self.localFile)))
        case let .giftCollection(value): return .giftCollection(TelegramMediaWebpageGiftCollectionAttribute(files: value.files.map(self.localFile)))
        case let .starGift(value): return .starGift(TelegramMediaWebpageStarGiftAttribute(gift: self.localGift(value.gift)))
        case let .giftAuction(value): return .giftAuction(TelegramMediaWebpageGiftAuctionAttribute(gift: self.localGift(value.gift), endDate: value.endDate))
        default: return attribute
        }
    }

    private func localRichPage(_ page: InstantPage) -> InstantPage {
        return InstantPage(blocks: page.blocks, rawMedia: page.rawMedia.mapValues { self.localMedia($0) }, isComplete: page.isComplete, rtl: page.rtl, url: page.url, views: page.views)
    }

    private func localMedia(_ media: Media) -> Media {
        return self.localMedia(media, depth: 0)
    }

    private func localMedia(_ media: Media, depth: Int) -> Media {
        guard depth <= 8 else { return media }
        if let image = media as? TelegramMediaImage { return self.localImage(image) }
        if let file = media as? TelegramMediaFile { return self.localFile(file) }
        if let webFile = media as? TelegramMediaWebFile {
            return TelegramMediaWebFile(resource: self.mediaStore.localResource(for: webFile.resource), mimeType: webFile.mimeType, size: webFile.size, attributes: webFile.attributes)
        }
        if let poll = media as? TelegramMediaPoll {
            return nagramiXMapPollMedia(poll, transform: { self.localMedia($0, depth: depth + 1) }) ?? poll
        }
        if let game = media as? TelegramMediaGame {
            return TelegramMediaGame(gameId: game.gameId, accessHash: game.accessHash, name: game.name, title: game.title, description: game.description, image: game.image.map(self.localImage), file: game.file.map(self.localFile))
        }
        if let webpage = media as? TelegramMediaWebpage, case let .Loaded(content) = webpage.content {
            let page = content.instantPage?._parse()
            let localPage = page.map { value in
                InstantPage(blocks: value.blocks, rawMedia: value.rawMedia.mapValues { self.localMedia($0, depth: depth + 1) }, isComplete: value.isComplete, rtl: value.rtl, url: value.url, views: value.views)
            }
            let localContent = TelegramMediaWebpageLoadedContent(url: content.url, displayUrl: content.displayUrl, hash: content.hash, type: content.type, websiteName: content.websiteName, title: content.title, text: content.text, embedUrl: content.embedUrl, embedType: content.embedType, embedSize: content.embedSize, duration: content.duration, author: content.author, isMediaLargeByDefault: content.isMediaLargeByDefault, imageIsVideoCover: content.imageIsVideoCover, image: content.image.map(self.localImage), file: content.file.map(self.localFile), story: content.story, attributes: content.attributes.map(self.localWebpageAttribute), instantPage: localPage)
            return TelegramMediaWebpage(webpageId: webpage.webpageId, content: .Loaded(localContent))
        }
        if let invoice = media as? TelegramMediaInvoice {
            let photo = invoice.photo.map { TelegramMediaWebFile(resource: self.mediaStore.localResource(for: $0.resource), mimeType: $0.mimeType, size: $0.size, attributes: $0.attributes) }
            let extended: TelegramExtendedMedia?
            if let original = invoice.extendedMedia, case let .full(media) = original {
                extended = .full(media: self.localMedia(media, depth: depth + 1))
            } else {
                extended = invoice.extendedMedia
            }
            return TelegramMediaInvoice(title: invoice.title, description: invoice.description, photo: photo, receiptMessageId: invoice.receiptMessageId, currency: invoice.currency, totalAmount: invoice.totalAmount, startParam: invoice.startParam, extendedMedia: extended, subscriptionPeriod: invoice.subscriptionPeriod, flags: invoice.flags, version: invoice.version)
        }
        return media
    }

    private func hasCompleteRetainedMedia(_ media: Media, depth: Int = 0) -> Bool {
        guard depth <= 8 else { return false }
        if let file = media as? TelegramMediaFile {
            return file.resource is LocalFileReferenceMediaResource
                && file.alternativeRepresentations.allSatisfy { self.hasCompleteRetainedMedia($0, depth: depth + 1) }
                && (file.videoCover.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
        }
        if let image = media as? TelegramMediaImage {
            return image.representations.max(by: { Int64($0.dimensions.width) * Int64($0.dimensions.height) < Int64($1.dimensions.width) * Int64($1.dimensions.height) })?.resource is LocalFileReferenceMediaResource
                && image.videoRepresentations.allSatisfy { $0.resource is LocalFileReferenceMediaResource }
                && (image.video.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
        }
        if let webFile = media as? TelegramMediaWebFile { return webFile.resource is LocalFileReferenceMediaResource }
        if let poll = media as? TelegramMediaPoll { return nagramiXPollMediaAttachments(poll).allSatisfy { self.hasCompleteRetainedMedia($0, depth: depth + 1) } }
        if let webpage = media as? TelegramMediaWebpage, case let .Loaded(content) = webpage.content {
            return (content.image.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
                && (content.file.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
                && self.retainedWebpageFiles(content.attributes).allSatisfy { self.hasCompleteRetainedMedia($0, depth: depth + 1) }
                && (content.instantPage?._parse().rawMedia.values.allSatisfy { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
        }
        if let game = media as? TelegramMediaGame {
            return (game.image.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
                && (game.file.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true)
        }
        if let invoice = media as? TelegramMediaInvoice {
            let photoComplete = invoice.photo.map { self.hasCompleteRetainedMedia($0, depth: depth + 1) } ?? true
            if let extended = invoice.extendedMedia, case let .full(media) = extended {
                return photoComplete && self.hasCompleteRetainedMedia(media, depth: depth + 1)
            }
            return photoComplete
        }
        // Text, contacts, locations and other metadata-only native objects have
        // no primary file to await. Their presence must not hide the retained row.
        return true
    }

    private static func retainedContentAttributes(_ attributes: [MessageAttribute]) -> [Data] {
        return attributes.filter {
            $0 is RichTextMessageAttribute || $0 is MediaSpoilerMessageAttribute
                || $0 is WebpagePreviewMessageAttribute || $0 is InvertMediaMessageAttribute
                || $0 is ReplyMessageAttribute || $0 is OutgoingContentInfoMessageAttribute
        }.map(self.encodedRootObject)
    }

    private static func isRegularArchiveIdentifier(_ id: MessageId) -> Bool {
        if id.peerId.isVerificationCodes { return false }
        if id.peerId.namespace == Namespaces.Peer.SecretChat {
            return id.namespace == Namespaces.Message.SecretIncoming || id.namespace == Namespaces.Message.Local
        }
        return id.namespace == Namespaces.Message.Cloud
    }

    private static func makeRecord(message: StoreMessage, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        guard case let .Id(id) = message.id else {
            return nil
        }
        let retainedTemporary = nagramiXCanRetainTemporaryMessage(message)
        guard (id.namespace == Namespaces.Message.Cloud && id.peerId.namespace != Namespaces.Peer.SecretChat) || retainedTemporary else {
            return nil
        }
        // Synthetic display messages must never become a fresh producer after clear.
        guard !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) else { return nil }
        guard !id.peerId.isVerificationCodes else {
            return nil
        }
        let temporary = message.attributes.contains(where: { attribute in
            if let value = attribute as? AutoremoveTimeoutMessageAttribute { return value.timeout > 0 }
            if let value = attribute as? AutoclearTimeoutMessageAttribute { return value.timeout > 0 }
            return false
        })
        let replay = retainedTemporary
        guard !message.flags.contains(.CopyProtected) || (temporary && NagramiXMessageArchiveSettings.current.saveTemporaryMessages) || replay else {
            return nil
        }
        guard !temporary || retainedTemporary else { return nil }
        guard !message.attributes.contains(where: { $0 is EphemeralMessageAttribute || $0 is EphemeralOutgoingMessageAttribute }),
              !message.media.contains(where: { $0 is TelegramMediaExpiredContent }) else {
            return nil
        }
        guard !message.media.contains(where: { $0 is TelegramMediaPaidContent }) else {
            return nil
        }
        guard peers[id.peerId]?.isCopyProtectionEnabled != true || retainedTemporary else {
            return nil
        }

        let entities = (message.attributes.first(where: { $0 is TextEntitiesMessageAttribute }) as? TextEntitiesMessageAttribute)?.entities ?? []
        let media = message.media.compactMap { media -> Data? in
            if retainedTemporary || media is TelegramMediaImage || media is TelegramMediaFile || media is TelegramMediaPoll {
                return self.encodedRootObject(media)
            }
            return nil
        }
        var peerData: [String: Data] = [:]
        var peerIds = Set<PeerId>([id.peerId])
        if let authorId = message.authorId {
            peerIds.insert(authorId)
        }
        if let info = message.forwardInfo {
            if let id = info.authorId { peerIds.insert(id) }
            if let id = info.sourceId { peerIds.insert(id) }
        }
        for media in message.media {
            peerIds.formUnion(media.peerIds)
        }
        for attribute in message.attributes { peerIds.formUnion(attribute.associatedPeerIds) }
        for peerId in peerIds {
            if let peer = peers[peerId] {
                peerData["\(peerId.toInt64())"] = self.encodedRootObject(peer)
            }
        }
        return NagramiXArchivedRecord(
            peerId: id.peerId.toInt64(),
            namespace: id.namespace,
            id: id.id,
            authorId: message.authorId?.toInt64(),
            timestamp: message.timestamp,
            threadId: message.threadId,
            groupingKey: message.groupingKey,
            incoming: message.flags.contains(.Incoming),
            temporary: temporary,
            viewOnceReplay: replay ? true : nil,
            peerData: peerData,
            content: NagramiXArchivedContent(text: message.text, entities: entities, media: media),
            contentTimestamp: (message.attributes.first(where: { $0 is EditedMessageAttribute }) as? EditedMessageAttribute).flatMap { $0.date > 0 ? $0.date : nil } ?? message.timestamp,
            revisions: [],
            deletedAt: nil,
            transcriptionAttributes: temporary ? message.attributes.filter {
                $0 is AudioTranscriptionMessageAttribute || $0 is DerivedDataMessageAttribute
            }.map(self.encodedRootObject) : nil,
            forwardInfo: message.forwardInfo.map(NagramiXArchivedForwardInfo.init),
            globallyUniqueId: message.globallyUniqueId,
            contentAttributes: retainedTemporary ? Self.retainedContentAttributes(message.attributes) : nil
        )
    }

    private static func makeRecord(message: Message, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        return self.makeRecord(
            message: StoreMessage(
                id: .Id(message.id),
                customStableId: nil,
                globallyUniqueId: message.globallyUniqueId,
                groupingKey: message.groupingKey,
                threadId: message.threadId,
                timestamp: message.timestamp,
                flags: StoreMessageFlags(message.flags),
                tags: message.tags,
                globalTags: message.globalTags,
                localTags: message.localTags,
                forwardInfo: message.forwardInfo.map(StoreMessageForwardInfo.init),
                authorId: message.author?.id,
                text: message.text,
                attributes: message.attributes,
                media: message.media
            ),
            peers: peers
        )
    }

    /// Called after a successful native send has its final server ID/resources.
    /// captureIncoming is the historical shared ingestion entry, now bidirectional.
    public func captureSent(_ message: StoreMessage, transaction: Transaction) {
        guard !message.flags.contains(.Incoming),
              NagramiXMessageArchiveSettings.current.showDeletedMessages || nagramiXCanRetainTemporaryMessage(message) else { return }
        var peers: [PeerId: Peer] = [:]
        var ids = Set<PeerId>([message.id.peerId])
        if let authorId = message.authorId { ids.insert(authorId) }
        if let forward = message.forwardInfo {
            if let id = forward.authorId { ids.insert(id) }
            if let id = forward.sourceId { ids.insert(id) }
        }
        for media in message.media { ids.formUnion(media.peerIds) }
        for attribute in message.attributes { ids.formUnion(attribute.associatedPeerIds) }
        for id in ids { if let peer = transaction.getPeer(id) { peers[id] = peer } }
        self.captureIncoming(message, peers: peers)
    }

    public func captureIncoming(_ message: StoreMessage, peers: [PeerId: Peer]) {
        if message.media.contains(where: { $0 is TelegramMediaExpiredContent }), case let .Id(id) = message.id {
            self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
            return
        }
        let settings = NagramiXMessageArchiveSettings.current
        // Edit history captures the real previous Message immediately before an edit is
        // applied. Keeping each approved message on disk is only necessary when a
        // later server-side deletion may need to be rendered locally.
        let eligibleReplay = nagramiXCanRetainTemporaryMessage(message)
        guard settings.showDeletedMessages || eligibleReplay else {
            return
        }
        guard let record = Self.makeRecord(message: message, peers: peers), record.messageId.peerId != self.accountPeerId else {
            return
        }
        guard !self.purgedKeys.with({ $0.contains(Self.key(record.messageId)) }) else { return }
        let requests = self.mediaRequests(record)
        let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
        self.queue.async { [weak self] in
            guard let self, !self.rejectPurgedCapture(key: Self.key(record.messageId), ticket: ticket) else { return }
            var updated = self.mutationState
            let key = Self.key(record.messageId)
            if let current = updated.records[key] {
                var record = record
                if current.viewOnceReplay == true { record.viewOnceReplay = true }
                if current.wasTemporary { record.temporary = true }
                if record.content == current.content, record.contentAttributes == nil { record.contentAttributes = current.contentAttributes }
                record.revisions = current.revisions
                if record.content.media == current.content.media, record.transcriptionAttributes?.isEmpty != false {
                    record.transcriptionAttributes = current.transcriptionAttributes
                }
                if record.content == current.content {
                    // Re-fetching a message must not reset the edit date.
                    record.contentTimestamp = max(current.contentTimestamp ?? current.timestamp, record.contentTimestamp ?? record.timestamp)
                } else if settings.messageEditHistory && (record.content.text != current.content.text || record.content.entities != current.content.entities) {
                    // History pages / sync can refresh an existing snapshot too,
                    // without going through the explicit edit-update operation.
                    NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp), to: &record.revisions)
                }
                record.deletedAt = current.deletedAt
                updated.records[key] = record
            } else {
                updated.records[key] = record
            }
            self.persist(updated)
            self.publishUpdate()
            let retainedRequests = updated.records[key].map(self.mediaRequests) ?? requests
            self.mediaStore.retain(key: key, requests: retainedRequests, ticket: ticket)
        }
    }

    /// Also covers existing attachments when the switch was enabled after receipt.
    /// Capturing bytes does not itself consume the message or start its timer.
    public func captureTemporaryBeforeViewing(message: Message) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.saveTemporaryMessages, nagramiXCanRetainTemporaryMessage(message),
              !message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) else { return }
        let peers: [PeerId: Peer] = message.peers.reduce([:], { current, entry in
            var current = current
            current[entry.0] = entry.1
            return current
        })
        if let record = Self.makeRecord(message: message, peers: peers), record.wasTemporary, record.messageId.peerId != self.accountPeerId {
            guard !self.purgedKeys.with({ $0.contains(Self.key(record.messageId)) }) else { return }
            let replayCapture = record.viewOnceReplay == true
            if replayCapture && self.state.with({ $0.records[Self.key(record.messageId)]?.viewOnceReplay == true }) { return }
            if replayCapture {
                var inserted = false
                _ = self.replayCapturePending.modify { pending in
                    var pending = pending; inserted = pending.insert(record.messageId).inserted; return pending
                }
                guard inserted else { return }
            }
            let requests = self.mediaRequests(record)
            let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
            self.queue.async { [weak self] in
                guard let self else { return }
                defer {
                    if replayCapture { _ = self.replayCapturePending.modify { pending in var pending = pending; pending.remove(record.messageId); return pending } }
                }
                guard !self.rejectPurgedCapture(key: Self.key(record.messageId), ticket: ticket) else { return }
            var updated = self.mutationState
                let key = Self.key(record.messageId)
                if updated.records[key] == nil { updated.records[key] = record }
                else if record.viewOnceReplay == true { updated.records[key]?.viewOnceReplay = true }
                self.persist(updated)
                self.publishUpdate()
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            }
        }
    }

    /// Called immediately before Telegram replaces media with expired content.
    /// Existing approved copies remain archived even if capture is later disabled.
    public func archiveTemporaryExpiration(message: Message, expiredAt: Int32) {
        self.captureTemporaryBeforeViewing(message: message)
        self.markTemporaryExpired(id: message.id, expiredAt: expiredAt)
    }

    public func markTemporaryExpired(id: MessageId, expiredAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            let key = Self.key(id)
            guard var record = updated.records[key], record.wasTemporary, record.deletedAt == nil else { return }
            record.deletedAt = expiredAt
            updated.records[key] = record
            self.persist(updated)
            self.publishUpdate()
        }
    }

    public func recordIncomingEdit(previousMessage: Message, replacementMessage: StoreMessage, peers: [PeerId: Peer], receivedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.messageEditHistory || nagramiXCanRetainTemporaryMessage(previousMessage) || nagramiXCanRetainTemporaryMessage(replacementMessage) else {
            return
        }
        guard let previous = Self.makeRecord(message: previousMessage, peers: peers), let replacement = Self.makeRecord(message: replacementMessage, peers: peers), replacement.messageId.peerId != self.accountPeerId else {
            return
        }
        let requests = self.mediaRequests(replacement)
        let ticket = self.mediaStore.reserve(key: Self.key(replacement.messageId), requests: requests)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            guard !self.rejectPurgedCapture(key: Self.key(replacement.messageId), ticket: ticket) else { return }
            var updated = self.mutationState
            let key = Self.key(replacement.messageId)
            var current = updated.records[key] ?? previous
            guard current.content != replacement.content || current.contentAttributes != replacement.contentAttributes else {
                self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
                return
            }
            if settings.messageEditHistory && (current.content.text != replacement.content.text || current.content.entities != replacement.content.entities) {
                let previousRevision = NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp)
                NagramiXMessageRevision.appendIfChanged(previousRevision, to: &current.revisions)
                // If capture was paused or sync skipped intermediate updates,
                // also retain the actual previous Postbox version we observed.
                NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: previous.content.text, entities: previous.content.entities, timestamp: previous.contentTimestamp ?? previous.timestamp), to: &current.revisions)
            }
            current.content = replacement.content
            current.contentAttributes = replacement.contentAttributes ?? current.contentAttributes
            current.contentTimestamp = (replacementMessage.attributes.first(where: { $0 is EditedMessageAttribute }) as? EditedMessageAttribute).flatMap { $0.date > 0 ? $0.date : nil } ?? receivedAt
            current.peerData = replacement.peerData
            updated.records[key] = current
            self.persist(updated)
            self.mediaStore.retain(key: key, requests: requests, ticket: ticket)
            self.publishUpdate()
        }
    }

    public func archiveServerDeletion(upToMessageId id: MessageId, deletedAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            let ids = self.mutationState.records.values.filter { $0.messageId.peerId == id.peerId && $0.namespace == id.namespace && $0.id <= id.id }.map { $0.messageId }
            self.archiveServerDeletion(messageIds: ids, deletedAt: deletedAt)
        }
    }

    public func archiveServerDeletion(messageIds: [MessageId], deletedAt: Int32) {
        // A later switch-off pauses capture and hides the archive, but does not
        // discard content that was already saved with the user's approval.
        let keys = Set(messageIds.map { Self.key($0) })
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            var changed = false
            for key in keys {
                if var record = updated.records[key] {
                    // Consumption in another client changes deletion state, not
                    // the retained media's type, bytes or transcription ownership.
                    if record.deletedAt != nil { continue }
                    record.deletedAt = deletedAt
                    updated.records[key] = record
                    changed = true
                }
            }
            if changed {
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    public func archiveServerDeletion(globalIds: [Int32], deletedAt: Int32) {
        let ids = Set(globalIds)
        self.queue.async { [weak self] in
            guard let self else {
                return
            }
            var updated = self.mutationState
            var changed = false
            let matchingKeys = updated.records.compactMap { key, record -> String? in
                if record.namespace == Namespaces.Message.Cloud && record.messageId.peerId.namespace != Namespaces.Peer.CloudChannel && ids.contains(record.id) {
                    return key
                } else {
                    return nil
                }
            }
            for key in matchingKeys {
                guard var record = updated.records[key] else {
                    continue
                }
                if record.deletedAt != nil { continue }
                record.deletedAt = deletedAt
                updated.records[key] = record
                changed = true
            }
            if changed {
                self.persist(updated)
                self.publishUpdate()
            }
        }
    }

    /// Reserve available media before native deletion. OFF never captures new content.
    public func archiveMessagesBeforeDeletion(_ messages: [Message], deletedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        let ids = Set(messages.map { $0.id })
        var captured: [(NagramiXArchivedRecord, [NagramiXArchiveMediaRequest], Int64)] = []
        if settings.showDeletedMessages || settings.saveTemporaryMessages {
            for message in messages where settings.showDeletedMessages || nagramiXCanRetainTemporaryMessage(message) {
                let peers: [PeerId: Peer] = message.peers.reduce([:], { current, entry in
                    var current = current
                    current[entry.0] = entry.1
                    return current
                })
                guard let record = Self.makeRecord(message: message, peers: peers), record.messageId.peerId != self.accountPeerId else { continue }
                guard !self.purgedKeys.with({ $0.contains(Self.key(record.messageId)) }) else { continue }
                let requests = self.mediaRequests(record)
                let ticket = self.mediaStore.reserve(key: Self.key(record.messageId), requests: requests)
                captured.append((record, requests, ticket))
            }
        }
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            for (snapshot, _, ticket) in captured {
                if self.rejectPurgedCapture(key: Self.key(snapshot.messageId), ticket: ticket) { continue }
                let key = Self.key(snapshot.messageId)
                var record = snapshot
                if let current = updated.records[key] {
                    record.revisions = current.revisions
                    if current.viewOnceReplay == true { record.viewOnceReplay = true }
                    if current.wasTemporary { record.temporary = true }
                    if record.content == current.content, record.contentAttributes == nil { record.contentAttributes = current.contentAttributes }
                    if record.content.media == current.content.media, record.transcriptionAttributes?.isEmpty != false {
                        record.transcriptionAttributes = current.transcriptionAttributes
                    }
                    if record.content == current.content {
                        record.contentTimestamp = max(current.contentTimestamp ?? current.timestamp, record.contentTimestamp ?? record.timestamp)
                    } else if settings.messageEditHistory && (record.content.text != current.content.text || record.content.entities != current.content.entities) {
                        NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: current.content.text, entities: current.content.entities, timestamp: current.contentTimestamp ?? current.timestamp), to: &record.revisions)
                    }
                    record.deletedAt = current.deletedAt
                }
                updated.records[key] = record
            }
            for id in ids {
                let key = Self.key(id)
                guard var record = updated.records[key] else { continue }
                if record.deletedAt == nil { record.deletedAt = deletedAt }
                updated.records[key] = record
            }
            if updated != self.mutationState {
                self.persist(updated)
                self.publishUpdate()
            }
            for (record, requests, ticket) in captured {
                if self.rejectPurgedCapture(key: Self.key(record.messageId), ticket: ticket) { continue }
                let key = Self.key(record.messageId)
                self.mediaStore.retain(key: key, requests: updated.records[key].map(self.mediaRequests) ?? requests, ticket: ticket)
            }
        }
    }

    public func archiveHistoryBeforeDeletion(transaction: Transaction, peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, namespaces: MessageIdNamespaces) {
        let settings = NagramiXMessageArchiveSettings.current
        let regularNamespaces: [MessageId.Namespace] = peerId.namespace == Namespaces.Peer.SecretChat
            ? [Namespaces.Message.SecretIncoming, Namespaces.Message.Local] : [Namespaces.Message.Cloud]
        guard regularNamespaces.contains(where: { namespaces.contains($0) }) else { return }
        let deletedAt = Int32(Date().timeIntervalSince1970)
        if settings.showDeletedMessages || settings.saveTemporaryMessages {
            var messages: [Message] = []
            for namespace in regularNamespaces where namespaces.contains(namespace) {
                transaction.withAllMessages(peerId: peerId, namespace: namespace, { message in
                    if (threadId == nil || message.threadId == threadId)
                        && (minTimestamp == nil || message.timestamp >= minTimestamp!)
                        && (maxTimestamp == nil || message.timestamp <= maxTimestamp!)
                        && (settings.showDeletedMessages || nagramiXCanRetainTemporaryMessage(message)) {
                        messages.append(message)
                    }
                    return true
                })
            }
            self.archiveMessagesBeforeDeletion(messages, deletedAt: deletedAt)
        }
        self.archiveHistoryDeletion(peerId: peerId, threadId: threadId, minTimestamp: minTimestamp, maxTimestamp: maxTimestamp, deletedAt: deletedAt)
    }

    public func archiveMessageRangeBeforeDeletion(transaction: Transaction, peerId: PeerId, namespace: MessageId.Namespace, minId: Int32, maxId: Int32, deletedAt: Int32) {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.saveTemporaryMessages, Self.isRegularArchiveIdentifier(MessageId(peerId: peerId, namespace: namespace, id: minId)) else { return }
        var messages: [Message] = []
        transaction.withAllMessages(peerId: peerId, namespace: namespace, { message in
            if message.id.id >= minId && message.id.id <= maxId, settings.showDeletedMessages || nagramiXCanRetainTemporaryMessage(message) { messages.append(message) }
            return true
        })
        self.archiveMessagesBeforeDeletion(messages, deletedAt: deletedAt)
    }

    private func archiveHistoryDeletion(peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, deletedAt: Int32) {
        self.queue.async { [weak self] in
            guard let self else { return }
            let ids = self.mutationState.records.values.filter { record in
                record.messageId.peerId == peerId && Self.isRegularArchiveIdentifier(record.messageId)
                    && (threadId == nil || record.threadId == threadId)
                    && (minTimestamp == nil || record.timestamp >= minTimestamp!)
                    && (maxTimestamp == nil || record.timestamp <= maxTimestamp!)
            }.map { $0.messageId }
            self.archiveServerDeletion(messageIds: ids, deletedAt: deletedAt)
        }
    }

    /// The key includes conversation, namespace and topic; equal album keys in
    /// other chats must never share selection or deletion ownership.
    public func postMessageIds(messageIds: Set<MessageId>, messages: [Message]) -> Set<MessageId> {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.saveTemporaryMessages else { return messageIds }
        let records = self.state.with { $0.records }
        var descriptors: [MessageId: NagramiXArchivePostKey] = [:]
        for record in records.values where settings.showDeletedMessages || (settings.saveTemporaryMessages && record.wasTemporary) {
            if let key = record.groupingKey { descriptors[record.messageId] = NagramiXArchivePostKey(peerId: record.messageId.peerId, namespace: record.namespace, threadId: record.threadId, groupingKey: key) }
        }
        for message in messages {
            if Self.isRegularArchiveIdentifier(message.id), let key = message.groupingKey { descriptors[message.id] = NagramiXArchivePostKey(peerId: message.id.peerId, namespace: message.id.namespace, threadId: message.threadId, groupingKey: key) }
        }
        let groups = Set(messageIds.compactMap { descriptors[$0] })
        return messageIds.union(descriptors.compactMap { groups.contains($0.value) ? $0.key : nil })
    }

    public func localPostDeletionCandidates(messages: [Message]) -> Set<MessageId> {
        let liveGroups = Set(messages.filter { !$0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) }.compactMap { message -> NagramiXArchivePostKey? in
            guard let key = message.groupingKey else { return nil }
            return NagramiXArchivePostKey(peerId: message.id.peerId, namespace: message.id.namespace, threadId: message.threadId, groupingKey: key)
        })
        return Set(messages.filter { message in
            guard message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }), self.isLocallyDeletedMessage(id: message.id) else { return false }
            if let key = message.groupingKey { return !liveGroups.contains(NagramiXArchivePostKey(peerId: message.id.peerId, namespace: message.id.namespace, threadId: message.threadId, groupingKey: key)) }
            return true
        }.map { $0.id })
    }

    /// Freeze the phase before confirmation/undo. A subsequent server deletion
    /// of a live selected post must not turn the first click into a local purge.
    public func postDeletionPlan(transaction: Transaction, messageIds: Set<MessageId>, localCandidates: Set<MessageId>) -> NagramiXArchivePostDeletionPlan {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.saveTemporaryMessages else {
            return NagramiXArchivePostDeletionPlan(nativeMessageIds: messageIds, localMessageIds: [])
        }
        var live: [MessageId: Message] = [:]
        for id in messageIds {
            if let message = transaction.getMessage(id) { live[id] = message }
            for message in transaction.getMessageGroup(id) ?? [] { live[message.id] = message }
        }
        let ids = self.postMessageIds(messageIds: messageIds, messages: Array(live.values))
        for id in ids where live[id] == nil { live[id] = transaction.getMessage(id) }
        let records = self.state.with { $0.records }
        if !settings.showDeletedMessages {
            // Explicit deletion is different from remote expiry. Freeze proof
            // from the native row/retained record before confirmation and Undo.
            let liveTemporary = Set(live.values.filter { nagramiXCanRetainTemporaryMessage($0) }.map { $0.id }).intersection(ids)
            let retainedTemporary = Set(ids.filter { id in
                records[Self.key(id)]?.wasTemporary == true && (live[id] == nil || live[id]?.media.contains(where: { $0 is TelegramMediaExpiredContent }) == true)
            })
            return NagramiXArchivePostDeletionPlan(nativeMessageIds: ids.subtracting(retainedTemporary.subtracting(Set(live.keys))), localMessageIds: liveTemporary.union(retainedTemporary), liveMessageIds: Set(live.keys).intersection(ids))
        }
        func group(_ id: MessageId) -> NagramiXArchivePostKey? {
            if let message = live[id], let key = message.groupingKey {
                return NagramiXArchivePostKey(peerId: id.peerId, namespace: id.namespace, threadId: message.threadId, groupingKey: key)
            }
            if let record = records[Self.key(id)], let key = record.groupingKey {
                return NagramiXArchivePostKey(peerId: id.peerId, namespace: id.namespace, threadId: record.threadId, groupingKey: key)
            }
            return nil
        }
        func isExpiredRetainedPlaceholder(_ id: MessageId) -> Bool {
            return records[Self.key(id)]?.wasTemporary == true && records[Self.key(id)]?.deletedAt != nil
                && live[id]?.media.contains(where: { $0 is TelegramMediaExpiredContent }) == true
        }
        let liveGroups = Set(live.keys.filter { !isExpiredRetainedPlaceholder($0) }.compactMap(group))
        let approved = localCandidates.filter { records[Self.key($0)]?.deletedAt != nil }
        let approvedGroups = Set(approved.compactMap(group))
        let local = Set(ids.filter { id in
            guard live[id] == nil || isExpiredRetainedPlaceholder(id), records[Self.key(id)] != nil else { return false }
            if let key = group(id) { return approvedGroups.contains(key) && !liveGroups.contains(key) }
            return approved.contains(id)
        })
        return NagramiXArchivePostDeletionPlan(nativeMessageIds: ids.subtracting(local.subtracting(Set(live.keys))), localMessageIds: local, liveMessageIds: Set(live.keys).intersection(ids))
    }

    private func rejectPurgedCapture(key: String, ticket: Int64) -> Bool {
        guard ticket <= self.captureClearBarrier.with({ $0 }) || self.purgedKeys.with({ $0.contains(key) }) else {
            self.captureTickets[key] = max(self.captureTickets[key] ?? ticket, ticket)
            return false
        }
        // A late reservation may be newer than the purge barrier. Do not remove
        // bytes still displayed after a failed JSON commit; defer to didPersist.
        if self.state.with({ $0.records[key] }) != nil {
            self.removalTickets[key] = max(self.removalTickets[key] ?? ticket, ticket)
        } else {
            self.mediaStore.remove(keys: Set([key]), before: ticket)
        }
        return true
    }

    /// Only the explicit second-stage UI action calls this method. Native and
    /// server deletion paths continue to retain snapshots rather than purge them.
    public func deleteArchivedPosts(messageIds: Set<MessageId>, allowingLiveTemporaryMessageIds: Set<MessageId> = []) -> Signal<Void, NoError> {
        return Signal { [self] subscriber in
            let records = self.state.with { $0.records }
            let explicitTemporary = allowingLiveTemporaryMessageIds.intersection(messageIds).filter { id in
                Self.isRegularArchiveIdentifier(id) && (records[Self.key(id)]?.wasTemporary ?? true)
            }
            let deleted = messageIds.filter { id in
                guard let record = records[Self.key(id)] else { return false }
                return record.deletedAt != nil || (explicitTemporary.contains(id) && record.wasTemporary)
            }
            let groups = Set(deleted.compactMap { id -> NagramiXArchivePostKey? in
                guard let record = records[Self.key(id)], let key = record.groupingKey else { return nil }
                return NagramiXArchivePostKey(peerId: id.peerId, namespace: id.namespace, threadId: record.threadId, groupingKey: key)
            })
            let approved = Set(messageIds.compactMap { id -> String? in
                let key = Self.key(id)
                guard let record = records[key] else { return nil }
                if deleted.contains(id) { return key }
                guard let group = record.groupingKey, groups.contains(NagramiXArchivePostKey(peerId: id.peerId, namespace: id.namespace, threadId: record.threadId, groupingKey: group)) else { return nil }
                return key
            }).union(explicitTemporary.map { Self.key($0) })
            guard !approved.isEmpty else { subscriber.putCompletion(); return EmptyDisposable }
            _ = self.purgedKeys.modify { $0.union(approved) }
            let ticket = self.mediaStore.barrier()
            self.queue.async { [weak self] in
                guard let self else { subscriber.putCompletion(); return }
                var updated = self.mutationState
                updated.purgedMessageKeys = (updated.purgedMessageKeys ?? []).union(approved)
                for key in approved {
                    updated.records.removeValue(forKey: key)
                    self.removalTickets[key] = max(self.removalTickets[key] ?? ticket, ticket)
                }
                self.persist(updated, retryNow: true)
                self.publishUpdate()
                subscriber.putNext(())
                subscriber.putCompletion()
            }
            return EmptyDisposable
        }
    }

    public func removeLocal(messageIds: [MessageId]) {
        // Individual deletion never purges an approved archive snapshot.
        self.archiveServerDeletion(messageIds: messageIds, deletedAt: Int32(Date().timeIntervalSince1970))
    }

    public func clear(peerId: PeerId) {
        // Keep this compatibility entry non-destructive. Only clearAll purges data.
        self.archiveHistoryDeletion(peerId: peerId, threadId: nil, minTimestamp: nil, maxTimestamp: nil, deletedAt: Int32(Date().timeIntervalSince1970))
    }

    public func clearAll() {
        let ticket = self.mediaStore.barrier()
        _ = self.captureClearBarrier.modify { max($0, ticket) }
        self.queue.async { [weak self] in
            guard let self else { return }
            for key in self.mutationState.records.keys where (self.captureTickets[key] ?? 0) <= ticket {
                self.removalTickets[key] = max(self.removalTickets[key] ?? ticket, ticket)
            }
            self.clearTicket = ticket
            // A durable snapshot dropping pre-barrier captures is the tombstone. Keep the
            // previous JSON and media on failure; clear bytes only after commit.
            self.loadBlocked = false // explicit user-requested full reset
            var empty = NagramiXMessageArchiveState()
            let old = self.mutationState
            // A producer reserved after this clear barrier may already have
            // committed before the clear block reached the serial queue.
            empty.records = old.records.filter { (self.captureTickets[$0.key] ?? 0) > ticket }
            let deletedKeys = Set(old.records.compactMap { $0.value.deletedAt != nil && empty.records[$0.key] == nil ? $0.key : nil })
            empty.purgedMessageKeys = (old.purgedMessageKeys ?? []).union(deletedKeys)
            _ = self.purgedKeys.modify { $0.union(deletedKeys) }
            self.persist(empty, retryNow: true)
            self.publishUpdate()
        }
    }

    public func revisions(messageId: MessageId, currentText: String? = nil, currentEntities: [MessageTextEntity]? = nil) -> [NagramiXMessageRevision] {
        guard NagramiXMessageArchiveSettings.current.messageEditHistory else {
            return []
        }
        guard let record = self.state.with({ $0.records[Self.key(messageId)] }) else {
            return []
        }
        var result = record.revisions
        let text = currentText ?? record.content.text
        let entities = currentEntities ?? record.content.entities
        let current = NagramiXMessageRevision(text: text, entities: entities, timestamp: record.contentTimestamp ?? record.timestamp)
        NagramiXMessageRevision.appendIfChanged(current, to: &result)
        return result.count > 1 ? result : []
    }

    /// Обработчики выделения должны получать тот же объект, который виден в ленте,
    /// когда вместо истёкшей записи Postbox показано сохранённое вложение.
    /// Resolve an incoming one-time message to a completed local copy for
    /// explicit copy actions; never turn the original into a server forward.
    public func replayCopyForInteraction(id: MessageId, liveMessage: Message?) -> Message? {
        guard nagramiXTemporaryMessagesEnabled(),
              let result = self.temporaryInteractionMessage(id: id, liveMessage: liveMessage),
              result.attributes.contains(where: { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }) else { return nil }
        return result
    }

    /// Resolve a retained temporary snapshot without capture, expiry, reads or RPCs.
    /// Native live messages keep their identity when retention is disabled.
    public func temporaryInteractionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        guard nagramiXTemporaryMessagesEnabled() else { return liveMessage }
        guard let record = self.state.with({ $0.records[Self.key(id)] }), record.wasTemporary,
              Self.isRegularArchiveIdentifier(record.messageId) else { return liveMessage }
        return self.renderDeletedRecord(record, requireCompleteMedia: false) ?? liveMessage
    }

    /// Missing Postbox rows may still own a queued content-read operation.
    /// Only proven incoming temporary snapshots suppress it; unknown IDs remain native.
    public func shouldSuppressTemporaryContentReceipt(id: MessageId) -> Bool {
        guard nagramiXTemporaryMessagesEnabled(), Self.isRegularArchiveIdentifier(id) else { return false }
        return self.state.with { state in
            guard let record = state.records[Self.key(id)] else { return false }
            return record.incoming && record.wasTemporary
        }
    }

    public func shouldSuppressTemporaryContentReceipt(peerId: PeerId, globallyUniqueId: Int64) -> Bool {
        guard nagramiXTemporaryMessagesEnabled(), peerId.namespace == Namespaces.Peer.SecretChat else { return false }
        return self.state.with { state in
            state.records.values.contains { record in
                record.messageId.peerId == peerId && record.globallyUniqueId == globallyUniqueId
                    && record.incoming && record.wasTemporary && Self.isRegularArchiveIdentifier(record.messageId)
            }
        }
    }

    public func interactionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        if let retained = self.temporaryInteractionMessage(id: id, liveMessage: liveMessage), retained.attributes.contains(where: { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }) { return retained }
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) {
            return liveMessage.id == id ? liveMessage : nil
        }
        let retained = self.deletedMessage(id: id) ?? (liveMessage == nil ? nil : self.snapshotForExpiredMessage(id: id))
        return Self.interactionMessage(id: id, liveMessage: liveMessage, retainedMessage: retained)
    }

    public static func interactionMessage(id: MessageId, liveMessage: Message?, retainedMessage: Message?) -> Message? {
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) { return liveMessage }
        if let retainedMessage, retainedMessage.id == id,
           retainedMessage.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) {
            return retainedMessage
        }
        return liveMessage
    }

    /// Read-only resolution for ASR. Unlike opening an expired row, this must
    /// not mark it expired, consume it, capture new bytes or change its lifetime.
    public func transcriptionMessage(id: MessageId, liveMessage: Message?) -> Message? {
        if let retained = self.temporaryInteractionMessage(id: id, liveMessage: liveMessage), retained.attributes.contains(where: { ($0 as? NagramiXArchivedMessageAttribute)?.isTemporary == true }) { return retained }
        guard liveMessage == nil || liveMessage?.id == id else { return nil }
        if let liveMessage, !liveMessage.media.contains(where: { $0 is TelegramMediaExpiredContent }) { return liveMessage }
        guard let record = self.state.with({ $0.records[Self.key(id)] }),
              record.deletedAt != nil || (liveMessage != nil && record.wasTemporary) else { return liveMessage }
        return self.renderDeletedRecord(record) ?? liveMessage
    }

    /// Store only ASR attributes on an already retained temporary voice or round video.
    /// All archive mutations (including clearAll) share this serial queue. A late
    /// recognizer can neither recreate a cleared record nor insert into Postbox.
    public func updateTranscriptionAttributes(id: MessageId, requireCompleteMedia: Bool = true, transform: @escaping (Message) -> [MessageAttribute]?) -> Signal<Bool, NoError> {
        return Signal { subscriber in
            self.queue.async {
                var updated = self.mutationState
                let key = Self.key(id)
                guard var record = updated.records[key],
                      let current = self.renderDeletedRecord(record, requireCompleteMedia: requireCompleteMedia), nagramiXCanTranscribeTemporaryMedia(current),
                      let attributes = transform(current) else {
                    subscriber.putNext(false); subscriber.putCompletion(); return
                }
                record.transcriptionAttributes = attributes.filter {
                    $0 is AudioTranscriptionMessageAttribute || $0 is DerivedDataMessageAttribute
                }.map(Self.encodedRootObject)
                updated.records[key] = record
                let saved = self.persist(updated)
                if saved { self.publishUpdate() }
                subscriber.putNext(saved); subscriber.putCompletion()
            }
            return EmptyDisposable
        }
    }

    /// Native Premium and its asynchronous update share the same durable local
    /// destination. A cleared/disabled record cannot be recreated by a late RPC.
    func retainTelegramTranscription(id: MessageId, attribute: AudioTranscriptionMessageAttribute) {
        guard attribute.error == nil else { return }
        let _ = self.updateTranscriptionAttributes(id: id, requireCompleteMedia: false, transform: { current in
            // A delayed initial pending response cannot replace completed text.
            if attribute.isPending, current.attributes.contains(where: {
                guard let saved = $0 as? AudioTranscriptionMessageAttribute else { return false }
                return saved.id == attribute.id && !saved.isPending && saved.error == nil && !saved.text.isEmpty
            }) { return nil }
            var attributes = current.attributes.filter { !($0 is AudioTranscriptionMessageAttribute) }
            attributes.append(attribute)
            return attributes
        }).startStandalone()
    }

    public func deletedMessage(id: MessageId) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        guard let record = self.state.with({ $0.records[Self.key(id)] }), record.deletedAt != nil,
              settings.showDeletedMessages || (settings.replayViewOnce && record.wasTemporary) else { return nil }
        return self.renderDeletedRecord(record)
    }

    public func snapshotForExpiredMessage(id: MessageId) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        guard let record = self.state.with({ $0.records[Self.key(id)] }), record.wasTemporary,
              (settings.showDeletedMessages && settings.saveTemporaryMessages) || (settings.replayViewOnce && record.wasTemporary) else { return nil }
        self.markTemporaryExpired(id: id, expiredAt: Int32(Date().timeIntervalSince1970))
        return self.renderDeletedRecord(record, requireCompleteMedia: false)
    }

    public func containsArchivedMessage(id: MessageId) -> Bool {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.saveTemporaryMessages else { return false }
        return self.state.with { state in
            guard let record = state.records[Self.key(id)], !record.wasTemporary || settings.saveTemporaryMessages else { return false }
            return record.deletedAt != nil || record.wasTemporary
        }
    }

    /// Deletion ownership must survive switching archive visibility off while a
    /// confirmation or undo is open. Unexpired/live temporary messages stay native.
    public func isLocallyDeletedMessage(id: MessageId) -> Bool {
        return self.state.with { $0.records[Self.key(id)]?.deletedAt != nil }
    }

    public func updateDeletedMessageText(id: MessageId, text: String) {
        self.queue.async { [weak self] in
            guard let self else { return }
            var updated = self.mutationState
            let key = Self.key(id)
            guard var record = updated.records[key], record.deletedAt != nil,
                  text != record.content.text, !text.isEmpty || !record.content.media.isEmpty else { return }
            let timestamp = Int32(Date().timeIntervalSince1970)
            NagramiXMessageRevision.appendIfChanged(NagramiXMessageRevision(text: record.content.text, entities: record.content.entities, timestamp: record.contentTimestamp ?? record.timestamp), to: &record.revisions)
            // Plain-text local editing must not retain invalid entity offsets.
            record.content = NagramiXArchivedContent(text: text, entities: [], media: record.content.media)
            record.contentTimestamp = timestamp
            updated.records[key] = record
            self.persist(updated, retryNow: true)
            self.publishUpdate()
        }
    }

    public func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?, limit: Int = 200) -> [Message] {
        let settings = NagramiXMessageArchiveSettings.current
        guard settings.showDeletedMessages || settings.replayViewOnce else {
            return []
        }
        let rawPeerId = peerId.toInt64()
        let records = self.state.with { state -> [NagramiXArchivedRecord] in
            state.records.values.filter { record in
                let visibleInArchive = settings.showDeletedMessages && (!record.wasTemporary || settings.saveTemporaryMessages)
                let visibleForReplay = settings.replayViewOnce && record.wasTemporary
                guard record.peerId == rawPeerId && record.deletedAt != nil && (threadId == nil || record.threadId == threadId), visibleInArchive || visibleForReplay else {
                    return false
                }
                let index = MessageIndex(id: record.messageId, timestamp: record.timestamp)
                if let minIndex, index < minIndex {
                    return false
                }
                if let maxIndex, index > maxIndex {
                    return false
                }
                return true
            }
            .sorted(by: { MessageIndex(id: $0.messageId, timestamp: $0.timestamp) < MessageIndex(id: $1.messageId, timestamp: $1.timestamp) })
            .suffix(max(1, limit))
            .map { $0 }
        }
        return records.compactMap { self.renderDeletedRecord($0, requireCompleteMedia: false) }.sorted(by: { $0.index < $1.index })
    }

    private func renderDeletedRecord(_ record: NagramiXArchivedRecord, requireCompleteMedia: Bool = true) -> Message? {
        let settings = NagramiXMessageArchiveSettings.current
        let visibleInArchive = settings.showDeletedMessages && (!record.wasTemporary || settings.saveTemporaryMessages)
        let visibleForReplay = settings.replayViewOnce && record.wasTemporary
        guard visibleInArchive || visibleForReplay else { return nil }
        var peers: [PeerId: Peer] = [:]
        for (_, data) in record.peerData {
            if let peer = Self.decodedRootObject(data) as? Peer {
                peers[peer.id] = peer
            }
        }
        let decodedMedia = record.content.media.compactMap { Self.decodedRootObject($0) as? Media }
        guard decodedMedia.count == record.content.media.count else { return nil }
        let media = decodedMedia.map(self.localMedia)
        // A retained view-once row must not claim to be replayable until all
        // primary bytes are available in the independent local store.
        if visibleForReplay && requireCompleteMedia {
            guard media.allSatisfy({ self.hasCompleteRetainedMedia($0) }) else { return nil }
        }
        let encodedContentAttributes = record.contentAttributes ?? []
        let decodedContentAttributes = encodedContentAttributes.compactMap { Self.decodedRootObject($0) as? MessageAttribute }
        guard decodedContentAttributes.count == encodedContentAttributes.count else { return nil }
        var attributes: [MessageAttribute] = decodedContentAttributes.map { attribute in
            if let rich = attribute as? RichTextMessageAttribute {
                return RichTextMessageAttribute(instantPage: self.localRichPage(rich.instantPage), fullInstantPage: rich.fullInstantPage.map(self.localRichPage))
            }
            return attribute
        }
        attributes.append(contentsOf: (record.transcriptionAttributes ?? []).compactMap {
            let attribute = Self.decodedRootObject($0)
            guard attribute is AudioTranscriptionMessageAttribute || attribute is DerivedDataMessageAttribute else { return nil }
            return attribute as? MessageAttribute
        })
        if !record.content.entities.isEmpty {
            attributes.append(TextEntitiesMessageAttribute(entities: record.content.entities))
        }
        attributes.append(NagramiXArchivedMessageAttribute(deletedAt: record.deletedAt ?? record.timestamp, revisions: record.revisions, isTemporary: record.wasTemporary, isViewOnceReplay: visibleForReplay))
        let flags: StoreMessageFlags = record.incoming ? [.Incoming] : []
        // Classify the retained media with the same tags as a native message.
        // Expiry attributes belong to the consumed original, not this local copy.
        let (tags, globalTags) = tagsForStoreMessage(incoming: record.incoming, attributes: attributes, media: media, textEntities: record.content.entities, isPinned: false)
        let storeMessage = StoreMessage(
            id: .Id(record.messageId),
            customStableId: nil,
            globallyUniqueId: record.globallyUniqueId,
            groupingKey: record.groupingKey,
            threadId: record.threadId,
            timestamp: record.timestamp,
            flags: flags,
            tags: tags,
            globalTags: globalTags,
            localTags: [],
            forwardInfo: record.forwardInfo?.storeInfo,
            authorId: record.authorId.map { PeerId($0) },
            text: record.content.text,
            attributes: attributes,
            media: media
        )
        guard let rendered = locallyRenderedMessage(message: storeMessage, peers: peers) else { return nil }
        var retainedPeers = rendered.peers
        for (peerId, peer) in peers { retainedPeers[peerId] = peer }
        return Message(stableId: rendered.stableId, stableVersion: UInt32(clamping: record.revisions.count) &+ self.renderVersion.with { $0 }, id: rendered.id, globallyUniqueId: record.globallyUniqueId, groupingKey: record.groupingKey, groupInfo: rendered.groupInfo, threadId: rendered.threadId, timestamp: rendered.timestamp, flags: rendered.flags, tags: rendered.tags, globalTags: rendered.globalTags, localTags: rendered.localTags, customTags: rendered.customTags, forwardInfo: rendered.forwardInfo, author: rendered.author, text: rendered.text, attributes: rendered.attributes, media: rendered.media, peers: retainedPeers, associatedMessages: rendered.associatedMessages, associatedMessageIds: rendered.associatedMessageIds, associatedMedia: rendered.associatedMedia, associatedThreadInfo: rendered.associatedThreadInfo, associatedStories: rendered.associatedStories)
    }
}

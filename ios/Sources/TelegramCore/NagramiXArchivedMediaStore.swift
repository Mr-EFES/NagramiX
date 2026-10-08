import Foundation
import Postbox
import SwiftSignalKit

struct NagramiXArchiveMediaRequest {
    let reference: MediaResourceReference
    let temporary: Bool
    let primary: Bool
}

private struct NagramiXArchivedResourceFile: Codable {
    let fileName: String
    let localId: Int64
    let size: Int64
}

private final class NagramiXArchiveTransfer {
    let request: NagramiXArchiveMediaRequest
    let data = MetaDisposable()
    let fetch = MetaDisposable()
    let keep = MetaDisposable()

    init(request: NagramiXArchiveMediaRequest) {
        self.request = request
    }

    func dispose() {
        self.data.dispose()
        self.fetch.dispose()
        self.keep.dispose()
    }

    deinit {
        self.dispose()
    }
}

/// Owns complete files outside MediaBox's disposable cache. Mutable download
/// state is confined to the owning archive queue; rendering/removal use Atomic snapshots.
final class NagramiXArchivedMediaStore {
    private let mediaBox: MediaBox
    private let queue: Queue
    private let directory: String
    private let changed: () -> Void
    private let files = Atomic<[String: NagramiXArchivedResourceFile]>(value: [:])
    private let sequence = Atomic<Int64>(value: 0)
    private let pendingClear = Atomic<Int64>(value: 0)
    private let reservations = Atomic<[String: (Int64, Set<String>, Bool)]>(value: [:])
    private var owners: [String: [String: NagramiXArchiveMediaRequest]] = [:]
    private var requests: [String: NagramiXArchiveMediaRequest] = [:]
    private var active: [String: NagramiXArchiveTransfer] = [:]
    private var failures: [String: Int] = [:]
    private var retryAfter: [String: TimeInterval] = [:]
    private var retryTimer: SwiftSignalKit.Timer?
    private var enabled = false
    private var temporaryEnabled = false

    init(mediaBox: MediaBox, queue: Queue, basePath: String, changed: @escaping () -> Void) {
        self.mediaBox = mediaBox
        self.queue = queue
        self.directory = basePath + "/nagramix-message-media"
        self.changed = changed
    }

    deinit {
        self.retryTimer?.invalidate()
        self.active.removeAll()
    }

    private func filePath(_ file: NagramiXArchivedResourceFile) -> String? {
        guard file.size >= 0, file.localId > 0,
              file.fileName.hasSuffix(".bin"),
              UUID(uuidString: String(file.fileName.dropLast(4))) != nil else { return nil }
        return self.directory + "/" + file.fileName
    }

    private func existingPath(_ file: NagramiXArchivedResourceFile) -> String? {
        guard let path = self.filePath(file),
              let attributes = try? FileManager.default.attributesOfItem(atPath: path),
              attributes[.type] as? FileAttributeType == .typeRegular,
              (attributes[.size] as? NSNumber)?.int64Value == file.size else { return nil }
        return path
    }

    func load() {
        if let data = try? Data(contentsOf: URL(fileURLWithPath: self.directory + "/index.json")),
           let files = try? JSONDecoder().decode([String: NagramiXArchivedResourceFile].self, from: data) {
            _ = self.files.swap(files.filter { self.existingPath($0.value) != nil })
        }
    }

    func localResource(for resource: TelegramMediaResource) -> TelegramMediaResource {
        guard let file = self.files.with({ $0[resource.id.stringRepresentation] }),
              let path = self.existingPath(file) else { return resource }
        return LocalFileReferenceMediaResource(localFilePath: path, randomId: file.localId, isUniquelyReferencedTemporaryFile: false, size: file.size)
    }

    /// Reserve synchronously, before native deletion can remove a just-received
    /// resource. Tickets let a queued clear keep reservations made after it.
    func reserve(key: String, requests: [NagramiXArchiveMediaRequest]) -> Int64 {
        let ticket = self.sequence.modify { $0 + 1 }
        let ids = Set(requests.map { $0.reference.resource.id.stringRepresentation })
        _ = self.reservations.modify { current in
            var current = current
            current[key] = (ticket, ids, requests.contains(where: { $0.temporary }))
            return current
        }
        return ticket
    }

    func reserveRestored(key: String, requests: [NagramiXArchiveMediaRequest]) -> Int64? {
        let ticket = self.sequence.modify { $0 + 1 }
        let ids = Set(requests.map { $0.reference.resource.id.stringRepresentation })
        let result = self.reservations.modify { current in
            var current = current
            if current[key] == nil { current[key] = (ticket, ids, requests.contains(where: { $0.temporary })) }
            return current
        }
        return result[key]?.0 == ticket ? ticket : nil
    }

    func barrier(clearFiles: Bool = false) -> Int64 {
        let ticket = self.sequence.modify { $0 + 1 }
        if clearFiles { _ = self.pendingClear.modify { max($0, ticket) } }
        return ticket
    }

    func resourcesToRemove(_ resources: [MediaResourceId], includeTemporary: Bool) -> [MediaResourceId] {
        let reserved = self.reservations.with { values in
            Set(values.values.filter { !$0.2 || includeTemporary }.flatMap { $0.1 })
        }
        let files = self.files.with { $0 }
        let clearing = self.pendingClear.with { $0 != 0 }
        return resources.filter { id in
            if !reserved.contains(id.stringRepresentation) { return true }
            if clearing { return false }
            return files[id.stringRepresentation].flatMap(self.existingPath) != nil
        }
    }

    func retain(key: String, requests: [NagramiXArchiveMediaRequest], ticket: Int64) {
        guard self.reservations.with({ $0[key]?.0 }) == ticket else { return }
        self.owners[key] = Dictionary(uniqueKeysWithValues: requests.map { ($0.reference.resource.id.stringRepresentation, $0) })
        self.rebuildRequests()
        self.prune(removeStoredFiles: false)
        // Prioritize a new view-once attachment over a long ordinary download.
        let pendingTemporary = requests.contains { request in
            request.temporary && self.files.with { $0[request.reference.resource.id.stringRepresentation] }.flatMap(self.existingPath) == nil
        }
        if pendingTemporary, self.temporaryEnabled, self.active.count >= 2,
           let ordinary = self.active.first(where: { !$0.value.request.temporary }) {
            self.stop(id: ordinary.key)
        }
        self.pump()
    }

    func configure(enabled: Bool, temporaryEnabled: Bool) {
        self.enabled = enabled
        self.temporaryEnabled = temporaryEnabled
        self.failures.removeAll()
        self.retryAfter.removeAll()
        for id in Array(self.active.keys) where !enabled || (self.requests[id]?.temporary == true && !temporaryEnabled) {
            self.stop(id: id)
        }
        self.pump()
    }

    func remove(keys: Set<String>, before ticket: Int64) {
        for key in keys { self.owners.removeValue(forKey: key) }
        _ = self.reservations.modify { values in
            values.filter { !keys.contains($0.key) || $0.value.0 > ticket }
        }
        self.rebuildRequests()
        self.prune()
        self.pump()
    }

    func clear(before ticket: Int64) {
        self.retryTimer?.invalidate()
        self.retryTimer = nil
        for id in Array(self.active.keys) { self.stop(id: id) }
        self.owners.removeAll()
        self.requests.removeAll()
        self.failures.removeAll()
        self.retryAfter.removeAll()
        _ = self.reservations.modify { $0.filter { $0.value.0 > ticket } }
        let files = self.files.swap([:])
        self.removePlaybackCache(Array(files.values))
        try? FileManager.default.removeItem(atPath: self.directory)
        _ = self.pendingClear.modify { $0 == ticket ? 0 : $0 }
        self.changed()
    }

    private func persist(_ files: [String: NagramiXArchivedResourceFile]) throws {
        try FileManager.default.createDirectory(atPath: self.directory, withIntermediateDirectories: true)
        var url = URL(fileURLWithPath: self.directory)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? url.setResourceValues(values)
        #if os(iOS)
        try FileManager.default.setAttributes([.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication], ofItemAtPath: self.directory)
        #endif
        try JSONEncoder().encode(files).write(to: URL(fileURLWithPath: self.directory + "/index.json"), options: .atomic)
    }

    private func rebuildRequests() {
        var combined: [String: NagramiXArchiveMediaRequest] = [:]
        for resources in self.owners.values {
            for (id, request) in resources {
                if let previous = combined[id] {
                    combined[id] = NagramiXArchiveMediaRequest(reference: previous.temporary && !request.temporary ? request.reference : previous.reference, temporary: previous.temporary && request.temporary, primary: previous.primary || request.primary)
                } else {
                    combined[id] = request
                }
            }
        }
        self.requests = combined
    }

    private func prune(removeStoredFiles: Bool = true) {
        let used = Set(self.owners.values.flatMap { $0.keys }).union(self.reservations.with { Set($0.values.flatMap { $0.1 }) })
        for id in Array(self.active.keys) where self.requests[id] == nil {
            self.stop(id: id)
            self.failures.removeValue(forKey: id)
            self.retryAfter.removeValue(forKey: id)
        }
        guard removeStoredFiles else { return }
        let old = self.files.with { $0 }
        let removed = old.filter { !used.contains($0.key) }
        guard !removed.isEmpty else { return }
        let updated = old.filter { used.contains($0.key) }
        do {
            try self.persist(updated)
            _ = self.files.swap(updated)
            self.removePlaybackCache(Array(removed.values))
            for file in removed.values {
                if let path = self.filePath(file) { try? FileManager.default.removeItem(atPath: path) }
            }
        } catch {
            Logger.shared.log("NagramiXArchive", "Could not prune archived media")
        }
    }

    private func stop(id: String) {
        self.active.removeValue(forKey: id)?.dispose()
    }

    private func removePlaybackCache(_ files: [NagramiXArchivedResourceFile]) {
        let ids = files.compactMap { file -> MediaResourceId? in
            guard let path = self.filePath(file) else { return nil }
            return LocalFileReferenceMediaResource(localFilePath: path, randomId: file.localId, isUniquelyReferencedTemporaryFile: false, size: file.size).id
        }
        if !ids.isEmpty { let _ = self.mediaBox.removeCachedResources(ids, force: true).start() }
    }

    private func pump() {
        self.retryTimer?.invalidate()
        self.retryTimer = nil
        guard self.enabled else { return }
        let now = Date().timeIntervalSince1970
        let candidates = self.requests.filter { id, request in
            guard self.active[id] == nil, self.failures[id, default: 0] < 3,
                  !request.temporary || self.temporaryEnabled else { return false }
            return self.files.with({ $0[id] }).flatMap(self.existingPath) == nil
        }.sorted { lhs, rhs in
            if lhs.value.temporary != rhs.value.temporary { return lhs.value.temporary }
            if lhs.value.primary != rhs.value.primary { return lhs.value.primary }
            return lhs.key < rhs.key
        }
        for (id, request) in candidates where self.retryAfter[id, default: 0] <= now {
            guard self.active.count < 2 else { break }
            self.start(id: id, request: request)
        }
        if self.active.count < 2, let next = candidates.compactMap({ self.retryAfter[$0.key] }).filter({ $0 > now }).min() {
            let timer = SwiftSignalKit.Timer(timeout: max(1, next - now), repeat: false, completion: { [weak self] in self?.pump() }, queue: self.queue)
            self.retryTimer = timer
            timer.start()
        }
    }

    private func start(id: String, request: NagramiXArchiveMediaRequest) {
        let transfer = NagramiXArchiveTransfer(request: request)
        self.active[id] = transfer
        transfer.keep.set(self.mediaBox.keepResource(id: request.reference.resource.id).start())
        transfer.data.set((self.mediaBox.resourceData(request.reference.resource)
        |> filter { $0.complete }
        |> take(1)
        |> deliverOn(self.queue)).start(next: { [weak self, weak transfer] data in
            guard let self, let transfer, self.active[id] === transfer else { return }
            do {
                try self.copyComplete(data: data, id: id)
                self.stop(id: id)
                self.failures.removeValue(forKey: id)
                self.retryAfter.removeValue(forKey: id)
                self.changed()
                self.pump()
            } catch {
                self.failed(id: id, transfer: transfer)
            }
        }))
        if self.active[id] === transfer {
            transfer.fetch.set((fetchedMediaResource(mediaBox: self.mediaBox, userLocation: .other, userContentType: .other, reference: request.reference, reportResultStatus: true)
            |> deliverOn(self.queue)).start(error: { [weak self, weak transfer] _ in
                guard let self, let transfer else { return }
                self.failed(id: id, transfer: transfer)
            }))
        }
    }

    private func failed(id: String, transfer: NagramiXArchiveTransfer) {
        guard self.active[id] === transfer else { return }
        self.stop(id: id)
        self.failures[id, default: 0] += 1
        self.retryAfter[id] = Date().timeIntervalSince1970 + 30.0 * Double(self.failures[id, default: 1])
        self.pump()
    }

    private func copyComplete(data: MediaResourceData, id: String) throws {
        guard data.complete, data.offset == 0,
              let attributes = try? FileManager.default.attributesOfItem(atPath: data.path),
              attributes[.type] as? FileAttributeType == .typeRegular,
              (attributes[.size] as? NSNumber)?.int64Value == data.size else {
            throw NSError(domain: "org.nagramix.archive", code: 1)
        }
        try FileManager.default.createDirectory(atPath: self.directory, withIntermediateDirectories: true)
        let file = NagramiXArchivedResourceFile(fileName: UUID().uuidString.lowercased() + ".bin", localId: Int64.random(in: 1 ... Int64.max), size: data.size)
        let destination = self.directory + "/" + file.fileName
        // Copy files directly; never load a multi-gigabyte video into a Data buffer.
        do {
            try FileManager.default.copyItem(atPath: data.path, toPath: destination)
            var updated = self.files.with { $0 }
            let previous = updated[id]
            updated[id] = file
            try self.persist(updated)
            _ = self.files.swap(updated)
            if let previous, let path = self.filePath(previous) {
                self.removePlaybackCache([previous])
                try? FileManager.default.removeItem(atPath: path)
            }
        } catch {
            try? FileManager.default.removeItem(atPath: destination)
            throw error
        }
    }
}

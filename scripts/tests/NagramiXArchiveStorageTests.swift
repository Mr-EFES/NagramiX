// Appended to the real extracted archive members, so its private Codable model
// remains private and unchanged. No fake implementation of persist is tested.
@main struct ArchiveStorageTests {
    static func main() throws {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ description: String) {
            checks += 1; if !value() { fatalError("FAIL: " + description) }
        }
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        func id(_ value: Int32, peer: Int64 = 2) -> MessageId { MessageId(peerId: PeerId(peer), namespace: 0, id: value) }
        let archive = ArchiveHarness(path: folder.appendingPathComponent("archive.json").path)
        archive.mediaStore.beforeRemoval = { keys in
            let persisted = try! JSONDecoder().decode(NagramiXMessageArchiveState.self, from: Data(contentsOf: URL(fileURLWithPath: archive.path)))
            check(keys.isDisjoint(with: Set(persisted.records.keys)), "media removed only after metadata no longer references it")
        }
        archive.capture(id(1), text: "original"); Queue.drain()
        check(archive.records.count == 1 && archive.status == .ready, "capture commits memory only after successful real atomic IO")
        let firstBytes = try Data(contentsOf: URL(fileURLWithPath: archive.path))
        // Replace the directory by a regular file: a deterministic real write
        // error, without filling a disk or relying on chmod under root.
        archive.capture(id(2), text: "two"); Queue.drain()
        check(archive.records.count == 2, "second normal capture is durable")
        let durableBeforeFailure = try Data(contentsOf: URL(fileURLWithPath: archive.path))
        check(durableBeforeFailure != firstBytes, "second committed record actually reaches disk")
        let holding = folder.deletingLastPathComponent().appendingPathComponent(UUID().uuidString)
        func failWrites() throws { try FileManager.default.moveItem(at: folder, to: holding); try Data([0]).write(to: folder) }
        func restoreWrites() throws { try FileManager.default.removeItem(at: folder); try FileManager.default.moveItem(at: holding, to: folder) }
        try failWrites()
        archive.capture(id(3), text: "pending"); Queue.drain()
        check(archive.records.count == 2 && archive.dirtyCount == 3, "real filesystem failure keeps previous committed archive and latest dirty capture")
        check(archive.status == .failed(.writeFailed), "real write failure is visible instead of silent success")
        check(try! Data(contentsOf: holding.appendingPathComponent("archive.json")) == durableBeforeFailure, "failed write leaves last successful JSON byte-identical")
        archive.archiveServerDeletion(messageIds: [id(3)], deletedAt: 42); Queue.drain()
        check(archive.dirtyRecord(id(3))?.deletedAt == 42, "deletion merges into failed incoming snapshot")
        try restoreWrites(); SwiftSignalKit.Timer.fire()
        check(archive.records.count == 3 && archive.record(id(3))?.deletedAt == 42 && archive.status == .ready, "retry publishes latest capture plus deletion and clears error")
        let loaded = ArchiveHarness(path: archive.path); loaded.load()
        check(loaded.records.count == 3 && loaded.record(id(3))?.deletedAt == 42, "committed state survives actual JSON reload")
        try failWrites()
        archive.removeLocal(messageIds: [id(1)]); Queue.drain()
        check(archive.record(id(1)) != nil && archive.mediaStore.removed.isEmpty, "failed local deletion keeps visible committed record and media bytes")
        try restoreWrites(); SwiftSignalKit.Timer.fire()
        check(archive.record(id(1)) == nil && archive.mediaStore.removed.contains("2:0:1"), "successful deletion commits JSON before byte cleanup")
        try failWrites()
        archive.removeLocal(messageIds: [id(2)]); Queue.drain()
        archive.capture(id(2), text: "recaptured"); Queue.drain()
        try restoreWrites(); SwiftSignalKit.Timer.fire()
        check(archive.record(id(2))?.content.text == "recaptured" && !archive.mediaStore.removed.contains("2:0:2"), "recapture of the same key cancels obsolete deferred byte removal")
        try failWrites()
        archive.clearAll(); Queue.drain()
        check(archive.records.count == 2 && archive.mediaStore.clears == 0, "failed full clear preserves records, JSON and media")
        archive.capture(id(4), text: "after clear"); Queue.drain()
        try restoreWrites(); SwiftSignalKit.Timer.fire()
        check(archive.records.count == 1 && archive.record(id(4))?.content.text == "after clear", "capture after failed clear survives latest-snapshot retry")
        check(archive.mediaStore.clears == 0 && archive.mediaStore.retained.contains("2:0:4"), "deferred clear never deletes a newer capture's media")
        archive.clearAll(); Queue.drain()
        check(archive.records.isEmpty && archive.mediaStore.clears == 1 && FileManager.default.fileExists(atPath: archive.path), "successful clear stores durable empty JSON then clears media")
        let empty = ArchiveHarness(path: archive.path); empty.load()
        check(empty.records.isEmpty && empty.status == .ready, "full clear cannot resurrect old records after restart")
        archive.capture(id(5), text: "five"); archive.capture(id(6, peer: 3), text: "other account peer"); Queue.drain()
        archive.clear(peerId: PeerId(2)); Queue.drain()
        check(archive.record(id(5)) == nil && archive.record(id(6, peer: 3)) != nil, "peer clear preserves other peer")
        archive.capture(id(7), text: "temporary", temporary: true); Queue.drain()
        try failWrites()
        archive.markTemporaryExpired(id: id(7), expiredAt: 99); Queue.drain()
        check(archive.record(id(7))?.deletedAt == nil && archive.dirtyRecord(id(7))?.deletedAt == 99, "temporary expiration is not falsely published before persistence")
        try restoreWrites(); archive.retryPersistence(); Queue.drain()
        check(archive.record(id(7))?.deletedAt == 99, "explicit retry commits temporary expiration")
        archive.updateDeletedMessageText(id: id(7), text: "edited"); Queue.drain()
        check(archive.record(id(7))?.content.text == "edited" && archive.record(id(7))?.revisions.last?.text == "temporary", "local edit and revision persist together")
        try Data("invalid archive".utf8).write(to: URL(fileURLWithPath: archive.path))
        let corrupt = ArchiveHarness(path: archive.path); corrupt.load()
        check(corrupt.status == .failed(.unreadable), "unreadable archive is reported")
        corrupt.capture(id(8), text: "must not overwrite"); Queue.drain()
        check(String(data: try! Data(contentsOf: URL(fileURLWithPath: archive.path)), encoding: .utf8) == "invalid archive", "unreadable existing file is never replaced by an empty capture")
        corrupt.clearAll(); Queue.drain()
        check(corrupt.records.isEmpty && corrupt.status == .ready, "only explicit full reset may replace unreadable archive")
        let reset = try JSONDecoder().decode(NagramiXMessageArchiveState.self, from: Data(contentsOf: URL(fileURLWithPath: archive.path)))
        check(reset.records.isEmpty, "explicit reset is durable")
        print("PASS: \(checks) actual archive mutation/atomic IO/recovery checks")
    }
}

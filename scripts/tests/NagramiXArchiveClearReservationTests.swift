import Foundation

// The complete production MediaStore is compiled above this test. Only the
// Postbox/MediaBox boundary is substituted; copying/index IO/unlinking are real.
@main struct ArchiveClearReservationTests {
    static func main() throws {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ message: String) {
            checks += 1
            precondition(condition(), message)
        }
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        func fixture(_ name: String) -> (NagramiXArchivedMediaStore, MediaBox, Queue, String) {
            let base = root.appendingPathComponent(name).path
            let box = MediaBox(base + "/cache"), queue = Queue()
            let store = NagramiXArchivedMediaStore(mediaBox: box, queue: queue, basePath: base, changed: {})
            store.configure(enabled: true, temporaryEnabled: true)
            return (store, box, queue, base)
        }
        func seed(_ store: NagramiXArchivedMediaStore, _ box: MediaBox, _ queue: Queue, _ base: String,
                  key: String, resource: TestResource, temporary: Bool = false) throws -> (Int64, LocalFileReferenceMediaResource) {
            let path = base + "/source-" + resource.id.stringRepresentation
            try Data([1, 2, 3, 4]).write(to: URL(fileURLWithPath: path))
            box.sources[resource.id] = path
            let request = NagramiXArchiveMediaRequest(reference: MediaResourceReference(resource: resource, incoming: true), temporary: temporary, primary: true)
            let ticket = store.reserve(key: key, requests: [request])
            store.retain(key: key, requests: [request], ticket: ticket); queue.drain()
            guard let local = store.localResource(for: resource) as? LocalFileReferenceMediaResource else { fatalError("real media copy did not complete") }
            return (ticket, local)
        }
        for temporary in [false, true] {
            let (store, box, queue, base) = fixture("shared-\(temporary)")
            let resource = TestResource("reused"), obsolete = TestResource("obsolete")
            let (_, retained) = try seed(store, box, queue, base, key: "old", resource: resource, temporary: temporary)
            let (_, removed) = try seed(store, box, queue, base, key: "obsolete", resource: obsolete)
            let clear = store.barrier()
            let requests = [NagramiXArchiveMediaRequest(reference: MediaResourceReference(resource: resource, incoming: true), temporary: temporary, primary: true)]
            let newer = store.reserve(key: "new", requests: requests)
            check(newer > clear, "new capture owns a later ticket")
            // Native cache can be deleted because the retained file is complete.
            let removable = store.resourcesToRemove([resource.id], includeTemporary: true)
            _ = box.removeCachedResources(removable, force: true).start()
            check(!FileManager.default.fileExists(atPath: box.sources[resource.id]!), "original source is unavailable")
            store.clear(before: clear)
            check(store.testReservation("new") == newer, "clear retains newer reservation")
            check(FileManager.default.fileExists(atPath: retained.localFilePath), "clear must retain bytes reused by newer capture")
            check(!FileManager.default.fileExists(atPath: removed.localFilePath), "clear removes unrelated archived bytes")
            check(box.completedResourcePath(removed) == nil, "obsolete playback cache is removed")
            check(box.completedResourcePath(retained) != nil, "playback cache for retained bytes survives")
            store.retain(key: "new", requests: requests, ticket: newer); queue.drain()
            check((store.localResource(for: resource) as? LocalFileReferenceMediaResource)?.localFilePath == retained.localFilePath,
                  "queued retain reuses the same full file with original gone")
            let reopened = NagramiXArchivedMediaStore(mediaBox: box, queue: queue, basePath: base, changed: {})
            reopened.load()
            check((reopened.localResource(for: resource) as? LocalFileReferenceMediaResource)?.localFilePath == retained.localFilePath,
                  "filtered index survives reopen")
            check(reopened.localResource(for: obsolete).id == obsolete.id, "old entry cannot resurrect from index")
            let lastClear = store.barrier()
            store.clear(before: lastClear)
            check(!FileManager.default.fileExists(atPath: retained.localFilePath), "later explicit clear removes the formerly protected file")
            check(store.testFilesEmpty && store.testReservationsEmpty, "later clear leaves empty index/reservations")
        }
        do {
            let (store, box, queue, base) = fixture("new-owner")
            let resource = TestResource("owned")
            let (_, retained) = try seed(store, box, queue, base, key: "same-key", resource: resource)
            let old = store.barrier()
            let requests = [NagramiXArchiveMediaRequest(reference: MediaResourceReference(resource: resource, incoming: true), temporary: false, primary: true)]
            let ticket = store.reserve(key: "same-key", requests: requests)
            store.retain(key: "same-key", requests: requests, ticket: ticket)
            store.remove(keys: ["same-key"], before: old)
            check(store.testHasOwner("same-key") && store.testHasRequest(resource.id.stringRepresentation),
                  "stale per-key cleanup must retain newer download ownership")
            store.clear(before: old)
            check(store.testHasOwner("same-key") && FileManager.default.fileExists(atPath: retained.localFilePath),
                  "stale full clear also retains newer owners")
        }
        do {
            let (store, box, queue, base) = fixture("index-failure")
            let resource = TestResource("keep-on-failure")
            let (_, retained) = try seed(store, box, queue, base, key: "old", resource: resource)
            let index = store.testDirectory + "/index.json"
            let oldIndex = try Data(contentsOf: URL(fileURLWithPath: index))
            let saved = store.testDirectory + "-saved"
            try FileManager.default.moveItem(atPath: store.testDirectory, toPath: saved)
            // Real IO failure: the directory's path is occupied by a file.
            try Data([9]).write(to: URL(fileURLWithPath: store.testDirectory))
            store.clear(before: store.barrier())
            check(!store.testFilesEmpty, "failed index commit must not publish an empty file map")
            check(FileManager.default.fileExists(atPath: saved + "/" + URL(fileURLWithPath: retained.localFilePath).lastPathComponent),
                  "failed index commit must not unlink retained bytes")
            try FileManager.default.removeItem(atPath: store.testDirectory)
            try FileManager.default.moveItem(atPath: saved, toPath: store.testDirectory)
            let restoredIndex = try Data(contentsOf: URL(fileURLWithPath: index))
            check(restoredIndex == oldIndex, "previous index is unchanged on IO failure")
            store.clear(before: store.barrier())
            check(store.testFilesEmpty && !FileManager.default.fileExists(atPath: retained.localFilePath), "subsequent clear retries cleanup successfully")
        }
        do {
            let (store, box, queue, base) = fixture("atomic-prune")
            let resource = TestResource("old")
            _ = try seed(store, box, queue, base, key: "old", resource: resource)
            let began = DispatchSemaphore(value: 0), finished = DispatchSemaphore(value: 0)
            var blocked = false
            box.beforeRemove = {
                box.beforeRemove = nil
                DispatchQueue.global().async {
                    began.signal()
                    _ = store.reserve(key: "concurrent", requests: [])
                    finished.signal()
                }
                precondition(began.wait(timeout: .now() + 2) == .success)
                blocked = finished.wait(timeout: .now() + 0.05) == .timedOut
            }
            store.clear(before: store.barrier())
            check(blocked, "reserve cannot publish while real pruning is between index commit and unlink")
            check(finished.wait(timeout: .now() + 2) == .success, "reservation resumes after pruning releases the lock")
            check(store.testReservation("concurrent") != nil, "concurrent later reservation remains published")
        }
        print("PASS: \(checks) real media-store clear/reservation/index/cache/IO/concurrency checks")
    }
}

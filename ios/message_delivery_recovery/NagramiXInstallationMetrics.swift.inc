import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

// A pending event belongs to this installation, across all Telegram accounts.
actor NagramiXInstallationMetrics {
    private enum State: String, Codable {
        case opened
        case authorized
    }

    private struct Record: Codable, Equatable {
        let id: UUID
        var observed: State
        var acknowledged: State?
    }

    private final class NoRedirects: NSObject, URLSessionTaskDelegate {
        func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
            completionHandler(nil)
        }
    }

    private let endpoint: URL
    private let directory: URL
    private let session: URLSession
    private var record: Record?
    private var sawAuthorizedAccount = false
    private var sending = false

    init(endpoint: URL = URL(string: "https://nagramix-bot.mr-efes.workers.dev/v1/installation")!, directory: URL? = nil, session: URLSession? = nil) {
        self.endpoint = endpoint
        self.directory = directory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("NagramiXInstallationMetrics", isDirectory: true)
        if let session {
            self.session = session
        } else {
            let config = URLSessionConfiguration.ephemeral
            config.httpShouldSetCookies = false
            config.urlCredentialStorage = nil
            config.urlCache = nil
            config.timeoutIntervalForRequest = 15
            config.timeoutIntervalForResource = 60
            #if os(iOS)
            config.waitsForConnectivity = true
            #endif
            self.session = URLSession(configuration: config, delegate: NoRedirects(), delegateQueue: nil)
        }
    }

    private var file: URL { directory.appendingPathComponent("installation.json") }

    private var backup: URL { directory.appendingPathComponent("installation-backup.json") }

    private func read(_ url: URL) throws -> Data? {
        do {
            return try Data(contentsOf: url)
        } catch let error as CocoaError where error.code == .fileReadNoSuchFile {
            return nil
        }
    }

    // Decode the identifier independently of the two progress fields in older files.
    private struct RecoverableRecord: Decodable {
        let id: UUID
        let observed: State?
        let acknowledged: State?

        private enum CodingKeys: CodingKey { case id, observed, acknowledged }

        init(from decoder: Decoder) throws {
            let values = try decoder.container(keyedBy: CodingKeys.self)
            id = try values.decode(UUID.self, forKey: .id)
            observed = try? values.decode(State.self, forKey: .observed)
            acknowledged = try? values.decode(State.self, forKey: .acknowledged)
        }
    }

    private func recover(_ data: Data) -> RecoverableRecord? {
        let decoder = JSONDecoder()
        if let stored = try? decoder.decode(RecoverableRecord.self, from: data) { return stored }
        // A truncated legacy JSON may still contain its complete top-level UUID.
        guard data.count <= 1024 else { return nil }
        let separators = data.indices.reversed().filter { data[$0] == 0x2c }.prefix(3)
        for end in [data.endIndex] + separators {
            var prefix = Data(data[..<end])
            prefix.append(0x7d)
            if let stored = try? decoder.decode(RecoverableRecord.self, from: prefix) { return stored }
        }
        return nil
    }

    private func load() throws -> Record {
        if let record { return record }
        var folder = directory
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        #if os(iOS)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try folder.setResourceValues(values)
        #endif
        let primaryData = try read(file)
        let backupData = try read(backup)
        let decoder = JSONDecoder()
        let candidates = [primaryData, backupData].compactMap { data in
            data.flatMap(recover)
        }
        let id: UUID
        if let known = candidates.first?.id {
            id = known
        } else if primaryData == nil && backupData == nil {
            id = UUID()
        } else {
            // An unreadable legacy identity may already be registered on the server.
            throw CocoaError(.fileReadCorruptFile)
        }
        let sameInstallation = candidates.filter { $0.id == id }
        let acknowledgements = sameInstallation.compactMap(\.acknowledged)
        let acknowledged: State? = acknowledgements.contains(.authorized) ? .authorized : acknowledgements.first
        let authorized = sawAuthorizedAccount || acknowledged == .authorized || sameInstallation.contains { $0.observed == .authorized }
        let current = Record(id: id, observed: authorized ? .authorized : .opened, acknowledged: acknowledged)
        if [primaryData, backupData].contains(where: { data in
            guard let data, let stored = try? decoder.decode(Record.self, from: data) else { return true }
            return stored != current
        }) {
            try save(current)
        } else {
            record = current
        }
        return current
    }

    private func save(_ value: Record) throws {
        let data = try JSONEncoder().encode(value)
        try data.write(to: backup, options: .atomic)
        try data.write(to: file, options: .atomic)
        record = value
    }

    func observe(isAuthorized: Bool) async {
        if isAuthorized { sawAuthorizedAccount = true }
        do {
            var current = try load()
            if sawAuthorizedAccount && current.observed == .opened {
                current.observed = .authorized
                try save(current)
            }
            guard !sending, current.observed != current.acknowledged else { return }
            sending = true
            defer { sending = false }
            // A successful login can arrive while the first open is in flight.
            while let pending = record, pending.observed != pending.acknowledged {
                var request = URLRequest(url: endpoint)
                request.httpMethod = "PUT"
                request.setValue(pending.id.uuidString.lowercased(), forHTTPHeaderField: "X-Installation-ID")
                request.setValue(pending.observed.rawValue, forHTTPHeaderField: "X-Installation-State")
                let (_, response) = try await session.data(for: request)
                guard (response as? HTTPURLResponse)?.statusCode == 204, var latest = record else { return }
                latest.acknowledged = pending.observed
                try save(latest)
            }
        } catch {
            // Keep the pending state. Returning to the foreground retries it.
        }
    }
}

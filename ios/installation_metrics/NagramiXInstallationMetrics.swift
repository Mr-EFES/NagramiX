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

    private struct Record: Codable {
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

    private func load() throws -> Record {
        if let record { return record }
        var folder = directory
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        #if os(iOS)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try folder.setResourceValues(values)
        #endif
        do {
            let stored = try JSONDecoder().decode(Record.self, from: Data(contentsOf: file))
            record = stored
            return stored
        } catch let error as CocoaError where error.code == .fileReadNoSuchFile {
            let fresh = Record(id: UUID(), observed: sawAuthorizedAccount ? .authorized : .opened, acknowledged: nil)
            try save(fresh)
            return fresh
        }
    }

    private func save(_ value: Record) throws {
        try JSONEncoder().encode(value).write(to: file, options: .atomic)
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

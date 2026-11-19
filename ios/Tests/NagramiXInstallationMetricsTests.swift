import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

private final class Stub: URLProtocol {
    // URLSession calls startLoading on its queue. The async tests also read this state.
    private static let lock = NSLock()
    private static var events: [(UUID, String)] = []
    private static var status = 204
    private static var holdNext = false
    private static var held: Stub?

    static func received() -> [(UUID, String)] {
        lock.lock()
        defer { lock.unlock() }
        return events
    }

    static func reply(with status: Int) {
        lock.lock()
        defer { lock.unlock() }
        self.status = status
    }

    static func holdNextRequest() {
        lock.lock()
        defer { lock.unlock() }
        holdNext = true
    }

    static func isHolding() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return held != nil
    }

    static func releaseHeldRequest() {
        lock.lock()
        let request = held
        held = nil
        lock.unlock()
        precondition(request != nil)
        request?.finish(status: 204)
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        precondition(request.url?.absoluteString == "https://local.invalid/v1/installation")
        precondition(request.httpMethod == "PUT" && request.httpBody == nil)
        let id = UUID(uuidString: request.value(forHTTPHeaderField: "X-Installation-ID")!)!
        let state = request.value(forHTTPHeaderField: "X-Installation-State")!
        precondition(id.uuid.6 >> 4 == 4)
        Self.lock.lock()
        Self.events.append((id, state))
        let code = Self.status
        let shouldHold = Self.holdNext
        if shouldHold {
            Self.held = self
            Self.holdNext = false
        }
        Self.lock.unlock()
        if !shouldHold { finish(status: code) }
    }

    private func finish(status: Int) {
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@main struct InstallationMetricsTests {
    static func main() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [Stub.self]
        let session = URLSession(configuration: config)
        defer { session.invalidateAndCancel() }
        func install(_ name: String) -> NagramiXInstallationMetrics {
            NagramiXInstallationMetrics(endpoint: URL(string: "https://local.invalid/v1/installation")!,
                                        directory: folder.appendingPathComponent(name), session: session)
        }
        let first = install("first")
        Stub.holdNextRequest()
        let opening = Task { await first.observe(isAuthorized: false) }
        for _ in 0..<1000 {
            if Stub.isHolding() { break }
            try await Task.sleep(nanoseconds: 2_000_000)
        }
        precondition(Stub.isHolding())
        await first.observe(isAuthorized: true)
        Stub.releaseHeldRequest()
        await opening.value
        await first.observe(isAuthorized: true)
        await install("first").observe(isAuthorized: false)
        let received = Stub.received()
        precondition(received.map { $0.1 } == ["opened", "authorized"] && received[0].0 == received[1].0)

        // Upgrade with a restored account. The Worker is unavailable until a later launch.
        Stub.reply(with: 503)
        await install("updated").observe(isAuthorized: true)
        Stub.reply(with: 204)
        let updated = install("updated")
        await updated.observe(isAuthorized: false)
        await updated.observe(isAuthorized: true)
        await install("updated").observe(isAuthorized: false)
        let retried = Stub.received()
        precondition(retried.map { $0.1 } == ["opened", "authorized", "authorized", "authorized"])
        precondition(retried[2].0 == retried[3].0 && retried[2].0 != received[0].0)

        let damaged = folder.appendingPathComponent("damaged")
        try FileManager.default.createDirectory(at: damaged, withIntermediateDirectories: true)
        try Data("incomplete".utf8).write(to: damaged.appendingPathComponent("installation.json"))
        await install("damaged").observe(isAuthorized: false)
        precondition(Stub.received().count == 4)

        try FileManager.default.removeItem(at: folder.appendingPathComponent("first"))
        await install("first").observe(isAuthorized: false)
        let final = Stub.received()
        precondition(final.count == 5 && final[4].1 == "opened" && Set(final.map { $0.0 }).count == 3)
        print("Installation metrics passed: first launch, concurrent login, restart, restored session, retry and reinstall.")
    }
}

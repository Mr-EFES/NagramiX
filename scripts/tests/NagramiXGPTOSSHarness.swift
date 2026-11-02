import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

final class GPTOSSTestClock {
    private let lock = NSLock()
    private var value = Date(timeIntervalSince1970: 1000)
    func now() -> Date { lock.lock(); defer { lock.unlock() }; return value }
    func advance(_ seconds: TimeInterval) {
        lock.lock(); value = value.addingTimeInterval(seconds); lock.unlock()
        NotificationCenter.default.post(name: NagramiXTranslationSettings.changed, object: nil)
    }
}

final class GPTOSSHTTP: URLProtocol {
    static let lock = NSLock()
    private static var history: [URLRequest] = []
    static var handler: (URLRequest) -> (Int, Data, [String: String], TimeInterval) = { _ in (500, Data(), [:], 0) }
    private let state = NSLock()
    private var stopped = false
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.lock.lock(); Self.history.append(request); let handler = Self.handler; Self.lock.unlock()
        let response = handler(request)
        DispatchQueue.global().asyncAfter(deadline: .now() + response.3) {
            self.state.lock(); defer { self.state.unlock() }
            guard !self.stopped else { return }
            self.client?.urlProtocol(self, didReceive: HTTPURLResponse(url: self.request.url!, statusCode: response.0, httpVersion: nil, headerFields: response.2)!, cacheStoragePolicy: .notAllowed)
            self.client?.urlProtocol(self, didLoad: response.1); self.client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { state.lock(); stopped = true; state.unlock() }
    static func reset(_ handler: @escaping (URLRequest) -> (Int, Data, [String: String], TimeInterval)) {
        lock.lock(); history = []; self.handler = handler; lock.unlock()
    }
    static var requests: [URLRequest] { lock.lock(); defer { lock.unlock() }; return history }
    static func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral; config.protocolClasses = [GPTOSSHTTP.self]
        return URLSession(configuration: config)
    }
    static func response(_ texts: [String], model: String = "gpt-oss-20b", finish: String = "stop") -> Data {
        let payload = try! JSONSerialization.data(withJSONObject: ["translations": texts])
        return try! JSONSerialization.data(withJSONObject: ["model":model,"choices":[["finish_reason":finish,"message":["content":String(data: payload, encoding: .utf8)!, "reasoning":"never show this"]]]])
    }
}

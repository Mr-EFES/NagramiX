import Foundation
import FoundationNetworking

private final class MockAudioHTTP: URLProtocol {
    static let lock = NSLock()
    static var count = 0
    static var status = 200
    static var delay: Double = 0
    static var requests: [URLRequest] = []
    private var stopped = false
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.lock.lock(); Self.count += 1; Self.requests.append(self.request); let status = Self.status; let delay = Self.delay; Self.lock.unlock()
        DispatchQueue.global().asyncAfter(deadline: .now() + delay) {
            Self.lock.lock(); let stopped = self.stopped; Self.lock.unlock(); guard !stopped else { return }
            let response = HTTPURLResponse(url:self.request.url!,statusCode:status,httpVersion:nil,headerFields:["Retry-After":"30"])!
            self.client?.urlProtocol(self,didReceive:response,cacheStoragePolicy:.notAllowed)
            self.client?.urlProtocol(self,didLoad:Data("{\"text\":\"Привет\"}".utf8)); self.client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { Self.lock.lock(); self.stopped = true; Self.lock.unlock() }
}
private var checks = 0
private func check(_ value: @autoclosure () -> Bool,_ label:String) { checks += 1; if !value() { fatalError(label) } }
@main struct TranscriptionHTTPTests {
    static func main() {
        let sessionConfig = URLSessionConfiguration.ephemeral; sessionConfig.protocolClasses = [MockAudioHTTP.self]
        let client = NagramiXTranscriptionCloud(session:URLSession(configuration:sessionConfig))
        var config = NagramiXTranscriptionConfiguration(); config.provider = .groq; config.enabled = true
        func call(_ config:NagramiXTranscriptionConfiguration, key:String="owned", token:NagramiXTranscriptionCancellation=NagramiXTranscriptionCancellation()) -> Result<String,NagramiXTranscriptionFailure> {
            let semaphore = DispatchSemaphore(value:0); var answer:Result<String,NagramiXTranscriptionFailure>?
            client.transcribe(configuration:config,key:key,audio:Data([1,2,3]),cancellation:token) { answer=$0;semaphore.signal() }
            check(semaphore.wait(timeout:.now()+3) == .success,"HTTP callback");return answer!
        }
        if case .failure(.cloudPermission) = call(config) {} else { fatalError("No consent") }
        check(MockAudioHTTP.count==0,"No network without consent")
        config.cloudAllowed["groq"] = true
        if case .failure(.missingKey) = call(config,key:"") {} else { fatalError("No key") }
        check(MockAudioHTTP.count==0,"No network without key")
        if case .success("Привет") = call(config) {} else { fatalError("HTTP result") }
        check(MockAudioHTTP.count==1,"Exactly one request")
        check(MockAudioHTTP.requests[0].url!.host=="api.groq.com","No substituted provider")
        MockAudioHTTP.status=429
        if case .failure(.quota) = call(config) {} else { fatalError("Quota") }
        let count=MockAudioHTTP.count
        if case .failure(.quota) = call(config) {} else { fatalError("Quota cooldown") }
        check(MockAudioHTTP.count==count,"Retry-After prevents immediate quota retry")
        config.provider = .chatgpt;config.cloudAllowed["chatgpt"] = true; MockAudioHTTP.status=401
        if case .failure(.authorization) = call(config) {} else { fatalError("Bad key") }
        check(MockAudioHTTP.requests.last!.url!.host=="api.openai.com","No Groq key/route reuse")
        MockAudioHTTP.status=200;MockAudioHTTP.delay=0.5
        let token=NagramiXTranscriptionCancellation();let semaphore=DispatchSemaphore(value:0)
        client.transcribe(configuration:config,key:"owned",audio:Data([1]),cancellation:token) { result in
            if case .failure(.cancelled)=result { semaphore.signal() } else { fatalError("Late success after cancel") }
        }
        token.cancel(); check(semaphore.wait(timeout:.now()+3) == .success,"In-flight cancellation")
        let cancelled=NagramiXTranscriptionCancellation();cancelled.cancel();let before=MockAudioHTTP.count
        if case .failure(.cancelled)=call(config,token:cancelled) {} else { fatalError("Pre-cancel") }
        check(MockAudioHTTP.count==before,"No task after pre-cancel")
        print("PASS: \(checks) actual cloud client / mocked HTTP checks")
    }
}

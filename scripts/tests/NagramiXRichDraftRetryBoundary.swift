import Foundation

// Only scheduling and Telegram IO are boundaries. Signal, subscribers,
// disposables, atomics, retry, catch, mapToSignal and take use pinned sources.
struct DispatchTime {
    let seconds: Double
    static func now() -> DispatchTime { DispatchTime(seconds: Scheduler.now) }
    static func + (left: DispatchTime, right: Double) -> DispatchTime { DispatchTime(seconds: left.seconds + right) }
}
enum Scheduler {
    static var now = 0.0
    static var tasks: [(Double, () -> Void)] = []
    static var delays: [Double] = []
    static func advance(_ seconds: Double) {
        let target = now + seconds
        var iterations = 0
        while let next = tasks.indices.filter({ tasks[$0].0 <= target }).min(by: { tasks[$0].0 < tasks[$1].0 }) {
            let task = tasks.remove(at: next)
            now = task.0; task.1(); iterations += 1
            precondition(iterations < 1000, "unbounded immediate retry")
        }
        now = target
    }
}
public final class TestDispatchQueue {
    func asyncAfter(deadline: DispatchTime, execute: @escaping () -> Void) {
        Scheduler.delays.append(deadline.seconds - Scheduler.now)
        Scheduler.tasks.append((deadline.seconds, execute))
    }
}
public final class Queue {
    let queue = TestDispatchQueue()
    public static func concurrentDefaultQueue() -> Queue { Queue() }
}
func delay<T,E>(_ seconds: Double, queue: Queue) -> (Signal<T,E>) -> Signal<T,E> { { $0 } }

enum Api {
    struct InputRichMessage: Equatable { var ids: [Int]; var blocks: [String] }
    struct MessageEntity: Equatable { let id: Int }
    struct InputReplyTo: Equatable { let id: Int }
    struct InputPeer: Equatable { let id: Int }
    enum Bool { case boolTrue, boolFalse }
    struct SaveDraft {
        var flags: Int32
        var replyTo: InputReplyTo?
        var peer: InputPeer
        var message: String
        var entities: [MessageEntity]
        var suggestedPost: Int?
        var richMessage: InputRichMessage?
    }
    enum functions { enum messages {
        static func saveDraft(flags: Int32, replyTo: InputReplyTo?, peer: InputPeer, message: String, entities: [MessageEntity], media: Int?, effect: Int?, suggestedPost: Int?, richMessage: InputRichMessage?) -> SaveDraft {
            SaveDraft(flags: flags, replyTo: replyTo, peer: peer, message: message, entities: entities, suggestedPost: suggestedPost, richMessage: richMessage)
        }
    } }
}
enum MTRpcError { case unavailable }
final class Network {
    var requests: [Api.SaveDraft] = []
    var saveFails = false
    func request(_ draft: Api.SaveDraft) -> Signal<Api.Bool,MTRpcError> {
        Signal { subscriber in
            self.requests.append(draft)
            if self.saveFails { subscriber.putError(.unavailable) }
            else { subscriber.putNext(.boolTrue); subscriber.putCompletion() }
            return EmptyDisposable
        }
    }
}
struct PeerId { var namespace: Int32 = 0 }
enum Namespaces { enum Peer { static let SecretChat: Int32 = 3 } }
final class Postbox {}
final class AccountAuxiliaryMethods {}
final class MessageMediaPreuploadManager {}
struct RichTextMessageAttribute {
    struct Page { var rawMedia: [Int]; var blocks: [String] }
    var instantPage: Page
    func apiInputRichMessage() -> Api.InputRichMessage { .init(ids: [], blocks: instantPage.blocks) }
}
enum PendingMessageUploadError { case generic }
enum Content { case richMessage(Api.InputRichMessage), other }
struct UploadedContent { var content: Content }
enum UploadResult { case progress(Float), content(UploadedContent) }
enum UploadControl {
    static var attempts = 0
    static var failures = 0
    static var invalidContent = false
    static func reset(_ failures: Int = 0) { attempts = 0; self.failures = failures; invalidContent = false }
}
func richMessageContentToUpload(network: Network, postbox: Postbox, auxiliaryMethods: AccountAuxiliaryMethods, messageMediaPreuploadManager: MessageMediaPreuploadManager, forceReupload: Bool, peerId: PeerId, instantPage: RichTextMessageAttribute.Page) -> Signal<UploadResult,PendingMessageUploadError> {
    Signal { subscriber in
        UploadControl.attempts += 1
        if UploadControl.attempts <= UploadControl.failures { subscriber.putError(.generic) }
        else {
            subscriber.putNext(.progress(0.5))
            subscriber.putNext(.content(UploadedContent(content: UploadControl.invalidContent ? .other : .richMessage(.init(ids: instantPage.rawMedia, blocks: instantPage.blocks)))))
            subscriber.putCompletion()
        }
        return EmptyDisposable
    }
}
enum RequestEditMessageInternalError { enum Code { case generic }; case error(Code) }

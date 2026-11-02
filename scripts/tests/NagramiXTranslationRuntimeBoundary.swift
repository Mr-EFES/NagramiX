// Only the Apple ML, SwiftSignalKit and Postbox delivery/storage boundaries are
// replaced here. The entire production Runtime.swift is compiled unchanged
// except imports/access modifiers. These tests do not run Apple frameworks.
import Foundation

enum NoError: Error {}
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    let action: () -> Void
    var disposed = false
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { if !disposed { disposed = true; action() } }
}
let EmptyDisposable: Disposable = ActionDisposable({})
final class MetaDisposable: Disposable {
    private var value: Disposable?
    private var disposed = false
    func set(_ value: Disposable?) { self.value?.dispose(); self.value = value; if disposed { value?.dispose() } }
    func dispose() { self.disposed = true; self.value?.dispose(); self.value = nil }
}
final class Subscriber<T,E> {
    var disposed = false
    let next: (T) -> Void, error: (E) -> Void, completed: () -> Void
    init(next: @escaping (T) -> Void, error: @escaping (E) -> Void, completed: @escaping () -> Void) { self.next = next; self.error = error; self.completed = completed }
    func putNext(_ value: T) { if !disposed { next(value) } }
    func putError(_ value: E) { if !disposed { disposed = true; error(value) } }
    func putCompletion() { if !disposed { disposed = true; completed() } }
}
final class Signal<T,E> {
    let generator: (Subscriber<T,E>) -> Disposable
    init(_ generator: @escaping (Subscriber<T,E>) -> Disposable) { self.generator = generator }
    static func single(_ value: T) -> Signal<T,E> { Signal { s in s.putNext(value); s.putCompletion(); return EmptyDisposable } }
    static func complete() -> Signal<T,E> { Signal { s in s.putCompletion(); return EmptyDisposable } }
    static func fail(_ error: E) -> Signal<T,E> { Signal { s in s.putError(error); return EmptyDisposable } }
    func start(next: @escaping (T) -> Void = { _ in }, error: @escaping (E) -> Void = { _ in }, completed: @escaping () -> Void = {}) -> Disposable {
        let subscriber = Subscriber(next: next, error: error, completed: completed)
        let disposable = generator(subscriber)
        return ActionDisposable { subscriber.disposed = true; disposable.dispose() }
    }
    func startStandalone(completed: @escaping () -> Void = {}) -> Disposable { start(completed: completed) }
}
precedencegroup PipePrecedence {
    associativity: left
    higherThan: AssignmentPrecedence
}
infix operator |>: PipePrecedence
func |> <T,R>(value: T, transform: (T) -> R) -> R { transform(value) }
func map<T,R,E>(_ f: @escaping (T) -> R) -> (Signal<T,E>) -> Signal<R,E> { { signal in Signal { s in signal.start(next: { s.putNext(f($0)) }, error: s.putError, completed: s.putCompletion) } } }
func mapToSignal<T,R,E>(_ f: @escaping (T) -> Signal<R,E>) -> (Signal<T,E>) -> Signal<R,E> {
    return { signal in Signal { s in
        let inner = MetaDisposable(), outer = MetaDisposable()
        var emitted = false
        outer.set(signal.start(next: { value in
            emitted = true; inner.set(f(value).start(next: s.putNext, error: s.putError, completed: s.putCompletion))
        }, error: s.putError, completed: { if !emitted { s.putCompletion() } }))
        return ActionDisposable { outer.dispose(); inner.dispose() }
    } }
}
func castError<T,E,R>(_ type: R.Type) -> (Signal<T,E>) -> Signal<T,R> { { signal in Signal { s in signal.start(next: s.putNext, completed: s.putCompletion) } } }
func ignoreValues<T,E>(_ signal: Signal<T,E>) -> Signal<Never,E> { Signal { s in signal.start(error: s.putError, completed: s.putCompletion) } }
func `catch`<T,E,R>(_ f: @escaping (E) -> Signal<T,R>) -> (Signal<T,E>) -> Signal<T,R> { { signal in Signal { s in
    let inner = MetaDisposable()
    let outer = signal.start(next: s.putNext, error: { error in inner.set(f(error).start(next: s.putNext, error: s.putError, completed: s.putCompletion)) }, completed: s.putCompletion)
    return ActionDisposable { outer.dispose(); inner.dispose() }
} } }
func combineLatest<T,E>(_ signals: [Signal<T,E>]) -> Signal<[T],E> {
    return Signal { s in
        if signals.isEmpty { s.putNext([]); s.putCompletion(); return EmptyDisposable }
        var values: [T?] = Array(repeating: nil, count: signals.count), completed = 0
        let disposables = signals.enumerated().map { index, signal in
            signal.start(next: { value in
                values[index] = value
                if values.allSatisfy({ $0 != nil }) { s.putNext(values.map { $0! }) }
            }, error: s.putError, completed: { completed += 1; if completed == signals.count { s.putCompletion() } })
        }
        return ActionDisposable { disposables.forEach { $0.dispose() } }
    }
}
func combineLatest<A,B,E>(_ first: Signal<A,E>, _ second: Signal<B,E>) -> Signal<(A,B),E> {
    return Signal { s in
        var a: A?, b: B?
        let left = first.start(next: { a = $0; if let a, let b { s.putNext((a,b)) } }, error: s.putError)
        let right = second.start(next: { b = $0; if let a, let b { s.putNext((a,b)) } }, error: s.putError)
        return ActionDisposable { left.dispose(); right.dispose() }
    }
}
struct Queue { static func mainQueue() -> Queue { Queue() } }
func timeout<T,E>(_ seconds: Double, queue: Queue, alternate: Signal<T,E>) -> (Signal<T,E>) -> Signal<T,E> { { $0 } }

struct NLLanguage: Hashable { let rawValue: String }
final class NLLanguageRecognizer {
    var value = ""
    func processString(_ text: String) { self.value = text }
    func languageHypotheses(withMaximum: Int) -> [NLLanguage: Double] {
        let russian = self.value.unicodeScalars.contains { (0x400 ... 0x4ff).contains($0.value) }
        return [NLLanguage(rawValue: russian ? "ru" : "en"): 0.99]
    }
}
struct PeerId: Hashable { var namespace: Int32 = 1; let value: Int64; func toInt64() -> Int64 { value } }
struct MessageId: Hashable { let peerId: PeerId; var namespace: Int32 = 0; let id: Int32 }
enum EnginePeer { typealias Id = PeerId }
enum EngineMessage { typealias Id = MessageId }
enum Namespaces { enum Peer { static let SecretChat: Int32 = 2 }; enum Message { static let Cloud: Int32 = 0 } }
enum MessageTextEntityType: Equatable {
    case Mention, Hashtag, BotCommand, Url, Email, Bold, Italic, Code, Pre, TextUrl, TextMention, PhoneNumber, BankCard, TonAddress, CustomEmoji, FormattedDate
}
struct MessageTextEntity: Equatable { let range: Range<Int>; let type: MessageTextEntityType }
protocol MessageAttribute {}
struct TextEntitiesMessageAttribute: MessageAttribute { let entities: [MessageTextEntity] }
struct TranslationMessageAttribute: MessageAttribute { let text: String; let entities: [MessageTextEntity]; let toLang: String }
struct Peer { let id: PeerId }
struct MessageForwardInfo {}
struct StoreMessageForwardInfo { init(_ value: MessageForwardInfo) {} }
struct StoreMessageFlags { init(_ value: Int) {} }
final class Message {
    let id: MessageId
    let text: String
    var attributes: [MessageAttribute] = []
    var threadId: Int64?
    var richText: String?
    var adAttribute: Int?
    var author: Peer?
    var globallyUniqueId: Int64? = 99, groupingKey: Int64? = 33
    let timestamp: Int32 = 123
    let flags = 7, tags = 8, globalTags = 9, localTags = 10
    let forwardInfo: MessageForwardInfo? = nil
    let media: [String] = ["attachment"]
    init(id: MessageId, text: String) { self.id = id; self.text = text }
    func effectivelyIncoming(_ peer: PeerId) -> Bool { self.author?.id != peer }
}
struct StoreMessage {
    let id: MessageId, customStableId: Int?, globallyUniqueId: Int64?, groupingKey: Int64?, threadId: Int64?, timestamp: Int32
    let flags: StoreMessageFlags, tags: Int, globalTags: Int, localTags: Int, forwardInfo: StoreMessageForwardInfo?, authorId: PeerId?
    let text: String, attributes: [MessageAttribute], media: [String]
}
enum UpdateMessage { case update(StoreMessage) }
final class Transaction {
    var messages: [MessageId: Message] = [:]
    var updates = 0
    func getMessage(_ id: MessageId) -> Message? { messages[id] }
    func updateMessage(_ id: MessageId, update: (Message) -> UpdateMessage) {
        guard let message = messages[id] else { return }
        if case let .update(value) = update(message) {
            precondition(value.text == message.text && value.timestamp == message.timestamp && value.media == message.media)
            message.attributes = value.attributes; updates += 1
        }
    }
}
final class Postbox {
    let store = Transaction()
    func transaction<T>(_ action: @escaping (Transaction) -> T) -> Signal<T,NoError> { Signal { s in s.putNext(action(self.store)); s.putCompletion(); return EmptyDisposable } }
}
struct MessageHistoryView { struct Entry { let message: Message }; var entries: [Entry] }
enum HistoryLocation { case peer(peerId: PeerId, threadId: Int64?) }
enum HistoryIndex { case upperBound }
final class ViewTracker {
    var messages: [Message] = []
    func aroundMessageHistoryViewForLocation(_ location: HistoryLocation, index: HistoryIndex, anchorIndex: HistoryIndex, count: Int, fixedCombinedReadStates: Int?) -> Signal<(MessageHistoryView,Int,Int),NoError> {
        .single((MessageHistoryView(entries: self.messages.map { .init(message: $0) }),0,0))
    }
}
struct Strings { let baseLanguageCode: String }
struct PresentationData { let strings: Strings }
final class Atomic<T> { let value: T; init(_ value: T) { self.value = value }; func with<R>(_ f: (T) -> R) -> R { f(value) } }
final class SharedContext {
    let currentPresentationData = Atomic(PresentationData(strings: Strings(baseLanguageCode: "ru")))
    var presentationData: Signal<PresentationData,NoError> { .single(self.currentPresentationData.value) }
}
final class Account { let peerId: PeerId; let postbox = Postbox(); let viewTracker = ViewTracker(); init(_ value: Int64) { peerId = PeerId(value: value) } }
final class AccountContext { let account: Account; let sharedContext = SharedContext(); init(_ value: Int64 = 1) { account = Account(value) } }
struct ChatTranslationState { let baseLang: String, fromLang: String, timestamp: Int32?, toLang: String?, isEnabled: Bool }
enum NagramiXTranslationKeys { static func read(_ provider: NagramiXTranslationProvider) -> NagramiXTranslationCredential? { nil } }
protocol ExperimentalInternalTranslationService: AnyObject {
    func translate(texts: [AnyHashable:String], fromLang: String, toLang: String) -> Signal<[AnyHashable:String]?,NoError>
}
var engineExperimentalInternalTranslationService: ExperimentalInternalTranslationService?
final class LocalService: ExperimentalInternalTranslationService {
    struct Request { let texts: [AnyHashable:String]; let source: String; let target: String; let subscriber: Subscriber<[AnyHashable:String]?,NoError> }
    var requests: [Request] = []
    func translate(texts: [AnyHashable:String], fromLang: String, toLang: String) -> Signal<[AnyHashable:String]?,NoError> {
        return Signal { s in
            self.requests.append(Request(texts: texts, source: fromLang, target: toLang, subscriber: s))
            return EmptyDisposable
        }
    }
    func finish(_ text: String = "Перевод") {
        let request = self.requests.last!
        request.subscriber.putNext(request.texts.mapValues { _ in text }); request.subscriber.putCompletion()
    }
}

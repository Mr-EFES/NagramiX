import Foundation

enum NoError: Error {}
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    let action: () -> Void
    var disposed = false
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { if !disposed { disposed = true; action() } }
}
var EmptyDisposable: Disposable { ActionDisposable({}) }
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

final class DisposableSet: Disposable {
    private let lock=NSRecursiveLock();private var items:[Disposable]=[];private var disposed=false
    func add(_ disposable:Disposable) { lock.lock();defer{lock.unlock()};if disposed{disposable.dispose()}else{items.append(disposable)} }
    func dispose(){lock.lock();defer{lock.unlock()};disposed=true;let all=items;items=[];all.forEach{$0.dispose()} }
}
func filter<T,E>(_ predicate:@escaping(T)->Bool)->(Signal<T,E>)->Signal<T,E>{{ signal in Signal { s in signal.start(next:{if predicate($0){s.putNext($0)}},error:s.putError,completed:s.putCompletion) }}}
func take<T,E>(_ count:Int)->(Signal<T,E>)->Signal<T,E>{{ signal in Signal { s in var remaining=count;return signal.start(next:{if remaining>0{remaining-=1;s.putNext($0);if remaining==0{s.putCompletion()}}},error:s.putError,completed:s.putCompletion) }}}
func deliverOnMainQueue<T,E>(_ signal:Signal<T,E>)->Signal<T,E>{signal}
struct PeerId:Hashable{var namespace:Int32=1;let value:Int64;func toInt64()->Int64{value}}
struct MessageId:Hashable{let peerId:PeerId;var namespace:Int32=0;let id:Int32}
enum EngineMessage{typealias Id=MessageId}
enum Namespaces{enum Peer{static let SecretChat:Int32=2};enum Message{static let Cloud:Int32=0}}
protocol MessageAttribute{}
struct CodableEntry{let data:Data;init?<T:Encodable>(_ value:T){guard let data=try? JSONEncoder().encode(value)else{return nil};self.data=data};func get<T:Decodable>(_ type:T.Type)->T?{try? JSONDecoder().decode(type,from:data)}}
final class DerivedDataMessageAttribute:MessageAttribute{let data:[String:CodableEntry];init(data:[String:CodableEntry]){self.data=data}}
final class AudioTranscriptionMessageAttribute:MessageAttribute{
 let id:Int64;let text:String;let isPending:Bool;let didRate:Bool;let error:Int?
 init(id:Int64,text:String,isPending:Bool,didRate:Bool,error:Int?){self.id=id;self.text=text;self.isPending=isPending;self.didRate=didRate;self.error=error}
}
struct MessageFlags:OptionSet{let rawValue:Int32;static let Incoming=Self(rawValue:1)}
struct StoreMessageFlags{init(_ flags:MessageFlags){}}
struct ResourceId:Equatable{let stringRepresentation:String}
struct Resource{let id:ResourceId}
final class TelegramMediaFile{let resource:Resource;var isVoice=true;var isInstantVideo=false;var size:Int64?=1024;var duration:Double?=10;init(_ id:String){resource=Resource(id:ResourceId(stringRepresentation:id))}}
struct Peer{let id:PeerId}
struct MessageForwardInfo{}
struct StoreMessageForwardInfo{init(_ value:MessageForwardInfo){}}
final class Message{
 let id:MessageId;var media:[Any];var attributes:[MessageAttribute]=[];var containsSecretMedia=false;var isSelfExpiring=false;var protected=false
 var flags:MessageFlags=[.Incoming];let text="Original caption";let threadId:Int64?=73;let timestamp:Int32=999
 let globallyUniqueId:Int64?=31;let groupingKey:Int64?=41;let tags=11,globalTags=12,localTags=13
 let forwardInfo:MessageForwardInfo?=nil;let author:Peer?=nil
 init(_ id:MessageId,_ file:TelegramMediaFile){self.id=id;self.media=[file]}
 func isCopyProtected()->Bool{protected}
}
typealias EngineRawMessage=Message
struct StoreMessage{let id:MessageId;let customStableId:Int?;let globallyUniqueId:Int64?;let groupingKey:Int64?;let threadId:Int64?;let timestamp:Int32;let flags:StoreMessageFlags;let tags:Int;let globalTags:Int;let localTags:Int;let forwardInfo:StoreMessageForwardInfo?;let authorId:PeerId?;let text:String;let attributes:[MessageAttribute];let media:[Any]}
enum UpdateMessage{case update(StoreMessage)}
final class Transaction{
 var messages:[MessageId:Message]=[:];var updates=0
 func getMessage(_ id:MessageId)->Message?{messages[id]}
 func updateMessage(_ id:MessageId,update:(Message)->UpdateMessage){guard let message=messages[id]else{return};if case let .update(value)=update(message){precondition(value.text==message.text&&value.threadId==message.threadId&&value.timestamp==message.timestamp&&value.globallyUniqueId==message.globallyUniqueId&&value.groupingKey==message.groupingKey&&value.tags==message.tags&&value.globalTags==message.globalTags&&value.localTags==message.localTags);message.attributes=value.attributes;updates+=1}}
}
final class Postbox{let store=Transaction();func transaction<T>(_ action:@escaping(Transaction)->T)->Signal<T,NoError>{Signal{s in s.putNext(action(self.store));s.putCompletion();return EmptyDisposable}}}
struct MessageReference{init(_ message:Message){}}
enum MediaReference<T>{case message(message:MessageReference,media:T)}
enum MediaResourceReference{case media(media:MediaReference<TelegramMediaFile>,resource:Resource)}
enum MediaResourceUserLocation{case peer(PeerId)}
enum MediaResourceUserContentType{case audioVideoMessage}
enum FetchError:Error{case missing}
enum EngineMediaResource{struct Id{let id:ResourceId;init(_ id:ResourceId){self.id=id}};struct ResourceData{let isComplete:Bool;let path:String}}
final class Resources{
 var complete=true;var fetches=0;var fail=false
 func data(id:EngineMediaResource.Id)->Signal<EngineMediaResource.ResourceData,NoError>{.single(.init(isComplete:complete,path:"/tmp/fake-audio.m4a"))}
 func fetch(reference:MediaResourceReference,userLocation:MediaResourceUserLocation,userContentType:MediaResourceUserContentType)->Signal<Int,FetchError>{fetches+=1;return fail ? .fail(.missing):.complete()}
}
final class Engine{let resources=Resources()}
final class Account{let peerId=PeerId(value:1);let postbox=Postbox()}
final class AccountContext{let account=Account();let engine=Engine()}
enum UIApplication{static let didEnterBackgroundNotification=Notification.Name("FakeBackground");static let didReceiveMemoryWarningNotification=Notification.Name("FakeMemoryWarning")}
enum NagramiXTranscriptionKeys{static var reads=0;static var key:String?="owned";static func read(_ provider:NagramiXTranscriptionProvider)->String?{reads+=1;return key}}
final class NagramiXWhisperModels{static let shared=NagramiXWhisperModels();var ready=true;func installed(_ model:NagramiXWhisperModel)->Bool{ready}}
final class NagramiXTranscriptionMedia{
 let audio=URL(fileURLWithPath:"/tmp/nagramix-asr-boundary-audio.m4a")
 static var preparations=0
 static func prepare(path:String,cancellation:NagramiXTranscriptionCancellation,completion:@escaping(Result<NagramiXTranscriptionMedia,NagramiXTranscriptionFailure>)->Void){preparations+=1;completion(.success(.init()))}
}
enum AudioBoundary{
 static let lock=NSLock();static var callback:((Result<String,NagramiXTranscriptionFailure>)->Void)?;static var started=DispatchSemaphore(value:0);static var provider:NagramiXTranscriptionProvider?
 static func recognize(_ provider:NagramiXTranscriptionProvider,_ completion:@escaping(Result<String,NagramiXTranscriptionFailure>)->Void){lock.lock();self.provider=provider;callback=completion;lock.unlock();started.signal()}
 static func finish(_ result:Result<String,NagramiXTranscriptionFailure>){lock.lock();let callback=self.callback;self.callback=nil;lock.unlock();callback?(result)}
}
enum NagramiXTranscriptionApple{
 static var authorized=true;static var supported=true
 static func available(_ language:String)->Bool{supported&&language != "auto"}
 static func transcribe(url:URL,language:String,automatic:Bool,cancellation:NagramiXTranscriptionCancellation,completion:@escaping(Result<String,NagramiXTranscriptionFailure>)->Void){AudioBoundary.recognize(.apple,completion)}
}
enum NagramiXTranscriptionWhisper{static func transcribe(media:NagramiXTranscriptionMedia,configuration:NagramiXTranscriptionConfiguration,cancellation:NagramiXTranscriptionCancellation,completion:@escaping(Result<String,NagramiXTranscriptionFailure>)->Void){AudioBoundary.recognize(.whisper,completion)}}
final class NagramiXTranscriptionCloud{static let shared=NagramiXTranscriptionCloud();func transcribe(configuration:NagramiXTranscriptionConfiguration,key:String,audio:Data,cancellation:NagramiXTranscriptionCancellation,completion:@escaping(Result<String,NagramiXTranscriptionFailure>)->Void){AudioBoundary.recognize(configuration.provider,completion)}}

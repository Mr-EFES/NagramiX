// Scheduling adapter for the production playback helper and native filter.
public enum NoError:Error {}
public protocol Disposable {func dispose()}
public final class ActionDisposable:Disposable {
    let action:()->Void
    public init(_ action:@escaping()->Void={}){self.action=action}
    public func dispose(){action()}
}
public final class MetaDisposable:Disposable {
    var value:Disposable?
    public init(){}
    public func set(_ value:Disposable?){self.value?.dispose();self.value=value}
    public func dispose(){value?.dispose();value=nil}
}
public final class Signal<T,E:Error> {
    let subscribe:(@escaping(T)->Void)->Disposable
    public init(_ subscribe:@escaping(@escaping(T)->Void)->Disposable){self.subscribe=subscribe}
    public func start(next:@escaping(T)->Void)->Disposable {subscribe(next)}
}
public final class Channel<T> {
    var nextId=0
    var observers:[Int:(T)->Void]=[:]
    public var value:T
    public var deferred=false
    public init(_ value:T){self.value=value}
    public var signal:Signal<T,NoError> {Signal{[weak self] next in
        guard let self else{return ActionDisposable()}
        let id=self.nextId;self.nextId+=1;self.observers[id]=next
        if !self.deferred {next(self.value)}
        return ActionDisposable{[weak self] in self?.observers.removeValue(forKey:id)}
    }}
    public func set(_ value:T){self.value=value;for f in Array(observers.values){f(value)}}
}
infix operator |> : AdditionPrecedence
public func |> <T,U>(_ value:T,_ transform:(T)->U)->U {transform(value)}
public func take<T,E>(_ count:Int)->(Signal<T,E>)->Signal<T,E> { { signal in Signal { next in
    var remaining=count
    return signal.start{value in if remaining>0 {remaining-=1;next(value)}}
}}}
public func deliverOnMainQueue<T,E>(_ signal:Signal<T,E>)->Signal<T,E> {signal}
public func map<T,U,E>(_ transform:@escaping(T)->U)->(Signal<T,E>)->Signal<U,E> {{signal in Signal{next in signal.start{next(transform($0))}}}}
public func distinctUntilChanged<T,E>(isEqual:@escaping(T,T)->Bool)->(Signal<T,E>)->Signal<T,E> {{signal in Signal{next in
    var previous:T?
    return signal.start{value in if let previous,isEqual(previous,value){return};previous=value;next(value)}
}}}

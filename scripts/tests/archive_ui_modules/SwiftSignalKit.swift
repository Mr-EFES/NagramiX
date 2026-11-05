public enum NoError: Error {}
public final class Signal<T, E: Error> {
    public static func single(_ value: T) -> Signal<T, E> { fatalError("interface only") }
}
infix operator |> : AdditionPrecedence
public func |> <A, B>(value: A, transform: (A) -> B) -> B { transform(value) }
public func mapToSignal<A, B, E: Error>(_ transform: @escaping (A) -> Signal<B, E>) -> (Signal<A, E>) -> Signal<B, E> {
    fatalError("interface only")
}

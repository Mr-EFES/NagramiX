import Foundation

// Signal boundaries for the real NotificationCenter bridge. Counter functions
// and their original versions are extracted verbatim from pinned native files.
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    private var action: (() -> Void)?
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { let action = self.action; self.action = nil; action?() }
}
enum NoError {}
enum SignalProbe { static weak var subscriber: AnyObject? }
final class Subscriber<T,E>: @unchecked Sendable {
    private let next: (T) -> Void
    init(_ next: @escaping (T) -> Void) { self.next = next }
    func putNext(_ value: T) { next(value) }
}
final class Signal<T,E> {
    let generate: (Subscriber<T,E>) -> Disposable
    init(_ generate: @escaping (Subscriber<T,E>) -> Disposable) { self.generate = generate }
    func start(next: @escaping (T) -> Void) -> Disposable {
        let subscriber = Subscriber<T,E>(next); SignalProbe.subscriber = subscriber
        return generate(subscriber)
    }
}
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <A,B>(value: A, f: (A) -> B) -> B { f(value) }
func distinctUntilChanged<T: Equatable,E>(_ source: Signal<T,E>) -> Signal<T,E> {
    Signal { subscriber in var last: T?; return source.start(next: { value in if last != value { last = value; subscriber.putNext(value) } }) }
}
final class Values<T>: @unchecked Sendable {
    private let lock = NSLock(); private var storage: [T] = []
    func append(_ value: T) { lock.lock(); storage.append(value); lock.unlock() }
    var all: [T] { lock.lock(); defer { lock.unlock() }; return storage }
}

@main struct NumberRoundingTests {
    static func main() {
        let defaults = UserDefaults.standard, key = "nagramix.interface.roundNumbers"
        if CommandLine.arguments.count > 1 {
            let command = CommandLine.arguments[1], enabled = CommandLine.arguments[2] == "true"
            if command == "set" { NagramiXNumberSettings.setRoundingEnabled(enabled); _ = defaults.synchronize() }
            else {
                precondition(NagramiXNumberSettings.roundingEnabled == enabled, "saved rounding survives cold restart")
                precondition(compactNumericCountString(1234) == (enabled ? "1.2K" : NagramiXNumberSettings.fullCountString(1234)), "formatter immediately uses persisted setting on cold launch")
                if command == "fresh" { precondition(defaults.object(forKey: key) == nil, "fresh getter does not save an artificial choice") }
            }
            print("PASS cold " + command + " " + String(enabled)); return
        }
        defaults.removeObject(forKey:key)
        defer { defaults.removeObject(forKey:key); _ = defaults.synchronize() }
        var total = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) { precondition(value(),label); total += 1 }
        check(!NagramiXNumberSettings.roundingEnabled && defaults.object(forKey:key) == nil, "first launch OFF without writing settings")
        let exact: [(Int64,String)] = [(0,"0"),(1,"1"),(-1,"-1"),(999,"999"),(1000,"1,000"),(1234,"1,234"),(-1234,"-1,234"),(1234567,"1,234,567"),(Int64.max,"9,223,372,036,854,775,807"),(Int64.min,"-9,223,372,036,854,775,808")]
        for (value,expected) in exact {
            check(NagramiXNumberSettings.fullCountString(value,groupingSeparator:",") == expected, "all digits including signed extremes, without abs overflow")
        }
        check(NagramiXNumberSettings.fullCountString(UInt64.max,groupingSeparator:",") == "18,446,744,073,709,551,615", "generic formatter preserves unsigned limit")
        check(NagramiXNumberSettings.fullCountString(1234,groupingSeparator:"") == "1234", "empty grouping remains exact")
        check(NagramiXNumberSettings.fullCountString(1234567,groupingSeparator:"\u{202f}") == "1\u{202f}234\u{202f}567", "nonbreaking regional separator")
        check(NagramiXNumberSettings.fullCountString(-1234567,groupingSeparator:"xy") == "-1xy234xy567", "multi-character separator keeps correct group order")
        let values: [Int] = [Int.min,-1000000001,-1000001,-1234,-1000,-999,-1,0,1,10,99,999,1000,1001,1099,1100,1234,1999,9999,10000,99999,100000,999999,1000000,1000001,1234567,999999999,1000000000,1234567890,Int(Int32.max),Int.max]
        let regionSeparator = Locale.current.groupingSeparator ?? "\u{00a0}"
        for enabled in [false,true,false,true] {
            NagramiXNumberSettings.setRoundingEnabled(enabled)
            check(NagramiXNumberSettings.roundingEnabled == enabled, "explicit ON and OFF retained")
            for value in values {
                for decimal in [".",",","\u{066b}"] {
                    for show in [false,true] {
                        let actual = compactNumericCountString(value,decimalSeparator:decimal,showDecimalPart:show)
                        if enabled {
                            check(actual == stockCompactNumericCountString(value,decimalSeparator:decimal,showDecimalPart:show), "ON matches original Telegram compact formatter exactly")
                        } else {
                            check(actual == NagramiXNumberSettings.fullCountString(value), "OFF ignores compact decimal options and preserves exact count")
                            check(actual.replacingOccurrences(of:regionSeparator,with:"") == String(value), "full displayed counter retains every digit")
                        }
                    }
                }
                for forceDecimal in [false,true] {
                    let actual = countString(Int64(value),forceDecimal:forceDecimal)
                    check(actual == (enabled ? stockCountString(Int64(value),forceDecimal:forceDecimal) : NagramiXNumberSettings.fullCountString(Int64(value))), "second common counter uses same mode and preserves native ON")
                }
                for separator in ["",","," ","\u{202f}"] {
                    let text = NagramiXNumberSettings.fullCountString(value,groupingSeparator:separator)
                    check((separator.isEmpty ? text : text.replacingOccurrences(of:separator,with:"")) == String(value), "no precision loss for signed boundary values")
                }
            }
        }
        NagramiXNumberSettings.setRoundingEnabled(false)
        let updates = Values<Bool>()
        let subscription = nagramiXNumberRoundingSignal().start(next:updates.append)
        check(updates.all == [false], "presentation bridge publishes current value on subscription")
        NagramiXNumberSettings.setRoundingEnabled(false)
        NagramiXNumberSettings.setRoundingEnabled(true)
        NagramiXNumberSettings.setRoundingEnabled(true)
        NagramiXNumberSettings.setRoundingEnabled(false)
        check(updates.all == [false,true,false], "only real format changes refresh native presentation pipeline")
        subscription.dispose()
        check(SignalProbe.subscriber == nil, "disposal removes observer and releases retained subscriber")
        NagramiXNumberSettings.setRoundingEnabled(true)
        check(updates.all == [false,true,false], "disposed presentation observer never emits")
        check(compactNumericCountString(1234) == "1.2K" && compactNumericCountString(1234,decimalSeparator:",") == "1,2K", "native compact decimal separators unchanged")
        print("PASS: \(total) actual settings/formatter/refresh/lifetime checks")
    }
}

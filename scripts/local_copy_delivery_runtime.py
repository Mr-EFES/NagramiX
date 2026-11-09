#!/usr/bin/env python3
"""Исполнить реальный SignalKit и production-защиту отправки копий."""
from pathlib import Path

from validate_quick_format import block

CORE = 'submodules/TelegramCore/Sources/'
UPLOAD = CORE + 'PendingMessages/PendingMessageUploadedContent.swift'
MANAGER = CORE + 'State/PendingMessageManager.swift'
SK = 'submodules/SSignalKit/SwiftSignalKit/Source/'

BOUNDARY = r'''import Foundation

// Only time and scheduling are adapters. Signal, Subscriber, Atomic and
// disposal below are the exact production SignalKit implementations.
enum FixtureClock {
    static var now = 0.0
    static var timers: [BoundaryTimer] = []
    static var tasks: [() -> Void] = []
    static func drain() {
        var budget = 10000
        while !tasks.isEmpty {
            precondition(budget > 0, "scheduler failed to quiesce")
            budget -= 1
            let task = tasks.removeFirst()
            task()
        }
    }
    static func advance(_ delta: Double) {
        let end = now + delta
        drain()
        while let timer = timers.filter({ !$0.invalidated && $0.deadline <= end })
            .min(by: { $0.deadline < $1.deadline }) {
            now = max(now, timer.deadline)
            timer.fire()
            drain()
        }
        now = end
        drain()
    }
    static func suspendWithoutDispatch(_ delta: Double) { now += delta }
    static func resumeDueTimers() {
        let due = timers.filter { !$0.invalidated && $0.deadline <= now }
        // A suspended dispatch source coalesces its missed repeating ticks;
        // it does not execute every missed event at an old clock value.
        for timer in due { timer.fire(); drain() }
    }
    static func reset() {
        timers.removeAll()
        tasks.removeAll()
        now = 0.0
    }
}
enum ProcessInfo {
    struct Snapshot { var systemUptime: Double { FixtureClock.now } }
    static var processInfo: Snapshot { Snapshot() }
}
public final class Queue {
    public static let shared = Queue()
    public static func mainQueue() -> Queue { shared }
    public static func concurrentDefaultQueue() -> Queue { shared }
    public func isCurrent() -> Bool { true }
    public func async(_ f: @escaping () -> Void) { FixtureClock.tasks.append(f) }
}
public final class BoundaryTimer {
    let interval: Double
    let completion: () -> Void
    let repeating: Bool
    var deadline = 0.0
    var invalidated = false
    public init(timeout: Double, repeat repeating: Bool, completion: @escaping () -> Void, queue: Queue) {
        self.interval = timeout
        self.completion = completion
        self.repeating = repeating
    }
    func fire() {
        guard !self.invalidated else { return }
        if self.repeating { self.deadline = FixtureClock.now + self.interval }
        else { self.invalidated = true }
        self.completion()
    }
    public func start() {
        if !self.invalidated {
            self.deadline = FixtureClock.now + self.interval
            FixtureClock.timers.append(self)
        }
    }
    public func invalidate() { self.invalidated = true }
}
enum SwiftSignalKit { typealias Timer = BoundaryTimer }
'''

TESTS = r'''
enum CopyFailure: Equatable { case transport, stalled }
enum Event: Equatable { case progress(Double), content(Int), acknowledgement }
final class Input<T, E> {
    var subscriber: Subscriber<T, E>?
    var starts = 0
    var disposals = 0
    func signal(initial: T? = nil) -> Signal<T, E> {
        Signal { subscriber in
            self.starts += 1
            self.subscriber = subscriber
            if let initial { subscriber.putNext(initial) }
            return ActionDisposable { self.disposals += 1 }
        }
    }
    func next(_ value: T) { self.subscriber?.putNext(value) }
    func fail(_ error: E) { self.subscriber?.putError(error) }
    func complete() { self.subscriber?.putCompletion() }
}
final class Probe {
    var values: [Event] = []
    var errors: [CopyFailure] = []
    var completions = 0
    var disposable: Disposable?
    func start(_ source: Signal<Event, CopyFailure>, _ online: Signal<Bool, NoError>, timeout: Double = 10.0) {
        self.disposable = nagramiXCopyDeliverySignal(source, queue: Queue.shared, isOnline: online,
            idleTimeout: timeout, progress: { event in
                if case let .progress(value) = event { return value }
                return nil
            }, isContent: { event in
                if case .content = event { return true }
                return false
            }, failure: .stalled).start(next: { self.values.append($0) },
                error: { self.errors.append($0) }, completed: { self.completions += 1 })
        FixtureClock.drain()
    }
}
var checks = 0
func check(_ value: @autoclosure () -> Bool, _ message: String) {
    if !value() { fputs("FAIL: \(message)\n", stderr); exit(91) }
    checks += 1
}
func fresh(_ online: Bool = true) -> (Input<Event, CopyFailure>, Input<Bool, NoError>, Probe) {
    FixtureClock.reset()
    let input = Input<Event, CopyFailure>()
    let connectivity = Input<Bool, NoError>()
    let probe = Probe()
    probe.start(input.signal(), connectivity.signal(initial: online))
    return (input, connectivity, probe)
}
@main enum DeliveryRuntime {
    static func main() {
        // Empty completion is not a successful preparation and must release it.
        for online in [false, true] {
            let (input, network, probe) = fresh(online)
            input.complete(); FixtureClock.drain()
            check(probe.errors == [.stalled], "empty completion becomes a real failure")
            check(probe.values.isEmpty && probe.completions == 0, "empty preparation cannot report success")
            check(input.disposals == 1 && network.disposals == 1, "empty completion releases all sources")
            FixtureClock.advance(100)
            check(probe.errors.count == 1, "empty result fails once")
        }
        // A source may finish synchronously inside start; disposal still arrives.
        for synchronous in [Signal<Event, CopyFailure>.single(.content(7)),
                            .single(.content(8)), .complete(), .fail(.transport)] {
            FixtureClock.reset()
            let network = Input<Bool, NoError>()
            let probe = Probe()
            probe.start(synchronous, network.signal(initial: true))
            check(probe.values.count + probe.errors.count == 1, "synchronous source has one outcome")
            check(network.disposals == 1, "synchronous outcome releases connectivity")
            FixtureClock.advance(100)
            check(probe.values.count + probe.errors.count == 1, "synchronous outcome remains final")
        }
        // Native cloud-reference content remains immediate and has no byte stage.
        do {
            let (input, network, probe) = fresh()
            input.next(.content(42)); FixtureClock.drain()
            check(probe.values == [.content(42)], "cloud content passes without waiting for timeout")
            check(probe.errors.isEmpty && probe.completions == 1, "content terminates successfully")
            check(input.disposals == 1 && network.disposals == 1, "content releases upload and network")
            input.next(.content(43)); input.fail(.transport); input.complete()
            FixtureClock.advance(100)
            check(probe.values == [.content(42)] && probe.errors.isEmpty && probe.completions == 1,
                  "late upload events cannot duplicate the copy")
        }
        // Errors carry their original reason and never turn into a stuck spinner.
        do {
            let (input, network, probe) = fresh()
            input.fail(.transport); FixtureClock.drain()
            check(probe.errors == [.transport] && probe.completions == 0, "original upload error preserved")
            check(input.disposals == 1 && network.disposals == 1, "failure cancels both subscriptions")
            FixtureClock.advance(100)
            check(probe.errors == [.transport], "no watchdog error after original failure")
        }
        // Duplicated progress, nil activity and non-finite values cannot keep a
        // non-advancing upload alive forever.
        for stalled: Event in [.progress(0), .acknowledgement, .progress(.nan), .progress(.infinity)] {
            let (input, network, probe) = fresh()
            input.next(stalled); FixtureClock.drain()
            for _ in 0 ..< 9 { FixtureClock.advance(1); input.next(stalled); FixtureClock.drain() }
            check(probe.errors.isEmpty, "idle budget has not expired early")
            FixtureClock.advance(1.01)
            check(probe.errors == [.stalled], "duplicate or invalid progress cannot renew idle budget")
            check(input.disposals == 1 && network.disposals == 1, "stalled upload releases its queue inputs")
        }
        // A large transfer may take arbitrarily longer than the idle interval.
        do {
            let (input, _, probe) = fresh()
            for n in 0 ..< 100 {
                input.next(.progress(Double(n) / 100)); FixtureClock.drain()
                FixtureClock.advance(9)
                check(probe.errors.isEmpty, "advancing large file has no absolute timeout")
            }
            input.next(.content(99)); FixtureClock.drain()
            check(probe.values.last == .content(99) && probe.completions == 1, "long transfer completes normally")
        }
        // Progress can legitimately restart at a lower fraction in a new stage.
        do {
            let (input, _, probe) = fresh()
            for value in [0.9, 0.1, 0.2, 0.0, 0.3] {
                input.next(.progress(value)); FixtureClock.drain(); FixtureClock.advance(9)
                check(probe.errors.isEmpty, "phase progress decrease counts as activity")
            }
            input.next(.content(5)); FixtureClock.drain()
            check(probe.completions == 1, "multi-stage copy succeeds")
        }
        // Offline time consumes no idle budget, including long background gaps.
        do {
            let (input, network, probe) = fresh(false)
            FixtureClock.advance(1000)
            check(probe.errors.isEmpty, "offline copy remains pending")
            network.next(true); FixtureClock.drain(); FixtureClock.advance(6)
            network.next(false); FixtureClock.drain(); FixtureClock.advance(1000)
            check(probe.errors.isEmpty, "disconnected time pauses existing budget")
            network.next(true); FixtureClock.drain(); FixtureClock.advance(3.9)
            check(probe.errors.isEmpty, "remaining online idle budget preserved")
            FixtureClock.advance(0.2)
            check(probe.errors == [.stalled] && input.disposals == 1, "offline pause does not reset the accumulated online budget")
        }
        do {
            let (input, network, probe) = fresh(false)
            FixtureClock.advance(1000); input.next(.content(3)); FixtureClock.drain()
            check(probe.completions == 1 && probe.errors.isEmpty, "local cached preparation can finish offline")
            check(network.disposals == 1, "offline success cancels connectivity observer")
        }
        // Connectivity repetition must not silently extend a stopped transfer.
        do {
            let (_, network, probe) = fresh()
            for _ in 0 ..< 9 { FixtureClock.advance(1); network.next(true); FixtureClock.drain() }
            FixtureClock.advance(1.1)
            check(probe.errors == [.stalled], "duplicate online state does not renew idle budget")
        }
        // A canceled timer may already have enqueued its callback. Generation
        // checks inside the real helper must reject it after progress.
        do {
            let (input, _, probe) = fresh()
            let previous = FixtureClock.timers.last!
            FixtureClock.advance(9)
            input.next(.progress(0.2)); FixtureClock.drain()
            previous.completion(); FixtureClock.drain()
            check(probe.errors.isEmpty, "stale watchdog cannot fail fresh progress")
            input.next(.content(10)); FixtureClock.drain()
            previous.completion(); FixtureClock.drain()
            check(probe.errors.isEmpty && probe.completions == 1, "stale watchdog cannot change terminal success")
        }
        // Cancellation is silent, disposes every input and invalidates timeouts.
        do {
            let (input, network, probe) = fresh()
            let previous = FixtureClock.timers.last!
            probe.disposable?.dispose(); FixtureClock.drain()
            check(input.disposals == 1 && network.disposals == 1, "cancellation disposes sources")
            previous.completion(); input.next(.content(100)); FixtureClock.advance(100)
            check(probe.values.isEmpty && probe.errors.isEmpty && probe.completions == 0,
                  "cancellation emits no success or synthetic error")
        }
        for invalid in [0.0, -1, Double.nan, .infinity] {
            FixtureClock.reset()
            let source = Input<Event, CopyFailure>(), network = Input<Bool, NoError>()
            let probe = Probe()
            probe.start(source.signal(), network.signal(initial: true), timeout: invalid)
            check(probe.errors == [.stalled], "invalid watchdog budget is rejected immediately")
            check(source.starts == 0 && network.starts == 0, "invalid configuration creates no subscriptions")
        }
        // Each recipient has its own watchdog and disposal budget.
        do {
            FixtureClock.reset()
            let first = Input<Event, CopyFailure>(), second = Input<Event, CopyFailure>()
            let firstOnline = Input<Bool, NoError>(), secondOnline = Input<Bool, NoError>()
            let a = Probe(), b = Probe()
            a.start(first.signal(), firstOnline.signal(initial: true))
            b.start(second.signal(), secondOnline.signal(initial: true))
            FixtureClock.advance(9); first.next(.progress(0.2)); FixtureClock.drain()
            FixtureClock.advance(2)
            check(a.errors.isEmpty && b.errors == [.stalled], "stalled recipient cannot cancel an advancing recipient")
            first.next(.content(88)); FixtureClock.drain()
            check(a.completions == 1 && a.errors.isEmpty, "independent recipient completes its original payload")
        }
        // The OS can suspend this process while the last network value still
        // says online. A late dispatch tick must not charge that wall-clock gap
        // before callbacks have a chance to resume their genuine progress.
        do {
            let (input, _, probe) = fresh()
            FixtureClock.advance(4)
            FixtureClock.suspendWithoutDispatch(600)
            FixtureClock.resumeDueTimers()
            check(probe.errors.isEmpty, "late tick after OS suspension cannot fail resumed copy")
            input.next(.progress(0.4)); FixtureClock.drain()
            FixtureClock.advance(9)
            check(probe.errors.isEmpty, "resumed real progress receives the full active idle budget")
            input.next(.content(23)); FixtureClock.drain()
            check(probe.completions == 1 && probe.errors.isEmpty, "suspended copy can finish without a synthetic failure")
        }
        do {
            let (_, _, probe) = fresh()
            FixtureClock.advance(4)
            FixtureClock.suspendWithoutDispatch(600)
            FixtureClock.resumeDueTimers()
            check(probe.errors.isEmpty, "suspension time is excluded without requiring offline notification")
            FixtureClock.advance(5.9)
            check(probe.errors.isEmpty, "suspension preserves the remaining active budget")
            FixtureClock.advance(0.2)
            check(probe.errors == [.stalled], "real active idle still expires after suspension")
        }
        do {
            let (_, network, probe) = fresh()
            FixtureClock.advance(4)
            FixtureClock.suspendWithoutDispatch(600)
            network.next(false); FixtureClock.drain()
            FixtureClock.resumeDueTimers()
            check(probe.errors.isEmpty, "offline callback after suspension does not charge the missing wall time")
            FixtureClock.suspendWithoutDispatch(600)
            network.next(true); FixtureClock.drain()
            FixtureClock.advance(5.9)
            check(probe.errors.isEmpty, "offline suspension keeps the previous active budget")
            FixtureClock.advance(0.2)
            check(probe.errors == [.stalled], "normal idle detection resumes after suspended offline transition")
        }
        print("Local copy delivery SignalKit checks: \(checks)")
    }
}
'''


def signal_runtime(source: Path) -> str:
    pieces = [BOUNDARY]
    for name in ['Atomic.swift', 'Disposable.swift', 'Subscriber.swift']:
        pieces.append((source / (SK + name)).read_text())
    signal = (source / (SK + 'Signal.swift')).read_text()
    pieces.append(signal[:signal.index('@available(iOS 13.0')])
    upload = (source / UPLOAD).read_text()
    pieces.append(block(upload, 'func nagramiXCopyDeliverySignal<'))
    return '\n'.join(pieces)


def fixture(source: Path) -> str:
    return signal_runtime(source) + TESTS


POLICY_BOUNDARY = r'''
enum ConnectionStatus { case offline, connecting, online }
final class Network { let connectionStatus: Signal<ConnectionStatus, NoError>
    init(_ signal: Signal<ConnectionStatus, NoError>) { self.connectionStatus = signal }
}
protocol MessageAttribute {}
struct OutgoingContentInfoFlags: OptionSet { let rawValue: Int; static let nagramiXCopy = Self(rawValue: 2) }
struct OutgoingContentInfoMessageAttribute: MessageAttribute { let flags: OutgoingContentInfoFlags }
struct ForwardSourceInfoAttribute: MessageAttribute {}
struct Message { let attributes: [MessageAttribute] }
struct PendingMessageUploadedContentProgress {
    enum Phase { case processing, uploading }
    let progress: Float
    let phase: Phase
}
enum PendingMessageUploadedContentResult { case progress(PendingMessageUploadedContentProgress), content(Int) }
enum Api { struct Updates: Equatable { let token: Int } }
enum NetworkRequestResult<T> { case progress(Float, Int32), acknowledged, result(T) }
struct MTRpcError: Equatable { let errorCode: Int; let errorDescription: String }
'''

POLICY_TESTS = r'''
var checks = 0
func check(_ value: @autoclosure () -> Bool, _ label: String) {
    if !value() { fputs("FAIL: \(label)\n", stderr); exit(91) }
    checks += 1
}
final class PolicyInput<T, E> {
    var subscriber: Subscriber<T, E>?
    var disposed = 0
    func signal(_ initial: T? = nil) -> Signal<T, E> {
        Signal { s in self.subscriber = s; if let initial { s.putNext(initial) }
            return ActionDisposable { self.disposed += 1 } }
    }
    func next(_ value: T) { self.subscriber?.putNext(value); FixtureClock.drain() }
    func fail(_ error: E) { self.subscriber?.putError(error); FixtureClock.drain() }
}
@main enum RequestPolicyTests {
    static func main() {
        let native = Message(attributes: [])
        let copy = Message(attributes: [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])])
        let forward = Message(attributes: [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy]), ForwardSourceInfoAttribute()])
        check(!nagramiXIsLocalCopyMessage(native) && nagramiXIsLocalCopyMessage(copy), "only authored copies opt in")
        check(!nagramiXIsLocalCopyMessage(forward), "native forward of copied content is not a local-copy RPC")
        let processing = PendingMessageUploadedContentResult.progress(.init(progress: 0.7, phase: .processing))
        let uploading = PendingMessageUploadedContentResult.progress(.init(progress: 0.0, phase: .uploading))
        check(nagramiXCopyUploadProgress(processing) == Double(Float(0.7)), "processing fraction is meaningful activity")
        check(nagramiXCopyUploadProgress(uploading) == 2, "upload phase transition renews activity")
        check(nagramiXCopyUploadProgress(.content(1)) == nil, "finished upload has no synthetic progress")
        check(nagramiXCopyRequestProgress(.acknowledged) == nil, "acknowledgement is not server delivery")
        check(nagramiXCopyRequestProgress(.result(.init(token: 1))) == nil, "server result is final content")
        check(nagramiXCopyRequestProgress(.progress(0.2, 300)) != nil, "packet progress is measured")
        for code in ["FLOOD_WAIT_15", "FLOOD_PREMIUM_WAIT_90"] {
            check(nagramiXCopySendFailureReason(code, isCopy: true) == .flood, "copy RPC flood wait uses native failure reason")
            check(nagramiXCopySendFailureReason(code, isCopy: false) == nil, "ordinary sender keeps its original flood policy")
        }
        check(nagramiXCopySendFailureReason("PEER_FLOOD", isCopy: true) == .flood, "native peer flood remains recognized")
        check(nagramiXCopySendFailureReason("SLOWMODE_WAIT_10", isCopy: true) == .slowmodeActive, "other native failure reasons remain recognized")
        check(nagramiXCopySendFailureReason("UNKNOWN", isCopy: true) == nil, "unknown RPC code is not misreported")

        // The real single-send wrapper must remain pending after an ack and
        // deliver the actual server result, preserving the request identity.
        do {
            FixtureClock.reset()
            let source = PolicyInput<NetworkRequestResult<Api.Updates>, MTRpcError>()
            let connectivity = PolicyInput<ConnectionStatus, NoError>()
            let network = Network(connectivity.signal(.online))
            var results: [Api.Updates] = [], ack = 0, errors: [MTRpcError] = [], completed = 0
            let d = policySingle(copy, source.signal(), network).start(next: { value in
                switch value { case let .result(value): results.append(value); case .acknowledged: ack += 1; case .progress: break }
            }, error: { errors.append($0) }, completed: { completed += 1 })
            FixtureClock.drain()
            source.next(.acknowledged)
            check(ack == 1 && completed == 0 && errors.isEmpty, "RPC ack cannot complete or discard an authored copy")
            FixtureClock.advance(100)
            check(errors.isEmpty, "single RPC keeps its full server-response budget")
            source.next(.result(.init(token: 73)))
            check(results == [.init(token: 73)] && completed == 1 && errors.isEmpty, "actual server result completes copy once")
            check(source.disposed == 1 && connectivity.disposed == 1, "single RPC releases both inputs")
            d.dispose()
        }
        // Only local copies receive the copy watchdog; native repost and the
        // ordinary sender retain their stock waiting/retry policy.
        for message in [native, forward] {
            FixtureClock.reset()
            let source = PolicyInput<NetworkRequestResult<Api.Updates>, MTRpcError>()
            let network = Network(.single(.online))
            var errors = 0
            let d = policySingle(message, source.signal(), network).start(error: { _ in errors += 1 })
            FixtureClock.drain(); FixtureClock.advance(1000)
            check(errors == 0 && source.disposed == 0, "native request is not subject to copy idle watchdog")
            d.dispose()
        }
        for online: ConnectionStatus in [.offline, .connecting] {
            FixtureClock.reset()
            let source = PolicyInput<NetworkRequestResult<Api.Updates>, MTRpcError>()
            let connectivity = PolicyInput<ConnectionStatus, NoError>()
            var errors = 0
            let d = policySingle(copy, source.signal(), Network(connectivity.signal(online)))
                .start(error: { _ in errors += 1 })
            FixtureClock.drain(); FixtureClock.advance(1000)
            check(errors == 0, "offline or connecting request does not exhaust response budget")
            connectivity.next(.online); FixtureClock.advance(120.01)
            check(errors == 1, "online missing RPC result terminates copy")
            d.dispose()
        }
        // A broadcast group is protected only if every member is an authored
        // copy; mixed/native groups keep their original transport policy.
        for messages in [[copy, native], [copy, forward], [native, native]] {
            FixtureClock.reset()
            let source = PolicyInput<Api.Updates, MTRpcError>()
            var errors = 0
            let d = policyGroup(messages, source.signal(), Network(.single(.online)))
                .start(error: { _ in errors += 1 })
            FixtureClock.drain(); FixtureClock.advance(1000)
            check(errors == 0 && source.disposed == 0, "mixed native group keeps stock transport policy")
            d.dispose()
        }
        do {
            FixtureClock.reset()
            let source = PolicyInput<Api.Updates, MTRpcError>()
            var values: [Api.Updates] = [], errors = 0, completed = 0
            let d = policyGroup([copy, copy], source.signal(), Network(.single(.online)))
                .start(next: { values.append($0) }, error: { _ in errors += 1 }, completed: { completed += 1 })
            FixtureClock.drain(); source.next(.init(token: 91))
            check(values == [.init(token: 91)] && completed == 1 && errors == 0, "broadcast retains exact server result")
            d.dispose()
        }
        do {
            FixtureClock.reset()
            let source = PolicyInput<Api.Updates, MTRpcError>()
            var errors: [MTRpcError] = []
            let d = policyGroup([copy, copy], source.signal(), Network(.single(.online)))
                .start(error: { errors.append($0) })
            FixtureClock.drain(); FixtureClock.advance(120.01)
            check(errors.count == 1 && errors[0].errorCode == 408, "broadcast without result has explicit transport error")
            d.dispose()
        }
        print("Local copy request-policy checks: \(checks)")
    }
}
'''


def policy_fixture(source: Path) -> str:
    manager = (source / MANAGER).read_text()
    pieces = [signal_runtime(source), POLICY_BOUNDARY]
    mapping = (source / (SK + 'Signal_Mapping.swift')).read_text()
    for marker in ['public func map<T, E, R>(', 'private class DistinctUntilChangedContext<T>',
                   'public func distinctUntilChanged<T: Equatable, E>(']:
        pieces.append(block(mapping, marker))
    for marker in ['private func nagramiXIsLocalCopyMessage(',
                   'private func nagramiXCopyNetworkIsOnline(',
                   'private func nagramiXCopyUploadProgress(',
                   'private func nagramiXCopyRequestProgress(']:
        pieces.append(block(manager, marker))
    for marker in ['public enum PendingMessageFailureReason', 'func sendMessageReasonForError(',
                   'private func nagramiXCopySendFailureReason(']:
        pieces.append(block(manager, marker))
    for kind, result_type, arguments in [
        ('Single', 'NetworkRequestResult<Api.Updates>', '_ message: Message'),
        ('Group', 'Api.Updates', '_ members: [Message]'),
    ]:
        marker = f'                let copyDeliveryRequest: Signal<{result_type}, MTRpcError>'
        start = manager.index(marker)
        end = manager.index('                |> deliverOn(queue)', start)
        body = manager[start:end]
        body = body.replace('                return copyDeliveryRequest', '                return copyDeliveryRequest')
        setup = 'let messages = members.map { ($0, 0) }\n' if kind == 'Group' else ''
        pieces.append(f'''func policy{kind}({arguments}, _ sendMessageRequest: Signal<{result_type}, MTRpcError>, _ network: Network) -> Signal<{result_type}, MTRpcError> {{
    let queue = Queue.shared
    {setup}
{body}
}}
''')
    pieces.append(POLICY_TESTS)
    return '\n'.join(pieces)


def semantic_negatives(swift: str):
    production = block(swift, 'func nagramiXCopyDeliverySignal<')
    variants = [
        ('empty-completion', 'queue.async { fail(failure) }',
         'queue.async { }', 'empty completion becomes a real failure'),
        ('duplicate-progress', 'valueProgress != lastProgress',
         'true', 'duplicate or invalid progress cannot renew idle budget'),
        ('absolute-timeout', 'lastProgress = valueProgress\n                            remaining = idleTimeout',
         'lastProgress = valueProgress', 'advancing large file has no absolute timeout'),
        ('missing-completion', 'subscriber.putCompletion()',
         '// Incorrectly omit successful completion.', 'content terminates successfully'),
        ('offline-budget', 'online = value', 'online = true',
         'disconnected time pauses existing budget'),
        ('offline-reset', 'online = value\n                    armTimer()',
         'online = value\n                    if online { remaining = idleTimeout }\n                    armTimer()',
         'offline pause does not reset the accumulated online budget'),
        ('suspended-wall-clock', 'elapsed >= 0.0 && elapsed <= max(5.0, tick * 3.0)',
         'elapsed >= 0.0', 'late tick after OS suspension cannot fail resumed copy'),
        ('nonrepeating-idle', 'repeat: true', 'repeat: false',
         'duplicate or invalid progress cannot renew idle budget'),
    ]
    for name, before, after, diagnostic in variants:
        assert production.count(before) == 1, (name, production.count(before))
        replacement = production.replace(before, after)
        if name == 'duplicate-progress':
            replacement = replacement.replace('lastProgress = valueProgress', '_ = lastProgress\n                            lastProgress = valueProgress')
        yield name, swift.replace(production, replacement, 1), diagnostic


def policy_negatives(swift: str):
    variants = [
        ('native-forward', '        && !message.attributes.contains(where: { $0 is ForwardSourceInfoAttribute })',
         '', 'native forward of copied content is not a local-copy RPC'),
        ('premature-ack', 'isContent: { if case .result = $0 { return true }; return false }',
         'isContent: { if case .acknowledged = $0 { return true }; return false }',
         'RPC ack cannot complete or discard an authored copy'),
        ('mixed-group', 'if messages.allSatisfy({ nagramiXIsLocalCopyMessage($0.0) }) {',
         'if messages.contains(where: { nagramiXIsLocalCopyMessage($0.0) }) {',
         'mixed native group keeps stock transport policy'),
    ]
    for name, before, after, diagnostic in variants:
        assert swift.count(before) == 1, (name, swift.count(before))
        yield name, swift.replace(before, after), diagnostic

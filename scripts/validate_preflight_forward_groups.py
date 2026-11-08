#!/usr/bin/env python3
"""Exercise actual multi-source enqueue preparation without an SDK or network."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

LOAD = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
HELPER = 'submodules/TelegramUI/Sources/Chat/NagramiXTemporaryReplySend.swift'
ENQUEUE = 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
COLLECTION_END = '                let _ = (strongSelf.shouldDivertMessagesToScheduled'
QUEUE = '                    let performEnqueue: () -> Void = {'
QUEUE_END = '                    \n                        let _ = (signal'
ORDINARY = '                        } else {\n                            var transformedMessages = transformedMessages'


def read(source, name, baseline):
    path = source / name
    return path.read_text() if path.is_file() else (baseline / name).read_text()


def parts(text):
    start = text.index('                var forwardSourcePeerIds = Set<EnginePeer.Id>()')
    legacy = text.rfind('                var forwardedMessages: [[EnqueueMessage]] = []', 0, start)
    if legacy >= 0:
        start = legacy
    collection = text[start:text.index(COLLECTION_END, start)]
    queue = text[text.index(QUEUE) + len(QUEUE):text.index(QUEUE_END, text.index(QUEUE))]
    return collection, queue


def verify(source, baseline):
    current = read(source, LOAD, baseline)
    previous = (baseline / LOAD).read_text()
    collection, queue = parts(current)
    old_collection, old_queue = parts(previous)
    assert 'var forwardedMessages' not in collection and 'last.append(message)' not in collection
    assert 'if forwardSourcePeerIds.count > 1 {' in queue
    assert 'temporaryReplySend?.includesLocalCopy' not in queue
    assert 'nagramiXTemporaryReplyEnqueueGroups(transformedMessages)' in queue
    assert 'else if forwardSourcePeerIds.count > 1' not in queue
    assert 'var enqueueNext: Signal<[EngineMessage.Id?], NoError> = .single([])' in queue
    assert '|> mapToSignal { accumulated -> Signal<[EngineMessage.Id?], NoError> in' in queue
    assert 'signal = enqueueNext' in queue and 'combineLatest(signals)' not in queue
    # The source count collection and preparation branch are the only changes.
    assert current.replace(collection, old_collection, 1).replace(queue, old_queue, 1) == previous
    ordinary = queue[queue.index(ORDINARY):]
    assert ordinary == old_queue[old_queue.index(ORDINARY):]
    assert '''                    if let temporaryReplySend {
                        temporaryReplySend.beforeEnqueue { allowed in
                            guard allowed else { return }
                            performEnqueue()''' in current
    helper_text = read(source, HELPER, baseline)
    assert helper_text == (baseline / HELPER).read_text(), 'Grouping helper or source ownership changed'
    helper = block(helper_text, 'func nagramiXTemporaryReplyEnqueueGroups(')
    enqueue = read(source, ENQUEUE, baseline)
    assert enqueue == (baseline / ENQUEUE).read_text(), 'Native enqueue API changed'
    native_enqueue = block(enqueue, 'public func enqueueMessages(account: Account, peerId: PeerId, messages: [EnqueueMessage])')
    assert native_enqueue.index('opportunisticallyTransformOutgoingMedia(') < native_enqueue.index('return account.postbox.transaction')
    return current, previous, collection, queue, old_collection, old_queue, helper, enqueue


ADAPTERS = r'''import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
struct MessageId: Hashable { let peerId: Int64; let id: Int32 }
enum EnginePeer { typealias Id = Int64 }
enum EngineMessage { typealias Id = MessageId }
typealias MediaId = Int64
typealias StoryId = Int64
typealias ItemCollectionId = Int64
struct EngineMessageReplySubject { let messageId: MessageId }
protocol Media: AnyObject {}
final class Payload: Media { let name: String; init(_ name: String) { self.name = name } }
struct AnyMediaReference { let media: Media }
protocol MessageAttribute: AnyObject {}
final class PreservedAttribute: MessageAttribute { let value: String; init(_ value: String) { self.value = value } }
final class OutgoingScheduleInfoMessageAttribute: MessageAttribute {
    let scheduleTime: Int32; let repeatPeriod: Int32?
    init(scheduleTime: Int32, repeatPeriod: Int32?) { self.scheduleTime = scheduleTime; self.repeatPeriod = repeatPeriod }
}
enum NoError: Error {}
final class Signal<T, E: Error> {
    let subscribe: (@escaping (T) -> Void) -> Void
    init(_ subscribe: @escaping (@escaping (T) -> Void) -> Void) { self.subscribe = subscribe }
    static func single(_ value: T) -> Signal<T, E> { Signal { next in next(value) } }
    func start(next: @escaping (T) -> Void) { self.subscribe(next) }
}
infix operator |> : AdditionPrecedence
func |> <T, U>(value: T, f: (T) -> U) -> U { f(value) }
func map<T, U, E>(_ f: @escaping (T) -> U) -> (Signal<T, E>) -> Signal<U, E> {
    { signal in Signal { next in signal.start { next(f($0)) } } }
}
func mapToSignal<T, U, E>(_ f: @escaping (T) -> Signal<U, E>) -> (Signal<T, E>) -> Signal<U, E> {
    { signal in Signal { next in signal.start { value in f(value).start(next: next) } } }
}
func combineLatest<T, E>(_ signals: [Signal<T, E>]) -> Signal<[T], E> {
    Signal { next in
        if signals.isEmpty { next([]); return }
        var values = Array<T?>(repeating: nil, count: signals.count)
        for (index, signal) in signals.enumerated() {
            signal.start { value in
                values[index] = value
                if values.allSatisfy({ $0 != nil }) { next(values.map { $0! }) }
            }
        }
    }
}
struct Context { let account = 567 }
final class Controller { let context = Context() }
struct Lease { let includesLocalCopy: Bool }
var captured: [[EnqueueMessage]] = []
var pendingTransactions: [() -> Void] = []
var deferredMedia: [() -> Void] = []
var deferFirstMedia = false
var didDeferMedia = false
var constructedGroups = 0
var subscribedGroups = 0
var nextLocalId: Int32 = 1
func enqueueMessages(account: Int, peerId: Int64, messages: [EnqueueMessage]) -> Signal<[EngineMessage.Id?], NoError> {
    precondition(account == 567 && peerId == 99)
    constructedGroups += 1
    return Signal { next in
        subscribedGroups += 1
        let commit = {
            captured.append(messages)
            let ids = messages.map { _ -> MessageId? in
                defer { nextLocalId += 1 }
                return MessageId(peerId: peerId, id: nextLocalId)
            }
            next(ids)
        }
        let hasMedia = messages.contains { message in
            if case let .message(_, _, _, reference, _, _, _, _, _, _) = message { return reference != nil }
            return false
        }
        if deferFirstMedia && !didDeferMedia && hasMedia {
            didDeferMedia = true
            deferredMedia.append(commit)
        } else {
            pendingTransactions.append(commit)
        }
    }
}
func drainTransactions() {
    while !pendingTransactions.isEmpty || !deferredMedia.isEmpty {
        while !pendingTransactions.isEmpty { pendingTransactions.removeFirst()() }
        if !deferredMedia.isEmpty { deferredMedia.removeFirst()() }
    }
}
var checks = 0
func check(_ value: @autoclosure () -> Bool, _ description: String) {
    checks += 1
    if !value() { print("forward groups regression: " + description); exit(42) }
}
'''


TESTS = r'''
func message(_ text: String, group: Int64? = nil) -> EnqueueMessage {
    let payload = Payload(text)
    return .message(text: text, attributes: [PreservedAttribute("silent/fee/effect/" + text), OutgoingScheduleInfoMessageAttribute(scheduleTime: 123, repeatPeriod: 44)], inlineStickers: [7: payload], mediaReference: AnyMediaReference(media: payload), threadId: 700, replyToMessageId: EngineMessageReplySubject(messageId: MessageId(peerId: 99, id: 5)), replyToStoryId: 88, localGroupingKey: group, correlationId: 900, bubbleUpEmojiOrStickersets: [11, 12])
}
func forward(_ peer: Int64, _ id: Int32) -> EnqueueMessage {
    .forward(source: MessageId(peerId: peer, id: id), threadId: 701, grouping: .auto, attributes: [PreservedAttribute("silent/fee/source/\(peer)/\(id)"), OutgoingScheduleInfoMessageAttribute(scheduleTime: 123, repeatPeriod: 44)], correlationId: 901)
}
func fingerprint(_ value: EnqueueMessage, schedule: Bool) -> String {
    let result: String
    switch value {
    case let .message(text, _, stickers, media, thread, reply, story, grouping, correlation, bubble):
        result = "message:\(text):\(stickers.keys.sorted()):\(stickers.values.map { ObjectIdentifier($0).debugDescription }.sorted()):\(media.map { ObjectIdentifier($0.media).debugDescription } ?? "nil"):\(thread ?? -1):\(reply?.messageId.id ?? -1):\(story ?? -1):\(grouping ?? -1):\(correlation ?? -1):\(bubble)"
    case let .forward(source, thread, grouping, _, correlation):
        result = "forward:\(source.peerId):\(source.id):\(thread ?? -1):\(grouping):\(correlation ?? -1)"
    }
    let kept = value.attributes.compactMap { ($0 as? PreservedAttribute).map { "\(ObjectIdentifier($0)):\($0.value)" } }
    let scheduled = value.attributes.compactMap { $0 as? OutgoingScheduleInfoMessageAttribute }
    check(scheduled.count == 1, "schedule attribute retained or replaced once")
    if schedule {
        let target = Int32(Date().timeIntervalSince1970) + 10 * 24 * 60 * 60
        check(abs(Int64(scheduled[0].scheduleTime) - Int64(target)) <= 3 && scheduled[0].repeatPeriod == nil, "diversion uses native date and repeat policy")
    } else {
        check(scheduled[0].scheduleTime == 123 && scheduled[0].repeatPeriod == 44, "native existing schedule and repeat metadata preserved")
    }
    return result + kept.joined(separator: ",")
}
func expectedGroups(_ values: [EnqueueMessage]) -> [[EnqueueMessage]] {
    let sources = Set(values.compactMap { value -> Int64? in if case let .forward(source, _, _, _, _) = value { return source.peerId }; return nil })
    if sources.count <= 1 { return [values] }
    var groups: [[EnqueueMessage]] = []
    var lastKind: String?
    for value in values {
        let kind: String
        switch value { case .message: kind = "message"; case let .forward(source, _, _, _, _): kind = "source:\(source.peerId)" }
        if kind == lastKind { groups[groups.count - 1].append(value) } else { groups.append([value]) }
        lastKind = kind
    }
    return groups
}
func exercise(_ values: [EnqueueMessage], lease: Lease?, divert: Bool, deferred: Bool = false, verifyCold: Bool = true) {
    captured = []
    pendingTransactions = []; deferredMedia = []
    deferFirstMedia = deferred; didDeferMedia = false
    constructedGroups = 0; subscribedGroups = 0; nextLocalId = 1
    let before = values.map { fingerprint($0, schedule: false) }
    let prepared = run(values, shouldDivert: divert, temporaryReplySend: lease)
    let sources = Set(values.compactMap { value -> Int64? in if case let .forward(source, _, _, _, _) = value { return source.peerId }; return nil })
    if verifyCold && sources.count > 1 { check(constructedGroups == 0, "later batch preparation remains cold until subscription") }
    var result: [EngineMessage.Id?]?
    prepared.0.start { result = $0 }
    if verifyCold && sources.count > 1 {
        check(constructedGroups == 1 && subscribedGroups == 1, "only the first group starts before its local transaction completes")
        check(result == nil && captured.isEmpty, "deferred local enqueue cannot report accepted IDs early")
    }
    drainTransactions()
    let sent = captured.flatMap { $0 }
    check(sent.count == values.count && result?.count == values.count, "all selected items reach the native queue")
    check(sent.map { fingerprint($0, schedule: divert) } == before, "exact item order and every media/topic/reply/group/correlation/fee/silent field preserved")
    check(captured.map { $0.count } == expectedGroups(values).map { $0.count }, "contiguous native source batches preserve albums and repeated peer runs")
    check(result?.compactMap { $0?.id } == Array(1 ... Int32(values.count)), "returned IDs agree with actual local enqueue order")
    check(prepared.1 == divert, "native scheduled-screen policy preserved")
}
let selected = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "all"
if selected == "duplicates" {
    exercise([forward(1, 1), forward(1, 2), forward(2, 3)], lease: nil, divert: false, verifyCold: false)
} else if selected == "comment" {
    exercise([message("comment"), forward(1, 1), forward(2, 3)], lease: nil, divert: false, verifyCold: false)
} else if selected == "async" {
    exercise([message("slow-local-copy"), forward(1, 1), forward(2, 3)], lease: Lease(includesLocalCopy: true), divert: false, deferred: true, verifyCold: false)
} else {
    let scenarios: [[EnqueueMessage]] = [
        [forward(1, 1), forward(1, 2), forward(2, 3)],
        [message("comment"), forward(1, 1), forward(2, 3)],
        [message("copy-a", group: 90), message("copy-b", group: 90), forward(1, 1), forward(2, 3), message("answer")],
        [forward(1, 1), forward(2, 3), forward(1, 2)],
        [forward(1, 1), message("between"), forward(2, 3)],
        [message("single-source-comment"), forward(1, 1), forward(1, 2)],
        [message("ordinary", group: 91), message("ordinary-album", group: 91)],
    ]
    for lease in [Optional<Lease>.none, Lease(includesLocalCopy: false), Lease(includesLocalCopy: true)] {
        for divert in [false, true] {
            for values in scenarios { exercise(values, lease: lease, divert: divert) }
            exercise([message("slow-local-copy"), forward(1, 1), forward(2, 3)], lease: lease, divert: divert, deferred: true)
            exercise([forward(1, 1), message("slow-between"), forward(2, 3), forward(1, 2)], lease: lease, divert: divert, deferred: true)
        }
    }
}
print("PASS production forward enqueue groups: \(checks)")
'''


def fixture(collection, queue, helper, enqueue, mode='current'):
    if mode == 'concurrent-batches':
        start = queue.index('                            // Transform and enqueue each source run only after')
        end = queue.index('                            signal = enqueueNext', start) + len('                            signal = enqueueNext')
        concurrent = '''                            let signals = groups.map { group in
                                enqueueMessages(account: strongSelf.context.account, peerId: peerId, messages: group)
                            }
                            signal = combineLatest(signals)
                            |> map { groups in groups.flatMap { $0 } }'''
        queue = queue[:start] + concurrent + queue[end:]
    if mode == 'drop-message-runs':
        helper = helper.replace('    for message in messages {', '    for message in messages.filter({ if case .forward = $0 { return true }; return false }) {', 1)
    elif mode == 'merge-sources':
        helper = 'func nagramiXTemporaryReplyEnqueueGroups(_ messages: [EnqueueMessage]) -> [[EnqueueMessage]] { return [messages] }'
    native_enum = block(enqueue, 'public enum EnqueueMessage {').replace('public ', '')
    grouping = block(enqueue, 'public enum EnqueueMessageGrouping {').replace('public ', '')
    run = '''func run(_ transformedMessages: [EnqueueMessage], shouldDivert: Bool, temporaryReplySend: Lease?) -> (Signal<[EngineMessage.Id?], NoError>, Bool) {
        let strongSelf = Controller()
        let peerId: Int64 = 99
''' + collection + queue + '''
        return (signal, shouldOpenScheduledMessages)
}
'''
    return ADAPTERS + grouping + '\n' + native_enum + '\n' + helper + '\n' + run + TESTS


def no_core_dump():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def execute(data, swiftc, directory):
    _, _, collection, queue, old_collection, old_queue, helper, enqueue = data
    runs, rejected = [], []
    for optimized in (False, True):
        suffix = 'O' if optimized else 'debug'
        for mode in ('current', 'old', 'concurrent-batches', 'drop-message-runs', 'merge-sources'):
            source = directory / (mode + '-' + suffix + '.swift')
            source.write_text(fixture(old_collection if mode == 'old' else collection, old_queue if mode == 'old' else queue, helper, enqueue, mode))
            binary = source.with_suffix('')
            flags = ['-O'] if optimized else []
            subprocess.run([str(swiftc), '-warnings-as-errors', '-module-cache-path', str(directory / 'cache'), *flags, str(source), '-o', str(binary)], check=True)
            cases = ('duplicates', 'comment', 'async') if mode == 'old' else (('async',) if mode == 'concurrent-batches' else ('all',))
            for case in cases:
                result = subprocess.run([str(binary), case], text=True, capture_output=True, preexec_fn=no_core_dump)
                if mode == 'current':
                    assert result.returncode == 0, result.stdout + result.stderr
                    runs.append({'optimized': optimized, 'result': result.stdout.strip()})
                else:
                    assert result.returncode == 42 and 'forward groups regression:' in result.stdout, result.stdout + result.stderr
                    rejected.append({'optimized': optimized, 'variant': mode, 'case': case, 'diagnostic': result.stdout.strip()})
    return runs, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    data = verify(args.source, args.baseline)
    with tempfile.TemporaryDirectory(prefix='preflight-forward-groups-') as temporary:
        runs, rejected = execute(data, args.swiftc, Path(temporary))
    subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / LOAD)], check=True)
    report = {'production_runs': runs, 'semantic_negatives': rejected,
              'outputs': {LOAD: hashlib.sha256(data[0].encode()).hexdigest()},
              'baseline_sha256': hashlib.sha256(data[1].encode()).hexdigest(),
              'parse_files': 1,
              'source_boundary': 'Complete file reverses exactly after replacing only source collection and queue preparation. Lease validation, native scheduling, UI completion, topic/fee/silent/correlation transformations remain byte-exact.',
              'runtime_boundary': 'Actual collection, enqueue branching, native EnqueueMessage enum/withUpdatedAttributes and existing grouping helper execute. Signals are cold bounded adapters with deferred media callbacks and deferred local queue transactions; actual commit order is checked separately from flattened IDs. No real SignalKit cancellation, Postbox, UIKit, SDK or live delivery.',
              'native_sdk': 'not_run', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

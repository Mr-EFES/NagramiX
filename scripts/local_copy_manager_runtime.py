#!/usr/bin/env python3
"""Исполнить реальный queued-upload маршрут копий с явной границей Postbox."""
import json
from pathlib import Path

from validate_quick_format import block


ROOT = Path(__file__).resolve().parents[1]
MANAGER = 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift'

BOUNDARY = r'''import Foundation

// This fixture tests the actual manager routing method. Signal event delivery,
// the unchanged common starter's database failure write, and Telegram RPC are
// explicit observable adapters. The generic guard is exercised separately with
// the native SignalKit implementation, not reimplemented in this boundary.
protocol Disposable { func dispose() }
final class ActionDisposable: Disposable {
    private var action: (() -> Void)?
    init(_ action: @escaping () -> Void) { self.action = action }
    func dispose() { let f = self.action; self.action = nil; f?() }
}
final class MetaDisposable {
    private var current: Disposable?
    func set(_ value: Disposable) { self.current?.dispose(); self.current = value }
    deinit { self.current?.dispose() }
}
final class Queue { func isCurrent() -> Bool { true } }
precedencegroup PipeRight {
    associativity: left
    higherThan: DefaultPrecedence
}
infix operator |> : PipeRight
func |> <T, U>(value: T, function: (T) -> U) -> U { function(value) }
func deliverOn<T, E>(_ queue: Queue) -> (Signal<T, E>) -> Signal<T, E> { { $0 } }
final class Signal<T, E> {
    struct Handler { let next: ((T) -> Void)?; let error: ((E) -> Void)?; let completed: (() -> Void)? }
    private var handlers: [Int: Handler] = [:]
    private var token = 0
    private var terminated = false
    var starts = 0
    var activeSubscribers: Int { self.handlers.count }
    func start(next: ((T) -> Void)? = nil, error: ((E) -> Void)? = nil, completed: (() -> Void)? = nil) -> Disposable {
        self.starts += 1
        self.token += 1
        let token = self.token
        if !self.terminated { self.handlers[token] = Handler(next: next, error: error, completed: completed) }
        return ActionDisposable { [weak self] in self?.handlers.removeValue(forKey: token) }
    }
    func emit(_ value: T) { for h in Array(self.handlers.values) { h.next?(value) } }
    func fail(_ error: E) {
        let handlers = Array(self.handlers.values)
        self.handlers.removeAll(); self.terminated = true
        for h in handlers { h.error?(error) }
    }
    func complete() {
        let handlers = Array(self.handlers.values)
        self.handlers.removeAll(); self.terminated = true
        for h in handlers { h.completed?() }
    }
}
typealias PeerId = Int64
struct MessageId: Hashable, Comparable {
    let peerId: PeerId
    let id: Int
    static func < (lhs: Self, rhs: Self) -> Bool { (lhs.peerId, lhs.id) < (rhs.peerId, rhs.id) }
}
protocol MessageAttribute {}
struct OutgoingContentInfoFlags: OptionSet {
    let rawValue: Int
    static let nagramiXCopy = Self(rawValue: 2)
    static let disableLinkPreviews = Self(rawValue: 1)
}
final class OutgoingContentInfoMessageAttribute: MessageAttribute {
    let flags: OutgoingContentInfoFlags
    init(flags: OutgoingContentInfoFlags) { self.flags = flags }
}
final class ForwardSourceInfoAttribute: MessageAttribute {}
final class OtherAttribute: MessageAttribute {}
struct Message { let attributes: [MessageAttribute] }
enum PendingMessageUploadError { case generic }
enum PendingMessageUploadedContentType { case media, text }
struct PendingMessageUploadedContentProgress { let progress: Float }
struct PendingMessageUploadedContentAndReuploadInfo { let token: Int }
enum PendingMessageUploadedContentResult {
    case progress(PendingMessageUploadedContentProgress)
    case content(PendingMessageUploadedContentAndReuploadInfo)
}
struct PendingMessageStatus {
    struct Progress {
        let progress: Float
        init(progress: Float) { self.progress = progress }
        init(_ value: PendingMessageUploadedContentProgress) { self.progress = value.progress }
    }
    let isRunning: Bool
    let progress: Progress
}
struct PeerActivitySpace: Equatable {
    enum Category: Equatable { case global, thread(Int64) }
    let peerId: PeerId
    let category: Category
}
enum PendingMessageState {
    case none
    case waitingForUploadToStart(groupId: Int64?, upload: Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>)
    case uploading(groupId: Int64?)
    case waitingToBeSent(groupId: Int64?, content: PendingMessageUploadedContentAndReuploadInfo)
    case sending
}
final class Subscribers {
    var values: [(PendingMessageStatus?, Int?) -> Void] = []
    func copyItems() -> [(PendingMessageStatus?, Int?) -> Void] { self.values }
}
final class PendingMessageContext {
    var state: PendingMessageState = .none
    let uploadDisposable = MetaDisposable()
    var threadId: Int64?
    var contentType: PendingMessageUploadedContentType?
    var nagramiXIsCopiedMessage = false
    var postponeSending = false
    var status: PendingMessageStatus?
    var error: Int?
    let statusSubscribers = Subscribers()
}
struct StartRecord: Equatable {
    let id: MessageId
    let thread: Int64?
    let group: Int64?
}
final class ManagerBoundary {
    let queue = Queue()
    var messageContexts: [MessageId: PendingMessageContext] = [:]
    var commonStarts: [StartRecord] = []
    var sent: [StartRecord] = []
    var failures: [MessageId] = []
    var groups: [Int64] = []
    var activities: [PeerActivitySpace] = []
    var pendingUpdates = 0
    func canBeginUploadingMessage(id: MessageId, type: PendingMessageUploadedContentType) -> Bool {
        !self.messageContexts.contains { otherId, context in
            guard otherId.peerId == id.peerId else { return false }
            if case .uploading = context.state { return true }
            return false
        }
    }
    func addContextActivityIfNeeded(_ context: PendingMessageContext, peerId: PeerActivitySpace) {
        self.activities.append(peerId)
    }
    func updatePendingMediaUploads() { self.pendingUpdates += 1 }
    func beginSendingGroupIfPossible(groupId: Int64) { self.groups.append(groupId) }
    func beginSendingMessage(messageContext: PendingMessageContext, messageId: MessageId, groupId: Int64?, content: PendingMessageUploadedContentAndReuploadInfo) {
        self.sent.append(StartRecord(id: messageId, thread: messageContext.threadId, group: groupId))
        if let groupId { messageContext.state = .waitingToBeSent(groupId: groupId, content: content) }
        else { messageContext.state = .sending }
    }
    // The ordinary production failure writer is required to stay unchanged.
    // This adapter observes the same-ID failure transition for the routing
    // scenarios below. The real atomic group writer has a separate fixture;
    // this adapter does not claim to run Postbox or that transaction.
    func beginUploadingMessage(messageContext: PendingMessageContext, id: MessageId, threadId: Int64?, groupId: Int64?, uploadSignal: Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>) {
        self.commonStarts.append(StartRecord(id: id, thread: threadId, group: groupId))
        messageContext.state = .uploading(groupId: groupId)
        messageContext.status = PendingMessageStatus(isRunning: true, progress: .init(progress: 0))
        for f in messageContext.statusSubscribers.copyItems() { f(messageContext.status, messageContext.error) }
        self.addContextActivityIfNeeded(messageContext, peerId: .init(peerId: id.peerId, category: threadId.map(PeerActivitySpace.Category.thread) ?? .global))
        self.updatePendingMediaUploads()
        messageContext.uploadDisposable.set(uploadSignal.start(next: { [weak self, weak messageContext] next in
            guard let self, let messageContext else { return }
            switch next {
            case let .progress(progress):
                messageContext.status = PendingMessageStatus(isRunning: true, progress: .init(progress))
                for f in messageContext.statusSubscribers.copyItems() { f(messageContext.status, messageContext.error) }
                self.updatePendingMediaUploads()
            case let .content(content):
                self.beginSendingMessage(messageContext: messageContext, messageId: id, groupId: groupId, content: content)
                self.updateWaitingUploads(peerId: id.peerId)
                if let groupId { self.beginSendingGroupIfPossible(groupId: groupId) }
            }
        }, error: { [weak self, weak messageContext] _ in
            guard let self, let messageContext else { return }
            self.failures.append(id)
            messageContext.state = .none
            messageContext.status = nil
            self.updateWaitingUploads(peerId: id.peerId)
        }))
    }
'''

TESTS = r'''
    func run(_ peerId: PeerId) { self.updateWaitingUploads(peerId: peerId) }
}
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    if !condition() { FileHandle.standardError.write(Data((label + "\n").utf8)); exit(93) }
    checks += 1
}
typealias UploadSignal = Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>
@main struct LocalCopyManagerTests {
    static func main() {
        for copy in [false, true] {
            for forward in [false, true] {
                for preview in [false, true] {
                    var flags: OutgoingContentInfoFlags = []
                    if copy { flags.insert(.nagramiXCopy) }
                    if preview { flags.insert(.disableLinkPreviews) }
                    var attributes: [MessageAttribute] = [OutgoingContentInfoMessageAttribute(flags: flags), OtherAttribute()]
                    if forward { attributes.append(ForwardSourceInfoAttribute()) }
                    check(nagramiXIsLocalCopyMessage(Message(attributes: attributes)) == (copy && !forward), "native forward of copied content stays outside copy policy")
                }
            }
        }
        check(!nagramiXIsLocalCopyMessage(Message(attributes: [])), "message without copy metadata keeps native policy")
        func add(_ manager: ManagerBoundary, _ id: MessageId, copy: Bool, group: Int64? = nil, thread: Int64? = nil, postpone: Bool = false) -> (PendingMessageContext, UploadSignal) {
            let signal = UploadSignal()
            let context = PendingMessageContext()
            context.nagramiXIsCopiedMessage = copy
            context.threadId = thread; context.postponeSending = postpone
            context.state = .waitingForUploadToStart(groupId: group, upload: signal)
            manager.messageContexts[id] = context
            return (context, signal)
        }
        for thread: Int64? in [nil, 17] {
            for group: Int64? in [nil, 81] {
                let manager = ManagerBoundary()
                let first = MessageId(peerId: 2, id: 1), next = MessageId(peerId: 2, id: 2)
                let (context, signal) = add(manager, first, copy: true, group: group, thread: thread)
                let (following, nextSignal) = add(manager, next, copy: true)
                var statuses: [Float] = []
                context.statusSubscribers.values.append { status, _ in if let status { statuses.append(status.progress.progress) } }
                manager.run(2)
                check(manager.commonStarts == [.init(id: first, thread: thread, group: group)], "queued copy uses common error-handling starter")
                check(signal.starts == 1 && nextSignal.starts == 0, "queued copy admits exactly one active upload")
                check(context.status?.isRunning == true && statuses == [0], "shared starter publishes running status")
                check(manager.activities == [.init(peerId: 2, category: thread.map(PeerActivitySpace.Category.thread) ?? .global)], "copy thread activity is preserved")
                manager.run(2)
                check(signal.starts == 1 && nextSignal.starts == 0, "repeated pump cannot duplicate active copy")
                signal.emit(.progress(.init(progress: 0.25)))
                check(statuses == [0, 0.25] && context.status?.progress.progress == 0.25, "copy progress reaches subscribers")
                // The actual SignalKit guard independently turns empty or idle
                // completion into this failure event. Here it must reach the
                // common database-failure path selected by production routing.
                signal.fail(.generic)
                check(manager.failures == [first], "queued copy failure reaches common failure consumer")
                check(nextSignal.starts == 1 && manager.commonStarts.map { $0.id } == [first, next], "failed copy releases next copy for the same peer")
                if case .uploading = following.state {} else { check(false, "next copy begins after failed predecessor") }
                nextSignal.emit(.content(.init(token: 200)))
                check(manager.sent.map { $0.id } == [next], "copy final content preserves pending message identity")
            }
        }
        do {
            let manager = ManagerBoundary()
            let late = MessageId(peerId: 2, id: 100), early = MessageId(peerId: 2, id: 1)
            let (_, laterSignal) = add(manager, late, copy: true)
            let (_, firstSignal) = add(manager, early, copy: true)
            let (_, otherSignal) = add(manager, .init(peerId: 3, id: 0), copy: true)
            manager.run(2)
            check(manager.commonStarts.map { $0.id } == [early], "queue preserves sorted order independent of insertion")
            check(firstSignal.starts == 1 && laterSignal.starts == 0 && otherSignal.starts == 0, "queue filters the selected peer")
        }
        do {
            let manager = ManagerBoundary()
            let first = MessageId(peerId: 2, id: 1)
            let (context, signal) = add(manager, first, copy: true, postpone: true)
            let (_, following) = add(manager, .init(peerId: 2, id: 2), copy: true)
            manager.run(2)
            check(manager.commonStarts.isEmpty && signal.starts == 0 && following.starts == 0, "postponed copy does not jump send gate")
            context.postponeSending = false; manager.run(2)
            check(signal.starts == 1 && following.starts == 0, "committing postponed copy enters same shared starter")
        }
        do {
            let manager = ManagerBoundary()
            let busy = PendingMessageContext(); busy.state = .uploading(groupId: nil)
            manager.messageContexts[.init(peerId: 2, id: 0)] = busy
            let (_, signal) = add(manager, .init(peerId: 2, id: 1), copy: true)
            manager.run(2); check(signal.starts == 0, "existing peer upload keeps copy waiting")
            busy.state = .none; manager.run(2)
            check(signal.starts == 1, "copy can enter after existing upload ends")
        }
        do {
            let manager = ManagerBoundary()
            let busy = PendingMessageContext(); busy.state = .uploading(groupId: nil)
            manager.messageContexts[.init(peerId: 2, id: 0)] = busy
            let (context, signal) = add(manager, .init(peerId: 2, id: 1), copy: true)
            context.contentType = .text
            manager.run(2)
            check(signal.starts == 1, "text copy preserves native priority over media upload")
        }
        do {
            let manager = ManagerBoundary()
            let busy = PendingMessageContext(); busy.state = .uploading(groupId: nil)
            manager.messageContexts[.init(peerId: 2, id: 100)] = busy
            let (_, signal) = add(manager, .init(peerId: 2, id: 1), copy: true)
            manager.run(2)
            check(signal.starts == 1, "earlier copy preserves native admission before later active upload")
        }
        for thread: Int64? in [nil, 9] {
            for group: Int64? in [nil, 72] {
                let manager = ManagerBoundary()
                let id = MessageId(peerId: 4, id: 1)
                let (context, signal) = add(manager, id, copy: false, group: group, thread: thread)
                var statuses: [Float] = []
                context.statusSubscribers.values.append { status, _ in if let status { statuses.append(status.progress.progress) } }
                manager.run(4)
                check(manager.commonStarts.isEmpty && signal.starts == 1, "ordinary queued message preserves native starter")
                signal.emit(.progress(.init(progress: 0.5)))
                check(statuses == [0, 0.5], "ordinary queued message preserves native progress")
                signal.emit(.content(.init(token: 12)))
                check(manager.sent == [.init(id: id, thread: thread, group: group)], "ordinary content route preserves identifiers")
                check(manager.groups == group.map { [$0] } ?? [], "ordinary album send gate is preserved")
                check(manager.activities == [.init(peerId: 4, category: thread.map(PeerActivitySpace.Category.thread) ?? .global)], "ordinary thread activity is preserved")
            }
        }
        do {
            let manager = ManagerBoundary()
            let first = MessageId(peerId: 2, id: 1)
            let (_, signal) = add(manager, first, copy: true, group: 91, thread: 7)
            manager.run(2); signal.emit(.content(.init(token: 50)))
            check(manager.sent == [.init(id: first, thread: 7, group: 91)] && manager.groups == [91], "copy grouped content reaches its existing group gate")
        }
        print("Queued local-copy manager routing checks: \(checks)")
    }
}
'''


def production_boundary(source):
    text = (source / MANAGER).read_text()
    adapter = block(BOUNDARY, '    func canBeginUploadingMessage(')
    production = block(text, '    private func canBeginUploadingMessage(')
    return BOUNDARY.replace(adapter, production.replace('    private func', '    func', 1), 1)


def fixture(source):
    text = (source / MANAGER).read_text()
    method = block(text, '    private func updateWaitingUploads(')
    assert 'context.nagramiXIsCopiedMessage' in method, 'copy route is not implemented yet'
    plan = json.loads((ROOT / 'ios/local_copy_delivery_patches.json').read_text())
    before = (ROOT / 'ios' / plan['previous'][MANAGER]).read_text()
    # The copy-specific group branch is the only permitted change to this
    # mature starter. The ordinary Postbox failure writer stays byte-identical.
    marker = '    private func beginUploadingMessage('
    common = block(text, marker)
    capture = '        let nagramiXIsCopiedUpload = messageContext.nagramiXIsCopiedMessage\n'
    assert common.count(capture) == 1
    branch = block(common, '                if nagramiXIsCopiedUpload, let groupId {')
    expected_branch = '''                if nagramiXIsCopiedUpload, let groupId {
                    let ids = strongSelf.messageContexts.compactMap { entry -> MessageId? in
                        return entry.key.peerId == id.peerId && entry.key.namespace == id.namespace && entry.value.state.groupId == groupId ? entry.key : nil
                    }
                    return nagramiXFailCopiedUploadGroup(postbox: strongSelf.postbox, failedId: id, groupId: groupId, threadId: threadId, contextIds: ids)
                }'''
    assert branch == expected_branch, 'unexpected copy group failure branch'
    native_common = common.replace(capture, '', 1).replace(branch, '', 1)
    normalize = lambda value: '\n'.join(line.rstrip() for line in value.splitlines() if line.strip())
    assert normalize(native_common) == normalize(block(before, marker)), 'ordinary common upload starter changed'
    marker = '    func updatePendingMessageIds('
    assert block(text, marker) == block(before, marker), 'database removal queue drain changed'
    copy_route = block(method, '                    if context.nagramiXIsCopiedMessage {')
    native_after = method.replace(copy_route, '', 1)
    native_before = block(before, '    private func updateWaitingUploads(')
    assert normalize(native_after) == normalize(native_before), 'ordinary queued upload path changed'
    detection = block(text, 'private func nagramiXIsLocalCopyMessage(')
    return production_boundary(source) + method.replace('    private func', '    func', 1) + TESTS + '\n' + detection


def semantic_negatives(swift):
    marker = 'if context.nagramiXIsCopiedMessage {'
    assert swift.count(marker) == 1
    yield ('queued-copy-common-starter', swift.replace(marker, 'if false {', 1),
           'queued copy uses common error-handling starter')
    marker = '&& !message.attributes.contains(where: { $0 is ForwardSourceInfoAttribute })'
    assert swift.count(marker) == 1
    yield ('native-forward-scope', swift.replace(marker, '', 1),
           'native forward of copied content stays outside copy policy')


ADMISSION_TYPES = r'''
enum NoError {}
enum ConnectionStatus { case online, connecting }
final class Network {
    let connectionStatus = Signal<ConnectionStatus, NoError>()
    init() { self.connectionStatus.owner = ObjectIdentifier(self) }
}
func map<T, E, R>(_ f: @escaping (T) -> R) -> (Signal<T, E>) -> Signal<R, E> {
    { source in let result = Signal<R, E>(); result.owner = source.owner; return result }
}
func distinctUntilChanged<T: Equatable, E>(_ source: Signal<T, E>) -> Signal<T, E> { source }
struct GuardRecord {
    let original: ObjectIdentifier
    let wrapped: ObjectIdentifier
    let queue: ObjectIdentifier
    let network: ObjectIdentifier?
    let idleTimeout: Double
    let retainedWrapper: AnyObject
}
var deliveryGuards: [GuardRecord] = []
// This boundary records admission into the separately tested real SignalKit
// guard. It intentionally supplies no `network` global: the extracted escaping
// production closure must qualify the property through its captured owner.
func nagramiXCopyDeliverySignal<T, E>(_ source: Signal<T, E>, queue: Queue,
    isOnline: Signal<Bool, NoError>, idleTimeout: Double,
    progress: @escaping (T) -> Double?, isContent: @escaping (T) -> Bool,
    failure: E) -> Signal<T, E> {
    let wrapped = Signal<T, E>()
    deliveryGuards.append(.init(original: ObjectIdentifier(source), wrapped: ObjectIdentifier(wrapped),
        queue: ObjectIdentifier(queue), network: isOnline.owner, idleTimeout: idleTimeout, retainedWrapper: wrapped))
    return wrapped
}
struct PaidStarsAttribute { let postponeSending: Bool }
'''

ADMISSION_TESTS = r'''
    func admission(_ messagesToUpload: [(PendingMessageContext, Message, PendingMessageUploadedContentType, Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>)]) -> () -> Void {
        return { [weak self] in
            guard let strongSelf = self else { return }
'''

ADMISSION_AFTER = r'''
        }
    }
}
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    if !condition() { FileHandle.standardError.write(Data((label + "\n").utf8)); exit(93) }
    checks += 1
}
@main struct LocalCopyAdmissionTests {
    static func main() {
        typealias Upload = Signal<PendingMessageUploadedContentResult, PendingMessageUploadError>
        for copy in [false, true] {
            for forward in [false, true] {
                for blocked in [false, true] {
                    for paidPostpone in [false, true] {
                        deliveryGuards = []
                        let manager = ManagerBoundary()
                        let id = MessageId(peerId: 4, id: 10)
                        let context = PendingMessageContext()
                        context.nagramiXIsCopiedMessage = !copy // stale state must be overwritten
                        context.threadId = 12
                        manager.messageContexts[id] = context
                        if blocked {
                            let busy = PendingMessageContext(); busy.state = .uploading(groupId: nil)
                            manager.messageContexts[.init(peerId: 4, id: 0)] = busy
                        }
                        let source = Upload()
                        var attributes: [MessageAttribute] = [OtherAttribute()]
                        if copy { attributes.append(OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])) }
                        if forward { attributes.append(ForwardSourceInfoAttribute()) }
                        let message = Message(attributes: attributes, id: id, threadId: 12, groupingKey: 84,
                            paidStarsAttribute: paidPostpone ? .init(postponeSending: true) : nil)
                        let action = manager.admission([(context, message, .media, source)])
                        action()
                        let expectedCopy = copy && !forward
                        check(context.nagramiXIsCopiedMessage == expectedCopy, "admission refreshes copy flag and excludes native forward")
                        check(deliveryGuards.count == (expectedCopy ? 1 : 0), "only local copies enter upload watchdog")
                        let expectedSignal: ObjectIdentifier
                        if expectedCopy {
                            let guarded = deliveryGuards[0]
                            expectedSignal = guarded.wrapped
                            check(guarded.original == ObjectIdentifier(source), "watchdog wraps the original upload signal")
                            check(guarded.queue == ObjectIdentifier(manager.queue) && guarded.network == ObjectIdentifier(manager.network), "watchdog captures this manager network and queue")
                            check(guarded.idleTimeout == 60, "upload uses its specified idle interval")
                        } else { expectedSignal = ObjectIdentifier(source) }
                        check(manager.postponed == (paidPostpone ? [id] : []), "admission preserves paid postpone commit")
                        if blocked || paidPostpone {
                            check(manager.commonStarts.isEmpty && source.starts == 0, "admission retains blocked or postponed copy")
                            if case let .waitingForUploadToStart(group, upload) = context.state {
                                check(group == 84 && ObjectIdentifier(upload) == expectedSignal, "queued state retains exact guarded signal and group")
                            } else { check(false, "admission keeps pending state") }
                        } else {
                            check(manager.commonStarts == [.init(id: id, thread: 12, group: 84)], "immediate admission preserves pending identity thread and group")
                            check(manager.startedSignals == [expectedSignal], "admission starts the selected native or guarded signal")
                        }
                    }
                }
            }
        }
        do {
            deliveryGuards = []
            let manager = ManagerBoundary()
            var list: [(PendingMessageContext, Message, PendingMessageUploadedContentType, Upload)] = []
            for peer: Int64 in [4, 5] {
                let context = PendingMessageContext(), id = MessageId(peerId: peer, id: 1)
                manager.messageContexts[id] = context
                list.append((context, Message(attributes: [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])],
                    id: id, threadId: nil, groupingKey: nil, paidStarsAttribute: nil), .media, Upload()))
            }
            manager.admission(list)()
            check(deliveryGuards.count == 2 && Set(deliveryGuards.map { $0.wrapped }).count == 2, "recipient copies receive independent guarded subscriptions")
            check(manager.commonStarts.map { $0.id.peerId } == [4, 5], "admission preserves recipient isolation")
        }
        print("Local-copy escaping admission checks: \(checks)")
    }
}
'''


def admission_fixture(source):
    text = (source / MANAGER).read_text()
    loop = block(text, '                for (messageContext, message, type, originalUploadSignal) in messagesToUpload {')
    assert 'isOnline: nagramiXCopyNetworkIsOnline(strongSelf.network)' in loop
    boundary = production_boundary(source)
    boundary = boundary.replace('    var starts = 0', '    var starts = 0\n    var owner: ObjectIdentifier?')
    old = 'struct Message { let attributes: [MessageAttribute] }'
    new = '''struct Message {
    let attributes: [MessageAttribute]
    var id: MessageId = .init(peerId: 0, id: 0)
    var threadId: Int64? = nil
    var groupingKey: Int64? = nil
    var paidStarsAttribute: PaidStarsAttribute? = nil
}'''
    assert boundary.count(old) == 1
    boundary = boundary.replace(old, new)
    boundary = boundary.replace('struct PendingMessageUploadedContentProgress { let progress: Float }',
        'struct PendingMessageUploadedContentProgress { enum Phase { case processing, uploading }; var phase: Phase = .uploading; let progress: Float }')
    marker = 'final class ManagerBoundary {'
    assert boundary.count(marker) == 1
    boundary = boundary.replace(marker, ADMISSION_TYPES + marker)
    boundary = boundary.replace('    let queue = Queue()', '    let queue = Queue()\n    let network = Network()\n    var startedSignals: [ObjectIdentifier] = []\n    var postponed: [MessageId] = []\n    func beginWaitingForPostponedMessageCommit(messageContext: PendingMessageContext, id: MessageId) { self.postponed.append(id); messageContext.postponeSending = true }')
    marker = '        self.commonStarts.append(StartRecord(id: id, thread: threadId, group: groupId))'
    assert boundary.count(marker) == 1
    boundary = boundary.replace(marker, marker + '\n        self.startedSignals.append(ObjectIdentifier(uploadSignal))')
    queue = block(text, '    private func updateWaitingUploads(').replace('    private func', '    func', 1)
    helpers = '\n'.join(block(text, marker) for marker in (
        'private func nagramiXIsLocalCopyMessage(', 'private func nagramiXCopyNetworkIsOnline(',
        'private func nagramiXCopyUploadProgress('))
    return boundary + queue + ADMISSION_TESTS + loop + ADMISSION_AFTER + '\n' + helpers


def admission_capture_negative(swift):
    marker = 'isOnline: nagramiXCopyNetworkIsOnline(strongSelf.network)'
    assert swift.count(marker) == 1
    return ('escaping-upload-network-capture', swift.replace(marker, 'isOnline: nagramiXCopyNetworkIsOnline(network)', 1),
            "reference to property 'network'")


def failure_reason_fixture(source):
    text = (source / MANAGER).read_text()
    helpers = '\n'.join(block(text, marker) for marker in (
        'public enum PendingMessageFailureReason {', 'func sendMessageReasonForError(',
        'private func nagramiXCopySendFailureReason('))
    return 'import Foundation\n' + helpers + r'''
@main struct CopyFailureReasonTests {
    static func main() {
        var checks = 0
        func name(_ value: PendingMessageFailureReason?) -> String { value.map { String(describing: $0) } ?? "nil" }
        let ordinary = ["PEER_FLOOD", "SENDING_TOO_FAST", "USER_BANNED_IN_CHANNEL", "CHAT_SEND_MEDIA_FORBIDDEN", "SLOWMODE_WAIT_20", "SCHEDULE_TOO_MUCH", "VOICE_MESSAGES_FORBIDDEN", "PRIVACY_PREMIUM_REQUIRED", "NETWORK_ERROR", "NAGRAMIX_COPY_SEND_INCOMPLETE"]
        for error in ordinary {
            for isCopy in [false, true] {
                precondition(name(nagramiXCopySendFailureReason(error, isCopy: isCopy)) == name(sendMessageReasonForError(error)))
                checks += 1
            }
        }
        for error in ["FLOOD_WAIT_1", "FLOOD_WAIT_900", "FLOOD_PREMIUM_WAIT_30"] {
            precondition(name(nagramiXCopySendFailureReason(error, isCopy: true)) == "flood")
            precondition(name(nagramiXCopySendFailureReason(error, isCopy: false)) == name(sendMessageReasonForError(error)))
            checks += 2
        }
        print("Local-copy native error reason checks: \(checks)")
    }
}
'''


GROUP_BOUNDARY = r'''import Foundation
struct MessageId: Hashable, Comparable {
    let peerId: Int64
    let id: Int
    static func < (lhs: Self, rhs: Self) -> Bool { (lhs.peerId, lhs.id) < (rhs.peerId, rhs.id) }
}
struct Message { let groupingKey: Int64? }
struct PendingMessageUploadedContentAndReuploadInfo { let token: Int }
enum PendingMessageState {
    case none
    case waitingForForwardSendGate
    case collectingInfo(message: Message)
    case waitingForUploadToStart(groupId: Int64?, upload: Int)
    case uploading(groupId: Int64?)
    case waitingToBeSent(groupId: Int64?, content: PendingMessageUploadedContentAndReuploadInfo)
    case waitingForSendGate(groupId: Int64?, content: PendingMessageUploadedContentAndReuploadInfo)
    case sending(groupId: Int64?)
    case waitingForNewTopic(message: Message)
}
final class PendingMessageContext {
    var state: PendingMessageState
    init(_ state: PendingMessageState) { self.state = state }
}
final class CopyGroupGateBoundary {
    var messageContexts: [MessageId: PendingMessageContext] = [:]
    var committed: [[MessageId]] = []
    func commitSendingMessageGroup(groupId: Int64, messages: [(messageContext: PendingMessageContext, messageId: MessageId, content: PendingMessageUploadedContentAndReuploadInfo)]) {
        self.committed.append(messages.map { $0.messageId }.sorted())
        for member in messages { member.messageContext.state = .sending(groupId: groupId) }
    }
    // Postbox's unchanged pending-set observer clears all removed contexts
    // before it pumps any affected group. The production atomic writer itself
    // executes in another fixture; this method models its one view update.
    func pendingSetRemoved(_ ids: [MessageId]) {
        for id in ids { self.messageContexts[id]?.state = .none }
    }
'''

GROUP_TESTS = r'''
    func members(_ group: Int64) -> [MessageId]? { self.dataForPendingMessageGroup(group)?.map { $0.messageId }.sorted() }
    func pump(_ group: Int64) { self.beginSendingGroupIfPossible(groupId: group) }
}
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    if !condition() { FileHandle.standardError.write(Data((label + "\n").utf8)); exit(93) }
    checks += 1
}
@main struct CopyGroupGateTests {
    static func main() {
        let a = MessageId(peerId: 4, id: 10), b = MessageId(peerId: 4, id: 11)
        let unrelated = MessageId(peerId: 5, id: 30), group: Int64 = 81
        let ready = PendingMessageUploadedContentAndReuploadInfo(token: 7)
        func pair() -> CopyGroupGateBoundary {
            let manager = CopyGroupGateBoundary()
            manager.messageContexts[a] = .init(.waitingToBeSent(groupId: group, content: ready))
            manager.messageContexts[b] = .init(.uploading(groupId: group))
            manager.messageContexts[unrelated] = .init(.uploading(groupId: group + 1))
            return manager
        }
        do {
            let manager = pair()
            check(manager.members(group) == nil, "ready sibling waits for the uploading member")
            manager.pump(group)
            check(manager.committed.isEmpty, "uploading copy blocks partial group commit")
            // Receiving the upload failure must not clear the blocking state
            // before the complete Postbox transaction becomes visible.
            manager.pump(group)
            check(manager.committed.isEmpty, "failed upload remains blocking until atomic view update")
            let atomicallyRemoved = [a, b]
            manager.pendingSetRemoved(atomicallyRemoved)
            check(manager.members(group) == nil, "atomic failure leaves no ready album remainder")
            manager.pump(group)
            check(manager.committed.isEmpty, "atomic failed copy album never sends a partial post")
            if case .uploading = manager.messageContexts[unrelated]!.state {} else {
                check(false, "other recipient group remains untouched")
            }
        }
        do {
            // This is the old single-ID failure control: the native collector
            // really would send the survivor, proving why the writer is atomic.
            let manager = pair()
            manager.pendingSetRemoved([b])
            check(manager.members(group) == [a], "control reproduces old partial album candidate")
            manager.pump(group)
            check(manager.committed == [[a]], "control reproduces old partial album send")
        }
        let blockers: [PendingMessageState] = [
            .collectingInfo(message: .init(groupingKey: group)),
            .waitingForUploadToStart(groupId: group, upload: 9),
            .uploading(groupId: group), .sending(groupId: group),
            .waitingForNewTopic(message: .init(groupingKey: group))
        ]
        for blocker in blockers {
            let manager = pair(); manager.messageContexts[b]!.state = blocker
            check(manager.members(group) == nil, "each unfinished member preserves native group gate")
            manager.pump(group)
            check(manager.committed.isEmpty, "no unfinished copy group commits")
        }
        for state: PendingMessageState in [
            .waitingToBeSent(groupId: group, content: ready),
            .waitingForSendGate(groupId: group, content: ready)
        ] {
            let manager = pair(); manager.messageContexts[b]!.state = state
            check(manager.members(group) == [a, b], "ready copy album retains every member")
            manager.pump(group)
            check(manager.committed == [[a, b]], "fully ready group commits complete post")
            manager.pump(group)
            check(manager.committed.count == 1, "sending album cannot commit twice")
        }
        do {
            let manager = pair()
            manager.pendingSetRemoved([a, b])
            check(manager.members(group) == nil, "empty group cannot become a valid send")
        }
        print("Local-copy atomic album gate checks: \(checks)")
    }
}
'''


def group_gate_fixture(source):
    text = (source / MANAGER).read_text()
    methods = '\n'.join(block(text, marker) for marker in (
        '    private func beginSendingGroupIfPossible(',
        '    private func dataForPendingMessageGroup('))
    return GROUP_BOUNDARY + methods + GROUP_TESTS


def group_gate_negatives(swift):
    marker = 'let atomicallyRemoved = [a, b]'
    assert swift.count(marker) == 1
    yield ('partial-removal-boundary', swift.replace(marker, 'let atomicallyRemoved = [b]', 1),
           'atomic failure leaves no ready album remainder')
    marker = '''            case let .uploading(contextGroupId):
                if contextGroupId == groupId {
                    return nil
                }'''
    assert swift.count(marker) == 1
    yield ('uploading-member-gate', swift.replace(marker, '''            case let .uploading(contextGroupId):
                _ = contextGroupId''', 1), 'ready sibling waits for the uploading member')

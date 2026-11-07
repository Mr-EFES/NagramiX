#!/usr/bin/env python3
"""Exercise the actual acknowledgement method and its deferred caller.

SDK183 proved the previous nested expression still timed out. This check does
not claim to reproduce a whole TelegramUI type-check timeout on Linux. UIKit
and asynchronous delivery are explicit boundaries; the full Apple SDK is final.
"""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile
import textwrap

from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks
from validate_upstream_13_2_release_ui_compile import braced

STAGE = 'upstream_13_2_release_ack_compile'
COPY = 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift'
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
PROTOCOL = 'submodules/AccountContext/Sources/PeerSelectionController.swift'


def check_move(before, after):
    old = before[FORWARD]
    at = old.index('next: { [weak self] (accepted: [[EngineMessage.Id?]]) in')
    callback = braced(old, at)
    prefix = 'next: { [weak self] (accepted: [[EngineMessage.Id?]]) in\n'
    body = textwrap.dedent(callback[len(prefix):-1]).strip()
    body = body.removeprefix('guard let self else { return }\n')
    body = body.replace('let ids: [EngineMessage.Id?] = accepted.indices.contains(index) ? accepted[index] : []', 'var ids: [EngineMessage.Id?] = []\n    if index < accepted.count {\n        ids = accepted[index]\n    }')
    body = body.replace('for index in peers.indices {', 'for index in 0 ..< peers.count {')
    method = block(after[COPY], '    func nagramiXHandleCopyEnqueued(')
    actual_body = textwrap.dedent(method[method.index('{') + 1:-1]).strip()
    assert actual_body == body, 'Acknowledgement behavior changed during extraction'
    assert after[COPY] == before[COPY].rstrip() + '\n\nextension ChatControllerImpl {\n' + method + '\n}\n'
    new_at = after[FORWARD].index('next: { [weak self] (accepted: [[EngineMessage.Id?]]) in')
    new_callback = braced(after[FORWARD], new_at)
    assert new_callback.count('nagramiXHandleCopyEnqueued(') == 1
    assert 'for index' not in new_callback and 'accepted[' not in new_callback and 'contains' not in new_callback
    restored = after[FORWARD][:new_at] + callback + after[FORWARD][new_at + len(new_callback):]
    restored = restored.replace('let copyEnqueueResults: Signal<[[EngineMessage.Id?]], NoError> = combineLatest(copyEnqueueSignals)\n                                    let _ = (copyEnqueueResults\n', 'let _ = (combineLatest(copyEnqueueSignals)\n')
    assert restored == before[FORWARD], 'Unrelated forwarding code changed'
    assert after[FORWARD].index('batch.commit()') < after[FORWARD].index('let copyEnqueueResults:')
    assert 'accepted.indices.contains' not in after[FORWARD] + after[COPY]
    return method


def fixture(copy, forward):
    method = block(copy, '    func nagramiXHandleCopyEnqueued(')
    helper = block(copy, 'func nagramiXCopyEnqueueAcknowledgement(')
    at = forward.index('let copyEnqueueResults:')
    callback_start = forward.index('next: { [weak self] (accepted:', at)
    callback = braced(forward, callback_start)
    caller = forward[at:callback_start + len(callback) + 1]
    assert caller.endswith('})')
    return r'''
struct MessageId: Equatable { let value: Int }
enum EngineMessage { typealias Id = MessageId }
struct NoError: Error {}
struct EnginePeer { let id: Int; func displayTitle(strings: Strings, displayOrder: Int) -> String { "peer\(id)" } }
struct Strings { let nagramiXArchiveCopyUnavailable = "unavailable"; let Common_OK = "OK" }
struct PresentationData { let strings = Strings(); let nameDisplayOrder = 0 }
struct NagramiXCopyDeliveryRecipient { let peer: EnginePeer; let messageIds: [EngineMessage.Id]; let correlationIds: [Int64] }
struct TextAlertAction { enum Kind { case defaultAction }; let type: Kind; let title: String; let action: () -> Void }
struct Alert { let text: String }
enum Presentation { enum Root { case root }; case window(Root) }
func textAlertController(context: Int, title: String?, text: String, actions: [TextAlertAction]) -> Alert { Alert(text: text) }
var pendingWork: (() -> Void)?
var observationCount = 0
var alertCount = 0
struct Signal<T, E: Error> {
    let value: T
    func startStandalone(next: @escaping (T) -> Void) -> Int { pendingWork = { next(value) }; return 0 }
}
infix operator |> : AdditionPrecedence
func |> <A, B>(value: A, transform: (A) -> B) -> B { transform(value) }
func combineLatest(_ signals: [Signal<[EngineMessage.Id?], NoError>]) -> Signal<[[EngineMessage.Id?]], NoError> { .init(value: signals.map { $0.value }) }
func take<T, E: Error>(_ count: Int) -> (Signal<T, E>) -> Signal<T, E> { precondition(count == 1); return { $0 } }
func deliverOnMainQueue<T, E: Error>(_ signal: Signal<T, E>) -> Signal<T, E> { signal }
''' + helper + r'''
final class ChatControllerImpl {
    let context = 0
    let presentationData = PresentationData()
    var alerts: [String] = []
    var recipients: [NagramiXCopyDeliveryRecipient] = []
    var deliveryCompleted: (() -> Void)?
    var successCount = 0
    func present(_ alert: Alert, in whereTo: Presentation) { alerts.append(alert.text); alertCount += 1 }
    func nagramiXObserveCopyDelivery(_ recipients: [NagramiXCopyDeliveryRecipient], success: @escaping () -> Void) {
        self.recipients = recipients; self.deliveryCompleted = success; observationCount += 1
    }
''' + method + r'''
    func dispatch(peers: [EnginePeer], accepted: [[EngineMessage.Id?]], copyExpectedCounts: [Int], copyRecipientCorrelations: [[Int64]]) {
        let copyEnqueueSignals: [Signal<[EngineMessage.Id?], NoError>] = accepted.map { .init(value: $0) }
        let showForwardResult: () -> Void = { [weak self] in self?.successCount += 1 }
''' + caller + r'''
    }
    func finish() { let completion = deliveryCompleted; deliveryCompleted = nil; completion?() }
}
let a = MessageId(value: 1), b = MessageId(value: 2), c = MessageId(value: 3)
let peers = [EnginePeer(id: 1), EnginePeer(id: 2)]
func flush() { let work = pendingWork; pendingWork = nil; work?() }
func send(_ accepted: [[MessageId?]], counts: [Int] = [2, 1], correlations: [[Int64]] = [[11, 12], [13]]) -> ChatControllerImpl {
    let controller = ChatControllerImpl()
    controller.dispatch(peers: peers, accepted: accepted, copyExpectedCounts: counts, copyRecipientCorrelations: correlations)
    precondition(controller.recipients.isEmpty && controller.alerts.isEmpty && controller.successCount == 0)
    flush()
    return controller
}
let full = send([[a, b], [c]])
precondition(full.alerts.isEmpty && full.successCount == 0)
precondition(full.recipients.map { $0.peer.id } == [1, 2])
precondition(full.recipients[0].messageIds == [a, b] && full.recipients[1].messageIds == [c])
precondition(full.recipients[0].correlationIds == [11, 12] && full.recipients[1].correlationIds == [13])
full.finish(); precondition(full.successCount == 1); full.finish(); precondition(full.successCount == 1)
let partial = send([[a, nil], [c]])
precondition(partial.alerts == ["peer1\n\nunavailable"])
precondition(partial.recipients.count == 2 && partial.recipients[0].messageIds == [a] && partial.recipients[0].correlationIds == [11])
partial.finish(); precondition(partial.successCount == 0)
let missing = send([[a, b]])
precondition(missing.alerts == ["peer2\n\nunavailable"] && missing.recipients.count == 1)
missing.finish(); precondition(missing.successCount == 0)
let none = send([])
precondition(none.alerts == ["peer1, peer2\n\nunavailable"] && none.recipients.isEmpty && none.deliveryCompleted == nil && none.successCount == 0)
let shortCount = send([[a, b], [c]], counts: [3, 1])
precondition(shortCount.alerts == ["peer1\n\nunavailable"])
shortCount.finish(); precondition(shortCount.successCount == 0)
let excess = send([[a, b, c], [c]])
precondition(excess.alerts == ["peer1\n\nunavailable"])
precondition(excess.recipients[0].messageIds == [a, b] && excess.recipients[0].correlationIds == [11, 12])
excess.finish(); precondition(excess.successCount == 0)
let uncorrelated = send([[a, b], [c]], correlations: [[11], [13]])
precondition(uncorrelated.alerts == ["peer1\n\nunavailable"] && uncorrelated.recipients[0].messageIds == [a])
uncorrelated.finish(); precondition(uncorrelated.successCount == 0)
let extraRecipient = send([[a, b], [c], [b]])
precondition(extraRecipient.alerts.isEmpty && extraRecipient.recipients.count == 2)
extraRecipient.finish(); precondition(extraRecipient.successCount == 1)
var released: ChatControllerImpl? = ChatControllerImpl()
weak var reference = released
released?.dispatch(peers: peers, accepted: [[a, b], [c]], copyExpectedCounts: [2, 1], copyRecipientCorrelations: [[11, 12], [13]])
let priorObservations = observationCount, priorAlerts = alertCount
released = nil
precondition(reference == nil)
flush(); precondition(observationCount == priorObservations && alertCount == priorAlerts)
print("PASS: actual extracted handler/caller; deferred enqueue, ordered isolated recipients, partial/nil/missing/excess ACK, no false success, weak lifetime")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = {name: (OVERLAY / snap).read_text() for name, snap in plan['previous'].items()}
    after = {name: (args.source / name).read_text() for name in plan['outputs']}
    check_move(before, after)
    assert 'var multiplePeersSelected: (([EnginePeer], [EnginePeer.Id: EnginePeer]' in (args.source / PROTOCOL).read_text()
    assert 'public typealias Id = MessageId' in (args.source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Message.swift').read_text()
    assert 'public func enqueueMessages(account: Account, peerId: PeerId, messages: [EnqueueMessage]) -> Signal<[MessageId?], NoError>' in (args.source / 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift').read_text()
    assert 'public func startStandalone(next: ((T) -> Void)! = nil' in (args.source / 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift').read_text()
    current = fixture(after[COPY], after[FORWARD])
    mutations = [
        ('if allAccepted { showForwardResult() }', 'showForwardResult()'),
        ('if index < accepted.count {', 'if true {'),
        ('messageIds: pairs.map { $0.0 }', 'messageIds: pairs.reversed().map { $0.0 }'),
    ]
    with tempfile.TemporaryDirectory(prefix='nagramix-ack-sdk-132-') as temporary:
        folder = Path(temporary)
        guards = folder / 'guards'; guards.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guards)
        file = folder / 'Probe.swift'; binary = folder / 'probe'
        for flags in ([], ['-O']):
            common = [str(args.swiftc), '-module-cache-path', str(folder / 'cache'), *flags]
            file.write_text(current)
            subprocess.run([*common, '-warnings-as-errors', str(file), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
            for original, replacement in mutations:
                assert current.count(original) == 1, original
                file.write_text(current.replace(original, replacement, 1))
                subprocess.run([*common, str(file), '-o', str(binary)], check=True, capture_output=True, text=True)
                failed = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                assert failed.returncode != 0, 'Acknowledgement regression accepted: ' + original
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'replacements': 2, 'guards': len(plan['guards']), 'fail_closed': len(rejected), 'production_handler_and_caller_executions': 2,
              'semantic_regressions_rejected': 6, 'source_move_equivalence': 'passed;only split callback,typed signal,scalar bounds check',
              'old_timeout': 'SDK183;isolated Linux type checking cannot reproduce entire TelegramUI constraints', 'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()

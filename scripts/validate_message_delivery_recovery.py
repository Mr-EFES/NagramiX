#!/usr/bin/env python3
"""Run the four audit regressions against the Swift in the build projection."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_archive_history_restoration import fixture as archive_fixture
from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest

STAGE = 'message_delivery_recovery'
ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'scripts/tests'


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    sources = {}
    for name, expected in plan['outputs'].items():
        path = source / name
        assert digest(path) == expected, name
        subprocess.run([swiftc, '-frontend', '-parse', path], check=True)
        sources[path.name] = path.read_text()

    native = sources['Transcription.swift']
    handler = native.split('let description = error.errorDescription ?? ""', 1)[1].split('return .single(.error(mappedError))', 1)[0]
    rpc = '''import Foundation
struct RpcError { let errorDescription: String! }
enum AudioTranscriptionMessageAttribute { enum TranscriptionError: Equatable { case generic, tooLong } }
enum Outcome: Equatable { case limitExceeded(Int32), error(AudioTranscriptionMessageAttribute.TranscriptionError) }
struct Result { let value: Outcome; static func single(_ v: Outcome) -> Self { Self(value: v) } }
func classify(_ error: RpcError) -> Result {
''' + 'let description = error.errorDescription ?? ""' + handler + '''return .single(.error(mappedError))
}
@main enum Checks { static func main() {
    for (raw, expected): (String?, Outcome) in [(nil, .error(.generic)), ("", .error(.generic)), ("FLOOD_WAIT_19", .limitExceeded(19)), ("FLOOD_WAIT_x", .error(.generic)), ("MSG_VOICE_TOO_LONG", .error(.tooLong))] {
        precondition(classify(RpcError(errorDescription: raw)).value == expected)
    }
    print("PASS native transcription errors, nil and flood limits")
} }
'''
    archive = archive_fixture(source)
    anchor = '        print("PASS archive hide'
    assert archive.count(anchor) == 1
    archive = archive.replace(anchor, '''        archive.state.value.suspendHistory(peerId: other, topCloudId: 199, clearedAt: 1500)
        archive.receivedNewHistoryMessage(id: id(200, other), timestamp: 1490, media: [])
        precondition(record(id(4, other)).hiddenFromChat)
        archive.receivedNewHistoryMessage(id: id(199, other), timestamp: 1501, media: [])
        precondition(record(id(4, other)).hiddenFromChat)
        archive.receivedNewHistoryMessage(id: id(201, other), timestamp: 1500, media: [])
        precondition(record(id(4, other)).historyVisibility == .restored)
''' + anchor)
    assert 'remoteTimestamp: network.getApproximateRemoteTimestamp' in sources['Account.swift']
    assert 'let deletedAt = self.remoteTimestamp()' in block(sources['NagramiXMessageArchive.swift'], '    public func archiveHistoryBeforeDeletion(')

    store = sources['NagramiXDeferredReactionsStore.swift']
    chat = sources['ChatController.swift']
    native_queue = block(sources['MessageReactions.swift'], 'func nagramiXEnqueueReactions(')
    guard = next(line.strip() for line in native_queue.splitlines() if 'guard !messageIds.isEmpty' in line)
    assert native_queue.index(guard) < native_queue.index('transaction.setPendingMessageAction')
    assert 'messageIds.compactMap { transaction.getMessage($0) }' in native_queue
    assert 'return (true, nagramiXReadBoundaries)' in native_queue
    assert 'cachedData.sendAsPeerId' in native_queue
    assert 'expectedSender: nil' in block(sources['MessageReactions.swift'], 'public func updateMessageReactionsInteractively(')
    commands = [block(store, decl) for decl in ('    public struct Intent:', '    public func pending(', '    public func resolveSender(', '    public func enqueue(')]
    ui = chat[chat.index('    private let nagramiXReactionView ='):chat.index('\n', chat.index('alert: AlertController)?'))]
    ui += '\n' + block(chat, '    private var nagramiXDeferredReactionChatActive:') + '\n' + block(chat, '    func nagramiXFlushDeferredReactionsIfActive()')
    reactions = (TESTS / 'NagramiXDeferredReactionRecovery.swift').read_text().replace('// STORE', '\n'.join(commands).replace('public ', '')).replace('// CHAT', ui)
    reactions = reactions.replace('// NATIVE GUARD', guard.replace('return (false, [])', 'receive(false); return'))

    old_metrics = (ROOT / 'ios/Tests/NagramiXInstallationMetricsTests.swift').read_text()
    stub = old_metrics.split('@main struct InstallationMetricsTests', 1)[0]
    metrics = sources['NagramiXInstallationMetrics.swift']
    cases = [('Transcription', rpc), ('Archive', archive), ('Reactions', reactions),
             ('Installation', metrics + '\n' + stub + '\n' + (TESTS / 'NagramiXInstallationRecovery.swift').read_text()),
             ('InstallationLifecycle', metrics + '\n' + old_metrics)]
    for name, code in cases:
        for result in execute(swiftc, folder, name, code):
            print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source', type=Path)
    group.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-delivery-recovery-') as tmp:
        folder = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = folder / 'source'
            canonical_projection(source, STAGE)
        validate(source, args.swiftc, folder)

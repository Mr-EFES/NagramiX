#!/usr/bin/env python3
"""Separate media consumption/expiry from genuine deletion without faking read receipts."""
import argparse
import json
import re
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import temporary_expiration_semantics_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'temporary_expiration_semantics'


def source_contract(source, plan):
    assert plan['required_previous_stage'] == 'web_video_picture_in_picture'
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    assert set(plan['outputs']) == {runtime.ARCHIVE, runtime.CONSUME, runtime.TIMER, runtime.HISTORY}
    assert not plan['copies'] and not plan['deletions']
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == value, name
    before = {n: (ROOT / 'ios' / plan['previous'][n]).read_text() for n in plan['outputs']}
    after = {n: (source / n).read_text() for n in plan['outputs']}
    a, old = after[runtime.ARCHIVE], before[runtime.ARCHIVE]
    assert 'var mediaExpiredAt: Int32? = nil' in block(a, 'private struct NagramiXArchivedRecord:')
    for header in [
        'public final class NagramiXArchivedMessageAttribute:', 'public extension Message {',
        '    public func archiveServerDeletion(messageIds:', '    public func archiveServerDeletion(globalIds:',
        '    public func archiveServerDeletion(upToMessageId', '    private func archiveHistoryDeletion(',
        '    public func shouldSuppressTemporaryContentReceipt(id:',
        '    public func shouldSuppressTemporaryContentReceipt(peerId:',
        '    private func renderDeletedRecord(', '    public func updateTranscriptionAttributes(',
    ]:
        current = block(a, header).replace('''                    // Delete updates change deletion state. Media consumption is
                    // tracked separately without discarding the retained bytes.
''','''                    // Consumption in another client changes deletion state, not
                    // the retained media's type, bytes or transcription ownership.
''')
        assert current == block(old, header), header
    for header in ['    public func postDeletionPlan(', '    public func deleteArchivedPosts(', '    public func localPostDeletionCandidates(']:
        current = block(a, header)
        current = current.replace('self.state.with({ $0.records[Self.key(message.id)]?.hasLocalRemovalOwnership == true })', 'self.isLocallyDeletedMessage(id: message.id)')
        current = current.replace('records[Self.key(id)]?.hasLocalRemovalOwnership == true', 'records[Self.key(id)]?.deletedAt != nil')
        current = current.replace('records[Self.key($0)]?.hasLocalRemovalOwnership == true', 'records[Self.key($0)]?.deletedAt != nil')
        current = current.replace('record.hasLocalRemovalOwnership ||', 'record.deletedAt != nil ||')
        assert current == block(old, header), header
    expiry = block(a, '    public func markTemporaryExpired(')
    assert 'record.mediaExpiredAt = expiredAt' in expiry and 'record.mediaExpiredAt == nil' in expiry
    assert not re.search(r'record\.deletedAt\s*=(?!=)', expiry)
    snapshot = block(a, '    public func snapshotForExpiredMessage(')
    assert 'record.mediaExpiredAt = expiredAt' in snapshot and not re.search(r'record\.deletedAt\s*=(?!=)', snapshot)
    interaction = block(a, '    public func temporaryInteractionMessage(')
    assert interaction.replace('record.mediaExpiredAt = record.mediaExpiredAt ??', 'record.deletedAt = record.deletedAt ??') == block(old, '    public func temporaryInteractionMessage(')
    assert 'record.mediaExpiredAt == nil' in block(a, '    public func canExplicitlyOpenTemporaryMedia(')
    assert 'record.mediaExpiredAt == nil' in block(a, '    public func authorizeTemporaryMediaOpen(')
    for header in ['    public func captureIncoming(', '    public func archiveMessagesBeforeDeletion(']:
        current = block(a, header)
        addition = next(line for line in current.splitlines(keepends=True) if 'record.mediaExpiredAt = current.mediaExpiredAt' in line)
        assert current.replace(addition, '', 1) == block(old, header), header

    c, previous = after[runtime.CONSUME], before[runtime.CONSUME]
    remote = block(c, 'func markMessageContentAsConsumedRemotely(')
    original = block(previous, 'func markMessageContentAsConsumedRemotely(')
    extra = '''        let nagramiXPreserveTemporaryMedia = nagramiXCanRetainTemporaryMessage(message)
        if nagramiXPreserveTemporaryMedia {
            messageArchive?.captureTemporaryBeforeViewing(message: message)
            let retainedAttributes = nagramiXTemporaryAttributesWithoutCountdown(updatedAttributes)
            updatedAttributes = retainedAttributes.attributes
            updateMessage = updateMessage || retainedAttributes.changed
        }
'''
    assert remote.replace(extra, '', 1).replace('            if nagramiXPreserveTemporaryMedia { continue }\n', '', 1) == original
    helpers = '\n\n'.join(block(c, header) for header in [
        'func nagramiXTemporaryAttributesWithoutCountdown(',
        'func nagramiXPreserveTemporaryMediaBeforeExpiration(',
    ])
    assert 'setPendingMessageAction' not in helpers and 'ConsumableContentMessageAttribute(' not in helpers
    for header in ['func _internal_markMessageContentAsConsumedInteractively(', 'func _internal_markTemporaryMediaOpened(']:
        assert block(c, header) == block(previous, header), header
    guard = '''                        if nagramiXPreserveTemporaryMediaBeforeExpiration(transaction: transaction, postbox: postbox, message: message) {
                            return
                        }
'''
    assert after[runtime.TIMER].replace(guard, '', 1) == before[runtime.TIMER]
    history = after[runtime.HISTORY]
    assert 'message: snapshot, isRead: entry.isRead' in history
    helper = block(history, 'private func nagramiXRetainedTemporaryMessageIsRead(')
    assert 'state.isOutgoingMessageIndexRead(message.index)' in helper
    assert 'view.transientReadStates ?? view.fixedReadStates' in history
    current = history.replace('''// Missing native rows have no default read confirmation. Use the same
// per-peer/namespace read state as Postbox's ordinary outgoing history entries.
''' + helper + '\n\n', '', 1)
    current = current.replace('''                let retainedIsRead = context.account.nagramiXMessageArchive.isLocallyDeletedMessage(id: message.id)
                    || nagramiXRetainedTemporaryMessageIsRead(message, readStates: view.transientReadStates ?? view.fixedReadStates)
''', '', 1).replace('isRead: retainedIsRead,', 'isRead: true,', 1)
    assert current == before[runtime.HISTORY]
    view = (source / 'submodules/Postbox/Sources/MessageHistoryView.swift').read_text()
    assert 'public let transientReadStates: MessageHistoryViewReadState?' in view
    assert 'public let fixedReadStates: MessageHistoryViewReadState?' in view
    assert 'public func isOutgoingMessageIndexRead(_ index: MessageIndex) -> Bool' in (source / 'submodules/Postbox/Sources/PeerReadState.swift').read_text()
    # The same native presentation predicate still owns both marker and 50%.
    bubble = (source / 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift').read_text()
    assert 'let nagramiXIsArchived = item.content.firstMessage.nagramiXShowsArchiveNotice' in bubble
    assert 'let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0' in bubble
    timeout = (source / (runtime.CORE + 'SyncCore/SyncCore_AutoremoveTimeoutMessageAttribute.swift')).read_text()
    assert 'self.automaticTimestampBasedAttribute = nil' in timeout
    replay = (source / (runtime.CORE + 'State/Sync/StateReplay+ReadStates.swift')).read_text()
    assert 'messageArchive: NagramiXMessageArchive.forPostbox(postbox)' in replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    source_contract(args.source, plan)
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='temporary-expiry-') as temporary:
        folder = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, folder / 'guards')
        archive = runtime.archive(args.source)
        receipts = runtime.consumption(args.source)
        history = runtime.history(args.source)
        runs = execute(args.swiftc, folder, 'expiry-archive', archive)
        runs += execute(args.swiftc, folder, 'expiry-consumption', receipts)
        runs += execute(args.swiftc, folder, 'expiry-read-status', history)
        for name, text, diagnostic in runtime.negatives(archive, receipts, history):
            runs += execute(args.swiftc, folder, name, text, diagnostic)
        for name in plan['outputs']:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert manifest(args.source) == initial
    report = {
        'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
        'loader_refusals': len(refusals), 'executions': runs, 'swift_parse': len(plan['outputs']),
        'source_files': len(initial), 'source_unchanged_by_checks': True,
        'boundary': 'Actual remote consumption and complete TTL-reset helpers execute with Postbox/media IO adapters. Actual archive models, JSON persistence and expiry/deletion/render/interaction/consent/clear methods execute in debug and optimized modes. Native read state and genuine deletion bodies, playback, ASR, layout and 50% predicate are unchanged. UIKit, server-delivery causality and physical iPhone playback require Apple SDK/device validation.',
        'legacy': 'Records without expiry provenance retain their existing deletion state; genuine old deletions are not guessed away.',
        'server_delete_without_reason': 'Still handled as deletion; Telegram delete updates do not identify sender intent or automatic expiry.',
        'apple_sdk': 'not_run', 'device': 'pending',
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

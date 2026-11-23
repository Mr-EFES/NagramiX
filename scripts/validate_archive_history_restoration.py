#!/usr/bin/env python3
"""Exercise local visibility, restored-only confirmation, native deletion and Undo without an iOS build."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest
from validate_private_temporary_transcription import execute

STAGE = 'archive_history_restoration'
TESTS = Path(__file__).with_name('tests')
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
CHAT = 'submodules/TelegramUI/Sources/ChatControllerAdminBanUsers.swift'


def fixture(source):
    archive = (source / ARCHIVE).read_text()
    chat = (source / CHAT).read_text()
    code = (TESTS / 'NagramiXArchiveLocalDeleteTransition.swift').read_text().split('@main enum LocalDeleteChecks')[0]
    code = code.replace('public struct PeerId: Hashable', 'public struct PeerId: Hashable, Codable').replace('public struct MessageId: Hashable', 'public struct MessageId: Hashable, Codable').replace('let id: Int\n', 'let id: Int32\n')
    code = code.replace('struct NagramiXArchivedRecord {', '''struct NagramiXArchivedRecord: Codable, Equatable {
    var historyVisibility: NagramiXArchiveVisibility?
    var deletedAt: Int32?
    var id: Int32 { messageId.id }
    var timestamp: Int32 = 400
''' + block(archive, '    var hiddenFromChat: Bool'))
    declarations = ('private enum NagramiXArchiveVisibility:', 'private struct NagramiXArchiveHistoryBoundary:', 'private struct NagramiXMessageArchiveState:', 'private struct NagramiXArchivePostKey:', 'public struct NagramiXArchivePostDeletionPlan')
    code = code.replace('// ACTUAL_ARCHIVE_PLAN', '\n'.join(block(archive, decl).removeprefix('private ') for decl in declarations))
    code = code.replace('struct ArchiveState { var records: [String: NagramiXArchivedRecord] }', 'extension PeerId { func toInt64() -> Int64 { Int64(value) } }\ntypealias NagramiXMessageArchive = Archive')
    code = code.replace('ArchiveState(records: [:])', 'NagramiXMessageArchiveState()').replace('private static func key(_ id:', 'fileprivate static func key(_ id:')
    prior_purge = block(code, '    func deleteArchivedPosts(')
    code = code.replace(prior_purge, block(archive, '    public func deleteArchivedPosts('))
    methods = ('    private static func isRegularArchiveIdentifier(', '    public func postMessageIds(', '    public func postDeletionPlan(', '    public func removeLocal(', '    public func usesLocalHistoryVisibility(', '    func receivedNewHistoryMessage(')
    code = code.replace('// ACTUAL_ARCHIVE_METHODS', '''
    struct TestQueue { func async(_ work: @escaping () -> Void) { work() } }
    let queue = TestQueue()
    var mutationState: NagramiXMessageArchiveState { state.value }
    struct MediaStore { func barrier() -> Int64 { 1 } }
    let mediaStore = MediaStore()
    var removalTickets: [String: Int64] = [:]
    func persist(_ updated: NagramiXMessageArchiveState, retryNow: Bool = false) {
        let removed = state.value.records.compactMap { updated.records[$0.key] == nil ? $0.value.messageId : nil }
        if !removed.isEmpty { purges.append(Set(removed)) }
        state.value = updated
    }
    func publishUpdate() {}
    func finishLocalDeletion() -> Signal<Void, NoError> { .complete() }
''' + '\n'.join(block(archive, m) for m in methods))
    code = code.replace('// ACTUAL_HISTORY_STATE', ' var nagramiXPendingRetainedDeletionIds: Set<MessageId> = []')
    code = code.replace('struct Strings {', '''struct Strings {
    let Common_Delete = "Delete", Common_Cancel = "Cancel", ConvertToSupergroup_Note = "Cannot undo"
    func nagramiXLocalCopiesDeletionWarning(_ count: Int) -> String { "Copies: " + String(count) }''')
    code = code.replace('enum Destination { case current }', '''enum Window { case root }
    enum Destination { case current, window(Window) }
    var alerts: [TestAlert] = []
    func present(_ controller: TestAlert, in destination: Destination) { alerts.append(controller) }''')
    methods = ('    private func nagramiXDeleteArchivedPostsWithUndo(', '    private func nagramiXCommitDeletionWithUndo(')
    code = code.replace('// ACTUAL_CONTROLLER_METHOD', '\n'.join(block(chat, m) for m in methods).replace('private func nagramiXDeleteArchivedPostsWithUndo(', 'func confirm('))
    return code + (TESTS / 'NagramiXArchiveHistoryRestoration.swift').read_text()


def check(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for path, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / path) == expected, path
    for path in plan['outputs']:
        subprocess.run([swiftc, '-frontend', '-parse', source / path], check=True)
    archive = (source / ARCHIVE).read_text()
    assert archive.count('record.historyVisibility = current.historyVisibility') == 2
    assert 'if requestedByUser && settings.showDeletedMessages' in block(archive, '    public func archiveMessagesBeforeDeletion(')
    assert 'if !forTranscription && (record.hiddenFromChat' in block(archive, '    private func renderDeletedRecord(')
    assert 'forTranscription: record.hiddenFromChat' in block(archive, '    public func transcriptionMessage(')
    assert '.resumeHistory(' in block(archive, '    func receivedNewHistoryMessage(')
    def content(suffix):
        return (source / next(p for p in plan['outputs'] if p.endswith('/' + suffix))).read_text()
    replay = content('StateReplay+Messages.swift')
    arrival = replay.index('archive.receivedNewHistoryMessage')
    assert replay.rindex('if case .UpperHistoryBlock = location', 0, arrival) < replay.rindex('!transaction.messageExists(id: id)', 0, arrival) < arrival < replay.index('transaction.addMessages(messages, location: location)')
    assert 'receivedNewHistoryMessage(' in block(archive, '    public func captureSent(')
    remove = content('RemovePeerChat.swift')
    assert remove.count('requestedByUser: true)') == 3
    interactive = content('DeleteMessagesInteractively.swift')
    assert 'requestedByUser: true)' in interactive
    assert 'requestedByUser: true' in block(interactive, 'func _internal_clearHistoryInRangeInteractively(')
    assert 'threadId == nil && minTimestamp == nil && maxTimestamp == nil' in block(archive, '    public func archiveHistoryBeforeDeletion(')
    assert 'usesLocalHistoryVisibility' in content('ChatHistoryEntriesForView.swift')
    for result in execute(swiftc, folder, 'ArchiveHistoryRestoration', fixture(source)):
        print(result['mode'], result['output'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--canonical', action='store_true')
    mode.add_argument('--source', type=Path)
    parser.add_argument('--swiftc', default='swiftc')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = folder / 'source'
            canonical_projection(source, STAGE)
        check(source, args.swiftc, folder)


if __name__ == '__main__':
    main()

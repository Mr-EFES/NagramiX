#!/usr/bin/env python3
"""Проверить область показа архива и сохранение до явной полной очистки."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

from validate_archive_persistence import models, method
from validate_quick_format import block, manifest
from validate_scheduled_archive_isolation import source_entries

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'archive_chat_scope_patches.json').read_text())
A = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
H = 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift'
D = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/DeleteMessages.swift'
R = 'submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift'
WRITER = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivePersistence.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'Archive scope outputs differ'
    for name, digest in PLAN['guards'].items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name


def reverse(source, prior):
    names = set(PLAN['inputs'])
    for path in OVERLAY.glob('*_patches.json'):
        item = json.loads(path.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings',
                  'submodules/TelegramPresentationData/Sources/PresentationData.swift',
                  'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift'])
    for name in names:
        path = OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name
        if path.is_file():
            target = prior / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_free_content import delegate_if_applied as delegate_next
    if delegate_next(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='archive-scope-prior-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('archive_chat_scope', OVERLAY / 'archive_chat_scope.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def seed(label):
        target = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            data = (OVERLAY / PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source / name).read_bytes()
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return target
    rejected = []
    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_archive_chat_scope(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_archive_chat_scope(valid, OVERLAY)
    assert all((valid / name).read_bytes() == (source / name).read_bytes() for name in PLAN['outputs'])
    reject(valid, 'повторное применение')
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ('missing', 'drift'):
            target = seed(str(len(rejected)))
            path = target / name
            if kind == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, kind + ' ' + name)
    mutations = []
    for field in ('inputs', 'outputs', 'guards', 'templates'):
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field + '-SHA', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations'][A][0][0] += ' broken'
    mutations.append(('anchor', bad))
    bad = copy.deepcopy(PLAN)
    bad['previous'][A] = '../outside.swift'
    mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ('inputs', 'outputs', 'previous', 'operations'):
        bad[field]['../outside.swift'] = bad[field].pop(A)
    mutations.append(('source-traversal', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations']['/outside.swift'] = bad['operations'].pop(A)
    mutations.append(('operation-path', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for path in PLAN['templates']:
            destination = overlay / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OVERLAY / path).read_bytes())
        (overlay / 'archive_chat_scope_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    for label, name in [('input-symlink', A), ('guard-symlink', next(iter(PLAN['guards'])))]:
        target = seed(label)
        path = target / name
        external = temp / (label + '.swift')
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(target, label)
    return rejected


def swift_harness(source, previous_archive=False, previous_history=False):
    archive = (source / A).read_text()
    before = (OVERLAY / PLAN['previous'][A]).read_text()
    boundary = (ROOT / 'scripts/tests/NagramiXArchiveChatScopeBoundary.swift').read_text()
    namespace = block((source / 'submodules/Postbox/Sources/Message.swift').read_text(), 'public enum MessageIdNamespaces:')
    settings = block(archive, 'private struct NagramiXMessageArchiveSettings ')
    properties = archive[archive.index('    private let storageStatusValue ='):archive.index('    private lazy var mediaStore =')]
    result = boundary + '\n' + namespace + '\n' + settings + '\n' + models(archive) + '''
private typealias NagramiXMessageArchive = ArchiveHarness
private final class ArchiveHarness {
    private static let registry = Atomic<[ObjectIdentifier: NagramiXWeakMessageArchive]>(value: [:])
    let postbox: Postbox
    let accountPeerId = PeerId(1)
    let path: String
    private let queue = Queue()
    let mediaStore = MediaStoreSpy()
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    var listCalls = 0
    init(path: String, postbox: Postbox) {
        self.path = path; self.postbox = postbox
        Self.registry.modify { $0[ObjectIdentifier(postbox)] = NagramiXWeakMessageArchive(self) }
    }
    var records: [String: NagramiXArchivedRecord] { state.with { $0.records } }
    func record(_ id: MessageId) -> NagramiXArchivedRecord? { records[Self.key(id)] }
    func load() { _ = loadPersistedState() }
    private func publishUpdate() {}
    private func mediaRequests(_ record: NagramiXArchivedRecord) -> [NagramiXArchiveMediaRequest] {
        record.content.media.map { NagramiXArchiveMediaRequest(data: $0) }
    }
    private static func makeRecord(message: Message, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {
        guard message.eligible, message.id.namespace == Namespaces.Message.Cloud,
              message.id.peerId.namespace != Namespaces.Peer.SecretChat else { return nil }
        return NagramiXArchivedRecord(peerId: message.id.peerId.toInt64(), namespace: message.id.namespace,
            id: message.id.id, authorId: nil, timestamp: message.timestamp, threadId: message.threadId,
            groupingKey: message.groupingKey, incoming: message.incoming, temporary: message.temporary,
            viewOnceReplay: message.replay, peerData: [:],
            content: NagramiXArchivedContent(text: message.text, entities: [], media: message.bytes),
            contentTimestamp: message.timestamp, revisions: [], deletedAt: nil)
    }
    private func renderDeletedRecord(_ record: NagramiXArchivedRecord) -> Message? {
        Message(record.messageId, timestamp: record.timestamp, thread: record.threadId, grouping: record.groupingKey,
                text: record.content.text, incoming: record.incoming, bytes: record.content.media,
                temporary: record.temporary == true, replay: record.viewOnceReplay == true, deleted: true)
    }
    func captureTemporaryBeforeViewing(message: Message) {}
''' + properties
    names = ['public static func forMediaBox(', 'public static func forPostbox(',
             'private func loadPersistedState()', 'public func retryPersistence()', 'private func retryStorage()',
             'private func persist(', 'private func didPersist(', 'private static func key(',
             'public func archiveMessagesBeforeDeletion(', 'public func archiveHistoryBeforeDeletion(',
             'public func archiveMessageRangeBeforeDeletion(', 'private func archiveHistoryDeletion(',
             'public func archiveServerDeletion(messageIds:', 'public func archiveServerDeletion(globalIds:',
             'public func archiveServerDeletion(upToMessageId', 'public func removeLocal(', 'public func clear(peerId:',
             'public func clearAll()', 'public func recordIncomingEdit(', 'public func markTemporaryExpired(',
             'public func deletedMessage(', 'public func snapshotForExpiredMessage(']
    for name in names:
        origin = before if previous_archive and name in ('public func removeLocal(', 'public func clear(peerId:') else archive
        result += method(origin, name)
    result += method(archive, 'public func deletedMessages(').replace('public func deletedMessages(', 'private func actualDeletedMessages(', 1)
    result += '''
    func deletedMessages(peerId: PeerId, threadId: Int64?, minIndex: MessageIndex?, maxIndex: MessageIndex?, limit: Int = 200) -> [Message] {
        listCalls += 1
        return actualDeletedMessages(peerId: peerId, threadId: threadId, minIndex: minIndex, maxIndex: maxIndex, limit: limit)
    }
}
'''
    core = (source / D).read_text()
    hooks = []
    for marker in ('public func _internal_deleteMessages(', 'func _internal_clearHistory(', 'func _internal_clearHistoryInRange('):
        hooks.append(block(core, marker).splitlines()[1])
    result += '''
private func performDelete(transaction: Transaction, mediaBox: MediaBox, ids: [MessageId]) {
''' + hooks[0] + '''
    transaction.remove(ids)
}
private func performClear(transaction: Transaction, mediaBox: MediaBox, peerId: PeerId, threadId: Int64?, minTimestamp: Int32?, maxTimestamp: Int32?, namespaces: MessageIdNamespaces) {
    if let minTimestamp, let maxTimestamp {
''' + hooks[2] + '''
    } else {
''' + hooks[1] + '''
    }
    transaction.clear(peerId: peerId, threadId: threadId, minTimestamp: minTimestamp, maxTimestamp: maxTimestamp, namespaces: namespaces)
}
'''
    state = (source / R).read_text()
    start = state.index('            case let .DeleteMessagesWithGlobalIds(ids):')
    global_hooks = state[start:].splitlines()[1:3]
    start = state.index('                NagramiXMessageArchive.forPostbox(postbox)?.archiveMessageRangeBeforeDeletion(')
    range_hooks = state[start:].splitlines()[:2]
    result += '''
private func performGlobalDelete(transaction: Transaction, postbox: Postbox, ids: [Int32]) {
''' + '\n'.join(global_hooks) + '''
    transaction.remove(transaction.messageIdsForGlobalIds(ids))
}
private func performRangeDelete(transaction: Transaction, postbox: Postbox, id: MessageId) {
''' + '\n'.join(range_hooks) + '''
    transaction.remove(transaction.messages.filter { $0.id.peerId == id.peerId && $0.id.namespace == id.namespace && $0.id.id <= id.id }.map { $0.id })
}
private func renderHistory(context: TestContext, subject: ChatControllerSubject?, view: MessageHistoryView, location: ChatLocation, isMusicPlaylist: Bool, associatedData: AssociatedData) -> [MessageHistoryEntry] {
'''
    history = (OVERLAY / PLAN['previous'][H]).read_text() if previous_history else (source / H).read_text()
    result += source_entries(history) + '\n    return sourceEntries\n}\n'
    result += (ROOT / 'scripts/tests/NagramiXArchiveChatScopeTests.swift').read_text()
    signature = 'private static func makeRecord(message: Message, peers: [PeerId: Peer]) -> NagramiXArchivedRecord? {'
    assert signature in archive and signature in result, 'Codec boundary signature differs from production'
    return result


def run_swift(source, swiftc, temp):
    runs = []
    for label, old_archive, old_history in [('current', False, False), ('old-delete', True, False), ('old-pinned', False, True)]:
        source_path = temp / (label + '.swift')
        source_path.write_text(swift_harness(source, old_archive, old_history))
        for optimized in (False, True):
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command += ['-O']
            subprocess.run([*command, str(source / WRITER), str(source / 'submodules/Postbox/Sources/SimpleDictionary.swift'), str(source_path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                env=dict(os.environ, XDG_CONFIG_HOME=str(temp / (binary.name + '-prefs'))),
                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(binary.name + ': ' + result.stdout.strip())
            else:
                expected = 'individual delete must retain archived message' if old_archive else 'pinned/scheduled/custom view must contain only native messages'
                assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr
                runs.append(binary.name + ': прежний дефект воспроизведён и отвергнут')
            print(runs[-1], flush=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_author_check_badge_icon import delegate_variant_five_if_applied
    if delegate_variant_five_if_applied(args, Path(__file__)):
        return
    verify(args.source)
    archive = (args.source / A).read_text()
    previous = (OVERLAY / PLAN['previous'][A]).read_text()
    for marker in ('public func clearAll()', 'private func renderDeletedRecord('):
        assert block(archive, marker) == block(previous, marker), marker
    assert 'current.deletedAt = nil' not in block(archive, 'public func recordIncomingEdit(')
    assert models(archive) == models(previous), 'Схема JSON изменилась'
    calls = (OVERLAY / 'apply_overlay.py').read_text()
    assert calls.index('    apply_ghostgram_pip_compile_fix(') < calls.index('    apply_archive_chat_scope(')
    with tempfile.TemporaryDirectory(prefix='nagramix-archive-scope-check-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'changed_files': len(PLAN['outputs']), 'guards': len(PLAN['guards']),
              'fail_closed': rejected, 'executions': runs, 'sdk': 'не запускалась',
              'device': 'ожидает проверки на iPhone',
              'runtime': 'production archive mutations/history block/deletion hooks and persistence; Postbox/UI/MediaBox/codec boundaries; real Foundation JSON IO'}
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Validate real archive persistence, failure recovery and final native overlay."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
WRITER = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivePersistence.swift'
CONTEXT = 'submodules/TelegramUI/Sources/AccountContext.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def method(source, name):
    start = source.index('    ' + name)
    annotation = '    @discardableResult\n'
    if source[:start].endswith(annotation): start -= len(annotation)
    return source[start:source.index('\n    }', start) + len('\n    }')] + '\n'


def models(source):
    return source[source.index('public struct NagramiXMessageRevision:'):source.index('/// Marks a synthetic')] + source[source.index('private struct NagramiXArchivedContent:'):source.index('private final class NagramiXWeakMessageArchive')]


def harness(source):
    properties = source[source.index('    private let storageStatusValue ='):source.index('    private lazy var mediaStore =')]
    result = 'import Foundation\n' + models(source) + '''private final class ArchiveHarness {
    let path: String
    private let queue = Queue()
    let mediaStore = MediaStoreSpy()
    private let state = Atomic<NagramiXMessageArchiveState>(value: NagramiXMessageArchiveState())
    var revisionsPublished = 0
    init(path: String) { self.path = path }
    var records: [String: NagramiXArchivedRecord] { self.state.with { $0.records } }
    var dirtyCount: Int { self.persistence.pending?.records.count ?? 0 }
    var status: NagramiXArchiveStorageStatus { self.storageStatusValue.value }
    func record(_ id: MessageId) -> NagramiXArchivedRecord? { self.records[Self.key(id)] }
    func dirtyRecord(_ id: MessageId) -> NagramiXArchivedRecord? { self.persistence.pending?.records[Self.key(id)] }
    private func publishUpdate() { self.revisionsPublished += 1 }
    func load() { _ = self.loadPersistedState() }
''' + properties
    for name in ['private func loadPersistedState()', 'public func retryPersistence()', 'private func retryStorage()', 'private func persist(', 'private func didPersist(', 'private static func key(', 'public func removeLocal(', 'public func clear(peerId:', 'public func clearAll()', 'public func markTemporaryExpired(', 'public func archiveServerDeletion(messageIds:', 'public func updateDeletedMessageText(']:
        result += method(source, name)
    start = source.index('            var updated = self.mutationState', source.index('    public func captureIncoming('))
    capture = source[start:source.index('\n        }\n    }', start)]
    return result + '''    func capture(_ id: MessageId, text: String, temporary: Bool = false) {
        let record = NagramiXArchivedRecord(peerId: id.peerId.toInt64(), namespace: id.namespace, id: id.id, authorId: nil, timestamp: 1, threadId: nil, groupingKey: nil, incoming: true, temporary: temporary, peerData: [:], content: NagramiXArchivedContent(text: text, entities: [], media: []), contentTimestamp: 1, revisions: [], deletedAt: nil)
        let requests: [Int] = []
        let ticket = self.mediaStore.barrier()
        let settings = NagramiXMessageArchiveSettings()
        self.queue.async {
''' + capture + '\n        }\n    }\n}\n' + (ROOT / 'scripts/tests/NagramiXArchiveStorageTests.swift').read_text()


def validate(before, after, swiftc):
    a, b = manifest(before), manifest(after)
    plan = json.loads((ROOT / 'ios/archive_persistence_patches.json').read_text())
    changed = {ARCHIVE, CONTEXT, *[n for n in plan['provided'].values() if n != ARCHIVE]}
    assert set(b) - set(a) == {WRITER} and not set(a) - set(b)
    assert {n for n in a if a[n] != b[n]} == changed
    for n, sha in plan['hashes'].items(): assert a[n] == sha
    restored = (after / CONTEXT).read_text()
    for n, old, new, count in reversed(plan['patches']):
        assert n == CONTEXT and restored.count(new) == count
        restored = restored.replace(new, old, count)
    assert restored == (before / CONTEXT).read_text()
    for template, name in {**plan['provided'], **plan['copies']}.items():
        assert (after / name).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    previous, current = (before / ARCHIVE).read_text(), (after / ARCHIVE).read_text()
    assert models(previous) == models(current), 'Archive schema or revision rules changed'
    for first, last in [('    private static func key(', '    public func captureIncoming('), ('    public func revisions(', '    public func updateDeletedMessageText(')]:
        assert previous[previous.index(first):previous.index(last)] == current[current.index(first):current.index(last)], first
    assert previous[previous.index('    public func deletedMessages('):] == current[current.index('    public func deletedMessages('):], 'Rendering/export paths changed'
    assert current.count('_ = self.state.swap(updated)') == 1
    assert 'try? JSONEncoder' not in current and 'try? data.write' not in current
    assert 'try? FileManager.default.removeItem(atPath: self.path)' not in current
    assert 'self.inForeground = foreground\n                    self.refreshMediaDownloads()\n                    if foreground { self.retryStorage() }' in current
    assert 'Sources/**/*.swift' in (after / 'submodules/TelegramCore/BUILD').read_text()
    ui = (after / CONTEXT).read_text()
    assert 'guard foreground, presentedFailure != failure' in ui and 'self.nagramiXArchiveStorageDisposable.dispose()' in ui
    executions = []
    spec = importlib.util.spec_from_file_location('archive_storage', ROOT / 'ios/archive_persistence.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    negatives = 0
    with tempfile.TemporaryDirectory(prefix='nagramix-archive-storage-') as folder:
        folder = Path(folder)
        archive_test = folder / 'Archive.swift'; archive_test.write_text(harness(current))
        old_test = folder / 'Original.swift'
        old_test.write_text('import Foundation\n' + models(previous) + '''private final class OriginalArchive {
    let path: String
    init(path: String) { self.path = path }
''' + method(previous, 'private func persist(') + '''    func save() { self.persist(NagramiXMessageArchiveState()) }
}
@main struct OriginalFailure {
    static func main() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        let blocker = folder.appendingPathComponent("file")
        try Data([0]).write(to: blocker)
        let path = blocker.appendingPathComponent("archive.json").path
        OriginalArchive(path: path).save()
        precondition(!FileManager.default.fileExists(atPath: path))
        print("Original regression reproduced: persist returns normally without a saved file or failure result")
    }
}
''')
        boundary = ROOT / 'scripts/tests/NagramiXArchiveStorageBoundary.swift'
        for mode in ['debug', 'optimized']:
            suites = {'original': [boundary, old_test], 'coordinator': [after / WRITER, ROOT / 'scripts/tests/NagramiXArchivePersistenceTests.swift'], 'archive': [after / WRITER, boundary, archive_test]}
            for label, sources in suites.items():
                binary = folder / (label + mode)
                command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, sources), '-o', str(binary)]
                if mode == 'optimized': command.insert(1, '-O')
                subprocess.run(command, check=True)
                result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(folder / 'preferences')), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
                assert result.returncode == 0, result.stdout
                executions.append(mode + ': ' + result.stdout.strip())

        def seed(case_plan):
            source, overlay = folder / 'source', folder / 'overlay'
            for n in set(plan['hashes']) | set(plan['provided'].values()):
                p = source / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((before / n).read_bytes())
            for template, n in plan['provided'].items(): (source / n).write_bytes((ROOT / 'ios' / template).read_bytes())
            for template in set(plan['provided']) | set(plan['copies']):
                p = overlay / template; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT / 'ios' / template).read_bytes())
            for n in plan['copies'].values():
                (source / n).parent.mkdir(parents=True, exist_ok=True); (source / n).unlink(missing_ok=True)
            (overlay / 'archive_persistence_patches.json').write_text(json.dumps(case_plan))
            return source, overlay

        def reject(source, overlay):
            nonlocal negatives
            snapshot = manifest(source)
            try: module.apply_archive_persistence(source, overlay)
            except (SystemExit, FileNotFoundError):
                assert snapshot == manifest(source), 'Partial write on failure'
                negatives += 1
            else: raise AssertionError('Drift accepted')

        source, overlay = seed(plan); module.apply_archive_persistence(source, overlay)
        for n in set(plan['hashes']) | set(plan['provided'].values()) | {WRITER}:
            assert (source / n).read_bytes() == (after / n).read_bytes()
        reject(source, overlay)
        for n in plan['hashes']:
            source, overlay = seed(plan); p = source / n; p.write_bytes(p.read_bytes() + b'\n// drift'); reject(source, overlay)
            source, overlay = seed(plan); (source / n).unlink(); reject(source, overlay)
        for n in plan['provided'].values():
            source, overlay = seed(plan); (source / n).write_text('drift'); reject(source, overlay)
        for n, old, _, _ in plan['patches']:
            case_plan = copy.deepcopy(plan); source, overlay = seed(case_plan); p = source / n
            p.write_text(p.read_text().replace(old, '// moved anchor\n', 1)); case_plan['hashes'][n] = hashlib.sha256(p.read_bytes()).hexdigest()
            (overlay / 'archive_persistence_patches.json').write_text(json.dumps(case_plan)); reject(source, overlay)
        source, overlay = seed(plan); (source / WRITER).write_text('collision'); reject(source, overlay)
        source, overlay = seed(plan); (overlay / next(iter(plan['copies']))).unlink(); reject(source, overlay)
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in sorted(changed | {WRITER}) if n.endswith('.swift')]], check=True)
    for lang in ['ru', 'en']:
        text = (ROOT / f'ios/Sources/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        for key in ['Title', 'NoSpace', 'WriteFailed', 'Unreadable', 'Retry']: assert text.count('"NagramiX.Archive.Storage.' + key + '" = ') == 1
    for n in ['ios/archive_persistence.py', 'ios/apply_features.py', 'scripts/validate_archive_persistence.py']: ast.parse((ROOT / n).read_text())
    return {'outputs': len(b), 'changed': sorted(changed), 'added': [WRITER], 'unchanged': len(a) - len(changed), 'archive_schema_and_rendering': 'unchanged', 'UI_exact_reverse': 'PASS', 'overlay_replay': 'PASS', 'fail_closed_cases_without_writes': negatives, 'execution': executions, 'Apple_SDK': 'not run', 'physical_iPhone': 'pending', 'IPA': 'not started'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

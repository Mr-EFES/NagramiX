#!/usr/bin/env python3
"""Проверить изоляцию альбомов и файлов при рассылке копий нескольким адресатам."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'recipient_copy_isolation_patches.json').read_text())
A = 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift'
U = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
P = 'submodules/TelegramUI/Sources/Chat/NagramiXProtectedCopyPreparation.swift'
PENDING = 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift'
FETCH = 'submodules/TelegramCore/Sources/State/Fetch.swift'
STAGER = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift'
POLICY = 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'Recipient copy outputs differ'
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
    from validate_inline_temporary_voice import delegate_if_applied as delegate_next
    if delegate_next(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='recipient-copy-prior-') as folder:
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
    spec = importlib.util.spec_from_file_location('recipient_copy_isolation', OVERLAY / 'recipient_copy_isolation.py')
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
            module.apply_recipient_copy_isolation(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_recipient_copy_isolation(valid, OVERLAY)
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
        (overlay / 'recipient_copy_isolation_patches.json').write_text(json.dumps(bad))
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


def stripped(text):
    return 'import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')).replace('public ', '')


def common_source(source):
    boundary = (ROOT / 'scripts/tests/NagramiXContentCopyTests.swift').read_text().split('@main struct ContentCopyTests', 1)[0]
    anchor = '    func completedResourcePath(_ resource: MediaResource) -> String? { paths[resource.id.stringRepresentation] }'
    assert boundary.count(anchor) == 1
    boundary = boundary.replace(anchor, '    var lookupHook: ((MediaResource) -> String?)?\n    func completedResourcePath(_ resource: MediaResource) -> String? { if let lookupHook { return lookupHook(resource) }; return paths[resource.id.stringRepresentation] }')
    rich = (ROOT / 'scripts/tests/NagramiXRichContentCopyTests.swift').read_text().split('@main struct RichContentCopyTests', 1)[0]
    rich = rich.replace('    let postbox: TestCopyPostbox\n', '    let postbox: TestCopyPostbox\n    let pendingMessageManager = PendingStatusBoundary()\n')
    pending = (source / PENDING).read_text()
    forward = (source / U).read_text()
    commit_marker = 'if let batch = nagramiXRecipientCopies {\n                                    // All recipients'
    commit = block(forward, commit_marker)
    return boundary + '\n' + rich + '\n' + (ROOT / 'scripts/tests/NagramiXRecipientCopyBoundary.swift').read_text() + '\n' + block(pending, 'private enum PendingMessageState') + '''
private final class PendingCollector {
    private var messageContexts: [MessageId: PendingMessageContext] = [:]
    func add(_ messages: [EnqueueMessage], peer: Int) {
        for (i, message) in messages.enumerated() {
            let id = MessageId(peerId: PeerId(value: peer), value: i + 1)
            messageContexts[id] = PendingMessageContext(.waitingToBeSent(groupId: message.localGroupingKey, content: 1))
        }
    }
    func holdUpload(peer: Int) {
        for (id, context) in messageContexts where id.peerId.value == peer {
            context.state = .uploading(groupId: context.state.groupId)
        }
    }
    func collect(_ key: Int64) -> [(messageContext: PendingMessageContext, messageId: MessageId, content: PendingMessageUploadedContentAndReuploadInfo)]? {
        dataForPendingMessageGroup(key)
    }
''' + block(pending, 'private func dataForPendingMessageGroup(') + '''
}
private final class RecipientSender {
    let context: SenderContext
    var shareStatusDisposable: MetaDisposable?
    var errors = 0
    init(_ account: Account) { context = SenderContext(account) }
    func present(_ alert: Int, in surface: SenderSurface) { errors += 1 }
    func start(_ batch: NagramiXRecipientCopyBatch, signals: [Signal<[MessageId?], NoError>], counts: [Int], completed: @escaping () -> Void) {
        let nagramiXRecipientCopies: NagramiXRecipientCopyBatch? = batch
        let copyEnqueueSignals = signals
        let copyExpectedCounts = counts
        let showForwardResult = completed
''' + commit + '\n    }\n}\n'


def run_swift(source, swiftc, temp):
    common = common_source(source)
    helpers = []
    for path in (STAGER, POLICY):
        destination = temp / Path(path).name
        destination.write_text(stripped((source / path).read_text()))
        helpers.append(destination)
    current = (source / A).read_text()
    old_reuse = current.replace('        let copy = NagramiXArchivedMediaCopy(mediaBox: account.postbox.mediaBox)', '        let copy = mediaCopies.first ?? NagramiXArchivedMediaCopy(mediaBox: account.postbox.mediaBox)')
    old_group = current.replace('        batches.append(batch)', '        batches.append(batches.first ?? batch)')
    runtime = (ROOT / 'scripts/tests/NagramiXRecipientCopyTests.swift').read_text()
    rich = '@main struct RichContentCopyTests' + (ROOT / 'scripts/tests/NagramiXRichContentCopyTests.swift').read_text().split('@main struct RichContentCopyTests', 1)[1]
    runs = []
    for label, implementation, tests in [('current', current, runtime), ('old-shared-group', old_group, runtime), ('old-shared-path', old_reuse, runtime), ('rich-regression', current, rich)]:
        outgoing = temp / (label + '-copier.swift')
        outgoing.write_text(stripped(implementation))
        suite = temp / (label + '.swift'); suite.write_text(common + '\n' + tests)
        for optimized in (False, True):
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command += ['-O']
            subprocess.run([*command, *map(str, helpers), str(outgoing), str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label in ('current', 'rich-regression'):
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(binary.name + ': ' + result.stdout.strip())
            else:
                expected = 'each recipient must have a separate pending group' if label == 'old-shared-group' else 'movable staging files are independent per recipient'
                assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr
                runs.append(binary.name + ': прежний дефект воспроизведён и отвергнут')
            print(runs[-1], flush=True)
    return runs


def contracts(source):
    pending = (source / PENDING).read_text()
    collector = block(pending, 'private func dataForPendingMessageGroup(')
    assert 'for (id, context) in self.messageContexts' in collector
    assert 'if contextGroupId == groupId' in collector
    assert 'let peerId = group[0].messageId.peerId' in block(pending, 'private func sendGroupMessagesContent(')
    assert 'move: localFileResource.isUniquelyReferencedTemporaryFile' in (source / FETCH).read_text()
    forward = (source / U).read_text()
    assert forward.index('nagramiXPrepareRecipientCopies(') < forward.index('strongController.dismiss()', forward.index('let proceed ='))
    assert forward.count('for (destinationIndex, target) in targetPeersShouldDivert.enumerated()') == 1
    assert 'batch.messages(forRecipientAt: destinationIndex, template: result)' in forward
    assert 'recipientCorrelationIds.append(id)' in forward
    assert 'combineLatest(targetPeersShouldDivertSignals) |> take(1)' in forward
    assert forward.count('guard !nagramiXCopyCommitted else { return }') == 1
    assert forward.count('guard !nagramiXProtectedOriginal || NagramiXPrivacySettings.current.bypassScreenshots') == 3
    copies_start = forward.index('                                if let batch = nagramiXRecipientCopies {\n                                    // All recipients')
    copies_end = forward.index('\n                                } else {\n                                    showForwardResult()', copies_start)
    copies_commit = forward[copies_start:copies_end]
    assert copies_commit.index('batch.commit()') < copies_commit.index('combineLatest(copyEnqueueSignals)') < copies_commit.index('showForwardResult()')
    assert 'zip(accepted, copyExpectedCounts).allSatisfy' in copies_commit
    assert 'accepted.flatMap { $0 }' in copies_commit
    assert 'guard !finished.swap(true), let self else { return }' in block((source / P).read_text(), 'func nagramiXPrepareProtectedCopy(')
    for marker in ('func nagramiXAllowsProtectedContentExport(', 'func nagramiXSaveCopiedMediaToFiles(', 'func nagramiXPrepareRichTextCopy('):
        assert block((source / P).read_text(), marker) == block((OVERLAY / PLAN['previous'][P]).read_text(), marker), marker
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_free_content(') < pipeline.index('    apply_recipient_copy_isolation(')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    contracts(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-recipient-copy-check-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'changed_files': len(PLAN['outputs']), 'guards': len(PLAN['guards']),
              'fail_closed': rejected, 'executions': runs, 'sdk': 'не запускалась',
              'device': 'ожидает проверки на iPhone',
              'runtime': 'production outgoing copier, recipient batch, file stager and native pending-group collector; real Foundation IO; Postbox/API boundaries; UI wiring guarded and parsed'}
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

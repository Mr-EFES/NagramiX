#!/usr/bin/env python3
"""Verify own voice/round view-once copies without building an IPA."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
MENU = 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'
LOAD = 'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
CORE = 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift'
PREPARE = 'submodules/TelegramUI/Sources/Chat/NagramiXProtectedCopyPreparation.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def validate(args):
    plan = json.loads((ROOT / 'ios/own_once_copy_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    changed = {n for n in before if before[n] != after[n]}
    assert before.keys() == after.keys()
    assert changed == {FORWARD, MENU, LOAD, CORE, PREPARE}, changed
    texts = {n: (args.before / n).read_text() for n in plan['hashes']}
    assert all(before[n] == sha for n, sha in plan['hashes'].items())
    for n, old, new, count in plan['patches']:
        assert texts[n].count(old) == count, old
        texts[n] = texts[n].replace(old, new, count)
    assert all(text == (args.after / n).read_text() for n, text in texts.items())
    for template, name in [('TelegramCore/NagramiXContentCopy.swift', CORE), ('TelegramUI/NagramiXProtectedCopyPreparation.swift', PREPARE)]:
        assert (ROOT / 'ios/Sources' / template).read_bytes() == (args.after / name).read_bytes()
    # General saving/protected export remains unchanged. The only preparation
    # change passes the actual account identity, not any preference or sender ID.
    old_core, new_core = (args.before / CORE).read_text(), (args.after / CORE).read_text()
    scope = lambda t: t.split('    var nagramiXAllowsContentCopy:', 1)[1].split('private enum', 1)[0]
    assert scope(old_core) == scope(new_core)
    prep_before, prep_after = (args.before / PREPARE).read_text(), (args.after / PREPARE).read_text()
    assert prep_before.replace('messages: messages)\n', 'messages: messages, accountPeerId: self.context.account.peerId)\n', 1) == prep_after
    spec = importlib.util.spec_from_file_location('own_once_copy', ROOT / 'ios/own_once_copy.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        def seed(target):
            for n in plan['hashes']:
                p = target / n
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.before / n, p)
        def reject(target, label, overlay=ROOT / 'ios'):
            saved = manifest(target)
            try:
                module.apply_own_once_copy(target, overlay)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError(label)
            assert manifest(target) == saved, label
            rejected.append(label)
        target = folder / 'valid'
        seed(target)
        module.apply_own_once_copy(target, ROOT / 'ios')
        assert all((target / n).read_text() == texts[n] for n in texts)
        reject(target, 'reapply')
        for i, n in enumerate(plan['hashes']):
            for kind in ['missing', 'drift']:
                target = folder / (kind + str(i))
                seed(target)
                if kind == 'missing': (target / n).unlink()
                else: (target / n).write_text((target / n).read_text() + '\n// drift\n')
                reject(target, kind + ' ' + n)
        overlay = folder / 'broken-overlay'
        overlay.mkdir()
        invalid = json.loads(json.dumps(plan))
        invalid['patches'][-1][1] += '// missing exact anchor'
        (overlay / 'own_once_copy_patches.json').write_text(json.dumps(invalid))
        target = folder / 'anchor'
        seed(target)
        reject(target, 'last anchor mismatch', overlay)

    forward = (args.after / FORWARD).read_text()
    menu = (args.after / MENU).read_text()
    production = 'enum NagramiXMessageTransferMode:' + forward.split('enum NagramiXMessageTransferMode:', 1)[1].split('func nagramiXArchivedCopyAlert', 1)[0]
    own = forward.split('        let nagramiXOwnViewOnceCopy = ', 1)[1].split('\n', 1)[0].replace('self.context.account.peerId', 'accountPeerId')
    protected = forward.split('        let nagramiXProtectedCopy = ', 1)[1].split('\n', 1)[0].replace('self.presentationInterfaceState.copyProtectionEnabled', 'enabled').replace('self.chatLocation.peerId', 'peer')
    effective = forward.split('        let transferMode = nagramiXProtectedCopy && ', 1)[1].split('\n', 1)[0]
    picker = forward.split('multipleSelectionLimit: nagramiXProtectedCopy && ', 1)[1].split(', forwardedMessageIds:', 1)[0]
    picker_ids = forward.split(', forwardedMessageIds: ', 1)[1].split(', selectForumThreads:', 1)[0].replace('messages.map { $0.id }', '[1]')
    production += '\n' + '\n'.join([
        'func productionProtectedCopy(_ transferMode: NagramiXMessageTransferMode, _ messages: [Message], _ enabled: Bool, _ peer: PeerId?, accountPeerId: PeerId? = nil) -> Bool { let nagramiXOwnViewOnceCopy = ' + own + '; return ' + protected + ' }',
        'func productionEffectiveMode(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> NagramiXMessageTransferMode { nagramiXProtectedCopy && ' + effective + ' }',
        'func productionPickerLimit(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> Int? { nagramiXProtectedCopy && ' + picker + ' }',
        'func productionPickerHasSourceIds(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> Bool { let ids: [Int] = ' + picker_ids + '; return !ids.isEmpty }',
    ])
    block = menu.split('        let nagramiXCanCopySelection = ', 1)[1].split('                actions.append', 1)[0]
    setup = 'let nagramiXCanCopySelection = ' + block.split('\n        if ', 1)[0]
    setup = setup.replace('context.account.peerId', 'accountPeerId')
    condition = block.split('\n        if ', 1)[1].split(' {\n', 1)[0].replace('data.messageActions.options.contains(.forward)', 'native')
    repost = block.split('\n            if ', 1)[1].split(' {\n', 1)[0].replace('data.messageActions.options.contains(.forward)', 'native')
    production += '\nfunc productionMenu(_ messagesToForward: [Message], accountPeerId: PeerId, native: Bool, isCopyProtected: Bool) -> (Bool,Bool) {\n' + setup + '\nreturn (' + condition + ', ' + repost + ')\n}\n'
    mode_gate = forward.split('                        let allowsMode: Bool\n', 1)[1].split('                        // Revalidate', 1)[0]
    production += '\nenum TestSendMode { case generic, silent, schedule, whenOnline }\nfunc productionAllowsMode(_ mode: TestSendMode) -> Bool {\nlet allowsMode: Bool\n' + mode_gate + '\nreturn allowsMode\n}\n'
    enqueue = (args.after / 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift').read_text()
    native_attributes = 'func outgoingMessageAttributes(' + enqueue.split('func outgoingMessageAttributes(', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
    assert 'case _ as AutoremoveTimeoutMessageAttribute:\n            return true' in enqueue
    # The requested-attribute filter is a boundary here; its native allow-list
    # is checked above. Execute the actual native media-timer conversion.
    production += '\nfunc filterMessageAttributesForOutgoingMessage(_ attributes: [MessageAttribute]) -> [MessageAttribute] { attributes }\n' + native_attributes
    upload = (args.after / 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift').read_text()
    assert 'if autoRemove {\n        return .single(.none)' in upload
    assert 'autoRemove: autoremoveMessageAttribute != nil || autoclearMessageAttribute != nil' in upload
    document_upload = upload.split('private func uploadedMediaFileContent(', 1)[1]
    assert 'ttlSeconds = attribute.timeout' in document_upload
    assert 'if ttlSeconds != nil {\n                            return .single(.content(PendingMessageUploadedContentAndReuploadInfo(content: .media(.inputMediaUploadedDocument' in document_upload
    # Every opening point uses an account-aware capability; the final builder
    # receives the same account before any copies are enqueued.
    load = (args.after / LOAD).read_text()
    assert 'canCopyMessagesWithoutSource: { [weak self] messages in' in load
    assert 'return nagramiXCanCopyMessagesAsNew(messages, accountPeerId: self.context.account.peerId)' in load
    assert menu.count('nagramiXCanCopyMessagesAsNew(selectAll ? messages : [message], accountPeerId: context.account.peerId)') == 2
    assert 'forceLocalMedia: nagramiXProtectedCopy, accountPeerId: strongSelf.context.account.peerId)' in forward
    assert 'if nagramiXOwnViewOnceCopy && transferMode == .forwardWithSource {' in forward
    assert 'filter.formUnion([.onlyPrivateChats, .excludeSavedMessages, .excludeSecretChats, .excludeBots])' in forward
    assert forward.index('guard allowsMode && allowsPeers else') < forward.index('strongController.dismiss()')
    assert forward.index('if nagramiXOwnViewOnceCopy && targetPeersShouldDivert.contains(where: { $0.1 })') < forward.index('enqueueMessages(account:')
    prepare = forward.split('        let nagramiXOwnViewOnceCopy = ', 1)[1].split('        let _ = self.presentVoiceMessageDiscardAlert', 1)[0]
    assert 'nagramiXPrepareProtectedCopy' in prepare and 'enqueueMessages' not in prepare
    for literal in ['case .copyAsNew, .copyToSingleRecipient:', 'case .silent:', 'case .schedule:', 'case .whenOnline:', 'sendPaidMessageStars', 'nagramiXCopyThreadIds[peer.id]', 'guard !transferMode.singleRecipient || peers.count == 1']:
        assert literal in forward
    execution = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        sources = []
        for i, name in enumerate(['submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', CORE, PREPARE]):
            text = (args.after / name).read_text()
            p = folder / ('Production' + str(i) + '.swift')
            p.write_text('import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')).replace('public ', '') + '\n')
            sources.append(p)
        p = folder / 'Copier.swift'
        p.write_text('import Foundation\n' + production)
        sources.append(p)
        p = folder / 'ExistingTests.swift'
        p.write_text((ROOT / 'scripts/tests/NagramiXContentCopyTests.swift').read_text().replace('@main struct ContentCopyTests', 'struct ContentCopyTests', 1))
        sources.append(p)
        sources += [ROOT / 'scripts/tests/NagramiXContentCopyUIBoundary.swift', ROOT / 'scripts/tests/NagramiXOwnOnceCopyTests.swift']
        for mode in ['debug', 'optimized']:
            binary = folder / ('tests-' + mode)
            cmd = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, sources), '-o', str(binary)]
            if mode == 'optimized': cmd.insert(1, '-O')
            subprocess.run(cmd, check=True)
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, timeout=45).strip())
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.after / n) for n in sorted(changed)]], check=True)
    for name in ['ios/own_once_copy.py', 'ios/apply_features.py']:
        ast.parse((ROOT / name).read_text())
    return {'native_outputs': len(after), 'changed': sorted(changed), 'unchanged': len(after) - len(changed),
            'sha_guards': len(plan['hashes']), 'exact_operations': len(plan['patches']),
            'fail_closed': rejected, 'execution': execution,
            'native_sdk': 'not run: requires separate build command', 'physical_iPhone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2) + '\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

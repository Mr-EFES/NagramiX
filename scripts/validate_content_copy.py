#!/usr/bin/env python3
"""Validate protected copy integration without building the iOS application."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def validate(before, after, swiftc):
    plan = json.loads((ROOT / 'ios/content_copy_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    changed = {n for n in a.keys() & b.keys() if a[n] != b[n]}
    expected = {n for n, *_ in plan['patches']} | {f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru', 'en']}
    assert changed == expected, changed ^ expected
    assert b.keys() - a.keys() == set(plan['copies'].values()) and not a.keys() - b.keys()
    texts = {n: (before / n).read_text() for n in plan['hashes']}
    assert all(a[n] == sha for n, sha in plan['hashes'].items())
    for n, old, new, count in plan['patches']:
        assert texts[n].count(old) == count
        texts[n] = texts[n].replace(old, new, count)
    assert all((after / n).read_bytes() == text.encode() for n, text in texts.items())
    for template, n in plan['copies'].items():
        assert (after / n).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    spec = importlib.util.spec_from_file_location('content_copy', ROOT / 'ios/content_copy.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        def seed(folder):
            for n in plan['hashes']:
                p = folder / n; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(before / n, p)
            for n in plan['copies'].values(): (folder / n).parent.mkdir(parents=True, exist_ok=True)
        def reject(folder, label, overlay=ROOT / 'ios'):
            saved = manifest(folder)
            try: module.apply_content_copy(folder, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(folder) == saved, 'partial write: ' + label
            rejected.append(label)
        folder = base / 'valid'; seed(folder); module.apply_content_copy(folder, ROOT / 'ios')
        assert all((folder / n).read_bytes() == (after / n).read_bytes() for n in plan['hashes'])
        reject(folder, 'reapply')
        for index, n in enumerate(plan['hashes']):
            for kind in ['missing', 'drift']:
                folder = base / (kind + str(index)); seed(folder)
                if kind == 'missing': (folder / n).unlink()
                else: (folder / n).write_bytes((folder / n).read_bytes() + b'\n// drift\n')
                reject(folder, kind + ' ' + n)
        for index, (template, n) in enumerate(plan['copies'].items()):
            folder = base / ('collision' + str(index)); seed(folder); (folder / n).write_text('// collision'); reject(folder, 'collision ' + n)
            folder = base / ('parent' + str(index)); seed(folder); (folder / n).parent.rmdir(); reject(folder, 'missing parent ' + n)
            folder = base / ('template' + str(index)); seed(folder)
            overlay = base / ('overlay' + str(index)); overlay.mkdir(); shutil.copy2(ROOT / 'ios/content_copy_patches.json', overlay)
            for other in plan['copies']:
                if other != template:
                    p = overlay / other; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / 'ios' / other, p)
            reject(folder, 'missing template ' + template, overlay)
    forward = (after / FORWARD).read_text()
    production = forward.split('enum NagramiXMessageTransferMode:', 1)[1].split('func nagramiXArchivedCopyAlert', 1)[0]
    production = 'enum NagramiXMessageTransferMode:' + production
    protected = forward.split('        let nagramiXProtectedCopy = ', 1)[1].split('\n', 1)[0]
    protected = protected.replace('self.presentationInterfaceState.copyProtectionEnabled', 'enabled').replace('self.chatLocation.peerId', 'peer')
    effective = forward.split('        let transferMode = nagramiXProtectedCopy && ', 1)[1].split('\n', 1)[0]
    picker = forward.split('multipleSelectionLimit: nagramiXProtectedCopy && ', 1)[1].split(', forwardedMessageIds:', 1)[0]
    picker_ids = forward.split(', forwardedMessageIds: ', 1)[1].split(', selectForumThreads:', 1)[0].replace('messages.map { $0.id }', '[1]')
    helpers = '\n'.join([
        'func productionProtectedCopy(_ transferMode: NagramiXMessageTransferMode, _ messages: [Message], _ enabled: Bool, _ peer: PeerId?) -> Bool { ' + protected + ' }',
        'func productionEffectiveMode(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> NagramiXMessageTransferMode { nagramiXProtectedCopy && ' + effective + ' }',
        'func productionPickerLimit(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> Int? { nagramiXProtectedCopy && ' + picker + ' }',
        'func productionPickerHasSourceIds(_ transferMode: NagramiXMessageTransferMode, _ nagramiXProtectedCopy: Bool) -> Bool { let ids: [Int] = ' + picker_ids + '; return !ids.isEmpty }',
    ])
    production += '\n' + helpers
    execution = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        sources = []
        for index, name in enumerate(['submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift', 'submodules/TelegramUI/Sources/Chat/NagramiXProtectedCopyPreparation.swift']):
            # Bodies are unchanged; Linux doubles replace module boundaries and
            # access levels do not establish native SDK API compatibility.
            source = (after / name).read_text()
            p = folder / ('Production' + str(index) + '.swift')
            p.write_text('import Foundation\n' + '\n'.join(line for line in source.splitlines() if not line.startswith('import ')).replace('public ', '') + '\n'); sources.append(p)
        p = folder / 'Copier.swift'; p.write_text('import Foundation\n' + production); sources.append(p)
        for mode in ['debug', 'optimized']:
            binary = folder / ('test-' + mode)
            command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, sources), str(ROOT / 'scripts/tests/NagramiXContentCopyTests.swift'), str(ROOT / 'scripts/tests/NagramiXContentCopyUIBoundary.swift'), '-o', str(binary)]
            if mode == 'optimized': command.insert(1, '-O')
            subprocess.run(command, check=True)
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, timeout=40).strip())
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in changed | set(plan['copies'].values()) if n.endswith('.swift')]], check=True)
    # Check that preparation/selection cannot enqueue, and the native send
    # transformations, payment/topic handling and archived draft remain intact.
    prepare = forward.split('        let nagramiXProtectedCopy = ', 1)[1].split('        let _ = self.presentVoiceMessageDiscardAlert', 1)[0]
    assert 'enqueueMessages' not in prepare and 'nagramiXPrepareProtectedCopy' in prepare
    assert 'let liveMessages = messages.filter { !$0.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }) }' in prepare
    peer = forward.split('            controller.peerSelected = ', 1)[1]
    assert 'if transferMode == .copyAsNew || nagramiXProtectedCopy {' in peer
    branch = peer.split('if transferMode == .copyAsNew || nagramiXProtectedCopy {', 1)[1].split('                if resetCurrent', 1)[0]
    assert 'nagramiXSelectCopyRecipient(peer)' in branch and 'enqueueMessages' not in branch and 'return' in branch
    for literal in ['case .copyAsNew, .copyToSingleRecipient:', 'forceLocalMedia: nagramiXProtectedCopy', 'case .silent:', 'case .schedule:', 'case .whenOnline:', 'sendPaidMessageStars', 'nagramiXCopyThreadIds[peer.id]', 'guard !transferMode.singleRecipient || peers.count == 1']:
        assert literal in forward, literal
    menu = (after / 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift').read_text()
    assert 'if data.messageActions.options.contains(.forward) && !isCopyProtected {' in menu
    assert 'if resourceAvailable, !message.containsSecretMedia && (!isCopyProtected || nagramiXProtectedExport)' in menu
    assert 'if file.isMusic || nagramiXProtectedExport' in menu
    assert menu.count('interfaceInteraction.forwardMessagesWithoutSource?(messagesToForward)') == 1
    assert menu.count('interfaceInteraction.copyMessagesWithoutSource?(messagesToForward)') == 1
    panel = (after / 'submodules/TelegramUI/Components/Chat/ChatMessageSelectionInputPanelNode/Sources/ChatMessageSelectionInputPanelNode.swift').read_text()
    assert panel.count('if let actions = self.actions, actions.isCopyProtected {') == 2 # native Repost/external Share remain protected
    assert 'let canCopySelection = self.nagramiXCanCopySelection\n' in panel
    assert 'messages.count == selectedIds.count' in panel and 'self.selectedMessages == selectedIds' in panel
    controller = (after / 'submodules/TelegramUI/Sources/ChatController.swift').read_text()
    assert controller.count('let nagramiXContentCopyDisposable = MetaDisposable()') == controller.count('self.nagramiXContentCopyDisposable.dispose()') == 1
    assert 'nagramiXSaveCopiedMediaToFiles(' in controller and 'nagramiXAllowsProtectedContentExport(message._asMessage())' in controller
    return {'outputs': len(b), 'changed': sorted(changed), 'added': sorted(b.keys() - a.keys()), 'unchanged': len(a) - len(changed), 'sha_guards': len(plan['hashes']), 'exact_operations': len(plan['patches']), 'fail_closed': rejected, 'execution': execution, 'apple_sdk': 'not run: no build authorization', 'physical_iphone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

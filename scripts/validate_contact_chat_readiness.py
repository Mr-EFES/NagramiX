#!/usr/bin/env python3
"""Reproduce build112's permission-dependent chat stall with real SwiftSignalKit."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = 'submodules/TelegramUI/Sources/ApplicationContext.swift'
KIT = 'submodules/SSignalKit/SwiftSignalKit/Source/'
PIN = 'f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838'
NATIVE = ['Atomic.swift', 'Bag.swift', 'Disposable.swift', 'Subscriber.swift',
          'Signal.swift', 'Promise.swift', 'Signal_Mapping.swift',
          'Signal_Meta.swift', 'Signal_Take.swift', 'Signal_Combine.swift',
          'Signal_Single.swift']


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def validate(args):
    before, after = manifest(args.before), manifest(args.after)
    assert before.keys() == after.keys()
    assert [n for n in before if before[n] != after[n]] == [APP]
    a, b = (args.before / APP).read_text(), (args.after / APP).read_text()
    tree = ast.parse((ROOT / 'ios/apply_features.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'apply_deferred_contact_permission')
    assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'patches' for t in n.targets))
    patches = ast.literal_eval(assignment.value)
    assert len(patches) == 3
    old, new = patches[-1]
    assert a.count(old) == 1 and a.replace(old, new, 1) == b
    assert 'DeviceAccess.authorizeAccess' not in new and 'UserDefaults' not in new
    # Keep the native import producer, sync preference and startup request policy.
    start = '        let importableContacts = '
    end = '        self.context.account.importableContacts.set(optionalImportableContacts)'
    producer_a = a.split(start, 1)[1].split(end, 1)[0]
    producer_b = b.split(start, 1)[1].split(end, 1)[0]
    assert producer_a == producer_b
    assert 'var order = config.order.filter { $0 != .contacts }' in b
    assert 'if contactsTimestamp == nil, case .requestable' not in b

    pinned = json.loads(args.upstream_tree.read_text())
    assert pinned['sha'] == PIN
    entries = {e['path']: e for e in pinned['tree'] if e['type'] == 'blob'}
    names = [KIT + n for n in NATIVE] + [
        'submodules/TelegramUI/Sources/DeviceContactDataManager.swift',
        'submodules/TelegramUI/Sources/ChatControllerContentData.swift',
        'submodules/TelegramCore/Sources/SyncCore/SyncCore_ContactsSettings.swift']
    for name in names:
        data = (args.upstream / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entries[name]['sha']
    manager = (args.upstream / names[-3]).read_text()
    assert 'authorizationStatus != .notDetermined' in manager
    assert 'if self.accessInitialized {\n            updated(self.importableContacts)' in manager
    assert 'return ContactsSettings(synchronizeContacts: true)' in (args.upstream / names[-1]).read_text()
    promise = (args.upstream / (KIT + 'Promise.swift')).read_text()
    assert 'self.value = nil' in promise.split('public func set(', 1)[1].split('public func get(', 1)[0]
    history = (args.after / 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
    assert 'deviceContactsNumbers |> debug_measureTimeToFirstEvent(label: "chatHistoryNode_deviceContactsNumbers")' in history
    assert 'let historyViewTransitionDisposable = (combineLatest(queue: messageViewQueue,' in history
    assert '_isReady.set(true)' in history

    spec = importlib.util.spec_from_file_location('features', ROOT / 'ios/apply_features.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []
    execution = []
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        stage = folder / 'stage'
        path = stage / APP
        path.parent.mkdir(parents=True)
        original = args.prestage.read_bytes()
        assert hashlib.sha256(original).hexdigest() == 'a4459e1ecf7265ed5971c183fdb3d2bfa85537adb3931d72d9be416652d358ca'
        path.write_bytes(original)
        module.apply_deferred_contact_permission(stage)
        assert path.read_bytes() == (args.after / APP).read_bytes()
        for label, data in [('reapply', path.read_bytes()), ('drift', original + b'\n// drift\n'), ('missing', None)]:
            if data is None:
                path.unlink()
            else:
                path.write_bytes(data)
            saved = manifest(stage)
            try:
                module.apply_deferred_contact_permission(stage)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError(label)
            assert manifest(stage) == saved
            rejected.append(label)
        sources = []
        for name in NATIVE:
            text = (args.upstream / (KIT + name)).read_text()
            # Apple Foundation reexports this symbol; Linux needs its import.
            if name == 'Signal_Meta.swift':
                text = 'import CoreFoundation\n' + text
            target = folder / name
            target.write_text(text)
            sources.append(target)
        support = folder / 'QueueBoundary.swift'
        support.write_text('public final class Queue {}\n'
                           'public func deliverOn<T,E>(_ queue: Queue) -> (Signal<T,E>) -> Signal<T,E> {\n'
                           ' return { _ in fatalError("OS scheduling must not be used in this synchronous test") }\n}\n')
        sources.append(support)
        selection = producer_a.split('        |> mapToSignal', 1)[1]
        production = 'import Foundation\nextension TestBinding {\n'
        for name, body in [('bindBefore', old), ('bindAfter', new)]:
            production += 'func ' + name + '(_ optionalImportableContacts: ContactSignal) {\n'
            production += end + '\n' + body + '\n}\n'
        production += '}\nfunc productionImportable(settings: Signal<TestPreferences?,NoError>, book: ContactSignal) -> ContactSignal {\n'
        production += 'let importableContacts = book\nreturn settings |> mapToSignal' + selection + '\n}\n'
        production += 'func observeHistory(_ context: TestContext, history: Signal<Bool,NoError> = .single(true), next: @escaping (Set<String>) -> Void) -> Disposable {\n'
        production += 'let numbers = context.sharedContext.deviceContactPhoneNumbers.get() |> distinctUntilChanged\n'
        production += 'return combineLatest(' + ',\n'.join(['history'] + ['Signal<Bool,NoError>.single(true)'] * 23 + ['numbers', 'Signal<Bool,NoError>.single(true)'])
        production += ').start(next: { next($0.24) })\n}\n'
        target = folder / 'Production.swift'
        target.write_text(production)
        sources.append(target)
        sources.append(ROOT / 'scripts/tests/NagramiXContactChatReadinessTests.swift')
        for mode in ['debug', 'optimized']:
            binary = folder / ('test-' + mode)
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'),
                       *map(str, sources), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, timeout=30).strip())
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.after / APP)], check=True)
    return {'native_outputs': len(after), 'changed': [APP], 'unchanged': len(after) - 1,
            'upstream_signal_files': len(NATIVE), 'signal_implementation': 'real pinned SwiftSignalKit',
            'history_gate': 'real 26-way combineLatest; other 25 inputs are ready boundary values',
            'fail_closed': rejected, 'execution': execution, 'native_import_and_request_policy': 'unchanged',
            'apple_sdk': 'not run: requires separate build command', 'physical_iPhone': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'prestage', 'upstream', 'upstream-tree', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Проверить foreground прокси и сохранность файлов при конкурентной очистке."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest
from validate_archive_persistence import harness, WRITER
from validate_outgoing_archive import production as outgoing_production

ROOT = Path(__file__).resolve().parents[1]
C = 'submodules/TelegramCore/Sources/Network/NagramiXProxyFailoverController.swift'
R = 'submodules/TelegramCore/Sources/Network/NagramiXNetworkRecovery.swift'
N = 'submodules/TelegramCore/Sources/Network/Network.swift'
M = 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift'
A = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
P = 'submodules/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def standalone(text):
    for module in ['SwiftSignalKit', 'NagramiXMediaSettings', 'UIKit', 'Postbox']:
        text = text.replace('import ' + module + '\n', '')
    return text


def proxy_boundary():
    text = (ROOT / 'scripts/tests/NagramiXProxyFailoverBoundary.swift').read_text()
    original = block(text, 'final class Queue {')
    current = '''final class Queue {
    private static var pending: [(String, () -> Void)] = []
    private let name: String
    init(name: String) { self.name = name }
    static func mainQueue() -> Queue { Queue(name: "main") }
    func async(_ action: @escaping () -> Void) { Self.pending.append((self.name, action)) }
    @discardableResult static func runNext(named: String? = nil) -> Bool {
        guard let index = self.pending.firstIndex(where: { named == nil || $0.0 == named }) else { return false }
        self.pending.remove(at: index).1(); return true
    }
    static func drain(excludingMain: Bool = false) {
        var turns = 0
        while let next = self.pending.firstIndex(where: { !excludingMain || $0.0 != "main" }) {
            turns += 1; precondition(turns < 10000, "unbounded controller callback loop")
            self.pending.remove(at: next).1()
        }
    }
}
final class UIApplication {
    enum State { case active, inactive, background }
    static let shared = UIApplication()
    var applicationState: State = .active
}'''
    return text.replace(original, current, 1)


def media_boundary():
    text = (ROOT / 'scripts/tests/NagramiXOutgoingArchiveBoundary.swift').read_text()
    text = text.replace('    var fetched=0\n', '    var fetched=0\n    var beforeRemove: (() -> Void)?\n', 1)
    text = text.replace('    func removeCachedResources(_ ids:[MediaResourceId],force:Bool)->Signal<Void,NoError>{\n',
                        '    func removeCachedResources(_ ids:[MediaResourceId],force:Bool)->Signal<Void,NoError>{\n        self.beforeRemove?()\n', 1)
    atomic = block(text, 'final class Atomic<T> {')
    text = text.replace(atomic, '''final class Atomic<T> {
    private var value: T
    private let lock = NSLock()
    init(value: T) { self.value = value }
    func with<R>(_ f: (T) -> R) -> R { lock.lock(); defer { lock.unlock() }; return f(value) }
    func swap(_ next: T) -> T { lock.lock(); defer { lock.unlock() }; let old = value; value = next; return old }
    func modify(_ f: (T) -> T) -> T { lock.lock(); defer { lock.unlock() }; value = f(value); return value }
}''', 1)
    return text



def test_inspection():
    # Same-file extension inspects private snapshots; production bodies and
    # access control remain unchanged in the app and in these test inputs.
    return """
extension NagramiXArchivedMediaStore {
    var testDirectory: String { self.directory }
    var testFilesEmpty: Bool { self.files.with { $0.isEmpty } }
    var testReservationsEmpty: Bool { self.reservations.with { $0.isEmpty } }
    func testReservation(_ key: String) -> Int64? { self.reservations.with { $0[key]?.0 } }
    func testHasOwner(_ key: String) -> Bool { self.owners[key] != nil }
    func testHasRequest(_ id: String) -> Bool { self.requests[id] != nil }
}
"""


def validate_guards(source, plan, temp):
    spec = importlib.util.spec_from_file_location('recovery_storage_fixes', ROOT / 'ios/recovery_storage_fixes.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    before = {name: (source / name).read_bytes() for name in {**plan['guards'], **plan['inputs']}}
    for name in plan['inputs']:
        text = before[name].decode()
        for target, old, new, count in reversed(plan['patches']):
            if target == name:
                assert text.count(new) == count, (name, new)
                text = text.replace(new, old, count)
        assert sha(text.encode()) == plan['inputs'][name], name
        before[name] = text.encode()
    checks = []
    def seed(label):
        root = temp / label
        for name, data in before.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return root
    def reject(root, label, overlay=ROOT / 'ios'):
        state = manifest(root)
        try: module.apply_recovery_storage_fixes(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят некорректный вход: ' + label)
        assert manifest(root) == state, 'Частичная запись: ' + label
        checks.append(label)
    target = seed('valid'); module.apply_recovery_storage_fixes(target, ROOT / 'ios')
    assert all((target / name).read_bytes() == (source / name).read_bytes() for name in before)
    reject(target, 'reapply')
    for name in before:
        for mode in ['missing', 'drift']:
            target = seed('bad-' + str(len(checks)))
            path = target / name
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, mode + ' ' + name)
    mutations = []
    for index in range(len(plan['patches'])):
        altered = copy.deepcopy(plan); altered['patches'][index][1] += ' broken'
        mutations.append(('anchor-' + str(index), altered))
    for section in ['inputs', 'outputs', 'guards']:
        altered = copy.deepcopy(plan); altered[section][next(iter(altered[section]))] = '0' * 64
        mutations.append((section + '-sha', altered))
    altered = copy.deepcopy(plan); altered['patches'][0][0] = '../outside.swift'; mutations.append(('operation-path', altered))
    altered = copy.deepcopy(plan); altered['inputs']['../outside.swift'] = '0' * 64; altered['outputs']['../outside.swift'] = '0' * 64
    mutations.append(('traversal', altered))
    for label, altered in mutations:
        overlay = temp / ('plan-' + label); overlay.mkdir()
        (overlay / 'recovery_storage_fixes_patches.json').write_text(json.dumps(altered))
        reject(seed('root-' + label), label, overlay)
    return before, checks


def execute(source, before, swiftc, temp):
    runs = []
    controller = temp / 'Controller.swift'; controller.write_text(standalone((source / C).read_text()))
    boundary = temp / 'ProxyBoundary.swift'; boundary.write_text(proxy_boundary())
    store = temp / 'MediaClear.swift'
    revision = block((source / A).read_text(), 'public struct NagramiXMessageRevision:')
    store.write_text(media_boundary() + '\n' + revision + '\n' + standalone((source / M).read_text()) + test_inspection() + '\n'
                     + (ROOT / 'scripts/tests/NagramiXArchiveClearReservationTests.swift').read_text())
    storage = temp / 'ArchiveStorage.swift'; storage.write_text(harness((source / A).read_text()))
    recovery = temp / 'Recovery.swift'; recovery.write_text(standalone((source / R).read_text()))
    # Keep/reconnect methods come from the final native Network, not a model.
    native = (source / N).read_text()
    keep = '        let shouldKeepConnectionSignal = self.shouldKeepConnection.get()\n'
    keep += native.split(keep, 1)[1].split('\n\n        self.isUserOnlineDisposable', 1)[0]
    marker = '    @discardableResult\n    public func reconnectForNagramiXDnsChange'
    reconnect = marker + native.split(marker, 1)[1].split('\n    }', 1)[0] + '\n    }'
    net = (ROOT / 'scripts/tests/NagramiXNetworkRecoveryBoundary.swift').read_text().replace('        // NATIVE_KEEP_SUBSCRIPTION', keep).replace('    // NATIVE_RECONNECT_METHOD', reconnect)
    net = net.replace('final class Network {', 'final class LivenessBoundary { func setResumed(_ value: Bool) {} }\nfinal class Network {\n    var livenessMonitor: LivenessBoundary?')
    proxy = proxy_boundary()
    integrated = temp / 'IntegratedProxy.swift'
    integrated.write_text(proxy.split('final class Network {', 1)[0] + net + '\nfinal class ProxyServersStatuses {' + proxy.split('\nfinal class ProxyServersStatuses {', 1)[1])
    outgoing_before = temp / 'before-outgoing'
    old_archive = (ROOT / 'ios/Sources/TelegramCore/NagramiXMessageArchive.swift').read_bytes()
    outgoing_plan = json.loads((ROOT / 'ios/outgoing_archive_patches.json').read_text())
    assert sha(old_archive) == outgoing_plan['hashes'][A]
    (outgoing_before / A).parent.mkdir(parents=True)
    (outgoing_before / A).write_bytes(old_archive)
    outgoing = temp / 'Outgoing.swift'
    outgoing.write_text((ROOT / 'scripts/tests/NagramiXOutgoingArchiveBoundary.swift').read_text() + '\n'
                        + outgoing_production(outgoing_before, source) + '\n'
                        + (ROOT / 'scripts/tests/NagramiXOutgoingArchiveTests.swift').read_text())
    def compile_run(label, inputs, optimized=False, failure=None):
        binary = temp / label
        command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
        if optimized: command.append('-O')
        subprocess.run([*command, *map(str, inputs), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(temp / (label + '-prefs'))),
                                capture_output=True, text=True, timeout=45,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        if failure:
            assert result.returncode != 0 and failure in result.stderr, result.stdout + result.stderr
            runs.append(label + ': исходная ошибка воспроизведена и отклонена')
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            runs.append(label + ': ' + result.stdout.strip())
            print(runs[-1], flush=True)
    for optimized in [False, True]:
        suffix = '-O' if optimized else '-debug'
        compile_run('foreground' + suffix, [boundary, source / P, controller, ROOT / 'scripts/tests/NagramiXProxyForegroundTests.swift'], optimized)
        compile_run('failover' + suffix, [boundary, source / P, controller, ROOT / 'scripts/tests/NagramiXProxyFailoverTests.swift'], optimized)
        compile_run('network-recovery' + suffix, [integrated, source / P, controller, recovery, ROOT / 'scripts/tests/NagramiXNetworkRecoveryTests.swift'], optimized)
        compile_run('media-clear' + suffix, [store], optimized)
        compile_run('outgoing' + suffix, [outgoing], optimized)
        compile_run('storage' + suffix, [source / WRITER, ROOT / 'scripts/tests/NagramiXArchiveStorageBoundary.swift', storage], optimized)
        compile_run('persistence' + suffix, [source / WRITER, ROOT / 'scripts/tests/NagramiXArchivePersistenceTests.swift'], optimized)
    old_controller = temp / 'OldController.swift'; old_controller.write_text(standalone(before[C].decode()))
    compile_run('old-foreground', [boundary, source / P, old_controller, ROOT / 'scripts/tests/NagramiXProxyForegroundTests.swift'], failure='restart must sample current state')
    old_store = temp / 'OldClear.swift'; old_store.write_text(media_boundary() + '\n' + revision + '\n' + standalone(before[M].decode()) + test_inspection() + '\n' + (ROOT / 'scripts/tests/NagramiXArchiveClearReservationTests.swift').read_text())
    compile_run('old-media-clear', [old_store], failure='clear must retain bytes reused by newer capture')
    subprocess.run([str(swiftc), '-frontend', '-parse', str(source / C), str(source / M)], check=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_media_privacy_fixes import delegate_if_applied
    if delegate_if_applied(args, __file__): return
    plan = json.loads((ROOT / 'ios/recovery_storage_fixes_patches.json').read_text())
    for name, digest in {**plan['guards'], **plan['outputs']}.items():
        assert sha((args.source / name).read_bytes()) == digest, name
    overlay = ast.parse((ROOT / 'ios/apply_overlay.py').read_text())
    calls = [node.func.id for node in ast.walk(overlay) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert calls.index('apply_round_video_refinement') < calls.index('apply_recovery_storage_fixes')
    with tempfile.TemporaryDirectory(prefix='nagramix-recovery-fixes-') as folder:
        temp = Path(folder)
        before, rejected = validate_guards(args.source, plan, temp)
        runs = execute(args.source, before, args.swiftc, temp) if args.swiftc else []
    result = dict(files=len(plan['outputs']), operations=len(plan['patches']), guards=len(plan['guards']), fail_closed=rejected,
                  runs=runs, runtime='production controller/store; реальные Foundation файлы; UIKit/MTProto/MediaBox boundaries',
                  SDK='не запускалась', device='ожидается', PiP='путь запуска не изменён; физический отказ134 не установлен')
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

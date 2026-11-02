#!/usr/bin/env python3
"""Validate login/account recovery using real final Swift bodies, no IPA build."""
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
ACCOUNT = 'submodules/TelegramCore/Sources/Account/Account.swift'
NETWORK = 'submodules/TelegramCore/Sources/Network/Network.swift'
CONTROLLER = 'submodules/TelegramCore/Sources/Network/NagramiXProxyFailoverController.swift'
RECOVERY = 'submodules/TelegramCore/Sources/Network/NagramiXNetworkRecovery.swift'
PREFERENCES = 'submodules/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def standalone(source):
    for module in ['NagramiXMediaSettings', 'SwiftSignalKit']:
        source = source.replace('import ' + module + '\n', '')
    return source


def validate(before, after, swiftc):
    a, b = manifest(before), manifest(after)
    assert set(b) - set(a) == {RECOVERY} and not set(a) - set(b)
    changed = {n for n in a if a[n] != b[n]}
    assert changed == {ACCOUNT, NETWORK, CONTROLLER}, changed
    plan = json.loads((ROOT / 'ios/login_network_recovery_patches.json').read_text())
    for name, digest in plan['hashes'].items():
        assert a[name] == digest
    # Reversing exactly the seven declared insertions must restore the full
    # native Account/Network files, including the earlier Postbox handoff.
    for name in [ACCOUNT, NETWORK]:
        text = (after / name).read_text()
        for n, old, new, count in reversed(plan['patches']):
            if n == name:
                assert text.count(new) == count
                text = text.replace(new, old, count)
        assert text == (before / name).read_text(), name
    for template, name in {**plan['provided'], **plan['copies']}.items():
        assert (after / name).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    controller_text = (after / CONTROLLER).read_text()
    controller_reverse = [
        ('    private var isCurrentNetwork: () -> Bool = { false }\n', ''),
        (', isCurrentNetwork: @escaping () -> Bool = { true }) {', ') {'),
        ('            guard isCurrentNetwork() else { return }\n            self.isCurrentNetwork = isCurrentNetwork\n', ''),
        ('        self.isCurrentNetwork = { false }\n', ''),
        ('return self.isCurrentNetwork() && self.inForeground', 'return self.inForeground'),
        ('        let isCurrentNetwork = self.isCurrentNetwork\n', ''),
        ('guard isCurrentNetwork(), !cancellation.with', 'guard !cancellation.with'),
    ]
    for new, old in controller_reverse:
        assert controller_text.count(new) == 1
        controller_text = controller_text.replace(new, old, 1)
    assert controller_text == (before / CONTROLLER).read_text(), 'Unrelated failover behavior changed'
    assert (after / PREFERENCES).read_bytes() == (ROOT / 'ios/Sources/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift').read_bytes()
    account = (after / ACCOUNT).read_text()
    assert account.count('NagramiXNetworkRecovery.attach(') == 2
    assert 'nagramiXDnsObserver' not in account and 'nagramiXProxyFailoverController.start' not in account
    assert 'allowsFailover: !supplementary' in account and 'Bundle.main.infoDictionary?["NSExtension"] == nil' in account
    assert 'Sources/**/*.swift' in (after / 'submodules/TelegramCore/BUILD').read_text()
    executions = []
    native = (after / NETWORK).read_text()
    keep = native.split('        let shouldKeepConnectionSignal = self.shouldKeepConnection.get()\n', 1)[1].split('\n\n        self.isUserOnlineDisposable', 1)[0]
    keep = '        let shouldKeepConnectionSignal = self.shouldKeepConnection.get()\n' + keep
    method = native.split('    @discardableResult\n    public func reconnectForNagramiXDnsChange', 1)[1].split('\n    }', 1)[0] + '\n    }'
    method = '    @discardableResult\n    public func reconnectForNagramiXDnsChange' + method
    spec = importlib.util.spec_from_file_location('login_recovery', ROOT / 'ios/login_network_recovery.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    negatives = 0
    with tempfile.TemporaryDirectory(prefix='nagramix-login-recovery-') as folder:
        folder = Path(folder)
        controller = folder / 'Controller.swift'; controller.write_text(standalone((after / CONTROLLER).read_text()))
        recovery = folder / 'Recovery.swift'; recovery.write_text(standalone((after / RECOVERY).read_text()))
        original_support = (ROOT / 'scripts/tests/NagramiXProxyFailoverBoundary.swift').read_text()
        network_boundary = (ROOT / 'scripts/tests/NagramiXNetworkRecoveryBoundary.swift').read_text()
        network_boundary = network_boundary.replace('        // NATIVE_KEEP_SUBSCRIPTION', keep).replace('    // NATIVE_RECONNECT_METHOD', method)
        support_text = original_support.split('final class Network {', 1)[0] + network_boundary + '\nfinal class ProxyServersStatuses {' + original_support.split('\nfinal class ProxyServersStatuses {', 1)[1]
        support_text = support_text.replace('    static func drain() {', '    static func runNext() { if !self.pending.isEmpty { self.pending.removeFirst()() } }\n    static func drain() {', 1)
        support = folder / 'Boundary.swift'; support.write_text(support_text)
        for mode in ['debug', 'optimized']:
            for label, boundary, sources, test in [
                ('recovery', support, [controller, recovery], 'NagramiXNetworkRecoveryTests.swift'),
                ('failover', ROOT / 'scripts/tests/NagramiXProxyFailoverBoundary.swift', [controller], 'NagramiXProxyFailoverTests.swift'),
            ]:
                binary = folder / (label + '-' + mode)
                command = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), str(boundary), str(after / PREFERENCES), *map(str, sources), str(ROOT / 'scripts/tests' / test), '-o', str(binary)]
                if mode == 'optimized': command.insert(1, '-O')
                subprocess.run(command, check=True)
                result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(folder / (binary.name + '-preferences'))), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
                assert result.returncode == 0, result.stdout
                executions.append(mode + ': ' + result.stdout.strip())

        # Verify that the queued-transaction assertions actually require the
        # new synchronous admission barrier, rather than merely async stop().
        unguarded = folder / 'WithoutAdmission.swift'
        unguarded.write_text(controller.read_text().replace('guard isCurrentNetwork(), !cancellation.with', 'guard !cancellation.with', 1))
        binary = folder / 'without-admission'
        subprocess.run([str(swiftc), '-O', '-module-cache-path', str(folder / 'cache'), str(support), str(after / PREFERENCES), str(unguarded), str(recovery), str(ROOT / 'scripts/tests/NagramiXNetworkRecoveryTests.swift'), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], env=dict(os.environ, XDG_CONFIG_HOME=str(folder / 'without-admission-preferences')), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
        assert result.returncode == 1 and 'replaced login network cannot commit before async stop' in result.stdout, result.stdout
        executions.append('optimized: removing transaction admission reproduces obsolete-owner writes')

        def fixture(case_plan):
            source = folder / 'source'; overlay = folder / 'overlay'
            source.mkdir(exist_ok=True); overlay.mkdir(exist_ok=True)
            for name in set(plan['hashes']) | set(plan['provided'].values()):
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((before / name).read_bytes())
            for template, name in plan['provided'].items():
                (source / name).write_bytes((ROOT / 'ios' / template).read_bytes())
            for template, name in plan['copies'].items():
                path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.unlink(missing_ok=True)
            for template in set(plan['provided']) | set(plan['copies']):
                path = overlay / template; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / 'ios' / template).read_bytes())
            (overlay / 'login_network_recovery_patches.json').write_text(json.dumps(case_plan))
            return source, overlay

        # Positive replay is byte-for-byte the full generated final output.
        source, overlay = fixture(plan)
        module.apply_login_network_recovery(source, overlay)
        for name in set(plan['hashes']) | {RECOVERY, CONTROLLER}:
            assert (source / name).read_bytes() == (after / name).read_bytes()

        def rejected(source, overlay):
            nonlocal negatives
            snapshot = manifest(source)
            try:
                module.apply_login_network_recovery(source, overlay)
            except (SystemExit, FileNotFoundError):
                assert manifest(source) == snapshot, 'Partial writes on failed overlay'
                negatives += 1
            else: raise AssertionError('Drift accepted')

        rejected(source, overlay)  # repeat application must fail before writes
        for name in plan['hashes']:
            source, overlay = fixture(plan)
            path = source / name; path.write_bytes(path.read_bytes() + b'\n// drift\n')
            rejected(source, overlay)
        for n, old, _, _ in plan['patches']:
            case_plan = copy.deepcopy(plan); source, overlay = fixture(case_plan)
            path = source / n; path.write_text(path.read_text().replace(old, '// moved anchor\n', 1))
            case_plan['hashes'][n] = hashlib.sha256(path.read_bytes()).hexdigest()
            (overlay / 'login_network_recovery_patches.json').write_text(json.dumps(case_plan))
            rejected(source, overlay)
        source, overlay = fixture(plan); (source / RECOVERY).write_text('collision'); rejected(source, overlay)
        source, overlay = fixture(plan); (source / CONTROLLER).write_text('drift'); rejected(source, overlay)
        source, overlay = fixture(plan); (overlay / next(iter(plan['copies']))).unlink(); rejected(source, overlay)
        for name in [ACCOUNT, NETWORK, CONTROLLER, RECOVERY]:
            subprocess.run([str(swiftc), '-frontend', '-parse', str(after / name)], check=True)
    ast.parse((ROOT / 'ios/login_network_recovery.py').read_text())
    ast.parse(Path(__file__).read_text())
    return {'outputs': len(b), 'changed': sorted(changed), 'added': [RECOVERY], 'unchanged': len(a) - len(changed), 'exact_reverse': 'PASS', 'overlay_replay': 'PASS', 'fail_closed_cases_without_writes': negatives, 'runtime': executions, 'Apple_SDK': 'not run', 'physical_iPhone': 'pending', 'IPA': 'not started'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

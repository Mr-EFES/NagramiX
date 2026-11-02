#!/usr/bin/env python3
"""Run the actual proxy failover controller without an iOS/IPA build.

Queue, time, transaction and network boundaries are deterministic doubles.
The controller and preference implementation execute unchanged apart from
module imports; native socket behaviour still needs Apple SDK/device tests.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = 'submodules/TelegramCore/Sources/Network/NagramiXProxyFailoverController.swift'
PREFERENCES = 'submodules/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def standalone(source):
    for module in ['NagramiXMediaSettings', 'SwiftSignalKit']:
        line = 'import ' + module + '\n'
        assert source.count(line) == 1
        source = source.replace(line, '', 1)
    return source


def validate(before, after, swiftc):
    a, b = manifest(before), manifest(after)
    assert a.keys() == b.keys(), 'Unexpected generated file addition/removal'
    assert {n for n in a if a[n] != b[n]} == {CONTROLLER}, 'Unexpected integration change'
    assert (after / CONTROLLER).read_bytes() == (ROOT / 'ios/Sources/TelegramCore/NagramiXProxyFailoverController.swift').read_bytes()
    assert (after / PREFERENCES).read_bytes() == (ROOT / 'ios/Sources/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift').read_bytes()
    # The exact requested fix: remove only the obsolete ping snapshot and make
    # native ONLINE authoritative. Everything outside those boundaries is kept.
    original = (before / CONTROLLER).read_text()
    restored = (after / CONTROLLER).read_text()
    new_online = restored.split('        case .online:\n', 1)[1].split('        case .waitingForNetwork:', 1)[0]
    old_online = original.split('        case let .online(proxyAddress):\n', 1)[1].split('        case .waitingForNetwork:', 1)[0]
    restored = restored.replace('        case .online:\n' + new_online, '        case let .online(proxyAddress):\n' + old_online, 1)
    restored = restored.replace('    private var settings: ProxySettings', '    private var healthStatuses: [ProxyServerSettings: ProxyServerStatus] = [:]\n    private var settings: ProxySettings', 1)
    restored = restored.replace('monitor.statuses() |> deliverOn(self.queue)).start(next: { [weak self] _ in\n                guard let self else { return }\n', 'monitor.statuses() |> deliverOn(self.queue)).start(next: { [weak self] statuses in\n                guard let self else { return }\n                self.healthStatuses = statuses\n', 1)
    restored = restored.replace('        self.network = nil\n    }', '        self.network = nil\n        self.healthStatuses.removeAll()\n    }', 1)
    assert restored == original, 'Unrelated failover logic changed'
    executions = []
    with tempfile.TemporaryDirectory(prefix='nagramix-proxy-failover-') as folder:
        folder = Path(folder)
        current, old = folder / 'Controller.swift', folder / 'Original.swift'
        current.write_text(standalone((after / CONTROLLER).read_text()))
        old.write_text(standalone(original))
        support = [ROOT / 'scripts/tests/NagramiXProxyFailoverBoundary.swift', after / PREFERENCES]
        tests = ROOT / 'scripts/tests/NagramiXProxyFailoverTests.swift'

        def compile_and_run(source, mode, regression=False):
            binary = folder / (source.stem + '-' + mode)
            args = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *map(str, support), str(source), str(tests), '-o', str(binary)]
            if mode == 'optimized': args.insert(1, '-O')
            subprocess.run(args, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(folder / (binary.name + '-preferences')))
            return subprocess.run([str(binary), *(['--regression-only'] if regression else [])], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)

        for mode in ['debug', 'optimized']:
            failed = compile_and_run(old, mode, regression=True)
            assert failed.returncode == 1 and 'failed independent ping must not switch a live connection' in failed.stdout, 'Original bug was not reproduced'
            executions.append(mode + ': original regression reproduced')
            result = compile_and_run(current, mode)
            assert result.returncode == 0, result.stdout
            executions.append(mode + ': ' + result.stdout.strip())
        subprocess.run([str(swiftc), '-frontend', '-parse', str(after / CONTROLLER)], check=True)
    ast.parse((ROOT / 'scripts/validate_proxy_failover.py').read_text())
    return {'outputs': len(b), 'changed': [CONTROLLER], 'unchanged': len(b) - 1, 'exact_reverse': 'PASS', 'execution': executions, 'Apple_SDK': 'not run', 'physical_iPhone': 'pending', 'IPA': 'not started'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

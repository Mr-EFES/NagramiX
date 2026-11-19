#!/usr/bin/env python3
"""Check the production iOS hooks and run the actual Worker client against a local transport."""
import argparse
from pathlib import Path
import platform
import subprocess
import tempfile


def validate(source: Path, swiftc: Path) -> None:
    sources = source / 'submodules/TelegramUI/Sources'
    delegate = (sources / 'AppDelegate.swift').read_text()
    helper = sources / 'NagramiXInstallationMetrics.swift'
    assert delegate.count('NagramiXInstallationMetrics()') == 1
    assert 'self.installationLoginDisposable.set((sharedContext.activeAccountContexts\n            |> filter { !$0.accounts.isEmpty }' in delegate
    assert 'Task { await metrics.observe(isAuthorized: true) }' in delegate
    foreground = delegate.split('func runForegroundTasks() {', 1)[1].split('func handleDidBecomeActive()', 1)[0]
    assert 'await metrics.observe(isAuthorized: false)' in foreground
    assert 'self.runForegroundTasks()' in delegate.split('func handleWillEnterForeground()', 1)[1].split('func runForegroundTasks()', 1)[0]
    assert 'https://nagramix-bot.mr-efes.workers.dev/v1/installation' in helper.read_text()
    tests = Path(__file__).resolve().parents[1] / 'ios/Tests/NagramiXInstallationMetricsTests.swift'
    with tempfile.TemporaryDirectory(prefix='nagramix-metrics-') as directory:
        binary = Path(directory) / 'check'
        host_target = []
        if platform.system() == 'Darwin':
            sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
            subprocess.run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-typecheck', '-parse-as-library',
                            '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-module-cache-path',
                            Path(directory) / 'ios-cache', helper], check=True, timeout=120)
            host_target = ['-target', platform.machine() + '-apple-macosx13.0']
        for flags in ([], ['-O']):
            subprocess.run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', *host_target, *flags,
                            '-module-cache-path', Path(directory) / 'cache', helper, tests, '-o', binary], check=True, timeout=120)
            subprocess.run([binary], check=True, timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    validate(args.source, args.swiftc)

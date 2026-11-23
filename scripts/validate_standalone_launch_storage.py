#!/usr/bin/env python3
"""Exercise the startup container and passcode policy without building an IPA."""
import argparse
from pathlib import Path
import tempfile

from validate_private_temporary_transcription import execute
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', default='swiftc')
    args = parser.parse_args()
    plan = checked_plan('standalone_launch_storage')
    if args.source:
        for path, expected in {**plan['outputs'], **plan['guards']}.items():
            assert digest(args.source / path) == expected, path

    def output(path):
        file = args.source / path if args.source else OVERLAY / plan['replacements'][path]
        return file.read_text()

    app = output('submodules/TelegramUI/Sources/AppDelegate.swift')
    passcode = output('submodules/PasscodeCore/Sources/Passcode.swift')
    wallet = output('submodules/WalletContext/Sources/WalletSecurity.swift')
    items = output('submodules/WalletContext/Sources/WalletStorage.swift')
    accounts = ((args.source / 'submodules/TelegramCore/Sources/Account/AccountManager.swift') if args.source
                else OVERLAY / 'release_090_preflight_fixes/Guard12.inc').read_text()
    storage = app[app.index('private struct NagramiXLaunchStorage'):app.index('@objc(AppDelegate)')]
    root = accounts[accounts.index('public func rootPathForBasePath'):accounts.index('public func performAppGroupUpgrades')]
    environment = passcode[passcode.index('public struct PasscodeConfiguration'):passcode.index('protocol PasscodeStorage')]
    assert 'appOnlyStorage: storage.sharedGroup == nil' in app
    assert 'configuration.sharedContainerIdentifier = self.launchStorage?.sharedGroup' in app
    assert 'appGroupUrl = storage.baseURL' in app
    assert 'NagramiXStandaloneStorage' in app and 'standalone: standalone' in app
    assert app.index('self.launchStorage = storage') < app.index('BuildConfig.deviceSpecificEncryptionParameters(rootPath')
    assert 'try account.hasPrefix("biometric.") ? self.environment.privateAccessGroup() : self.environment.sharedAccessGroup()' in passcode
    assert 'return self.environment.storageKeychainService(service)' in passcode
    assert 'return environment.storageKeychainService(self.unscopedServicePrefix)' in wallet
    assert 'return PasscodeEnvironment.shared.storageKeychainService(service)' in items
    fixture = Path(__file__).with_name('tests') / 'NagramiXStandaloneLaunchStorage.swift'
    program = 'import Foundation\nenum PasscodeError: Error { case unavailable }\n'
    with tempfile.TemporaryDirectory() as temporary:
        execute(args.swiftc, Path(temporary), 'StandaloneLaunchStorage', program + root + storage + environment + fixture.read_text())
    print('Standalone launch storage and passcode checks passed (debug and optimized)')


if __name__ == '__main__':
    main()

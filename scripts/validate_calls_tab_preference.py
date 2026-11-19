#!/usr/bin/env python3
"""Exercise shared Calls visibility against the production settings, routing and tab layout."""
import argparse
from pathlib import Path
import tempfile

import tab_visibility_runtime as tab
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan

STAGE = 'calls_tab_preference'
PREF = 'submodules/TelegramUIPreferences/Sources/CallListSettings.swift'


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for name in plan['inputs']:
        run([swiftc, '-frontend', '-parse', source / name], timeout=60)

    delegate = (source / 'submodules/TelegramUI/Sources/AppDelegate.swift').read_text()
    assert 'current.migratingCallsTabVisibility(legacyHidden: NagramiXTabSettings.storedHideCalls)' in delegate
    assert 'transaction.updateSharedData(key, { _ in SharedPreferencesEntry(migrated) })' in delegate
    assert delegate.index('return migrated') < delegate.index('showCallsTab: callListSettings.showTab')
    context = (source / 'submodules/TelegramUI/Sources/ApplicationContext.swift').read_text()
    assert 'self.showCallsTab = showCallsTab\n        NagramiXTabSettings.reflectCallsTabVisibility(showCallsTab)' in context
    assert 'strongSelf.showCallsTab = value\n                    NagramiXTabSettings.reflectCallsTabVisibility(value)' in context
    assert 'sharedData.entries[ApplicationSpecificSharedDataKeys.callListSettings]?.get(CallListSettings.self)' in context
    assert 'return SharedPreferencesEntry(f(currentSettings))' in (source / PREF).read_text()

    tests = tab.ROOT / 'ios/Tests'
    code = tab.fixture(source, adds_contact=True).split('@main private enum TabVisibilityTests', 1)[0]
    # Contacts navigation has a separate host in the later header stage.
    code = code.replace(block(code, 'func contactsBackAction('), '', 1)
    code += block((tests / 'TranslationDefaultsTests.swift').read_text(), 'struct StringCodingKey:')
    code += '\n' + block((source / PREF).read_text(), 'public struct CallListSettings:')
    # Exercise the actual transforms from all three entry points with the same preference.
    paths = [
        ('settingChange', ', hidden: Bool', 'updateHideCalls: { hidden in', tab.SETTINGS),
        ('hideFromMenu', '', 'text: self.presentationData.strings.Calls_HideCallsTab',
         'submodules/CallListUI/Sources/CallListController.swift'),
        ('nativeSwitchChange', ', visible value: Bool', '}, updateShowCallsTab: { [weak self] value in',
         'submodules/CallListUI/Sources/CallListControllerNode.swift'),
    ]
    for function, parameters, anchor, path in paths:
        section = (source / path).read_text().split(anchor, 1)[1]
        update = section.split('updateCallListSettingsInteractively(accountManager:', 1)[1]
        assert 'sharedContext.accountManager' in update.split(', {', 1)[0]
        transform = update.split(', {', 1)[1].split('}).start', 1)[0].strip()
        code += (f'\nprivate func {function}(_ preference: CallListSettings{parameters}) -> CallListSettings {{\n'
                 f'    let change: (CallListSettings) -> CallListSettings = {{ {transform} }}\n'
                 '    return change(preference)\n}\n')
    fixture = folder / 'Calls.swift'
    fixture.write_text(code + '\n' + (tests / 'NagramiXCallsTabPreference.swift').read_text())
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        link, env = tab.modules(source, swiftc, folder / mode, flags)
        binary = folder / ('calls-' + mode)
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
             '-module-cache-path', folder / mode / 'cache', *flags, *link, fixture, '-o', binary], timeout=180)
        print(run([binary], env=env, timeout=30).stdout.strip(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='calls-tab-preference-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))

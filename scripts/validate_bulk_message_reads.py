#!/usr/bin/env python3
"""Exercise account-local and explicitly confirmed read boundaries without an IPA build."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import OVERLAY
from validate_app_language_localization import strings
from validate_upstream_13_2_release_string_compile import real_extensions
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_settings_argument_bindings import SETTINGS, validate as validate_bindings
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'bulk_message_reads'
CORE = 'submodules/TelegramCore/Sources/'
TESTS = OVERLAY.parent / 'scripts/tests'


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    if source is None:
        source = work / 'source'
        for name, template in {**plan['replacements'], **plan['guard_sources']}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / template).read_bytes())
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    guard_checks(source, STAGE, plan, work / 'guards')
    run([swiftc, '-frontend', '-parse', *(source / n for n in plan['outputs'] if n.endswith('.swift'))])
    ui = (source / SETTINGS).read_text()
    assert '        .clearMessageArchive,\n        .readAllLocally,\n        .readAllOnServer,' in ui
    assert ui.count('actionLayout: .vertical') >= 2
    assert 'runBulkRead(remaining.send())' in ui
    validate_bindings(ui, swiftc, work)
    alert_test = (TESTS / 'NagramiXBulkReadAlerts.swift').read_text()
    run_bulk = block(ui, '    func runBulkRead(')
    show_bulk = block(ui, '        readAllMessages: { onServer in').split(': ', 1)[1]
    callbacks = 'var bulkReadInFlight = false\n' + run_bulk + '\nlet show: (Bool) -> Void = ' + show_bulk
    catalog = strings(source / 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings')
    labels = {key: value for key, value in catalog.items() if key.startswith('NagramiX.BulkRead.') or key == 'NagramiX.Archive.Storage.Retry'}
    dictionary = 'let catalog = [' + ', '.join(json.dumps(k, ensure_ascii=False) + ': ' + json.dumps(v, ensure_ascii=False) for k, v in labels.items()) + ']\n'
    probe = real_extensions(source) + '\n' + dictionary + alert_test.replace('// PRODUCTION_CALLBACKS', callbacks)
    for result in execute(swiftc, work, 'bulk-alerts', probe):
        print(result['mode'], result['output'])
    postbox = (source / 'submodules/Postbox/Sources/Postbox.swift').read_text()
    local = block(postbox, '    fileprivate func setLocalReadState(')
    assert 'resetStates' in local and 'UpdateReadState' in local and 'synchronize' not in local
    push = (source / (CORE + 'State/SynchronizePeerReadState.swift')).read_text()
    assert 'nagramiXNativePushState(transaction:' in push and 'readState: readState)' in push

    def standalone(path):
        return '\n'.join(line for line in path.read_text().splitlines()
                         if not line.startswith(('import ', 'internal import ')) or line == 'import Foundation')
    models = OVERLAY / 'Sources/NagramiXMediaSettings/Sources'
    parts = [(TESTS / 'NagramiXReadModeActionTests.swift').read_text().split('@main struct ReadModeActionTests')[0]]
    parts += [standalone(models / ('NagramiX' + name + 'Settings.swift')) for name in ('ReadMode', 'Privacy', 'Ghost', 'Story')]
    parts += [standalone(source / (CORE + name + '.swift')) for name in ('NagramiXGhostReadActions', 'NagramiXReadModeActions')]
    parts.append((TESTS / 'NagramiXBulkReadTests.swift').read_text())
    for result in execute(swiftc, work, 'bulk-reads', '\n'.join(parts)):
        print(result['mode'], result['output'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-bulk-reads-') as directory:
        validate(args.source, args.swiftc, Path(directory))

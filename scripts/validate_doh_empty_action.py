#!/usr/bin/env python3
"""Проверить динамические Отменить/Удалить без изменения сохранённого DNS при отмене."""
import argparse
import json
from pathlib import Path
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_quick_format import block, manifest
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_app_language_localization import strings
import doh_empty_action_runtime as runtime

STAGE = 'doh_empty_action'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'wide_portal_api'
    assert set(plan['inputs']) == {runtime.EDITOR} and len(plan['guards']) == 23
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = (OVERLAY / plan['previous'][runtime.EDITOR]).read_text()
    after = (args.source / runtime.EDITOR).read_text()
    for marker in ['private func validatedNagramiXDohUrl(', 'private final class NagramiXCustomDohSubmission {']:
        assert block(before, marker) == block(after, marker)
    assert before.split('    applyImpl =', 1)[1] == after.split('    applyImpl =', 1)[1], 'Endpoint validation/save/disposal must remain exact'
    catalogs = list((args.source / 'submodules/NagramiXCore/Resources').glob('*.lproj/Localizable.strings'))
    assert len(catalogs) == 71
    assert runtime.native_value(args.source, 'WebApp.Download.Cancel') == 'Отменить'
    assert all('NagramiX.Network.DNS.CustomInvalid' in strings(p) for p in catalogs)
    state = manifest(args.source)
    code = runtime.fixture(args.source)
    with tempfile.TemporaryDirectory(prefix='doh-empty-action-') as temporary:
        folder = Path(temporary)
        refused = guard_checks(args.source, STAGE, plan, folder / 'guards')
        runs = execute(args.swiftc, folder, STAGE, code)
        current = '\n'.join(line for line in after.splitlines() if not line.startswith('import '))
        original = '\n'.join(line for line in before.splitlines() if not line.startswith('import '))
        assert code.count(current) == 1
        runs += execute(args.swiftc, folder, 'original74-always-delete', code.replace(current, original, 1), 'empty field displays Cancel and Save')
        old = '        if !inputState.value.isEmpty {\n            clear()\n        }'
        assert code.count(old) == 1
        runs += execute(args.swiftc, folder, 'cancel-deletes-saved-dns', code.replace(old, '        clear()', 1), 'Cancel preserves saved DNS even through stale Delete closure')
        run([args.swiftc, '-frontend', '-parse', args.source / runtime.EDITOR])
    assert manifest(args.source) == state
    report = {
        'stage': STAGE, 'runtime_paths': [runtime.EDITOR], 'guards': len(plan['guards']),
        'loader_refusals': len(refused), 'executions': runs,
        'localizations': '71 existing catalogs unchanged; localized native cancel verb reused; no new keys',
        'source_unchanged_by_checks': True,
        'boundary': 'Whole actual controller, URL validator, submission state, actual PresentationStrings getters, native Action/Configuration/initializer signature, input ExternalState and real SwiftSignalKit execute. Alert rendering, text field mounting and resolver transport are explicit adapters. UIKit pixels, live DoH and physical iPhone are not verified.',
        'full_application_sdk': 'pending', 'physical_iphone': 'pending', 'new_actions_or_ipa_started': False,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

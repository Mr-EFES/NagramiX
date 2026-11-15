#!/usr/bin/env python3
"""Проверить очистку DoH без повторного входа в обновляющийся ComponentView."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import manifest, block
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_private_temporary_transcription import execute, save_failed_fixture
import doh_clear_input_lifecycle_runtime as runtime

STAGE = 'doh_clear_input_lifecycle'


def regressions(source, swiftc, folder):
    """Keep positive runs before the exact original219 and partial-fix negatives."""
    folder.mkdir(parents=True, exist_ok=True)
    code = runtime.fixture(source)
    runs = execute(swiftc, folder, 'native-doh-clear', code)
    plan = checked_plan(STAGE)
    current = '\n'.join(l for l in (source / runtime.EDITOR).read_text().splitlines() if not l.startswith('import '))
    previous = '\n'.join(l for l in (OVERLAY / plan['previous'][runtime.EDITOR]).read_text().splitlines() if not l.startswith('import '))
    assert code.count(current) == 1
    variants = [
        ('original219-synchronous-input', code.replace(current, previous, 1)),
        ('only-actions-deferred', code.replace('    let doneIsEnabled = inputValues', '    let doneIsEnabled = inputState.valueSignal', 1)),
        ('only-save-deferred', code.replace('let actionsSignal: Signal<[AlertScreen.Action], NoError> = inputValues', 'let actionsSignal: Signal<[AlertScreen.Action], NoError> = inputState.valueSignal', 1)),
    ]
    for name, text in variants:
        assert text != code and text.count('precondition(!self.isUpdating)') == 1
        # Observation only. The actual native precondition remains and traps;
        # no OS-specific backtrace/diagnostic wording is used as the oracle.
        text = text.replace('precondition(!self.isUpdating)', 'if self.isUpdating { print("NATIVE_REENTRY_219"); fflush(stdout) }\n        precondition(!self.isUpdating)', 1)
        assert text.count('self.setText(text: "")') == 1
        text = text.replace('self.setText(text: "")', 'print("CLEAR_X_219"); fflush(stdout)\n                            self.setText(text: "")', 1)
        path = folder / (name + '.swift')
        path.write_text(text)
        for mode, flags in [('debug', []), ('optimized', ['-O'])]:
            binary = folder / (name + '-' + mode)
            result = subprocess.run([str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-module-cache-path', str(folder / 'cache'), *flags, str(path), '-o', str(binary)], capture_output=True, text=True, timeout=180)
            if result.returncode:
                save_failed_fixture(path, name, mode, 'compile', result)
            assert result.returncode == 0, result.stdout + result.stderr
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            expected = result.returncode in (-4, -5) and result.stdout.strip() == 'CLEAR_X_219\nNATIVE_REENTRY_219'
            if not expected:
                save_failed_fixture(path, name, mode, 'expected-native-reentry-trap', result)
            assert expected, (name, mode, result.returncode, result.stdout, result.stderr)
            runs.append({'name': name, 'mode': mode, 'original219_reentry_rejected': True, 'native_precondition_signal': -result.returncode, 'observation': result.stdout.strip()})
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'release_098_compile_compatibility'
    assert set(plan['inputs']) == {runtime.EDITOR} and len(plan['guards']) == 14
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = (OVERLAY / plan['previous'][runtime.EDITOR]).read_text()
    after = (args.source / runtime.EDITOR).read_text()
    a = before.index('    let doneIsEnabled = ')
    b = before.index('    let progress = ', a)
    x = after.index('    // Input publishes while ')
    y = after.index('    let progress = ', x)
    assert before[:a] == after[:x]
    assert before[b:].replace('let actionsSignal: Signal<[AlertScreen.Action], NoError> = inputState.valueSignal', 'let actionsSignal: Signal<[AlertScreen.Action], NoError> = inputValues', 1) == after[y:]
    for marker in ['private func validatedNagramiXDohUrl(', 'private final class NagramiXCustomDohSubmission {']:
        assert block(before, marker) == block(after, marker)
    assert before.split('    removeImpl =', 1)[1] == after.split('    removeImpl =', 1)[1], 'Delete/Cancel/Save/resolver/disposal must stay exact'
    state = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-doh-clear-') as d:
        folder = Path(d)
        refused = guard_checks(args.source, STAGE, plan, folder / 'guards')
        runs = regressions(args.source, args.swiftc, folder / 'runtime')
        result = subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / runtime.EDITOR)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    assert manifest(args.source) == state
    report = {
        'stage': 93, 'name': STAGE, 'runtime_paths': [runtime.EDITOR], 'guards': 14,
        'loader_refusals': len(refused), 'executions': runs,
        'source_unchanged_by_checks': True,
        'boundary': 'Whole actual DoH controller; native ComponentView._update including its precondition; ComponentState, input clear closure/setText/publication, Alert/Save callbacks and real SwiftSignalKit/Queue/combineLatest. UIKit painting and component erasure/context storage/transport are recording adapters. Both consumers must defer; all three original/partial fixes must trap in the unchanged native precondition after an observed reentry, debug and -O.',
        'unchanged': 'Delete/Cancel/Save/validation/resolver/disposal, all shared UI components, settings, resources, keys, dependencies and signing',
        'full_application_sdk': 'not_run', 'physical_iphone': 'pending', 'new_actions_or_ipa_started': False,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

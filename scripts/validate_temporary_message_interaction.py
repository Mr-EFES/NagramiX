#!/usr/bin/env python3
"""Проверить целостную девятую правку без SDK, сети и реального приложения."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'temporary_message_interaction'
COMPONENTS = (
    'consumption', 'archive', 'asr', 'reply', 'delete', 'repost',
    'send', 'engine_opening', 'forward_source',
)


def source_contract(source, baseline):
    plan = checked_plan(STAGE)
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == value, name
    for name, value in plan['inputs'].items():
        assert digest(baseline / name) == value, 'Wrong pre-task checkpoint: ' + name
    for name, value in plan['guards'].items():
        assert digest(baseline / name) == value, name
    for name, item in plan['copies'].items():
        assert not (baseline / name).exists(), 'Helper already exists in baseline'
        assert digest(source / name) == item['sha256'], name
    before, after = manifest(baseline), manifest(source)
    assert len(before) > 37000, 'A source projection is not a full checkpoint'
    assert before.keys() - after.keys() == set(), 'Unexpected application deletion'
    assert after.keys() - before.keys() == set(plan['copies']), 'Unexpected application additions'
    changed = {name for name in before if before[name] != after[name]}
    assert changed == set(plan['outputs']), 'Previous eight fixes changed outside the reviewed scope'
    # The earlier eight stages must be present, not merely the wide-setting key.
    from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
    assert LATE_SOURCE_STAGES[-1] == STAGE
    assert verified_prefix(baseline) == len(LATE_SOURCE_STAGES) - 1
    assert verified_prefix(source) == len(LATE_SOURCE_STAGES)
    return plan, {
        'baseline_files': len(before), 'final_files': len(after),
        'changed_files': sorted(changed), 'added_files': sorted(plan['copies']),
        'previous_files_preserved': len(before) - len(changed),
    }


def run_component(component, source, baseline, swiftc, directory):
    script = ROOT / 'scripts' / ('validate_temporary_interaction_' + component + '.py')
    assert script.is_file(), 'Missing component validator: ' + str(script)
    report = directory / (component + '.json')
    log = directory / (component + '.log')
    args = [sys.executable, str(script), '--source', str(source), '--swiftc', str(swiftc), '--report', str(report)]
    if re.search(r'add_argument\(\s*[\'"]--baseline[\'"]', script.read_text()):
        args += ['--baseline', str(baseline)]
    with log.open('w') as output:
        result = subprocess.run(args, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    assert result.returncode == 0, component + ':\n' + log.read_text()[-12000:]
    assert report.is_file(), 'Validator returned without evidence: ' + component
    return {'component': component, 'exit_code': result.returncode,
            'evidence': json.loads(report.read_text()), 'log': str(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    assert 1 <= args.jobs <= 2, 'Bound compiler concurrency to two independent suites'
    plan, tree = source_contract(args.source, args.baseline)
    subprocess.run([sys.executable, str(args.source / 'build-system/Make/PostboxImportCheck.py'), str(args.source)], check=True)
    with tempfile.TemporaryDirectory(prefix='temporary-message-interaction-') as temporary:
        directory = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, directory / 'stage')
        logs = directory / 'components'
        if args.report:
            logs = args.report.parent / (args.report.stem + '-components')
        logs.mkdir(parents=True, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            pending = {pool.submit(run_component, component, args.source, args.baseline, args.swiftc, logs): component for component in COMPONENTS}
            results = []
            errors = []
            for future in concurrent.futures.as_completed(pending):
                try:
                    result = future.result()
                except Exception as error:
                    errors.append(str(error))
                    print('FAIL temporary interaction:', pending[future], str(error), flush=True)
                    continue
                results.append(result)
                print('PASS temporary interaction:', result['component'], flush=True)
            assert not errors, '\n'.join(errors)
        for name in plan['outputs']:
            if name.endswith('.swift'):
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
        for name in plan['copies']:
            if name.endswith('.swift'):
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    # Verify no test or asynchronous fixture changed the checked application.
    _, after = source_contract(args.source, args.baseline)
    assert after == tree
    report = {
        'stage': STAGE, 'source_outputs': plan['outputs'], 'copies': plan['copies'],
        'guards': len(plan['guards']), 'fail_closed': len(rejected),
        'full_source': tree, 'components': sorted(results, key=lambda item: item['component']),
        'swift_parse': len(plan['outputs']) + len(plan['copies']),
        'native_postbox_imports': 'passed',
        'boundaries': 'Production bodies execute in explicit adapters; UIKit/AVKit, cryptography delivery, Postbox storage, external services and physical playback are not a live application test.',
        'apple_sdk': 'not_run', 'ipa': 'not_built', 'device': 'pending',
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('components', 'source_outputs', 'copies')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

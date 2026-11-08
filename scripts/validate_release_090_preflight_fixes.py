#!/usr/bin/env python3
"""Check the two confirmed preflight corrections without an app/SDK build."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'release_090_preflight_fixes'
FILES = {
    'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift',
    'submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift',
}


def source_contract(source, baseline):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == set(plan['outputs']) == FILES
    assert not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
    for name, value in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == value, name
    for name, value in {**plan['inputs'], **plan['guards']}.items():
        assert digest(baseline / name) == value, name
    before, after = manifest(baseline), manifest(source)
    assert len(before) > 37000 and before.keys() == after.keys()
    changed = {name for name in before if before[name] != after[name]}
    assert changed == FILES, changed
    prefix = LATE_SOURCE_STAGES.index(STAGE)
    assert prefix == 10 and LATE_SOURCE_STAGES[prefix - 1] == 'account_settings_entry'
    assert verified_prefix(baseline) == prefix
    assert verified_prefix(source) == prefix + 1
    return plan, {'baseline_files': len(before), 'final_files': len(after),
                  'changed_files': sorted(changed), 'previous_files_preserved': len(before) - len(changed),
                  'baseline_prefix': prefix, 'final_prefix': prefix + 1}


def component(name, source, baseline, swiftc, directory):
    report = directory / (name + '.json')
    log = directory / (name + '.log')
    command = [sys.executable, str(ROOT / 'scripts' / ('validate_preflight_' + name + '.py')),
               '--source', str(source), '--swiftc', str(swiftc), '--report', str(report)]
    if name == 'forward_groups':
        command += ['--baseline', str(baseline)]
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    assert result.returncode == 0, name + ':\n' + log.read_text()[-10000:]
    assert report.is_file(), name
    return {'name': name, 'exit_code': result.returncode, 'evidence': json.loads(report.read_text())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan, tree = source_contract(args.source, args.baseline)
    subprocess.run([sys.executable, str(args.source / 'build-system/Make/PostboxImportCheck.py'), str(args.source)], check=True)
    with tempfile.TemporaryDirectory(prefix='release-090-preflight-') as temporary:
        directory = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, directory / 'guards')
        logs = directory / 'components'
        if args.report:
            logs = args.report.parent / (args.report.stem + '-components')
        logs.mkdir(parents=True, exist_ok=True)
        results, errors = [], []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(component, name, args.source, args.baseline, args.swiftc, logs): name
                       for name in ('forward_groups', 'archive_media')}
            for future in concurrent.futures.as_completed(pending):
                try:
                    results.append(future.result())
                    print('PASS preflight fix:', pending[future], flush=True)
                except Exception as error:
                    errors.append(str(error))
                    print('FAIL preflight fix:', pending[future], str(error), flush=True)
        assert not errors, '\n'.join(errors)
        for name in sorted(FILES):
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    _, after = source_contract(args.source, args.baseline)
    assert after == tree
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'full_source': tree, 'components': sorted(results, key=lambda item: item['name']),
              'fail_closed': len(rejected), 'swift_parse': len(FILES), 'native_postbox_imports': 'passed',
              'boundary': 'Production bodies execute in bounded adapters. Native API declarations, exact source preservation and historical prefixes are checked. No UIKit, live Postbox, delivery or Apple SDK execution.',
              'apple_sdk': 'not_run', 'ipa': 'not_built', 'physical_iphone': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'components'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

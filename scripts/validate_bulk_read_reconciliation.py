#!/usr/bin/env python3
"""Reproduce the three bulk read regressions and exercise their fixes with real Swift bodies."""
import argparse
from pathlib import Path
import tempfile

from validate_bulk_message_reads import CORE, OVERLAY, TESTS
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'bulk_read_reconciliation'
MEMBERSHIP = CORE + 'State/NonMemberChannelReadState.swift'
SYNC = CORE + 'State/SynchronizePeerReadState.swift'
ACTIONS = [CORE + name + '.swift' for name in ('NagramiXGhostReadActions', 'NagramiXReadModeActions')]


def standalone(path):
    return '\n'.join(line for line in path.read_text().splitlines()
                     if not line.startswith(('import ', 'internal import ')))


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
    run([swiftc, '-frontend', '-parse', *(source / name for name in plan['outputs'])])
    members = (source / MEMBERSHIP).read_text()
    models = OVERLAY / 'Sources/NagramiXMediaSettings/Sources'
    common = [(TESTS / 'NagramiXReadModeActionTests.swift').read_text().split('@main struct ReadModeActionTests')[0],
              (TESTS / 'NagramiXBulkReadTests.swift').read_text().replace('@main struct BulkReadTests', 'struct BulkReadTests'),
              block(members, 'func peerKeepsReadState('),
              next(line for line in members.splitlines() if line.startswith('let nonMemberChannelReadState:'))]
    common += [standalone(models / ('NagramiX' + name + 'Settings.swift')) for name in ('ReadMode', 'Privacy', 'Ghost', 'Story')]
    # Preserve TelegramCore's file boundaries so an accidental private declaration fails early.
    boundary = work / 'Boundary.swift'
    boundary.write_text('\n'.join(common))
    files = [boundary]
    for name in ACTIONS:
        path = work / Path(name).name
        path.write_text('import Foundation\n' + standalone(source / name))
        files.append(path)
    run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-typecheck',
         '-module-cache-path', work / 'cache', *files])
    sync = (source / SYNC).read_text()
    assert 'markedUnread: nagramiXLocalUnreadMark(transaction:' in sync
    tests = (TESTS / 'NagramiXBulkReadReconciliationTests.swift').read_text()
    for label in ('before', 'after'):
        current = label == 'after'
        parts = common + [standalone(source / name if current else OVERLAY / plan['previous'][name]) for name in ACTIONS]
        parts += ['let repaired = ' + str(current).lower(), tests]
        if current:
            sender = block(sync, '            guard let readState = allowed else')
            parts += [(TESTS / 'NagramiXBulkManualMarkPush.swift').read_text().replace('// PRODUCTION_GUARD', sender)]
        else:
            parts += ['func testManualMarkPush() {}']
        for result in execute(swiftc, work, 'bulk-read-' + label, '\n'.join(parts)):
            print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-bulk-read-reconciliation-') as directory:
        validate(args.source, args.swiftc, Path(directory))

#!/usr/bin/env python3
"""Verify the order and identity of the existing message settings."""
import argparse
from pathlib import Path
import re
import shutil
import tempfile

from late_source_stages import OVERLAY
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_settings_argument_bindings import SETTINGS
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'message_settings_order'
ROWS = ('hideBlockedMessages', 'messageEditHistory', 'saveTemporaryMessages',
        'showDeletedMessages', 'deletedMessageLabel', 'clearMessageArchive')


def verify_rows(text, previous):
    def visible_rows(controller):
        entries = block(controller, 'private func nagramiXAllSettingsEntries(')
        start = entries.index('        .hideBlockedMessages(')
        end = entries.index('        .privacyHeader,', start)
        return entries[start:end].splitlines()

    rows = visible_rows(text)
    assert sorted(rows) == sorted(visible_rows(previous)), 'Message setting bindings changed'
    assert tuple(re.match(r'\s*\.(\w+)', row)[1] for row in rows) == ROWS, 'Visible row order'
    ids = block(text, '    var stableId: Int32 {')
    assert ids == block(previous, '    var stableId: Int32 {'), 'Stable identifiers changed'
    compare = block(text, '    static func <')
    assert 'default: return entry.stableId * 10' in compare
    assert 'return position(lhs) < position(rhs)' in compare

    def position(name):
        pattern = rf'case \.{name}: return (\d+)'
        rank = re.search(pattern, compare)
        return int(rank[1]) if rank else int(re.search(pattern, ids)[1]) * 10

    order = [position(name) for name in ('sendSilently', *ROWS)]
    assert all(a < b for a, b in zip(order, order[1:])), 'Native list update order'
    assert block(text, '    func item(') == block(previous, '    func item('), 'Setting action changed'


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    if source is None:
        source = work / 'source'
        for name, template in {**plan['replacements'], **plan['guard_sources']}.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / template, path)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    guard_checks(source, STAGE, plan, work / 'guards')
    run([swiftc, '-frontend', '-parse', source / SETTINGS])
    verify_rows((source / SETTINGS).read_text(), (OVERLAY / plan['previous'][SETTINGS]).read_text())
    print('PASS: six message settings, native list order, stable IDs and existing item actions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='message-settings-order-') as directory:
        validate(args.source, args.swiftc, Path(directory))

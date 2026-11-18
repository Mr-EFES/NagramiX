#!/usr/bin/env python3
"""Exercise the Contacts menu using the real tab dispatch and settings."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
import tab_visibility_runtime as tab
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan

STAGE = 'contacts_tab_add'
MENU = '    private func nagramiXPresentTabMenu('


def check(source, swiftc, folder):
    plan = checked_plan(STAGE)
    before_controller = (OVERLAY / plan['previous'][tab.CONTACTS]).read_text()
    controller = (source / tab.CONTACTS).read_text()
    assert controller.replace('@objc public func addPressed()', '@objc func addPressed()', 1) == before_controller
    assert '@objc public func addPressed()' in controller

    before_root = (OVERLAY / plan['previous'][tab.ROOT_UI]).read_text()
    root = (source / tab.ROOT_UI).read_text()
    assert root.replace(block(root, MENU), block(before_root, MENU), 1) == before_root
    # The unchanged navigation button uses this same generated string and handler.
    node = (source / tab.CONTACT_NODE).read_text()
    assert 'strings.Contacts_VoiceOver_AddContact' in node
    assert 'self.controller?.addPressed()' in node
    for name in plan['inputs']:
        run([swiftc, '-frontend', '-parse', source / name], timeout=60)

    fixture = folder / 'TabMenu.swift'
    fixture.write_text(tab.fixture(source, adds_contact=True))
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        link, env = tab.modules(source, swiftc, folder / mode, flags)
        binary = folder / f'tab-menu-{mode}'
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
             '-module-cache-path', folder / mode / 'cache', *flags, *link, fixture, '-o', binary], timeout=180)
        result = run([binary], env=env, timeout=60)
        print(f'{mode}: {result.stdout.strip()}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    with tempfile.TemporaryDirectory(prefix='nagramix-contacts-tab-') as temporary:
        check(args.source, args.swiftc, Path(temporary))


if __name__ == '__main__':
    main()

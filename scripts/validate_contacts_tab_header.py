#!/usr/bin/env python3
"""Exercise the actual Contacts header configuration in all entry modes."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from tab_visibility_runtime import CONTACT_NODE
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, ROOT, checked_plan

STAGE = 'contacts_tab_header'
METHOD = '    func updateNavigationBar('


def check(source: Path, swiftc: Path, folder: Path) -> None:
    plan = checked_plan(STAGE)
    previous = (OVERLAY / plan['previous'][CONTACT_NODE]).read_text()
    updated = (source / CONTACT_NODE).read_text()
    previous_header = block(previous, METHOD)
    header = block(updated, METHOD)
    assert updated.replace(header, previous_header, 1) == previous
    content, separator, render_body = header.partition('        let navigationBarSize = ')
    assert separator and render_body == previous_header.partition(separator)[2]
    run([swiftc, '-frontend', '-parse', source / CONTACT_NODE], timeout=60)

    content = content.split('\n', 1)[1]
    boundary = (ROOT / 'scripts/tests/NagramiXContactsHeaderBoundary.swift').read_text()
    fixture = folder / 'ContactsHeader.swift'
    fixture.write_text(boundary.replace(
        '        // ACTUAL_HEADER_CONTENT',
        content + '        _ = (tabsNode, tabsNodeIsSearch)\n        return primaryContent',
        1,
    ))
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = folder / f'header-{mode}'
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
             '-module-cache-path', folder / 'cache', *flags, fixture, '-o', binary], timeout=60)
        result = run([binary], timeout=30)
        print(f'{mode}: {result.stdout.strip()}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    with tempfile.TemporaryDirectory(prefix='nagramix-contacts-header-') as folder:
        check(args.source, args.swiftc, Path(folder))


if __name__ == '__main__':
    main()

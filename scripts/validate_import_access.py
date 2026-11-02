#!/usr/bin/env python3
"""Reject ambiguous implicit/explicit imports before expensive Core SDK compilation."""
import argparse
from collections import defaultdict
from pathlib import Path
import re


def validate(source: Path) -> None:
    root = source / 'submodules/TelegramCore/Sources'
    if not root.is_dir():
        raise SystemExit(f'TelegramCore source not found: {root}')
    modules = defaultdict(lambda: defaultdict(list))
    pattern = re.compile(
        r'^[ \t]*(?:@[A-Za-z_]\w*(?:\([^\n]*?\))?[ \t]+)*'
        r'(?:(public|internal|package|private|fileprivate)[ \t]+)?'
        r'import[ \t]+(?:class[ \t]+|struct[ \t]+|enum[ \t]+|protocol[ \t]+|func[ \t]+|var[ \t]+|let[ \t]+|typealias[ \t]+)?(\w+)',
        re.M,
    )
    count = 0
    for path in sorted(root.rglob('*.swift')):
        count += 1
        for match in pattern.finditer(path.read_text()):
            level, name = match.groups()
            modules[name][level or 'implicit'].append(str(path.relative_to(source)))
    failures = []
    for name, levels in sorted(modules.items()):
        if 'implicit' in levels and len(levels) > 1:
            failures.append(f'{name}: implicit import conflicts with explicit access levels')
            failures.extend('  ' + name for name in sorted(set(levels['implicit'])))
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'PASS: {count} TelegramCore sources; no ambiguous mixed-access imports')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    validate(parser.parse_args().source)

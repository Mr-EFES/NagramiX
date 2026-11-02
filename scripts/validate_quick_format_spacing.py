#!/usr/bin/env python3
"""Проверить внешние края сетки A/B на итоговых исходниках."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    plan = json.loads((ROOT / 'ios/quick_format_equal_spacing_patches.json').read_text())
    for name, expected in plan['outputs'].items():
        assert hashlib.sha256((args.source/name).read_bytes()).hexdigest() == expected, name
    keyboard = (args.source/PREFIX/'NagramiXFormattingKeyboard.swift').read_text()
    assert 'self.heading.text = title' not in keyboard
    assert keyboard.count('self.heading.text = nil') == 2
    assert 'composer.window === window' in keyboard
    assert 'self.convert(composer.bounds, from: composer)' in keyboard
    if args.swiftc:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            geometry = args.source/PREFIX/'NagramiXFormattingGeometry.swift'
            for flags in [[], ['-O']]:
                subprocess.run([str(args.swiftc), '-parse-as-library', '-module-cache-path', str(temp/'cache'),
                    *flags, str(geometry), str(ROOT/'scripts/tests/NagramiXFormattingSpacingTests.swift'),
                    '-o', str(temp/'test')], check=True)
                subprocess.run([str(temp/'test')], check=True)
            # Регрессия: одинаковые внутренние отступы не учитывают внешний gap.
            broken = temp/'Broken.swift'
            original = geometry.read_text()
            assert original.count('top: outside - gap') == 1
            broken.write_text(original.replace('top: outside - gap', 'top: outside'))
            subprocess.run([str(args.swiftc), '-parse-as-library', '-module-cache-path', str(temp/'cache'),
                str(broken), str(ROOT/'scripts/tests/NagramiXFormattingSpacingTests.swift'),
                '-o', str(temp/'broken')], check=True)
            failed = subprocess.run([str(temp/'broken')], capture_output=True)
            assert failed.returncode != 0, 'Прежний неравный внешний зазор не обнаружен'
            print('PASS: regression with equal internal bands rejected')
            subprocess.run([str(args.swiftc), '-frontend', '-parse',
                *[str(args.source/name) for name in plan['outputs']]], check=True)
    print('PASS: exact source guards and hidden heading; Apple SDK/device pending')

if __name__ == '__main__':
    main()

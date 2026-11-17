"""Тела настоящих updateType/empty/layout; измерение текста и UIKit — IO-hosts."""
from pathlib import Path
from validate_quick_format import block
ROOT = Path(__file__).resolve().parents[1]
CALLS = 'submodules/CallListUI/Sources/CallListControllerNode.swift'


def fixture(source):
    text = (source / CALLS).read_text()
    code = (ROOT / 'scripts/tests/NagramiXCallFilterVisualBoundary.swift').read_text()
    methods = '\n'.join(block(text, m) for m in ['    func updateType(', '    func updateEmptyPlaceholder(', '    func updateLayout('])
    assert code.count('// METHODS') == 1
    return code.replace('// METHODS', methods, 1) + '\n' + (ROOT / 'scripts/tests/NagramiXCallFilterVisualTests.swift').read_text()

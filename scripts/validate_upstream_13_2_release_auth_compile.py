#!/usr/bin/env python3
"""Compile the actual phone-art visibility branch against its static node shape.

This boundary checks identity/visibility and rejects the old animation members;
the full UIKit layout and Apple SDK remain mandatory CI checks.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks

STAGE = 'upstream_13_2_release_auth_compile'
PHONE = 'submodules/AuthorizationUI/Sources/AuthorizationSequencePhoneEntryControllerNode.swift'
REMOVED = ('            self.animationNode.visibility = true\n',
           '            // The intro animation hands over to the managed one once it completes (and leaves its supernode).\n',
           '            self.managedAnimationNode.isHidden = self.animationNode.supernode != nil\n',
           '            self.managedAnimationNode.isHidden = true\n')


def fixture(text):
    start = text.index('        if items.first?.node === self.animationNode {')
    end = text.index('        let buttonFrame: CGRect', start)
    visibility = text[start:end]
    assert 'private let animationNode: ASImageNode' in text
    return r'''
class ASDisplayNode { var isHidden = false }
final class ASImageNode: ASDisplayNode {}
struct AuthorizationLayoutItem { let node: ASDisplayNode }
final class PhoneProbe {
    private let animationNode: ASImageNode
    init(image: ASImageNode) { self.animationNode = image }
    func update(items: [AuthorizationLayoutItem]) {
''' + visibility + r'''
    }
}
let image = ASImageNode()
let other = ASDisplayNode()
let phone = PhoneProbe(image: image)
phone.update(items: [.init(node: image)])
precondition(!image.isHidden)
phone.update(items: [.init(node: other), .init(node: image)])
precondition(image.isHidden)
phone.update(items: [])
precondition(image.isHidden)
phone.update(items: [.init(node: image), .init(node: other)])
precondition(!image.isHidden)
print("PASS: static phone artwork is visible exactly when retained as the first layout item")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = (OVERLAY / plan['previous'][PHONE]).read_text()
    after = (args.source / PHONE).read_text()
    expected = before
    for line in REMOVED:
        assert expected.count(line) == 1
        expected = expected.replace(line, '', 1)
    assert after == expected, 'Unrelated changes to authorization layout'
    assert 'managedAnimationNode' not in after and 'animationNode.visibility' not in after
    assert 'self.animationNode.image = NagramiXOnboardingImage(6)' in after
    # Other authorization screens still use genuine animated nodes.
    for name in plan['guards']:
        if name.endswith('ControllerNode.swift'):
            assert 'private let animationNode: AnimatedStickerNode' in (args.source / name).read_text()
    with tempfile.TemporaryDirectory(prefix='nagramix-auth-sdk-132-') as temporary:
        folder = Path(temporary)
        guards = folder / 'guards'
        guards.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guards)
        file = folder / 'visibility.swift'
        for flags in ([], ['-O']):
            cache = ['-module-cache-path', str(folder / 'cache')]
            file.write_text(fixture(after))
            binary = folder / 'visibility'
            subprocess.run([str(args.swiftc), *cache, '-warnings-as-errors', *flags, str(file), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
            file.write_text(fixture(before))
            failed = subprocess.run([str(args.swiftc), *cache, '-typecheck', *flags, str(file)], capture_output=True, text=True)
            assert failed.returncode != 0
            for member in ('visibility', 'managedAnimationNode'):
                assert "has no member '" + member + "'" in failed.stderr, failed.stderr
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / PHONE)], check=True)
    result = {'replacements': 1, 'guards': 5, 'fail_closed': len(rejected), 'production_boundary_executions': 2,
              'old_member_errors_reproduced': 2, 'full_apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

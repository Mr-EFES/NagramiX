#!/usr/bin/env python3
"""Check the narrow13.2 dependency repair and refusal of unexpected sources."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fetch_upstream_submodules as dependencies


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.plan = dependencies.load_plan()
        self.folder = tempfile.TemporaryDirectory(prefix='nagramix-dependency-contract-')
        self.addCleanup(self.folder.cleanup)
        self.source = Path(self.folder.name)
        self.modules = b'[submodule "fixture"]\npath=fixture\nurl=https://github.com/fixture/repository\n'
        (self.source / '.gitmodules').write_bytes(self.modules)

    def validate(self, *, change_tree=None, head=None, modules=None):
        plan = copy.deepcopy(self.plan)
        text = ''.join('[submodule "' + item['path'] + '"]\npath=' + item['path'] + '\nurl=' + item['declared_url'] + '\n' for item in plan['submodules'])
        (self.source / '.gitmodules').write_text(text)
        plan['gitmodules_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        tree = {item['path']: item['expected_ref'] for item in plan['submodules']}
        if change_tree:
            change_tree(tree)
        if modules:
            (self.source / '.gitmodules').write_text(modules)
        def git(source, *args, capture=False):
            self.assertTrue(capture)
            if args == ('rev-parse', 'HEAD'):
                return head or plan['target_pin']
            self.assertEqual(args, ('ls-tree', '-r', 'HEAD'))
            return '\n'.join('160000 commit ' + sha + '\t' + name for name, sha in tree.items())
        with mock.patch.object(dependencies, 'git', side_effect=git):
            dependencies.validate_source(self.source, plan)

    def test_exact_native_source(self):
        self.validate()

    def test_changed_native_pin_rejected(self):
        with self.assertRaises(AssertionError):
            self.validate(head='0' * 40)

    def test_changed_gitlink_rejected(self):
        with self.assertRaises(AssertionError):
            self.validate(change_tree=lambda tree: tree.update({dependencies.CALLS: '0' * 40}))

    def test_missing_dependency_rejected(self):
        with self.assertRaises(AssertionError):
            self.validate(change_tree=lambda tree: tree.pop(dependencies.CALLS))

    def test_unexpected_dependency_rejected(self):
        with self.assertRaises(AssertionError):
            self.validate(change_tree=lambda tree: tree.update({'unexpected': '0' * 40}))

    def test_changed_url_rejected_before_fetch(self):
        with self.assertRaises(AssertionError):
            self.validate(modules=self.modules.decode())

    def test_repair_is_fixed_and_visible(self):
        lines = dependencies.provenance_lines(self.plan)
        self.assertEqual(len(lines), 1)
        self.assertIn(dependencies.UNAVAILABLE + ' -> ' + dependencies.PUBLISHED, lines[0])
        self.assertIn('https://github.com/TelegramMessenger/tgcalls.git', lines[0])

    def test_changed_repair_rejected(self):
        path = self.source / 'dependencies.json'
        plan = copy.deepcopy(self.plan)
        next(item for item in plan['submodules'] if item['path'] == dependencies.CALLS)['checkout_ref'] = '0' * 40
        path.write_text(json.dumps(plan))
        with mock.patch.object(dependencies, 'PLAN', path), self.assertRaises(AssertionError):
            dependencies.load_plan()


if __name__ == '__main__':
    unittest.main()

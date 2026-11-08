import importlib.util
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'scripts/cleanup_source_checkpoint.py'
spec = importlib.util.spec_from_file_location('cleanup_source_checkpoint', SCRIPT)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CheckpointCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nagramix-cleanup-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'runner-temp'
        self.root.mkdir()
        self.active = self.application(self.base / 'workspace/Telegram-iOS')
        self.name = 'nagramix-pre-pip'
        self.target = self.application(self.root / self.name)

    def application(self, path):
        (path / 'Telegram').mkdir(parents=True)
        (path / 'Telegram/BUILD').write_text('application marker\n')
        (path / 'keep.swift').write_text('preserve bytes\n')
        return path

    def refuse(self, *, root=None, name=None, active=None):
        with self.assertRaises((cleanup.CleanupRefused, OSError)):
            cleanup.cleanup_checkpoint(root or self.root, name or self.name, active or self.active)
        self.assertTrue(self.active.exists())
        self.assertEqual((self.active / 'keep.swift').read_text(), 'preserve bytes\n')

    def test_all_four_names_delete_only_requested_checkpoint(self):
        for name in cleanup.CHECKPOINT_NAMES:
            with self.subTest(name=name):
                target = self.root / name
                if not target.exists(): self.application(target)
                neighbor = self.root / 'unrelated'
                neighbor.mkdir(exist_ok=True)
                (neighbor / 'keep').write_text('neighbor')
                self.assertEqual(cleanup.cleanup_checkpoint(self.root, name, self.active), target)
                self.assertFalse(target.exists())
                self.assertEqual((neighbor / 'keep').read_text(), 'neighbor')
                self.assertEqual((self.active / 'keep.swift').read_text(), 'preserve bytes\n')

    def test_contained_symlinks_do_not_touch_external_files_or_directory(self):
        outside = self.application(self.base / 'outside')
        (self.target / 'external-directory').symlink_to(outside, target_is_directory=True)
        (self.target / 'external-file').symlink_to(outside / 'keep.swift')
        (self.target / 'broken-link').symlink_to(self.base / 'missing')
        cleanup.cleanup_checkpoint(self.root, self.name, self.active)
        self.assertFalse(self.target.exists())
        self.assertEqual((outside / 'keep.swift').read_text(), 'preserve bytes\n')

    def test_unknown_and_traversal_names_refused(self):
        for name in ('unknown', '../'+self.name, self.name+'/child', '/'+self.name):
            with self.subTest(name=name): self.refuse(name=name)
        self.assertTrue(self.target.exists())

    def test_relative_traversing_and_unsafe_roots_refused(self):
        for root in (Path('.'), Path('/'), Path('/tmp'), Path('/var/tmp'), Path('/private/var/tmp'), self.root/'..'/'runner-temp', Path.home()):
            with self.subTest(root=root): self.refuse(root=root)
        self.assertTrue(self.target.exists())

    def test_final_root_symlink_refused_but_macos_style_ancestor_alias_is_safe(self):
        alias = self.base / 'root-link'
        alias.symlink_to(self.root, target_is_directory=True)
        self.refuse(root=alias)
        parent_alias = self.base / 'parent-link'
        parent_alias.symlink_to(self.base, target_is_directory=True)
        cleanup.cleanup_checkpoint(parent_alias/'runner-temp', self.name, self.active)
        self.assertFalse(self.target.exists())

    def test_checkpoint_symlink_refused(self):
        for child in self.target.rglob('*'):
            if child.is_file(): child.unlink()
        (self.target/'Telegram').rmdir(); self.target.rmdir()
        self.target.symlink_to(self.active, target_is_directory=True)
        self.refuse()
        self.assertTrue(self.target.is_symlink())

    def test_missing_or_file_checkpoint_refused(self):
        self.refuse(name='nagramix-pre-temporary-interaction')
        path=self.root/'nagramix-pre-account-settings-entry';path.write_text('not a tree')
        self.refuse(name=path.name)
        self.assertEqual(path.read_text(), 'not a tree')

    def test_missing_or_symlink_marker_refused(self):
        marker=self.target/'Telegram/BUILD';marker.unlink()
        self.refuse()
        marker.symlink_to(self.active/'Telegram/BUILD')
        self.refuse()
        self.assertTrue(self.target.exists())

    def test_marker_parent_symlink_refused(self):
        (self.target/'Telegram/BUILD').unlink();(self.target/'Telegram').rmdir()
        (self.target/'Telegram').symlink_to(self.active/'Telegram',target_is_directory=True)
        self.refuse()

    def test_active_equal_descendant_or_ancestor_refused(self):
        self.refuse(active=self.target)
        nested=self.application(self.target/'nested-active')
        self.refuse(active=nested)
        nested_root=self.active/'runner-temp';nested_root.mkdir()
        nested_target=self.application(nested_root/self.name)
        self.refuse(root=nested_root)
        self.assertTrue(nested_target.exists())

    def test_active_alias_overlap_and_missing_source_refused(self):
        alias=self.base/'active-link';alias.symlink_to(self.target,target_is_directory=True)
        self.refuse(active=alias)
        self.refuse(active=self.base/'missing-source')

    def test_unsafe_rmtree_implementation_refused(self):
        with mock.patch.object(cleanup.shutil.rmtree, 'avoids_symlink_attacks', False):
            self.refuse()
        self.assertTrue(self.target.exists())

    def test_symlink_swap_before_removal_does_not_follow_active_source(self):
        original_rmtree=cleanup.shutil.rmtree
        moved=self.root/'moved-original'
        def swap_and_remove(name, *, dir_fd):
            self.target.rename(moved)
            self.target.symlink_to(self.active,target_is_directory=True)
            return original_rmtree(name,dir_fd=dir_fd)
        swap_and_remove.avoids_symlink_attacks=original_rmtree.avoids_symlink_attacks
        with mock.patch.object(cleanup.shutil,'rmtree',swap_and_remove):
            self.refuse()
        self.assertTrue(moved.exists())
        self.assertTrue(self.target.is_symlink())

    def test_cli_rejects_and_succeeds_without_removing_reports(self):
        report=self.root/'report.json';report.write_text('{}')
        args=['python3',str(SCRIPT),'--root',str(self.root),'--active-source',str(self.active),'--name']
        rejected=subprocess.run(args+['unknown'],capture_output=True,text=True)
        self.assertEqual(rejected.returncode,2);self.assertTrue(self.target.exists())
        accepted=subprocess.run(args+[self.name],capture_output=True,text=True)
        self.assertEqual(accepted.returncode,0,accepted.stderr);self.assertFalse(self.target.exists())
        self.assertEqual(report.read_text(),'{}')

    def test_relative_active_source_used_by_workflow(self):
        result=subprocess.run(['python3',str(SCRIPT),'--root',str(self.root),'--name',self.name,'--active-source','Telegram-iOS'],cwd=self.active.parent,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.target.exists())

    def test_failed_validator_keeps_checkpoint_under_ci_bash_error_mode(self):
        command=shlex.join(['python3',str(SCRIPT),'--root',str(self.root),'--name',self.name,'--active-source',str(self.active)])
        failed=subprocess.run(['bash','-e','-c','false\n'+command],capture_output=True,text=True)
        self.assertNotEqual(failed.returncode,0)
        self.assertTrue(self.target.exists())
        accepted=subprocess.run(['bash','-e','-c','true\n'+command],capture_output=True,text=True)
        self.assertEqual(accepted.returncode,0,accepted.stderr)
        self.assertFalse(self.target.exists())

    def test_workflow_cleans_each_copy_only_after_its_validator(self):
        text=(REPO/'.github/workflows/build-unsigned-ipa.yml').read_text()
        pairs={'nagramix-pre-pip':'pip_swipe_handoff','nagramix-pre-temporary-interaction':'temporary_message_interaction','nagramix-pre-account-settings-entry':'account_settings_entry','nagramix-pre-release-090-preflight':'release_090_preflight_fixes'}
        lines=text.splitlines()
        cleanup_lines=[line.strip() for line in lines if 'python3 scripts/cleanup_source_checkpoint.py ' in line]
        self.assertEqual(len(cleanup_lines),4)
        for name,validator in pairs.items():
            indexes=[i for i,line in enumerate(lines) if 'python3 scripts/validate_'+validator+'.py ' in line]
            self.assertEqual(len(indexes),1)
            expected='python3 scripts/cleanup_source_checkpoint.py --root "$RUNNER_TEMP" --name '+name+' --active-source Telegram-iOS'
            self.assertEqual(lines[indexes[0]+1].strip(),expected)
            references=[line for line in lines if name in line]
            self.assertEqual(len(references),3, 'Only copy, validator and cleanup may reference a checkpoint')
        validation_block=next(block for block in text.split('\n      - name: ') if 'validate_release_090_preflight_fixes.py' in block)
        self.assertNotIn('continue-on-error:',validation_block)
        self.assertNotIn('always()',validation_block)


if __name__ == '__main__':
    unittest.main()

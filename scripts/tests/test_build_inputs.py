"""Регрессии ранней проверки сборочных входов без подмены Apple-компиляции."""
import sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import validate_build_inputs as checks


class BuildInputsTests(unittest.TestCase):
    def setUp(self):self.workflow=(checks.ROOT/'.github/workflows/build-unsigned-ipa.yml').read_text()
    def test_current_workflow(self):self.assertGreater(len(checks.workflow_contract(self.workflow)),30)
    def test_push_duplicate_refused(self):
        with self.assertRaises(SystemExit):checks.workflow_contract(self.workflow.replace('on:\n','on:\n  push:\n',1))
    def test_concurrency_cancellation_refused(self):
        with self.assertRaises(SystemExit):checks.workflow_contract(self.workflow+'\nconcurrency:\n  cancel-in-progress: true\n')
    def test_simulator_refused(self):
        with self.assertRaises(SystemExit):checks.workflow_contract(self.workflow.replace('--configuration=release_arm64','--configuration=debug_sim_arm64'))
    def test_changed_signing_mode_refused(self):
        with self.assertRaises(SystemExit):checks.workflow_contract(self.workflow.replace('--team NAGRAMIX0','--team OTHERTEAM'))
    def test_wrong_case_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Sources').mkdir();(root/'Sources/Camera.swift').write_text('')
            self.assertEqual(checks.exact_path(root,'Sources/Camera.swift'),root/'Sources/Camera.swift')
            with self.assertRaises(SystemExit):checks.exact_path(root,'Sources/camera.swift')
    def test_missing_file_refused(self):
        with tempfile.TemporaryDirectory() as folder,self.assertRaises(SystemExit):checks.exact_path(Path(folder),'missing.swift')
    def test_no_fake_native_success(self):
        with mock.patch.object(checks.sys,'platform','linux'),self.assertRaises(SystemExit):checks.check_native(Path('/tmp'))

if __name__=='__main__':unittest.main()

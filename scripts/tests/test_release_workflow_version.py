"""Не допускать потери .0 при числовом YAML и расхождения настоящей среды CI."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_version import workflow_release_version, validate_workflow_release_version
import validate_build_inputs
import validate_release_metadata


def workflow(value):
    return 'name: release\nenv:\n  NAGRAMIX_VERSION: ' + value + '\njobs:\n  build: {}\n'


class WorkflowReleaseVersionTests(unittest.TestCase):
    def test_quoted_approved_sequence_preserves_full_label(self):
        for version in ['0.9.9', '1.0', '1.0.1', '1.0.9', '1.1', '1.2', '2.0', '10.0']:
            with self.subTest(version=version):
                text = workflow(json.dumps(version))
                self.assertEqual(workflow_release_version(text), version)
                self.assertEqual(validate_workflow_release_version(text, version,
                                 {'GITHUB_ACTIONS': 'true', 'NAGRAMIX_VERSION': version}), version)

    def test_original_numeric_yaml_and_other_non_strings_are_rejected(self):
        for value in ['1.0', '1.1', '10.0', '1', '1e0', 'true', 'null', '[]', '{}']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                workflow_release_version(workflow(value))

    def test_missing_duplicate_and_job_only_versions_are_rejected(self):
        for text in [
            'jobs:\n  build: {}\n',
            'jobs:\n  build:\n    env:\n      NAGRAMIX_VERSION: "1.0"\n',
            workflow('"1.0"').replace('jobs:', '  NAGRAMIX_VERSION: "1.0"\njobs:'),
            workflow('"1.0"') + 'env:\n  NAGRAMIX_VERSION: "1.0"\n',
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                workflow_release_version(text)

    def test_invalid_or_computed_labels_are_rejected(self):
        for value in ['"1"', '"1.0.0"', '"01.0"', '"1.0\\n"', "'1.0'", '${{ vars.VERSION }}']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                workflow_release_version(workflow(value))

    def test_effective_actions_value_must_match_exactly(self):
        for actual in ['1', '1.0.0', '', None]:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, 'Фактическая'):
                validate_workflow_release_version(workflow('"1.0"'), '1.0',
                                                  {'GITHUB_ACTIONS': 'true', 'NAGRAMIX_VERSION': actual})

    def test_registry_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'реестром'):
            validate_workflow_release_version(workflow('"1.0"'), '1.1', {})

    def test_local_checks_do_not_require_actions_environment(self):
        self.assertEqual(validate_workflow_release_version(workflow('"1.0"'), '1.0', {}), '1.0')

    def test_actual_metadata_entry_rejects_truncated_ci_environment(self):
        with mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'NAGRAMIX_VERSION': '1'}):
            with self.assertRaisesRegex(SystemExit, 'Фактическая NAGRAMIX_VERSION'):
                validate_release_metadata.main()

    def test_actual_build_inputs_entry_rejects_truncated_ci_environment(self):
        with mock.patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'NAGRAMIX_VERSION': '1'}):
            with self.assertRaisesRegex(SystemExit, 'Фактическая NAGRAMIX_VERSION'):
                validate_build_inputs.check_repo()


if __name__ == '__main__':
    unittest.main()

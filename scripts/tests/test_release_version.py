"""Границы утверждённой нумерации и совместимость числовых IPA-контрактов."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_version import is_release_version, next_release_version, parse_release_version


class ReleaseVersionTests(unittest.TestCase):
    def test_approved_sequence(self):
        for current, expected in [
            ('0.9.8', '0.9.9'), ('0.9.9', '1.0'), ('1.0', '1.0.1'),
            ('1.0.1', '1.0.2'), ('1.0.8', '1.0.9'), ('1.0.9', '1.1'),
            ('1.1', '1.1.1'), ('1.1.8', '1.1.9'), ('1.1.9', '1.2'),
            ('1.9.9', '2.0'), ('9.9.9', '10.0'),
        ]:
            with self.subTest(current=current):
                self.assertEqual(next_release_version(current), expected)
                self.assertTrue(is_release_version(expected))
                self.assertGreater(parse_release_version(expected), parse_release_version(current))

    def test_short_versions_compare_numerically(self):
        self.assertEqual(parse_release_version('1.0'), (1, 0, 0))
        self.assertLess(parse_release_version('0.9.9'), parse_release_version('1.0'))
        self.assertLess(parse_release_version('1.0'), parse_release_version('1.0.1'))
        self.assertLess(parse_release_version('1.0.9'), parse_release_version('1.1'))
        self.assertGreater(parse_release_version('10.0'), parse_release_version('9.9.9'))

    def test_noncanonical_labels_cannot_be_released(self):
        for value in ['', '1', 'v1.0', '1.0\n', ' 1.0', '01.0', '1.00',
                      '1.0.0', '1.10', '1.0.10', '0.9', '0.10.0',
                      '1.0-beta', '1.0.1.2', '-1.0', '١.٠', None]:
            with self.subTest(value=value):
                self.assertFalse(is_release_version(value))
                with self.assertRaises(ValueError):
                    next_release_version(value)

    def test_historical_numeric_catalog_comparison_is_preserved(self):
        self.assertEqual(parse_release_version('0.10.0'), (0, 10, 0))
        self.assertEqual(parse_release_version('0.9.100'), (0, 9, 100))


if __name__ == '__main__':
    unittest.main()

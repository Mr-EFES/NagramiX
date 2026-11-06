#!/usr/bin/env python3
"""Regression checks for exact old/new IPA localization catalogs."""
import io
import json
from pathlib import Path
import plistlib
import unittest
import zipfile

from validate_app_language_localization import strings
from validate_unsigned_ipa import validate_settings_localizations

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'Payload/Telegram.app/'
RESOURCE = PREFIX + 'Frameworks/TelegramUIFramework.framework/NagramiXLocalization.bundle/'


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        overlay = ROOT / 'ios'
        plan = json.loads((overlay / 'upstream_13_2_release_post_patches.json').read_text())
        cls.current = {}
        cls.previous = {}
        for name in plan['outputs']:
            if name.startswith('submodules/NagramiXCore/Resources/') and name.endswith('.lproj/Localizable.strings'):
                code = Path(name).parent.name.removesuffix('.lproj')
                cls.current[code] = strings(overlay / plan['replacements'][name])
                cls.previous[code] = strings(overlay / plan['previous'][name])

    def archive(self, catalogs, change=None):
        target = io.BytesIO()
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for code, original in catalogs.items():
                values = dict(original)
                if change and not change(code, values):
                    continue
                archive.writestr(RESOURCE + code + '.lproj/Localizable.strings', plistlib.dumps(values, fmt=plistlib.FMT_BINARY))
        target.seek(0)
        return zipfile.ZipFile(target)

    def test_current_exact_71_by_629(self):
        self.assertEqual(len(self.current), 71)
        self.assertTrue(all(len(values) == 629 for values in self.current.values()))
        with self.archive(self.current) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.8.9'), 71)

    def test_old_published_contract_still_supported(self):
        self.assertTrue(all(len(values) == 613 for values in self.previous.values()))
        with self.archive(self.previous) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.8.8'), 71)

    def test_old_catalog_rejected_for_new_release(self):
        with self.archive(self.previous) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.8.9')

    def test_missing_language_rejected(self):
        with self.archive(self.current, lambda code, values: code != 'de') as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.8.9')

    def test_modified_translation_rejected(self):
        def change(code, values):
            if code == 'ru':
                values['NagramiX.Settings.Page.Other'] = 'changed'
            return True
        with self.archive(self.current, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.8.9')

    def test_new_debug_key_missing_rejected(self):
        def change(code, values):
            if code == 'en':
                del values['NagramiX.Debug.Remove Downloaded Models']
            return True
        with self.archive(self.current, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.8.9')


if __name__ == '__main__':
    unittest.main()

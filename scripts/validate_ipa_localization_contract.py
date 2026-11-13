#!/usr/bin/env python3
"""Regression checks for exact old/new IPA localization catalogs."""
import io
import hashlib
import json
from pathlib import Path
import plistlib
import unittest
from unittest import mock
import zipfile

from validate_app_language_localization import strings
from validate_unsigned_ipa import expected_nagramix_catalogs, validate_settings_localizations
from late_source_stages import LATE_SOURCE_STAGES

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
        cls.wide_plan = json.loads((overlay / 'wide_tab_bar_setting_patches.json').read_text())
        cls.latest = {}
        for name, snapshot in cls.wide_plan['replacements'].items():
            if name.startswith('submodules/NagramiXCore/Resources/') and name.endswith('.lproj/Localizable.strings'):
                code = Path(name).parent.name.removesuffix('.lproj')
                cls.latest[code] = strings(overlay / snapshot)
        cls.round_plan = json.loads((overlay / 'round_video_editor_patches.json').read_text())
        cls.round_video = {}
        for name, snapshot in cls.round_plan['replacements'].items():
            if name.startswith('submodules/NagramiXCore/Resources/') and name.endswith('.lproj/Localizable.strings'):
                code = Path(name).parent.name.removesuffix('.lproj')
                cls.round_video[code] = strings(overlay / snapshot)

        cls.premium_plan = json.loads((overlay / 'hide_premium_offers_patches.json').read_text())
        cls.consent_plan = json.loads((overlay / 'content_interaction_consent_patches.json').read_text())
        cls.next_catalogs = {}
        for name, snapshot in cls.consent_plan['replacements'].items():
            if name.startswith('submodules/NagramiXCore/Resources/') and name.endswith('.lproj/Localizable.strings'):
                code = Path(name).parent.name.removesuffix('.lproj')
                cls.next_catalogs[code] = strings(overlay / snapshot)

        # Derive the final source independently of the package expectation
        # builder. A later label-only stage must not be lost at the same count.
        cls.final_snapshots = {}
        for stage in LATE_SOURCE_STAGES:
            stage_plan = json.loads((overlay / (stage + '_patches.json')).read_text())
            for name, snapshot in stage_plan['replacements'].items():
                if name.startswith('submodules/NagramiXCore/Resources/') and name.endswith('.lproj/Localizable.strings'):
                    code = Path(name).parent.name.removesuffix('.lproj')
                    cls.final_snapshots[code] = (overlay / snapshot, stage_plan['outputs'][name])
        cls.final_catalogs = {code: strings(path) for code, (path, _) in cls.final_snapshots.items()}

    def archive(self, catalogs, change=None, extra=None):
        target = io.BytesIO()
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for code, original in catalogs.items():
                values = dict(original)
                if change and not change(code, values):
                    continue
                archive.writestr(RESOURCE + code + '.lproj/Localizable.strings', plistlib.dumps(values, fmt=plistlib.FMT_BINARY))
            if extra:
                for code, values in extra.items():
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

    def test_090_exact_71_by_630(self):
        self.assertEqual(len(self.latest), 71)
        self.assertTrue(all(len(values) == 630 for values in self.latest.values()))
        self.assertEqual(expected_nagramix_catalogs('0.9.0'), self.latest)
        with self.archive(self.latest) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.0'), 71)

    def test_published_091_keeps_630_contract(self):
        with self.archive(self.latest) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.1'), 71)

    def test_092_exact_71_by_635(self):
        self.assertEqual(len(self.next_catalogs), 71)
        self.assertTrue(all(len(values) == 635 for values in self.next_catalogs.values()))
        self.assertEqual(expected_nagramix_catalogs('0.9.2'), self.next_catalogs)
        with self.archive(self.next_catalogs) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.2'), 71)

    def test_pre_fonts_version_keeps_635_contract(self):
        latest = {code: dict(values) for code, values in self.next_catalogs.items()}
        label_plan = json.loads((ROOT / 'ios/premium_label_spelling_patches.json').read_text())
        resource = 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'
        latest['ru'] = strings(ROOT / 'ios' / label_plan['replacements'][resource])
        self.assertEqual(expected_nagramix_catalogs('0.9.3'), latest)
        with self.archive(latest) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.3'), 71)
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.4'), 71)
        with self.archive(self.next_catalogs) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.3')
        with self.archive(latest) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_old_catalog_rejected_for_092(self):
        with self.archive(self.latest) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_round_catalog_rejected_for_published_091(self):
        with self.archive(self.next_catalogs) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.1')

    def test_round_hint_missing_rejected(self):
        def change(code, values):
            if code == 'ru':
                del values['NagramiX.RoundVideo.CropHint']
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_round_title_modified_rejected(self):
        def change(code, values):
            if code == 'en':
                values['NagramiX.RoundVideo.Title'] = 'changed'
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_old_key_replaced_at_same_count_rejected_for_092(self):
        def change(code, values):
            if code == 'de':
                del values['NagramiX.Settings.Page.Other']
                values['NagramiX.Unexpected.Placeholder'] = 'unchanged count'
                self.assertEqual(len(values), 635)
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_missing_language_rejected_for_092(self):
        with self.archive(self.next_catalogs, lambda code, values: code != 'de') as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_extra_language_rejected_for_092(self):
        with self.archive(self.next_catalogs, extra={'zz': self.next_catalogs['en']}) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_round_source_snapshot_sha_is_checked(self):
        name = 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'
        source = ROOT / 'ios' / self.round_plan['replacements'][name]
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b'\n// drift\n' if path == source else data
        with mock.patch.object(Path, 'read_bytes', new=corrupted), self.assertRaisesRegex(SystemExit, 'каталог круглого видео изменён'):
            expected_nagramix_catalogs('0.9.2')

    def test_629_catalog_rejected_for_090(self):
        with self.archive(self.current) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_630_catalog_rejected_for_089(self):
        with self.archive(self.latest) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.8.9')

    def test_wide_key_missing_rejected_for_090(self):
        def change(code, values):
            if code == 'ru':
                del values['NagramiX.Settings.Tabs.WideBar']
            return True
        with self.archive(self.latest, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_old_key_replaced_at_same_count_rejected_for_090(self):
        def change(code, values):
            if code == 'de':
                del values['NagramiX.Settings.Page.Other']
                values['NagramiX.Unexpected.Placeholder'] = 'unchanged count'
                self.assertEqual(len(values), 630)
            return True
        with self.archive(self.latest, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_extra_language_rejected_for_090(self):
        with self.archive(self.latest, extra={'zz': self.latest['en']}) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_missing_language_rejected_for_090(self):
        with self.archive(self.latest, lambda code, values: code != 'de') as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_modified_wide_translation_rejected_for_090(self):
        def change(code, values):
            if code == 'ru':
                values['NagramiX.Settings.Tabs.WideBar'] = 'changed'
            return True
        with self.archive(self.latest, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.0')

    def test_wide_source_snapshot_sha_is_checked(self):
        name = 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'
        source = ROOT / 'ios' / self.wide_plan['replacements'][name]
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b'\n// drift\n' if path == source else data
        with mock.patch.object(Path, 'read_bytes', new=corrupted), self.assertRaisesRegex(SystemExit, 'каталог широкой панели изменён'):
            expected_nagramix_catalogs('0.9.0')


    def test_intermediate_632_rejected_for_092(self):
        with self.archive(self.round_video) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_intermediate_634_rejected_for_092(self):
        catalogs = {}
        for name, snapshot in self.premium_plan['replacements'].items():
            if name.endswith('.lproj/Localizable.strings'):
                catalogs[Path(name).parent.name.removesuffix('.lproj')] = strings(ROOT / 'ios' / snapshot)
        with self.archive(catalogs) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_explicit_open_label_missing_rejected(self):
        def change(code, values):
            if code == 'ru':
                del values['NagramiX.Temporary.MarkOpened']
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_premium_hint_missing_rejected(self):
        def change(code, values):
            if code == 'ru':
                del values['NagramiX.Settings.HidePremiumOffersInfo']
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_premium_translation_changed_rejected(self):
        def change(code, values):
            if code == 'en':
                values['NagramiX.Settings.HidePremiumOffers'] = 'changed'
            return True
        with self.archive(self.next_catalogs, change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.2')

    def test_premium_source_snapshot_sha_is_checked(self):
        name = 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'
        source = ROOT / 'ios' / self.premium_plan['replacements'][name]
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b'\n// drift\n' if path == source else data
        with mock.patch.object(Path, 'read_bytes', new=corrupted), self.assertRaisesRegex(SystemExit, 'каталог скрытия Premium изменён'):
            expected_nagramix_catalogs('0.9.2')

    def test_effects_catalog_has_all_keys(self):
        catalogs = expected_nagramix_catalogs('0.9.6')
        self.assertEqual(len(catalogs), 71)
        self.assertTrue(all(len(values) == 668 for values in catalogs.values()))
        self.assertEqual(catalogs['ru']['NagramiX.InputEffects.Enabled'], 'Анимация при наборе')

    def test_snowfall_keys_are_required(self):
        def change(code, values):
            if code == 'ca': del values['NagramiX.Atmosphere.Density']
            return True
        with self.archive(expected_nagramix_catalogs('0.9.6'), change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_effects_keys_are_required(self):
        def change(code, values):
            if code == 'ja': del values['NagramiX.InputEffects.Preset.PanelWave']
            return True
        with self.archive(expected_nagramix_catalogs('0.9.6'), change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_preview_096_exact_catalogs(self):
        with self.archive(expected_nagramix_catalogs('0.9.6')) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.6'), 71)

    def test_096_matches_every_final_source_catalog(self):
        for path, digest in self.final_snapshots.values():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertEqual(len(self.final_catalogs), 71)
        self.assertTrue(all(len(values) == 668 for values in self.final_catalogs.values()))
        self.assertEqual(expected_nagramix_catalogs('0.9.6'), self.final_catalogs)
        with self.archive(self.final_catalogs) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.6'), 71)

    def test_097_matches_current_source_catalogs(self):
        self.assertEqual(expected_nagramix_catalogs('0.9.7'), self.final_catalogs)
        with self.archive(self.final_catalogs) as archive:
            self.assertEqual(validate_settings_localizations(archive, PREFIX, '0.9.7'), 71)

    def test_original208_quoted_local_read_is_rejected(self):
        def change(code, values):
            if code == 'ru': values['NagramiX.ReadMode.Local'] = 'Локальное «чтение»'
            return True
        with self.archive(self.final_catalogs, change) as archive, self.assertRaisesRegex(SystemExit, 'неполны: ru'):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_096_local_read_keeps_published_095_unchanged(self):
        self.assertEqual(expected_nagramix_catalogs('0.9.5')['ru']['NagramiX.ReadMode.Local'], 'Локальное «чтение»')
        self.assertEqual(expected_nagramix_catalogs('0.9.6')['ru']['NagramiX.ReadMode.Local'], 'Локальное чтение')

    def test_096_other_value_changed_at_same_count_is_rejected(self):
        def change(code, values):
            if code == 'en': values['NagramiX.Settings.Page.Other'] = 'changed'
            return True
        with self.archive(self.final_catalogs, change) as archive, self.assertRaisesRegex(SystemExit, 'неполны: en'):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_096_missing_language_is_rejected(self):
        with self.archive(self.final_catalogs, lambda code, values: code != 'de') as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_096_extra_language_is_rejected(self):
        with self.archive(self.final_catalogs, extra={'zz': self.final_catalogs['en']}) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_local_read_source_snapshot_sha_is_checked(self):
        plan = json.loads((ROOT/'ios/local_read_label_patches.json').read_text())
        name = 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'
        source = ROOT/'ios'/plan['replacements'][name]
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b'\n// drift\n' if path == source else data
        with mock.patch.object(Path, 'read_bytes', new=corrupted), self.assertRaisesRegex(SystemExit, 'каталог локального чтения изменён'):
            expected_nagramix_catalogs('0.9.6')

    def test_095_catalog_rejected_for_096(self):
        with self.archive(expected_nagramix_catalogs('0.9.5')) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_096_catalog_rejected_for_published_095(self):
        with self.archive(expected_nagramix_catalogs('0.9.6')) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.5')

    def test_preview_key_missing_rejected(self):
        def change(code, values):
            if code == 'de': del values['NagramiX.Fonts.Current']
            return True
        with self.archive(expected_nagramix_catalogs('0.9.6'), change) as archive, self.assertRaises(SystemExit):
            validate_settings_localizations(archive, PREFIX, '0.9.6')

    def test_preview_source_snapshot_sha_is_checked(self):
        plan = json.loads((ROOT/'ios/font_preview_apply_patches.json').read_text())
        name = 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'
        source = ROOT/'ios'/plan['replacements'][name]
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b'\n// drift\n' if path == source else data
        with mock.patch.object(Path, 'read_bytes', new=corrupted), self.assertRaisesRegex(SystemExit, 'каталог предпросмотра шрифтов изменён'):
            expected_nagramix_catalogs('0.9.6')


if __name__ == '__main__':
    unittest.main()

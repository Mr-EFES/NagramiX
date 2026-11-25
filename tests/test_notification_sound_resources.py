"""Не допускать публикацию пакета с пустыми разделами встроенных мелодий."""

import importlib.util
import io
import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ipa_validator", ROOT / "scripts/validate_unsigned_ipa.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
SOUNDS = ROOT / "ios/Resources/NotificationSounds"
MANIFEST = json.loads((SOUNDS / "manifest.json").read_text())
PREFIX = "Payload/NagramiX.app/"


class NotificationSoundResourcesTest(unittest.TestCase):
    def archive(self, missing=None, damaged=None):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for row in MANIFEST:
                if row["file"] == missing:
                    continue
                content = (SOUNDS / row["file"]).read_bytes()
                if row["file"] == damaged:
                    content = content[:16]
                archive.writestr(PREFIX + row["file"], content)
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_complete_catalog(self):
        with self.archive() as archive:
            self.assertEqual(validator.validate_notification_sound_resources(archive, PREFIX), 31)

    def test_missing_tone_in_each_group(self):
        for name in ("200.m4a", "100.m4a", "2.m4a"):
            with self.subTest(name=name), self.archive(missing=name) as archive:
                with self.assertRaisesRegex(SystemExit, "отсутствует встроенная мелодия"):
                    validator.validate_notification_sound_resources(archive, PREFIX)

    def test_partial_audio_file(self):
        with self.archive(damaged="205.m4a") as archive:
            with self.assertRaisesRegex(SystemExit, "повреждена встроенная мелодия"):
                validator.validate_notification_sound_resources(archive, PREFIX)


if __name__ == "__main__":
    unittest.main()

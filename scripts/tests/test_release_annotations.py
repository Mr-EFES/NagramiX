"""Preserve published annotations while validating the complete release catalog."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate_release_metadata import ANNOTATION, annotation_errors, published_status_errors


class AnnotationTests(unittest.TestCase):
    def test_published_annotation_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for version in ['0.9.7','0.9.8']:
                (folder/(version+'.md')).write_text(ANNOTATION+'\n')
            before=(folder/'0.9.7.md').read_bytes()
            self.assertEqual(annotation_errors(folder,'0.9.8'),[])
            self.assertEqual((folder/'0.9.7.md').read_bytes(),before)

    def test_current_annotation_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'0.9.7.md').write_text(ANNOTATION)
            self.assertTrue(annotation_errors(folder,'0.9.8'))

    def test_old_content_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'0.9.8.md').write_text(ANNOTATION)
            (folder/'0.9.7.md').write_text('changed')
            self.assertTrue(annotation_errors(folder,'0.9.8'))

    def test_future_or_invalid_filename_is_rejected(self):
        for name in ['0.9.9.md','notes.md']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                folder=Path(d);(folder/'0.9.8.md').write_text(ANNOTATION)
                (folder/name).write_text(ANNOTATION)
                self.assertTrue(annotation_errors(folder,'0.9.8'))

    def test_current_content_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'0.9.8.md').write_text('changed')
            self.assertTrue(annotation_errors(folder,'0.9.8'))

    def test_short_release_keeps_older_annotations(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for version in ['0.9.8','0.9.9','1.0','1.0.9','1.1']:
                (folder/(version+'.md')).write_text(ANNOTATION)
            self.assertEqual(annotation_errors(folder,'1.1'),[])
            self.assertTrue(any('будущей версии' in error for error in annotation_errors(folder,'1.0')))

    def test_zero_patch_alias_is_not_another_release(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for version in ['1.0','1.0.0']:
                (folder/(version+'.md')).write_text(ANNOTATION)
            self.assertTrue(any('Неверное имя' in error for error in annotation_errors(folder,'1.0')))


class PublishedStatusTests(unittest.TestCase):
    def test_downloads_must_point_to_latest_ipa(self):
        url = "https://github.com/Mr-EFES/NagramiX/releases/download/v1.0.6/NagramiX-1.0.6-unsigned.ipa"
        release = {"tag_name": "v1.0.6", "draft": False, "prerelease": False,
                   "assets": [{"name": url.rsplit("/", 1)[1], "browser_download_url": url}]}
        current = f"[Скачать IPA]({url})"
        old = current.replace("1.0.6", "1.0.5")
        self.assertEqual(published_status_errors(current, "1.0.6", release), [])
        for text in ("", old, current + "\n" + old):
            with self.subTest(text=text):
                self.assertTrue(published_status_errors(text, "1.0.6", release))
        self.assertTrue(published_status_errors(current, "1.0.7", release))


if __name__=='__main__':unittest.main()

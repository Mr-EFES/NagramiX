"""Preserve published annotations while validating the complete release catalog."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate_release_metadata import ANNOTATION,annotation_errors


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


if __name__=='__main__':unittest.main()

"""Регрессии чтения Swift UI-строк, включая raw/multiline и интерполяцию."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from localization_literals import canonical,literals


def values(source):return [canonical(parts) for _,_,parts in literals(source)]


class SwiftLiterals(unittest.TestCase):
    def test_comments(self):
        self.assertEqual(values('/* title: "skip" /* nested */ */ let text = "shown" // "skip"'),['shown'])

    def test_interpolation(self):
        source=r'"Загрузка \(String(format: "%.1f", value))%"'
        self.assertEqual(values(source),['Загрузка %1$@%%'])

    def test_raw(self):
        self.assertEqual(values(r'##"A \n \##(value)"##'),[r'A \n %1$@'])

    def test_raw_unicode(self):
        self.assertEqual(values(r'#"\#u{41} \u{42}"#'),[r'A \u{42}'])

    def test_multiline(self):
        self.assertEqual(values('"""\n    Hello\n    world\n    """'),['Hello\nworld'])

    def test_multiline_interpolation_spacing(self):
        self.assertEqual(values('"""\n    Hello \\(name)    world\n    """'),['Hello %1$@    world'])

    def test_raw_multiline(self):
        self.assertEqual(values('##"""\n    \"Raw\" \\##(value)\n    """##'),['"Raw" %1$@'])

    def test_escapes(self):
        self.assertEqual(values(r'"\u{1F399}\n\"Test\" \\"'),['🎙\n"Test" \\'])

    def test_nested_comment_interpolation(self):
        self.assertEqual(values(r'"Value \(foo(/* ) */ value))"'),['Value %1$@'])

    def test_invalid(self):
        for source in ['"unfinished','/* unterminated',r'"\(x"']:
            with self.subTest(source=source),self.assertRaises(ValueError):values(source)

if __name__=='__main__':unittest.main()

"""Пакетные регрессии шрифтов без сборки приложения."""
import io,json,plistlib,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate_ipa_fonts import validate_font_resources
from validate_unsigned_ipa import expected_nagramix_catalogs
ROOT=Path(__file__).resolve().parents[2];PREFIX='Payload/Telegram.app/';BUNDLE=PREFIX+'Frameworks/TelegramUIFramework.framework/NagramiXFontsResources.bundle/'

class FontsPackageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=json.loads((ROOT/'ios/app_font_selection_patches.json').read_text())
  cls.resources={Path(n).name:(ROOT/'ios'/item['source']).read_bytes() for n,item in cls.plan['copies'].items() if '/Resources/' in n}
 def archive(self,mutate=None):
  resources=dict(self.resources)
  if mutate:mutate(resources)
  buffer=io.BytesIO()
  with zipfile.ZipFile(buffer,'w') as archive:
   archive.writestr(BUNDLE+'Info.plist',plistlib.dumps({'CFBundleIdentifier':'com.mr-efes.nagramix.fonts'}))
   for name,data in resources.items():archive.writestr(BUNDLE+name,data)
  buffer.seek(0);return zipfile.ZipFile(buffer)
 def test_complete(self):
  with self.archive() as a:self.assertEqual(validate_font_resources(a,PREFIX)['faces'],20)
 def test_missing_face(self):
  with self.archive(lambda d:d.pop('PTAstraSans-Regular.ttf')) as a:
   with self.assertRaises(AssertionError):validate_font_resources(a,PREFIX)
 def test_corrupt_face(self):
  with self.archive(lambda d:d.update({'Roboto-Regular.ttf':b'wrong'})) as a:
   with self.assertRaises(AssertionError):validate_font_resources(a,PREFIX)
 def test_missing_license(self):
  with self.archive(lambda d:d.pop('Roboto-LICENSE.txt')) as a:
   with self.assertRaises(AssertionError):validate_font_resources(a,PREFIX)
 def test_unapproved_font(self):
  with self.archive(lambda d:d.update({'Unapproved.ttf':b'wrong'})) as a:
   with self.assertRaises(AssertionError):validate_font_resources(a,PREFIX)
 def test_versioned_catalogs(self):
  previous=expected_nagramix_catalogs('0.9.4');new=expected_nagramix_catalogs('0.9.5')
  self.assertEqual(expected_nagramix_catalogs('0.10.0'),expected_nagramix_catalogs('0.9.6'))
  self.assertEqual(expected_nagramix_catalogs('0.9.100'),expected_nagramix_catalogs('0.9.6'))
  self.assertEqual(set(previous),set(new));self.assertEqual(len(new),71)
  for code,values in new.items():
   self.assertEqual(len(values),647)
   self.assertEqual({k:v for k,v in values.items() if not k.startswith('NagramiX.Fonts.')},previous[code])
  self.assertEqual(new['ru']['NagramiX.Fonts.Title'],'Шрифты')
  self.assertEqual(new['en']['NagramiX.Fonts.Title'],'Fonts')
 def test_preview_catalogs_preserve_published_095(self):
  published=expected_nagramix_catalogs('0.9.5');next_release=expected_nagramix_catalogs('0.9.6')
  self.assertEqual(len(next_release),71)
  keys={'NagramiX.Fonts.Comparison','NagramiX.Fonts.Current','NagramiX.Fonts.Choose'}
  for code,values in next_release.items():
   self.assertEqual(len(values),650);self.assertEqual(values.keys()-published[code].keys(),keys)
   previous={k:v for k,v in values.items() if k not in keys}
   if code=='ru':previous['NagramiX.Fonts.Licenses']='Лицензии шрифтов'
   self.assertEqual(previous,published[code])
  self.assertEqual(next_release['ru']['NagramiX.Fonts.Licenses'],'Лицензия шрифтов')
if __name__=='__main__':unittest.main()

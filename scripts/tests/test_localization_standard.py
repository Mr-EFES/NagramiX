"""Проверить блокировку новых непереведённых настроек и debug-пунктов."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate_localization_standard import OVERLAY,UI_CATALOG,catalog_contract,source_contract


class LocalizationStandard(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.source=Path(self.temp.name)
        plan=json.loads((OVERLAY/'app_language_localization_patches.json').read_text())
        for name in plan['outputs']:
            if name.endswith('.swift'):self.write(name,'// boundary fixture\n')
        self.write('submodules/NagramiXCore/Resources/en.lproj/Localizable.strings',
                   '"Known.Key" = "Known";\n"NagramiX.Debug.Example" = "Example";\n'+json.dumps(UI_CATALOG['Качественные кружки']['key'])+' = "Quality";\n')

    def tearDown(self):self.temp.cleanup()
    def write(self,name,text):
        path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    def check_source(self,text,path='submodules/SettingsUI/Sources/NagramiXNewFeature.swift',reject=False):
        self.write(path,text)
        if reject:
            with self.assertRaises(ValueError):source_contract(self.source)
        else:source_contract(self.source)

    def test_new_checkbox_english(self):self.check_source('Row(title: "New Checkbox")',reject=True)
    def test_new_checkbox_russian(self):self.check_source('Row(title: "Новый переключатель")',reject=True)
    def test_raw_literal(self):self.check_source('Row(title: #"Raw Checkbox"#)',reject=True)
    def test_multiline(self):self.check_source('label.text = """\n    Another label\n    """',reject=True)
    def test_new_debug(self):self.check_source('strings.nagramiXDebugLocalized("New Debug Item")',reject=True)
    def test_known_debug(self):self.check_source('strings.nagramiXDebugLocalized("Example")')
    def test_known_key(self):self.check_source('Row(title: strings.nagramiXLocalized("Known.Key"))')
    def test_missing_key(self):self.check_source('Row(title: strings.nagramiXLocalized("Missing.Key"))',reject=True)
    def test_known_adapter(self):self.check_source('Row(title: strings.nagramiXUILocalized("Качественные кружки"))')
    def test_new_adapter(self):self.check_source('Row(title: strings.nagramiXUILocalized("Ещё неизвестная подпись"))',reject=True)
    def test_setter(self):self.check_source('button.setTitle("New title", for: .normal)',reject=True)
    def test_swiftui(self):self.check_source('Text("New title")',reject=True)
    def test_model_error(self):self.check_source('return "Новая неизвестная ошибка"',path='submodules/NagramiXModels/Sources/Model.swift',reject=True)
    def test_comments(self):self.check_source('// Row(title: "not UI")\n/* nested /* Row(title: "skip") */ */')
    def test_localized_raw_literal(self):self.check_source('Row(title: strings.nagramiXUILocalized(#"Качественные кружки"#))')
    def test_brand(self):self.check_source('Row(title: "Telegram Premium")',path='submodules/NagramiXTranscription/Sources/Preferences.swift')
    def test_no_expansion_of_reviewed_count(self):self.check_source('Row(title: "Telegram Premium");Row(title: "Telegram Premium")',path='submodules/NagramiXTranscription/Sources/Preferences.swift',reject=True)
    def test_other_module_is_scanned(self):self.check_source('let text = "New feature"',path='submodules/NagramiXAnotherFeature/Sources/Controller.swift',reject=True)

    def translated(self,change=None):
        english={'Known.Key':'Known','NagramiX.Debug.Example':'Example',UI_CATALOG['Качественные кружки']['key']:'Quality'}
        values={key:'Übersetzung '+text for key,text in english.items()}
        if change:change(values,english)
        self.write('submodules/NagramiXCore/Resources/de.lproj/Localizable.strings',''.join(json.dumps(k)+' = '+json.dumps(v,ensure_ascii=False)+';\n' for k,v in values.items()))

    def test_complete_catalogs(self):
        self.translated();self.assertEqual(catalog_contract(self.source,{'en','de'}),(2,3))

    def test_missing_language(self):
        with self.assertRaisesRegex(ValueError,'отсутствуют'):catalog_contract(self.source,{'en','de'})

    def test_missing_new_key_in_final_tree(self):
        self.translated(lambda v,e:v.pop('Known.Key'))
        with self.assertRaisesRegex(ValueError,'ключей'):catalog_contract(self.source,{'en','de'})

    def test_english_copy_is_not_a_translation(self):
        self.translated(lambda v,e:v.update(e))
        with self.assertRaisesRegex(ValueError,'копия'):catalog_contract(self.source,{'en','de'})

    def test_placeholder_rejected(self):
        self.translated(lambda v,e:v.update({'Known.Key':'Argument %1$@'}))
        with self.assertRaisesRegex(ValueError,'Аргументы'):catalog_contract(self.source,{'en','de'})

    def test_empty_translation(self):
        self.translated(lambda v,e:v.update({'Known.Key':'  '}))
        with self.assertRaisesRegex(ValueError,'Пустой'):catalog_contract(self.source,{'en','de'})

    def test_translation_stub(self):
        self.translated(lambda v,e:v.update({'Known.Key':'TODO_TRANSLATE Known'}))
        with self.assertRaisesRegex(ValueError,'заглушка'):catalog_contract(self.source,{'en','de'})

if __name__=='__main__':unittest.main()

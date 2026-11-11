"""Добавить утверждённый выбор шрифтов приложения и лицензированный встроенный набор."""
import hashlib
import json
from pathlib import Path


def apply_app_font_selection(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'app_font_selection_patches.json').read_text())
    expected_inputs = {'submodules/NagramiXCore/Resources/tk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/af.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ur.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings', 'submodules/TelegramPresentationData/Sources/PresentationData.swift', 'submodules/NagramiXCore/Resources/da.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ml.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/de.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ja.lproj/Localizable.strings', 'submodules/Display/BUILD', 'submodules/NagramiXCore/Resources/cs.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/az.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ro.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/te.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ca.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sq.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eo.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ko.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/mt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/et.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/my.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-pt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-br.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/es.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/uz.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sw.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/vi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fa.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/he.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/uk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ms.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ga.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ar.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/el.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fil.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/am.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/it.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ka.lproj/Localizable.strings', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/NagramiXCore/Resources/zh-hans.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ne.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/th.lproj/Localizable.strings', 'submodules/Display/Source/Font.swift', 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hy.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/id.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/or.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ta.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/km.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/mr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nb.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/zh-hant.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/be.lproj/Localizable.strings'}
    required_guards = {'submodules/Display/Source/ViewController.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift', 'submodules/TelegramPresentationData/BUILD', 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift', 'submodules/NagramiXMediaSettings/BUILD', 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', 'submodules/SettingsUI/BUILD', 'submodules/NagramiXTranscription/Sources/Runtime.swift', 'submodules/TelegramPresentationData/Sources/PresentationTheme.swift', 'submodules/ItemListUI/Sources/Items/ItemListSwitchItem.swift', 'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/NagramiXTranscription/Sources/Settings.swift', 'submodules/TelegramUI/Sources/SharedMediaPlayer.swift', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift', 'submodules/ItemListUI/Sources/Items/ItemListDisclosureItem.swift'}
    expected_copies = {'submodules/Display/Resources/NagramiXFonts/Roboto-NOTICE.txt', 'submodules/Display/Resources/NagramiXFonts/Roboto-Italic.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSerif-Bold.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSerif-Italic.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-Regular.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-Medium.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-Thin.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSans-Regular.ttf', 'submodules/Display/Source/NagramiXFontManager.swift', 'submodules/Display/Resources/NagramiXFonts/PTAstraSans-Italic.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSans-BoldItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSerif-LICENSE.txt', 'submodules/Display/Resources/NagramiXFonts/PTAstraSans-LICENSE.txt', 'submodules/Display/Resources/NagramiXFonts/PTAstraSerif-Regular.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-Light.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-LightItalic.ttf', 'submodules/SettingsUI/Sources/NagramiXFontsController.swift', 'submodules/Display/Resources/NagramiXFonts/Roboto-ThinItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSans-Bold.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-BoldItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-LICENSE.txt', 'submodules/Display/Resources/NagramiXFonts/Roboto-Bold.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-BlackItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-MediumItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/PTAstraSerif-BoldItalic.ttf', 'submodules/Display/Resources/NagramiXFonts/Roboto-Black.ttf', 'submodules/NagramiXMediaSettings/Sources/NagramiXFontSettings.swift'}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'transcription_account_defaults'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('app_font_selection: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('app_font_selection: unsafe path ' + name)
        if any((root / Path(*relative.parts[:index])).is_symlink() for index in range(1, len(relative.parts) + 1)):
            raise SystemExit('app_font_selection: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('app_font_selection: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('app_font_selection: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('app_font_selection: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('app_font_selection: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('app_font_selection: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('app_font_selection: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('app_font_selection: invalid copy record ' + name)
        path = safe(source, name)
        if path.exists() or path.is_symlink():
            raise SystemExit('app_font_selection: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in path.parents if parent != source.parent):
            raise SystemExit('app_font_selection: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        path = safe(source, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

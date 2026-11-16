"""Единая видимость вкладок и меню скрытия; весь preflight до записи."""
import hashlib
import json
from pathlib import Path


def apply_tab_visibility_sync(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'tab_visibility_sync_patches.json').read_text())
    expected_inputs = {'submodules/NagramiXCore/Resources/mt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fil.lproj/Localizable.strings', 'submodules/TelegramUI/Sources/TelegramRootController.swift', 'submodules/NagramiXCore/Resources/sk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/az.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/or.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/id.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ca.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ro.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fa.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/he.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/th.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sw.lproj/Localizable.strings', 'submodules/TelegramUI/Components/TabBarComponent/Sources/TabBarComponent.swift', 'submodules/NagramiXCore/Resources/hy.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ur.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/it.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/uz.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nb.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/am.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/da.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/et.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ar.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ne.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eo.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/te.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/af.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ja.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/zh-hans.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ms.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fr.lproj/Localizable.strings', 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', 'submodules/NagramiXCore/Resources/ml.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nl.lproj/Localizable.strings', 'submodules/ContactListUI/Sources/ContactsController.swift', 'submodules/NagramiXCore/Resources/uk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ga.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ka.lproj/Localizable.strings', 'submodules/ContactListUI/Sources/ContactsControllerNode.swift', 'submodules/NagramiXCore/Resources/vi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/be.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/el.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings', 'submodules/TabBarUI/Sources/TabBarContollerNode.swift', 'submodules/NagramiXCore/Resources/km.lproj/Localizable.strings', 'submodules/TabBarUI/Sources/TabBarController.swift', 'submodules/NagramiXCore/Resources/zh-hant.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/de.lproj/Localizable.strings', 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift', 'submodules/NagramiXCore/Resources/tk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/mr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/my.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sq.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/es.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-pt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/cs.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ko.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ta.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-br.lproj/Localizable.strings'}
    required_guards = {'submodules/TabBarUI/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Disposable.swift', 'submodules/NagramiXCore/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Mapping.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Atomic.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Meta.swift', 'submodules/ContactListUI/BUILD', 'submodules/Display/Source/ViewController.swift', 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift', 'submodules/TelegramUIPreferences/Sources/CallListSettings.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Queue.swift', 'submodules/TelegramUI/BUILD', 'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Single.swift', 'submodules/CallListUI/Sources/CallListController.swift', 'submodules/TabBarUI/Sources/TabBarNode.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Signal.swift', 'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift', 'submodules/TelegramUI/Components/TabBarComponent/BUILD', 'submodules/SSignalKit/SwiftSignalKit/Source/Subscriber.swift'}
    expected_copies = set()
    expected_native_inputs = {'submodules/ContactListUI/Sources/ContactsControllerNode.swift': 'c3965b20e4feca3be390b0d62b0d09efb581a87d'}
    expected_native_guards = {}
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'round_video_encoding'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or set(plan['copies']) != expected_copies or plan['deletions']
        or set(plan['guards']) != required_guards
        or set(plan['guard_sources']) != set(plan['guards'])
        or plan.get('native_inputs', {}) != expected_native_inputs
        or plan.get('native_guards', {}) != expected_native_guards):
        raise SystemExit('tab_visibility_sync: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('tab_visibility_sync: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('tab_visibility_sync: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('tab_visibility_sync: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('tab_visibility_sync: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('tab_visibility_sync: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('tab_visibility_sync: guard mismatch ' + name)
    for name, expected in plan['native_guards'].items():
        data = checked(source, name, plan['guards'][name])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected:
            raise SystemExit('tab_visibility_sync: native guard origin ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('tab_visibility_sync: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('tab_visibility_sync: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    for name, item in plan['copies'].items():
        if set(item) != {'source', 'sha256'}:
            raise SystemExit('tab_visibility_sync: invalid copy record ' + name)
        destination = safe(source, name)
        if destination.exists() or destination.is_symlink():
            raise SystemExit('tab_visibility_sync: existing copy ' + name)
        if any(parent.exists() and not parent.is_dir() for parent in destination.parents if parent != source.parent):
            raise SystemExit('tab_visibility_sync: invalid copy parent ' + name)
        prepared[name] = template(item['source'], item['sha256'])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        destination = safe(source, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

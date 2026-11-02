#!/usr/bin/env python3
"""Проверка явного просмотра одной истории; SDK и сервер проверяются отдельно."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

from validate_contact_chat_readiness import KIT, NATIVE
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/'
ITEM = PREFIX + 'Sources/StoryItemSetContainerComponent.swift'
SCREEN = PREFIX + 'Sources/StoryContainerScreen.swift'
CORE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Stories.swift'
ENGINE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--upstream', type=Path)
    args = parser.parse_args()
    from validate_media_privacy_fixes import delegate_if_applied
    if delegate_if_applied(args, __file__): return
    overlay = ROOT / 'ios'
    plan = json.loads((overlay / 'story_explicit_view_patches.json').read_text())
    expected = {**plan['guards'], **plan['outputs']}
    quality = json.loads((overlay / 'story_download_quality_patches.json').read_text())
    icons = json.loads((overlay / 'story_icon_consistency_patches.json').read_text())
    has_icons = sha((args.source/ITEM).read_bytes()) == icons['outputs'][ITEM]
    has_quality = has_icons or sha((args.source/ITEM).read_bytes()) == quality['outputs'][ITEM]
    if has_quality:
        expected.update(quality['outputs'])
    if has_icons:
        expected.update(icons['outputs'])
    for name, digest in expected.items():
        assert sha((args.source/name).read_bytes()) == digest, name
    for name, digest in plan['templates'].items():
        assert sha((overlay/name).read_bytes()) == digest, name
    for name, entry in plan['copies'].items():
        assert sha((args.source/name).read_bytes()) == entry['sha256'], name

    after = {name: (args.source/name).read_text() for name in plan['outputs']}
    if has_icons:
        for name, old, new, count in reversed(icons['patches']):
            assert after[name].count(new) == count
            after[name] = after[name].replace(new, old, count)
        assert sha(after[ITEM].encode()) == quality['outputs'][ITEM]
    if has_quality:
        for name, old, new, count in reversed(quality['patches']):
            assert after[name].count(new) == count
            after[name] = after[name].replace(new, old, count)
        assert sha(after[ITEM].encode()) == plan['outputs'][ITEM]
    before = dict(after)
    for name, old, new, count in reversed(plan['patches']):
        assert before[name].count(new) == count, name
        before[name] = before[name].replace(new, old, count)
    for name, text in before.items():
        assert sha(text.encode()) == plan['inputs'][name], name
    # Автоматические чтения, approval/cancel и сохранение историй не меняются.
    for name, markers in {
        CORE: ['func _internal_markStoryAsSeen('],
        SCREEN: ['fileprivate func nagramiXCanMarkStoryAsSeen(', 'fileprivate func nagramiXConfirmNavigation(',
                 'private func nagramiXUsesAnonymousViewing('],
        ITEM: ['private func requestSave('],
    }.items():
        for marker in markers:
            assert block(before[name], marker) == block(after[name], marker), marker
    method = block(after[CORE], 'func _internal_nagramiXRecordStoryView(')
    assert method == (overlay/'story_explicit_view/Core.swift.inc').read_text().split('\n', 1)[1].rstrip()
    assert 'incrementStoryViews(peer: inputPeer, id: [id])' in method
    assert all(s not in method for s in ['readStories(', 'maxReadId', 'setPeerStoryState', 'NagramiXStorySettings', 'SynchronizeViewStories'])
    view = after[ITEM]
    assert view.count('items.append(self.nagramiXRecordViewItem(component))') == 2
    assert view.count('component.strings.Story_ContextStealthMode') == before[ITEM].count('component.strings.Story_ContextStealthMode') == 2
    assert 'self.nagramiXViewDisclosure.status(for: self.nagramiXViewDisclosureKey) != .recorded' in view
    assert 'fileprivate let nagramiXViewDisclosure = NagramiXStoryViewDisclosure()' in after[SCREEN]
    for lang in ['ru', 'en']:
        text = after[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings']
        for key in ['RecordView', 'RecordingView', 'ViewRecorded', 'RecordViewFailed', 'ServerStealthActive']:
            assert text.count('"NagramiX.Story.' + key + '" =') == 1
    print('PASS: exact source/templates, both menus, explicit one-ID RPC, unchanged automatic privacy/approval/read/save paths')

    # Ошибки preflight не должны оставлять частично применённую правку.
    spec = importlib.util.spec_from_file_location('story_explicit_view', overlay/'story_explicit_view.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        def seed(source):
            for name in {**plan['guards'], **plan['inputs']}:
                path = source/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(before[name]) if name in before else path.write_bytes((args.source/name).read_bytes())
        def snapshot(source):
            return {str(p.relative_to(source)): sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
        def reject(source, root):
            saved = snapshot(source)
            try: module.apply_story_explicit_view(source, root)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError('preflight accepted drift')
            assert snapshot(source) == saved
        valid = temp/'valid'; seed(valid); module.apply_story_explicit_view(valid, overlay)
        for name in plan['outputs']:
            assert (valid/name).read_text() == after[name]
        for name in plan['copies']:
            assert (valid/name).read_bytes() == (args.source/name).read_bytes()
        reject(valid, overlay)
        for i, name in enumerate({**plan['inputs'], **plan['guards']}):
            bad = temp/f'input-{i}'; seed(bad); (bad/name).write_text('// drift'); reject(bad, overlay)
        for variant in ['output', 'anchor', 'path', 'template', 'collision']:
            bad = temp/variant; seed(bad)
            custom_overlay = temp/(variant+'-overlay'); custom_overlay.mkdir()
            custom = json.loads(json.dumps(plan))
            for name in plan['templates']:
                path = custom_overlay/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((overlay/name).read_bytes())
            if variant == 'output': custom['outputs'][next(iter(custom['outputs']))] = '0'*64
            elif variant == 'anchor': custom['patches'][-1][1] += '// drift'
            elif variant == 'path': custom['inputs']['../outside'] = '0'*64; custom['outputs']['../outside'] = '0'*64
            elif variant == 'template': (custom_overlay/next(iter(custom['templates']))).write_text('// drift')
            else:
                path = bad/next(iter(custom['copies'])); path.parent.mkdir(parents=True, exist_ok=True); path.write_text('// existing')
            (custom_overlay/'story_explicit_view_patches.json').write_text(json.dumps(custom))
            reject(bad, custom_overlay)
        print('PASS: guarded stage rejects input/template/anchor/output/path/collision drift without partial writes')

        if args.swiftc:
            upstream = args.upstream or args.source
            signal = []
            for name in NATIVE + ['Signal_Catch.swift']:
                text = (upstream/(KIT+name)).read_text()
                if name == 'Signal_Meta.swift': text = 'import CoreFoundation\n'+text
                path = temp/name; path.write_text(text); signal.append(path)
            boundary = (ROOT/'scripts/tests/NagramiXStoryExplicitViewBoundary.swift').read_text()
            engine = block(after[ENGINE], 'public func nagramiXRecordStoryView(').replace('public func', 'func').replace('EnginePeer.Id', 'PeerId')
            properties = '\n'.join(block(view, marker) for marker in ['var nagramiXViewDisclosureKey:', 'var nagramiXUsesAnonymousViewing:'])
            methods = (overlay/'story_explicit_view/Menu.swift.inc').read_text().replace('private func', 'func')
            boundary = boundary.replace('// ENGINE_METHOD', engine).replace('// COMPONENT_PROPERTIES', properties).replace('// MENU_METHODS', methods)
            harness = temp/'Boundary.swift'; harness.write_text(boundary+'\n'+method)
            helper = args.source/next(iter(plan['copies']))
            for flags in [[], ['-O']]:
                subprocess.run([str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(temp/'cache'), *flags,
                    *map(str, signal), str(harness), str(helper), str(ROOT/'scripts/tests/NagramiXStoryExplicitViewTests.swift'),
                    '-o', str(temp/'tests')], check=True)
                subprocess.run([str(temp/'tests')], check=True, timeout=30)
            subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.source/name)
                for name in list(plan['outputs'])+list(plan['copies']) if name.endswith('.swift')]], check=True)
    print('PASS: story explicit view; Apple SDK/physical iPhone/Telegram server pending')


if __name__ == '__main__':
    main()

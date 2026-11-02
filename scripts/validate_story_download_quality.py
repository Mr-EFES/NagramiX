#!/usr/bin/env python3
"""Проверить лучшее доступное качество явного сохранения историй."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/'
ITEM = PREFIX+'Sources/StoryItemSetContainerComponent.swift'
SAVER = 'submodules/SaveToCameraRoll/Sources/NagramiXStorySave.swift'

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--upstream', type=Path)
    args = parser.parse_args()
    from validate_media_privacy_fixes import delegate_if_applied
    if delegate_if_applied(args, __file__): return
    overlay = ROOT/'ios'
    plan = json.loads((overlay/'story_download_quality_patches.json').read_text())
    icons = json.loads((overlay/'story_icon_consistency_patches.json').read_text())
    has_icons = sha((args.source/ITEM).read_bytes()) == icons['outputs'][ITEM]
    expected = {**plan['guards'], **plan['outputs']}
    if has_icons: expected.update(icons['outputs'])
    for name, digest in expected.items():
        assert sha((args.source/name).read_bytes()) == digest, name
    for name, digest in plan['templates'].items():
        assert sha((overlay/name).read_bytes()) == digest, name
    for name, item in plan['copies'].items():
        assert sha((args.source/name).read_bytes()) == item['sha256'], name
    final = (args.source/ITEM).read_text()
    if has_icons:
        for name, a, b, count in reversed(icons['patches']):
            assert final.count(b) == count
            final = final.replace(b, a, count)
        assert sha(final.encode()) == plan['outputs'][ITEM]
    old = final
    for name, a, b, count in reversed(plan['patches']):
        assert name == ITEM and old.count(b) == count
        old = old.replace(b, a, count)
    assert sha(old.encode()) == plan['inputs'][ITEM]
    for marker in ['private var nagramiXCanDownloadStory:', 'private func requestSave(',
                   'private func nagramiXRecordView(', 'private func nagramiXRecordViewItem(']:
        assert block(old, marker) == block(final, marker), marker
    download = block(final, '@objc private func nagramiXDownloadStoryPressed(')
    assert download.index('nagramiXBestStoryMediaForSaving(item)') < download.index('nagramiXSaveStoryToCameraRoll(')
    assert 'id: item.id, media: media._asMedia()' in download
    assert final.count('self.nagramiXDownloadStoryPressed()') == old.count('self.nagramiXDownloadStoryPressed()')
    saver = (args.source/SAVER).read_text()
    assert 'largestImageRepresentation(image.representations)' in saver
    assert 'resource = file.resource' in saver
    assert 'FileManager.default.linkItem(atPath: data.path, toPath: temporary.path)' in saver
    assert 'FileManager.default.copyItem(atPath: data.path, toPath: temporary.path)' in saver
    assert 'PHAssetCreationRequest.forAsset().addResource(' in saver
    helper = (overlay/'story_download_quality/Quality.swift').read_text()
    assert all(word not in helper for word in ['preferHighQuality', 'UserDefaults', 'isPremium', 'readStories', 'markStoryAsSeen', 'AVAssetExportSession'])
    print('PASS: exact quality integration, original bytes saver, snapshot/menu/OFF/privacy/explicit-view paths retained')
    spec = importlib.util.spec_from_file_location('story_download_quality', overlay/'story_download_quality.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        def seed(root):
            for name in {**plan['inputs'], **plan['guards']}:
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(old) if name == ITEM else path.write_bytes((args.source/name).read_bytes())
        def manifest(root): return {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
        def reject(root):
            snapshot = manifest(root)
            try: module.apply_story_download_quality(root, overlay)
            except SystemExit: pass
            else: raise AssertionError('accepted source drift')
            assert manifest(root) == snapshot
        valid = temp/'valid'; seed(valid); module.apply_story_download_quality(valid, overlay)
        assert (valid/ITEM).read_text() == final
        reject(valid)
        for i,name in enumerate({**plan['inputs'],**plan['guards']}):
            target=temp/str(i);seed(target);(target/name).write_text('// drift');reject(target)
        target=temp/'collision';seed(target)
        path=target/next(iter(plan['copies']));path.parent.mkdir(parents=True,exist_ok=True);path.write_text('// existing');reject(target)
        if args.swiftc:
            production = temp/'Quality.swift'; production.write_text(helper.replace('import TelegramCore\n', ''))
            upstream = args.upstream or args.source
            source = (upstream/'submodules/TelegramCore/Sources/Utils/ImageRepresentationsUtils.swift').read_text()
            photo = temp/'Photo.swift'; photo.write_text(block(source, 'public func largestImageRepresentation(').replace('public func', 'func'))
            for flags in [[], ['-O']]:
                subprocess.run([str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(temp/'cache'), *flags,
                    str(ROOT/'scripts/tests/NagramiXStoryDownloadQualityBoundary.swift'), str(production), str(photo),
                    str(ROOT/'scripts/tests/NagramiXStoryDownloadQualityTests.swift'), '-o', str(temp/'tests')], check=True)
                subprocess.run([str(temp/'tests')], check=True)
            # Негативная регрессия: сохранение первой уменьшенной альтернативы.
            production.write_text('func nagramiXBestStoryMediaForSaving(_ item: EngineStoryItem) -> EngineMedia { item.alternativeMediaList.first ?? item.media }')
            subprocess.run([str(args.swiftc), '-O', '-module-cache-path', str(temp/'cache'),
                str(ROOT/'scripts/tests/NagramiXStoryDownloadQualityBoundary.swift'), str(production), str(photo),
                str(ROOT/'scripts/tests/NagramiXStoryDownloadQualityTests.swift'), '-o', str(temp/'bad')], check=True)
            result = subprocess.run([str(temp/'bad')], capture_output=True)
            assert result.returncode != 0
            print('PASS: selecting first low-quality alternative is rejected during execution')
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source/ITEM),
                            str(args.source/next(iter(plan['copies'])))], check=True)
    print('PASS: story download quality, fail-closed guards; Apple SDK/server/Photos pending')

if __name__ == '__main__': main()

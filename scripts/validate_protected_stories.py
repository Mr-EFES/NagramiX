#!/usr/bin/env python3
"""Exercise protected-story actions, live capture policy and gallery export gates.

UIKit/AVFoundation, media rendering/fetching and Photos remain API boundaries.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from validate_quick_format import ROOT, block, manifest

STORIES = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/'
VIEW = STORIES + 'Sources/StoryItemSetContainerComponent.swift'
IMAGE = STORIES + 'Sources/StoryItemImageView.swift'
CONTENT = STORIES + 'Sources/StoryItemContentComponent.swift'
SCREEN = STORIES + 'Sources/StoryContainerScreen.swift'
MESSAGE_POLICY = 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift'
GALLERY_POLICY = 'submodules/GalleryUI/Sources/NagramiXGallerySavePolicy.swift'


def strip_imports(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import '))


def production(before, after):
    old, new = (before / VIEW).read_text(), (after / VIEW).read_text()
    image = (after / IMAGE).read_text().split('final class CaptureProtectedInfoComponent:', 1)[0]
    baseline_image = (before / IMAGE).read_text().split('final class CaptureProtectedInfoComponent:', 1)[0]
    boundary = (ROOT / 'scripts/tests/NagramiXProtectedStoryBoundary.swift').read_text()
    boundary = boundary.replace('// ACTUAL_MESSAGE_ELIGIBILITY', block((after / MESSAGE_POLICY).read_text(), 'var nagramiXAllowsContentCopy:'))
    lifecycle = block(image, 'override init(frame: CGRect)') + '\n' + block(image, 'deinit {')
    boundary = boundary.replace('// ACTUAL_IMAGE_LIFECYCLE', lifecycle)
    boundary = boundary.replace('// ACTUAL_IMAGE_PROTECTION', block(image, 'private func updateImage('))
    boundary = boundary.replace('// ACTUAL_LEGACY_IMAGE_PROTECTION', block(baseline_image, 'private func updateImage('))
    start = image.index('        self.nagramiXCaptureUpdate = ', image.index('    func update(context:'))
    end = image.index('        var dimensions: CGSize?', start)
    boundary = boundary.replace('// ACTUAL_IMAGE_UPDATE_PREAMBLE', image[start:end])
    boundary = boundary.replace('// ACTUAL_STORY_ELIGIBILITY', block(new, 'private var nagramiXCanDownloadStory:'))
    boundary = boundary.replace('// ACTUAL_BASELINE_STORY_ELIGIBILITY',
        block(old, 'private var nagramiXCanDownloadStory:').replace('nagramiXCanDownloadStory', 'baselineCanDownloadStory', 1))
    boundary = boundary.replace('// ACTUAL_SAVE_DISPATCH', block(block(new, 'private func requestSave('), 'if self.nagramiXCanDownloadStory {'))
    visibility = re.findall(r'} else if ([^\n]*self\.nagramiXCanDownloadStory) {\n +let saveText:', new)
    assert len(visibility) == 1
    boundary = boundary.replace('/* ACTUAL_MENU_VISIBILITY */', visibility[0])
    start = new.index('                        let nagramiXCanSaveStory = ')
    end = new.index('                    if case .user = component.slice.effectivePeer, !isLiveStream {', start)
    action = block(new[start:end], 'action: { [weak self] _, a in')
    action = action.replace('action: { [weak self] _, a in', 'let action: (Int?, (MenuDismiss) -> Void) -> Void = { [weak self] _, a in', 1)
    boundary = boundary.replace('// ACTUAL_MENU_ACTION', action)
    assert '// ACTUAL_' not in boundary
    video = re.findall(r'nagramiXAllowsScreenshotBypass: (true|false),', (after / CONTENT).read_text())
    assert video == ['true']
    return boundary, '\n'.join([
        'import Foundation',
        strip_imports((after / 'submodules/Display/Source/NagramiXCaptureProtection.swift').read_text()),
        strip_imports((after / GALLERY_POLICY).read_text()),
        'func storyVideoAllowsScreenshotBypass() -> Bool { return ' + video[0] + ' }',
    ])


def validate(args):
    plan = json.loads((ROOT / 'ios/protected_stories_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert {n for n in before if before[n] != after.get(n)} == set(plan['inputs'])
    assert after.keys() - before.keys() == plan['copies'].keys()
    assert not before.keys() - after.keys()
    assert all(before[n] == sha for n, sha in {**plan['guards'], **plan['inputs']}.items())
    assert all(after[n] == sha for n, sha in plan['outputs'].items())
    # These preserve session incognito/read/approval, the saver and message
    # protection exclusions; the new path doesn't edit source protection flags.
    for n in [SCREEN, MESSAGE_POLICY, 'submodules/SaveToCameraRoll/Sources/NagramiXStorySave.swift',
              'submodules/Display/Source/NagramiXCaptureProtection.swift',
              'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift']:
        assert (args.before / n).read_bytes() == (args.after / n).read_bytes(), n
    old, new = (args.before / VIEW).read_text(), (args.after / VIEW).read_text()
    marker = '            guard let component = self.component, let peerReference = PeerReference(component.slice.effectivePeer) else {'
    a, b = block(old, 'private func requestSave('), block(new, 'private func requestSave(')
    assert a[a.index(marker):] == b[b.index(marker):]
    assert block(old, '@objc private func nagramiXDownloadStoryPressed(') == block(new, '@objc private func nagramiXDownloadStoryPressed(')
    assert '"//submodules/NagramiXMediaSettings:NagramiXMediaSettings"' in (args.after / (STORIES + 'BUILD')).read_text()
    executions = []
    with tempfile.TemporaryDirectory(prefix='protected-stories-') as directory:
        tmp = Path(directory)
        boundary, native = production(args.before, args.after)
        (tmp / 'Boundary.swift').write_text(boundary)
        (tmp / 'Production.swift').write_text(native)
        settings = args.after / 'submodules/NagramiXMediaSettings/Sources'
        sources = [settings / 'NagramiXPrivacySettings.swift', settings / 'NagramiXReadModeSettings.swift',
            args.after / 'submodules/NagramiXCore/Sources/NagramiXStoryDownloadSettings.swift',
            tmp / 'Boundary.swift', tmp / 'Production.swift', ROOT / 'scripts/tests/NagramiXProtectedStoryTests.swift']
        for mode in ['debug', 'optimized']:
            binary = tmp / mode
            command = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'), *map(str, sources), '-o', str(binary)]
            if mode == 'optimized':
                command.insert(1, '-O')
            subprocess.run(command, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(tmp / ('prefs-' + mode)))
            executions.append(dict(mode=mode, output=subprocess.check_output([str(binary)], text=True, env=env, timeout=30).strip()))
            cold_env = dict(os.environ, XDG_CONFIG_HOME=str(tmp / ('cold-' + mode)))
            subprocess.run([str(binary), 'read', 'false', 'false'], env=cold_env, check=True, timeout=15)
            for download, capture in [('true', 'false'), ('false', 'true'), ('true', 'true'), ('false', 'false')]:
                for operation in ['set', 'read']:
                    subprocess.run([str(binary), operation, download, capture], env=cold_env, check=True, timeout=15)
            executions.append(dict(mode=mode, cold_processes=9, result='PASS'))
        swift = [str(args.after / n) for n in list(plan['inputs']) + list(plan['copies']) if n.endswith('.swift')]
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *swift], check=True)
    for n in ['ios/protected_stories.py', 'ios/apply_overlay.py', 'scripts/validate_protected_stories.py']:
        ast.parse((ROOT / n).read_text())
    return dict(execution=executions, original_capture_and_view_policies='preserved',
        native_story_saver='unchanged; same snapshot/lease/Photos-success contract',
        UIKit_AVFoundation='API/lifecycle boundaries, not real rendering or capture', Photos_network='not executed',
        Apple_SDK='pending separate build', physical_iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

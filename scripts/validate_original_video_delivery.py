#!/usr/bin/env python3
"""Exercise file intent, original camera/library movies and Telegram's stock media routes."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

import original_video_gallery_runtime as gallery
from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest

STAGE = 'original_video_delivery'
TESTS = Path(__file__).with_name('tests')


def check(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for path, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / path) == expected, path
    for path in plan['outputs']:
        subprocess.run([swiftc, '-frontend', '-parse', source / path], check=True)

    legacy = (source / gallery.LEGACY).read_text()
    picker = (source / 'submodules/MediaPickerUI/Sources/MediaPickerScreen.swift').read_text()
    assert 'let sendAsFile = asFile || controller.subjectIsFile || controller.subject.isFilesMode' in picker
    assert picker.count('intent: sendAsFile ? TGMediaAssetsControllerSendFileIntent') == 2
    assert picker.count('legacyAssetPickerItemGenerator(forceVideoDocument: sendAsFile)') == 2
    assert legacy.count('asFile = forceVideoDocument || (dict["document"] as? NSNumber)?.boolValue == true') == 2
    assert 'nagramiXPrepareOriginalVideoValue(account: account, value: $0, enabled: enabled)' in legacy
    assert 'appendVideo(file, reference: .standalone(media: file), caption: caption, item: item, asFile: !file.isVideo' in legacy
    files = (source / 'submodules/TelegramUI/Sources/ChatControllerOpenAttachmentMenu.swift').read_text()
    document = files[files.index('var attributes: [TelegramMediaFileAttribute]', files.index('let mimeType = guessMimeTypeByFileExtension((item.fileName')):]
    document = document[:document.index('messages.append(message)')]
    assert '.FileName(fileName: item.fileName)' in document and 'ICloudFileResource(urlData: item.urlData, thumbnail: false)' in document
    assert '.Video(' not in document and 'originalVideos' not in document

    geometry = block(legacy, 'private func nagramiXOriginalVideoMetadata(')
    if sys.platform == 'darwin':
        # Typecheck the actual AVFoundation API against the deployment target.
        api = folder / 'CameraMetadata.swift'
        api.write_text('import AVFoundation\nstruct PixelDimensions { init(_ size: CGSize) {} }\n' + geometry)
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        subprocess.run([swiftc, '-typecheck', '-swift-version', '5', '-warnings-as-errors', '-sdk', sdk, '-target', 'arm64-apple-ios15.0', api], check=True)

    extras = (TESTS / 'NagramiXOriginalDeliveryBoundary.swift').read_text()
    for marker in ['private func nagramiXStoreOriginalVideo(', 'private func nagramiXCameraVideoURL(',
                   'private func nagramiXCameraVideoName(', 'public func nagramiXOriginalCameraVideoFile(',
                   'private func nagramiXOriginalVideoGroupedValues(', 'private func nagramiXOriginalVideoPickerValues(']:
        extras += '\n' + block(legacy, marker)
    single = (source / (gallery.BASE + 'Sources/ChatMediaSendSingleItem.swift')).read_text()
    extras += '\n' + block(single, 'public struct ChatMediaEditorResult').replace('public ', '')
    extras += '\n' + block(single, 'public func chatMediaEditorEnqueueMessages(').replace('public ', '')
    dispatch = (source / 'submodules/SSignalKit/SwiftSignalKit/Source/Signal_Dispatch.swift').read_text()
    extras += '\n' + block(dispatch, 'public func runOn<T, E>(_ queue: Queue)')
    code = gallery.fixture(source, test_name='NagramiXOriginalDeliveryTests.swift', extra_source=extras, camera_branch=True)
    for result in execute(swiftc, folder, 'OriginalVideoDelivery', code):
        print(result['mode'], result['output'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', default='swiftc')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = folder / 'source'
            canonical_projection(source, STAGE)
        check(source, args.swiftc, folder)


if __name__ == '__main__':
    main()

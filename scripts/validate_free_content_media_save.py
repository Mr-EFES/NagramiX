#!/usr/bin/env python3
"""Test the chat and gallery save policy against the persisted privacy and menu settings."""
import argparse
from pathlib import Path
import tempfile

import tab_visibility_runtime as tab
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan

CORE = 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift'
GALLERY = 'submodules/GalleryUI/Sources/NagramiXGallerySavePolicy.swift'
MENU = 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'


def validate(source, swiftc, folder):
    plan = checked_plan('free_content_media_save')
    for name in plan['outputs']:
        run([swiftc, '-frontend', '-parse', source / name], timeout=60)

    gallery_items = source / 'submodules/GalleryUI/Sources/Items'
    for name, receiver, count in [('ChatImageGalleryItem', 'self', 2), ('UniversalVideoGalleryItem', 'item', 5)]:
        item = (gallery_items / (name + '.swift')).read_text()
        assert item.count(f'nagramiXCanSaveGalleryMedia(message, peerIsCopyProtected: {receiver}.peerIsCopyProtected)') == count

    menu = (source / MENU).read_text()
    display = 'let nagramiXProtectedExport = isCopyProtected && nagramiXAllowsProtectedContentExport(message)'
    assert display in menu
    chat_saves = menu.split('if resourceAvailable, (!message.containsSecretMedia', 1)[1].split('var threadId:', 1)[0]
    assert '(!isCopyProtected || nagramiXProtectedExport)' in chat_saves.split('var mediaReference:', 1)[0]
    assert 'if !isCopyProtected || nagramiXProtectedExport {' in chat_saves.split('Conversation_SaveToFiles', 1)[0]
    for action, operation in [('strings.Gallery_SaveImage', 'saveToCameraRoll('),
                              ('strings.Conversation_SaveToFiles', 'controllerInteraction.saveMediaToFiles(')]:
        handler = chat_saves.split(action, 1)[1].split(operation, 1)[0]
        assert '!isCopyProtected || nagramiXAllowsProtectedContentExport(message)' in handler
    for option, command in [('showForwardWithoutAuthor', 'nagramiXForwardWithoutAuthor'),
                            ('showBroadcastMessages', 'nagramiXBroadcastMessages')]:
        assert f'strings.{command},' in block(menu, f'if NagramiXTabSettings.current.{option} {{')

    policy = block((source / CORE).read_text(), 'public func nagramiXAllowsProtectedContentExport(')
    gallery = block((source / GALLERY).read_text(), 'func nagramiXCanSaveGalleryMedia(')
    fixture = folder / 'Save.swift'
    fixture.write_text((tab.ROOT / 'ios/Tests/NagramiXFreeContentMediaSave.swift').read_text()
                       + '\n' + policy + '\n' + gallery + '\n')
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        link, env = tab.modules(source, swiftc, folder / mode, flags)
        binary = folder / ('save-' + mode)
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
             '-module-cache-path', folder / mode / 'cache', *flags, *link, fixture, '-o', binary], timeout=180)
        print(run([binary], env=env, timeout=30).stdout.strip(), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='free-content-media-save-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))

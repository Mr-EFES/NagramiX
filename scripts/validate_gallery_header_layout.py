#!/usr/bin/env python3
"""Check gallery title ownership and place both title capsules against the actual navigation row."""
import argparse
from pathlib import Path
import shutil
import tempfile

from late_source_stages import OVERLAY, ROOT
from validate_local_copy_delivery import execute, run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks

STAGE = 'gallery_header_layout'
GALLERY = Path('submodules/GalleryUI/Sources')
NAVIGATION = 'submodules/TelegramUI/Components/NavigationBarNode/Sources/NavigationBarNode.swift'
PLACEMENT = 'submodules/Display/Source/NavigationBarTitlePlacement.swift'


def validate(source, swiftc, work):
    plan = checked_plan(STAGE)
    if source is None:
        source = work / 'source'
        for path, template in {**plan['replacements'], **plan['guard_sources']}.items():
            dest = source / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / template, dest)
    for path, sha in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / path) == sha, path
    for path in plan['outputs']:
        run([swiftc, '-frontend', '-parse', source / path])
    guard_checks(source, STAGE, plan, work / 'guards')
    controller = (source / GALLERY / 'GalleryController.swift').read_text()
    node = (source / GALLERY / 'GalleryControllerNode.swift').read_text()
    assert 'self.titleView.alignedContentInsets = .zero' in controller
    assert 'titleView: titleView, disableTapNavigation: disableTapNavigation, titleInNavigationBar: true)' in controller
    binding = block(controller, 'self.centralItemTitleContent.get().start(next:')
    assert 'titleContent == nil ? nil : self.titleView' in binding and 'self.navigationItem.titleView = titleView' in binding
    assert 'self.overlayTitleView = titleInNavigationBar ? nil : titleView' in node
    assert 'self.interactionTitleView?.updateIsInteracting' in node
    assert 'self.interactionTitleView?.alpha' not in node
    video = (source / GALLERY / 'Items/UniversalVideoGalleryItem.swift').read_text()
    assert '#selector(self.nagramiXOpenYoutube)' not in block(video, 'private func nagramiXRefreshPiPControls(')

    title = (source / GALLERY / 'GalleryTitleView.swift').read_text()
    method = block(title, '    public func updateLayout(availableSize:').replace('public func', 'func', 1)
    # The host supplies a measured counter label in place of the iOS text renderer.
    start = method.index('        let titleSize = self.title.update(')
    end = method.index('        let titleBackgroundSize', start)
    constraint = method[start:end].split('containerSize: ')[1].split('\n')[0]
    method = method[:start] + '        let titleSize = self.title.measure(' + constraint + ')\n' + method[end:]
    nav = block((source / NAVIGATION).read_text(), '    private func layoutTitleView(').replace('private func', 'func', 1)
    placement = (source / PLACEMENT).read_text().replace('import UIKit', '')
    fixture = (ROOT / 'scripts/tests/NagramiXGalleryHeaderLayout.swift').read_text()
    fixture = fixture.replace('// PRODUCTION_TITLE', method).replace('// PRODUCTION_NAVIGATION', nav).replace('// PRODUCTION_PLACEMENT', placement)
    fixture = fixture.replace('// PRODUCTION_BINDING', binding.split('titleContent in', 1)[1].rsplit('}', 1)[0])
    for result in execute(swiftc, work, 'GalleryHeaderLayout', fixture):
        print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='gallery-header-layout-') as directory:
        validate(args.source, args.swiftc, Path(directory))

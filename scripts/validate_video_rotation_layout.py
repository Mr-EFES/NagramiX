#!/usr/bin/env python3
"""Проверить штатный полноэкранный layout при повторных поворотах видео."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import block
from validate_system_pip_restore import verify_source

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'submodules/GalleryUI/Sources/'
EXPECTED = {
    'ZoomableContentGalleryItemNode.swift': 'aa3622cb64a22ff92877f236a45d8b080ab73b4f7c67828f1de7d1d0fb70c424',
    'GalleryPagerNode.swift': '61d1d34a07e57c66cd2fa8e1071314c5cdb98386214bfc4840cd9a46be6d0993',
    'GalleryController.swift': 'f25cd0fe06d75bfa49b21abe4af099e6b8064ed20c1cdca28a601be2f59fc847',
}


def validate(source, swiftc):
    result = verify_source(source)
    for name, digest in EXPECTED.items():
        assert hashlib.sha256((source / (PREFIX + name)).read_bytes()).hexdigest() == digest, name
    controller = (source / (PREFIX + 'GalleryController.swift')).read_text()
    pager = (source / (PREFIX + 'GalleryPagerNode.swift')).read_text()
    video = (source / (PREFIX + 'Items/UniversalVideoGalleryItem.swift')).read_text()
    assert 'self.galleryNode.frame = CGRect(origin: CGPoint(), size: layout.size)' in controller
    assert 'self.galleryNode.containerLayoutUpdated(layout,' in controller
    assert 'self.itemNodes[i].containerLayoutUpdated(layout,' in pager
    surface = 'videoSurface' if 'self.videoSurface.bounds = CGRect(origin: .zero, size: layout.size)' in video else 'nagramiXPiPSurface'
    assert video.index('self.' + surface + '.bounds = CGRect(origin: .zero, size: layout.size)') < video.index('super.containerLayoutUpdated(layout, navigationBarHeight: navigationBarHeight, transition: transition)')
    native = (source / (PREFIX + 'ZoomableContentGalleryItemNode.swift')).read_text()
    parts = [block(native, marker) for marker in [
        'public var zoomableContent:', 'override open func containerLayoutUpdated(',
        'private func resetScrollViewContents(', 'private func centerScrollViewContents(',
        'open func scrollViewDidZoom(',
    ]]
    production = '''import Foundation
final class NativeZoomLayout: GalleryItemNode {
 let scrollNode = ASScrollNode()
 private var containerLayout: ContainerViewLayout?
 private var ignoreZoom = false
 private var ignoreZoomTransition: ContainedViewLayoutTransition?
''' + '\n'.join(part.replace('public ', '').replace('open ', '') for part in parts) + '\n}\n'
    result['rotation_layout_files'] = len(EXPECTED)
    result['execution'] = []
    if swiftc:
        with tempfile.TemporaryDirectory(prefix='video-rotation-layout-') as directory:
            temp = Path(directory)
            path = temp / 'Production.swift'
            path.write_text(production)
            for mode in [[], ['-O']]:
                binary = temp / 'test'
                def compile_run():
                    subprocess.run([str(swiftc), '-module-cache-path', str(temp / 'cache'), *mode,
                                    str(ROOT / 'scripts/tests/NagramiXVideoRotationLayoutBoundary.swift'), str(path),
                                    str(ROOT / 'scripts/tests/NagramiXVideoRotationLayoutTests.swift'), '-o', str(binary)], check=True)
                    return subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
                path.write_text(production)
                run = compile_run()
                assert run.returncode == 0, run.stdout + run.stderr
                result['execution'].append({'optimized': bool(mode), 'output': run.stdout.strip()})
                # Prove that the suite rejects leaving portrait bounds on rotation.
                broken = production.replace('shouldResetContents = !containerLayout.size.equalTo(layout.size)', 'shouldResetContents = false // stale viewport')
                assert broken != production
                path.write_text(broken)
                bad = compile_run()
                assert bad.returncode != 0 and 'stale portrait/landscape viewport' in bad.stdout
                result['execution'].append({'optimized': bool(mode), 'stale_viewport_regression': 'rejected'})
    result.update(Apple_SDK='pending', UIKit_animation='physical device pending')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_ghostgram_pip_cleanup import delegate_if_applied
    if delegate_if_applied(args, Path(__file__)): return
    result = validate(args.source, args.swiftc)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

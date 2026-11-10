#!/usr/bin/env python3
"""Рано проверить настоящие импорты геометрии в новых Swift test boundaries."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_round_video_replay_stability import UI_BOUNDARY
from validate_pip_gallery_placeholder import CORE_GRAPHICS_IMPORT, DECORATION_BOUNDARY
from validate_download_sheet_edge import LAYOUT_BOUNDARY
from temporary_notice_recovery_runtime import BOUNDARY as TEMPORARY_NOTICE_BOUNDARY
from validate_edit_history_number_badges import GEOMETRY_BOUNDARY as REVISION_BADGE_BOUNDARY
from validate_pip_visual_continuity import GEOMETRY_BOUNDARY as PIP_CONTINUITY_BOUNDARY
from round_video_editor_runtime import GEOMETRY_BOUNDARY as ROUND_VIDEO_EDITOR_BOUNDARY
from round_replacement_geometry_runtime import BOUNDARY as ROUND_REPLACEMENT_BOUNDARY
from download_sheet_vector_contour_runtime import BOUNDARY as DOWNLOAD_CONTOUR_BOUNDARY
from bubble_selection_edge_runtime import BOUNDARY as BUBBLE_EDGE_BOUNDARY


PROBE = r'''
@main struct GeometryImportCheck {
    static func main() {
        let first = CGSize(width: 120, height: 120)
        let second = CGSize(width: 348, height: 348)
        precondition(first != second)
        precondition(first == CGSize(width: 120, height: 120))
        let frame = CGRect(origin: .zero, size: second)
        precondition(frame == CGRect(x: 0, y: 0, width: 348, height: 348))
        precondition(frame.origin == CGPoint.zero)
    }
}
'''


def check(swiftc):
    boundaries = {
        'round-row': UI_BOUNDARY,
        'pip-handoff': CORE_GRAPHICS_IMPORT + 'import Foundation\n',
        'pip-snapshot': DECORATION_BOUNDARY,
        'download-layout': LAYOUT_BOUNDARY,
        'temporary-notice': TEMPORARY_NOTICE_BOUNDARY,
        'revision-badge': REVISION_BADGE_BOUNDARY,
        'pip-continuity': PIP_CONTINUITY_BOUNDARY,
        'round-video-editor': ROUND_VIDEO_EDITOR_BOUNDARY,
        'round-replacement': ROUND_REPLACEMENT_BOUNDARY.split('struct CATransform3D')[0],
        'download-contour': DOWNLOAD_CONTOUR_BOUNDARY.split('struct UIRectCorner')[0],
        'bubble-selection-edge': BUBBLE_EDGE_BOUNDARY.split('struct UIEdgeInsets')[0],
    }
    report = {'boundaries': [], 'apple_import_negatives': [],
              'boundary': 'Actual test boundary imports and geometry operators; no UIKit or whole-app SDK build.'}
    with tempfile.TemporaryDirectory(prefix='nagramix-geometry-imports-') as temporary:
        root = Path(temporary)
        common = [str(swiftc), '-swift-version', '5', '-parse-as-library',
                  '-warnings-as-errors', '-module-cache-path', str(root / 'cache')]
        for name, boundary in boundaries.items():
            # Linux Foundation already exports these conformances. Require the
            # real conditional import too, then exercise it with Apple Swift in CI.
            assert CORE_GRAPHICS_IMPORT in boundary, name
            source = root / (name + '.swift')
            source.write_text(boundary + PROBE)
            for mode, flags in [('debug', []), ('optimized', ['-O'])]:
                binary = root / (name + '-' + mode)
                result = subprocess.run(common + flags + [str(source), '-o', str(binary)],
                                        text=True, capture_output=True)
                assert result.returncode == 0, result.stdout + result.stderr
                subprocess.run([str(binary)], check=True, timeout=30)
                binary.unlink()
                report['boundaries'].append({'name': name, 'mode': mode, 'passed': True})
            if sys.platform == 'darwin':
                source.write_text(boundary.replace(CORE_GRAPHICS_IMPORT, '') + PROBE)
                result = subprocess.run(common + ['-typecheck', str(source)],
                                        text=True, capture_output=True)
                assert result.returncode != 0 and any(
                    phrase in result.stderr for phrase in
                    ("cannot be applied to two 'CGSize'", "cannot be applied to two 'CGRect'",
                     "cannot be applied to two 'CGPoint'", "type 'CGRect' has no member 'zero'")), result.stdout + result.stderr
                report['apple_import_negatives'].append({'name': name, 'old_missing_import_rejected': True})
    if sys.platform != 'darwin':
        report['apple_import_negative_boundary'] = 'Runs only with Apple Swift; Linux Foundation differs.'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = check(args.swiftc)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Verify one shared contour for the attached sheet, without an Apple SDK build."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
from validate_download_sheet_edge import selection_fixture
import download_sheet_vector_contour_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'download_sheet_vector_contour'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'round_replacement_geometry'
    assert set(plan['outputs']) == {runtime.GROUP}
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    current = (args.source / runtime.GROUP).read_text()
    previous = (ROOT / 'ios' / plan['previous'][runtime.GROUP]).read_text()
    # Layout, selection, touch routing, native dim animation and safe-area
    # positioning stay unchanged. Only the complementary contour pair differs.
    for marker in ('    func updateLayout(', '    func updateItemNodes(',
                   '    func setOverlayNode(', '    override func hitTest(',
                   '    func animateDimViewsAlpha(', '    private func currentVerticalOverscroll()',
                   '    private func currentRealVerticalOverscroll()'):
        assert block(current, marker) == block(previous, marker), marker
    marker = '    private func updateOverscroll('
    assert block(current, marker).replace('        self.nagramiXUpdateTopCornerLayers(transition: transition)\n', '') == block(previous, marker)
    assert 'nagramiXActionSheetTopCornerDimImage' not in current
    assert current.count('self.clippingNode.layer.mask =') == 1
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='download-sheet-vector-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = runtime.fixture(args.source)
        results = execute(args.swiftc, root, 'group-contour', text)
        for name, mutated, diagnostic in runtime.negatives(text):
            results += execute(args.swiftc, root, name, mutated, diagnostic)
        results += execute(args.swiftc, root, 'selection', selection_fixture(args.source))
        run([args.swiftc, '-frontend', '-parse', args.source / runtime.GROUP])
    assert manifest(args.source) == initial
    result = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'loader_refusals': len(refusals), 'executions': results, 'swift_parse': 1,
              'source_files': len(initial), 'source_unchanged_by_checks': True,
              'boundary': 'Complete production ActionSheetItemGroupNode initializer, mode changes, hierarchy, layout, overscroll and dim animation execute with explicit UIKit/Texture/layer adapters. Analytical paths check alpha containment, complement and resizing; production option factory tests callbacks. These checks do not prove CoreAnimation/CoreGraphics pixels, live blur, frame timing or physical iPhone rendering.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

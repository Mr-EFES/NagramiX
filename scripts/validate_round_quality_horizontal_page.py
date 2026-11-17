#!/usr/bin/env python3
"""Проверить утверждённый горизонтальный выбор качества без изменения механики."""
import argparse, json, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from late_source_stages import verified_prefix, LATE_SOURCE_STAGES
from validate_private_temporary_transcription import execute
from round_quality_horizontal_apple import check as apple_check
from round_quality_compact_runtime import fixture as controls_fixture
import round_quality_horizontal_runtime as rt

STAGE = 'round_quality_horizontal_page'


def contracts(source):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {rt.U} and len(plan['guards']) == 8 and len(plan['templates']) == 10
    assert plan['required_previous_stage'] == 'gallery_round_export' and not plan['copies'] and not plan['deletions']
    before = (OVERLAY / plan['previous'][rt.U]).read_text()
    after = (source / rt.U).read_text()
    for marker in ['func nagramiXRoundQualityTitle(', 'func nagramiXRoundQualitySubtitle(',
                   'private final class NagramiXRoundBitRateCell:', 'final class NagramiXRoundQualityController:']:
        assert block(before, marker) == block(after, marker), 'Unrelated behavior changed: ' + marker
    button = 'private final class NagramiXRoundSegmentButton:'
    for marker in ['    override func layoutSubviews()', '    override var isHighlighted:', '    func update(', '    @objc private func tapped()']:
        assert block(block(before, button), marker) == block(block(after, button), marker)
    assert 'nagramiXRoundQualityUsesVerticalLayout' not in after
    assert 'adjustsFontSizeToFitWidth' not in after and 'minimumScaleFactor' not in after
    return {'runtime_paths': 1, 'new_app_files_strings_dependencies': 0,
            'whole_controller_and_bitrate_cell_verbatim': True,
            'selection_storage_and_cinematic_capability_verbatim': True,
            'camera_encoding_and_independent_gallery_quality_guarded': True,
            'horizontal_equal_quality_cells_with_centered_check': True,
            'large_type_or_long_translation_scrolls_without_font_reduction': True}


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    contract = contracts(source)
    code = rt.fixture(source)
    runs = execute(swiftc, folder, 'horizontal-quality', code)
    runs += execute(swiftc, folder, 'round-page-controls', controls_fixture(source))
    negatives = []
    for name, old, new, diagnostic in [
        ('vertical-layout', 'row.axis = .horizontal', 'row.axis = .vertical', 'quality never becomes a vertical list'),
        ('clip-overflow', 'self.width = max(viewport, minimum)', 'self.width = max(viewport, minimum * 0)', 'complete text and check gutter fit even on narrow screens'),
        ('detail-aligned-check', 'self.checkView.centerYAnchor.constraint(equalTo: self.centerYAnchor)', 'self.checkView.centerYAnchor.constraint(equalTo: self.detailLabel.centerYAnchor)', 'check is centered on the whole cell'),
        ('shrink-quality-font', 'Font.semibold(presentationData.listsFontSize.itemListBaseFontSize)', 'Font.semibold(presentationData.listsFontSize.itemListBaseFontSize * 0.8)', 'font size is never reduced to fit'),
        ('wrong-quality-route', 'self?.changed?(index)', 'self?.changed?(0)', 'each quality button keeps its own route'),
        ('missing-selected-reveal', 'scroll.scrollRectToVisible(rect, animated: false)', '_ = rect', 'selected quality is revealed after layout'),
    ]:
        assert old in code, name
        negatives += execute(swiftc, folder, name, code.replace(old, new, 1), diagnostic)
    p = subprocess.run([str(swiftc), '-frontend', '-parse', str(source / rt.U)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return {'contracts': contract, 'executions': runs, 'semantic_negatives': negatives,
            'apple_api': apple_check(source, swiftc, folder / 'apple'),
            'boundary': 'Actual button/cell/layout and existing complete controls/model/store routes.71 real title catalogs. UIKit typography metrics, constraints and scrolling are recording IO hosts, not pixels. Complete real UIKit page typecheck required on macOS.',
            'full_application_sdk': 'not_run', 'pixel_verification': 'not_run', 'physical_iphone': 'pending'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--swiftc', type=Path, required=True)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    assert verified_prefix(a.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='horizontal-round-') as d:
        folder = Path(d)
        refused = guard_checks(a.source, STAGE, checked_plan(STAGE), folder / 'guards')
        report = check(a.source, a.swiftc, folder / 'runtime')
    assert manifest(a.source) == before
    report.update(stage=108, name=STAGE, loader_refusals=refused, source_unchanged_by_checks=True)
    if a.report:
        a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Проверить ширину пузырьков и прежние native-права выделения до SDK."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
import bubble_selection_edge_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'bubble_selection_edge'


def source_contract(source, plan):
    assert plan['required_previous_stage'] == 'download_sheet_vector_contour'
    assert set(plan['outputs']) == {runtime.BUBBLE}
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    current = (source / runtime.BUBBLE).read_text()
    previous = (ROOT / 'ios' / plan['previous'][runtime.BUBBLE]).read_text()
    helpers = ('\n' + block(current, 'private func nagramiXBubbleCanHaveSelection(') + '\n\n'
               + block(current, 'private func nagramiXBubbleSelectionWidthInset(') + '\n')
    start = previous.index('        var canHaveSelection = true', previous.index('    override public func updateSelectionState'))
    end = previous.index('        if let selectionState = item.controllerInteraction.selectionState, canHaveSelection {', start)
    original_policy = previous[start:end]
    restored = current.replace(helpers, '', 1)
    restored = restored.replace('        let canHaveSelection = nagramiXBubbleCanHaveSelection(item)\n        \n', original_policy, 1)
    reserve = '        tmpWidth -= nagramiXBubbleSelectionWidthInset(item: item, incoming: incoming, hasBubble: !bubbleStyle.isBubbleless)\n'
    assert restored.count(reserve) == 1
    restored = restored.replace(reserve, '', 1)
    assert restored == previous, 'Changes outside the native policy extraction and width budget'
    # Native history rebuilds both single entries and groups when selection
    # changes; the immutable item state also covers recycled/offscreen rows.
    history = (source / (runtime.BASE + 'Components/Chat/ChatHistoryEntry/Sources/ChatHistoryEntry.swift')).read_text()
    assert history.count('if lhsSelection != rhsSelection {') == 2
    item = (source / runtime.ITEM).read_text()
    assert 'return messages.contains(where: { isSelectable($0.2) })' in block(item, '    public var isInSelection: Bool {')
    assert 'item.controllerInteraction.selectionState' not in block(current, 'private func nagramiXBubbleSelectionWidthInset(')
    return previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    previous = source_contract(args.source, plan)
    initial = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='bubble-selection-edge-') as temporary:
        root = Path(temporary)
        refusals = guard_checks(args.source, STAGE, plan, root / 'guards')
        text = runtime.fixture(args.source, previous)
        results = execute(args.swiftc, root, 'bubble-edge', text)
        for name, mutated, diagnostic in runtime.negatives(text):
            results += execute(args.swiftc, root, name, mutated, diagnostic)
        run([args.swiftc, '-frontend', '-parse', args.source / runtime.BUBBLE])
    assert manifest(args.source) == initial
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'loader_refusals': len(refusals), 'executions': results, 'swift_parse': 1,
              'source_files': len(initial), 'source_unchanged_by_checks': True,
              'boundary': 'Real width-fill, compact constants, native width preparation and final bubble/content placement execute together with actual item selection and native eligibility/translation. Text measurement is an explicit fixed-advance adapter; UIKit, CoreText pixels and actual transition frames require Apple SDK/iPhone. Every other byte of the parent file is reconstructed and compared with the proven baseline.',
              'apple_sdk': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Check that re-created round-quality rows are laid out before the next tap."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

import gallery_round_export_runtime as gallery
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import ROOT, checked_plan

STAGE = 'round_quality_sheet_navigation'
DISPLAY = 'submodules/Display/Source/'
TEST = ROOT / 'scripts/tests/NagramiXRoundQualitySheetNavigationTests.swift'


def fixture(source: Path) -> tuple[str, str]:
    view = (source / DISPLAY / 'ViewController.swift').read_text()
    controller = (source / DISPLAY / 'ActionSheetController.swift').read_text()
    controller_node = (source / DISPLAY / 'ActionSheetControllerNode.swift').read_text()
    group_node = (source / DISPLAY / 'ActionSheetItemGroupsContainerNode.swift').read_text()
    item_groups = block(group_node, '    func setGroups(')
    assert 'groupNode.removeFromSupernode()' in item_groups and 'self.groupNodes.removeAll()' in item_groups
    assert 'updateLayout(' not in item_groups and 'requestLayout?()' not in item_groups.split('node.requestLayout =', 1)[0]

    code = gallery.model_fixture(source).split('@main struct GalleryRoundProfileTests', 1)[0]
    old_host = block(code, 'final class ActionSheetController')
    native_host = '''
enum ContainedViewLayoutTransition { case immediate }
final class ItemGroupsHost {
    private var groups: [ActionSheetItemGroup] = []
    private(set) var displayed: [ActionSheetItem] = []
    private(set) var layouts = 0

    func setGroups(_ groups: [ActionSheetItemGroup]) {
        self.groups = groups
        self.displayed = []
    }
    func layout() {
        layouts += 1
        displayed = groups.flatMap { $0.items }
    }
}
final class ActionSheetNode {
    let itemGroupsContainerNode = ItemGroupsHost()
''' + block(controller_node, '    func setGroups(') + '''
}
final class ActionSheetController {
    private(set) var groups: [ActionSheetItemGroup] = []
    var dismissed: ((Bool) -> Void)?
    private(set) var closes = 0
    let actionSheetNode = ActionSheetNode()
    var isViewLoaded = false
    private var validLayout: CGSize?

    init(presentationData: PresentationData) {}

    func appear() {
        isViewLoaded = true
        actionSheetNode.setGroups(groups)
        containerLayoutUpdated(CGSize(width: 360, height: 740), transition: .immediate)
    }

    func containerLayoutUpdated(_ layout: CGSize, transition: ContainedViewLayoutTransition) {
        validLayout = layout
        actionSheetNode.itemGroupsContainerNode.layout()
    }

    func dismissAnimated() {
        closes += 1
        dismissed?(false)
    }
''' + block(controller, '    public func setItemGroups(') + '\n' + block(view, '    public func requestLayout(transition:') + '\n}'
    production = (source / gallery.H).read_text()
    row = block(production, 'private final class NagramiXRoundQualitySheetNode:')
    assert '.touchUpInside' in row and 'self.rowButton.frame = CGRect(origin: .zero, size: size)' in row
    assert 'self.rowButton.accessibilityTraits' in row and 'self.radioView.isHidden = item.kind != .option' in row
    assert 'self.chevronView.isHidden = item.kind != .parameter' in row
    editor = block((source / gallery.Q).read_text(), '    private func nagramiXPresentRoundQuality(')
    assert 'self.pageModel.currentItem.uniqueId == itemId' in editor
    assert 'self.mediaEditor.values = current.withUpdatedNagramiXRoundTuning' in editor
    assert 'self.selectionEditCommitted()' in editor and 'self.requestLayout(transition: .immediate)' in editor
    toolbar_file = gallery.H.replace('NagramiXRoundQualitySheet.swift', 'ChatMediaEditorBottomControlsComponent.swift')
    toolbar = (source / toolbar_file).read_text()
    badge = block(toolbar, 'func nagramiXRoundVideoQualityCode(')
    return code.replace(old_host, native_host, 1) + '\n' + badge + '\n' + TEST.read_text(), production


def apple_typecheck(source: Path, swiftc: Path, work: Path, production: str) -> None:
    if sys.platform != 'darwin':
        return
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    probe = work / 'RoundQualityUIKit.swift'
    native_button = (source / DISPLAY / 'HighlightTrackingButton.swift').read_text()
    native_item = (source / DISPLAY / 'ActionSheetItemNode.swift').read_text().replace('import AsyncDisplayKit\n', '')
    localization_host = (ROOT / 'scripts/tests/NagramiXUnifiedMenusBoundary.swift').read_text()
    strings = block(localization_host, 'struct PresentationStrings').rstrip() + '''
extension PresentationStrings {
    struct Primary { let languageCode = "ru" }
    var primaryComponent: Primary { Primary() }
    var Common_Back: String { "Назад" }
    var Appearance_TextSize_Apply: String { "Применить" }
    var UserInfo_NotificationsDefault: String { "По умолчанию" }
    func nagramiXUILocalized(_ string: String) -> String { string }
}
'''
    host = '''
import Foundation
import UIKit
open class ASDisplayNode: NSObject {
    let view = UIView()
    var isHidden: Bool { get { view.isHidden } set { view.isHidden = newValue } }
    var frame: CGRect { get { view.frame } set { view.frame = newValue } }
    var backgroundColor: UIColor? { get { view.backgroundColor } set { view.backgroundColor = newValue } }
    func addSubnode(_ node: ASDisplayNode) { view.addSubview(node.view) }
}
public struct ActionSheetControllerTheme {
    let itemBackgroundColor = UIColor.black, itemHighlightedBackgroundColor = UIColor.darkGray
    let secondaryTextColor = UIColor.gray, controlColor = UIColor.gray
    let primaryTextColor = UIColor.white, controlAccentColor = UIColor.systemBlue
    let baseFontSize: CGFloat = 17
}
public enum ContainedViewLayoutTransition { case immediate }
protocol NagramiXGlassActionSheetItem { var nagramiXUsesFloatingGlass: Bool { get } }
protocol ActionSheetItem { func node(theme: ActionSheetControllerTheme) -> ActionSheetItemNode; func updateNode(_ node: ActionSheetItemNode) }
struct ActionSheetItemGroup { let items: [ActionSheetItem] }
final class ActionSheetController {
    var dismissed: ((Bool) -> Void)?
    init(presentationData: PresentationData) {}
    func setItemGroups(_ groups: [ActionSheetItemGroup]) {}
    func requestLayout(transition: ContainedViewLayoutTransition) {}
    func dismissAnimated() {}
}
struct PresentationData { let strings = PresentationStrings() }
struct MediaEditorValues {
    let nagramiXRoundTuning: [Int]?
    func withUpdatedNagramiXRoundTuning(_ tuning: [Int]) -> Self { Self(nagramiXRoundTuning: tuning) }
}
enum Font {
    static func regular(_ size: CGFloat) -> UIFont { UIFont.systemFont(ofSize: size) }
    static func semibold(_ size: CGFloat) -> UIFont { UIFont.systemFont(ofSize: size, weight: .semibold) }
}
let UIScreenPixel: CGFloat = 0.5
'''
    tuning = block((source / gallery.V).read_text(), 'func chatMediaEditorRoundVideoTuning(')
    body = '\n'.join(line for line in production.splitlines() if not line.startswith('import '))
    probe.write_text('\n'.join([host, strings, native_button, native_item, tuning, body]))
    run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-typecheck', '-parse-as-library', '-sdk', sdk,
         '-target', 'arm64-apple-ios15.0', '-module-cache-path', work / 'cache', probe], timeout=180)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name in plan['inputs']:
        run([args.swiftc, '-frontend', '-parse', args.source / name], timeout=60)
    with tempfile.TemporaryDirectory(prefix='round-quality-sheet-navigation-') as folder:
        work = Path(folder)
        code, production = fixture(args.source)
        source_file = work / 'QualityNavigation.swift'
        source_file.write_text(code)
        common = [args.swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                  '-module-cache-path', work / 'cache']
        for mode, flags in [('debug', []), ('optimized', ['-O'])]:
            executable = work / mode
            run([*common, *flags, source_file, '-o', executable], timeout=100)
            result = run([executable], timeout=30)
            print(f'{mode}: {result.stdout.strip()}', flush=True)
        missing_layout = '        sheet.requestLayout(transition: .immediate)'
        assert code.count(missing_layout) == 1
        source_file.write_text(code.replace(missing_layout, '', 1))
        executable = work / 'old-behavior'
        run([*common, source_file, '-o', executable], timeout=100)
        negative = subprocess.run([executable], text=True, capture_output=True, timeout=30)
        assert negative.returncode == 96 and 'options are laid out before the next tap' in negative.stderr, negative.stderr
        print('Regression reproduced when the layout request is removed', flush=True)
        apple_typecheck(args.source, args.swiftc, work, production)


if __name__ == '__main__':
    main()

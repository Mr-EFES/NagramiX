#!/usr/bin/env python3
"""Verify the settings category bar against the actual list and navigation layout."""
import argparse
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_local_copy_delivery import run
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan

STAGE = 'settings_category_bar_layout'
ITEM_LIST = 'submodules/ItemListUI/Sources/'
DISPLAY = 'submodules/Display/Source/'


def fixture(source: Path, paths: dict) -> str:
    files = {Path(name).stem: (source / name).read_text() for name in paths}
    controller = files['ItemListController']
    title = files['NagramiXItemListControllerSegmentedTitleView']
    list_node = files['ItemListControllerNode']
    navigator = files['NavigationBarNode']
    tabs = files['NagramiXHorizontalTabsComponent']
    search = (source / 'submodules/SettingsUI/Sources/NagramiXSettingsSearchHeader.swift').read_text()
    assert 'width: max(1.0, params.width - params.leftInset - params.rightInset)' in search
    assert 'alignedContentInsets = ItemListControllerNode.listContentInsets(layout: layout)' in controller
    update = block(controller, '    override open func updateNavigationBarLayout(')
    assert update.index('listContentInsets') < update.index('super.updateNavigationBarLayout')
    category_case = controller.split('case let .equalSectionControl(', 1)[1].split('case let .textWithTabs(', 1)[0]
    assert category_case.index('listContentInsets') < category_case.index('navigationItem.titleView =')
    assert list_node.count('var insets = Self.listContentInsets(layout: layout)') == 2
    assert 'self.clipsToBounds = true' in title and 'self.window' not in title
    assert 'containerSize: CGSize(width: width, height: height)' in title
    assert tabs.count('containerSize: CGSize(width: equalSlotWidth ?? 1000.0,') == 2
    assert 'size.width = component.equalSlotWidth ??' in tabs
    assert 'containerSize: CGSize(width: titleWidth, height: 100.0)' in tabs

    placement = (source / DISPLAY / 'NavigationBarTitlePlacement.swift').read_text().replace('import UIKit\n', '')
    protocol = block(files['NavigationBarTitleView'], 'public protocol NavigationBarTitleView:')
    defaults = block(files['NavigationBarTitleView'], 'public extension NavigationBarTitleView')
    insets = block(list_node, '    static func listContentInsets(')
    placement_method = block(navigator, '    private func layoutTitleView(').replace('private func', 'func', 1)
    slot_start = tabs.index('            let equalSlotWidth: CGFloat?')
    slot_end = tabs.index('            var items:', slot_start)
    slots = tabs[slot_start:slot_end]
    scale_start = tabs.index('                let titleWidth = component.equalSlotWidth.map')
    scale_end = tabs.index('                let rawAttributedString', scale_start)
    fitting = tabs[scale_start:scale_end]

    return '''
import Foundation
public func floorToScreenPixels(_ value: CGFloat) -> CGFloat { floor(value * 3) / 3 }
public struct UIEdgeInsets {
    var top: CGFloat = 0
    var left: CGFloat = 0
    var bottom: CGFloat = 0
    var right: CGFloat = 0
}
public class UIView { var frame: CGRect = .zero }
public struct ContainedViewLayoutTransition {
    static let immediate = Self()
    func updateFrame(view: UIView, frame: CGRect) { view.frame = frame }
}
struct ContainerViewLayout {
    var size: CGSize
    var safe: UIEdgeInsets
    var intrinsic: UIEdgeInsets
    enum Option { case input }
    func insets(options: [Option]) -> UIEdgeInsets { intrinsic }
    func listSideMargins(base: CGFloat) -> (left: CGFloat, right: CGFloat) {
        (base + safe.left, base + safe.right)
    }
}
struct NavigationBarComponent {
    struct View {
        var primaryLeftButtonsWidth: CGFloat
        var primaryRightButtonsWidth: CGFloat = 0
    }
}
''' + placement + protocol + '\n' + defaults + '''
final class NativeTitle: UIView, NavigationBarTitleView {
    var requestUpdate: ((ContainedViewLayoutTransition) -> Void)?
    func animateLayoutTransition() {}
    func updateLayout(availableSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        CGSize(width: min(200, availableSize.width), height: 40)
    }
}
final class CategoryTitle: UIView, NavigationBarTitleView {
    var alignedContentInsets: UIEdgeInsets?
    var requestUpdate: ((ContainedViewLayoutTransition) -> Void)?
    func animateLayoutTransition() {}
    func updateLayout(availableSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        CGSize(width: availableSize.width, height: 40)
    }
}
struct ItemListControllerNode {
''' + insets + '''
}
final class NavigationBarNode {
    static let nominalHeight: CGFloat = 60
    var titleView: UIView?
    var trailingButtonsInset: CGFloat = 0
    struct Layout {
        var size: CGSize
        var leftInset: CGFloat
        var rightInset: CGFloat
    }
''' + placement_method + '''
}
private func categorySlot(width: CGFloat, count: Int) -> CGFloat {
    enum Layout { case fit, equal }
    let component = (layout: Layout.equal, unused: false)
    let availableSize = CGSize(width: width, height: 40)
    let lensInset: CGFloat = 3
    let sideInset: CGFloat = 0
    let orderedTabs = 0..<count
''' + slots + '''
    return equalSlotWidth!
}
private struct TestFont {
    var pointSize: CGFloat
    func withSize(_ size: CGFloat) -> Self { Self(pointSize: size) }
}
private enum Font {
    static func bold(_ size: CGFloat) -> TestFont { TestFont(pointSize: size) }
    static func medium(_ size: CGFloat) -> TestFont { TestFont(pointSize: size) }
}
private func fittedSize(slot: CGFloat, measuredWidth: CGFloat, isBold: Bool) -> (pointSize: CGFloat, width: CGFloat) {
    let component = (equalSlotWidth: Optional(slot), unused: false)
    let title = (isBold: isBold, unused: false)
    let sideInset: CGFloat = 4
''' + fitting.replace('ceil((title.text as NSString).size(withAttributes: [.font: font]).width)', 'ceil(measuredWidth)') + '''
    return (font.pointSize, titleWidth)
}
@main enum LayoutChecks {
    static func main() {
        let bar = NavigationBarNode()
        let title = CategoryTitle()
        bar.titleView = title
        for (width, safeLeft, safeRight, intrinsicRight, backWidth) in [
            (402.0, 0.0, 0.0, 0.0, 40.0),
            (320.0, 0.0, 0.0, 0.0, 40.0),
            (744.0, 42.0, 18.0, 5.0, 50.0),
            (1024.0, 0.0, 0.0, 0.0, 0.0),
            (402.0, 0.0, 0.0, 0.0, 40.0),
        ] {
            let layout = ContainerViewLayout(size: CGSize(width: width, height: 780), safe: .init(left: safeLeft, right: safeRight), intrinsic: .init(right: intrinsicRight))
            let list = ItemListControllerNode.listContentInsets(layout: layout)
            title.alignedContentInsets = list
            bar.layoutTitleView(layout: .init(size: layout.size, leftInset: safeLeft, rightInset: safeRight), rowView: .init(primaryLeftButtonsWidth: backWidth), contentVerticalOrigin: 50, transition: .immediate)
            precondition(abs(title.frame.maxX - (width - list.right)) < 0.001, "trailing edge drifted from list")
            let expectedLeft = backWidth == 0 ? list.left : max(list.left, safeLeft + 16 + backWidth + 8)
            precondition(title.frame.minX == expectedLeft && title.frame.height == 40)
            let slot = categorySlot(width: title.frame.width, count: 3)
            precondition(abs(slot * 3 + 6 - title.frame.width) < 0.001)
            precondition(title.frame.minX + 3 + slot * 3 < title.frame.maxX, "last selection reaches the edge")
            let fitted = fittedSize(slot: slot, measuredWidth: 94, isBold: true)
            precondition(fitted.width < slot && fitted.pointSize <= 15)
            if slot > 72 && slot < 94 {
                precondition(fitted.pointSize < 15 && 94 * fitted.pointSize / 15 <= fitted.width)
            }
        }
        title.alignedContentInsets = .init(left: 90, right: 90)
        bar.layoutTitleView(layout: .init(size: CGSize(width: 160, height: 400), leftInset: 0, rightInset: 0), rowView: .init(primaryLeftButtonsWidth: 40), contentVerticalOrigin: 0, transition: .immediate)
        precondition(title.frame.width == 0, "a temporarily collapsed container offered negative width")

        let stock = NativeTitle()
        bar.titleView = stock
        bar.layoutTitleView(layout: .init(size: CGSize(width: 402, height: 700), leftInset: 0, rightInset: 0), rowView: .init(primaryLeftButtonsWidth: 40), contentVerticalOrigin: 50, transition: .immediate)
        precondition(stock.frame == CGRect(x: 101, y: 60, width: 200, height: 40), "stock title positioning changed")
        print("PASS shared insets, narrow/regular/landscape layout, collapsed width, return, equal slots, label fitting and stock titles")
    }
}
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name in plan['inputs']:
        run([args.swiftc, '-frontend', '-parse', args.source / name], timeout=60)
    with tempfile.TemporaryDirectory(prefix='settings-category-bar-layout-') as folder:
        work = Path(folder)
        source = work / 'CategoryLayout.swift'
        source.write_text(fixture(args.source, plan['inputs']))
        for mode, flags in [('debug', []), ('optimized', ['-O'])]:
            executable = work / mode
            run([args.swiftc, '-swift-version', '5', '-warnings-as-errors', '-parse-as-library',
                 '-module-cache-path', work / 'cache', *flags, source, '-o', executable], timeout=90)
            result = run([executable], timeout=30)
            print(f'{mode}: {result.stdout.strip()}', flush=True)


if __name__ == '__main__':
    main()

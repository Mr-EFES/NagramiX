private extension NagramiXRoundSegmentButton {
    var name: UILabel { nameLabel }
    var detail: UILabel { detailLabel }
    var mark: UIImageView { checkView }
    var labels: UIStackView { nameLabel.superview as! UIStackView }
    func tap() { tapped() }
}
private extension NagramiXRoundSegmentCell {
    var picks: [NagramiXRoundSegmentButton] { buttons }
    var stack: UIStackView { row }
    var scroll: UIScrollView? { qualityScroll }
    var rowWidth: CGFloat { qualityWidth!.constant }
    var lines: [UIView] { separators }
}
private func linked(_ first: Anchor, _ second: Anchor, _ constant: CGFloat) -> Bool {
    NSLayoutConstraint.active.contains { $0.first == first && $0.second == second && $0.constant == constant && $0.relation == "=" }
}
@main private enum HorizontalQualityChecks {
    static func main() {
        var checks = 0
        func check(_ value: Bool, _ message: String) {
            if !value { print("Horizontal quality: " + message); exit(96) }; checks += 1
        }
        check(actualTitles.count == 71, "all real catalogs represented")
        for titles in actualTitles {
            for font: CGFloat in [14, 17, 26, 34] {
                for width: CGFloat in [240, 280, 335, 350, 430, 768] {
                    NSLayoutConstraint.active = []
                    let cell = NagramiXRoundSegmentCell(presentationData: PresentationData(font), count: 3, qualityLayout: true)
                    let options = titles.enumerated().map { NagramiXRoundSegmentOption(title: $0.element, subtitle: ["480×480", "512×512", "640×640"][$0.offset], selected: $0.offset == 2, enabled: true) }
                    cell.contentView.frame.size.width = width
                    cell.update(options, availableWidth: width)
                    let scroll = cell.scroll!
                    check(cell.stack.axis == .horizontal, "quality never becomes a vertical list")
                    check(cell.stack.distribution == .fillEqually, "three equal selectable cells")
                    check(cell.rowWidth >= width - 8, "quality fills the viewport")
                    check(cell.lines.count == 2 && cell.lines.allSatisfy { !$0.isHidden && $0.superview === cell.stack }, "only two boundaries travel with the row")
                    check(scroll.isScrollEnabled == (cell.rowWidth > width - 8 + 0.5), "overflow is reachable horizontally")
                    check(!scroll.bounces && scroll.isDirectionalLockEnabled && !scroll.showsVerticalScrollIndicator, "horizontal interaction does not add vertical bounce")
                    check(linked(cell.stack.heightAnchor, scroll.frameLayoutGuide.heightAnchor, 0), "scrolling does not collapse self-sizing height")
                    let column = (cell.rowWidth - 2) / 3
                    for (index, button) in cell.picks.enumerated() {
                        check(button.name.text == titles[index] && button.detail.text == options[index].subtitle, "full localized words and resolutions preserved")
                        check(button.name.numberOfLines == 1 && button.detail.numberOfLines == 1, "no split quality words")
                        check(button.name.font == font && button.detail.font == floor(font * 13 / 17), "font size is never reduced to fit")
                        check(column - 25 >= max(button.name.intrinsicContentSize.width, button.detail.intrinsicContentSize.width), "complete text and check gutter fit even on narrow screens")
                        check(linked(button.labels.trailingAnchor, button.mark.leadingAnchor, -3) && linked(button.mark.trailingAnchor, button.trailingAnchor, -4), "check has a separate gutter")
                        check(linked(button.mark.centerYAnchor, button.centerYAnchor, 0) && !linked(button.mark.centerYAnchor, button.detail.centerYAnchor, 0), "check is centered on the whole cell")
                        check(button.mark.alpha == (index == 2 ? 1 : 0), "only the selected check is visible")
                        check(button.accessibilityLabel == titles[index] && button.accessibilityValue == options[index].subtitle, "VoiceOver retains the complete values")
                        var tapped = -1; cell.changed = { tapped = $0 }; button.tap()
                        check(tapped == index, "each quality button keeps its own route")
                        button.frame = CGRect(x: CGFloat(index) * column, y: 0, width: column, height: 72)
                    }
                    cell.layoutSubviews()
                    check(scroll.revealed.last == cell.picks[2].frame, "selected quality is revealed after layout")
                    let fitted = cell.systemLayoutSizeFitting(CGSize(width: 900, height: 80), withHorizontalFittingPriority: .required, verticalFittingPriority: .required)
                    check(fitted.width == 900 && cell.stack.axis == .horizontal, "sizing and rotation retain the horizontal row")
                }
            }
        }
        let ru = ["Стандарт", "Высокое", "Максимум"]
        let regular = NagramiXRoundSegmentCell(presentationData: PresentationData(), count: 3, qualityLayout: true)
        regular.update(ru.enumerated().map { NagramiXRoundSegmentOption(title: $0.element, subtitle: ["480×480", "512×512", "640×640"][$0.offset], selected: $0.offset == 2, enabled: true) }, availableWidth: 335)
        check(regular.scroll?.isScrollEnabled == false, "Russian default fits a regular narrow viewport in the measurement host")
        for subtitle: String? in [nil, "Эффективное сжатие"] {
            NSLayoutConstraint.active = []
            let other = NagramiXRoundSegmentCell(presentationData: PresentationData(), count: 2)
            other.update([NagramiXRoundSegmentOption(title: "A", subtitle: subtitle, selected: true, enabled: true), NagramiXRoundSegmentOption(title: "B", subtitle: subtitle, selected: false, enabled: false)], availableWidth: 100)
            check(other.scroll == nil && other.stack.axis == .horizontal, "FPS codec and cinema retain native layout")
            for b in other.picks {
                check(b.name.numberOfLines == 0 && b.detail.numberOfLines == 0, "other groups retain multiline labels")
                check(linked(b.labels.trailingAnchor, b.mark.leadingAnchor, -4) && linked(b.mark.trailingAnchor, b.trailingAnchor, -8), "other groups retain native gutter")
            }
            var taps = 0; other.changed = { _ in taps += 1 }; other.picks[1].tap()
            check(taps == 0, "disabled settings reject delayed taps")
        }
        print("Horizontal quality: \(checks) actual layout/button checks passed; UIKit metrics/constraints/scroll are recording hosts")
    }
}

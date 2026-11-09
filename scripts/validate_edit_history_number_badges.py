#!/usr/bin/env python3
"""Проверить круглые номера редакций на production bodies, без UIKit/SDK."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_upstream_13_2_release_string_compile import real_extensions
from validate_localization_standard import strings

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'edit_history_number_badges'
UI = 'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift'


# UIKit owns measurement and Auto Layout on the device. This boundary makes
# text metrics explicit; all badge sizing, rounding and configuration bodies
# themselves are extracted unchanged from the production Swift file.
GEOMETRY_BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct UIColor: Equatable {
    let name: String
    var alpha: CGFloat = 1
    static let clear = Self(name: "clear")
    static let white = Self(name: "white")
    func withAlphaComponent(_ alpha: CGFloat) -> Self { Self(name: name, alpha: alpha) }
}
struct UIFont: Equatable {
    let pointSize: CGFloat
    var lineHeight: CGFloat { ceil(pointSize * 1.2) }
}
enum Font {
    static func regular(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func semibold(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func italic(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func semiboldItalic(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func monospace(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
}
struct UIFontMetrics {
    enum Style { case body, caption1 }
    static var scale: CGFloat = 1
    init(forTextStyle: Style) {}
    func scaledFont(for font: UIFont) -> UIFont { UIFont(pointSize: font.pointSize * Self.scale) }
}
enum NSLayoutConstraintAxis: Hashable { case horizontal, vertical }
struct UILayoutPriority: Equatable {
    let rawValue: Float
    static let required = Self(rawValue: 1000)
    static let defaultHigh = Self(rawValue: 750)
}
final class Layer {
    enum Curve { case continuous, circular }
    var cornerRadius: CGFloat = 0
    var cornerCurve = Curve.circular
    var masksToBounds = false
}
struct BoundaryAnchor {
    let owner: ObjectIdentifier
    let attribute: String
    func constraint(equalTo other: Self, constant: CGFloat = 0) -> NSLayoutConstraint { NSLayoutConstraint(first: self, relation: .equal, second: other, constant: constant) }
    func constraint(greaterThanOrEqualTo other: Self, constant: CGFloat = 0) -> NSLayoutConstraint { NSLayoutConstraint(first: self, relation: .minimum, second: other, constant: constant) }
    func constraint(lessThanOrEqualTo other: Self, constant: CGFloat = 0) -> NSLayoutConstraint { NSLayoutConstraint(first: self, relation: .maximum, second: other, constant: constant) }
}
struct NSLayoutConstraint {
    enum Relation { case equal, minimum, maximum }
    let first: BoundaryAnchor
    let relation: Relation
    let second: BoundaryAnchor
    let constant: CGFloat
    static var activated: [Self] = []
    static func activate(_ constraints: [Self]) { activated += constraints }
}
class UIView {
    var backgroundColor: UIColor?, isHidden = false
    var frame = CGRect.zero
    var bounds: CGRect { get { CGRect(origin: .zero, size: frame.size) } set { frame.size = newValue.size } }
    let layer = Layer()
    var clipsToBounds = false, isAccessibilityElement = false
    var isUserInteractionEnabled = true
    var translatesAutoresizingMaskIntoConstraints = true
    var accessibilityLabel: String?
    var subviews: [UIView] = []
    var invalidations = 0
    var hugging: [NSLayoutConstraintAxis: UILayoutPriority] = [:]
    var compression: [NSLayoutConstraintAxis: UILayoutPriority] = [:]
    init(frame: CGRect = .zero) { self.frame = frame }
    required init?(coder: NSCoder) { fatalError("test boundary") }
    var intrinsicContentSize: CGSize { .zero }
    func layoutSubviews() {}
    func addSubview(_ view: UIView) { subviews.append(view) }
    func invalidateIntrinsicContentSize() { invalidations += 1 }
    func setNeedsLayout() {}
    func setContentHuggingPriority(_ value: UILayoutPriority, for axis: NSLayoutConstraintAxis) { hugging[axis] = value }
    func setContentCompressionResistancePriority(_ value: UILayoutPriority, for axis: NSLayoutConstraintAxis) { compression[axis] = value }
    var widthAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "width") }
    var heightAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "height") }
    var centerXAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "centerX") }
    var centerYAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "centerY") }
    var leadingAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "leading") }
    var trailingAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "trailing") }
    var topAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "top") }
    var bottomAnchor: BoundaryAnchor { BoundaryAnchor(owner: ObjectIdentifier(self), attribute: "bottom") }
}
final class UILabel: UIView {
    enum Alignment { case left, center, right }
    var text: String?, font: UIFont?, textColor: UIColor?
    var textAlignment = Alignment.left
    var numberOfLines = 1
    func sizeThatFits(_ size: CGSize) -> CGSize {
        let font = font ?? UIFont(pointSize: 13)
        return CGSize(width: CGFloat(text?.count ?? 0) * font.pointSize * 0.64, height: font.lineHeight)
    }
    override var intrinsicContentSize: CGSize { sizeThatFits(CGSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)) }
}
final class UIStackView {
    enum Axis { case vertical, horizontal }
    enum Alignment { case leading, top, center, trailing }
    var axis = Axis.horizontal, alignment = Alignment.top, isHidden = false
}
struct NSDirectionalEdgeInsets {
    var top: CGFloat, leading: CGFloat, bottom: CGFloat, trailing: CGFloat
}
struct TextAttributes { var font: UIFont? }
struct UIConfigurationTextAttributesTransformer {
    let transform: (TextAttributes) -> TextAttributes
    init(_ transform: @escaping (TextAttributes) -> TextAttributes) { self.transform = transform }
}
struct UIImage {
    struct SymbolConfiguration {
        enum Weight { case regular }
        init(pointSize: CGFloat, weight: Weight) {}
    }
    let name: String
    var mirrors = false
    init?(systemName: String, withConfiguration: SymbolConfiguration) { name = systemName }
    func imageFlippedForRightToLeftLayoutDirection() -> Self { var copy = self; copy.mirrors = true; return copy }
}
final class UIButton: UIView {
    enum ButtonType { case system }
    struct Configuration {
        enum Placement { case leading }
        enum LineBreak { case byWordWrapping }
        var title: String?, image: UIImage?, imagePlacement = Placement.leading
        var imagePadding: CGFloat = 0, titleAlignment = Placement.leading
        var titleLineBreakMode = LineBreak.byWordWrapping
        var contentInsets: NSDirectionalEdgeInsets?, baseForegroundColor: UIColor?
        var titleTextAttributesTransformer: UIConfigurationTextAttributesTransformer?
        static func plain() -> Self { Self() }
    }
    var configuration: Configuration?
    init(type: ButtonType) { super.init() }
    required init?(coder: NSCoder) { fatalError("test boundary") }
}
struct RichText { var text: String, entities: [String] }
final class UITextView {
    var isSelectable = false
    var attributedText: RichText?
}
struct Category { var isAccessibilityCategory = false }
struct Traits { var preferredContentSizeCategory = Category() }
struct ListTheme {
    var itemBlocksBackgroundColor = UIColor(name: "card")
    var itemPrimaryTextColor = UIColor(name: "primary")
    var itemSecondaryTextColor = UIColor(name: "secondary")
    var itemAccentColor = UIColor(name: "accent")
    var itemBlocksSeparatorColor = UIColor(name: "separator")
}
struct Theme { var list = ListTheme() }
struct ListsFontSize { var baseDisplaySize: CGFloat = 17 }
struct NagramiXMessageRevision { let text: String, entities: [String], timestamp: Int32 }
func stringWithAppliedEntities(_ text: String, entities: [String], baseColor: UIColor,
    linkColor: UIColor, baseFont: UIFont, linkFont: UIFont, boldFont: UIFont,
    italicFont: UIFont, boldItalicFont: UIFont, fixedFont: UIFont, blockQuoteFont: UIFont,
    message: String?) -> RichText { RichText(text: text, entities: entities) }
'''

CELL_BOUNDARY = r'''
extension PresentationStrings {
    var baseLanguageCode: String { primaryComponent.languageCode }
    var Conversation_ContextMenuCopy: String { "Copy" }
    var Conversation_ContextMenuForward: String { "Forward" }
}
struct PresentationData { var theme = Theme(), listsFontSize = ListsFontSize(); let strings: PresentationStrings }
'''


def contract(source):
    plan = checked_plan(STAGE)
    assert set(plan['inputs']) == {UI}
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    before = (ROOT / 'ios' / plan['previous'][UI]).read_text()
    after = (source / UI).read_text()
    # Snapshot/export/storage behavior is outside this visual task.
    marker = 'final class NagramiXEditHistoryController:'
    assert before[before.index(marker):] == after[after.index(marker):]
    for marker in ('func nagramiXEditHistorySnapshot(', '    @objc private func copyPressed()', '    @objc private func forwardPressed()'):
        assert block(before, marker) == block(after, marker), marker
    old_configure, configure = (block(text, '    func configure(') for text in (before, after))
    marker = '        let formatter = DateFormatter()'
    assert old_configure[old_configure.index(marker):] == configure[configure.index(marker):]
    # Existing text/actions and native layout direction remain unchanged.
    for line in ('self.heading.numberOfLines = 0', 'self.headerStack.addArrangedSubview(self.heading)',
                 'self.headerStack.addArrangedSubview(self.counterBadge)', 'self.headerStack.spacing = 8.0',
                 'self.actions.distribution = .fillEqually', 'self.card.layer.cornerRadius = 20.0',
                 'UIStackView(arrangedSubviews: [self.headerStack, self.date, self.textView, self.divider, self.actions])'):
        assert line in before and line in after, line
    assert after.count('constraint(greaterThanOrEqualToConstant: 44.0)') == 2
    assert 'self.counterBadge.layer.cornerRadius = 10.0' not in after
    assert 'adjustsFontSizeToFitWidth' not in after and 'minimumScaleFactor' not in after
    assert 'self.counter.text = ordinal' in configure
    assert 'numberFormatter.locale = Locale(identifier: strings.baseLanguageCode)' in configure
    assert 'numberFormatter.usesGroupingSeparator = false' in configure
    assert 'self.headerStack.axis = .horizontal' in configure
    assert 'self.headerStack.alignment = .top' in configure
    return plan, after


def fixture(source, text):
    badge = block(text, 'private final class NagramiXEditHistoryCounterBadge:').replace('private ', '')
    cell = block(text, 'private final class NagramiXEditHistoryCell:')
    props = cell[cell.index('{') + 1:cell.index('    override init(style:')].replace('private ', '')
    configure = block(cell, '    func configure(')
    callbacks = '\n'.join(block(cell, marker).replace('@objc private ', '') for marker in ('    @objc private func copyPressed()', '    @objc private func forwardPressed()'))
    catalogs = {}
    for path in sorted((source / 'submodules/NagramiXCore/Resources').glob('*.lproj/Localizable.strings')):
        values = strings(path)
        catalogs[path.parent.name.removesuffix('.lproj')] = {key: values[key] for key in ('NagramiX.Messages.SavedVersion', 'NagramiX.Messages.CurrentVersion', 'NagramiX.Messages.RevisionWithoutText')}
    assert len(catalogs) == 71
    literal = '[' + ',\n'.join(json.dumps(language) + ': [' + ', '.join(json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False) for key, value in values.items()) + ']' for language, values in catalogs.items()) + ']'
    return real_extensions(source) + GEOMETRY_BOUNDARY + CELL_BOUNDARY + badge + '\nfinal class CellBoundary {\nvar traitCollection = Traits()\n' + props + configure + '\n' + callbacks + '\n}\nlet catalogs: [String: [String: String]] = ' + literal + '\n' + TESTS


TESTS = r'''
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fputs("Badge regression: \(message)\n", stderr); exit(91) }
    checks += 1
}
func localizedOrdinal(_ value: Int, _ language: String) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.locale = Locale(identifier: language)
    formatter.usesGroupingSeparator = false
    return formatter.string(from: NSNumber(value: value))!
}
@main enum BadgeTests {
    static func main() {
        for text in ["1", "9", "99", "100", "3000", "١٢٣", "۱۲۳۴۵", "1000000"] {
            for size: CGFloat in [13, 20, 40, 52] {
                let badge = NagramiXEditHistoryCounterBadge(frame: .zero)
                badge.label.text = text; badge.label.font = Font.semibold(size)
                let metrics = badge.label.intrinsicContentSize
                let actual = badge.intrinsicContentSize
                check(actual.width == actual.height && actual.width >= 28, "badge has equal width and height")
                check(actual.width >= metrics.width + 16 && actual.height >= metrics.height + 8, "all digits fit with label padding")
                check(actual.width >= (metrics.width * metrics.width + metrics.height * metrics.height).squareRoot() + 8, "glyph corners fit inside circle")
                badge.bounds = CGRect(origin: .zero, size: actual); badge.layoutSubviews()
                check(badge.layer.cornerRadius == actual.width / 2, "circle radius tracks bounds")
                check(badge.layer.cornerCurve == .circular, "circle never uses squircle corners")
                check(badge.label.textAlignment == .center && badge.label.numberOfLines == 1, "one centered ordinal")
                check(!badge.isAccessibilityElement && !badge.label.isAccessibilityElement && !badge.isUserInteractionEnabled, "badge does not steal gestures or duplicate VoiceOver")
                for axis in [NSLayoutConstraintAxis.horizontal, .vertical] {
                    check(badge.hugging[axis] == .required && badge.compression[axis] == .required, "badge cannot stretch or compress in header stack")
                }
                let owner = ObjectIdentifier(badge), label = ObjectIdentifier(badge.label)
                let constraints = NSLayoutConstraint.activated.filter { $0.first.owner == owner || $0.first.owner == label }
                check(constraints.contains { $0.first.owner == owner && $0.first.attribute == "width" && $0.relation == .equal && $0.second.owner == owner && $0.second.attribute == "height" }, "explicit circle aspect constraint")
                for axis in ["centerX", "centerY"] {
                    check(constraints.contains { $0.first.owner == label && $0.first.attribute == axis && $0.relation == .equal && $0.second.owner == owner && $0.second.attribute == axis }, "glyph centered on both axes")
                }
                for (side, relation, inset) in [("leading", NSLayoutConstraint.Relation.minimum, CGFloat(8)), ("trailing", .maximum, -8), ("top", .minimum, 4), ("bottom", .maximum, -4)] {
                    check(constraints.contains { $0.first.owner == label && $0.first.attribute == side && $0.relation == relation && $0.second.owner == owner && $0.second.attribute == side && $0.constant == inset }, "glyph insets constrain all edges")
                }
            }
        }
        for (language, dictionary) in catalogs {
            let strings = PresentationStrings(language: language, dictionary: dictionary)
            var data = PresentationData(strings: strings)
            let cell = CellBoundary()
            var copied: [String] = [], forwarded: [String] = []
            let old = NagramiXMessageRevision(text: "A 👩🏽‍💻 https://example.org", entities: ["bold", "url"], timestamp: 1794177034)
            let current = NagramiXMessageRevision(text: "B", entities: ["italic"], timestamp: 1794177047)
            func configure(_ revision: NagramiXMessageRevision, _ index: Int, _ count: Int, _ export: Bool = true, _ forward: Bool = true) {
                cell.configure(revision: revision, index: index, count: count, presentationData: data,
                    canExport: export, canForward: forward, copy: { copied.append(revision.text) }, forward: { forwarded.append(revision.text) })
            }
            let one = localizedOrdinal(1, language), two = localizedOrdinal(2, language), large = localizedOrdinal(3000, language)
            configure(old, 0, 2)
            check(cell.heading.text == strings.nagramiXSavedVersion && cell.counter.text == one, "application language numeral and saved heading")
            check(!cell.counter.text!.contains("/"), "visible ordinal has no total fraction")
            check(cell.counterBadge.backgroundColor == data.theme.list.itemSecondaryTextColor.withAlphaComponent(0.18) && cell.counter.textColor == data.theme.list.itemPrimaryTextColor, "saved badge uses neutral circle with readable numeral")
            check(cell.heading.accessibilityLabel == strings.nagramiXSavedVersion + ", " + one + " / " + two, "VoiceOver retains full revision position")
            check(cell.textView.attributedText?.text == old.text && cell.textView.attributedText?.entities == old.entities, "selected version text and entities")
            check(!cell.copyButton.isHidden && !cell.forwardButton.isHidden && !cell.actions.isHidden && !cell.divider.isHidden && cell.textView.isSelectable, "ordinary export actions")
            check(cell.actions.axis == .horizontal && cell.headerStack.axis == .horizontal && cell.headerStack.alignment == .top, "ordinary top trailing header and horizontal actions")
            let formatter = DateFormatter(); formatter.locale = Locale(identifier: language); formatter.dateStyle = .medium; formatter.timeStyle = .medium
            check(cell.date.text == formatter.string(from: Date(timeIntervalSince1970: TimeInterval(old.timestamp))), "application-language date")
            check(cell.copyButton.configuration?.image?.name == "doc.on.doc" && cell.forwardButton.configuration?.image?.name == "arrowshape.turn.up.right", "native copy and forward symbols")
            check(cell.forwardButton.configuration?.image?.mirrors == true, "directional symbol follows RTL")
            check(cell.copyButton.configuration?.titleTextAttributesTransformer?.transform(TextAttributes()).font?.pointSize == 17, "configured app font retained")
            cell.copyPressed(); cell.forwardPressed()
            let oldInvalidations = cell.counterBadge.invalidations
            configure(current, 1, 2)
            cell.copyPressed(); cell.forwardPressed()
            check(copied == [old.text, current.text] && forwarded == copied, "reuse replaces both revision callbacks")
            check(cell.heading.text == strings.nagramiXCurrentVersion && cell.counter.text == two, "current visible ordinal")
            check(cell.counterBadge.backgroundColor == data.theme.list.itemAccentColor && cell.counter.textColor == .white, "current badge accent and white numeral")
            check(cell.counterBadge.invalidations == oldInvalidations + 1, "configuration invalidates reused glyph metrics")
            check(cell.copyButton.accessibilityLabel?.contains(two + " / " + two) == true, "VoiceOver action identifies selected revision")
            cell.traitCollection.preferredContentSizeCategory.isAccessibilityCategory = true
            UIFontMetrics.scale = 3
            configure(current, 2999, 3000)
            check(cell.headerStack.axis == .horizontal && cell.headerStack.alignment == .top && cell.actions.axis == .vertical, "accessibility keeps badge top trailing while actions receive full width")
            check(cell.counter.text == large && !cell.counter.text!.contains("/"), "large ordinals have no grouping or total")
            check(cell.counter.font?.pointSize == 39, "badge follows dynamic type instead of shrinking")
            let enlarged = cell.counterBadge.intrinsicContentSize
            check(enlarged.width == enlarged.height && enlarged.width > 28, "large font and ordinal grow a circle")
            cell.traitCollection.preferredContentSizeCategory.isAccessibilityCategory = false
            UIFontMetrics.scale = 1
            configure(old, 0, 3000)
            check(cell.counterBadge.backgroundColor == data.theme.list.itemSecondaryTextColor.withAlphaComponent(0.18) && cell.counter.textColor == data.theme.list.itemPrimaryTextColor, "reuse restores saved badge color")
            check(cell.actions.axis == .horizontal && cell.headerStack.axis == .horizontal, "reuse restores normal actions and keeps badge corner")
            check(cell.counterBadge.intrinsicContentSize.width < enlarged.width, "reuse recalculates smaller ordinal and font")
            data.theme.list.itemAccentColor = UIColor(name: "new-accent")
            data.theme.list.itemPrimaryTextColor = UIColor(name: "new-primary")
            data.theme.list.itemSecondaryTextColor = UIColor(name: "new-secondary")
            configure(current, 1, 2)
            check(cell.counterBadge.backgroundColor == UIColor(name: "new-accent") && cell.counter.textColor == .white, "theme refresh updates current badge")
            configure(old, 0, 2, false)
            check(cell.counter.textColor == UIColor(name: "new-primary") && cell.counterBadge.backgroundColor == UIColor(name: "new-secondary").withAlphaComponent(0.18), "theme refresh updates saved badge")
            check(cell.copyButton.isHidden && cell.forwardButton.isHidden && cell.actions.isHidden && cell.divider.isHidden && !cell.textView.isSelectable, "restricted export remains restricted")
            configure(old, 0, 2, true, false)
            check(!cell.copyButton.isHidden && cell.forwardButton.isHidden && !cell.actions.isHidden && !cell.divider.isHidden, "copy-only permissions")
            configure(NagramiXMessageRevision(text: "", entities: ["stale"], timestamp: 1), 0, 1)
            check(cell.textView.attributedText?.text == strings.nagramiXRevisionWithoutText && cell.textView.attributedText?.entities == [], "empty caption uses localized placeholder without stale entities")
            check(cell.copyButton.isHidden && cell.forwardButton.isHidden && cell.actions.isHidden && cell.divider.isHidden && !cell.textView.isSelectable, "empty version cannot export")
        }
        print("Revision badge geometry/state checks: \(checks); catalogs: \(catalogs.count)")
    }
}
'''


def semantic_negatives(swift):
    changes = [
        ('old-visible-fraction', 'self.counter.text = ordinal', 'self.counter.text = ordinal + " / " + total', 'application language numeral'),
        ('old-stretched-badge', 'return CGSize(width: diameter, height: diameter)', 'return CGSize(width: diameter * 3, height: diameter)', 'badge has equal width and height'),
        ('old-fixed-radius', 'min(self.bounds.width, self.bounds.height) * 0.5', '10.0', 'circle radius tracks bounds'),
        ('missing-aspect-constraint', '            self.widthAnchor.constraint(equalTo: self.heightAnchor),', '', 'explicit circle aspect constraint'),
        ('stale-current-tint', 'isCurrent ? theme.list.itemAccentColor : theme.list.itemSecondaryTextColor.withAlphaComponent(0.18)', 'isCurrent ? theme.list.itemAccentColor : (self.counterBadge.backgroundColor ?? theme.list.itemSecondaryTextColor.withAlphaComponent(0.18))', 'reuse restores saved badge color'),
        ('grouped-ordinal', 'numberFormatter.usesGroupingSeparator = false', 'numberFormatter.usesGroupingSeparator = true', 'large ordinals have no grouping or total'),
        ('wrong-locale', 'numberFormatter.locale = Locale(identifier: strings.baseLanguageCode)', 'numberFormatter.locale = Locale(identifier: "en")', 'application language numeral'),
        ('stale-glyph-size', 'self.counterBadge.invalidateIntrinsicContentSize()', '_ = self.counterBadge', 'configuration invalidates reused glyph metrics'),
    ]
    result = []
    for name, before, after, diagnostic in changes:
        assert swift.count(before) == 1, name
        result.append((name, swift.replace(before, after, 1), diagnostic))
    return result


def execute(swiftc, root, name, text, negative=None):
    path = root / (name + '.swift'); path.write_text(text)
    runs = []
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        binary = root / (name + '-' + mode)
        command = [str(swiftc), '-swift-version', '5', '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(root / 'cache'), *flags, str(path), '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        assert result.returncode == (91 if negative else 0), result.stdout + result.stderr
        assert negative is None or negative in result.stderr, result.stdout + result.stderr
        runs.append({'name': name, 'mode': mode, 'exit_code': result.returncode, 'output': (result.stdout + result.stderr).strip()})
        binary.unlink()
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan, text = contract(args.source)
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='edit-history-number-badges-') as temporary:
        root = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, root / 'guards')
        swift = fixture(args.source, text)
        runs = execute(args.swiftc, root, 'production', swift)
        for name, variant, diagnostic in semantic_negatives(swift):
            runs += execute(args.swiftc, root, name, variant, diagnostic)
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / UI)], check=True)
    assert manifest(args.source) == before
    subprocess.run(['python3', str(args.source / 'build-system/Make/PostboxImportCheck.py'), str(args.source)], check=True)
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'fail_closed': len(rejected), 'executions': runs,
              'interaction_snapshot_controller_bodies': 'byte-identical', 'localization': 'real custom getters and all 71 resource catalogs',
              'source_unchanged_by_checks': True, 'native_postbox_imports': 'passed', 'swift_parse': 1,
              'boundary': 'Production badge class and cell configure; explicit UIKit text metrics and constraint recorder, not Auto Layout solver or pixels.',
              'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

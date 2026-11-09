#!/usr/bin/env python3
"""Проверить карточки редакций и сохранение выбранного snapshot, без UIKit/SDK."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_upstream_13_2_release_string_compile import real_extensions
from validate_localization_standard import strings

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'edit_history_cards'
UI = 'submodules/TelegramUI/Sources/Chat/NagramiXEditHistoryController.swift'


def contract(source):
    plan = checked_plan(STAGE)
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, sha in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == sha, name
    before = (ROOT / 'ios' / plan['previous'][UI]).read_text()
    after = (source / UI).read_text()
    for marker in (
        'func nagramiXEditHistorySnapshot(',
        '    private func refreshPresentationAndLayout()',
        '    func tableView(_ tableView: UITableView, numberOfRowsInSection',
        '    func tableView(_ tableView: UITableView, cellForRowAt',
        '    @objc private func copyPressed()',
        '    @objc private func forwardPressed()',
    ):
        assert block(before, marker) == block(after, marker), marker
    # Archive refresh, subscriptions, formatter entities and the export policy
    # keep their actual production bodies, rather than test-only equivalents.
    start = '        self.updatesDisposable ='
    end = '    private func refreshPresentationAndLayout()'
    assert before[before.index(start):before.index(end)] == after[after.index(start):after.index(end)]
    assert 'nagramiXRevisionArchiveInfo' not in after
    assert 'tableFooterView' not in after and 'tableHeaderView' not in after
    assert 'self.tableView.backgroundView = self.revisions.isEmpty ? self.emptyStateContainer : nil' in after
    assert 'self.tableView.rowHeight = UITableView.automaticDimension' in after
    assert 'UIStackView(arrangedSubviews: [self.headerStack, self.date, self.textView, self.divider, self.actions])' in after
    assert 'self.actions.distribution = .fillEqually' in after
    assert all(after.count('self.actions.addArrangedSubview(self.' + name + ')') == 1 for name in ('copyButton', 'forwardButton'))
    assert after.count('constraint(greaterThanOrEqualToConstant: 44.0)') == 2
    assert 'self.counter.setContentCompressionResistancePriority(.required, for: .horizontal)' in after
    assert 'self.heading.numberOfLines = 0' in after
    assert 'self.copyButton.titleLabel?.numberOfLines = 0' in after
    assert 'self.forwardButton.titleLabel?.numberOfLines = 0' in after
    assert '.byWordWrapping' in after
    assert 'adjustsFontSizeToFitWidth' not in after
    assert 'self.card.layer.cornerRadius = 20.0' in after
    assert 'self.card.layer.cornerCurve = .continuous' in after
    assert 'self.tableView.sectionHeaderTopPadding = 0.0' in after
    assert 'if !self.didApplyInitialLayout, width > 0.0, self.tableView.bounds.height > 0.0' in after
    assert 'self.didApplyInitialLayout = true' in after
    return plan, after


BOUNDARY = r'''
extension PresentationStrings {
    var baseLanguageCode: String { primaryComponent.languageCode }
    var Conversation_ContextMenuCopy: String { "Copy" }
    var Conversation_ContextMenuForward: String { "Forward" }
}
struct UIColor: Equatable {
    let name: String
    var alpha: CGFloat = 1
    static let clear = Self(name: "clear")
    func withAlphaComponent(_ alpha: CGFloat) -> Self { Self(name: name, alpha: alpha) }
}
struct UIFont: Equatable { let pointSize: CGFloat }
enum Font {
    static func regular(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func semibold(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func italic(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func semiboldItalic(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
    static func monospace(_ size: CGFloat) -> UIFont { UIFont(pointSize: size) }
}
struct UIFontMetrics {
    enum Style { case body, caption1 }
    init(forTextStyle: Style) {}
    func scaledFont(for font: UIFont) -> UIFont { font }
}
final class UILabel {
    var text: String?, accessibilityLabel: String?
    var font: UIFont?, textColor: UIColor?
}
final class UIView { var backgroundColor: UIColor?, isHidden = false }
final class UIStackView {
    enum Axis { case vertical, horizontal }
    enum Alignment { case leading, top }
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
final class UIButton {
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
    var configuration: Configuration?, accessibilityLabel: String?, isHidden = false
}
struct RichText { var text: String, entities: [String] }
final class UITextView { var isSelectable = false, attributedText: RichText? }
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
struct PresentationData { var theme = Theme(), listsFontSize = ListsFontSize(); let strings: PresentationStrings }
struct NagramiXMessageRevision { let text: String, entities: [String], timestamp: Int32 }
func stringWithAppliedEntities(_ text: String, entities: [String], baseColor: UIColor,
    linkColor: UIColor, baseFont: UIFont, linkFont: UIFont, boldFont: UIFont,
    italicFont: UIFont, boldItalicFont: UIFont, fixedFont: UIFont, blockQuoteFont: UIFont,
    message: String?) -> RichText { RichText(text: text, entities: entities) }
final class CellBoundary {
    let card = UIView(), counterBadge = UIView(), divider = UIView()
    let heading = UILabel(), counter = UILabel(), date = UILabel()
    let headerStack = UIStackView(), actions = UIStackView(), textView = UITextView()
    let copyButton = UIButton(), forwardButton = UIButton()
    var copyAction: (() -> Void)?, forwardAction: (() -> Void)?
    var traitCollection = Traits()
'''


TESTS = r'''
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    guard condition() else { fputs("Revision regression: \(message)\n", stderr); exit(91) }
    checks += 1
}
@main enum RevisionTests {
    static func main() {
        for (language, dictionary) in catalogs {
            let strings = PresentationStrings(language: language, dictionary: dictionary)
            let data = PresentationData(strings: strings)
            let cell = CellBoundary()
            var copied: [String] = [], forwarded: [String] = []
            let old = NagramiXMessageRevision(text: "A 👩🏽‍💻 https://example.org", entities: ["bold", "url"], timestamp: 1794177034)
            let current = NagramiXMessageRevision(text: "B", entities: ["italic"], timestamp: 1794177047)
            func configure(_ revision: NagramiXMessageRevision, _ index: Int, _ count: Int, _ export: Bool = true, _ forward: Bool = true) {
                cell.configure(revision: revision, index: index, count: count, presentationData: data,
                    canExport: export, canForward: forward, copy: { copied.append(revision.text) }, forward: { forwarded.append(revision.text) })
            }
            configure(old, 0, 2)
            check(cell.heading.text == strings.nagramiXSavedVersion && cell.counter.text == "1 / 2", "saved heading and independent counter")
            check(cell.counterBadge.backgroundColor == .clear, "saved badge is neutral")
            check(cell.textView.attributedText?.text == old.text && cell.textView.attributedText?.entities == old.entities, "selected version text and entities")
            check(!cell.copyButton.isHidden && !cell.forwardButton.isHidden && !cell.actions.isHidden && !cell.divider.isHidden && cell.textView.isSelectable, "ordinary export actions")
            check(cell.actions.axis == .horizontal && cell.headerStack.axis == .horizontal, "ordinary horizontal rows")
            let formatter = DateFormatter(); formatter.locale = Locale(identifier: language); formatter.dateStyle = .medium; formatter.timeStyle = .medium
            check(cell.date.text == formatter.string(from: Date(timeIntervalSince1970: TimeInterval(old.timestamp))), "application-language date")
            check(cell.copyButton.configuration?.image?.name == "doc.on.doc" && cell.forwardButton.configuration?.image?.name == "arrowshape.turn.up.right", "native copy and forward symbols")
            check(cell.forwardButton.configuration?.image?.mirrors == true, "directional symbol follows RTL")
            check(cell.copyButton.configuration?.titleTextAttributesTransformer?.transform(TextAttributes()).font?.pointSize == 17, "configured app font is retained")
            cell.copyPressed(); cell.forwardPressed()
            configure(current, 1, 2)
            cell.copyPressed(); cell.forwardPressed()
            check(copied == [old.text, current.text] && forwarded == copied, "reuse replaces both revision callbacks")
            check(cell.heading.text == strings.nagramiXCurrentVersion && cell.counter.text == "2 / 2", "current heading and counter")
            check(cell.counterBadge.backgroundColor == data.theme.list.itemAccentColor.withAlphaComponent(0.16), "current badge accent")
            check(cell.copyButton.accessibilityLabel?.contains("2 / 2") == true, "VoiceOver identifies selected revision")
            configure(old, 0, 2, false)
            check(cell.copyButton.isHidden && cell.forwardButton.isHidden && cell.actions.isHidden && cell.divider.isHidden && !cell.textView.isSelectable, "restricted export remains restricted")
            configure(old, 0, 2, true, false)
            check(!cell.copyButton.isHidden && cell.forwardButton.isHidden && !cell.actions.isHidden && !cell.divider.isHidden, "copy-only permissions")
            configure(NagramiXMessageRevision(text: "", entities: ["stale"], timestamp: 1), 0, 1)
            check(cell.textView.attributedText?.text == strings.nagramiXRevisionWithoutText && cell.textView.attributedText?.entities == [], "empty caption uses localized placeholder without stale entities")
            check(cell.copyButton.isHidden && cell.forwardButton.isHidden && cell.actions.isHidden && cell.divider.isHidden && !cell.textView.isSelectable, "empty version cannot export")
            cell.traitCollection.preferredContentSizeCategory.isAccessibilityCategory = true
            configure(current, 2999, 3000)
            check(cell.headerStack.axis == .vertical && cell.actions.axis == .vertical, "accessible rows receive full width")
            check(cell.counter.text == "3000 / 3000" && !cell.actions.isHidden && !cell.divider.isHidden, "large history and hidden-state reuse")
            cell.traitCollection.preferredContentSizeCategory.isAccessibilityCategory = false
            configure(old, 0, 3000)
            check(cell.actions.axis == .horizontal && cell.headerStack.axis == .horizontal && cell.counterBadge.backgroundColor == .clear, "reuse restores ordinary layout and neutral badge")
        }
        print("Revision state checks: \(checks); catalogs: \(catalogs.count)")
    }
}
'''


def fixture(source, text):
    production = block(text, '    func configure(')
    callbacks = '\n'.join(block(text, marker).replace('@objc private ', '') for marker in ('    @objc private func copyPressed()', '    @objc private func forwardPressed()'))
    catalogs = {}
    for path in sorted((source / 'submodules/NagramiXCore/Resources').glob('*.lproj/Localizable.strings')):
        values = strings(path)
        catalogs[path.parent.name.removesuffix('.lproj')] = {key: values[key] for key in ('NagramiX.Messages.SavedVersion', 'NagramiX.Messages.CurrentVersion', 'NagramiX.Messages.RevisionWithoutText')}
    assert len(catalogs) == 71
    # Serialize dictionaries with Swift syntax rather than treating JSON as Swift.
    literal = '[' + ',\n'.join(json.dumps(language) + ': [' + ', '.join(json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False) for key, value in values.items()) + ']' for language, values in catalogs.items()) + ']'
    return real_extensions(source) + BOUNDARY + production + '\n' + callbacks + '\n}\nlet catalogs: [String: [String: String]] = ' + literal + '\n' + TESTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan, text = contract(args.source)
    with tempfile.TemporaryDirectory(prefix='edit-history-cards-') as temporary:
        root = Path(temporary)
        rejected = guard_checks(args.source, STAGE, plan, root / 'guards')
        swift = root / 'states.swift'; swift.write_text(fixture(args.source, text))
        runs = []
        for mode, flags in (('debug', []), ('optimized', ['-O'])):
            binary = root / ('states-' + mode)
            command = [str(args.swiftc), '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-module-cache-path', str(root / 'cache'), *flags, str(swift), '-o', str(binary)]
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
            assert result.returncode == 0, result.stdout + result.stderr
            runs.append({'mode': mode, 'output': result.stdout.strip()})
        subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / UI)], check=True)
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']), 'fail_closed': len(rejected), 'executions': runs, 'snapshot_copy_forward_archive_bodies': 'byte-identical', 'localization': 'real custom getters and 71 resource catalogs', 'boundary': 'UIKit configuration state modeled; no Auto Layout solver, pixels or Apple SDK', 'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

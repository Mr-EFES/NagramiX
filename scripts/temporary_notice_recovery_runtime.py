#!/usr/bin/env python3
"""Exercise the existing temporary-media footer contract without an Apple SDK.

The shared bubble's production predicate, measurement and application/cleanup
branches run unchanged. Text metrics and node ownership are explicit adapters;
this does not claim UIKit rendering, native playback or network verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block

ARCHIVE = 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
BUBBLE = 'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift'

# Reviewed source16 bytes. The recovery task must not alter receipt suppression,
# TTL, ordinary cloud reads, approved secret reads, playback or deletion styling.
PROTECTED_SOURCE_HASHES = {
    ARCHIVE: '0d07e0ef8ff0d753a4477c6be33106c75e86bd1beb9701e0a1e2b5d7222b29af',
    'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift': '3a101a9df4262f9eea878273ddeb8d4438c777611b66febb5b3b979c2b281f45',
    'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift': 'b49f7d7be8171b43eb707ee171667fe3bbdca917d3599d5817b28a1342bb1ff7',
    'submodules/TelegramCore/Sources/State/ManagedAutoremoveMessageOperations.swift': 'c9ae6eff6e8e5e3514f55eeacad7c2641dc80f93bcdde8968b2fc278e608afcf',
    'submodules/TelegramCore/Sources/State/ManagedConsumePersonalMessagesActions.swift': '7044329bc98df033c72f10118afc92d3e07231e728ec80c2d09413c6a562db65',
    'submodules/TelegramCore/Sources/State/ManagedSynchronizeConsumeMessageContentsOperations.swift': '6835b27f67d58d0c235b1106b7716a4042fe3509e441ce13878379331e09c37b',
    'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift': '8ccf31e6f2bfe5a93ecad52a533186e7b2b2dab1a6d4cdb716e8259dc646d571',
    'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift': '799209ebea265e540fe22c677f5c9654d4032610fddf5446d1db4575e6715e1d',
    'submodules/TelegramCore/Sources/TelegramEngine/Messages/ApplyMaxReadIndexInteractively.swift': '2c5b45b15e57c0eeca9c0a2ed2ded3f0ff96d35605e75bd2b16e320a111f2e69',
    'submodules/TelegramCore/Sources/State/AccountViewTracker.swift': 'd711817c36850b7332cead2ce0b51669f01c68fd6be4ae851cfeee0ae76ff1c8',
    'submodules/TelegramCore/Sources/State/ManagedSynchronizeMarkAllUnseenPersonalMessagesOperations.swift': '0093761168fc0f4298ee4aaf570b61078b22ca1c9a56b7cdd9af495926f4a546',
    'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift': 'c7ac3830f83f723b8bbb38dc713c5460b5d5c5564bfefbfbf5e9e87b01198985',
    'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift': 'e354b419bfef6eaf299e78c858553d35d30691c7e85dd4125babf99cac957575',
    'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift': 'c8abde0f77376ff4c59172aa73727a3333d2efc351561ccd1da6a9a082b6ed84',
    'submodules/TelegramUI/Components/Chat/ChatMessageInstantVideoBubbleContentNode/Sources/ChatMessageInstantVideoBubbleContentNode.swift': '5c5002093df9d3bd698eca74dd9ac3c7265e87360e2e498157c847c33d73a75c',
    'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveMediaNode/Sources/ChatMessageInteractiveMediaNode.swift': 'e57b09860285bdb0ef1df115ad2aa55178221e552a70cb50e4f3ad6f10912371',
    'submodules/TelegramUI/Sources/SharedMediaPlayer.swift': '632316080cb2f15e5c15e75ab4239605c77c9a6432404b9ab3d4aa678c2d2744',
    'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift': '25aad7b147f1a2094d06822caab4588db4f3e4f9bbbb7857779f5442191f0519',
    'submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift': '441c53d4cfa128523c5af40caa3a529a526f0be73f71e4f10bd70576271cfd64',
    'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift': '186da7c73827f35eb6df0c6f77500b33e9b700f601cc7a8b252490183b4c403f',
    BUBBLE: 'a6192f623096f3db4c83eeb56729abc022de0cc358214f081b588717281de66b',
}


def assert_temporary_contract(source):
    """Return verified source hashes for the parent validator's receipt."""
    source = Path(source)
    for name, expected in PROTECTED_SOURCE_HASHES.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, name
    bubble = (source / BUBBLE).read_text()
    assert 'nagramiXViewOnceReplayLabel' not in bubble
    return dict(PROTECTED_SOURCE_HASHES)


def between(text, start, end):
    assert text.count(start) == 1, start
    assert text.count(end) == 1, end
    left, right = text.index(start), text.index(end)
    assert left < right
    return text[left:right]


def fixture(source):
    """Build a standalone Swift executable from unchanged production branches."""
    source = Path(source)
    archive = (source / ARCHIVE).read_text()
    bubble = (source / BUBBLE).read_text()
    predicate = block(archive, '    var nagramiXShowsArchiveNotice: Bool {')
    measurement = between(bubble, '        var nagramiXDeletedStatusHeight: CGFloat = 0.0',
                          '        var contentSize = CGSize(width: maxContentWidth, height: 0.0)')
    reservation = block(bubble, '        if nagramiXArchivedMessage {\n            // Keep the complete marker')
    apply = between(bubble, '        let nagramiXIsArchived = item.content.firstMessage.nagramiXShowsArchiveNotice',
                    '        strongSelf.updateSearchTextHighlightState()')
    layout_predicate = next(line for line in bubble.splitlines()
                            if line.strip() == 'let nagramiXArchivedMessage = firstMessage.nagramiXShowsArchiveNotice')
    return BOUNDARY + '\npublic extension Message {\n' + predicate + '\n}\n' + '''
func measure(_ item: Item, incoming: Bool) -> (width: CGFloat, height: CGFloat, footer: CGFloat) {
    let firstMessage = item.content.firstMessage
''' + layout_predicate + '''
    var maxContentWidth: CGFloat = 80.0
    let maximumContentWidth: CGFloat = 280.0
''' + measurement + '''
    var contentSize = CGSize(width: maxContentWidth, height: 100.0)
''' + reservation + '''
    return (contentSize.width, contentSize.height, nagramiXDeletedStatusHeight)
}
func applyNotice(_ strongSelf: BubbleNode, _ item: Item, incoming: Bool) {
    let layout = measure(item, incoming: incoming)
    let backgroundFrame = CGRect(x: 0, y: 0, width: layout.width, height: layout.height)
''' + apply + '\n}\n' + TESTS


BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

public protocol MessageAttribute {}
public struct NagramiXArchivedMessageAttribute: MessageAttribute {
    let deletedAt: Int32
    let isTemporary: Bool
    let isViewOnceReplay: Bool
}
struct OtherAttribute: MessageAttribute {}
enum MediaKind: CaseIterable { case voice, round, photo, video }
public struct Message {
    var attributes: [MessageAttribute]
    let kind: MediaKind
}
struct Color: Equatable { let name: String }
struct MessageTheme { let secondaryTextColor: Color }
struct MessageThemes {
    let incoming = MessageTheme(secondaryTextColor: Color(name: "incoming"))
    let outgoing = MessageTheme(secondaryTextColor: Color(name: "outgoing"))
}
struct ChatTheme { let message = MessageThemes() }
struct Theme { let chat = ChatTheme() }
struct ThemeWrapper { let theme = Theme() }
struct Strings {
    let nagramiXDeleted = "Это сообщение было удалено"
    // Available only so an old-branch mutant can compile and be rejected.
    let nagramiXViewOnceReplayLabel = "Одноразовое"
}
struct Presentation { let strings = Strings(); let theme = ThemeWrapper() }
struct Content { let firstMessage: Message }
struct Item { let content: Content; let presentationData = Presentation() }
struct NagramiXTabSettings {
    static var current = NagramiXTabSettings()
    var deletedMessageLabel = ""
}
enum Font { static func semibold(_ size: CGFloat) -> CGFloat { size } }
struct TextOptions: OptionSet {
    let rawValue: Int
    static let usesLineFragmentOrigin = TextOptions(rawValue: 1)
    static let usesFontLeading = TextOptions(rawValue: 2)
}
// Deterministic metrics stand in for UIKit; only production control flow,
// label selection, reserved geometry and ownership are under test.
struct NSAttributedString {
    let string: String
    let font: CGFloat
    let textColor: Color
    func size() -> CGSize { CGSize(width: CGFloat(string.count) * 6.0, height: 14.0) }
    func boundingRect(with size: CGSize, options: TextOptions, context: Any?) -> CGRect {
        let lines = max(1.0, ceil(self.size().width / max(1.0, size.width)))
        return CGRect(x: 0, y: 0, width: min(self.size().width, size.width), height: lines * 14.0)
    }
}
final class Layer { var allowsGroupOpacity = false }
class Node {
    var alpha: CGFloat = 1.0
    var frame = CGRect.zero
    var isUserInteractionEnabled = true
    let layer = Layer()
    weak var supernode: Node?
    var children: [Node] = []
    var removals = 0
    func addSubnode(_ node: Node) { node.supernode = self; children.append(node) }
    func removeFromSupernode() {
        supernode?.children.removeAll { $0 === self }
        supernode = nil
        removals += 1
    }
}
final class ImmediateTextNode: Node {
    var maximumNumberOfLines = 1
    var attributedText: NSAttributedString?
    func updateLayout(_ size: CGSize) -> CGSize {
        attributedText!.boundingRect(with: size, options: [], context: nil).size
    }
}
struct UIImage: Equatable { let bundleImageName: String }
func generateTintedImage(image: UIImage, color: Color) -> UIImage { image }
final class ASImageNode: Node { var image: UIImage? }
final class ContextSource { let contentNode = Node() }
final class BubbleNode {
    let backgroundNode = Node(), backgroundWallpaperNode = Node(), shadowNode = Node(), clippingNode = Node()
    var backgroundHighlightNode: Node? = Node(), actionButtonsNode: Node? = Node(), reactionButtonsNode: Node? = Node()
    let mainContextSourceNode = ContextSource()
    var nagramiXOriginalClippingGroupOpacity: Bool?
    var nagramiXDeletedStatusNode: ImmediateTextNode?
    var nagramiXDeletedStatusIconNode: ASImageNode?
    var presentedLayers: [Node] {
        [backgroundNode, backgroundWallpaperNode, shadowNode, clippingNode,
         backgroundHighlightNode!, actionButtonsNode!, reactionButtonsNode!]
    }
}
'''


TESTS = r'''
@main struct TemporaryNoticeTests {
    static func main() {
        var checks = 0
        func check(_ value: @autoclosure () -> Bool, _ label: String) {
            if !value() {
                FileHandle.standardError.write(Data(("Temporary notice regression: " + label + "\n").utf8))
                exit(97)
            }
            checks += 1
        }
        let defaultLabel = Strings().nagramiXDeleted
        for kind in MediaKind.allCases { for incoming in [false, true] {
            for custom in ["", "Мой архив", String(repeating: "Длинная подпись ", count: 5), "Одноразовое"] {
                NagramiXTabSettings.current.deletedMessageLabel = custom
                let expectedLabel = custom.isEmpty ? defaultLabel : custom
                let live = Item(content: Content(firstMessage: Message(attributes: [
                    OtherAttribute(), NagramiXArchivedMessageAttribute(deletedAt: 0, isTemporary: true, isViewOnceReplay: true)
                ], kind: kind)))
                let deleted = Item(content: Content(firstMessage: Message(attributes: [
                    OtherAttribute(), NagramiXArchivedMessageAttribute(deletedAt: 500, isTemporary: true, isViewOnceReplay: true)
                ], kind: kind)))
                check(!live.content.firstMessage.nagramiXShowsArchiveNotice, "live retained media has no deletion notice")
                check(deleted.content.firstMessage.nagramiXShowsArchiveNotice, "actual deletion shows notice")
                let liveLayout = measure(live, incoming: incoming)
                check(liveLayout.footer == 0 && liveLayout.height == 100 && liveLayout.width == 80,
                      "live retained media reserves no footer height or label width")
                let deletedLayout = measure(deleted, incoming: incoming)
                check(deletedLayout.footer >= 16 && deletedLayout.height == 100 + deletedLayout.footer,
                      "real deletion reserves measured footer height")
                check(deletedLayout.width >= 80 && deletedLayout.width <= 280,
                      "deletion footer uses native width limit")
                let node = BubbleNode()
                applyNotice(node, live, incoming: incoming)
                check(node.nagramiXDeletedStatusNode == nil && node.nagramiXDeletedStatusIconNode == nil
                      && node.mainContextSourceNode.contentNode.children.isEmpty, "live retained media has no footer nodes")
                check(node.presentedLayers.allSatisfy { $0.alpha == 1 }, "live media stays fully opaque")
                applyNotice(node, deleted, incoming: incoming)
                check(node.presentedLayers.allSatisfy { $0.alpha == 0.5 }, "real deleted media retains 50 percent opacity")
                check(node.clippingNode.layer.allowsGroupOpacity && node.nagramiXOriginalClippingGroupOpacity == false,
                      "deletion composites native layers before dimming")
                let status = node.nagramiXDeletedStatusNode!, icon = node.nagramiXDeletedStatusIconNode!
                check(status.attributedText?.string == expectedLabel, "deletion uses configured or default label")
                check(status.attributedText?.textColor == Color(name: incoming ? "incoming" : "outgoing"),
                      "deletion label uses native incoming or outgoing theme")
                check(status.maximumNumberOfLines == 0 && !status.isUserInteractionEnabled && !icon.isUserInteractionEnabled,
                      "footer permits wrapping without owning gestures")
                check(icon.image?.bundleImageName == "Chat/Context Menu/Delete", "deletion keeps native delete icon")
                check(node.mainContextSourceNode.contentNode.children.count == 2, "one label and one icon are attached")
                applyNotice(node, deleted, incoming: incoming)
                check(node.nagramiXDeletedStatusNode === status && node.nagramiXDeletedStatusIconNode === icon
                      && node.mainContextSourceNode.contentNode.children.count == 2, "relayout reuses footer nodes")
                applyNotice(node, live, incoming: incoming)
                check(node.nagramiXDeletedStatusNode == nil && node.nagramiXDeletedStatusIconNode == nil,
                      "reused live row clears footer references")
                check(status.removals == 1 && icon.removals == 1 && node.mainContextSourceNode.contentNode.children.isEmpty,
                      "reused live row removes label and icon from hierarchy")
                check(node.presentedLayers.allSatisfy { $0.alpha == 1 } && !node.clippingNode.layer.allowsGroupOpacity
                      && node.nagramiXOriginalClippingGroupOpacity == nil, "reuse restores opacity and original group setting")
                applyNotice(node, live, incoming: incoming)
                check(status.removals == 1 && icon.removals == 1, "repeated live layout does not remove stale nodes again")
            }
        } }
        // Ordinary deleted messages keep the same presentation; neither replay
        // eligibility nor the media kind is the deletion predicate.
        for temporary in [false, true] { for replay in [false, true] { for deletedAt: Int32 in [-1, 0, 1] {
            let message = Message(attributes: [NagramiXArchivedMessageAttribute(
                deletedAt: deletedAt, isTemporary: temporary, isViewOnceReplay: replay)], kind: .photo)
            check(message.nagramiXShowsArchiveNotice == (deletedAt > 0), "only positive deletion timestamp controls notice")
        } } }
        let ordinary = Item(content: Content(firstMessage: Message(attributes: [OtherAttribute()], kind: .video)))
        check(!ordinary.content.firstMessage.nagramiXShowsArchiveNotice && measure(ordinary, incoming: true).height == 100,
              "ordinary live media keeps its native height")
        print("Temporary notice regression checks: \(checks)")
    }
}
'''


def semantic_negatives(swift):
    """Regressions must fail executable assertions, with the source untouched."""
    replacements = [
        ('old-live-notice', 'return archived.deletedAt > 0',
         'return archived.deletedAt > 0 || archived.isViewOnceReplay', 'live retained media has no deletion notice'),
        ('old-once-label', 'let label = configuredLabel.isEmpty ? item.presentationData.strings.nagramiXDeleted : configuredLabel',
         'let label = item.content.firstMessage.attributes.contains { ($0 as? NagramiXArchivedMessageAttribute)?.isViewOnceReplay == true } ? item.presentationData.strings.nagramiXViewOnceReplayLabel : (configuredLabel.isEmpty ? item.presentationData.strings.nagramiXDeleted : configuredLabel)',
         'deletion uses configured or default label'),
        ('stale-footer-nodes', 'strongSelf.nagramiXDeletedStatusIconNode?.removeFromSupernode()',
         '// Regression: leave the previous footer icon attached.', 'reused live row removes label and icon from hierarchy'),
    ]
    results = []
    for name, before, after, diagnostic in replacements:
        assert before in swift, name
        results.append((name, swift.replace(before, after), diagnostic))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    hashes = assert_temporary_contract(args.source)
    swift = fixture(args.source)
    runs = []
    with tempfile.TemporaryDirectory(prefix='temporary-notice-recovery-') as temporary:
        root = Path(temporary)
        variants = [('production', swift, None), *semantic_negatives(swift)]
        for name, code, diagnostic in variants:
            path = root / (name + '.swift')
            path.write_text(code)
            for mode, flags in [('debug', []), ('optimized', ['-O'])]:
                binary = root / (name + '-' + mode)
                build = subprocess.run([str(args.swiftc), '-swift-version', '5', '-parse-as-library', '-warnings-as-errors',
                                        '-module-cache-path', str(root / 'cache'), *flags, str(path), '-o', str(binary)],
                                       capture_output=True, text=True)
                assert build.returncode == 0, build.stdout + build.stderr
                result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30,
                                        preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                expected = 0 if diagnostic is None else 97
                assert result.returncode == expected, result.stdout + result.stderr
                assert diagnostic is None or diagnostic in result.stderr, result.stdout + result.stderr
                runs.append({'case': name, 'mode': mode, 'exit_code': result.returncode,
                             'output': (result.stdout + result.stderr).strip()})
    assert assert_temporary_contract(args.source) == hashes
    report = {'protected_source_hashes': hashes, 'executions': runs, 'source_unchanged': True,
              'boundaries': 'Production predicate and shared bubble footer measurement/application/cleanup; text metrics and UI nodes are adapters.',
              'apple_sdk': 'not_run', 'native_playback': 'not_run', 'device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'protected_source_hashes'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

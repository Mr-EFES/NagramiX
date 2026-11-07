#!/usr/bin/env python3
"""Check the production delivery boundaries diagnosed by SDK build182.

The story schema and TextFormat declaration come from the pinned native sources.
Transport/UIKit are narrow doubles; full Apple SDK compilation is mandatory.
"""
import argparse
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile

from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks
from validate_upstream_13_2_release_ui_compile import braced

STAGE = 'upstream_13_2_release_delivery_compile'
COPY = 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift'
FORWARD = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
CONTACTS = 'submodules/ContactListUI/Sources/ContactsController.swift'
ROOT = 'submodules/TelegramUI/Sources/TelegramRootController.swift'
STORIES = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/StoryListContext.swift'
ENGINE = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift'
MEDIA = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Media.swift'
ENTITIES = 'submodules/TextFormat/Sources/GenerateTextEntities.swift'


def story_fixture(text, native):
    fields = ['media', 'music', 'mediaAreas', 'text', 'entities', 'isForwardingDisabled']
    declarations = []
    for name in fields:
        match = re.search(r'^    public let ' + name + r': [^\n]+', native, re.M)
        assert match, name
        declarations.append(match.group(0))
    marker = '                |> mapToSignal { item -> Signal<EngineRawMessage?, NoError> in'
    # The actual story mapping is the first occurrence after getStory.
    start = text.index(marker, text.index('return context.engine.messages.getStory('))
    closure = braced(text, start)
    body = closure[closure.index(' in\n') + 4:-1]
    return r'''
struct NoError: Error {}
struct Signal<T, E: Error> { let value: T; static func single(_ value: T) -> Self { .init(value: value) } }
public protocol Media { var id: Int { get } }
struct Picture: Media { let id: Int }
public struct EngineMedia { let media: Media; func _asMedia() -> Media { media } }
public struct MediaArea {}
public struct MessageTextEntity { let range: Range<Int>; let type: Int }
protocol MessageAttribute {}
struct TextEntitiesMessageAttribute: MessageAttribute { let entities: [MessageTextEntity] }
struct Marker: MessageAttribute {}
struct MessageFlags: OptionSet { let rawValue: Int; static let CopyProtected = Self(rawValue: 1) }
struct EngineRawMessage {
    var text: String
    var media: [Media]
    var attributes: [MessageAttribute]
    var flags: MessageFlags = []
    func withUpdatedText(_ value: String) -> Self { var copy = self; copy.text = value; return copy }
    func withUpdatedMedia(_ value: [Media]) -> Self { var copy = self; copy.media = value; return copy }
    func withUpdatedAttributes(_ value: [MessageAttribute]) -> Self { var copy = self; copy.attributes = value; return copy }
    func withUpdatedFlags(_ value: MessageFlags) -> Self { var copy = self; copy.flags = value; return copy }
}
final class EngineStoryItem {
''' + '\n'.join(declarations) + r'''
    init(music: EngineMedia? = nil, areas: [MediaArea] = [], protected: Bool = false) {
        self.media = EngineMedia(media: Picture(id: 42)); self.music = music; self.mediaAreas = areas
        self.text = "story"; self.entities = [.init(range: 0..<5, type: 2)]; self.isForwardingDisabled = protected
    }
}
struct AccountContext {}
struct PresentationData {}
func nagramiXCopyCard(context: AccountContext, message: EngineRawMessage, presentationData: PresentationData) -> Signal<EngineRawMessage?, NoError> {
    .single(message.withUpdatedText("fallback"))
}
func resolve(item: EngineStoryItem?, message: EngineRawMessage) -> Signal<EngineRawMessage?, NoError> {
    let context = AccountContext(), data = PresentationData()
''' + body + r'''
}
let source = EngineRawMessage(text: "😀", media: [], attributes: [Marker(), TextEntitiesMessageAttribute(entities: [.init(range: 0..<2, type: 1)])])
let copied = resolve(item: EngineStoryItem(protected: true), message: source).value!
precondition(copied.text == "😀\n\nstory" && copied.media.count == 1 && copied.media[0].id == 42)
precondition(copied.flags.contains(.CopyProtected) && copied.attributes.contains { $0 is Marker })
let entities = copied.attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.first!.entities
precondition(entities.count == 2 && entities[0].range == 0..<2 && entities[1].range == 4..<9)
let empty = EngineRawMessage(text: "", media: [], attributes: [])
let unprefixed = resolve(item: EngineStoryItem(), message: empty).value!
precondition(unprefixed.text == "story" && !unprefixed.flags.contains(.CopyProtected))
precondition(resolve(item: nil, message: source).value!.text == "fallback")
precondition(resolve(item: EngineStoryItem(music: .init(media: Picture(id: 5))), message: source).value!.text == "fallback")
precondition(resolve(item: EngineStoryItem(areas: [MediaArea()]), message: source).value!.text == "fallback")
print("PASS: native story object unwrap, media unwrap, UTF16 entities, protection and rich/unavailable fallback")
'''


def ack_fixture(copy, forward):
    helper = block(copy, 'func nagramiXCopyEnqueueAcknowledgement(')
    anchor = forward.index('(accepted: [[EngineMessage.Id?]]) in')
    start = forward.index('                                        for index in peers.indices {', anchor)
    loop = braced(forward, start)
    return r'''
struct MessageId: Equatable { let value: Int }
enum EngineMessage { typealias Id = MessageId }
struct Strings {}
struct PresentationData { let strings = Strings(); let nameDisplayOrder = 0 }
struct EnginePeer { let id: Int; func displayTitle(strings: Strings, displayOrder: Int) -> String { "peer\(id)" } }
struct NagramiXCopyDeliveryRecipient { let peer: EnginePeer; let messageIds: [MessageId]; let correlationIds: [Int64] }
''' + helper + r'''
final class Probe {
    let presentationData = PresentationData()
    func collect(peers: [EnginePeer], accepted: [[MessageId?]], copyExpectedCounts: [Int], copyRecipientCorrelations: [[Int64]]) -> ([NagramiXCopyDeliveryRecipient], [String]) {
        var recipients: [NagramiXCopyDeliveryRecipient] = []
        var rejectedNames: [String] = []
''' + loop + r'''
        return (recipients, rejectedNames)
    }
}
let a = MessageId(value: 1), b = MessageId(value: 2), c = MessageId(value: 3)
let full = nagramiXCopyEnqueueAcknowledgement([a, b], correlations: [11, 12], expectedCount: 2)
precondition(full.complete && full.pairs.map { $0.0 } == [a, b] && full.pairs.map { $0.1 } == [11, 12])
precondition(!nagramiXCopyEnqueueAcknowledgement([a, nil], correlations: [11, 12], expectedCount: 2).complete)
precondition(!nagramiXCopyEnqueueAcknowledgement([a, b], correlations: [11], expectedCount: 2).complete)
precondition(!nagramiXCopyEnqueueAcknowledgement([a], correlations: [11], expectedCount: 2).complete)
precondition(!nagramiXCopyEnqueueAcknowledgement([a, b], correlations: [11, 12], expectedCount: 1).complete)
precondition(nagramiXCopyEnqueueAcknowledgement([], correlations: [], expectedCount: 0).complete)
let probe = Probe(), peers = [EnginePeer(id: 1), EnginePeer(id: 2)]
let accepted = probe.collect(peers: peers, accepted: [[a, b], [c]], copyExpectedCounts: [2, 1], copyRecipientCorrelations: [[11, 12], [13]])
precondition(accepted.1.isEmpty && accepted.0.count == 2 && accepted.0[0].messageIds == [a, b] && accepted.0[1].messageIds == [c])
let partial = probe.collect(peers: peers, accepted: [[a, nil], [c]], copyExpectedCounts: [2, 1], copyRecipientCorrelations: [[11, 12], [13]])
precondition(partial.1 == ["peer1"] && partial.0.count == 2 && partial.0[0].messageIds == [a] && partial.0[0].correlationIds == [11])
let missing = probe.collect(peers: peers, accepted: [[a, b]], copyExpectedCounts: [2, 1], copyRecipientCorrelations: [[11, 12], [13]])
precondition(missing.1 == ["peer2"] && missing.0.count == 1)
print("PASS: typed recipient acknowledgement counts, nil IDs, correlations, order and partial recipients")
'''


def contacts_fixture(text, root):
    property = '    public var switchToChatsController: (() -> Void)?'
    declaration = property if property in text else ''
    start = text.index('                                if fromSearch {')
    action = braced(text, start)
    start = root.index('        contactsController.switchToChatsController = {')
    wire = braced(root, start)
    return r'''
var events: [String] = []
public final class ContactsController {
''' + declaration + r'''
    func deactivateSearch(animated: Bool) { precondition(!animated); events.append("search") }
    func purpose(fromSearch: Bool) -> () -> Void {
        return { [weak self] in
''' + action + r'''
        }
    }
}
final class RootProbe {
    func openChatsController(activateSearch: Bool) { precondition(!activateSearch); events.append("chats") }
    func wire(_ contactsController: ContactsController) {
''' + wire + r'''
    }
}
let contacts = ContactsController()
var root: RootProbe? = RootProbe()
root!.wire(contacts)
contacts.purpose(fromSearch: false)()
precondition(events.isEmpty)
contacts.purpose(fromSearch: true)()
precondition(events == ["search", "chats"])
events = []; root = nil
contacts.purpose(fromSearch: true)()
precondition(events == ["search"])
events = []
var temporary: ContactsController? = ContactsController()
let abandonedAction = temporary!.purpose(fromSearch: true)
temporary = nil
abandonedAction()
precondition(events.isEmpty)
let settings = ContactsController()
settings.purpose(fromSearch: true)()
precondition(events == ["search"])
print("PASS: root contacts search switches tabs once; default Settings contacts and weak lifetimes preserved")
'''


def entity_scope(source, before, after, compiler, folder):
    native = (source / ENTITIES).read_text()
    options = block(native, 'public struct EnabledEntityTypes:')
    signature = block(native, 'public func generateTextEntities(').split('{', 1)[0]
    core = folder / 'Core.swift'
    core.write_text('public struct MessageTextEntity {}\n')
    fmt = folder / 'Format.swift'
    fmt.write_text('import TelegramCore\n' + options + '\n' + signature + '{ fatalError("unexecuted module-boundary probe") }\n')
    common = [str(compiler), '-module-cache-path', str(folder / 'cache')]
    subprocess.run([*common, '-emit-module', '-module-name', 'TelegramCore', str(core), '-emit-module-path', str(folder / 'TelegramCore.swiftmodule')], check=True)
    subprocess.run([*common, '-I', str(folder), '-emit-module', '-module-name', 'TextFormat', str(fmt), '-emit-module-path', str(folder / 'TextFormat.swiftmodule')], check=True)
    probe = folder / 'Entities.swift'
    for label, text in [('after', after), ('before', before)]:
        call = re.search(r'^        let entities = generateTextEntities[^\n]+', text, re.M).group(0)
        imports = 'import TelegramCore\n' + ('import TextFormat\n' if '\nimport TextFormat\n' in text else '')
        probe.write_text(imports + 'func probe(_ text: String) -> [MessageTextEntity] {\n' + call + '\nreturn entities\n}\n')
        result = subprocess.run([*common, '-I', str(folder), '-typecheck', str(probe)], capture_output=True, text=True)
        if label == 'after':
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode != 0 and "cannot find 'generateTextEntities' in scope" in result.stderr, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = {name: (OVERLAY / snap).read_text() for name, snap in plan['previous'].items()}
    after = {name: (args.source / name).read_text() for name in plan['outputs']}
    native_story = (args.source / STORIES).read_text()
    assert 'public final class EngineStoryItem:' in native_story
    assert 'public let media: EngineMedia\n' in native_story
    assert 'public func getStory(peerId: EnginePeer.Id, id: Int32) -> Signal<EngineStoryItem?, NoError>' in (args.source / ENGINE).read_text()
    assert 'func _asMedia() -> Media {' in (args.source / MEDIA).read_text()
    assert '"//submodules/TextFormat:TextFormat"' in (args.source / 'submodules/TelegramUI/BUILD').read_text()
    assert '(accepted: [[EngineMessage.Id?]]) in' in after[FORWARD]
    assert 'public typealias Id = MessageId' in (args.source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages/Message.swift').read_text()
    assert 'public func enqueueMessages(account: Account, peerId: PeerId, messages: [EnqueueMessage]) -> Signal<[MessageId?], NoError>' in (args.source / 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift').read_text()
    with tempfile.TemporaryDirectory(prefix='nagramix-delivery-sdk-132-') as temporary:
        folder = Path(temporary)
        guards = folder / 'guards'; guards.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guards)
        module = folder / 'modules'; module.mkdir()
        entity_scope(args.source, before[COPY], after[COPY], args.swiftc, module)
        root = (args.source / ROOT).read_text()
        fixtures = [('story', story_fixture(after[COPY], native_story), story_fixture(before[COPY], native_story), "has no member 'item'"),
                    ('contacts', contacts_fixture(after[CONTACTS], root), contacts_fixture(before[CONTACTS], root), "has no member 'switchToChatsController'"),
                    ('ack', ack_fixture(after[COPY], after[FORWARD]), None, None)]
        for label, current, old, diagnostic in fixtures:
            for flags in ([], ['-O']):
                common = [str(args.swiftc), '-module-cache-path', str(folder / 'cache')]
                file = folder / (label + '.swift'); binary = folder / label
                file.write_text(current)
                subprocess.run([*common, '-warnings-as-errors', *flags, str(file), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True)
                if old is not None:
                    file.write_text(old)
                    bad = subprocess.run([*common, '-typecheck', *flags, str(file)], capture_output=True, text=True)
                    assert bad.returncode != 0 and diagnostic in bad.stderr, bad.stderr
                if label == 'ack':
                    original = 'return (pairs, hasExpectedCount && hasAllCorrelations)'
                    for replacement in ('return (pairs, hasExpectedCount)', 'return (Array(pairs.reversed()), hasExpectedCount && hasAllCorrelations)'):
                        mutated = current.replace(original, replacement, 1)
                        assert mutated != current
                        file.write_text(mutated)
                        compiled = subprocess.run([*common, *flags, str(file), '-o', str(binary)], capture_output=True, text=True)
                        assert compiled.returncode == 0, compiled.stderr
                        failed = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                        assert failed.returncode != 0, 'Acknowledgement regression accepted'
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'replacements': 3, 'guards': len(plan['guards']), 'fail_closed': len(rejected), 'production_runtime_executions': 6,
              'native_entity_module_boundary': 'passed;missing import reproduced', 'old_story_and_contacts_errors_reproduced': 4,
              'acknowledgement_regressions_rejected': 4,
              'old_full_module_typecheck_timeout': 'SDK182 diagnostic;isolated scope cannot reproduce timeout',
              'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

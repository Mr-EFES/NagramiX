"""Исполнить общий план пересылки и копий с нативным EnqueueMessage."""
from pathlib import Path

from local_copy_payload_runtime import COPY, POLICY, RETENTION, STAGER
from validate_copy_delivery import clean, model_boundary
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
UI = 'submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift'
DELIVERY = 'submodules/TelegramUI/Sources/Chat/NagramiXCopyDelivery.swift'
ENQUEUE = 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
MANAGER = 'submodules/TelegramCore/Sources/State/PendingMessageManager.swift'


def fixture(source):
    text = model_boundary(source)
    retention = (source / RETENTION).read_text()
    for marker in ('public func nagramiXTemporaryMessagesEnabled()',
                   'private func nagramiXIsTemporaryMessage(attributes:',
                   'private func nagramiXIsSupportedTemporaryMessage(',
                   'public func nagramiXCanRetainTemporaryMessage(_ message: Message)'):
        text += '\n' + clean(block(retention, marker)).replace('UserDefaults.standard', 'LocalCopyDefaultsBoundary.shared')
    text += '\n' + clean((source / POLICY).read_text().split('private enum NagramiXContentCopyFetchError')[0])
    text += '\n' + clean((source / COPY).read_text().split('/// Retrying a rejected copy')[0])
    text += '\n' + clean((source / STAGER).read_text())
    # Keep production EnqueueMessage (including both cases and its transforms).
    # Only media/Postbox values, Speech-free I/O and destination APIs are doubles.
    text = text.replace(block(text, 'struct EnqueueMessage {'), '')
    text = text.replace(block(text, 'extension EnqueueMessage {'), '')
    text = text.replace('struct ForwardSourceInfoAttribute: MessageAttribute {}',
                        'struct ForwardSourceInfoAttribute: MessageAttribute { var messageId = MessageId() }')
    text += '''
final class LocalCopyDefaultsBoundary {
    static let shared = LocalCopyDefaultsBoundary()
    var enabled = false
    func bool(forKey: String) -> Bool { enabled }
}
extension Namespaces.Peer { static let CloudGroup: Int32 = 2 }
extension Namespaces.Message { static let SecretIncoming: Int32 = 7; static let Local: Int32 = 8 }
struct EphemeralOutgoingMessageAttribute: MessageAttribute {}
extension Message { var nagramiXShowsArchiveNotice: Bool { attributes.contains { $0 is NagramiXArchivedMessageAttribute } } }
extension MessageId { var id: Int32 { Int32(clamping: value) } }
enum EnqueueMessageGrouping { case auto }
typealias EngineMessageReplySubject = Int
typealias StoryId = Int
typealias ItemCollectionId = Int
struct TelegramMediaWidget: Media {}
struct TelegramMediaDice: Media {}
struct TelegramMediaInvoice: Media {}
struct TelegramMediaStory: Media {}
struct TelegramMediaGiveaway: Media {}
struct ForwardOptionsMessageAttribute: MessageAttribute { let hideNames: Bool; let hideCaptions: Bool }
'''
    text += '\n' + clean(block((source / RETENTION).read_text(), 'public func nagramiXIsTemporaryMessage(_ message: Message)'))
    enqueue = (source / ENQUEUE).read_text()
    text += '\n' + clean(block(enqueue, 'public enum EnqueueMessage {'))
    text += '\n' + clean(block(enqueue, 'func forwardKeepsSenderHeader('))
    text += '\n' + clean(block((source / DELIVERY).read_text(), 'func nagramiXResolvedTransferMessage('))
    # Run the real native drop_author/drop_media_captions flag decisions.
    pending = (source / MANAGER).read_text()
    start = pending.index('                    if hideSendersNames && !messages.contains')
    end = pending.index('                    if videoTimestamp != nil', start)
    text += '''
func productionForwardFlags(_ source: Message, options: ForwardOptionsMessageAttribute) -> Int32 {
    var flags: Int32 = 0
    let hideSendersNames = options.hideNames, hideCaptions = options.hideCaptions
    let messages: [(Message, Int)] = [(source, 0)]
''' + pending[start:end] + '\n return flags\n}\n'
    text += (ROOT / 'scripts/tests/NagramiXGhostgramAuthorlessTests.swift').read_text()
    return text


def negatives(text):
    variants = [
        ('show-author', 'ForwardOptionsMessageAttribute(hideNames: true, hideCaptions: hideCaptions)',
         'ForwardOptionsMessageAttribute(hideNames: false, hideCaptions: hideCaptions)', 'fast route hides author'),
        ('all-copies', 'if forceLocalMedia { return messages }', 'return messages\n    if forceLocalMedia { return messages }', 'ordinary objects retain the fast path'),
        ('temporary-forward', '!message.containsSecretMedia, !nagramiXIsTemporaryMessage(message),',
         'true, true,', 'temporary source ID never forwarded'),
        ('split-album', 'if let key = message.groupingKey { copiedGroups[message.id.peerId, default: []].insert(key) }',
         'if let key = message.groupingKey, false { copiedGroups[message.id.peerId, default: []].insert(key) }', 'selected album stays on one transport'),
        ('shared-recipient', 'batches.append(batch)', 'batches.append(batches.first ?? batch)', 'recipient copy files remain independent'),
        ('resolved-original-id', 'flags: (info?.flags ?? []).union(.nagramiXCopy)',
         'flags: (info?.flags ?? [])', 'resolved card cannot forward original ID'),
        ('widget-author', ' || $0 is TelegramMediaWidget', '', 'widget cannot leak forced author header'),
        ('drop-author-rpc', 'flags |= (1 << 11)', 'flags |= (1 << 4)', 'native RPC receives drop_author'),
        ('no-forward-retry', '(isCopy || isHiddenForward)', '(isCopy || (isHiddenForward && false))', 'failed fast forward can retry same pending record'),
    ]
    for name, before, after, diagnostic in variants:
        assert text.count(before) == 1, (name, text.count(before))
        # all-copies needs to compile under warnings-as-errors without unreachable code.
        if name == 'all-copies':
            before = 'if forceLocalMedia { return messages }'
            after = 'if forceLocalMedia || !messages.isEmpty { return messages }'
        yield name, text.replace(before, after), diagnostic

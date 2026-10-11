import Foundation
import XCTest
import Postbox
@testable import TelegramCore

final class NagramiXProfileLinkedMessagesTests: XCTestCase {
    private let profile = PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(123))

    private func links(_ text: String, _ entities: [MessageTextEntity] = []) -> [MessageTextEntity] {
        return nagramiXProfileLinkEntities(text: text, entities: entities, linkType: .TextMention(peerId: self.profile))
    }
    private func added(_ entities: [MessageTextEntity]) -> [MessageTextEntity] {
        return entities.filter { if case .TextMention = $0.type { return true }; return false }
    }
    func testUTF16AndMultiline() {
        let text = "👋🏽 Привет\nВторая строка"
        XCTAssertEqual(self.added(self.links(text)), [MessageTextEntity(range: 0..<text.utf16.count, type: .TextMention(peerId: self.profile))])
    }
    func testFormattingBoundariesStayNested() {
        let bold = MessageTextEntity(range: 2..<5, type: .Bold)
        let result = self.links("abcdefgh", [bold])
        XCTAssertTrue(result.contains(bold))
        XCTAssertEqual(self.added(result).map { $0.range }, [0..<2, 2..<5, 5..<8])
    }
    func testExplicitLinkCodeAndEmojiStayUntouched() {
        let entities = [MessageTextEntity(range: 0..<4, type: .TextUrl(url: "https://example.org")), MessageTextEntity(range: 5..<9, type: .Code), MessageTextEntity(range: 10..<12, type: .CustomEmoji(stickerPack: nil, fileId: 1))]
        let result = self.links("link code 🙂 text", entities)
        XCTAssertTrue(entities.allSatisfy { result.contains($0) })
        XCTAssertEqual(self.added(result).map { $0.range }, [12..<17])
    }
    func testNaturalURLAndMentionAreNotRedirected() {
        let text = "See https://example.org and @example now"
        let protectedRanges = [NSRange(location: 4, length: 19), NSRange(location: 28, length: 8)]
        for link in self.added(self.links(text)) {
            for protected in protectedRanges {
                XCTAssertEqual(NSIntersectionRange(NSRange(location: link.range.lowerBound, length: link.range.count), protected).length, 0)
            }
        }
        XCTAssertFalse(self.added(self.links(text)).isEmpty)
    }
    func testInvalidAndSurrogateSplitRangesDoNotAddEntities() {
        let invalid = [MessageTextEntity(range: 1..<2, type: .Bold)]
        XCTAssertEqual(self.links("🙂", invalid), invalid)
        let outside = [MessageTextEntity(range: 0..<100, type: .Bold)]
        XCTAssertEqual(self.links("short", outside), outside)
    }
    func testEntityBudgetAndWhitespace() {
        let entities = (0..<100).map { _ in MessageTextEntity(range: 0..<1, type: .Bold) }
        XCTAssertEqual(self.links("text", entities), entities)
        XCTAssertTrue(self.links(" \n\t").isEmpty)
    }
    func testOriginalForwardAndDisabledMessageStayUnchanged() {
        let source = MessageId(peerId: self.profile, namespace: Namespaces.Message.Cloud, id: 1)
        let forward = EnqueueMessage.forward(source: source, threadId: nil, grouping: .none, attributes: [], correlationId: nil)
        if case .forward = nagramiXProfileLinkedMessage(forward, targetPeerId: self.profile, isSecretChat: false) {} else { XCTFail("Original forwarding must stay native") }
        let message = EnqueueMessage.message(text: "text", attributes: [], inlineStickers: [:], mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])
        if case let .message(text, attributes, _, _, _, _, _, _, _, _) = nagramiXProfileLinkedMessage(message, targetPeerId: nil, isSecretChat: false) {
            XCTAssertEqual(text, "text"); XCTAssertTrue(attributes.isEmpty)
        } else { XCTFail("Message type changed") }
    }
    func testSecretChatUsesEncodableURL() {
        let message = EnqueueMessage.message(text: "text", attributes: [], inlineStickers: [:], mediaReference: nil, threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: nil, correlationId: nil, bubbleUpEmojiOrStickersets: [])
        if case let .message(_, attributes, _, _, _, _, _, _, _, _) = nagramiXProfileLinkedMessage(message, targetPeerId: self.profile, isSecretChat: true) {
            let entities = attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.flatMap { $0.entities }
            XCTAssertEqual(entities, [MessageTextEntity(range: 0..<4, type: .TextUrl(url: "tg://user?id=123"))])
        } else { XCTFail("Message type changed") }
    }
}

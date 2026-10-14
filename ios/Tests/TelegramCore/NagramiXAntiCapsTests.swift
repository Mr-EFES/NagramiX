import Foundation
import XCTest
import Postbox
@testable import TelegramCore

final class NagramiXAntiCapsTests: XCTestCase {
    private func convert(_ text: String, entities: [MessageTextEntity] = []) -> String {
        return nagramiXAntiCapsText(text, entities: entities)?.text ?? text
    }

    func testRussianAndEnglish() {
        XCTAssertEqual(self.convert("ПРИВЕТ ВСЕМ"), "Привет всем")
        XCTAssertEqual(self.convert("HELLO EVERYONE!"), "Hello everyone!")
        XCTAssertEqual(self.convert("  👋🏽 ПРИВЕТ\nВСЕМ 123!"), "  👋🏽 Привет\nвсем 123!")
    }

    func testFourLettersAndMixedCase() {
        for text in ["ДОМ!", "А Б В", "SOS", "1234!!!", "🙂🙂🙂🙂", "Привет ВСЕМ", "ПРИВЕТ всем", "你好世界", ""] {
            XCTAssertNil(nagramiXAntiCapsText(text, entities: []), text)
        }
        XCTAssertEqual(self.convert("А Б В Г!"), "А б в г!")
        XCTAssertEqual(self.convert("ТЕСТ"), "Тест")
    }

    func testLinksAndTokensKeepCaseSensitiveContents() {
        let suffix = " https://example.org/CaseSensitive?Token=ABC @SomeUser #SomeTag /SomeCommand"
        XCTAssertEqual(self.convert("ПРИВЕТ" + suffix), "Привет" + suffix)
        XCTAssertEqual(self.convert("https://example.org/UPPERCASE"), "https://example.org/UPPERCASE")
        // Слова внутри защищённых сущностей не помогают достичь порога.
        XCTAssertEqual(self.convert("SOS @UPPERCASE"), "SOS @UPPERCASE")
    }

    func testCodeLinkLabelAndEmojiAreProtected() {
        let text = "ПРИВЕТ Code LiNk 🙂 ВСЕМ"
        let entities = [
            MessageTextEntity(range: 7..<11, type: .Code),
            MessageTextEntity(range: 12..<16, type: .TextUrl(url: "https://example.org/Case")),
            MessageTextEntity(range: 17..<19, type: .CustomEmoji(stickerPack: nil, fileId: 1)),
        ]
        let result = nagramiXAntiCapsText(text, entities: entities)
        XCTAssertEqual(result?.text, "Привет Code LiNk 🙂 всем")
        XCTAssertEqual(result?.entities, entities)
    }

    func testNestedFormattingAndUnicodeLengthChange() {
        let entities = [
            MessageTextEntity(range: 0..<10, type: .Bold),
            MessageTextEntity(range: 1..<2, type: .Italic),
            MessageTextEntity(range: 5..<9, type: .Spoiler),
        ]
        let result = nagramiXAntiCapsText("AİBC 👋🏽!", entities: entities)
        XCTAssertEqual(result?.text, "Ai\u{307}bc 👋🏽!")
        XCTAssertEqual(result?.entities, [
            MessageTextEntity(range: 0..<11, type: .Bold),
            MessageTextEntity(range: 1..<3, type: .Italic),
            MessageTextEntity(range: 6..<10, type: .Spoiler),
        ])
    }

    func testGreekContextAndSupplementaryAlphabet() {
        XCTAssertEqual(self.convert("ΚΟΣΜΟΣ"), "Κοσμος")
        XCTAssertEqual(self.convert("𐐀𐐁𐐂𐐃"), "𐐀𐐩𐐪𐐫")
        XCTAssertEqual(self.convert("İABC"), "İabc")
    }

    func testLinkEntityMovesAfterUnicodeExpansion() {
        let result = nagramiXAntiCapsText("AİBC Link", entities: [MessageTextEntity(range: 5..<9, type: .TextUrl(url: "https://example.org/Case"))])
        XCTAssertEqual(result?.text, "Ai\u{307}bc Link")
        XCTAssertEqual(result?.entities, [MessageTextEntity(range: 6..<10, type: .TextUrl(url: "https://example.org/Case"))])
    }

    func testInvalidEntityDoesNotDamageText() {
        for range in [1..<2, 0..<100, -1..<2, 2..<2] {
            XCTAssertNil(nagramiXAntiCapsText("🙂ПРИВЕТ", entities: [MessageTextEntity(range: range, type: .Bold)]))
        }
    }

    func testDefaultOffAndNativeForwardRemainUntouched() {
        let message = self.message("ПРИВЕТ ВСЕМ")
        if case let .message(text, _, _, _, _, _, _, _, _, _) = nagramiXAntiCapsMessage(message, enabled: false) {
            XCTAssertEqual(text, "ПРИВЕТ ВСЕМ")
        } else { XCTFail("Изменился тип сообщения") }
        let peer = PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(123))
        let forward = EnqueueMessage.forward(source: MessageId(peerId: peer, namespace: Namespaces.Message.Cloud, id: 1), threadId: nil, grouping: .none, attributes: [], correlationId: nil)
        if case .forward = nagramiXAntiCapsMessage(forward, enabled: true) {} else { XCTFail("Изменилась штатная пересылка") }
    }

    func testUnicodeExpansionDoesNotExceedServerLimit() {
        var limits = UserLimitsConfiguration.defaultValue
        limits.maxMessageLength = 4
        if case let .message(text, _, _, _, _, _, _, _, _, _) = nagramiXAntiCapsMessage(self.message("AİBC"), enabled: true, limits: limits) {
            XCTAssertEqual(text, "AİBC")
        } else { XCTFail("Изменился тип сообщения") }
        limits.maxMessageLength = 5
        if case let .message(text, _, _, _, _, _, _, _, _, _) = nagramiXAntiCapsMessage(self.message("AİBC"), enabled: true, limits: limits) {
            XCTAssertEqual(text, "Ai\u{307}bc")
        } else { XCTFail("Изменился тип сообщения") }
    }

    func testMessageMetadataAndFormattingStayIntact() {
        let message = self.message("ПРИВЕТ ВСЕМ", entities: [MessageTextEntity(range: 0..<6, type: .Bold)])
        let converted = nagramiXAntiCapsMessage(message, enabled: true)
        if case let .message(text, attributes, _, _, threadId, _, _, grouping, correlation, _) = converted {
            XCTAssertEqual(text, "Привет всем")
            XCTAssertEqual(threadId, 10)
            XCTAssertEqual(grouping, 20)
            XCTAssertEqual(correlation, 30)
            XCTAssertEqual(attributes.compactMap { $0 as? TextEntitiesMessageAttribute }.first?.entities, [MessageTextEntity(range: 0..<6, type: .Bold)])
        } else { XCTFail("Изменился тип сообщения") }
    }

    func testCaptionKeepsMediaAndUsesCaptionLimit() {
        let image = TelegramMediaImage(imageId: MediaId(namespace: Namespaces.Media.LocalImage, id: 1), representations: [], videoRepresentations: [], immediateThumbnailData: nil, emojiMarkup: nil, reference: nil, partialReference: nil, flags: [], video: nil)
        let message = EnqueueMessage.message(text: "AİBC", attributes: [], inlineStickers: [:], mediaReference: .standalone(media: image), threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: 20, correlationId: 30, bubbleUpEmojiOrStickersets: [])
        var limits = UserLimitsConfiguration.defaultValue
        limits.maxCaptionLength = 4
        if case let .message(text, _, _, reference, _, _, _, grouping, correlation, _) = nagramiXAntiCapsMessage(message, enabled: true, limits: limits) {
            XCTAssertEqual(text, "AİBC")
            XCTAssertEqual(reference?.media.id, image.id)
            XCTAssertEqual(grouping, 20)
            XCTAssertEqual(correlation, 30)
        } else { XCTFail("Изменился тип сообщения") }
        limits.maxCaptionLength = 5
        if case let .message(text, _, _, reference, _, _, _, _, _, _) = nagramiXAntiCapsMessage(message, enabled: true, limits: limits) {
            XCTAssertEqual(text, "Ai\u{307}bc")
            XCTAssertEqual(reference?.media.id, image.id)
        } else { XCTFail("Изменился тип сообщения") }
    }

    private func message(_ text: String, entities: [MessageTextEntity] = []) -> EnqueueMessage {
        return .message(text: text, attributes: entities.isEmpty ? [] : [TextEntitiesMessageAttribute(entities: entities)], inlineStickers: [:], mediaReference: nil, threadId: 10, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: 20, correlationId: 30, bubbleUpEmojiOrStickersets: [])
    }
}

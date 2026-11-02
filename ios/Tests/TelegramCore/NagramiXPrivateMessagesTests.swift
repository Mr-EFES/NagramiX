import Foundation
import XCTest
import Postbox
import TelegramApi
@testable import TelegramCore

final class NagramiXPrivateMessagesTests: XCTestCase {
    private func peer(_ value: Int64) -> PeerId {
        return PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(value))
    }

    private func sticker(mimeType: String = "image/webp", extra: [TelegramMediaFileAttribute] = []) -> TelegramMediaFile {
        return TelegramMediaFile(fileId: MediaId(namespace: Namespaces.Media.CloudFile, id: 42), partialReference: nil, resource: LocalFileMediaResource(fileId: 42), previewRepresentations: [], videoThumbnails: [], immediateThumbnailData: nil, mimeType: mimeType, size: 1234, attributes: [.FileName(fileName: "sticker"), .Sticker(displayText: "🙂", packReference: .id(id: 10, accessHash: 20), maskData: nil), .ImageSize(size: PixelDimensions(width: 512, height: 512))] + extra, alternativeRepresentations: [])
    }

    private func message(_ file: TelegramMediaFile) -> EnqueueMessage {
        return .message(text: "", attributes: [], inlineStickers: [:], mediaReference: .standalone(media: file), threadId: 11, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: 22, correlationId: 33, bubbleUpEmojiOrStickersets: [])
    }

    func testStaticAnimatedAndVideoStickersKeepBytesAndIdentityOfPackSource() {
        for mime in ["image/webp", "application/x-tgsticker", "video/webm"] {
            let original = self.sticker(mimeType: mime, extra: mime == "application/x-tgsticker" ? [.Animated] : [])
            let converted = nagramiXAnonymousStickerMessage(self.message(original), enabled: true)
            guard case let .message(_, attributes, _, reference, thread, _, _, grouping, correlation, _) = converted,
                  let copy = reference?.media as? TelegramMediaFile else { return XCTFail("Пропало вложение") }
            XCTAssertEqual(copy.fileId.namespace, Namespaces.Media.LocalFile)
            XCTAssertNotEqual(copy.fileId, original.fileId)
            XCTAssertEqual(copy.resource.id.stringRepresentation, original.resource.id.stringRepresentation)
            XCTAssertEqual(copy.mimeType, mime)
            XCTAssertEqual(copy.size, original.size)
            XCTAssertTrue(copy.isSticker)
            XCTAssertEqual(copy.attributes, nagramiXAnonymousStickerAttributes(original.attributes))
            XCTAssertEqual(thread, 11)
            XCTAssertEqual(grouping, 22)
            XCTAssertEqual(correlation, 33)
            let source = attributes.compactMap { $0 as? NagramiXAnonymousStickerMessageAttribute }.first?.source
            XCTAssertEqual(source?.fileId, original.fileId)
            XCTAssertEqual(source?.attributes, original.attributes)
            for attribute in copy.attributes {
                if case let .Sticker(emoji, pack, _) = attribute {
                    XCTAssertEqual(emoji, "🙂")
                    XCTAssertNil(pack)
                }
            }
        }
    }

    func testOffAndNativeForwardRemainNative() {
        let original = self.sticker()
        if case let .message(_, attributes, _, reference, _, _, _, _, _, _) = nagramiXAnonymousStickerMessage(self.message(original), enabled: false) {
            XCTAssertEqual((reference?.media as? TelegramMediaFile)?.fileId, original.fileId)
            XCTAssertTrue(attributes.isEmpty)
        } else { XCTFail("Изменился тип сообщения") }
        let forward = EnqueueMessage.forward(source: MessageId(peerId: self.peer(1), namespace: Namespaces.Message.Cloud, id: 10), threadId: nil, grouping: .none, attributes: [], correlationId: nil)
        if case .forward = nagramiXAnonymousStickerMessage(forward, enabled: true) {} else { XCTFail("Изменилась пересылка") }
    }

    func testWireStickerAttributeHasEmptySet() {
        let attributes = inputDocumentAttributesFromFileAttributes(nagramiXAnonymousStickerAttributes(self.sticker().attributes))
        var found = false
        for attribute in attributes {
            if case let .documentAttributeSticker(data) = attribute {
                found = true
                XCTAssertEqual(data.alt, "🙂")
                if case .inputStickerSetEmpty = data.stickerset {} else { XCTFail("В API осталась ссылка на набор") }
            }
        }
        XCTAssertTrue(found)
    }

    func testOrdinaryFileIsNotAnonymized() {
        let file = self.sticker().withUpdatedAttributes([.FileName(fileName: "document.webp")])
        if case let .message(_, attributes, _, reference, _, _, _, _, _, _) = nagramiXAnonymousStickerMessage(self.message(file), enabled: true) {
            XCTAssertTrue(attributes.isEmpty)
            XCTAssertEqual((reference?.media as? TelegramMediaFile)?.fileId, file.fileId)
        } else { XCTFail("Изменился тип сообщения") }
    }

    func testRetryKeepsQueuedStickerChoiceAndLocalId() {
        let queued = nagramiXAnonymousStickerMessage(self.message(self.sticker()), enabled: true)
        for enabled in [false, true] {
            guard case let .message(_, _, _, original, _, _, _, _, _, _) = queued,
                  case let .message(_, attributes, _, retried, _, _, _, _, _, _) = nagramiXAnonymousStickerMessage(queued, enabled: enabled) else { return XCTFail("Изменился тип сообщения") }
            XCTAssertEqual((original?.media as? TelegramMediaFile)?.fileId, (retried?.media as? TelegramMediaFile)?.fileId)
            XCTAssertEqual(attributes.filter { $0 is NagramiXAnonymousStickerMessageAttribute }.count, 1)
        }
    }

    func testSourceSurvivesPostboxCodingAndNativeAttributeFilter() {
        initializeAccountManagement()
        let original = self.sticker()
        let attribute = NagramiXAnonymousStickerMessageAttribute(source: original)
        let encoder = PostboxEncoder()
        encoder.encodeRootObject(attribute)
        let decoded = PostboxDecoder(buffer: MemoryBuffer(data: encoder.makeData())).decodeRootObject() as? NagramiXAnonymousStickerMessageAttribute
        XCTAssertEqual(decoded?.source?.fileId, original.fileId)
        XCTAssertEqual(decoded?.source?.attributes, original.attributes)
        for secret in [false, true] {
            XCTAssertTrue(outgoingMessageAttributes(requestedAttributes: [attribute], isSecretChat: secret, peerAutoremoveTimeout: nil).contains { $0 is NagramiXAnonymousStickerMessageAttribute })
        }
    }

    func testOnlyIncomingBlockedAuthorIsHidden() {
        let account = self.peer(1), blocked = self.peer(2), other = self.peer(3)
        XCTAssertTrue(NagramiXBlockedMessageFilter.shouldHide(authorId: blocked, isIncoming: true, accountPeerId: account, blockedAuthorIds: [blocked]))
        XCTAssertFalse(NagramiXBlockedMessageFilter.shouldHide(authorId: other, isIncoming: true, accountPeerId: account, blockedAuthorIds: [blocked]))
        XCTAssertFalse(NagramiXBlockedMessageFilter.shouldHide(authorId: blocked, isIncoming: false, accountPeerId: account, blockedAuthorIds: [blocked]))
        XCTAssertFalse(NagramiXBlockedMessageFilter.shouldHide(authorId: nil, isIncoming: true, accountPeerId: account, blockedAuthorIds: [blocked]))
        XCTAssertFalse(NagramiXBlockedMessageFilter.shouldHide(authorId: account, isIncoming: true, accountPeerId: account, blockedAuthorIds: [account]))
        XCTAssertFalse(NagramiXBlockedMessageFilter.shouldHide(authorId: blocked, isIncoming: true, accountPeerId: account, blockedAuthorIds: []))
    }

    func testBlockChangesWinAgainstStaleFullList() {
        let account = self.peer(1), justUnblocked = self.peer(2), justBlocked = self.peer(3)
        let result = NagramiXBlockedMessageFilter.resolvedAuthors([account, justUnblocked], changes: [justUnblocked: false, justBlocked: true], accountPeerId: account)
        XCTAssertEqual(result, [justBlocked])
    }
}

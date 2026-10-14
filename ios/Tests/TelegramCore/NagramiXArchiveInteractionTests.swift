import XCTest
import Postbox
@testable import TelegramCore

final class NagramiXArchiveInteractionTests: XCTestCase {
    private let peer = PeerId(namespace: Namespaces.Peer.CloudUser, id: PeerId.Id._internalFromInt64Value(10))

    private func message(id: Int32 = 1, text: String = "", media: [Media] = [], archived: Bool = false) throws -> Message {
        let attributes: [MessageAttribute] = archived ? [NagramiXArchivedMessageAttribute(deletedAt: 123, revisions: [])] : []
        let stored = StoreMessage(id: .Id(MessageId(peerId: self.peer, namespace: Namespaces.Message.Cloud, id: id)), customStableId: nil, globallyUniqueId: nil, groupingKey: nil, threadId: nil, timestamp: 100, flags: [.Incoming], tags: [], globalTags: [], localTags: [], forwardInfo: nil, authorId: nil, text: text, attributes: attributes, media: media)
        return try XCTUnwrap(locallyRenderedMessage(message: stored, peers: [:]))
    }

    private func file(round: Bool) -> TelegramMediaFile {
        let attribute: TelegramMediaFileAttribute = round
            ? .Video(duration: 5, size: PixelDimensions(width: 400, height: 400), flags: [.instantRoundVideo], preloadSize: nil, coverTime: nil, videoCodec: nil)
            : .Audio(isVoice: true, duration: 5, title: nil, performer: nil, waveform: nil)
        return TelegramMediaFile(fileId: MediaId(namespace: Namespaces.Media.LocalFile, id: 42), partialReference: nil, resource: LocalFileMediaResource(fileId: 42), previewRepresentations: [], videoThumbnails: [], immediateThumbnailData: nil, mimeType: round ? "video/mp4" : "audio/ogg", size: 1234, attributes: [attribute], alternativeRepresentations: [])
    }

    func testExpiredVoiceAndRoundResolveToFullRetainedMedia() throws {
        for round in [false, true] {
            let expired = try self.message(media: [TelegramMediaExpiredContent(data: round ? .videoMessage : .voiceMessage)])
            let file = self.file(round: round)
            let retained = try self.message(media: [file], archived: true)
            let result = try XCTUnwrap(NagramiXMessageArchive.interactionMessage(id: expired.id, liveMessage: expired, retainedMessage: retained))
            XCTAssertEqual(result.id, expired.id)
            XCTAssertFalse(result.media.contains { $0 is TelegramMediaExpiredContent })
            XCTAssertEqual((result.media.first as? TelegramMediaFile)?.resource.id.stringRepresentation, file.resource.id.stringRepresentation)
            XCTAssertEqual((result.media.first as? TelegramMediaFile)?.isInstantVideo, round)
            XCTAssertFalse(result.containsSecretMedia)
            XCTAssertTrue(result.attributes.contains { $0 is NagramiXArchivedMessageAttribute })
        }
    }

    func testDeletedTextResolvesWithoutPostboxRecord() throws {
        let retained = try self.message(text: "Сохранённый текст", archived: true)
        XCTAssertEqual(NagramiXMessageArchive.interactionMessage(id: retained.id, liveMessage: nil, retainedMessage: retained)?.text, "Сохранённый текст")
    }

    func testActualLiveMessageWinsOverOldSnapshot() throws {
        let live = try self.message(text: "Новый текст")
        let retained = try self.message(text: "Старый текст", archived: true)
        XCTAssertEqual(NagramiXMessageArchive.interactionMessage(id: live.id, liveMessage: live, retainedMessage: retained)?.text, "Новый текст")
    }

    func testLiveProtectionIsNotReplacedByArchivedFlags() throws {
        let live = try self.message(text: "Текст").withUpdatedFlags([.Incoming, .CopyProtected])
        let retained = try self.message(text: "Снимок", archived: true)
        XCTAssertTrue(try XCTUnwrap(NagramiXMessageArchive.interactionMessage(id: live.id, liveMessage: live, retainedMessage: retained)).isCopyProtected())
    }

    func testMissingOrUnmarkedSnapshotDoesNotInventAttachment() throws {
        let expired = try self.message(media: [TelegramMediaExpiredContent(data: .voiceMessage)])
        for retained in [nil, try self.message(media: [self.file(round: false)])] {
            let result = NagramiXMessageArchive.interactionMessage(id: expired.id, liveMessage: expired, retainedMessage: retained)
            XCTAssertTrue(result?.media.first is TelegramMediaExpiredContent)
        }
        XCTAssertNil(NagramiXMessageArchive.interactionMessage(id: expired.id, liveMessage: nil, retainedMessage: nil))
    }

    func testAnotherMessageCannotReplaceSelectedId() throws {
        let first = try self.message(id: 1, media: [TelegramMediaExpiredContent(data: .videoMessage)])
        let other = try self.message(id: 2, media: [self.file(round: true)], archived: true)
        XCTAssertTrue(NagramiXMessageArchive.interactionMessage(id: first.id, liveMessage: first, retainedMessage: other)?.media.first is TelegramMediaExpiredContent)
        XCTAssertNil(NagramiXMessageArchive.interactionMessage(id: first.id, liveMessage: other, retainedMessage: nil))
    }

    func testMixedSelectionKeepsLiveVoiceAndArchivedRoundInOrder() throws {
        let live = try self.message(id: 1, media: [self.file(round: false)])
        let expired = try self.message(id: 2, media: [TelegramMediaExpiredContent(data: .videoMessage)])
        let round = try self.message(id: 2, media: [self.file(round: true)], archived: true)
        let text = try self.message(id: 3, text: "Архив", archived: true)
        let ids = [text.id, expired.id, live.id].sorted()
        let database = [live.id: live, expired.id: expired]
        let archive = [round.id: round, text.id: text]
        let result = ids.compactMap { NagramiXMessageArchive.interactionMessage(id: $0, liveMessage: database[$0], retainedMessage: archive[$0]) }
        XCTAssertEqual(result.map { $0.id }, ids)
        XCTAssertEqual((result[0].media.first as? TelegramMediaFile)?.isVoice, true)
        XCTAssertEqual((result[1].media.first as? TelegramMediaFile)?.isInstantVideo, true)
        XCTAssertEqual(result[2].text, "Архив")
    }
}

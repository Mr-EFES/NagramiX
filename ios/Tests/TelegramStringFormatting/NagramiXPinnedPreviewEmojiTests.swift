import XCTest
import UIKit
import Postbox
import TelegramCore
import TextFormat
@testable import TelegramStringFormatting

final class NagramiXPinnedPreviewEmojiTests: XCTestCase {
    private func preview(_ rich: RichText, media: [MediaId: Media] = [:]) -> NSAttributedString {
        let text = buildInstantPagePreview(blocks: [.paragraph(rich)], environment: InstantPagePreviewEnvironment(label: { _ in "Media" }, formatDate: nil, media: media))
        return styleInstantPagePreview(text, font: .systemFont(ofSize: 15.0), italicFont: .italicSystemFont(ofSize: 15.0), textColor: .black)
    }

    private func file(_ id: Int64) -> TelegramMediaFile {
        return TelegramMediaFile(fileId: MediaId(namespace: Namespaces.Media.CloudFile, id: id), partialReference: nil, resource: LocalFileMediaResource(fileId: id), previewRepresentations: [], videoThumbnails: [], immediateThumbnailData: nil, mimeType: "image/webp", size: nil, attributes: [], alternativeRepresentations: [])
    }

    func testFiveUncachedABCEmojiBecomeNativeAttachmentsAfterResolution() throws {
        let source = self.preview(.concat((1 ... 5).map { .textCustomEmoji(fileId: Int64($0), alt: "🔤") } + [.plain(" Выступление Председателя")]))
        XCTAssertNil(source.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
        XCTAssertEqual(nagramiXPinnedPreviewEmojiFileIds(source), Set((1 ... 5).map { Int64($0) }))
        let files = Dictionary(uniqueKeysWithValues: (1 ... 5).map { (Int64($0), self.file(Int64($0))) })
        let resolved = nagramiXPinnedPreviewApplyingEmojiFiles(source, files: files)
        XCTAssertEqual(resolved.string, source.string)
        for index in 0 ..< 5 {
            let emoji = try XCTUnwrap(resolved.attribute(ChatTextInputAttributes.customEmoji, at: index * 2, effectiveRange: nil) as? ChatTextInputTextCustomEmojiAttribute)
            XCTAssertEqual(emoji.fileId, Int64(index + 1))
            XCTAssertEqual(emoji.file?.fileId, files[Int64(index + 1)]?.fileId)
        }
        XCTAssertTrue(nagramiXPinnedPreviewEmojiFileIds(resolved).isEmpty)
        XCTAssertNil(source.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
    }

    func testPartialUnavailableOrMismatchedResultsKeepReadableFallback() {
        let source = self.preview(.concat([.textCustomEmoji(fileId: 42, alt: "🔤"), .plain(" "), .textCustomEmoji(fileId: 43, alt: "🙂")]))
        let partial = nagramiXPinnedPreviewApplyingEmojiFiles(source, files: [42: self.file(42)])
        XCTAssertEqual(partial.string, source.string)
        XCTAssertNotNil(partial.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
        XCTAssertNil(partial.attribute(ChatTextInputAttributes.customEmoji, at: 3, effectiveRange: nil))
        XCTAssertEqual(nagramiXPinnedPreviewEmojiFileIds(partial), Set([43]))
        let unavailable: [[Int64: TelegramMediaFile]] = [[:], [42: self.file(99)], [99: self.file(42)]]
        for files in unavailable {
            let result = nagramiXPinnedPreviewApplyingEmojiFiles(source, files: files)
            XCTAssertTrue(result.isEqual(to: source))
        }
    }

    func testUnicodeSpoilerAndFormattingRangesSurvive() throws {
        let prefix = "👨‍👩‍👧‍👦 Привет "
        let source = self.preview(.concat([.plain(prefix), .textSpoiler(text: .italic(.textCustomEmoji(fileId: 42, alt: "🔤"))), .plain("\nДальше")]))
        let offset = (prefix as NSString).length
        let result = nagramiXPinnedPreviewApplyingEmojiFiles(source, files: [42: self.file(42)])
        XCTAssertEqual(result.string, source.string)
        XCTAssertEqual(result.attribute(NSAttributedString.Key(rawValue: TelegramTextAttributes.Spoiler), at: offset, effectiveRange: nil) as? Bool, true)
        XCTAssertEqual(result.attribute(.font, at: offset, effectiveRange: nil) as? UIFont, source.attribute(.font, at: offset, effectiveRange: nil) as? UIFont)
        XCTAssertEqual(try XCTUnwrap(result.attribute(ChatTextInputAttributes.customEmoji, at: offset, effectiveRange: nil) as? ChatTextInputTextCustomEmojiAttribute).fileId, 42)
    }

    func testRepeatedIdsResolveOnceAndOrdinaryTextIsNotReplaced() {
        let source = self.preview(.concat([.plain("ABC 🔤 "), .textCustomEmoji(fileId: 42, alt: "🔤"), .textCustomEmoji(fileId: 42, alt: "🔤")]))
        XCTAssertEqual(nagramiXPinnedPreviewEmojiFileIds(source), Set([42]))
        let result = nagramiXPinnedPreviewApplyingEmojiFiles(source, files: [42: self.file(42)])
        XCTAssertEqual(result.string, source.string)
        XCTAssertNil(result.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
        XCTAssertNil(result.attribute(ChatTextInputAttributes.customEmoji, at: 4, effectiveRange: nil))
        var count = 0
        result.enumerateAttribute(ChatTextInputAttributes.customEmoji, in: NSRange(location: 0, length: result.length)) { value, _, _ in
            if value != nil { count += 1 }
        }
        XCTAssertEqual(count, 2)
    }

    func testAlreadyResolvedPageMediaAndEmptyAltKeepNativeBehavior() {
        let file = self.file(42)
        let known = self.preview(.textCustomEmoji(fileId: 42, alt: "🔤"), media: [file.fileId: file])
        XCTAssertTrue(nagramiXPinnedPreviewEmojiFileIds(known).isEmpty)
        XCTAssertNotNil(known.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
        XCTAssertTrue(nagramiXPinnedPreviewApplyingEmojiFiles(known, files: [42: file]).isEqual(to: known))
        let empty = self.preview(.textCustomEmoji(fileId: 42, alt: ""))
        XCTAssertEqual(empty.string, "�")
        let result = nagramiXPinnedPreviewApplyingEmojiFiles(empty, files: [42: file])
        XCTAssertEqual(result.string, empty.string)
        XCTAssertNotNil(result.attribute(ChatTextInputAttributes.customEmoji, at: 0, effectiveRange: nil))
    }
}

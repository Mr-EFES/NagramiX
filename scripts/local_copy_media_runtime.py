#!/usr/bin/env python3
"""Проверить production-условия готового видео и необязательного превью."""
from pathlib import Path

from validate_quick_format import block

UPLOAD = 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift'

BOUNDARY = r'''import Foundation
protocol MessageAttribute {}
struct OutgoingContentInfoFlags: OptionSet { let rawValue: Int; static let nagramiXCopy = Self(rawValue: 2) }
struct OutgoingContentInfoMessageAttribute: MessageAttribute { let flags: OutgoingContentInfoFlags }
struct ForwardSourceInfoAttribute: MessageAttribute {}
struct OutgoingMessageInfoFlags: OptionSet { let rawValue: Int; static let transformedMedia = Self(rawValue: 1) }
struct OutgoingMessageInfoAttribute: MessageAttribute { let flags: OutgoingMessageInfoFlags }
struct PixelDimensions { let width: Int32; let height: Int32 }
enum TelegramMediaFileAttribute {
    case Video(duration: Double, size: PixelDimensions, flags: Int, preloadSize: Int32?, coverTime: Double?, videoCodec: String?)
    case Other
}
protocol MediaResource: AnyObject {}
final class LocalFileReferenceMediaResource: MediaResource {
    let localFilePath: String
    let size: Int64?
    init(_ path: String, _ size: Int64? = nil) { self.localFilePath = path; self.size = size }
}
final class CloudResource: MediaResource {}
struct Representation { let resource: MediaResource }
struct TelegramMediaFile {
    let mimeType: String
    let attributes: [TelegramMediaFileAttribute]
    let previewRepresentations: [Representation]
}
final class MediaBox {
    var complete: [ObjectIdentifier: String] = [:]
    func completedResourcePath(_ resource: MediaResource) -> String? { complete[ObjectIdentifier(resource)] }
}
struct Postbox { let mediaBox: MediaBox }
func smallestImageRepresentation(_ values: [Representation]) -> Representation? { values.first }
'''

TESTS = r'''
var checks = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    if !condition() { fputs("FAIL: \(label)\n", stderr); exit(91) }
    checks += 1
}
@main enum MediaTests {
    static func main() {
        let copy: [MessageAttribute] = [OutgoingContentInfoMessageAttribute(flags: [.nagramiXCopy])]
        let forward: [MessageAttribute] = copy + [ForwardSourceInfoAttribute()]
        let transformed: [MessageAttribute] = [OutgoingMessageInfoAttribute(flags: [.transformedMedia])]
        func video(_ duration: Double = 4, _ width: Int32 = 1280, _ height: Int32 = 720,
                   mime: String = "video/mp4", preview: MediaResource? = nil) -> TelegramMediaFile {
            TelegramMediaFile(mimeType: mime,
                attributes: [.Video(duration: duration, size: .init(width: width, height: height), flags: 0,
                                    preloadSize: nil, coverTime: nil, videoCodec: nil)],
                previewRepresentations: preview.map { [.init(resource: $0)] } ?? [])
        }
        let valid = video()
        check(nagramiXCopyHasFinalVideoMetadata(valid, attributes: copy), "finished copied video avoids needless transform")
        check(!nagramiXCopyHasFinalVideoMetadata(valid, attributes: []), "composer video keeps native transform")
        check(!nagramiXCopyHasFinalVideoMetadata(valid, attributes: forward), "native forward keeps original transform policy")
        check(nagramiXCopyHasFinalVideoMetadata(video(mime: "VIDEO/MP4"), attributes: copy), "video MIME is matched case-insensitively")
        for duration in [0.0, -1, .nan, .infinity, -.infinity] {
            check(!nagramiXCopyHasFinalVideoMetadata(video(duration), attributes: copy), "invalid duration cannot opt out of transform")
        }
        for (width, height): (Int32, Int32) in [(0, 720), (1280, 0), (-1, 720), (1280, -1)] {
            check(!nagramiXCopyHasFinalVideoMetadata(video(4, width, height), attributes: copy), "invalid dimensions keep native transform")
        }
        for mime in ["audio/mp4", "application/octet-stream", "image/jpeg", ""] {
            check(!nagramiXCopyHasFinalVideoMetadata(video(mime: mime), attributes: copy), "nonvideo file cannot bypass transform")
        }
        check(!nagramiXCopyHasFinalVideoMetadata(TelegramMediaFile(mimeType: "video/mp4", attributes: [.Other],
            previewRepresentations: []), attributes: copy), "missing video metadata keeps native transform")
        check(productionAlreadyTransformed(valid, copy), "copy metadata reaches production transform gate")
        check(!productionAlreadyTransformed(valid, []), "fresh composer reaches production transform gate unchanged")
        check(productionAlreadyTransformed(valid, transformed), "existing explicit transformed flag retains stock behavior")

        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("copy-preview-" + UUID().uuidString)
        try! FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        let full = folder.appendingPathComponent("complete.jpg")
        let empty = folder.appendingPathComponent("zero.jpg")
        try! Data([1, 2, 3]).write(to: full)
        try! Data().write(to: empty)
        let missing = folder.appendingPathComponent("missing.jpg")
        let box = MediaBox()
        for resource: MediaResource in [
            LocalFileReferenceMediaResource(full.path), LocalFileReferenceMediaResource(full.path, 3),
        ] {
            check(nagramiXCopyVideoPreviewIsLocal(resource, mediaBox: box), "complete local preview is retained")
            check(productionSelectsThumbnail(video(preview: resource), copy, box), "available copy thumbnail uses native upload")
        }
        for resource: MediaResource in [
            LocalFileReferenceMediaResource(missing.path), LocalFileReferenceMediaResource(empty.path),
            LocalFileReferenceMediaResource(full.path, 4), LocalFileReferenceMediaResource(folder.path), CloudResource(),
        ] {
            check(!nagramiXCopyVideoPreviewIsLocal(resource, mediaBox: box), "missing or incomplete preview cannot start remote fetch")
            check(!productionSelectsThumbnail(video(preview: resource), copy, box), "copy with absent optional preview does not wait for it")
            check(productionSelectsThumbnail(video(preview: resource), [], box), "composer thumbnail retains original native path")
            check(productionSelectsThumbnail(video(preview: resource), forward, box), "forward thumbnail retains original native path")
        }
        let cached = CloudResource()
        box.complete[ObjectIdentifier(cached)] = full.path
        check(nagramiXCopyVideoPreviewIsLocal(cached, mediaBox: box), "completed cache preview is available")
        check(productionSelectsThumbnail(video(preview: cached), copy, box), "completed cached preview uses stock thumbnail upload")
        for path in [empty.path, missing.path, folder.path] {
            box.complete[ObjectIdentifier(cached)] = path
            check(!nagramiXCopyVideoPreviewIsLocal(cached, mediaBox: box), "invalid completed cache path is not used")
        }
        check(!productionSelectsThumbnail(video(), copy, box), "no preview remains optional")
        print("Local copy video/preview checks: \(checks)")
    }
}
'''


def fixture(source: Path) -> str:
    upload = (source / UPLOAD).read_text()
    pieces = [BOUNDARY]
    for marker in ['func nagramiXCopyHasFinalVideoMetadata(', 'func nagramiXCopyVideoPreviewIsLocal(']:
        pieces.append(block(upload, marker))
    start = upload.index('        var alreadyTransformed = nagramiXCopyHasFinalVideoMetadata(')
    end = upload.index('        let transform: Signal<UploadedMediaTransform, NoError>', start)
    pieces.append('func productionAlreadyTransformed(_ file: TelegramMediaFile, _ attributes: [MessageAttribute]) -> Bool {\n'
                  + upload[start:end] + '\nreturn alreadyTransformed\n}\n')
    marker = '                            if let smallestThumbnail = smallestImageRepresentation(media.previewRepresentations),'
    start = upload.index(marker)
    end = upload.index(' {\n', start) + 2
    condition = upload[start:end]
    pieces.append('func productionSelectsThumbnail(_ media: TelegramMediaFile, _ attributes: [MessageAttribute], _ mediaBox: MediaBox) -> Bool {\n'
                  'let postbox = Postbox(mediaBox: mediaBox)\n'
                  + condition + '\nreturn true\n}\nreturn false\n}\n')
    pieces.append(TESTS)
    return '\n'.join(pieces)


def semantic_negatives(swift: str):
    variants = [
        ('transform-composer', 'guard attributes.contains(where: { ($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.nagramiXCopy) == true }),',
         'guard true,', 'composer video keeps native transform'),
        ('remote-preview', '!nagramiXCopyHasFinalVideoMetadata(media, attributes: attributes)\n                                || nagramiXCopyVideoPreviewIsLocal(smallestThumbnail.resource, mediaBox: postbox.mediaBox)',
         'true', 'copy with absent optional preview does not wait for it'),
        ('incomplete-preview', 'return reference?.size == nil || reference?.size == size',
         'return true', 'missing or incomplete preview cannot start remote fetch'),
    ]
    for name, before, after, diagnostic in variants:
        assert swift.count(before) == 1, (name, swift.count(before))
        replacement = swift.replace(before, after)
        if name == 'remote-preview':
            replacement = replacement.replace(' {\nreturn true\n}',
                                              ' {\n_ = postbox\n_ = smallestThumbnail\nreturn true\n}')
        yield name, replacement, diagnostic

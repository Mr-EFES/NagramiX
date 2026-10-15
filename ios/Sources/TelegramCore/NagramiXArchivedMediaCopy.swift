import Foundation
import Postbox

/// Prepares retained attachments for a new native upload, without cloud
/// references to the deleted original. Uncommitted temporary files roll back.
public final class NagramiXArchivedMediaCopy {
    private let mediaBox: MediaBox
    private var resources: [String: LocalFileReferenceMediaResource] = [:]
    private var paths: [String] = []
    private var committed = false

    public init(mediaBox: MediaBox) {
        self.mediaBox = mediaBox
    }

    deinit {
        if !self.committed {
            for path in self.paths {
                try? FileManager.default.removeItem(atPath: path)
            }
        }
    }

    public func commit() {
        self.committed = true
    }

    /// Native sent-media caching may reuse only a newly uploaded copy of this
    /// immutable archive resource, never the deleted original's cloud reference.
    public static func uploadedReferenceHash(resource: MediaResource) -> Data? {
        guard let resource = resource as? LocalFileReferenceMediaResource,
              resource.isUniquelyReferencedTemporaryFile else {
            return nil
        }
        let name = URL(fileURLWithPath: resource.localFilePath).lastPathComponent
        let prefix = "nagramix-archive-copy-"
        guard name.hasPrefix(prefix), let separator = name.firstIndex(of: "."),
              UUID(uuidString: String(name[name.index(name.startIndex, offsetBy: prefix.count) ..< separator])) != nil else {
            return nil
        }
        let encoded = String(name[name.index(after: separator)...])
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        guard encoded.utf8.count <= 172, let key = Data(base64Encoded: encoded), key.count <= 128,
              let identifier = String(data: key, encoding: .utf8),
              identifier.hasPrefix("nagramix-retained-upload-v1:"),
              identifier.utf8.count > "nagramix-retained-upload-v1:".utf8.count else {
            return nil
        }
        return key
    }

    private func resource(_ original: TelegramMediaResource) -> TelegramMediaResource? {
        if let resource = self.resources[original.id.stringRepresentation] {
            return resource
        }
        let sourcePath: String?
        var expectedSize: Int64?
        if let original = original as? LocalFileReferenceMediaResource {
            sourcePath = original.localFilePath
            expectedSize = original.size
        } else {
            sourcePath = self.mediaBox.completedResourcePath(original)
        }
        guard let sourcePath,
              let attributes = try? FileManager.default.attributesOfItem(atPath: sourcePath),
              attributes[.type] as? FileAttributeType == .typeRegular,
              let size = (attributes[.size] as? NSNumber)?.int64Value,
              size > 0, expectedSize == nil || expectedSize == size else {
            return nil
        }
        var cacheKeySuffix = ""
        if let original = original as? LocalFileReferenceMediaResource,
           URL(fileURLWithPath: original.localFilePath).deletingLastPathComponent().lastPathComponent == "nagramix-message-media" {
            let key = Data(("nagramix-retained-upload-v1:" + original.id.stringRepresentation).utf8)
            if key.count <= 128 {
                cacheKeySuffix = "." + key.base64EncodedString()
                    .replacingOccurrences(of: "+", with: "-")
                    .replacingOccurrences(of: "/", with: "_")
            }
        }
        let path = NSTemporaryDirectory() + "nagramix-archive-copy-" + UUID().uuidString + cacheKeySuffix
        do {
            do {
                // A hard link pins the complete bytes even if the archive is
                // cleared while a scheduled or multi-recipient send is pending.
                try FileManager.default.linkItem(atPath: sourcePath, toPath: path)
            } catch {
                try FileManager.default.copyItem(atPath: sourcePath, toPath: path)
            }
            let resource = LocalFileReferenceMediaResource(localFilePath: path, randomId: Int64.random(in: 1 ... Int64.max), isUniquelyReferencedTemporaryFile: true, size: size)
            self.paths.append(path)
            self.resources[original.id.stringRepresentation] = resource
            return resource
        } catch {
            try? FileManager.default.removeItem(atPath: path)
            return nil
        }
    }

    private func representation(_ original: TelegramMediaImageRepresentation) -> TelegramMediaImageRepresentation? {
        guard let resource = self.resource(original.resource) else {
            return nil
        }
        return TelegramMediaImageRepresentation(dimensions: original.dimensions, resource: resource, progressiveSizes: original.progressiveSizes, immediateThumbnailData: original.immediateThumbnailData, hasVideo: original.hasVideo, isPersonal: original.isPersonal, typeHint: original.typeHint)
    }

    private func image(_ original: TelegramMediaImage) -> TelegramMediaImage? {
        guard let largest = original.representations.max(by: { lhs, rhs in
            return Int64(lhs.dimensions.width) * Int64(lhs.dimensions.height) < Int64(rhs.dimensions.width) * Int64(rhs.dimensions.height)
        }), self.resource(largest.resource) != nil else {
            return nil
        }
        return TelegramMediaImage(imageId: MediaId(namespace: Namespaces.Media.LocalImage, id: Int64.random(in: 1 ... Int64.max)), representations: original.representations.compactMap(self.representation), videoRepresentations: [], immediateThumbnailData: original.immediateThumbnailData, emojiMarkup: original.emojiMarkup, reference: nil, partialReference: nil, flags: original.flags, video: original.video.flatMap(self.file))
    }

    private func file(_ original: TelegramMediaFile) -> TelegramMediaFile? {
        guard let resource = self.resource(original.resource) else {
            return nil
        }
        return TelegramMediaFile(fileId: MediaId(namespace: Namespaces.Media.LocalFile, id: Int64.random(in: 1 ... Int64.max)), partialReference: nil, resource: resource, previewRepresentations: original.previewRepresentations.compactMap(self.representation), videoThumbnails: original.videoThumbnails.compactMap { thumbnail in
            guard let resource = self.resource(thumbnail.resource) else {
                return nil
            }
            return TelegramMediaFile.VideoThumbnail(dimensions: thumbnail.dimensions, resource: resource)
        }, videoCover: original.videoCover.flatMap(self.image), immediateThumbnailData: original.immediateThumbnailData, mimeType: original.mimeType, size: (resource as? LocalFileReferenceMediaResource)?.size, attributes: original.attributes, alternativeRepresentations: [])
    }

    public func prepare(_ media: Media) -> Media? {
        if let image = media as? TelegramMediaImage {
            return self.image(image)
        } else if let file = media as? TelegramMediaFile {
            return self.file(file)
        }
        return media
    }
}

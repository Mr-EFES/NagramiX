import Foundation

// Postbox/Telegram API boundaries. The copier, resource staging and fetch
// functions under test are extracted unchanged from the composed source tree.
extension EnginePeer { typealias Id = PeerId }
final class TestCopyPostbox {
    let mediaBox: MediaBox
    init(_ mediaBox: MediaBox) { self.mediaBox = mediaBox }
}
final class Account {
    let postbox: TestCopyPostbox
    init(_ mediaBox: MediaBox) { self.postbox = TestCopyPostbox(mediaBox) }
}
final class InstantPage {
    let blocks: [String]
    let rawMedia: [MediaId: Media]
    let isComplete: Bool
    let rtl: Bool
    let url: String
    let views: Int32?
    init(blocks: [String], rawMedia: [MediaId: Media], isComplete: Bool, rtl: Bool, url: String, views: Int32?) {
        self.blocks = blocks; self.rawMedia = rawMedia; self.isComplete = isComplete
        self.rtl = rtl; self.url = url; self.views = views
    }
}
final class RichTextMessageAttribute: MessageAttribute {
    let instantPage: InstantPage
    var fullInstantPage: InstantPage?
    init(instantPage: InstantPage, fullInstantPage: InstantPage?) {
        self.instantPage = instantPage; self.fullInstantPage = fullInstantPage
    }
}

@main struct RichContentCopyTests {
    static func main() throws {
        var checks = 0
        func check(_ condition: @autoclosure () -> Bool, _ name: String) {
            precondition(condition(), name); checks += 1
        }
        let box = MediaBox()
        let account = Account(box)
        let blocks = ["photo:1", "paragraph:СМОТРЕТЬ НА SASFLIX", "link:https://example.org/watch", "photo:2"]
        let firstId = MediaId(namespace: 0, id: 1)
        let secondId = MediaId(namespace: 0, id: 2)
        let image = TelegramMediaImage(representations: [TelegramMediaImageRepresentation(dimensions: Dimensions(width: 100, height: 100), resource: CloudResource("image"))])
        let file = TelegramMediaFile(resource: CloudResource("video"))
        let page = InstantPage(blocks: blocks, rawMedia: [firstId: image, secondId: file], isComplete: true, rtl: true, url: "", views: 42)
        var post = Message()
        post.text = ""; post.media = []
        post.attributes = [RichTextMessageAttribute(instantPage: page, fullInstantPage: nil)]
        check(nagramiXCanCopyMessagesAsNew([post]), "rich post must enable the copy actions despite empty legacy fields")
        let ordinaryCopy = nagramiXCopyMessagesAsNew([post], account: account)!
        let copiedPage = (ordinaryCopy[0].attributes.first { $0 is RichTextMessageAttribute } as! RichTextMessageAttribute).instantPage
        check(copiedPage.blocks == blocks, "text, links, media order and formatting blocks survive")
        check(copiedPage.rawMedia.count == 2 && copiedPage.rawMedia[firstId] != nil && copiedPage.rawMedia[secondId] != nil, "every embedded attachment and its block key survive")
        check(copiedPage.rtl && copiedPage.views == nil, "retain direction without copying the source view counter")
        check(ordinaryCopy[0].mediaReference == nil && ordinaryCopy[0].text.isEmpty, "send rich content once without flattening it into a caption")

        let root = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let payload = Data([1, 2, 3, 4])
        for resource in ["image", "video"] {
            let url = root.appendingPathComponent(resource)
            try payload.write(to: url); box.paths[resource] = url.path
        }
        post.protected = true
        let protectedCopy = nagramiXCopyMessagesAsNew([post], account: account, forceLocalMedia: true)!
        let protectedPage = (protectedCopy[0].attributes.first { $0 is RichTextMessageAttribute } as! RichTextMessageAttribute).instantPage
        let localImage = protectedPage.rawMedia[firstId] as! TelegramMediaImage
        let localFile = protectedPage.rawMedia[secondId] as! TelegramMediaFile
        let imageResource = localImage.representations[0].resource as! LocalFileReferenceMediaResource
        let fileResource = localFile.resource as! LocalFileReferenceMediaResource
        defer { try? FileManager.default.removeItem(atPath: imageResource.localFilePath); try? FileManager.default.removeItem(atPath: fileResource.localFilePath) }
        check(localImage.imageId.namespace == Namespaces.Media.LocalImage && localImage.reference == nil && localFile.fileId.namespace == Namespaces.Media.LocalFile && localFile.partialReference == nil, "protected rich media receives new local identities")
        try FileManager.default.removeItem(at: root.appendingPathComponent("image"))
        try FileManager.default.removeItem(at: root.appendingPathComponent("video"))
        let imageBytes = try Data(contentsOf: URL(fileURLWithPath: imageResource.localFilePath))
        let fileBytes = try Data(contentsOf: URL(fileURLWithPath: fileResource.localFilePath))
        check(imageBytes == payload && fileBytes == payload, "scheduled copies retain their bytes after source cache removal")
        check(nagramiXCopyMessagesAsNew([post], account: account, forceLocalMedia: true) == nil, "missing protected media stops the whole copy")

        let partial = InstantPage(blocks: ["preview"], rawMedia: [:], isComplete: false, rtl: false, url: "", views: nil)
        var preview = Message(); preview.text = ""; preview.media = []
        preview.attributes = [RichTextMessageAttribute(instantPage: partial, fullInstantPage: nil)]
        check(nagramiXCanCopyMessagesAsNew([preview]), "a partial preview can offer resolution through the action")
        check(nagramiXCopyMessagesAsNew([preview], account: account) == nil, "a partial preview cannot be sent as the complete post")
        preview.attributes = [RichTextMessageAttribute(instantPage: partial, fullInstantPage: page)]
        let resolved = nagramiXCopyMessagesAsNew([preview], account: account)!
        check((resolved[0].attributes[0] as! RichTextMessageAttribute).instantPage.blocks == blocks, "use the full page rather than the preview")
        var invalid = preview
        invalid.attributes = [RichTextMessageAttribute(instantPage: InstantPage(blocks: blocks, rawMedia: [firstId: UnsupportedMedia()], isComplete: true, rtl: false, url: "", views: nil), fullInstantPage: nil)]
        check(nagramiXCopyMessagesAsNew([preview, invalid], account: account) == nil, "do not silently omit an unsupported embedded attachment")
        var empty = Message(); empty.text = ""; empty.media = []
        check(!nagramiXCanCopyMessagesAsNew([empty]), "truly empty content stays unavailable")
        let ordinary = Message()
        check(nagramiXCopyMessagesAsNew([ordinary])?.first?.text == ordinary.text, "ordinary message copying is unchanged")

        let fetchBox = MediaBox()
        var fetched: Bool?
        post.protected = false
        let fetch = nagramiXFetchContentCopyMedia(mediaBox: fetchBox, messages: [post]).start(next: { fetched = $0 })
        check(Set(fetchBox.fetched) == Set(["image", "video"]), "fetch every rich attachment")
        fetchBox.emit("image", ResourceData(complete: true)); check(fetched == nil, "wait for all embedded resources")
        fetchBox.emit("video", ResourceData(complete: true)); check(fetched == true, "finish once the complete rich payload is available")
        fetch.dispose()
        check(fetchBox.activeFetches == 0 && fetchBox.activeKeeps == 0, "release all fetch and cache leases")
        print("PASS: \(checks) rich-post copy regressions")
    }
}

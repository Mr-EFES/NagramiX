// AVFoundation is typechecked against the iOS SDK in the macOS gate. These
// deterministic track properties deliberately differ from the picker's thumbnail.
private func nagramiXOriginalVideoMetadata(_ url: URL) -> (dimensions: PixelDimensions, duration: Double)? {
    guard FileManager.default.fileExists(atPath: url.path) else { return nil }
    return (PixelDimensions(width: 96, height: 64), 0.5)
}

final class LocalFileVideoMediaResource: Resource {
    let id = UUID().uuidString
    init(randomId: Int64, path: String, adjustments: VideoMediaResourceAdjustments?) {}
}

struct AnyMediaReference {}
struct LegacyAssetPickerEnqueueMessage {
    var media: TelegramMediaFile?
    var caption: String
}
struct EditorCaption { var text: String }
func chatMediaSendCaption(_ caption: NSAttributedString) -> EditorCaption { EditorCaption(text: caption.string) }
func chatMediaSendMessage(media: EngineRawMedia, caption: EditorCaption, stickerFiles: [TelegramMediaFile], timer: Int32?, spoiler: Bool, groupingKey: Int64?, uniqueId: String?) -> LegacyAssetPickerEnqueueMessage {
    LegacyAssetPickerEnqueueMessage(media: media as? TelegramMediaFile, caption: caption.text)
}
func chatMediaEditorEnqueueMessage(result: ChatMediaEditorResult, forceHd: Bool, originalMediaReference: AnyMediaReference?, storeResourceData: (EngineMediaResource.Id, Data) -> Void) -> LegacyAssetPickerEnqueueMessage? {
    LegacyAssetPickerEnqueueMessage(media: nil, caption: "native editor")
}
func nagramiXRoundVideoCaptionMessage(_ caption: EditorCaption) -> LegacyAssetPickerEnqueueMessage {
    LegacyAssetPickerEnqueueMessage(media: nil, caption: caption.text)
}

extension UTType {
    init?(filenameExtension: String) {
        guard let mime = ["mp4": "video/mp4", "mov": "video/quicktime", "m4v": "video/x-m4v"][filenameExtension] else { return nil }
        self.init(mime)
    }
}

// ObjC picker input. The actual downstream batch preparation and grouping run
// against the native SwiftSignalKit operators.
private struct SSignal {
    let input: [Any]
    static func combineSignals(_ input: [Any]) -> Self { Self(input: input) }
    func start(next: (Any?) -> Void, error: (Any?) -> Void, completed: () -> Void) -> Disposable? {
        next(NSArray(array: input))
        completed()
        return EmptyDisposable
    }
}

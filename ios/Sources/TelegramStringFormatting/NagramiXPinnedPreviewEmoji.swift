import Foundation
import Postbox
import TelegramCore
import TextFormat

/// Rich previews keep an unresolved emoji's alt text readable. The pinned panel
/// resolves only these preview IDs, then hands known files to the native entity
/// renderer, just as the preview builder does for files already in page media.
public func nagramiXPinnedPreviewEmojiFileIds(_ text: NSAttributedString) -> Set<Int64> {
    var ids = Set<Int64>()
    text.enumerateAttribute(instantPagePreviewCustomEmoji, in: NSRange(location: 0, length: text.length)) { value, _, _ in
        if let emoji = value as? ChatTextInputTextCustomEmojiAttribute, emoji.file == nil, emoji.custom == nil {
            ids.insert(emoji.fileId)
        }
    }
    return ids
}

public func nagramiXPinnedPreviewApplyingEmojiFiles(_ text: NSAttributedString, files: [Int64: TelegramMediaFile]) -> NSAttributedString {
    guard !files.isEmpty else { return text }
    let result = NSMutableAttributedString(attributedString: text)
    text.enumerateAttribute(instantPagePreviewCustomEmoji, in: NSRange(location: 0, length: text.length)) { value, range, _ in
        guard let emoji = value as? ChatTextInputTextCustomEmojiAttribute,
              emoji.file == nil, emoji.custom == nil,
              let file = files[emoji.fileId],
              file.fileId == MediaId(namespace: Namespaces.Media.CloudFile, id: emoji.fileId) else { return }
        let resolved = ChatTextInputTextCustomEmojiAttribute(
            interactivelySelectedFromPackId: emoji.interactivelySelectedFromPackId,
            fileId: emoji.fileId, file: file, custom: emoji.custom,
            enableAnimation: emoji.enableAnimation
        )
        result.addAttribute(instantPagePreviewCustomEmoji, value: resolved, range: range)
        result.addAttribute(ChatTextInputAttributes.customEmoji, value: resolved, range: range)
    }
    return result
}

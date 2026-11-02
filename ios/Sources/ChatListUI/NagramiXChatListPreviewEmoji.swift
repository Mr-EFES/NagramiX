import Foundation
import Postbox
import TelegramCore
import TelegramStringFormatting
import SwiftSignalKit
import TextFormat

// Preserve UTF-16 entity positions and rich preview attributes when native
// media labels are prepended. Literal Unicode emoji are never substituted.
func nagramiXChatListPrependMediaPrefix(_ prefix: String, text: inout String,
    entities: inout [MessageTextEntity], spoilers: inout [NSRange]?,
    customEmoji: inout [(NSRange, ChatTextInputTextCustomEmojiAttribute)]?,
    richText: inout NSAttributedString?) {
    let offset = (prefix as NSString).length
    if let preview = richText, preview.string == text {
        let result = NSMutableAttributedString(string: prefix)
        result.append(preview)
        richText = result
    } else {
        richText = nil
    }
    entities = entities.map { MessageTextEntity(range: ($0.range.lowerBound + offset)..<($0.range.upperBound + offset), type: $0.type) }
    spoilers = spoilers?.map { NSRange(location: $0.location + offset, length: $0.length) }
    customEmoji = customEmoji?.map { (NSRange(location: $0.0.location + offset, length: $0.0.length), $0.1) }
    text = prefix + text
}

// One row owns one bounded preview request. Engine resolution and image/animation
// rendering stay native; no global cache, message mutation or polling is added.
final class NagramiXChatListPreviewEmoji {
    struct Snapshot {
        let accountPeerId: PeerId?
        let messageId: MessageId?
        let files: [Int64: TelegramMediaFile]

        func applying(to text: NSAttributedString, accountPeerId: PeerId, messageId: MessageId?) -> NSAttributedString {
            guard self.accountPeerId == accountPeerId, self.messageId == messageId else { return text }
            return nagramiXPinnedPreviewApplyingEmojiFiles(text, files: self.files)
        }
    }

    private let state = Atomic(value: Snapshot(accountPeerId: nil, messageId: nil, files: [:]))
    private let disposable = MetaDisposable()
    private let schedule: (@escaping () -> Void) -> Void
    private var ids = Set<Int64>()
    private var generation: UInt64 = 0
    private var refreshScheduled = false

    init(schedule: @escaping (@escaping () -> Void) -> Void = { Queue.mainQueue().async($0) }) {
        self.schedule = schedule
    }

    deinit { self.disposable.dispose() }

    func snapshot() -> Snapshot { self.state.with { $0 } }

    // setupItem runs before an asynchronous relayout on a reused row. Cancel
    // the old message now, so a late result cannot reapply its old layout.
    func prepare(accountPeerId: PeerId, messageId: MessageId?) {
        let current = self.snapshot()
        guard current.accountPeerId != accountPeerId || current.messageId != messageId else { return }
        self.generation &+= 1
        self.refreshScheduled = false
        self.disposable.set(nil)
        self.ids.removeAll()
        _ = self.state.swap(Snapshot(accountPeerId: accountPeerId, messageId: messageId, files: [:]))
    }

    // Called only from the row's main-thread apply. A synchronous cache result
    // is deferred until that apply finishes, before requesting the latest layout.
    func update(accountPeerId: PeerId, messageId: MessageId?, text: NSAttributedString,
        rendered: Snapshot? = nil,
        resolve: ([Int64], @escaping ([Int64: TelegramMediaFile]) -> Void) -> Disposable,
        refresh: @escaping () -> Void) {
        self.prepare(accountPeerId: accountPeerId, messageId: messageId)
        let ids = messageId == nil ? Set<Int64>() : nagramiXPinnedPreviewEmojiFileIds(text)
        let current = self.snapshot()
        if self.ids == ids {
            self.refreshIfNeeded(rendered: rendered, ids: ids, refresh: refresh)
            return
        }
        self.generation &+= 1
        self.refreshScheduled = false
        let generation = self.generation
        self.disposable.set(nil)
        self.ids = ids
        // Keep known files only for the same account/message and current IDs.
        let files = current.accountPeerId == accountPeerId && current.messageId == messageId
            ? current.files.filter { ids.contains($0.key) } : [:]
        _ = self.state.swap(Snapshot(accountPeerId: accountPeerId, messageId: messageId, files: files))
        self.refreshIfNeeded(rendered: rendered, ids: ids, refresh: refresh)
        let missing = ids.filter { files[$0] == nil }.sorted()
        guard !missing.isEmpty else { return }
        self.disposable.set(resolve(missing, { [weak self] files in
            guard let self else { return }
            self.schedule { [weak self] in
                guard let self, self.generation == generation else { return }
                let current = self.snapshot()
                guard current.accountPeerId == accountPeerId, current.messageId == messageId else { return }
                var updated = current.files
                for (id, file) in files where self.ids.contains(id) && updated[id] == nil {
                    guard file.fileId == MediaId(namespace: Namespaces.Media.CloudFile, id: id) else { continue }
                    updated[id] = file
                }
                guard updated.count != current.files.count else { return }
                _ = self.state.swap(Snapshot(accountPeerId: accountPeerId, messageId: messageId, files: updated))
                refresh()
            }
        }))
    }

    // Metadata can arrive after asyncLayout captured its snapshot but before
    // its apply. Repair that stale layout once, without another network query.
    private func refreshIfNeeded(rendered: Snapshot?, ids: Set<Int64>, refresh: @escaping () -> Void) {
        guard let rendered, !self.refreshScheduled else { return }
        let current = self.snapshot()
        let shown = rendered.accountPeerId == current.accountPeerId && rendered.messageId == current.messageId
            ? Set(rendered.files.keys) : []
        guard !ids.intersection(Set(current.files.keys)).isSubset(of: shown) else { return }
        self.refreshScheduled = true
        let generation = self.generation
        self.schedule { [weak self] in
            guard let self, self.generation == generation else { return }
            self.refreshScheduled = false
            refresh()
        }
    }
}

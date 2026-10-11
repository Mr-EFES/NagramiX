// Rank belongs to a view snapshot, not a global preference read inside '<'.
// Old/new lists therefore retain their own ranks during native list diffs.
func nagramiXSortUnreadChatListEntries(_ entries: inout [ChatListNodeEntry]) {
    // Ordinary folders may also contain native contact suggestions. Preserve
    // those rows, headers, pins and promotions at exactly their native slots.
    for entry in entries {
        switch entry {
        case .HeaderEntry, .PeerEntry, .GroupReferenceEntry, .ArchiveIntro, .EmptyIntro, .ContactEntry, .SectionHeader:
            break
        default:
            return
        }
    }
    var positions: [Int] = []
    var chats: [ChatListNodeEntry] = []
    for i in entries.indices {
        if case var .PeerEntry(peer) = entries[i], case let .chatList(index) = peer.index, index.pinningIndex == nil, peer.promoInfo == nil {
            // A manual unread flag without messages has count zero, matching
            // the requested ranking by actual unread message count.
            peer.nagramiXUnreadCount = max(0, Int(peer.readState?.count ?? 0))
            positions.append(i)
            chats.append(.PeerEntry(peer))
        }
    }
    chats.sort()
    for (position, chat) in zip(positions, chats) {
        entries[position] = chat
    }
}

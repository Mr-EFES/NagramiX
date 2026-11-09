import Foundation
import SwiftSignalKit
import TelegramCore

/// A row's visual status can briefly describe a player that has already ended.
/// Resolve the exact native voice playlist before toggling, otherwise open the
/// supplied retained snapshot. No removed Postbox message lookup is required.
public final class NagramiXArchivedPlaybackAction {
    private let disposable = MetaDisposable()
    private var generation: UInt64 = 0

    public init() {
    }

    deinit {
        self.disposable.dispose()
    }

    public func activate(context: AccountContext, message: EngineRawMessage, isCurrent: @escaping () -> Bool, open: @escaping () -> Void) {
        self.generation &+= 1
        let generation = self.generation
        let manager = context.sharedContext.mediaManager
        guard let (playlistId, itemId) = peerMessagesMediaPlaylistAndItemId(EngineMessage(message), isRecentActions: false, isGlobalSearch: false, isDownloadList: false, isSavedMusic: false, isAttachMusic: false) else { return }
        self.disposable.set((manager.filteredPlaylistState(
            accountId: context.account.id,
            playlistId: playlistId,
            itemId: itemId,
            type: .voice
        )
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] state in
            guard let self, self.generation == generation, isCurrent() else {
                return
            }
            var ended = false
            if let state, case .paused = state.status.status,
               state.status.duration.isFinite, state.status.duration > 0.0,
               state.status.timestamp.isFinite,
               state.status.timestamp >= state.status.duration - 0.05 {
                ended = true
            }
            if state != nil && !ended {
                manager.playlistControl(.playback(.togglePlayPause), type: .voice)
            } else {
                open()
            }
        }))
    }
}

import Foundation
import QuartzCore
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

    public func activate(context: AccountContext, message: EngineRawMessage, isCurrent: @escaping () -> Bool, openAt: ((Double) -> Void)? = nil, open: @escaping () -> Void) {
        self.generation &+= 1
        let generation = self.generation
        let manager = context.sharedContext.mediaManager
        guard let (playlistId, itemId) = peerMessagesMediaPlaylistAndItemId(EngineMessage(message), isRecentActions: false, isGlobalSearch: false, isDownloadList: false, isSavedMusic: false, isAttachMusic: false) else { return }
        if message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute }),
           let file = message.media.compactMap({ $0 as? TelegramMediaFile }).first(where: { $0.isInstantVideo }) {
            self.activateArchivedRound(context: context, message: message, file: file, playlistId: playlistId, itemId: itemId, generation: generation, isCurrent: isCurrent, openAt: openAt, open: open)
            return
        }
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

    // Loading is not evidence that this message has no player. The filtered API
    // collapses that state to nil, which used to reopen the post and reset its
    // playback/row size. Resolve the real native owner before issuing controls.
    private func activateArchivedRound(context: AccountContext, message: EngineRawMessage, file: TelegramMediaFile, playlistId: SharedMediaPlaylistId, itemId: SharedMediaPlaylistItemId, generation: UInt64, isCurrent: @escaping () -> Bool, openAt: ((Double) -> Void)?, open: @escaping () -> Void) {
        let manager = context.sharedContext.mediaManager
        let accountId = context.account.id
        self.disposable.set((manager.globalMediaPlayerState
        |> filter { value in
            if let (account, state, type) = value, account.id == accountId,
               case .voice = type, case .loading = state {
                return false
            }
            return true
        }
        |> timeout(0.5, queue: .mainQueue(), alternate: .single(nil))
        |> take(1)
        |> deliverOnMainQueue).start(next: { [weak self] value in
            guard let self, self.generation == generation, isCurrent() else {
                return
            }
            guard let (account, stateOrLoading, type) = value, account.id == accountId,
                  case .voice = type, case let .state(state) = stateOrLoading,
                  state.item.id.isEqual(to: itemId),
                  state.playlistId.isEqual(to: playlistId) || state.playlistId.isEqual(to: PeerMessagesMediaPlaylistId.peer(message.id.peerId)),
                  let data = state.item.playbackData, case .instantVideo = data.type,
                  case let .telegramFile(reference, _, _) = data.source,
                  reference.media.fileId == file.fileId else {
                open()
                return
            }
            var ended = false
            if case .paused = state.status.status, state.status.duration.isFinite,
               state.status.duration > 0.0, state.status.timestamp.isFinite,
               state.status.timestamp >= state.status.duration - 0.05 {
                ended = true
            }
            if reference.media.resource.id == file.resource.id {
                if ended {
                    // Restart the same native decoder, preserving its owner,
                    // rate and geometry instead of constructing another player.
                    manager.playlistControl(.seek(0.0), type: .voice)
                    manager.playlistControl(.playback(.play), type: .voice)
                } else {
                    manager.playlistControl(.playback(.togglePlayPause), type: .voice)
                }
            } else if let openAt {
                // A live message can become an independent local snapshot
                // during playback. Migrate once, retaining its current time.
                var position = state.status.timestamp
                if case .playing = state.status.status,
                   state.status.generationTimestamp.isFinite, state.status.generationTimestamp > 0.0,
                   state.status.baseRate.isFinite, state.status.baseRate > 0.0 {
                    position += max(0.0, CACurrentMediaTime() - state.status.generationTimestamp) * state.status.baseRate
                }
                let timestamp: Double
                if ended || !position.isFinite {
                    timestamp = 0.0
                } else if state.status.duration.isFinite && state.status.duration > 0.0 {
                    timestamp = min(state.status.duration, max(0.0, position))
                } else {
                    timestamp = max(0.0, position)
                }
                openAt(timestamp)
            } else {
                open()
            }
        }))
    }
}

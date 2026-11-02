import Foundation
import AccountContext
import UniversalMediaPlayer

struct NagramiXVideoNowPlayingEntry {
    let id: UUID
    let state: NagramiXVideoNowPlayingState
}

// Once a native playlist takes control, its paused state remains resumable.
// Only a new video owner or actual video playback may take it back.
final class NagramiXNowPlayingArbitration {
    private var previousVideoId: UUID?
    private var nativeHasPriority = false
    private var previousVideoWasPlaying = false
    private var previousSharedWasPlaying = false

    func choose(video: NagramiXVideoNowPlayingEntry?, sharedIsPlaying: Bool) -> NagramiXVideoNowPlayingEntry? {
        let newVideo = self.previousVideoId != video?.id
        let videoIsPlaying = video.map { NagramiXVideoNowPlayingRegistry.isPlaying($0.state.status.status) } ?? false
        if newVideo {
            self.previousVideoId = video?.id
            self.nativeHasPriority = false
        }
        if sharedIsPlaying && (!self.previousSharedWasPlaying || !videoIsPlaying) {
            self.nativeHasPriority = true
        }
        if videoIsPlaying && (newVideo || !self.previousVideoWasPlaying) {
            self.nativeHasPriority = false
        }
        self.previousSharedWasPlaying = sharedIsPlaying
        self.previousVideoWasPlaying = videoIsPlaying
        return self.nativeHasPriority ? nil : video
    }
}

// One registry feeds MediaManager's existing Now Playing writer. A gallery
// and a transferred PiP have independent leases; releasing one cannot clear
// the other. Status ticks do not reorder owners.
final class NagramiXVideoNowPlayingRegistry {
    private var entries: [UUID: NagramiXVideoNowPlayingState] = [:]
    private var order: [UUID] = []

    func update(id: UUID, state: NagramiXVideoNowPlayingState?) {
        if let state {
            if self.entries[id] == nil { self.order.append(id) }
            self.entries[id] = state
        } else {
            self.entries.removeValue(forKey: id)
            self.order.removeAll(where: { $0 == id })
        }
    }

    func preferred(backgroundEnabled: Bool) -> NagramiXVideoNowPlayingEntry? {
        for pip in [true, false] {
            for id in self.order.reversed() {
                if let state = self.entries[id], state.isPictureInPicture == pip,
                   pip || (backgroundEnabled && state.status.soundEnabled) {
                    return NagramiXVideoNowPlayingEntry(id: id, state: state)
                }
            }
        }
        return nil
    }

    static func isPlaying(_ status: MediaPlayerPlaybackStatus) -> Bool {
        switch status {
        case .playing: return true
        case let .buffering(_, whilePlaying, _, _): return whilePlaying
        case .paused: return false
        }
    }

    static func timeline(_ status: MediaPlayerStatus) -> (duration: Double?, elapsed: Double, rate: Double) {
        let duration = status.duration.isFinite && status.duration > 0 ? status.duration : nil
        var elapsed = status.timestamp.isFinite ? max(0, status.timestamp) : 0
        if let duration { elapsed = min(duration, elapsed) }
        var rate = 0.0
        if case .playing = status.status {
            rate = status.baseRate.isFinite && status.baseRate > 0 ? status.baseRate : 1
        }
        return (duration, elapsed, rate)
    }

    static func action(_ action: SharedMediaPlayerControlAction, status: MediaPlayerStatus) -> SharedMediaPlayerControlAction? {
        switch action {
        case .playback(.play), .playback(.pause): return action
        case .playback(.togglePlayPause):
            return .playback(self.isPlaying(status.status) ? .pause : .play)
        case let .seek(position):
            guard position.isFinite, status.duration.isFinite, status.duration > 0 else { return nil }
            return .seek(max(0, min(status.duration, position)))
        default: return nil
        }
    }
}

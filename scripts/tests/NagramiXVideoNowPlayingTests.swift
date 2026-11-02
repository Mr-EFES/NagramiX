import Foundation

var checks = 0
func expect(_ value: @autoclosure () -> Bool, _ text: String) {
    checks += 1
    if !value() { print("FAIL: " + text); exit(1) }
}
func status(_ state: MediaPlayerPlaybackStatus = .playing, duration: Double = 100, time: Double = 30, rate: Double = 1, sound: Bool = true) -> MediaPlayerStatus {
    MediaPlayerStatus(generationTimestamp: 0, duration: duration, dimensions: .zero, timestamp: time, baseRate: rate, seekId: 0, status: state, soundEnabled: sound)
}
func actionName(_ action: SharedMediaPlayerControlAction) -> String {
    switch action {
    case .playback(.play): return "play"
    case .playback(.pause): return "pause"
    case .playback(.togglePlayPause): return "toggle"
    case let .seek(time): return "seek:\(time)"
    default: return "other"
    }
}
@main struct VideoNowPlayingTests {
    static func main() {
        let registry = NagramiXVideoNowPlayingRegistry()
        let gallery = UUID(), pip = UUID(), other = UUID()
        var commands: [String] = []
        func state(_ title: String, pip: Bool = false, value: MediaPlayerStatus = status()) -> NagramiXVideoNowPlayingState {
            NagramiXVideoNowPlayingState(title: title, status: value, isPictureInPicture: pip, control: { commands.append(actionName($0)) })
        }
        expect(registry.preferred(backgroundEnabled: true) == nil, "no video leaves native controls")
        registry.update(id: gallery, state: state("gallery"))
        expect(registry.preferred(backgroundEnabled: true)?.id == gallery, "ordinary background video registered")
        expect(registry.preferred(backgroundEnabled: false) == nil, "setting OFF restores native behavior")
        registry.update(id: pip, state: state("PiP", pip: true))
        for index in 0..<20 {
            registry.update(id: gallery, state: state("gallery\(index)"))
            expect(registry.preferred(backgroundEnabled: true)?.id == pip, "gallery ticks cannot overwrite PiP")
        }
        expect(registry.preferred(backgroundEnabled: false)?.id == pip, "PiP independent of background preference")
        registry.update(id: gallery, state: nil)
        expect(registry.preferred(backgroundEnabled: true)?.id == pip, "gallery destruction cannot remove transferred PiP")
        registry.update(id: pip, state: state("paused PiP", pip: true, value: status(.paused)))
        expect(registry.preferred(backgroundEnabled: true)?.id == pip, "paused PiP keeps resumable controls")
        registry.update(id: pip, state: nil)
        expect(registry.preferred(backgroundEnabled: true) == nil, "close removes video entry")
        registry.update(id: gallery, state: state("A"))
        registry.update(id: other, state: state("B"))
        registry.update(id: gallery, state: state("A later tick"))
        expect(registry.preferred(backgroundEnabled: true)?.id == other, "older owner cannot steal new video's controls")
        registry.update(id: other, state: nil)
        registry.update(id: gallery, state: state("silent", value: status(sound: false)))
        expect(registry.preferred(backgroundEnabled: true) == nil, "silent ordinary video not registered")
        for value in [status(.playing), status(.paused), status(.buffering(initial: true, whilePlaying: true, progress: 0, display: true)), status(.buffering(initial: false, whilePlaying: false, progress: 0, display: false))] {
            let action = NagramiXVideoNowPlayingRegistry.action(.playback(.togglePlayPause), status: value)!
            expect(actionName(action) == (NagramiXVideoNowPlayingRegistry.isPlaying(value.status) ? "pause" : "play"), "toggle uses actual playing/buffering intention")
            expect(actionName(NagramiXVideoNowPlayingRegistry.action(.playback(.play), status: value)!) == "play", "remote play accepted")
            expect(actionName(NagramiXVideoNowPlayingRegistry.action(.playback(.pause), status: value)!) == "pause", "remote pause accepted")
            expect(NagramiXVideoNowPlayingRegistry.action(.next, status: value) == nil, "video next cannot affect music")
            expect(NagramiXVideoNowPlayingRegistry.action(.previous, status: value) == nil, "video previous cannot affect music")
        }
        for time in [-50.0, 0, 20, 100, 150] {
            expect(actionName(NagramiXVideoNowPlayingRegistry.action(.seek(time), status: status())!) == "seek:\(max(0,min(100,time)))", "seek clamped to video")
        }
        for duration in [Double.nan, .infinity, -1, 0] {
            let s = status(duration: duration, time: .nan)
            expect(NagramiXVideoNowPlayingRegistry.action(.seek(2), status: s) == nil, "invalid duration cannot seek")
            let t = NagramiXVideoNowPlayingRegistry.timeline(s)
            expect(t.duration == nil && t.elapsed == 0 && t.rate == 1, "unknown duration/time sanitized")
        }
        for time in [Double.nan, .infinity, -.infinity] {
            expect(NagramiXVideoNowPlayingRegistry.action(.seek(time), status: status()) == nil, "nonfinite seek rejected")
        }
        expect(NagramiXVideoNowPlayingRegistry.timeline(status(time: 120, rate: 2)).elapsed == 100, "elapsed clamped")
        expect(NagramiXVideoNowPlayingRegistry.timeline(status(rate: 2)).rate == 2, "speed matches video")
        expect(NagramiXVideoNowPlayingRegistry.timeline(status(.paused)).rate == 0, "paused timeline stopped")
        expect(NagramiXVideoNowPlayingRegistry.timeline(status(rate: .nan)).rate == 1, "invalid rate sanitized")

        let manager = NativeManager()
        let a = NagramiXVideoNowPlayingEntry(id: gallery, state: state("movie.mp4"))
        let center = MPRemoteCommandCenter.shared()
        manager.render(nil, PresentationData(), a)
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo?[MPMediaItemPropertyTitle] as? String == "movie.mp4", "actual manager publishes video metadata")
        expect(center.pauseCommand.isEnabled && center.togglePlayPauseCommand.isEnabled && center.changePlaybackPositionCommand.isEnabled, "pause/toggle/seek enabled")
        expect(!center.nextTrackCommand.isEnabled && !center.previousTrackCommand.isEnabled, "music navigation disabled for video")
        manager.remote(.playback(.pause))
        expect(commands == ["pause"], "remote command reaches displayed video")
        manager.applyArtwork(UIImage())
        manager.applyStatus(status(duration: 999, time: 555))
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo?[MPMediaItemPropertyArtwork] == nil, "late music artwork cannot replace video")
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo?[MPMediaItemPropertyPlaybackDuration] as? Double == 100, "late music status cannot replace video")
        let paused = NagramiXVideoNowPlayingEntry(id: gallery, state: state("movie.mp4", value: status(.paused)))
        manager.render(nil, PresentationData(), paused)
        expect(center.playCommand.isEnabled && !center.pauseCommand.isEnabled, "paused video retains play")
        manager.remote(.playback(.togglePlayPause))
        expect(commands.last == "play", "paused lock-screen control resumes same video")
        let music = SharedMediaPlayerItemPlaybackState(item: PlaylistItem(displayData: .music("song", "artist", nil, false, false)), status: status())
        manager.render((Account(), .state(music), .music), PresentationData(), paused)
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo?[MPMediaItemPropertyTitle] as? String == "song", "playing music regains native writer")
        expect(center.nextTrackCommand.isEnabled && center.previousTrackCommand.isEnabled, "native music controls restored")
        manager.remote(.playback(.pause))
        expect(manager.nativeCommands == ["pause"], "music command remains native")
        let pausedMusic = SharedMediaPlayerItemPlaybackState(item: music.item, status: status(.paused))
        manager.render((Account(), .state(pausedMusic), .music), PresentationData(), paused)
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo?[MPMediaItemPropertyTitle] as? String == "song", "paused music remains resumable with an old paused video open")
        manager.remote(.playback(.play))
        expect(manager.nativeCommands.last == "play", "paused music play does not resume old video")
        for videoFirst in [true, false] {
            let arbitration = NagramiXNowPlayingArbitration()
            _ = arbitration.choose(video: a, sharedIsPlaying: false)
            expect(arbitration.choose(video: a, sharedIsPlaying: true) == nil, "new native playback takes control despite stale video playing state")
            expect(arbitration.choose(video: a, sharedIsPlaying: false) == nil, "native pause cannot revive stale video state")
            expect(arbitration.choose(video: paused, sharedIsPlaying: false) == nil, "delayed video pause keeps native ownership")
            _ = arbitration.choose(video: paused, sharedIsPlaying: true)
            if videoFirst {
                expect(arbitration.choose(video: a, sharedIsPlaying: true)?.id == gallery, "video resume can arrive before music pause")
                expect(arbitration.choose(video: a, sharedIsPlaying: false)?.id == gallery, "music pause preserves resumed video")
            } else {
                expect(arbitration.choose(video: paused, sharedIsPlaying: false) == nil, "music pause can arrive first")
                expect(arbitration.choose(video: a, sharedIsPlaying: false)?.id == gallery, "later video resume takes control")
            }
        }
        manager.render(nil, PresentationData(), a)
        DispatchQueue.global().sync { manager.remote(.playback(.pause)) }
        let b = NagramiXVideoNowPlayingEntry(id: UUID(), state: state("new movie"))
        let count = commands.count
        manager.render(nil, PresentationData(), b)
        Queue.mainQueue().flush()
        expect(commands.count == count, "queued old-owner command cannot control new video")
        manager.render(nil, PresentationData(), nil)
        expect(MPNowPlayingInfoCenter.default().nowPlayingInfo == nil, "closing final video clears stale controls")
        expect(!center.playCommand.isEnabled && !center.pauseCommand.isEnabled && !center.changePlaybackPositionCommand.isEnabled, "closing removes commands")
        expect([center.playCommand,center.pauseCommand,center.previousTrackCommand,center.nextTrackCommand,center.togglePlayPauseCommand,center.changePlaybackPositionCommand].allSatisfy { $0.targets == 0 }, "no leaked command targets")
        print("PASS \(checks) video Now Playing ownership/metadata/remote-command checks; MediaPlayer/UIKit are boundaries")
    }
}

import Foundation

final class Scheduler {
    var tasks: [() -> Void] = []
    func async(_ action: @escaping () -> Void) { tasks.append(action) }
    func drain() {
        let pending = tasks
        tasks.removeAll()
        pending.forEach { $0() }
    }
}
enum DispatchQueue { static let main = Scheduler() }

struct ObservationOptions: OptionSet {
    let rawValue: Int
    static let initial = Self(rawValue: 1)
    static let new = Self(rawValue: 2)
}
final class Observation {
    var valid = true
    func invalidate() { valid = false }
}
typealias NSKeyValueObservation = Observation
final class AVPlayer {
    enum Status { case unknown, readyToPlay, failed }
    enum TimeControlStatus { case playing, paused }
    var status = Status.unknown, timeControlStatus = TimeControlStatus.paused
    var observer: ((AVPlayer, Int) -> Void)?, completion: ((Bool) -> Void)?
    var starts = 0, cancellations = 0
    func observe(_ path: KeyPath<AVPlayer, Status>, options: ObservationOptions,
                 changeHandler: @escaping (AVPlayer, Int) -> Void) -> Observation {
        observer = changeHandler
        if options.contains(.initial) { changeHandler(self, 0) }
        return Observation()
    }
    func cancelPendingPrerolls() { cancellations += 1 }
    func pause() { timeControlStatus = .paused }
    func preroll(atRate rate: Float, completionHandler: @escaping (Bool) -> Void) {
        precondition(status == .readyToPlay && timeControlStatus == .paused && rate == 1)
        starts += 1
        completion = completionHandler
    }
}

// PRODUCTION_PREROLL

final class Video {
    let player = AVPlayer()
    let nagramiXGalleryPreroll = NagramiXGalleryPreroll()
    var plays = 0
    func play() { plays += 1 }
    // PRODUCTION_PREPARE
}

@main struct PrerollTests {
    static func main() {
        let video = Video()
        let player = video.player
        video.nagramiXPrepareGalleryPlayback { true }
        DispatchQueue.main.drain()
        precondition(player.starts == 0 && video.plays == 0)
        player.status = .readyToPlay
        player.observer?(player, 0)
        DispatchQueue.main.drain()
        precondition(player.starts == 1 && video.plays == 0)
        player.completion?(true)
        video.nagramiXGalleryPreroll.cancel()
        DispatchQueue.main.drain()
        precondition(video.plays == 0)
        for approved in [false, true] {
            video.nagramiXPrepareGalleryPlayback { approved }
            DispatchQueue.main.drain()
            player.completion?(true)
            DispatchQueue.main.drain()
            precondition(video.plays == (approved ? 1 : 0))
        }
        video.nagramiXPrepareGalleryPlayback { true }
        DispatchQueue.main.drain()
        player.completion?(false)
        DispatchQueue.main.drain()
        player.status = .failed
        video.nagramiXPrepareGalleryPlayback { true }
        DispatchQueue.main.drain()
        precondition(player.starts == 4 && video.plays == 1)
        print("AVPlayer preparation waits for readiness and ignores failed or superseded playback")
    }
}

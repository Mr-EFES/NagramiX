import Foundation

// The scheduler is a deterministic boundary. Signal, Subscriber, disposal,
// catch/take/then/map and timeout below are extracted from native SignalKit.
public final class Queue {
    public static let shared = Queue()
    public static func concurrentDefaultQueue() -> Queue { shared }
}
public final class Timer {
    static var now = 0.0
    static var timers: [Timer] = []
    let interval: Double
    let completion: () -> Void
    var deadline = 0.0
    var invalidated = false
    public init(timeout: Double, repeat: Bool, completion: @escaping () -> Void, queue: Queue) {
        precondition(!`repeat`)
        self.interval = timeout
        self.completion = completion
    }
    public func start() {
        if !invalidated { deadline = Self.now + interval; Self.timers.append(self) }
    }
    public func invalidate() { invalidated = true }
    static func advance(_ interval: Double) {
        now += interval
        let pending = timers
        timers.removeAll()
        for timer in pending {
            if timer.invalidated { continue }
            if timer.deadline <= now { timer.invalidated = true; timer.completion() }
            else { timers.append(timer) }
        }
    }
    static func reset() { timers.removeAll(); now = 0.0 }
}

public struct MediaId: Hashable { public let namespace: Int32; public let id: Int64 }
public typealias PeerId = Int64
public enum EnginePeer { public typealias Id = PeerId }
public struct MessageTextEntity: Equatable { let token: Int }
public protocol Media: AnyObject { var id: MediaId? { get } }
public enum PartialMediaReference: Equatable { case message(message: Int64) }
public enum RevalidateMediaReferenceError { case generic }
public struct Message { let media: [Media] }
public protocol TelegramMediaResource: AnyObject {}
public final class CloudDocumentMediaResource: TelegramMediaResource {
    let fileId: Int64
    let accessHash: Int64
    let fileReference: Data?
    init(fileId: Int64, accessHash: Int64, fileReference: Data?) {
        self.fileId = fileId; self.accessHash = accessHash; self.fileReference = fileReference
    }
}
public final class LocalMediaResource: TelegramMediaResource {}
public struct TelegramMediaImageRepresentation { let token: Int }
public enum TelegramMediaImageReference: Equatable {
    case cloud(imageId: Int64, accessHash: Int64, fileReference: Data?)
}
public struct TelegramMediaFileAttribute: Equatable { let token: Int }
public enum TelegramMediaPollPublicity: Equatable { case anonymous, `public` }
public enum TelegramMediaPollKind: Equatable { case poll(multipleAnswers: Bool), quiz(multipleAnswers: Bool) }
public final class OtherMedia: Media {
    public let id: MediaId?
    init(_ id: MediaId?) { self.id = id }
}

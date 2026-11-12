import Foundation

// The slot is released only after the worker acknowledges cancellation, including
// C++ inference and AVAssetWriter. Scrolling cannot start overlapping decoders.
final class NagramiXTranscriptionCoordinator {
    static let shared = NagramiXTranscriptionCoordinator()
    typealias Outcome = Result<String, NagramiXTranscriptionFailure>
    typealias Work = (NagramiXTranscriptionCancellation, @escaping (Outcome) -> Void) -> Void
    private final class Job {
        let key: String; let revision: String; let configuration: NagramiXTranscriptionConfiguration; let automatic: Bool; let work: Work
        let cancellation = NagramiXTranscriptionCancellation()
        var listeners: [UUID: (Outcome) -> Void] = [:]
        init(key: String, configuration: NagramiXTranscriptionConfiguration, automatic: Bool, work: @escaping Work) { self.key = key; self.revision = configuration.revision; self.configuration = configuration; self.automatic = automatic; self.work = work }
    }
    private let queue = DispatchQueue(label: "NagramiXTranscription.Coordinator")
    private var pending: [Job] = []
    private var active: Job?
    private var failures: [String: Date] = [:]
    private var observer: NSObjectProtocol?
    init() {
        self.observer = NotificationCenter.default.addObserver(forName: NagramiXTranscriptionSettings.changed, object: nil, queue: nil) { [weak self] _ in self?.cancelObsolete() }
    }
    deinit { if let observer { NotificationCenter.default.removeObserver(observer) } }
    func request(key: String, configuration: NagramiXTranscriptionConfiguration, automatic: Bool, work: @escaping Work, completion: @escaping (Outcome) -> Void) -> NagramiXTranscriptionCancellation {
        let consumer = NagramiXTranscriptionCancellation(); let id = UUID()
        self.queue.async { [self] in
            guard !consumer.cancelled else { return }
            guard configuration.enabled, NagramiXTranscriptionSettings.configuration(matching: configuration).revision == configuration.revision else { completion(.failure(.disabled)); return }
            let existing = ([self.active].compactMap { $0 } + self.pending).first { $0.key == key && $0.revision == configuration.revision && !$0.cancellation.cancelled }
            let job: Job
            if let existing { job = existing }
            else {
                if automatic, let until = self.failures[key], until > Date() { completion(.failure(.busy)); return }
                guard self.pending.count < 8 else { completion(.failure(.busy)); return }
                job = Job(key: key, configuration: configuration, automatic: automatic, work: work)
                if automatic { self.pending.append(job) } else { self.pending.insert(job, at: 0) }
            }
            job.listeners[id] = { result in if !consumer.cancelled { completion(result) } }
            consumer.add { [weak self, weak job] in
                guard let self, let job else { return }
                self.queue.async {
                    job.listeners[id] = nil
                    if job.listeners.isEmpty {
                        job.cancellation.cancel()
                        self.pending.removeAll { $0 === job }
                    }
                    self.pump()
                }
            }
            self.pump()
        }
        return consumer
    }
    func cancelAll() {
        self.queue.async {
            let jobs = self.pending; self.pending.removeAll()
            for job in jobs { self.completeListeners(job, .failure(.cancelled)); job.cancellation.cancel() }
            if let active = self.active { self.completeListeners(active, .failure(.cancelled)); active.cancellation.cancel() }
        }
    }
    private func cancelObsolete() {
        self.queue.async {
            let isObsolete: (Job) -> Bool = { job in
                let current = NagramiXTranscriptionSettings.configuration(matching: job.configuration)
                return !current.enabled || job.revision != current.revision
            }
            let obsolete = self.pending.filter(isObsolete)
            self.pending.removeAll(where: isObsolete)
            for job in obsolete { self.completeListeners(job, .failure(.cancelled)); job.cancellation.cancel() }
            if let job = self.active, isObsolete(job) { self.completeListeners(job, .failure(.cancelled)); job.cancellation.cancel() }
            self.pump()
        }
    }
    private func completeListeners(_ job: Job, _ result: Outcome) {
        let listeners = job.listeners.values; job.listeners.removeAll()
        for callback in listeners { callback(result) }
    }
    private func pump() {
        guard self.active == nil, !self.pending.isEmpty else { return }
        let job = self.pending.removeFirst(); self.active = job
        guard !job.cancellation.cancelled else { self.active = nil; self.pump(); return }
        job.work(job.cancellation) { result in
            self.queue.async {
                guard self.active === job else { return }
                let outcome: Outcome = job.cancellation.cancelled ? .failure(.cancelled) : result
                if case let .failure(error) = outcome, error != .cancelled {
                    self.failures = self.failures.filter { $0.value > Date() }
                    if self.failures.count > 128 { self.failures.removeAll() }
                    self.failures[job.key] = Date().addingTimeInterval(60)
                }
                self.completeListeners(job, outcome)
                job.cancellation.cancel()
                self.active = nil; self.pump()
            }
        }
    }
}

import Foundation
import SwiftSignalKit

// All state and observer callbacks belong to the main queue. A Photos commit
// cannot be cancelled: keep it alive even when its progress screen closes.
final class NagramiXStorySaveJob {
    enum Event {
        case progress(Float)
        case saved
        case failed(NagramiXStorySaveError)
    }

    static var jobs: [String: NagramiXStorySaveJob] = [:]
    private let key: String
    private var observers: [UUID: (Event) -> Void] = [:]
    private var event: Event = .progress(0.0)
    private var operation: Disposable?
    private var committing = false
    private var finished = false

    init(key: String) {
        self.key = key
    }

    func subscribe(_ observer: @escaping (Event) -> Void) -> Disposable {
        assert(Thread.isMainThread)
        let token = UUID()
        self.observers[token] = observer
        observer(self.event)
        return ActionDisposable { [weak self] in
            Queue.mainQueue().async {
                guard let self else { return }
                self.observers.removeValue(forKey: token)
                if self.observers.isEmpty && !self.committing && !self.finished {
                    self.finished = true
                    self.remove()
                    self.operation?.dispose()
                    self.operation = nil
                }
            }
        }
    }

    func start(_ makeOperation: (@escaping () -> Void) -> Signal<Float, NagramiXStorySaveError>) {
        assert(Thread.isMainThread)
        guard !self.finished, !self.observers.isEmpty, self.operation == nil else { return }
        let operation = (makeOperation({ [weak self] in
            assert(Thread.isMainThread)
            self?.committing = true
        }) |> deliverOnMainQueue).start(next: { [weak self] value in
            self?.publish(.progress(value))
        }, error: { [weak self] error in
            self?.finish(.failed(error), keepSaved: false)
        }, completed: { [weak self] in
            self?.finish(.saved, keepSaved: true)
        })
        // A cached resource or permission denial can finish synchronously.
        if self.finished { operation.dispose() }
        else { self.operation = operation }
    }

    private func publish(_ event: Event) {
        guard !self.finished else { return }
        self.event = event
        for observer in Array(self.observers.values) { observer(event) }
    }

    private func finish(_ event: Event, keepSaved: Bool) {
        guard !self.finished else { return }
        self.finished = true
        self.event = event
        let operation = self.operation
        self.operation = nil
        operation?.dispose()
        if keepSaved {
            // Coalesce taps from the header and a menu that was already open.
            Queue.mainQueue().after(30.0, { [weak self] in self?.remove() })
        } else {
            self.remove()
        }
        for observer in Array(self.observers.values) { observer(event) }
        self.observers.removeAll()
    }

    private func remove() {
        if Self.jobs[self.key] === self { Self.jobs.removeValue(forKey: self.key) }
    }
}

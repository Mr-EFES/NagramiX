import Foundation

@main struct NagramiXMediaPrivacyTests {
    static func main() {
        // The real capture policy applies to both screenshot and recording
        // producers, including ephemeral media. Paid media/codes stay protected.
        for enabled in [false, true] {
            NagramiXPrivacySettings.current.bypassScreenshots = enabled
            precondition(nagramiXShouldNotifyScreenCapture() == !enabled)
        }
        let normal = Message(paidContent: nil, id: .init(peerId: .init(value: 2)), attributes: [])
        precondition(normal.nagramiXAllowsScreenshotBypass)
        var paid = normal; paid.paidContent = 1
        precondition(!paid.nagramiXAllowsScreenshotBypass)
        var codes = normal; codes.id = .init(peerId: .init(value: 777000))
        precondition(!codes.nagramiXAllowsScreenshotBypass)

        // Archive formatting is local only, with backwards-compatible decoding.
        let ordinary = NagramiXArchivedMessageAttribute(deletedAt: 1, revisions: [])
        let temporary = NagramiXArchivedMessageAttribute(deletedAt: 1, revisions: [], isTemporary: true)
        var message = normal
        precondition(!message.nagramiXShowsArchiveNotice)
        message.attributes = [ordinary]
        precondition(message.nagramiXShowsArchiveNotice)
        message.attributes = [temporary]
        precondition(!message.nagramiXShowsArchiveNotice)
        let encoder = PostboxEncoder()
        temporary.encode(encoder)
        precondition(NagramiXArchivedMessageAttribute(decoder: .init(encoder.values)).isTemporary)
        precondition(!NagramiXArchivedMessageAttribute(decoder: .init([:])).isTemporary)

        // Real core RPC mapper: false ACK is accepted, RPC error is retryable.
        let context = AccountContext()
        let story = StoryItemSetContainerComponent(context, .init(peerId: .init(value: 2), id: 9))
        let view = StoryViewHarness(story)
        view.tap(story)
        precondition(context.account.network.requests.last!.ids == [9])
        context.account.network.finish(false)
        precondition(!story.nagramiXUsesAnonymousViewing && context.errors.isEmpty)
        for index in 0..<3 {
            var answer: Bool?
            let disposable = _internal_nagramiXRecordStoryView(account: context.account, peerId: .init(value: 2), id: 10).start(next: { answer = $0 })
            context.account.network.finish(index == 0, error: index == 2)
            precondition(answer == (index != 2))
            disposable.dispose()
        }

        // Header and menu observe one real production save job. Closing both
        // progress screens during Photos commit must not allow a second write.
        let key = "account:peer:story:resource"
        let job = NagramiXStorySaveJob(key: key)
        NagramiXStorySaveJob.jobs[key] = job
        var saved = 0
        var progress: Float = 0
        let header = job.subscribe { if case .saved = $0 { saved += 1 } }
        let menu = job.subscribe { if case let .progress(value) = $0 { progress = value } }
        var receiver: Subscriber<Float, NagramiXStorySaveError>!
        var commit: (() -> Void)!
        var disposed = 0
        var started = 0
        job.start { begin in
            started += 1
            commit = begin
            return Signal { subscriber in
                receiver = subscriber
                return ActionDisposable { disposed += 1 }
            }
        }
        job.start { _ in started += 1; return .fail(.library) }
        precondition(started == 1)
        receiver.putNext(0.6)
        precondition(progress == 0.6)
        commit()
        header.dispose(); menu.dispose()
        precondition(disposed == 0 && NagramiXStorySaveJob.jobs[key] === job)
        let reopened = job.subscribe { if case .saved = $0 { saved += 1 } }
        receiver.putNext(1.0); receiver.putCompletion()
        precondition(saved == 1 && disposed == 1)
        let repeatTap = job.subscribe { if case .saved = $0 { saved += 1 } }
        precondition(saved == 2 && started == 1)
        reopened.dispose(); repeatTap.dispose()

        // An old delayed cleanup cannot erase a new operation for that key.
        let replacement = NagramiXStorySaveJob(key: key)
        NagramiXStorySaveJob.jobs[key] = replacement
        Queue.flushDelayed()
        precondition(NagramiXStorySaveJob.jobs[key] === replacement)
        NagramiXStorySaveJob.jobs.removeAll()

        // Cancellation before commit releases the operation and enables retry.
        let cancelled = NagramiXStorySaveJob(key: key)
        NagramiXStorySaveJob.jobs[key] = cancelled
        let observer = cancelled.subscribe { _ in }
        cancelled.start { _ in Signal { _ in ActionDisposable { disposed += 1 } } }
        observer.dispose()
        precondition(disposed == 2 && NagramiXStorySaveJob.jobs[key] == nil)

        // Permission/library errors are never cached as a successful save.
        let failed = NagramiXStorySaveJob(key: key)
        NagramiXStorySaveJob.jobs[key] = failed
        var errors = 0
        let errorObserver = failed.subscribe {
            if case .failed(.permissionDenied) = $0 { errors += 1 }
            if case .saved = $0 { preconditionFailure("False Photos success") }
        }
        failed.start { _ in .fail(.permissionDenied) }
        precondition(errors == 1 && NagramiXStorySaveJob.jobs[key] == nil)
        errorObserver.dispose()
        print("PASS: production capture/archive policy, true/false/error story ACK, shared save observers, cancellation before/during Photos, retry and stale cleanup; Apple APIs mocked")
    }
}

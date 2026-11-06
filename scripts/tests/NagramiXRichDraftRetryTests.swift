@main enum Tests {
    static var count = 0
    static func check(_ value: @autoclosure () -> Bool, _ message: String) {
        count += 1
        if !value() { fatalError("Rich draft retry regression: " + message) }
    }
    static let rich = RichTextMessageAttribute(instantPage: .init(rawMedia: [11,22], blocks: ["caption","album"]))
    static func main() {
        let network = Network()
        UploadControl.reset(2)
        var completed = 0
        let operation = synchronizeDraft(network: network, richText: rich).start(completed: { completed += 1 })
        check(UploadControl.attempts == 1 && network.requests.isEmpty && completed == 0, "failed upload retains the pending draft without a partial request")
        Scheduler.advance(0.19)
        check(UploadControl.attempts == 1, "retry must not spin or fire before its backoff")
        Scheduler.advance(0.02)
        check(UploadControl.attempts == 2 && network.requests.isEmpty && completed == 0, "second failure still keeps operation and local draft")
        Scheduler.advance(0.41)
        check(UploadControl.attempts == 3 && network.requests.count == 1 && completed == 1, "first successful retry saves the complete draft exactly once")
        let saved = network.requests[0]
        check(saved.richMessage == .init(ids: [11,22], blocks: ["caption","album"]), "complete attachment identities and blocks survive upload retries")
        check(saved.message.isEmpty && saved.entities.isEmpty && saved.flags & (1 << 9) != 0 && saved.flags & (1 << 3) == 0, "rich draft never duplicates fallback text/entities")
        check(saved.replyTo?.id == 5 && saved.peer.id == 7 && saved.suggestedPost == 9, "reply, recipient and suggested post preserved")
        check(saved.flags & (1 << 0) != 0 && saved.flags & (1 << 8) != 0, "unrelated native draft flags preserved")
        operation.dispose()
        Scheduler.advance(10)
        check(network.requests.count == 1 && completed == 1, "completed operation cannot save again")

        UploadControl.reset(100)
        let cancelledNetwork = Network()
        var cancelledComplete = 0
        let cancelled = synchronizeDraft(network: cancelledNetwork, richText: rich).start(completed: { cancelledComplete += 1 })
        cancelled.dispose()
        Scheduler.advance(100)
        check(UploadControl.attempts == 1 && cancelledNetwork.requests.isEmpty && cancelledComplete == 0, "account shutdown/draft replacement cancels scheduled retries")

        UploadControl.reset(1000)
        Scheduler.delays.removeAll()
        let pendingNetwork = Network()
        let pending = synchronizeDraft(network: pendingNetwork, richText: rich).start()
        Scheduler.advance(180)
        check(UploadControl.attempts > 30 && pendingNetwork.requests.isEmpty, "persistent upload failure never falls back to a media-less server draft")
        check(abs((Scheduler.delays.first ?? 0) - 0.2) < 1e-9 && Scheduler.delays.allSatisfy { $0 > 0 && $0 <= 5.0 + 1e-9 } && Scheduler.delays.contains { abs($0 - 5.0) < 1e-9 }, "native retry uses bounded increasing backoff")
        let attemptsBeforeCancel = UploadControl.attempts
        pending.dispose(); Scheduler.advance(100)
        check(UploadControl.attempts == attemptsBeforeCancel, "cancel remains effective after reaching maximum delay")

        UploadControl.reset()
        let plainNetwork = Network()
        var plainComplete = 0
        let plain = synchronizeDraft(network: plainNetwork, richText: nil).start(completed: { plainComplete += 1 })
        check(UploadControl.attempts == 0 && plainComplete == 1 && plainNetwork.requests.count == 1, "plain draft retains stock immediate path")
        check(plainNetwork.requests[0].message == "plain" && plainNetwork.requests[0].entities == [.init(id: 3)] && plainNetwork.requests[0].flags & (1 << 3) != 0, "plain text/entities remain exact")
        plain.dispose()
        let textNetwork = Network()
        let text = synchronizeDraft(network: textNetwork, richText: .init(instantPage: .init(rawMedia: [], blocks: ["text-only"]))).start()
        check(UploadControl.attempts == 0 && textNetwork.requests[0].richMessage?.blocks == ["text-only"], "text-only rich draft needs no upload")
        text.dispose()

        UploadControl.reset(1)
        var editErrors = 0
        let edit = resolveEdit(network: Network(), richText: rich).start(error: { _ in editErrors += 1 })
        check(editErrors == 1 && UploadControl.attempts == 1, "edit still exposes upload error rather than retrying or sending bare media")
        edit.dispose()
        let before = UploadControl.attempts
        Scheduler.advance(10)
        check(UploadControl.attempts == before, "draft retry was not added to the shared edit uploader")
        print("\(count) real SignalKit rich-draft checks passed")
    }
}

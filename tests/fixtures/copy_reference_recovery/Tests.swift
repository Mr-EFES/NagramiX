var checks = 0
func expect(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { fatalError(label) }
}
let provenance = PartialMediaReference.message(message: 17)
func doc(_ id: Int64, _ reference: String = "old", hash: Int64 = 3, wireId: Int64? = nil, token: Int = 7) -> TelegramMediaFile {
    TelegramMediaFile(fileId: MediaId(namespace: 1, id: id), partialReference: nil,
        resource: CloudDocumentMediaResource(fileId: wireId ?? id, accessHash: hash, fileReference: Data(reference.utf8)),
        previewRepresentations: [.init(token: token)], videoThumbnails: [.init(token: token)],
        immediateThumbnailData: Data([5]), mimeType: "video/mp4", size: 125,
        attributes: [.init(token: token)], alternativeRepresentations: [])
}
func photo(_ id: Int64, _ reference: String = "old", hash: Int64 = 3, wireId: Int64? = nil, token: Int = 7) -> TelegramMediaImage {
    TelegramMediaImage(imageId: MediaId(namespace: 2, id: id), representations: [.init(token: token)],
        videoRepresentations: [.init(token: token)], immediateThumbnailData: Data([5]),
        emojiMarkup: .init(token: token), reference: .cloud(imageId: wireId ?? id, accessHash: hash, fileReference: Data(reference.utf8)),
        partialReference: nil, flags: .init(rawValue: 3))
}
func poll(_ main: Media?, _ answer: Media?, _ solution: Media?, question: String = "Copied question", id: Int64 = 99) -> TelegramMediaPoll {
    TelegramMediaPoll(pollId: MediaId(namespace: 3, id: id), publicity: .public,
        kind: .quiz(multipleAnswers: true), text: question, textEntities: [.init(token: 9)],
        options: [.init(text: "Copied answer", entities: [.init(token: 8)], opaqueIdentifier: Data([7]),
                        media: answer, date: 12, addedBy: 45)], correctAnswers: [Data([7])],
        results: .init(voters: [.init(selected: true, opaqueIdentifier: Data([7]), count: 5, isCorrect: true)],
                       totalVoters: 5, recentVoters: [45],
                       solution: .init(text: "Copied explanation", entities: [.init(token: 6)], media: solution),
                       hasUnseenVotes: true, canViewStats: true), isClosed: false,
        deadlineTimeout: 15, deadlineDate: 18, pollHash: 5, openAnswers: true,
        revotingDisabled: true, shuffleAnswers: true, hideResultsUntilClose: true,
        isCreator: true, attachedMedia: main, restrictToSubscribers: true, countries: ["FR"])
}
func refresh(_ input: [Media], _ source: [Media]) -> [Media]? {
    nagramiXCopyRefreshedMedia(input, from: Message(media: source), partialReference: provenance)
}
func ref(_ file: TelegramMediaFile) -> String {
    String(data: (file.resource as! CloudDocumentMediaResource).fileReference!, encoding: .utf8)!
}

// A source edit may change its words and settings; only matching media references
// can flow back into the user's already-created copy.
do {
    let originalFile = doc(1)
    let refreshed = refresh([originalFile], [doc(1, "fresh", hash: 4, token: 99)])!
    let file = refreshed[0] as! TelegramMediaFile
    expect(ref(file) == "fresh", "file reference updated")
    expect((file.resource as! CloudDocumentMediaResource).accessHash == 4, "access hash updated")
    expect(file.attributes == originalFile.attributes, "file attributes preserved")
    expect(file.previewRepresentations[0].token == 7, "file preview preserved")
    expect(file.mimeType == originalFile.mimeType && file.size == originalFile.size, "file metadata preserved")
    expect(file.partialReference == provenance, "file source provenance retained")
    expect(file.fileId == originalFile.fileId, "file media identity preserved")
}
do {
    let original = photo(2)
    let image = refresh([original], [photo(2, "fresh", hash: 4, token: 99)])![0] as! TelegramMediaImage
    expect(image.reference == .cloud(imageId: 2, accessHash: 4, fileReference: Data("fresh".utf8)), "photo reference updated")
    expect(image.representations[0].token == 7 && image.videoRepresentations[0].token == 7, "photo representations preserved")
    expect(image.emojiMarkup?.token == 7 && image.immediateThumbnailData == original.immediateThumbnailData, "photo appearance preserved")
    expect(image.partialReference == provenance && image.imageId == original.imageId, "photo identity and provenance preserved")
}
do {
    let original = poll(doc(10), photo(11), doc(12))
    let source = poll(doc(10, "fresh-main"), photo(11, "fresh-answer"), doc(12, "fresh-solution"), question: "Edited at source", id: 100)
    let result = refresh([original], [source])![0] as! TelegramMediaPoll
    expect(ref(result.attachedMedia as! TelegramMediaFile) == "fresh-main", "main poll attachment refreshed")
    expect((result.options[0].media as! TelegramMediaImage).reference == .cloud(imageId: 11, accessHash: 3, fileReference: Data("fresh-answer".utf8)), "answer attachment refreshed")
    expect(ref(result.results.solution!.media as! TelegramMediaFile) == "fresh-solution", "solution attachment refreshed")
    expect(result.pollId == original.pollId && result.pollHash == original.pollHash, "copied poll identity preserved")
    expect(result.text == original.text && result.textEntities == original.textEntities, "question preserved")
    expect(result.options[0].opaqueIdentifier == original.options[0].opaqueIdentifier && result.options[0].date == 12 && result.options[0].addedBy == 45, "answer identity and author metadata preserved")
    expect(result.correctAnswers == original.correctAnswers && result.results.totalVoters == 5 && result.results.voters![0].selected, "quiz answers and vote metadata preserved")
    expect(result.results.solution!.text == "Copied explanation" && result.results.solution!.entities == [.init(token: 6)], "explanation preserved")
    expect(result.deadlineTimeout == 15 && result.deadlineDate == 18 && result.countries == ["FR"], "poll deadlines and countries preserved")
    expect(result.publicity == .public && result.kind == .quiz(multipleAnswers: true), "poll type preserved")
    expect(result.openAnswers && result.revotingDisabled && result.shuffleAnswers && result.hideResultsUntilClose && result.isCreator && result.restrictToSubscribers, "poll settings preserved")
}
do {
    let original = doc(20)
    expect(refresh([original], [doc(20)]) == nil, "unchanged reference falls back")
    expect(refresh([original], []) == nil, "missing source attachment falls back")
    expect(refresh([original], [doc(21, "fresh")]) == nil, "unrelated identity rejected")
    expect(refresh([original], [doc(20, "fresh", wireId: 21)]) == nil, "mismatched cloud identity rejected")
    expect(refresh([original], [photo(20, "fresh")]) == nil, "media type mismatch rejected")
    let sameIdWrongType = TelegramMediaImage(imageId: original.fileId, representations: [],
        immediateThumbnailData: nil, reference: .cloud(imageId: 20, accessHash: 3, fileReference: Data("fresh".utf8)),
        partialReference: nil, flags: .init(rawValue: 0))
    expect(refresh([original], [sameIdWrongType]) == nil, "same MediaId cannot change attachment type")
    expect(refresh([original], [doc(20, "")]) == nil, "empty reference rejected")
    expect(refresh([poll(doc(20), photo(21), doc(22))], [poll(doc(20, "fresh"), nil, doc(22, "fresh"))]) == nil, "missing required answer rejects whole refresh")
    expect(refresh([poll(doc(20), photo(21), doc(22))], [poll(doc(20, "fresh"), photo(21, "fresh"), nil)]) == nil, "missing required solution rejects whole refresh")
    let local = TelegramMediaFile(fileId: .init(namespace: 4, id: 23), partialReference: nil,
        resource: LocalMediaResource(), previewRepresentations: [], videoThumbnails: [],
        immediateThumbnailData: nil, mimeType: "video/mp4", size: 2, attributes: [], alternativeRepresentations: [])
    expect(refresh([local], [doc(23, "fresh")]) == nil, "local media is not replaced by source cloud media")
    let nonUploadable = OtherMedia(nil)
    let mixed = refresh([poll(doc(20), local, nonUploadable)], [doc(20, "fresh")])![0] as! TelegramMediaPoll
    expect(mixed.options[0].media === local && mixed.results.solution!.media === nonUploadable,
           "mixed local and non-uploadable poll slots remain unchanged")
}

// Timeouts and errors must produce one fallback decision and release the source.
do {
    Timer.reset()
    var values: [Int?] = []
    var completed = 0
    let good = nagramiXCopyRefreshSignal(Signal<Int, RevalidateMediaReferenceError>.single(8)).start(
        next: { values.append($0) }, completed: { completed += 1 })
    expect(values.count == 1 && values[0] == 8 && completed == 1, "single native source resolves once")
    Timer.advance(20)
    expect(values.count == 1, "success cancels timeout")
    good.dispose()
    values = []; completed = 0
    let failed = nagramiXCopyRefreshSignal(Signal<Int, RevalidateMediaReferenceError>.fail(.generic)).start(
        next: { values.append($0) }, completed: { completed += 1 })
    expect(values.count == 1 && values[0] == nil && completed == 1, "native error resolves fallback once")
    failed.dispose()
    values = []; completed = 0
    let multiple = Signal<Int, RevalidateMediaReferenceError> { subscriber in
        subscriber.putNext(3); subscriber.putNext(4); subscriber.putCompletion()
        return EmptyDisposable
    }
    let once = nagramiXCopyRefreshSignal(multiple).start(next: { values.append($0) }, completed: { completed += 1 })
    expect(values.count == 1 && values[0] == 3 && completed == 1, "multiple native values resolve one recovery decision")
    once.dispose()
    values = []; completed = 0
    let empty = nagramiXCopyRefreshSignal(Signal<Int, RevalidateMediaReferenceError>.complete()).start(
        next: { values.append($0) }, completed: { completed += 1 })
    expect(values.count == 1 && values[0] == nil && completed == 1, "empty native completion resolves fallback once")
    empty.dispose()
    values = []; completed = 0
    var disposed = 0
    let stalled = Signal<Int, RevalidateMediaReferenceError> { _ in ActionDisposable { disposed += 1 } }
    let waiting = nagramiXCopyRefreshSignal(stalled).start(next: { values.append($0) }, completed: { completed += 1 })
    Timer.advance(14.99)
    expect(values.isEmpty && disposed == 0, "refresh remains alive before fifteen seconds")
    Timer.advance(0.02)
    expect(values.count == 1 && values[0] == nil && completed == 1 && disposed == 1, "timeout resolves fallback and disposes native source")
    Timer.advance(30)
    expect(values.count == 1 && completed == 1, "timeout emits one terminal decision")
    waiting.dispose()
    expect(disposed == 1, "timeout disposal idempotent")
    Timer.reset()
    values = []; disposed = 0
    let cancelled = nagramiXCopyRefreshSignal(stalled).start(next: { values.append($0) })
    cancelled.dispose()
    Timer.advance(30)
    expect(values.isEmpty && disposed == 1, "outbox cancellation stops refresh and timer")
    // Native timeout starts alternate.next before replacing/disposal of the old
    // source. Reentering the source in that exact window models a concurrent late
    // response: the final native take(1) must fence it out.
    Timer.reset()
    values = []; completed = 0
    var nativeSubscriber: Subscriber<Int, RevalidateMediaReferenceError>?
    let lateSource = Signal<Int, RevalidateMediaReferenceError> { subscriber in
        nativeSubscriber = subscriber
        return EmptyDisposable
    }
    let racing = nagramiXCopyRefreshSignal(lateSource).start(next: { value in
        values.append(value)
        if value == nil { nativeSubscriber?.putNext(9) }
    }, completed: { completed += 1 })
    Timer.advance(15)
    expect(values.count == 1 && values[0] == nil && completed == 1, "late native result during timeout emits no second decision")
    racing.dispose()
}
// Execute the production sender's actual recovery branch with both immediate and
// asynchronous recursive-uploader results, and verify its original outbox identity.
do {
    let original = doc(30)
    let info = OutgoingContentInfoMessageAttribute()
    let attributes: [MessageAttribute] = [info]
    for signalContent in [false, true] {
        let context = MediaReferenceRevalidationContext(.single(Message(media: [doc(30, "fresh")])))
        let results = SenderResults()
        let request = results.observe(productionRefreshCopy(network: Network(signalContent: signalContent),
            revalidationContext: context, isGrouped: true, passFetchProgress: false, forceNoBigParts: true,
            attributes: attributes, media: [original]))
        expect(results.records.count == 1 && results.completed == 1, "sender flattens recursive result once")
        let record = results.records[0]
        expect(!record.forceReupload && !record.refreshAgain, "successful refresh retries cloud reference once")
        expect(ref(record.media[0] as! TelegramMediaFile) == "fresh", "sender forwards refreshed media")
        expect(record.messageId == MessageId(peerId: 2, id: 44) && record.peerId == 2, "same pending message and recipient")
        expect(record.attributes.count == 1 && record.attributes[0] === info && record.text == "copied caption", "same persisted attributes and caption")
        expect(record.isGrouped && !record.passFetchProgress && record.forceNoBigParts, "same native upload options")
        expect(context.requests == 1 && context.requestedSource == 17 && context.usedBackground == false, "one native source revalidation")
        request.dispose()
    }
    let fallbackSources: [Signal<Message, RevalidateMediaReferenceError>] = [
        .single(Message(media: [doc(30)])), .single(Message(media: [])), .fail(.generic), .complete()
    ]
    for source in fallbackSources {
        let context = MediaReferenceRevalidationContext(source)
        let results = SenderResults()
        let request = results.observe(productionRefreshCopy(revalidationContext: context, attributes: attributes, media: [original]))
        expect(results.records.count == 1 && results.records[0].forceReupload, "sender falls back to byte upload")
        expect(results.records[0].media[0] === original && results.records[0].messageId == MessageId(peerId: 2, id: 44), "fallback retains original media and pending identity")
        expect(!results.records[0].refreshAgain && context.requests == 1, "fallback does not recursively refresh")
        request.dispose()
    }
    Timer.reset()
    let stalled = MediaReferenceRevalidationContext(.never())
    let delayed = SenderResults()
    let waiting = delayed.observe(productionRefreshCopy(revalidationContext: stalled, attributes: attributes, media: [original]))
    expect(delayed.records.isEmpty, "sender waits for source before timeout")
    Timer.advance(15)
    expect(delayed.records.count == 1 && delayed.records[0].forceReupload && delayed.records[0].media[0] === original, "sender timeout reaches byte fallback once")
    waiting.dispose()
    let absent = MediaReferenceRevalidationContext(.never())
    let noSource = SenderResults()
    let noSourceRequest = noSource.observe(productionRefreshCopy(revalidationContext: absent, attributes: attributes,
        media: [original], explicitPartialReference: nil))
    expect(absent.requests == 0 && noSource.records.count == 1 && noSource.records[0].forceReupload, "missing provenance immediately uploads bytes")
    noSourceRequest.dispose()
    let referenceContext = MediaReferenceRevalidationContext(.single(Message(media: [doc(30, "fresh")])))
    let referenceResult = SenderResults()
    let referenceRequest = referenceResult.observe(productionRefreshCopy(revalidationContext: referenceContext,
        attributes: attributes, media: [original], mediaReference: .init(partial: .message(message: 18)), explicitPartialReference: nil))
    expect(referenceContext.requestedSource == 18 && referenceResult.records.count == 1 && !referenceResult.records[0].forceReupload,
           "mediaReference provenance supports recovery without persisted partial")
    referenceRequest.dispose()
    for mode in [0, 1, 2, 3] {
        let context = MediaReferenceRevalidationContext(.never())
        let bypass = SenderResults()
        let request = bypass.observe(productionRefreshCopy(revalidationContext: context,
            forceReupload: mode == 1, attributes: mode == 2 ? [] : attributes, media: [original],
            nagramiXRefreshCopyReferences: mode != 0, forwardInfo: mode == 3 ? ForwardSourceInfoAttribute() : nil))
        expect(context.requests == 0 && bypass.bypassed == 1 && bypass.records.isEmpty, "normal/forced/native forward sends bypass copy refresh")
        request.dispose()
    }
}
print("Copy reference recovery production/runtime checks: \(checks)")

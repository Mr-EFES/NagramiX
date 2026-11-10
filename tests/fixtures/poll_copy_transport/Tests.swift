var checks=0
func check(_ value:@autoclosure()->Bool,_ reason:String){if !value(){FileHandle.standardError.write(Data(("Poll transport regression: "+reason+"\n").utf8));exit(91)};checks+=1}
func error(_ text:String)->Signal<Api.MessageMedia,MTRpcError>{.fail(MTRpcError(errorCode:400,errorDescription:text))}
func fileInput(_ media:Api.InputMedia?)->TelegramMediaFile?{if case let .document(file)?=media{return file};return nil}
func answers(_ poll:Api.PollMedia)->[Api.PollAnswer]{switch poll.poll{case let .poll(data):return data.answers}}
func run(_ poll:TelegramMediaPoll,_ network:Network=Network(),_ postbox:Postbox=Postbox(),_ refresh:MediaReferenceRevalidationContext=MediaReferenceRevalidationContext(),peer:PeerId=2,attributes:[MessageAttribute]=[OutgoingContentInfoMessageAttribute()],force:Bool=false)->Probe{
    let probe=Probe();probe.start(productionPoll(poll,network:network,postbox:postbox,revalidationContext:refresh,peerId:peer,attributes:attributes,forceReupload:force));return probe
}
func copied(_ main:Media?,_ answer:Media?=nil,_ solution:Media?=nil)->TelegramMediaPoll{nagramiXCopyPollAsNew(poll(main,answer,solution))!}

@main struct PollCopyTransportTests {static func main(){
    // Received opaque IDs, selected votes, channel membership and timer state
    // never belong to a fresh independent poll. Native poll text and media do.
    let source=poll(doc(9),photo(2),doc(3))
    let copy=nagramiXCopyPollAsNew(source)!
    check(copy.pollId != source.pollId && copy.pollHash==0,"new local poll identity")
    check(copy.options[0].opaqueIdentifier==Data("0".utf8),"fresh native option IDs")
    check(copy.correctAnswers==[Data("0".utf8)],"quiz correct answer remaps to new option identity")
    check(!copy.restrictToSubscribers,"source channel rule is not inherited")
    check(copy.results.voters==nil && copy.results.totalVoters==nil && copy.deadlineDate==nil && copy.deadlineTimeout==nil,"votes and old deadline do not leak")
    check(copy.text==source.text && copy.options[0].text==source.options[0].text,"authored content remains complete")
    for peer:PeerId in [2,3,4] {
        let network=Network(),box=Postbox();let probe=run(copy,network,box,peer:peer)
        check(probe.errors==0 && probe.poll != nil,"whole poll produces final send payload")
        check(network.requests.count==3 && box.uploads.isEmpty,"cloud video is registered without byte upload")
        check(network.automaticWaits==[false,false,false],"no hidden infinite flood wait during registration")
        let wire=probe.poll!
        check(wire.attachedMedia != nil && wire.solutionMedia != nil,"question and solution attachments preserved")
        check(wire.flags & (1<<3) != 0 && wire.flags & (1<<2) != 0,"wire flags match present poll attachments")
        check(wire.correctAnswers==[0],"quiz indices follow canonical option ordering")
        for answer in answers(wire){if case let .inputPollAnswer(data)=answer {check(data.media != nil,"answer attachment preserved")}else{check(false,"new poll uses input answers")}}
    }
    // Include text-only options in the same new input constructor.
    let textOnly=copied(doc(9));let sent=run(textOnly)
    for answer in answers(sent.poll!){if case let .inputPollAnswer(data)=answer {check(data.media==nil,"text-only answer has no invented attachment")}else{check(false,"new poll uses input answers")}}
    // Match the reported post: one video, nine shuffled text options, regular
    // multiple choice, channel restrictions and received non-canonical IDs.
    do {
        let options=(0..<9).map { index in TelegramMediaPollOption(text:"Option \(index)",entities:[.init(token:index)],opaqueIdentifier:Data([UInt8(90+index)]),media:nil,date:15,addedBy:99) }
        let source=TelegramMediaPoll(pollId:MediaId(namespace:3,id:91),publicity:.anonymous,kind:.poll(multipleAnswers:true),text:"Video and voting https://example.org",textEntities:[.init(token:11)],options:options,correctAnswers:[],results:.init(voters:nil,totalVoters:900,recentVoters:[99],solution:nil,hasUnseenVotes:true,canViewStats:false),isClosed:false,deadlineTimeout:nil,deadlineDate:nil,pollHash:8,openAnswers:false,revotingDisabled:false,shuffleAnswers:true,hideResultsUntilClose:false,isCreator:false,attachedMedia:doc(9),restrictToSubscribers:true,countries:[])
        for peer:PeerId in [2,3,4] {
            let network=Network(),box=Postbox(),copy=nagramiXCopyPollAsNew(source)!
            let probe=run(copy,network,box,peer:peer)
            check(probe.poll != nil && probe.errors==0,"nine-option video poll builds for single/broadcast recipient")
            let wire=probe.poll!
            check(answers(wire).count==9 && wire.correctAnswers==nil && wire.solution==nil,"ordinary poll has all nine options and no quiz fields")
            if case let .poll(data)=wire.poll {
                check(data.flags & (1<<2) != 0 && data.flags & (1<<8) != 0 && data.flags & (1<<11)==0,"multiple/shuffle preserved and source channel rule removed")
            }
            check(network.requests.count==1 && box.uploads.isEmpty && fileInput(wire.attachedMedia) != nil,"video poll reuses cloud video without full download")
        }
    }
    // The ordinary composer/native send route keeps its original behavior.
    let nativeNetwork=Network();let native=run(poll(doc(9),nil,nil),nativeNetwork,attributes:[])
    check(native.poll != nil && nativeNetwork.requests.isEmpty,"native composer fast path unchanged")
    if case .pollAnswer = answers(native.poll!)[0]{}else{check(false,"native answer form unchanged")}
    // A stale reference refreshes once, then the new authored payload is kept.
    do {
        let network=Network(),box=Postbox(),refresh=MediaReferenceRevalidationContext()
        network.responders=[{error("FILE_REFERENCE_EXPIRED")}]
        refresh.result = .single(Message(media:[doc(9,"fresh")]))
        let probe=run(copied(doc(9)),network,box,refresh)
        check(probe.poll != nil && network.requests.count==2 && box.uploads.isEmpty,"stale media reference refreshes before byte upload")
        check(refresh.requests==1 && fileInput(probe.poll!.attachedMedia).map{String(data:($0.resource as! CloudDocumentMediaResource).fileReference!,encoding:.utf8)}=="fresh","refreshed file reference reaches final poll")
    }
    // Empty/error/timeout refresh releases the same send to byte upload.
    for mode in 0..<3 {
        Timer.reset();let network=Network(),box=Postbox(),refresh=MediaReferenceRevalidationContext()
        network.responders=[{error("FILE_REFERENCE_EXPIRED")}]
        if mode==1{refresh.result = .fail(.generic)}
        if mode==2{refresh.result=Signal{_ in EmptyDisposable}}
        let probe=run(copied(doc(9)),network,box,refresh)
        if mode==2{check(probe.poll==nil,"pending refresh waits without fake success");Timer.advance(16)}
        check(probe.poll != nil && box.uploads.count==1,"empty refresh falls back to bytes")
        check(box.uploads[0].forced && box.uploads[0].grouped && box.uploads[0].copyFlag,"byte fallback retains copied-media transport policy")
        check(box.uploads[0].partial == .message(message:17),"byte fallback keeps source fetch provenance")
    }
    // Second rejected reference goes to bytes once, never an unbounded loop.
    do {
        let network=Network(),box=Postbox(),refresh=MediaReferenceRevalidationContext()
        network.responders=[{error("FILE_REFERENCE_EXPIRED")},{error("MEDIA_INVALID")}]
        refresh.result = .single(Message(media:[doc(9,"fresh")]))
        let probe=run(copied(doc(9)),network,box,refresh)
        check(probe.poll != nil && refresh.requests==1 && network.requests.count==2 && box.uploads.count==1,"bounded refresh then bytes")
    }
    for failure in ["CHAT_WRITE_FORBIDDEN","USER_BANNED_IN_CHANNEL","FLOOD_WAIT_20","AUTH_KEY_UNREGISTERED"] {
        let network=Network(),box=Postbox(),refresh=MediaReferenceRevalidationContext();network.responders=[{error(failure)}]
        let probe=run(copied(doc(9)),network,box,refresh)
        check(probe.errors==1 && probe.poll==nil,"permission failure remains a real failure")
        check(box.uploads.isEmpty && refresh.requests==0,"permission failure does not start byte fallback")
    }
    do {
        let network=Network(),box=Postbox()
        network.responders=[{.single(.messageMediaDocument(.init(document:doc(9,""),altDocuments:nil)))}]
        let probe=run(copied(doc(9)),network,box)
        check(probe.poll != nil && box.uploads.count==1,"empty registered reference falls back instead of sending invalid poll media")
    }
    // Deduplicate reused slots, while preserving every original position.
    do {
        let file=doc(9),network=Network(),box=Postbox();let probe=run(copied(file,file,file),network,box)
        check(probe.poll != nil && network.requests.count==1,"shared poll resource registered once")
        check(fileInput(probe.poll!.attachedMedia) != nil && fileInput(probe.poll!.solutionMedia) != nil,"deduplicated reference fills all slots")
    }
    // Actual local media uses byte transport immediately; cloud must not.
    do {
        let network=Network(),box=Postbox();let probe=run(copied(doc(9)),network,box,force:true)
        check(probe.poll != nil && box.uploads.count==1 && network.requests.isEmpty,"forced independent bytes avoid original cloud reference")
    }
    // Cancellation detaches the pending native request before later callbacks.
    do {
        let network=Network(),box=Postbox();var pending:Subscriber<Api.MessageMedia,MTRpcError>?
        network.responders=[{Signal{subscriber in pending=subscriber;return EmptyDisposable}}]
        let probe=run(copied(doc(9)),network,box);probe.disposable?.dispose()
        pending?.putError(MTRpcError(errorCode:400,errorDescription:"FILE_REFERENCE_EXPIRED"))
        check(probe.poll==nil && box.uploads.isEmpty && network.cancellations==1,"cancelled registration cannot start late fallback")
    }
    print("PASS poll copy transport checks: \(checks)")
}}

private var checks=0
private final class WeakAction {weak var value:NagramiXArchivedPlaybackAction?;init(_ value:NagramiXArchivedPlaybackAction?){self.value=value}}
private func check(_ value:@autoclosure()->Bool,_ name:String){checks += 1;if !value(){print(name);exit(91)}}
private func snapshot(_ message:EngineRawMessage,_ file:TelegramMediaFile?=nil,status:MediaPlayerStatus.Status = .playing,time:Double=13,duration:Double=44,playlist:PeerMessagesMediaPlaylistId?=nil,itemMessage:EngineRawMessage?=nil,account:Int64=1,type:MediaManagerPlayerType = .voice,generation:Double=0,rate:Double=1)->TestMediaManager.Value {
    let itemMessage=itemMessage ?? message
    let file=file ?? message.media[0] as! TelegramMediaFile
    let state=SharedMediaPlayerItemPlaybackState(playlistId:playlist ?? .recentActions(message.id.peerId),playlistLocation:TestLocation(),item:TestItem(id:PeerMessagesMediaPlaylistItemId(messageId:itemMessage.id,messageIndex:itemMessage.index),playbackData:SharedMediaPlaybackData(type:.instantVideo,source:.telegramFile(reference:FileMediaReference(media:file),isCopyProtected:false,isViewOnce:false))),previousItem:nil,nextItem:nil,status:MediaPlayerStatus(status:status,timestamp:time,duration:duration,generationTimestamp:generation,baseRate:rate),order:.regular,looping:.none,playerIndex:17)
    return(Account(account),.state(state),type)
}
@main struct ArchivedRoundTests {
    static func main(){
        let message=EngineRawMessage()
        do {
            let manager=TestMediaManager();manager.value=snapshot(message)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1;manager.nativePlayerIndex += 1;manager.nativeSurfaceIndex += 1});Clock.advance()
            check(opens==0 && manager.commands==["toggle"],"pause keeps native player")
            check(manager.nativePlayerIndex==17 && manager.nativeSurfaceIndex==19 && manager.baseRate==1.5,"pause preserves decoder surface rate")
            check(manager.filteredCalls==0,"archive round uses native owner state")
            manager.value=snapshot(message,status:.paused,time:16)
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance()
            check(opens==0 && manager.commands==["toggle","toggle"],"resume keeps position and player")
            Clock.advance(1);check(opens==0,"completed decision cannot reopen later")
        }
        do {
            let manager=TestMediaManager();manager.value=snapshot(message,status:.paused,time:44)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance()
            check(opens==0 && manager.commands==["seek:0.0","play"],"repeat keeps native player")
        }
        do {
            let manager=TestMediaManager();manager.value=(Account(),.loading,.voice)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance(0.1)
            check(opens==0 && manager.commands.isEmpty,"loading never reopens")
            manager.emit(snapshot(message,status:.paused,time:21));Clock.advance()
            check(opens==0 && manager.commands==["toggle"],"loading resolves exact owner once")
            Clock.advance(1);check(opens==0 && manager.commands.count==1,"resolved loading cancels fallback")
        }
        do {
            let manager=TestMediaManager();manager.value=(Account(),.loading,.voice)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance(0.51)
            check(opens==1,"unresolved loading has bounded native open")
            manager.emit(snapshot(message));Clock.advance();check(manager.commands.isEmpty,"late owner cannot toggle after fallback")
        }
        for time in [0.0,13.25,43.0] {
            let manager=TestMediaManager();manager.value=snapshot(message,TelegramMediaFile(7,3),time:time,playlist:.peer(message.id.peerId))
            let action=NagramiXArchivedPlaybackAction();var openedAt:[Double]=[];var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},openAt:{openedAt.append($0)},open:{opens += 1});Clock.advance()
            check(openedAt==[time] && opens==0 && manager.commands.isEmpty,"migration retains playback position")
            manager.emit(snapshot(message,time:time));Clock.advance()
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},openAt:{openedAt.append($0)},open:{opens += 1});Clock.advance()
            check(openedAt.count==1 && manager.commands==["toggle"],"local copy migrates only once")
        }
        for time in [-1.0,Double.nan,Double.infinity,44.0] {
            let manager=TestMediaManager();manager.value=snapshot(message,TelegramMediaFile(7,3),status:.paused,time:time)
            let action=NagramiXArchivedPlaybackAction();var openedAt:[Double]=[]
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},openAt:{openedAt.append($0)},open:{});Clock.advance()
            check(openedAt==[0],"migration clamps invalid or ended time")
        }
        do {
            Clock.advance(10)
            let manager=TestMediaManager();manager.value=snapshot(message,TelegramMediaFile(7,3),time:13,generation:Clock.now-4,rate:1.5)
            let action=NagramiXArchivedPlaybackAction();var openedAt:[Double]=[]
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},openAt:{openedAt.append($0)},open:{});Clock.advance()
            check(openedAt==[19],"migration uses native clock and rate")
        }
        do {
            let manager=TestMediaManager();manager.value=(Account(),.loading,.voice)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1;manager.emit(snapshot(message))});Clock.advance(1)
            check(opens==1 && manager.commands.isEmpty,"fallback is one decision with synchronous reopen")
        }
        for caseId in 0..<6 {
            let manager=TestMediaManager()
            let other=EngineRawMessage();other.id.id=99
            switch caseId {
            case 0:manager.value=snapshot(message,itemMessage:other)
            case 1:manager.value=snapshot(message,account:2)
            case 2:manager.value=snapshot(message,type:.music)
            case 3:manager.value=snapshot(message,playlist:.custom)
            case 4:manager.value=snapshot(message,TelegramMediaFile(8,101))
            default:manager.value=nil
            }
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance()
            check(opens==1 && manager.commands.isEmpty,caseId==1 ? "other account not controlled" : "other message opens selected copy")
        }
        do {
            let manager=TestMediaManager();manager.value=snapshot(message)
            let action=NagramiXArchivedPlaybackAction();var current=true;var opens=0
            action.activate(context:AccountContext(manager),message:message,isCurrent:{current},open:{opens += 1});current=false;Clock.advance(1)
            check(opens==0 && manager.commands.isEmpty,"stale row has no side effects")
        }
        do {
            let manager=TestMediaManager();manager.value=(Account(),.loading,.voice)
            var action:NagramiXArchivedPlaybackAction?=NagramiXArchivedPlaybackAction();let released=WeakAction(action);var opens=0
            action?.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});action=nil;Clock.advance(1)
            check(released.value==nil && manager.observerCount==0 && opens==0,"disposal cancels observer and fallback")
        }
        do {
            let file=TelegramMediaFile();file.isInstantVideo=false
            let voice=EngineRawMessage(file)
            let manager=TestMediaManager();manager.value=snapshot(voice,file,status:.paused,time:44)
            let action=NagramiXArchivedPlaybackAction();var opens=0
            action.activate(context:AccountContext(manager),message:voice,isCurrent:{true},open:{opens += 1});Clock.advance()
            check(manager.filteredCalls==1 && opens==1,"voice action unchanged")
        }
        do {
            let manager=TestMediaManager();manager.value=snapshot(message,TelegramMediaFile(7,3),time:17)
            let row=TestRoundRow();let interaction=TestInteraction()
            row.item=TestRowItem(context:AccountContext(manager),message:message,controllerInteraction:interaction);row.media=message.media[0] as? TelegramMediaFile
            row.tap();Clock.advance()
            check(interaction.opens==[.timecode(17)],"real row passes migration timecode")
            manager.value=(Account(),.loading,.voice)
            row.tap();row.media=TelegramMediaFile(7,555)
            manager.emit(snapshot(message));Clock.advance(1)
            check(interaction.opens.count==1 && manager.commands.isEmpty,"recycled resource cancels old row action")
        }
        for status:MediaPlayerStatus.Status in [.playing,.paused,.buffering] {
            for time in [0.0,12.5,43.94,43.99,44] {
                let manager=TestMediaManager();manager.value=snapshot(message,status:status,time:time)
                let action=NagramiXArchivedPlaybackAction();var opens=0
                action.activate(context:AccountContext(manager),message:message,isCurrent:{true},open:{opens += 1});Clock.advance()
                let shouldReplay=status == .paused && time>=43.95
                check(opens==0 && manager.commands==(shouldReplay ? ["seek:0.0","play"] : ["toggle"]),"native state controls never reopen ready local media")
            }
        }
        for autoplay in [false,true] {
            NagramiXTabSettings.voiceAutoplayEnabled=autoplay
            let replay=NativeReplayProbe(message)
            let oldCompletion=replay.decoder.completion!
            oldCompletion() // The native decoder has already queued its old end notification.
            replay.userSeek(0)
            Clock.advance()
            check(replay.ended==0 && replay.next==0 && replay.decoder.pauses==0,"queued old completion cannot stop replay")
            replay.decoder.completion?();Clock.advance()
            check(autoplay ? replay.next==1 : replay.ended==1,"new replay completion works")
            replay.userSeek(0)
            replay.decoder.completion?();Clock.advance()
            check(autoplay ? replay.next==2 : replay.ended==2,"second replay completion works")
            check(replay.decoder.seeks==[0,0],"repeat keeps same native decoder")
        }
        NagramiXTabSettings.voiceAutoplayEnabled=false
        do {
            let ordinary=EngineRawMessage();ordinary.attributes=[]
            let replay=NativeReplayProbe(ordinary)
            replay.userSeek(0)
            check(replay.nagramiXPlaybackGeneration==1,"ordinary completion policy unchanged")
        }
        print("\(checks) archived native-round checks passed")
    }
}

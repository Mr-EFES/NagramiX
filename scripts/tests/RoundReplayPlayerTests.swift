import Foundation
import Postbox
import TelegramCore
import SwiftSignalKit
import AccountContext

@main struct RoundPlayerTests {
    static func main() {
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Round player regression: "+s+"\n").utf8));exit(96)};checks+=1}
        let context=AccountContext(),action=NagramiXArchivedPlaybackAction()
        let manager=context.sharedContext.mediaManager
        let id=MessageId(PeerId(8),1),otherId=MessageId(PeerId(8),2)
        let message=Message(id),archived=Message(id,[NagramiXArchivedMessageAttribute()])
        let item=PeerMessagesMediaPlaylistItemId(messageId:id,messageIndex:MessageIndex(id))
        var opens=0,current=true
        func activate(_ message:Message){action.activate(context:context,message:message,isCurrent:{current},open:{opens+=1})}
        func state(_ playlist:PeerMessagesMediaPlaylistId,_ status:PlaybackStatus,_ itemId:SharedMediaPlaylistItemId?=nil,_ account:Int=1){manager.channel.set((Account(account),.state(SharedMediaPlayerItemPlaybackState(playlist,itemId ?? item,status))))}
        activate(message)
        check(opens==1 && manager.toggles==0,"no player opens once")
        state(.peer(id.peerId),PlaybackStatus(.playing,27,3));activate(message)
        check(opens==1 && manager.toggles==1,"native single-message playlist toggles instead of recreating decoder")
        state(.recentActions(id.peerId),PlaybackStatus(.paused,27,3));activate(archived)
        check(opens==1 && manager.toggles==2,"same retained snapshot resumes existing decoder")
        state(.recentActions(id.peerId),PlaybackStatus(.paused,27,27));activate(archived)
        check(opens==2,"completed retained video reopens for replay")
        state(.recentActions(id.peerId),PlaybackStatus(.paused,27,3),nil,2);activate(archived)
        check(opens==3 && manager.toggles==2,"another account cannot be toggled")
        state(.recentActions(id.peerId),PlaybackStatus(.playing,27,3),PeerMessagesMediaPlaylistItemId(messageId:otherId,messageIndex:MessageIndex(otherId)));activate(archived)
        check(opens==4 && manager.toggles==2,"another message cannot be toggled")
        state(.recentActions(PeerId(9)),PlaybackStatus(.playing,27,3));activate(archived)
        check(opens==5 && manager.toggles==2,"another peer cannot be toggled")
        manager.channel.deferred=true
        activate(archived);current=false
        state(.recentActions(id.peerId),PlaybackStatus(.playing,27,3))
        check(opens==5 && manager.toggles==2,"stale row request cancelled by lease")
        current=true;activate(archived);activate(archived)
        state(.recentActions(id.peerId),PlaybackStatus(.playing,27,3))
        check(manager.toggles==3,"superseded asynchronous activation cannot double-toggle")
        state(.recentActions(id.peerId),PlaybackStatus(.playing,27,4))
        check(manager.toggles==3,"take-one ignores later playback ticks")
        print("Round player regression checks: \(checks)")
    }
}

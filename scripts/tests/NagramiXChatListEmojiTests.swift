private var checks = 0
private func check(_ value: @autoclosure ()->Bool, _ label: String) { precondition(value(), label); checks += 1 }

@main private enum Tests {
    static func main() {
        let account=PeerId(value:1), otherAccount=PeerId(value:2), peer=PeerId(value:100)
        let first=MessageId(peerId:peer,namespace:0,id:10), second=MessageId(peerId:peer,namespace:0,id:11)
        let scheduler=Scheduler(), resolver=Resolver()
        let state=NagramiXChatListPreviewEmoji(schedule:scheduler.schedule)
        var refreshes=0
        func preview(_ ids:[Int64], alt:String="🆕") -> NSAttributedString {
            let text=NSMutableAttributedString(string:"🙂 ")
            for id in ids {
                text.append(NSAttributedString(string:alt,attributes:[instantPagePreviewCustomEmoji:ChatTextInputTextCustomEmojiAttribute(interactivelySelectedFromPackId:42,fileId:id,file:nil,enableAnimation:false)]))
            }
            text.append(NSAttributedString(string:" — новое приложение")); return text
        }
        func update(_ text:NSAttributedString, message:MessageId?=nil, owner:PeerId?=nil) {
            state.update(accountPeerId:owner ?? account,messageId:message ?? first,text:text,resolve:resolver.request,refresh:{ refreshes += 1 })
        }
        let source=preview([5,2,5,9,2])
        check(nagramiXPinnedPreviewEmojiFileIds(source)==Set([2,5,9]),"deduplicate bounded preview IDs")
        update(source)
        check(resolver.ids==[[2,5,9]],"request missing original IDs in deterministic order")
        update(source)
        check(resolver.ids.count==1,"same unresolved layout does not loop requests")
        resolver.completions[0]([2:TelegramMediaFile(2),5:TelegramMediaFile(5),9:TelegramMediaFile(9)])
        check(refreshes==0,"cache result cannot reenter apply")
        scheduler.drain()
        check(refreshes==1,"metadata refreshes native layout once")
        let rendered=state.snapshot().applying(to:source,accountPeerId:account,messageId:first)
        check(rendered.string==source.string,"original alt backing text preserved")
        check(nagramiXPinnedPreviewEmojiFileIds(rendered).isEmpty,"resolved emoji become active native attributes")
        var attachments=0
        rendered.enumerateAttribute(ChatTextInputAttributes.customEmoji,in:NSRange(location:0,length:rendered.length)) { value,_,_ in
            if let emoji=value as? ChatTextInputTextCustomEmojiAttribute {
                check(emoji.file?.fileId.id==emoji.fileId,"actual file matches original emoji")
                check(emoji.interactivelySelectedFromPackId==42 && !emoji.enableAnimation,"native metadata and animation preference preserved")
                attachments += 1
            }
        }
        check(attachments==5,"five consecutive emoji including repeated IDs preserved")
        check(source.attribute(ChatTextInputAttributes.customEmoji,at:3,effectiveRange:nil)==nil,"no source/message mutation")
        check(state.snapshot().applying(to:source,accountPeerId:otherAccount,messageId:first) === source,"account isolation")
        check(state.snapshot().applying(to:source,accountPeerId:account,messageId:second) === source,"full message isolation")
        check(state.snapshot().applying(to:source,accountPeerId:account,messageId:MessageId(peerId:PeerId(value:999),namespace:0,id:10)) === source,"same numeric ID in another peer isolated")
        check(state.snapshot().applying(to:source,accountPeerId:account,messageId:MessageId(peerId:peer,namespace:1,id:10)) === source,"same numeric ID in another namespace isolated")
        let emptySnapshot=NagramiXChatListPreviewEmoji.Snapshot(accountPeerId:account,messageId:first,files:[:])
        let baselineRefreshes=refreshes
        for _ in 0..<5 {
            state.update(accountPeerId:account,messageId:first,text:source,rendered:emptySnapshot,resolve:resolver.request,refresh:{refreshes += 1})
        }
        check(refreshes==baselineRefreshes,"stale async apply refresh deferred")
        scheduler.drain()
        check(refreshes==baselineRefreshes+1 && resolver.ids.count==1,"stale async apply repaired once without network loop")
        state.update(accountPeerId:account,messageId:first,text:source,rendered:state.snapshot(),resolve:resolver.request,refresh:{preconditionFailure("fresh snapshot relayout loop")})
        scheduler.drain()
        let literal=NSAttributedString(string:"🆕 🆕 ABC ✅")
        check(nagramiXPinnedPreviewEmojiFileIds(literal).isEmpty,"literal NEW/ABC/Unicode never replaced")
        update(literal)
        check(state.snapshot().files.isEmpty,"changed preview clears unused files")
        check(resolver.ids.count==1,"plain text triggers no query")
        let known=NSMutableAttributedString(string:"🆕")
        known.addAttribute(instantPagePreviewCustomEmoji,value:ChatTextInputTextCustomEmojiAttribute(interactivelySelectedFromPackId:nil,fileId:70,file:TelegramMediaFile(70)),range:NSRange(location:0,length:2))
        update(known)
        check(resolver.ids.count==1,"known rich file needs no extra request")

        // Same message edited to other IDs: an old callback must be ignored.
        update(preview([100])); let stale=resolver.completions.last!
        update(preview([200])); stale([100:TelegramMediaFile(100)])
        scheduler.drain(); check(state.snapshot().files.isEmpty,"stale edited-preview reply ignored")
        resolver.completions.last!([200:TelegramMediaFile(200,namespace:1),999:TelegramMediaFile(999)])
        scheduler.drain(); check(state.snapshot().files.isEmpty,"wrong namespace/unrequested files rejected")
        resolver.completions.last!([200:TelegramMediaFile(200)])
        scheduler.drain(); check(state.snapshot().files[200] != nil,"valid later reply accepted")
        let before=refreshes
        resolver.completions.last!([200:TelegramMediaFile(200)])
        scheduler.drain(); check(refreshes==before,"duplicate metadata emits no layout loop")

        update(preview([300])); let prior=resolver.completions.last!
        state.prepare(accountPeerId:account,messageId:second)
        prior([300:TelegramMediaFile(300)]); scheduler.drain()
        check(state.snapshot().messageId==second && state.snapshot().files.isEmpty,"setup cancels old row before async layout")
        update(preview([300]),message:second,owner:otherAccount)
        let previousAccount=resolver.completions.last!
        state.prepare(accountPeerId:account,messageId:second)
        previousAccount([300:TelegramMediaFile(300)]); scheduler.drain()
        check(state.snapshot().accountPeerId==account && state.snapshot().files.isEmpty,"cross-account late callback rejected")
        check(resolver.cancelled>=4,"superseded native subscriptions disposed")

        let immediate=Resolver(); immediate.immediate=[7:TelegramMediaFile(7)]
        let sync=NagramiXChatListPreviewEmoji(schedule:scheduler.schedule)
        var syncRefresh=0
        sync.update(accountPeerId:account,messageId:first,text:preview([7]),resolve:immediate.request,refresh:{syncRefresh += 1})
        check(syncRefresh==0,"synchronous engine cache hit deferred")
        scheduler.drain(); check(syncRefresh==1 && sync.snapshot().files[7] != nil,"synchronous hit retained after apply")
        sync.update(accountPeerId:account,messageId:nil,text:preview([7]),resolve:immediate.request,refresh:{syncRefresh += 1})
        check(sync.snapshot().files.isEmpty && immediate.ids.count==1,"loading/empty row cancels without query")
        var temporary:NagramiXChatListPreviewEmoji?=NagramiXChatListPreviewEmoji(schedule:scheduler.schedule)
        let destroyed=Resolver()
        temporary!.update(accountPeerId:account,messageId:first,text:preview([8]),resolve:destroyed.request,refresh:{preconditionFailure("destroyed row refreshed")})
        weak var weakState=temporary; temporary=nil
        destroyed.completions[0]([8:TelegramMediaFile(8)]); scheduler.drain()
        check(weakState==nil && destroyed.cancelled==1,"deinit cancels without retain cycle")

        // UTF-16 offsets for every native media prefix, rich and ordinary entities.
        for prefix in ["🖼 ","📹 ","🎤 ","📎 "] {
            for leading in ["","🙂 ","👨‍👩‍👧‍👦 ","е\u{301} "] {
                let original=leading+"🆕 Тест"
                let start=(leading as NSString).length, length=("🆕" as NSString).length
                var text=original
                var entities=[MessageTextEntity(range:start..<(start+length),type:.emoji(50)),MessageTextEntity(range:0..<(original as NSString).length,type:.bold)]
                var spoilers:[NSRange]?=[NSRange(location:start,length:length)]
                let emoji=ChatTextInputTextCustomEmojiAttribute(interactivelySelectedFromPackId:nil,fileId:50,file:nil)
                var ranges:[(NSRange,ChatTextInputTextCustomEmojiAttribute)]?=[(NSRange(location:start,length:length),emoji)]
                let rich=NSMutableAttributedString(string:original)
                rich.addAttribute(instantPagePreviewCustomEmoji,value:emoji,range:NSRange(location:start,length:length))
                var result:NSAttributedString?=rich
                nagramiXChatListPrependMediaPrefix(prefix,text:&text,entities:&entities,spoilers:&spoilers,customEmoji:&ranges,richText:&result)
                let offset=(prefix as NSString).length
                check(text==prefix+original && result?.string==text,"prefix retains rich caption")
                check(entities[0].range==((start+offset)..<(start+offset+length)),"UTF-16 emoji entity shifted")
                check(entities[1].range.lowerBound==offset,"other formatting remains aligned")
                check(spoilers?.first?.location==start+offset && ranges?.first?.0.location==start+offset,"spoiler and service ranges aligned")
                check(result?.attribute(instantPagePreviewCustomEmoji,at:start+offset,effectiveRange:nil) as? ChatTextInputTextCustomEmojiAttribute === emoji,"rich custom emoji metadata retained")
                check(rich.string==original,"rich original untouched")
                let hydrated=nagramiXPinnedPreviewApplyingEmojiFiles(result!,files:[50:TelegramMediaFile(50)])
                check(hydrated.attribute(ChatTextInputAttributes.customEmoji,at:start+offset,effectiveRange:nil) != nil,"caption prefix still resolves native attachment")
            }
            var plain="🙂 🆕"
            var entities=[MessageTextEntity(range:3..<5,type:.emoji(77))]
            var spoilers:[NSRange]?=nil
            var ranges:[(NSRange,ChatTextInputTextCustomEmojiAttribute)]?=nil
            var rich:NSAttributedString?=nil
            nagramiXChatListPrependMediaPrefix(prefix,text:&plain,entities:&entities,spoilers:&spoilers,customEmoji:&ranges,richText:&rich)
            check(plain==prefix+"🙂 🆕" && rich==nil,"ordinary caption stays on native entity path")
            check(entities[0].range.lowerBound==3+(prefix as NSString).length,"ordinary custom emoji position corrected")
            check(spoilers==nil && ranges==nil,"nil native ranges remain nil")
        }
        print("PASS: \(checks) chat-list emoji resolution/lifecycle/UTF-16 checks")
    }
}

@main struct SilentSendTests {
    static var checks=0
    static func check(_ value: @autoclosure ()->Bool,_ label: String) { checks += 1;precondition(value(),label) }
    static func ids(_ attributes: [MessageAttribute]) -> [ObjectIdentifier] { attributes.map { ObjectIdentifier($0) } }
    static func notification(_ attributes: [MessageAttribute]) -> [NotificationInfoMessageAttribute] { attributes.compactMap { $0 as? NotificationInfoMessageAttribute } }
    static func main() {
        let args=CommandLine.arguments
        if args.count>1 {
            if args[1]=="set" {
                NagramiXSendSettings.setSendSilently(args[2]=="true")
                // Linux cold-process harness exits immediately; flush only here.
                _ = UserDefaults.standard.synchronize()
            }
            check(NagramiXSendSettings.sendSilently == (args[2]=="true"),"separate cold process retains explicit ON/OFF; absent defaults ON")
            return
        }
        let key="nagramix.messages.sendSilently"
        UserDefaults.standard.removeObject(forKey:key)
        check(NagramiXSendSettings.sendSilently,"fresh/missing preference defaults enabled")
        check(UserDefaults.standard.object(forKey:key)==nil,"reading default does not overwrite storage")
        let promise=SettingsPromise()
        productionSettingsToggle(false,settingsPromise:promise)
        check(!NagramiXSendSettings.sendSilently && promise.count==1,"native settings callback persists OFF and refreshes switch immediately")
        productionSettingsToggle(true,settingsPromise:promise)
        check(NagramiXSendSettings.sendSilently && promise.count==2,"native callback persists ON")

        let entity=Sentinel(1),ttl=Sentinel(2),schedule=Sentinel(3),fee=Sentinel(4),reply=Sentinel(5)
        let unrelated: [MessageAttribute]=[entity,ttl,schedule,fee,reply]
        let originals: [[MessageAttribute]]=[[],unrelated,[NotificationInfoMessageAttribute(flags:.muted)],unrelated+[NotificationInfoMessageAttribute(flags:.personal)],unrelated+[NotificationInfoMessageAttribute(flags:.automaticMessage),NotificationInfoMessageAttribute(flags:.personal)],unrelated+[NotificationInfoMessageAttribute(flags:[.personal,.muted,.automaticMessage])]]
        for enabled in [false,true] {
            for attributes in originals {
                let output=nagramiXSilentSendAttributes(attributes,enabled:enabled)
                if enabled {
                    let flags=notification(output)
                    check(flags.count==1 && flags[0].flags.contains(.muted),"silent default produces one native muted attribute")
                    var expected: NotificationInfoMessageAttributeFlags = .muted
                    for a in notification(attributes) { expected.formUnion(a.flags) }
                    check(flags[0].flags==expected,"personal/automatic notification flags preserved")
                    check(ids(output.filter { !($0 is NotificationInfoMessageAttribute) })==ids(attributes.filter { !($0 is NotificationInfoMessageAttribute) }),"entities/one-shot TTL/schedule/payment/reply attributes preserved in order")
                    check(productionRPCFlags(output)&(1<<5) != 0,"native standalone request consumes muted as RPC silent bit")
                    let again=nagramiXSilentSendAttributes(output,enabled:true)
                    check(notification(again).count==1 && notification(again)[0].flags==expected,"repeat policy does not accumulate notification attributes")
                    let encoder=PostboxEncoder();flags[0].encode(encoder)
                    check(NotificationInfoMessageAttribute(decoder:PostboxDecoder(encoder.raw)).flags==expected,"native persisted flags survive queue serialization/retry")
                } else {
                    check(ids(output)==ids(attributes),"OFF returns exact original attributes, including explicit manual silence")
                }
            }
        }
        for enabled in [false,true] {
            NagramiXSendSettings.setSendSilently(enabled)
            for kind in 0..<8 {
                // Distinct text/photo/video/file/voice/round/sticker/album payloads.
                let input=EnqueueMessage.message(text:"caption-\(kind)",attributes:unrelated,inlineStickers:[:],mediaReference:kind==0 ? nil : AnyMediaReference(id:kind),threadId:99,replyToMessageId:EngineMessageReplySubject(id:99),replyToStoryId:77,localGroupingKey:123,correlationId:456,bubbleUpEmojiOrStickersets:[1,2])
                let batch=productionBatch([(false,input),(true,input)])
                check(batch.count==2 && !batch[0].0 && batch[1].0,"media-transform metadata and album batch cardinality unchanged")
                for (_,message) in batch {
                    guard case let .message(text,attrs,inline,media,thread,reply,story,group,correlation,bubble)=message else { fatalError() }
                    check(text=="caption-\(kind)" && inline.isEmpty && media==(kind==0 ? nil : AnyMediaReference(id:kind)),"text/caption/media/inline resources preserved")
                    check(thread==99 && reply?.id==99 && story==77 && group==123 && correlation==456 && bubble==[1,2],"destination topic/reply/story/album grouping/correlation preserved")
                    check((productionRPCFlags(attrs)&(1<<5) != 0)==enabled,"native enqueue maps current setting to outgoing silent flag")
                    check(ids(attrs.filter { $0 is Sentinel })==ids(unrelated),"native send leaves TTL/payment/schedule/entity attributes intact")
                }
                check(ids(input.attributes)==ids(unrelated),"original copied media batch is not mutated")
            }
            let forward=EnqueueMessage.forward(source:17,threadId:88,grouping:.auto,attributes:unrelated,correlationId:42)
            guard case let .forward(source,thread,grouping,attrs,correlation)=productionBatch([(false,forward)])[0].1 else { fatalError() }
            check(source==17 && thread==88 && grouping == .auto && correlation==42,"native forwarding remains forwarding with source/topic unchanged")
            check((productionRPCFlags(attrs)&(1<<5) != 0)==enabled,"forward receives native silent bit")
            let share=productionShare([ShareMessage(isSilent:false),ShareMessage(isSilent:true)])
            check((productionRPCFlags(share[0])&(1<<5) != 0)==enabled,"standalone share batch honors automatic default")
            check(productionRPCFlags(share[1])&(1<<5) != 0,"manual share silence works with either default")
            check((productionRPCFlags(productionDirect(unrelated))&(1<<5) != 0)==enabled,"direct standalone text/media path honors current setting")
        }
        NagramiXSendSettings.setSendSilently(true)
        let queued=productionDirect(unrelated)
        NagramiXSendSettings.setSendSilently(false)
        check(productionRPCFlags(queued)&(1<<5) != 0,"changing preference does not rewrite already queued metadata")
        let explicit=unrelated+[NotificationInfoMessageAttribute(flags:.muted)]
        check(productionRPCFlags(productionDirect(explicit))&(1<<5) != 0,"OFF preserves explicit one-message silent command")
        UserDefaults.standard.removeObject(forKey:key)
        _ = UserDefaults.standard.synchronize()
        print("PASS \(checks) checks; real persisted defaults, native enqueue/share branches, flags and metadata; no UIKit/network delivery")
    }
}

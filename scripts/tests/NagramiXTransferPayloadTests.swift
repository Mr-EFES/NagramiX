import Foundation

@main struct TransferPayloadTests {
    // PRODUCTION_POLL_FIXTURE
    static func main() throws {
        var checks=0
        func check(_ ok:@autoclosure()->Bool,_ label:String){if !ok(){fatalError("Transfer payload regression: "+label)};checks+=1}
        let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        defer{try? FileManager.default.removeItem(at:root)}
        let box=MediaBox(),account=Account(box)
        let bytes=Data([1,2,3,4])
        for name in ["photo","video","voice","document","round"] {
            let path=root.appendingPathComponent(name);try bytes.write(to:path)
            box.paths[name]=path.path;box.complete.insert(name)
        }
        var originals:[Message]=[]
        func add(_ media:[Media],_ text:String,_ group:Int64?=nil,_ attributes:[MessageAttribute]=[]) {
            var message=Message();message.id.value=originals.count+1;message.text=text;message.media=media;message.groupingKey=group;message.attributes=attributes;originals.append(message)
        }
        let image=TelegramMediaImage(representations:[.init(dimensions:.init(width:50,height:50),resource:CloudResource("photo"))])
        add([],"Text 😀 https://example.org/post",nil,[TextEntitiesMessageAttribute(entities:[Entity(value:"bold")])])
        add([image],"Album caption",99)
        add([TelegramMediaFile(resource:CloudResource("video"),size:4,attributes:["video"])],"",99)
        add([TelegramMediaFile(resource:CloudResource("voice"),size:4,attributes:["voice"])],"")
        add([TelegramMediaFile(resource:CloudResource("document"),size:4)],"File caption")
        add([TelegramMediaContact()],"Contact")
        add([TelegramMediaMap()],"Location")
        add([poll()],"")
        let page=InstantPage(blocks:["paragraph:post","image:1","document:2"],rawMedia:[MediaId(namespace:0,id:1):image,MediaId(namespace:0,id:2):TelegramMediaFile(resource:CloudResource("document"),size:4)],isComplete:true,rtl:false,url:"",views:40)
        add([],"",nil,[RichTextMessageAttribute(instantPage:page,fullInstantPage:nil)])
        add([TelegramMediaFile(resource:CloudResource("video"),size:4,attributes:["video"])],"Видео с текстом 😀 https://example.org",nil,[TextEntitiesMessageAttribute(entities:[Entity(value:"bold")])])
        for sourceKind in ["open","protected","closed"] {
            let restricted=sourceKind != "open"
            let messages=originals.map{m -> Message in
                var m=m;m.protected=sourceKind == "protected"
                if sourceKind == "closed" {let channel=TelegramChannel();channel.participationStatus = .left;m.peers[m.id.peerId]=channel}
                return m
            }
            NagramiXPrivacySettings.current.bypassScreenshots=false
            check(nagramiXCanCopyMessagesAsNew(messages)==(!restricted),"Free Content OFF keeps normal source policy")
            NagramiXPrivacySettings.current.bypassScreenshots=true
            for recipients in [1,2,3] {
                let batch=nagramiXPrepareRecipientCopies(messages,account:account,recipientCount:recipients,forceLocalMedia:true,accountPeerId:account.peerId)!
                check(batch.recipientMessages.count==recipients,"all destinations prepared")
                for list in batch.recipientMessages {
                    check(list.count==messages.count,"every selected message has a complete copy")
                    check(list.map{$0.text}==messages.map{$0.text},"all captions/text and ordering survive")
                    check(list.allSatisfy{$0.threadId==nil && $0.replyToMessageId==nil},"source topic and reply cannot leak into recipient copies")
                    check(list[1].localGroupingKey==list[2].localGroupingKey && list[1].localGroupingKey != nil,"media album remains grouped")
                    let cloned=list[7].mediaReference!.media as! TelegramMediaPoll
                    check(cloned.results.totalVoters==nil && cloned.options.map{$0.text}==(messages[7].media[0] as! TelegramMediaPoll).options.map{$0.text},"poll is a fresh interactive copy with original options")
                    let rich=(list[8].attributes.first{$0 is RichTextMessageAttribute} as! RichTextMessageAttribute).instantPage
                    check(rich.blocks==page.blocks && rich.rawMedia.count==2,"structured post preserves all embedded media")
                    check(list[9].text==messages[9].text && list[9].attributes.contains{$0 is TextEntitiesMessageAttribute},"standalone video keeps caption and entities")
                    for index in [1,2,3,4,9] {
                        let medium=list[index].mediaReference!.media
                        let resource:LocalFileReferenceMediaResource
                        if let file=medium as? TelegramMediaFile {resource=file.resource as! LocalFileReferenceMediaResource}
                        else {resource=(medium as! TelegramMediaImage).representations[0].resource as! LocalFileReferenceMediaResource}
                        let copiedBytes=try Data(contentsOf:URL(fileURLWithPath:resource.localFilePath))
                        check(copiedBytes==bytes,"all copied attachment bytes are complete")
                    }
                }
                if recipients>1 {check(batch.recipientMessages[0][1].localGroupingKey != batch.recipientMessages[1][1].localGroupingKey,"recipient album identities are isolated")}
            }
        }
        NagramiXPrivacySettings.current.bypassScreenshots=true
        var quiz=Message();quiz.text="";quiz.media=[poll(kind:.quiz(multipleAnswers:false))]
        check(!nagramiXCanCopyMessagesAsNew([quiz]),"unknown quiz answer is never invented")
        quiz.media=[poll(kind:.quiz(multipleAnswers:false),correct:[Data([1])])]
        check(nagramiXCanCopyMessagesAsNew([quiz]),"quiz with known correct answer remains copyable")
        print("Transfer payload checks: \(checks)")
    }
}

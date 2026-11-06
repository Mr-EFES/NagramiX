import Foundation

@main struct EditorCopyTests {
    static func main() {
        var checks=0
        func check(_ ok: @autoclosure ()->Bool,_ message:String) { if !ok() { fatalError("Editor copy regression: "+message) }; checks += 1 }
        let preview=TelegramMediaWebpage()
        let page=InstantPage(blocks:["paragraph:body","audio:1","image:2"],rawMedia:[:],isComplete:true,rtl:false,url:"",views:nil)
        for hasPreview in [false,true] {
            for rich in [false,true] {
                for hide in [false,true] {
                    var post=Message()
                    post.text="Body https://example.org/post"
                    post.media=hasPreview ? [preview] : []
                    let size=WebpagePreviewMessageAttribute(leadingPreview:true,forceLargeMedia:false)
                    post.attributes=[TextEntitiesMessageAttribute(entities:[Entity(value:"original-url-entity")]),size,InvertMediaMessageAttribute()]
                    if rich { post.attributes.append(RichTextMessageAttribute(instantPage:page,fullInstantPage:nil)) }
                    let copies=nagramiXCopyMessagesAsNew([post],hideCaptions:hide)!
                    check(copies.count==1 && copies[0].text==post.text,"text links and text-only posts survive caption options")
                    let attributes=copies[0].attributes
                    let disabled=attributes.compactMap{$0 as? OutgoingContentInfoMessageAttribute}.contains{$0.flags.contains(.disableLinkPreviews)}
                    check(disabled == !hasPreview,"new preview must not be generated for bare source links")
                    check((copies[0].mediaReference?.media is TelegramMediaWebpage)==hasPreview,"original preview retained only when present")
                    check(attributes.contains{$0 is InvertMediaMessageAttribute}==hasPreview,"preview position comes from the original")
                    let copiedSize=attributes.compactMap{$0 as? WebpagePreviewMessageAttribute}.first
                    check((copiedSize?.forceLargeMedia==false)==hasPreview,"original compact preview size retained")
                    check(attributes.contains{$0 is TextEntitiesMessageAttribute},"original link entities retained")
                    check(attributes.contains{$0 is RichTextMessageAttribute}==rich,"rich content and block order retained")
                }
            }
        }
        var album: [Message]=[]
        for i in 0..<3 {
            var message=Message();message.text="Caption https://example.org/\(i)"
            message.id=MessageId(peerId:PeerId(),value:i+1,namespace:0)
            message.groupingKey=55
            message.media=[TelegramMediaFile(resource:CloudResource("file-\(i)"))]
            album.append(message)
        }
        let copied=nagramiXCopyMessagesAsNew(album)!
        check(copied.map{$0.text}==album.map{$0.text},"copy order and all captions retained")
        check(copied.allSatisfy{$0.mediaReference != nil},"all attachments retained")
        check(Set(copied.compactMap{$0.localGroupingKey}).count==1,"album grouping retained")
        check(copied.allSatisfy{$0.attributes.compactMap{$0 as? OutgoingContentInfoMessageAttribute}.contains{$0.flags.contains(.disableLinkPreviews)}},"album links cannot generate new previews")
        print("Editor copy checks: \(checks)")
    }
}

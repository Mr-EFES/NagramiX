@main struct NamedLinkCopyTests {
 static func main(){
  var checks=0;var serial=100
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  func source(_ media:[Media])->Message{serial+=1;var m=Message();m.id.value=serial;m.media=media;m.author=TestUser(id:PeerId(value:99));return m}
  LocalCopyDefaultsBoundary.shared.enabled=true
  let box=MediaBox();let account=Account(box)
  let media=[TelegramMediaFile(resource:CloudResource("video"),attributes:["video"]),TelegramMediaFile(resource:CloudResource("audio"),attributes:["music"])]
  for file in media {
   for hasPreview in [false,true] {
    for hasAttachment in [false,true] {
     var m=source((hasAttachment ? [file]:[])+(hasPreview ? [TelegramMediaWebpage()]:[]))
     m.text="Пост 😀 Радио Таврия — подписаться"
     let entities=[Entity(value:"bold-title"),Entity(value:"Радио Таврия — подписаться=https://t.me/example")]
     m.attributes=[TextEntitiesMessageAttribute(entities:entities),WebpagePreviewMessageAttribute(leadingPreview:true,forceLargeMedia:true),InvertMediaMessageAttribute(),MediaSpoilerMessageAttribute()]
     if hasPreview {check(!nagramiXCanForwardWithoutAuthor(m),"source webpage cannot use native fast forward")}
     else {check(nagramiXCanForwardWithoutAuthor(m),"ordinary no-preview messages retain fast route")}
     let copies=nagramiXCopyMessagesAsNew([m],account:account)!
     check(copies.count==1,"whole post stays one output")
     guard case let .message(text,attrs,_,reference,_,_,_,_,_,_)=copies[0] else{check(false,"copy uses authored send");return}
     check(text==m.text,"copied post preserves full text")
     check(attrs.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities.map{$0.value}==entities.map{$0.value},"copied post preserves hyperlink destination and formatting entities")
     check(attrs.compactMap{$0 as? OutgoingContentInfoMessageAttribute}.first!.flags.contains(.disableLinkPreviews),"copy always disables automatic preview")
     check(!attrs.contains{$0 is WebpagePreviewMessageAttribute},"copy drops preview-only metadata")
     check(reference==nil || !(reference!.media is TelegramMediaWebpage),"copy never carries old card as its attachment")
     check((reference?.media is TelegramMediaFile)==hasAttachment,"actual audio/video attachment survives")
     if hasPreview {
      let batch=nagramiXPrepareRecipientCopies([m],account:account,recipientCount:3)!
      for recipient in batch.recipientMessages {
       guard case let .message(t,a,_,r,_,_,_,_,_,_)=recipient[0] else{check(false,"broadcast strips preview through copied payload");return}
       check(t==m.text && !(r?.media is TelegramMediaWebpage),"each broadcast destination gets full text without card")
       check(a.compactMap{$0 as? OutgoingContentInfoMessageAttribute}.first!.flags.contains(.disableLinkPreviews),"each destination retains server no-preview flag")
      }
      batch.commit()
     }
    }
   }
  }
  var first=source([TelegramMediaWebpage()]);first.groupingKey=42
  var second=source([media[0]]);second.groupingKey=42
  check(nagramiXMessagesRequiringCopy([first,second]).count==2,"selected album remains on one preview-free transport")
  print("PASS \(checks) real copy/forward/broadcast payload checks; Postbox/models are explicit boundaries")
 }
}

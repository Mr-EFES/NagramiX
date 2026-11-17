@main struct WireCaptionSendChecks {
 static func main() throws {
  let text="🎙️ Совместный проект\n\nТекст 🟨\nРадио — подписаться"
  let ns=text as NSString, title=ns.range(of:"Совместный проект"),link=ns.range(of:"Радио — подписаться")
  let originalEntities=[MessageTextEntity(range:title.location..<NSMaxRange(title),type:.Bold),MessageTextEntity(range:link.location..<NSMaxRange(link),type:.TextUrl(url:"https://example.org/radio")),MessageTextEntity(range:link.location..<NSMaxRange(link),type:.Underline)]
  storeChatMessageTextInPasteboard(text,entities:originalEntities)
  let document=try DocumentCodec.decode(UIPasteboard.general.items[0][RichTextEditorClipboard.fragmentUTI] as! Data)
  let controller=ChatControllerImpl(ChatTextInputState())
  func sent(_ values:[EnqueueMessage])->(String,[MessageTextEntity],TelegramMediaFile?) {
   check(values.count==1,"one file remains one message")
   if case let .message(s,a,_,media,thread,reply,_,_,_,_)=values[0] {
    check(thread==17 && reply?.id==47,"thread and reply preserved")
    check(!a.contains{$0 is RichTextMessageAttribute},"classic native bubble retained")
    return (s,a.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities ?? [],media?.media as? TelegramMediaFile)
   };fatalError()
  }
  func canonical(_ e:[MessageTextEntity])->[String] {
   let encoder=JSONEncoder();encoder.outputFormatting=[.sortedKeys]
   return e.map{String(data:try! encoder.encode($0),encoding:.utf8)!}.sorted()
  }
  let paddedEntities=originalEntities.map{MessageTextEntity(range:($0.range.lowerBound+1)..<($0.range.upperBound+1),type:$0.type)}
  for kind in ["music","document","video","voice","animated","sticker"] {
   let f=file(10,kind);f.isAnimated=kind=="animated";f.isSticker=kind=="sticker"
   let padding=kind=="music" || kind=="document"
   let attachment=nagramiXLeadingAttachmentDocument([(mediaID:"file",naturalSize:CGSize(width:1,height:1),kind:kind=="music" || kind=="voice" ? .audio:kind=="video" ? .video:.document,caption:[])])
   let expanded=document.replacingRange(globalFrom:0,globalTo:0,with:attachment).document
   let content=chatInputContent(fromDocument:expanded,resolveEmoji:{_ in nil},resolveMedia:{_ in .file(f)})
   let caption=attributedString(from:content)
   FixtureCaption.context.userLimits.maxCaptionLength=4096
   let normal=sent(OrdinaryCaptionHost().send([f],caption))
   let rich=sent(buildRichTextMessages(controller,expanded,["file":.file(f)],[:],false)!)
   check(normal.0==(padding ? "\n"+text:text) && rich.0==normal.0,"both editors serialize the same approved spacing")
   check(normal.2 === f && rich.2 === f && f.payload==Data([1,2,3]),"file identity and bytes preserved")
   check(canonical(normal.1)==canonical(padding ? paddedEntities:originalEntities) && canonical(rich.1)==canonical(normal.1),"UTF16 ranges and named links remain exact")
  }
  let f=file(12,"music")
  let round=file(13,"round")
  check(chatComposerSpacedFileCaption(NSAttributedString(string:text),file:round,maxCaptionLength:4096).string==text,"round video does not receive file caption spacing")
  var caption=NSAttributedString(string:"**Тема**\n\nТекст")
  let nativeMarkdown=chatComposerTextMessages(effectiveInputText:caption).pieces[0].entities
  let shiftedMarkdown=nativeMarkdown.map{MessageTextEntity(range:($0.range.lowerBound+1)..<($0.range.upperBound+1),type:$0.type)}
  for _ in 0..<4 {
   let value=sent(OrdinaryCaptionHost().send([f],caption))
   check(value.0=="\nТема\n\nТекст","native Markdown and repeated normalization keep one blank line")
   check(canonical(value.1)==canonical(shiftedMarkdown),"Markdown styles match native conversion with shifted UTF16 positions")
   caption=chatInputStateStringWithAppliedEntities(value.0,entities:value.1)
  }
  let once=chatComposerSpacedFileCaption(NSAttributedString(string:"caption"),file:f,maxCaptionLength:1024)
  check(chatComposerSpacedFileCaption(once,file:f,maxCaptionLength:1024).string=="\ncaption","shared caption normalizer is idempotent")
  for limit in [1024,4096] {
   for length in [0,1,limit-1,limit] {
    let original=String(repeating:"я",count:length)
    FixtureCaption.context.userLimits.maxCaptionLength=limit
    let value=sent(OrdinaryCaptionHost().send([f],NSAttributedString(string:original)))
    check(value.0==(length>0 && length<limit ? "\n"+original:original),"limit boundary keeps the complete caption")
    check((value.0 as NSString).length<=limit,"serialized line respects actual account limit")
   }
  }
  FixtureCaption.context.userLimits.maxCaptionLength=1024
  for count in [511,512] {
   let value=String(repeating:"😀",count:count)
   let output=sent(OrdinaryCaptionHost().send([f],NSAttributedString(string:value)))
   check(output.0==(count==511 ? "\n"+value:value),"caption limit uses UTF16 rather than grapheme count")
  }
  FixtureCaption.context.userLimits.maxCaptionLength=4096
  let files=[file(1,"music"),file(2,"music"),file(3,"music")]
  let messages=OrdinaryCaptionHost().send(files,NSAttributedString(string:"caption"))
  check(messages.count==3,"all grouped files retained")
  var groups:[Int64?]=[]
  for (index,message) in messages.enumerated() {
   if case let .message(t,_,_,ref,_,_,_,group,_,_)=message {
    check(t==(index==2 ? "\ncaption":""),"only final grouped file carries the caption")
    check(ref?.media === files[index],"group preserves file order")
    groups.append(group)
   }
  }
  check(groups[0] != nil && groups.allSatisfy{$0==groups[0]},"album grouping preserved")
  print("File caption wire send: \(checks) actual native/expanded/Markdown/UTF16/limit checks passed; account/media/queue IO hosted")
 }
}

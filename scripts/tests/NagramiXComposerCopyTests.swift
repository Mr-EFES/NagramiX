private var checks=0
private func check(_ value:@autoclosure()->Bool,_ why:String) {
    if !value(){FileHandle.standardError.write(Data(("Composer copy regression: "+why+"\n").utf8));exit(96)}
    checks+=1
}
private func body(_ text:String)->ChatInputBlock {.paragraph(ChatInputParagraph(runs:[ChatInputRun(text:text)]))}
private func file(_ id:Int64,_ kind:String="document")->TelegramMediaFile {
    let f=TelegramMediaFile(id);f.isMusic=kind=="music";f.isVoice=kind=="voice";f.isVideo=kind=="video" || kind=="round";f.isInstantVideo=kind=="round";return f
}
private func medium(_ f:TelegramMediaFile)->ChatInputBlock {.media(ChatInputMedia(media:f,kind:.document,naturalSize:.init(width:1,height:1)))}
@main struct ComposerCopyChecks {
 static func main() throws {
    let text="🎙️ Совместный проект\n\nТекст 🟨\nРадио Таврия — подписаться"
    let source=text as NSString, linkRange=source.range(of:"Радио Таврия — подписаться"),titleRange=source.range(of:"Совместный проект")
    let entities=[MessageTextEntity(range:titleRange.location..<NSMaxRange(titleRange),type:.Bold),MessageTextEntity(range:linkRange.location..<NSMaxRange(linkRange),type:.TextUrl(url:"https://t.me/radio_tavria")),MessageTextEntity(range:linkRange.location..<NSMaxRange(linkRange),type:.Underline)]
    for _ in 0..<3 {
        let before=UIPasteboard.general.writes
        storeChatMessageTextInPasteboard(text,entities:entities)
        check(UIPasteboard.general.writes==before+1,"one atomic clipboard write")
        let item=UIPasteboard.general.items[0]
        check(item[RichTextEditorClipboard.fragmentUTI] is Data,"native private fragment is present")
        check(item["public.utf8-plain-text"] as? String==text,"full source text with UTF16 preserved")
        let legacy=try JSONDecoder().decode(AppSpecificPasteboardString.self,from:item["private.telegramtext"] as! Data)
        check(legacy.entities==entities && legacy.text==text,"exact legacy entities retained")
        let fragment=try DocumentCodec.decode(item[RichTextEditorClipboard.fragmentUTI] as! Data)
        let runs=fragment.blocks.flatMap {block->[TextRun] in if case let .paragraph(p)=block{return p.runs};return []}
        check(runs.contains{$0.attributes.link=="https://t.me/radio_tavria" && $0.text=="Радио Таврия — подписаться" && $0.attributes.underline},"first native paste preserves named link")
        check(runs.contains{$0.attributes.bold && $0.text=="Совместный проект"},"native paste preserves bold")
        let rtf=item["public.rtf"] as! Data
        let parsed=RTFImport.document(fromRTF:rtf)!
        let rtfRuns=parsed.blocks.flatMap {block->[TextRun] in if case let .paragraph(p)=block{return p.runs};return []}
        check(rtfRuns.contains{$0.attributes.link=="https://t.me/radio_tavria"},"real RTF retains clickable URL")
        check(rtfRuns.contains{$0.attributes.bold && $0.text.contains("Совместный проект")},"real RTF retains bold")
        let decoded=chatInputStateStringFromAppSpecificString(data:item["private.telegramtext"] as! Data)!
        check((decoded.attribute(ChatTextInputAttributes.textUrl,at:linkRange.location,effectiveRange:nil) as? ChatTextInputTextUrlAttribute)?.url=="https://t.me/radio_tavria","legacy paste preserves named link")
    }
    for type in [MessageTextEntityType.Bold,.Italic,.Underline,.Strikethrough,.Spoiler,.Code,.Pre(language:"swift"),.BlockQuote(isCollapsed:false),.CustomEmoji(stickerPack:nil,fileId:52),.TextMention(peerId:PeerId(119)),.FormattedDate(format:nil,date:123456)] {
        storeChatMessageTextInPasteboard("Ж🙂x",entities:[MessageTextEntity(range:0..<4,type:type)])
        let item=UIPasteboard.general.items[0],fragment=try DocumentCodec.decode(item[RichTextEditorClipboard.fragmentUTI] as! Data)
        check(!fragment.blocks.isEmpty,"format type encoded in native fragment")
        let flags:CharacterAttributes? = {if case let .paragraph(p)=fragment.blocks.first {return p.runs.first?.attributes};return nil}()
        switch type {
        case .Bold:check(flags?.bold==true,"native bold retained")
        case .Italic:check(flags?.italic==true,"native italic retained")
        case .Underline:check(flags?.underline==true,"native underline retained")
        case .Strikethrough:check(flags?.strikethrough==true,"native strike retained")
        case .Spoiler:check(flags?.spoiler==true,"native spoiler retained")
        case .Code:check(flags?.inlineCode==true,"native inline code retained")
        case .Pre:if case let .code(c)=fragment.blocks.first {check(c.language=="swift","native code language retained")} else {check(false,"native code language retained")}
        case .BlockQuote:if case .blockQuote=fragment.blocks.first {check(true,"native quote retained")} else {check(false,"native quote retained")}
        case .CustomEmoji:check(flags?.emoji?.id=="52","native custom emoji retained")
        case .TextMention:check(flags?.link=="tg://user?id=119","native mention retained")
        case .FormattedDate:check(flags?.link=="tg://timestamp?t=123456","native date retained")
        default:check(false,"unexpected fixture type")
        }
        check(try! JSONDecoder().decode(AppSpecificPasteboardString.self,from:item["private.telegramtext"] as! Data).entities[0].type==type,"format type preserved in legacy payload")
    }
    let attributed=chatInputStateStringWithAppliedEntities(text,entities:entities)
    let initial=ChatTextInputState(inputText:attributed,selectionRange:2..<8)
    for kind in ["document","music","voice","video","round"] {
        let f=file(7,kind),draft=nagramiXComposerFileDraft(initial,files:[f],caption:nil,initialState:nil)!
        check(draft.content.blocks.first==medium(f) || draft.content.allMedia.count==1,"file is present")
        if case .media=draft.content.blocks.first! {} else {check(false,"file begins the draft before upload")}
        check(Array(draft.content.blocks.dropFirst())==initial.content.blocks,"all source text structure stays after file")
        check(draft.selectionRange==initial.selectionRange,"text caret offsets remain unchanged")
        check(draft.selection.start.path[0].blockIndex==initial.selection.start.path[0].blockIndex+1,"text caret path shifts with leading media")
        let parsed=nagramiXComposerCaptionFiles(draft.content,maxCaptionLength:4096,sendWithoutFormatting:false)
        check((parsed != nil)==(kind != "round"),"leading file uses native caption unless unrepresentable round")
        check(draft.inputText.string==text,"visible source text unchanged after attach")
        let link=(draft.inputText.attribute(ChatTextInputAttributes.textUrl,at:linkRange.location,effectiveRange:nil) as? ChatTextInputTextUrlAttribute)?.url
        check(link=="https://t.me/radio_tavria","attachment does not flatten URL")
    }
    let f=file(1)
    let once=nagramiXComposerFileDraft(initial,files:[f],caption:nil,initialState:nil)!
    let twice=nagramiXComposerFileDraft(once,files:[file(2)],caption:nil,initialState:nil)!
    let ids=twice.content.allMedia.map {media->Int64 in if case let .file(file)=media {return file.fileId.id};return 0}
    check(ids==[1,2] && twice.selectionRange==initial.selectionRange,"repeated picks preserve order and text caret")
    let empty=nagramiXComposerFileDraft(ChatTextInputState(),files:[f],caption:nil,initialState:nil)!
    check(empty.selection.start.path.first?.blockIndex==0 && empty.content.allMedia.count==1,"empty draft has a valid leading media stop")
    for blocks in [[medium(f),body("caption")],[body("caption"),medium(f)],[medium(f)]] {
        check(nagramiXComposerCaptionFiles(ChatInputContent(blocks:blocks),maxCaptionLength:1024,sendWithoutFormatting:false)?.count==1,"both edge layouts take native caption route")
    }
    check(nagramiXComposerCaptionFiles(ChatInputContent(blocks:[body("before"),medium(f),body("after")]),maxCaptionLength:4096,sendWithoutFormatting:false)==nil,"intentional inline order stays rich")
    check(nagramiXComposerCaptionFiles(ChatInputContent(blocks:[medium(f),body(String(repeating:"x",count:1025))]),maxCaptionLength:1024,sendWithoutFormatting:false)==nil,"long text stays rich without truncation")
    let heading=ChatInputBlock.paragraph(ChatInputParagraph(style:.heading1,runs:[ChatInputRun(text:"Heading")]))
    check(nagramiXComposerCaptionFiles(ChatInputContent(blocks:[medium(f),heading]),maxCaptionLength:4096,sendWithoutFormatting:false)==nil,"structural heading stays rich")
    check(nagramiXComposerFileDraft(initial,files:[],caption:nil,initialState:nil)==nil,"cancel does not alter draft")
    let changed=ChatTextInputState(inputText:NSAttributedString(string:"newer draft"))
    check(nagramiXComposerFileDraft(changed,files:[f],caption:NSAttributedString(string:"obsolete picker text"),initialState:initial)==nil,"stale picker never overwrites draft")
    let messages=nagramiXComposerFileMessages(files:[f],caption:attributed,inlineStickers:[:],threadId:17,replyTo:.init(id:22))
    check(messages.count==1,"one file one post")
    if case let .message(caption,attrs,_,media,thread,reply,_,_,_,_)=messages[0] {
        check(caption==text && media?.media === f && thread==17 && reply?.id==22,"native post retains file text reply and thread")
        check(attrs.contains{($0 as? TextEntitiesMessageAttribute)?.entities.contains{if case let .TextUrl(url)=$0.type {return url=="https://t.me/radio_tavria"};return false}==true},"wire caption retains named URL")
        check(attrs.contains{($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.disableLinkPreviews)==true},"native file post disables redundant preview")
    }
    let existing=ChatPresentationInterfaceState.UrlPreview(url:"old-url",webPage:"old-card",positionBelowText:true,largeMedia:nil)
    let attached=PreviewState(interfaceState:InterfaceState(composeInputState:once),urlPreview:existing)
    let controller=PreviewController(),disposable=PreviewDisposable();controller.urlPreviewQueryState=(1,disposable)
    let (withoutCard,canPreview)=preparePreview(attached,controller:controller)
    check(disposable.disposed && controller.urlPreviewQueryState==nil && withoutCard.urlPreview==nil && !canPreview,"attachment clears existing preview and query")
    check(withoutCard.interfaceState.composeInputState==once,"preview removal never changes content")
    check(acceptLatePreview(attached).urlPreview==nil,"late preview cannot return after attachment")
    let plain=PreviewState(interfaceState:InterfaceState(composeInputState:initial),urlPreview:existing)
    check(preparePreview(plain,controller:PreviewController()).1 && acceptLatePreview(plain).urlPreview?.webPage=="late-card","text-only native preview remains unchanged")
    let seed=pasteFragmentDocument(fromChatInputContent:initial.content)
    let attachment=nagramiXLeadingAttachmentDocument([(mediaID:"audio-1",naturalSize:CGSize(width:1,height:1),kind:.audio,caption:[])])
    let expanded=seed.replacingRange(globalFrom:0,globalTo:0,with:attachment).document
    if case let .media(m)=expanded.blocks.first {check(m.items[0].mediaID=="audio-1" && m.items[0].kind == .audio,"expanded attachment goes above body")} else {check(false,"expanded attachment goes above body")}
    check(expanded.blocks.dropFirst().map {b in if case let .paragraph(p)=b{return p.runs.map(\.text).joined()};return ""}.joined(separator:"\n")==text,"expanded insert preserves all copied text")
    let batch=nagramiXLeadingAttachmentDocument([(mediaID:"a",naturalSize:CGSize(width:20,height:10),kind:.image,caption:[]),(mediaID:"b",naturalSize:CGSize(width:30,height:10),kind:.video,caption:[])])
    if case let .media(m)=batch.blocks.first {check(m.items.map(\.mediaID)==["a","b"],"expanded batch preserves pick order")} else {check(false,"expanded batch preserves pick order")}
    check(nagramiXLeadingAttachmentDocument([]).blocks.isEmpty,"expanded cancellation creates no fragment")
    print("Composer copy/draft production checks: \(checks)")
 }
}

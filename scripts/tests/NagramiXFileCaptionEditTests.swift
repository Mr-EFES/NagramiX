@main struct FileCaptionEditChecks {
 static func main(){
  let caption=NSMutableAttributedString(string:"🎙️ Совместный проект\nТекст\nПодписаться")
  let link=(caption.string as NSString).range(of:"Подписаться")
  caption.addAttribute(ChatTextInputAttributes.textUrl,value:ChatTextInputTextUrlAttribute(url:"https://example.org/radio"),range:link)
  caption.addAttribute(ChatTextInputAttributes.bold,value:true,range:(caption.string as NSString).range(of:"Совместный проект"))
  for kind in ["music","document","video"] {
   let f=file(71,kind),draft=nagramiXComposerFileDraft(ChatTextInputState(inputText:caption),files:[f],caption:nil,initialState:nil)!
   var mappedMedia:[String:EngineMedia]=[:]
   let mapped=document(fromChatInputContent:draft.content,registerEmoji:{id,_ in EmojiRef(id:String(id),instanceID:"fixture-emoji",altText:"")},registerMedia:{media in mappedMedia["file"]=media;return "file"})
   let expanded=chatInputContent(fromDocument:mapped,resolveEmoji:{_ in nil},resolveMedia:{mappedMedia[$0]})
   for content in [draft.content,expanded] {
    let state=ChatTextInputState(content:content,selectionRange:content.length..<content.length)
    let plan=editPlan(state,hasWebpage:true)
    check(plan.rich==nil,"both editors keep native file caption on edit")
    let partial=RichTextMessageAttribute(instantPage:FixtureEditPage(isComplete:false),fullInstantPage:nil)
    check(editPlan(state,originalRich:partial).rich != nil,"partial original rich page cannot become a truncated native edit")
    let full=RichTextMessageAttribute(instantPage:FixtureEditPage(),fullInstantPage:FixtureEditPage())
    check(editPlan(state,originalRich:full).rich != nil,"original full-page variant keeps its rich edit path")
    check(plan.updating,"edit transfers the file instead of dropping rich-only media")
    if case let .update(ref)=plan.media{check(ref.media === f,"edited native media reference is preserved")}else{check(false,"edit attaches the complete file")}
    check(plan.disablePreview && plan.webpage==nil && plan.preview==nil,"file edit does not replace file with link preview")
    let text=state.inputText
    check(text.string==caption.string,"edit keeps complete caption")
    let entities=generateChatInputTextEntities(text)
    check(entities.contains{if case let .TextUrl(url)=$0.type{return url=="https://example.org/radio"};return false},"edit keeps named hyperlink")
    check(entities.contains{if case .Bold=$0.type{return true};return false},"edit keeps bold caption")
    let explicit=file(99,"document"),replaced=editPlan(state,replacement:.standalone(media:explicit))
    if case let .update(ref)=replaced.media{check(ref.media === explicit,"explicit media replacement takes priority")}else{check(false,"explicit media replacement")}
    check(editPlan(state,limit:4).rich != nil,"account caption limit retains rich edit")
   }
  }
  let f=file(81,"music"),plain=ChatTextInputState(inputText:caption)
  let unchanged=editPlan(plain)
  check(unchanged.rich==nil && !unchanged.updating,"ordinary caption-only edit stays native")
  if case .keep=unchanged.media{check(true,"caption-only edit retains existing media")}else{check(false,"caption-only edit retains existing media")}
  let empty=ChatInputContent(blocks:[medium(f)])
  check(editPlan(ChatTextInputState(content:empty,selectionRange:0..<0)).rich==nil,"file without caption remains native")
  let two=ChatInputContent(blocks:[medium(f),medium(file(82,"music")),body("caption")])
  check(nagramiXEditableCaptionFile(two,maxCaptionLength:4096)==nil,"multiple files cannot become a partial single-media edit")
  check(editPlan(ChatTextInputState(content:two,selectionRange:0..<0)).rich != nil,"multiple-file edit retains complete rich layout")
  let inline=ChatInputContent(blocks:[body("before"),medium(f),body("after")])
  check(nagramiXEditableCaptionFile(inline,maxCaptionLength:4096)==nil,"inline media keeps its structural location")
  for kind in ["voice","round"] {
   let content=ChatInputContent(blocks:[medium(file(83,kind))])
   check(nagramiXEditableCaptionFile(content,maxCaptionLength:4096)==nil,"voice and round edits preserve existing route")
  }
  print("PASS file caption edit checks: \(checks)")
 }
}

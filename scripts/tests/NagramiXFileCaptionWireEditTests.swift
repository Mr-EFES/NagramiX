@main struct WireCaptionEditChecks {
 static func main() {
  let text="🎙️ Совместный проект\nРадио — подписаться"
  let ns=text as NSString,range=ns.range(of:"Радио — подписаться")
  let input=chatInputStateStringWithAppliedEntities(text,entities:[MessageTextEntity(range:range.location..<NSMaxRange(range),type:.TextUrl(url:"https://example.org/radio"))])
  let draft=ChatTextInputState(inputText:input)
  let f=file(20,"music")
  for richDocument in [false,true] {
   let current=richDocument ? nagramiXComposerFileDraft(draft,files:[f],caption:nil,initialState:nil)!:draft
   let plan=editPlan(current,existingFile:f)
   check(plan.text.string=="\n"+text,"both edit states keep the serialized caption line")
   check(plan.rich==nil,"representable file caption stays native on edit")
   check(plan.entities.contains{if case let .TextUrl(url)=$0.type{return url=="https://example.org/radio" && $0.range==(range.location+1)..<(NSMaxRange(range)+1)};return false},"edit named link range accounts for blank line")
  }
  var current=draft
  for _ in 0..<4 {
   let plan=editPlan(current,existingFile:f)
   check(plan.text.string=="\n"+text,"repeated save does not accumulate blank lines")
   current=ChatTextInputState(inputText:plan.text)
  }
  for kind in ["document","video","voice","round"] {
   let replacement=file(21,kind)
   let plan=editPlan(draft,replacement:.standalone(media:replacement),existingFile:f)
   check(plan.text.string==(kind=="document" ? "\n"+text:text),"explicit replacement determines caption spacing")
   if case let .update(ref)=plan.media {check(ref.media === replacement,"replacement keeps media precedence")} else {check(false,"replacement keeps media precedence")}
  }
  let image=TelegramMediaImage(decoder:PostboxDecoder(buffer:MemoryBuffer(data:Data())))
  check(editPlan(draft,replacement:.standalone(media:image),existingFile:f).text.string==text,"photo replacement does not inherit old file spacing")
  check(editPlan(draft,existingFile:f,captionAbove:true).text.string==text,"caption above media is not padded")
  check(editPlan(draft).text.string==text,"ordinary text-only edit is unchanged")
  check(editPlan(ChatTextInputState(inputText:NSAttributedString(string:"")),existingFile:f).text.length==0,"empty caption remains empty")
  for length in [1023,1024] {
   let value=String(repeating:"x",count:length)
   let plan=editPlan(ChatTextInputState(inputText:NSAttributedString(string:value)),limit:1024,existingFile:f)
   check(plan.text.string==(length==1023 ? "\n"+value:value),"edit at caption limit never truncates text")
  }
  print("File caption wire edit: \(checks) actual decision/trim/format/replacement checks passed; native pending manager/RPC not exercised")
 }
}

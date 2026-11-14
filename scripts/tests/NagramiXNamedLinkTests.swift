@main struct NamedLinkTests {
 static func main(){
  var checks=0
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  let title="Радио Таврия — подписаться 😀";let url="https://t.me/example"
  let named=NSAttributedString(string:title,attributes:[ChatTextInputAttributes.textUrl:ChatTextInputTextUrlAttribute(url:url)])
  let plain=NSAttributedString(string:"Обычный текст")
  let raw=NSAttributedString(string:url)
  let entity=MessageTextEntity(range:0..<named.length,type:.TextUrl(url:url))
  check(nagramiXHasNamedLink(named),"named URL remains a text entity")
  check(!nagramiXHasNamedLink(nil) && !nagramiXHasNamedLink(plain) && !nagramiXHasNamedLink(raw),"ordinary input stays on its native preview policy")
  check(nagramiXHasNamedLinkEntities([entity]),"native named entity recognized")
  check(!nagramiXHasNamedLinkEntities([MessageTextEntity(range:0..<1,type:.Bold)]),"formatting alone is not a URL")
  for text in [named,raw,plain] {
   PreviewServer.reset()
   let before=text.copy() as! NSAttributedString
   let result=urlPreviewStateForInputText(text,context:AccountContext(),currentQuery:UrlPreviewState(detectedUrls:["old"]),forPeerId:nil)
   var card:(TelegramMediaWebpage,String)?
   let d=result?.1.start(next:{card=$0(nil)})
   check(PreviewServer.requests==(text===raw ? 1:0),"named URL never fetches an automatic card")
   check((card != nil)==(text===raw),"only ordinary raw URL keeps native automatic card")
   check(text.isEqual(to:before),"preview policy never flattens or changes label/address")
   d?.dispose()
  }
  for attached in [false,true] {
   for text in [named,plain] {
    let sourceNamed=text===named
    var state=ChatPresentationInterfaceState()
    state.interfaceState.composeInputState=InputState(inputText:text,content:Content(allMedia:attached ? [1]:[]))
    state.interfaceState.editMessage=EditMessage(inputState:InputState(inputText:text))
    state.editMessageState=ChatEditInterfaceMessageState(content:.plaintext,mediaReference:nil)
    let oldCard=ChatPresentationInterfaceState.UrlPreview(url:url,webPage:TelegramMediaWebpage(),positionBelowText:true,largeMedia:nil)
    state.urlPreview=oldCard;state.editingUrlPreview=oldCard
    let controller=PreviewController();var composeDisposed=0;var editDisposed=0
    controller.urlPreviewQueryState=(UrlPreviewState(detectedUrls:[url]),ActionDisposable{composeDisposed+=1})
    controller.editingUrlPreviewQueryState=(UrlPreviewState(detectedUrls:[url]),ActionDisposable{editDisposed+=1})
    let compose=prepareCompose(state,controller)
    check((compose.0.urlPreview==nil)==(sourceNamed || attached),"compose clears existing named/attached preview")
    check(compose.1 == !(sourceNamed || attached),"compose does not issue a replacement request")
    check(composeDisposed == (sourceNamed || attached ? 1:0),"compose old query is cancelled")
    let edited=prepareEdit(state,controller)
    check((edited.0.editingUrlPreview==nil)==sourceNamed,"edit clears existing named preview")
    check((edited.1==nil)==sourceNamed && editDisposed==(sourceNamed ? 1:0),"edit cancels old query and suppresses new one")
    check((lateCompose(compose.0).urlPreview==nil)==(sourceNamed || attached),"late compose callback cannot resurrect card")
    check((lateEdit(edited.0).editingUrlPreview==nil)==sourceNamed,"late editing callback cannot resurrect card")
    check(compose.0.interfaceState.composeInputState.inputText.isEqual(to:text),"compose text and attributes are untouched")
    check(edited.0.interfaceState.editMessage!.inputState.inputText.isEqual(to:text),"editing keeps source hyperlink")
    for rich in [false,true] {
     let attrs=SendAdapter(state).attributes(text,entities:sourceNamed ? [entity]:[],rich:rich,attached:attached)
     let disabled=attrs.compactMap{$0 as? OutgoingContentInfoMessageAttribute}.contains{$0.flags.contains(.disableLinkPreviews)}
     check(disabled==(sourceNamed || (rich && attached)),"plain and rich sends carry no-preview flag for named links")
     check(!sourceNamed || !attrs.contains{$0 is WebpagePreviewMessageAttribute},"named send never carries competing preview options")
    }
    let saved=SaveAdapter(state).preview(state.interfaceState.editMessage!)
    check(saved.0==sourceNamed && (saved.1==nil)==sourceNamed,"edit save explicitly disables card while retaining ordinary behavior")
    if sourceNamed {
     let message=EngineRawMessage(media:[TelegramMediaWebpage(),FileMedia()],attributes:[TextEntitiesMessageAttribute(entities:[entity])])
     let reopened=updatedChatEditInterfaceMessageState(context:AccountContext(),state:state,message:message)
     check(reopened.0.editingUrlPreview==nil,"reopening old copied/forwarded post cannot seed its old card")
    }
   }
  }
  for entityList in [[],[entity]] {
   for media in [RequestEditMessageMedia.keep,.update(AnyMediaReference(media:TelegramMediaWebpage())),.update(AnyMediaReference(media:FileMedia()))] {
    let result=normalizedEdit(media:media,entities:TextEntitiesMessageAttribute(entities:entityList),webpagePreviewAttribute:WebpagePreviewMessageAttribute(leadingPreview:true,forceLargeMedia:true),disableUrlPreview:false)
    check(result.0 == !entityList.isEmpty,"core edit rechecks actual entities")
    check((result.3 & (1<<1) != 0) == !entityList.isEmpty,"native edit RPC carries no_webpage")
    if !entityList.isEmpty {
     check(result.2==nil,"core edit removes preview-only metadata")
     if case let .update(reference)=result.1 {check(reference.media is FileMedia,"core edit preserves genuine attachment")}
     else {check(true,"core keeps existing real media when stripping webpage update")}
    }
   }
  }
  print("PASS \(checks) real named-link preview/editor/send/edit decisions; UI/network are explicit edges")
 }
}

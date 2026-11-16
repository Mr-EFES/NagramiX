// IO граница: аккаунт/состояние контроллера, media reference и opaque rich page.
// Document, обе конверсии и всё тело production edit-decision исполняются.
public final class TelegramMediaWebpage:Media {
 public func isEqual(to other:Media)->Bool{other is TelegramMediaWebpage}
}
struct EditSource {let attributes:[MessageAttribute]}
struct EditDraft {let inputState:ChatTextInputState}
struct EditMediaState {let mediaReference:AnyMediaReference?}
struct EditPresentation {let editMessageState:EditMediaState?}
struct EditController {
 let context:FixtureCaptionContext
 let presentationInterfaceState:EditPresentation
 init(media:AnyMediaReference?,limit:Int){
  context=FixtureCaptionContext();context.userLimits.maxCaptionLength=limit
  presentationInterfaceState=EditPresentation(editMessageState:EditMediaState(mediaReference:media))
 }
}
struct EditPlan {
 let rich:RichTextMessageAttribute?,media:RequestEditMessageMedia,updating:Bool,disablePreview:Bool,webpage:TelegramMediaWebpage?,preview:Int?
}
func instantPage(from content:ChatInputContent)->FixtureEditPage{FixtureEditPage()}

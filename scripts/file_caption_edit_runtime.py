"""Настоящие helpers и ветки edit/native layout; account/queue/UI границы явные."""
from pathlib import Path
from validate_quick_format import block
import file_caption_consistency_runtime as previous
import rich_file_padding_runtime as rich
ROOT=Path(__file__).resolve().parents[1]
EDIT='submodules/TelegramUI/Sources/Chat/ChatControllerLoadDisplayNode.swift'
FILE=previous.FILE
TEXT='submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/Sources/ChatMessageTextBubbleContentNode.swift'


def fixture(source):
    code=previous.fixture(source).split('@main struct FileCaptionChecks',1)[0]
    # Rich page is opaque here; completeness/full-page flags are explicit IO data.
    code=code.replace(block(code,'                        let buildRichTextMessages:'),'',1)
    opaque=block(code,'public struct RichTextMessageAttribute:')
    code=code.replace(opaque,'''struct FixtureEditPage:Equatable {var isComplete=true}
public struct RichTextMessageAttribute:MessageAttribute {
 let instantPage:FixtureEditPage,fullInstantPage:FixtureEditPage?
 init(instantPage:FixtureEditPage,fullInstantPage:FixtureEditPage?){self.instantPage=instantPage;self.fullInstantPage=fullInstantPage}
}''',1)
    text=(source/EDIT).read_text()
    code+='\n'+block(text,'private func nagramiXEditableCaptionFile(')+'\n'
    code+='\n'+(ROOT/'scripts/tests/NagramiXFileCaptionEditBoundary.swift').read_text()+'\n'
    code+='\n'+block((source/'submodules/TelegramCore/Sources/PendingMessages/RequestEditMessage.swift').read_text(),'public enum RequestEditMessageMedia :').replace(' : Equatable','')+'\n'
    a=text.index('                let content = editMessage.inputState.content',text.index('        }, editMessage:'));b=text.index('                let entities =',a)
    decision=text[a:b]
    a=text.index('                var updatingMedia = false',b);b=text.index('                let _ = (strongSelf.context.account.postbox',a)
    media=text[a:b]
    code+='''func editPlan(_ draft:ChatTextInputState,limit:Int=4096,replacement:AnyMediaReference?=nil,hasWebpage:Bool=false,originalRich:RichTextMessageAttribute?=nil)->EditPlan {
 let message=EditSource(attributes:originalRich.map{[$0]} ?? [])
 let editMessage=EditDraft(inputState:draft)
 let strongSelf=EditController(media:replacement,limit:limit)
 var disableUrlPreview=false
 var webpage:TelegramMediaWebpage?=hasWebpage ? TelegramMediaWebpage():nil
 var webpagePreviewAttribute:Int?=hasWebpage ? 1:nil
'''+decision+media+'''
 return EditPlan(rich:richText,media:media,updating:updatingMedia,disablePreview:disableUrlPreview,webpage:webpage,preview:webpagePreviewAttribute)
}
'''
    code+='\n'+(ROOT/'scripts/tests/NagramiXFileCaptionEditTests.swift').read_text()
    return code


def geometry_fixture(source):
    file=(source/FILE).read_text();before=(ROOT/'ios/file_caption_edit/Before1.inc').read_text()
    common=(source/previous.COMMON).read_text();compact=block(common,'    public static var compact:')
    lines='\n'.join(x for x in compact.splitlines() if x.strip().startswith(('let file = ChatMessageItemFileLayoutConstants','let text = ChatMessageItemTextLayoutConstants')))
    text_top=block((source/TEXT).read_text(),'                    switch top {')
    def bottom(t):
        a=t.index('                    var bottomInset = fileInsets.bottom');b=t.index('                    return (CGSize(',a);return t[a:b]
    code='''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct UIEdgeInsets {let top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat}
struct ChatMessageItemFileLayoutConstants {let bubbleInsets:UIEdgeInsets}
struct ChatMessageItemTextLayoutConstants {let bubbleInsets:UIEdgeInsets}
struct Constants {let file:ChatMessageItemFileLayoutConstants,text:ChatMessageItemTextLayoutConstants}
func constants(_ UIScreenPixel:CGFloat)->Constants {
'''+lines+'''
 return Constants(file:file,text:text)
}
struct File {let isMusic:Bool}
enum Neighbour {case text,header,footer,media,reactions}
enum Spacing {case condensed,other}
enum Relative {case Neighbour(Bool,Neighbour,Spacing),None,other}
enum Position {case linear(Relative,Relative)}
func captionTop(_ pixel:CGFloat,top:Relative = .Neighbour(false,.text,.condensed))->CGFloat {
 let layoutConstants=constants(pixel)
 var topInset:CGFloat=0
'''+text_top+'''
 return topInset
}
'''
    for name,content in [('measure',file),('original',before)]:
        code+='func '+name+'''(_ fileSize:CGSize,music:Bool,caption:Bool,isBubbleless:Bool,pixel:CGFloat)->(CGSize,CGFloat,CGFloat) {
 let layoutConstants=constants(pixel),fileInsets=layoutConstants.file.bubbleInsets
 let selectedFile:File?=File(isMusic:music)
 let voiceRowHeight:CGFloat=38,voiceButtonOverhang:CGFloat=0
 let position=Position.linear(.None,caption ? .Neighbour(false,.text,.condensed):.None)
'''+bottom(content)+'''
 return (CGSize(width:fileSize.width+fileInsets.left+fileInsets.right,height:fileSize.height+fileInsets.top+bottomInset),fileInsets.top,bottomInset)
}
'''
    return code+r'''
@main enum FileEdges {
 static func main(){
  var checks=0
  func check(_ v:Bool,_ why:String){if !v{print("FAIL: "+why);exit(96)};checks+=1}
  for width:CGFloat in [170,350,500] {for height:CGFloat in [38,44,80] {for music in [false,true] {for caption in [false,true] {for bubbleless in [false,true] {for pixel:CGFloat in [0.5,1.0/3.0] {
   let size=CGSize(width:width,height:height)
   let now=measure(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel),old=original(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel)
   check(now.0.width==old.0.width,"classic bubble width is unchanged")
   check(now.1==old.1 && now.1==15,"file retains a visible native top inset")
   if !bubbleless && caption {
    check(abs(now.2+captionTop(pixel)-now.1)<0.00001,"top and complete file-to-text gap match")
    check(now.0.height>=old.0.height,"equal gap is counted in bubble height")
   } else {check(now.0==old.0,"no-caption and bubbleless layout unchanged")}
  }}}}}}
  print("PASS file edge geometry checks: \(checks)")
 }
}
'''

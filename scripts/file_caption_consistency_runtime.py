"""Реальные clipboard/Document/converters, native caption builder и standalone send closure."""
from pathlib import Path
from validate_quick_format import block
import composer_copy_integrity_runtime as old

ROOT=Path(__file__).resolve().parents[1]
MENU=old.MENU
FILE='submodules/TelegramUI/Components/Chat/ChatMessageFileBubbleContentNode/Sources/ChatMessageFileBubbleContentNode.swift'
COMMON='submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageItemCommon.swift'


def fixture(source):
    code=old.fixture(source).split('@main struct ComposerCopyChecks',1)[0]
    for name in ['preparePreview','acceptLatePreview']:
        code=code.replace(block(code,'func '+name+'('),'',1)
    # Only the test's opaque sticker-pack IO boundary needs the real enum shape
    # read by the unchanged account emoji policy in the standalone closure.
    code=code.replace('public struct StickerPackReference: Equatable, Codable {}','public enum StickerPackReference:Equatable,Codable {case id(id:Int64,accessHash:Int64)}',1)
    bridge=(source/old.BRIDGE).read_text()
    reverse=bridge[bridge.index('public func chatInputContent('):bridge.index('// MARK: - ChatInputContent')]
    code+='\n'+reverse+'\n'
    code+='\n'+block((source/'submodules/TelegramUI/Components/RichTextEditorMessageConversion/Sources/ButtonActionCodec.swift').read_text(),'public func instantPageRowAlignment(')+'\n'
    code+='\n'+(ROOT/'scripts/tests/NagramiXFileCaptionSendBoundary.swift').read_text()+'\n'
    menu=(source/MENU).read_text()
    code+='\n'+block(menu,'private func nagramiXDocumentUsesNativeFileCaption(')+'\n'
    code+='\n'+block(menu,'func nagramiXComposerCaptionMessages(')+'\n'
    code+='\n'+block(menu,'                        let buildRichTextMessages:')+'\n'
    code+='\n'+TESTS
    return code


TESTS=r'''
@main struct FileCaptionChecks {
 static func main() throws {
  let text="🎙️ Совместный проект\n\nТекст 🟨\nРадио — подписаться"
  let ns=text as NSString,link=ns.range(of:"Радио — подписаться"),title=ns.range(of:"Совместный проект")
  let entities=[MessageTextEntity(range:title.location..<NSMaxRange(title),type:.Bold),MessageTextEntity(range:link.location..<NSMaxRange(link),type:.TextUrl(url:"https://example.org/radio")),MessageTextEntity(range:link.location..<NSMaxRange(link),type:.Underline)]
  storeChatMessageTextInPasteboard(text,entities:entities)
  let document=try DocumentCodec.decode(UIPasteboard.general.items[0][RichTextEditorClipboard.fragmentUTI] as! Data)
  let controller=ChatControllerImpl(ChatTextInputState())
  func canonical(_ values:[MessageTextEntity])->[MessageTextEntity] {
   let encoder=JSONEncoder();encoder.outputFormatting=[.sortedKeys]
   return values.sorted{try! encoder.encode($0).lexicographicallyPrecedes(encoder.encode($1))}
  }
  for kind in ["music","document","voice","video"] {
   let f=file(10,kind)
   let attachment=nagramiXLeadingAttachmentDocument([(mediaID:"file",naturalSize:CGSize(width:1,height:1),kind:kind=="music" || kind=="voice" ? .audio:kind=="video" ? .video:.document,caption:[])])
   let expanded=document.replacingRange(globalFrom:0,globalTo:0,with:attachment).document
   let content=chatInputContent(fromDocument:expanded,resolveEmoji:{_ in nil},resolveMedia:{_ in .file(f)})
   let caption=attributedString(from:content)
   let normal=nagramiXComposerFileMessages(files:[f],caption:caption,inlineStickers:[:],threadId:17,replyTo:.init(id:47))
   let result=buildRichTextMessages(controller,expanded,["file":.file(f)],[:],false)!
   check(result.count==1 && normal.count==1,"one attachment remains one native post")
   if case let .message(sent,attrs,_,media,thread,reply,_,group,_,_)=result[0],case let .message(normalText,normalAttrs,_,_,_,_,_,_,_,_)=normal[0] {
    check(sent==text && sent==normalText,"normal and expanded send identical complete text")
    check(media?.media === f && f.payload==Data([1,2,3]),"native file reference and bytes preserved")
    check(thread==17 && reply?.id==47 && group==nil,"reply thread and single-file grouping preserved")
    check(!attrs.contains{$0 is RichTextMessageAttribute},"representable caption never becomes a wider rich bubble")
    let wire=attrs.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities ?? []
    let ordinary=normalAttrs.compactMap{$0 as? TextEntitiesMessageAttribute}.first?.entities ?? []
    check(canonical(wire)==canonical(ordinary),"normal and expanded send identical formatting entities")
    check(wire.contains{if case let .TextUrl(url)=$0.type{return url=="https://example.org/radio"};return false},"named hyperlink survives expanded attachment")
    check(wire.contains{if case .Bold=$0.type{return true};return false},"bold title survives expanded attachment")
    check(attrs.contains{($0 as? OutgoingContentInfoMessageAttribute)?.flags.contains(.disableLinkPreviews)==true},"file caption suppresses redundant link card")
   } else {check(false,"native enqueue schema")}
   check(FixtureCaption.richCalls==0,"native caption bypasses rich serializer")
  }
  let f=file(23,"music")
  let solo=Document(blocks:[.media(MediaBlock(id:BlockID.generate(),mediaID:"solo",kind:.audio,naturalSize:Size2D(width:1,height:1)))])
  check(buildRichTextMessages(controller,solo,["solo":.file(f)],[:],true)?.count==1,"empty caption with remove-formatting keeps file")
  let short=Document(blocks:[solo.blocks[0],.paragraph(ParagraphBlock(id:BlockID.generate(),style:.body,runs:[TextRun(text:"caption")]))])
  for limit in [0,6] {
   FixtureCaption.context.userLimits.maxCaptionLength=limit;FixtureCaption.richCalls=0
   let result=buildRichTextMessages(controller,short,["solo":.file(f)],[:],false)!
   check(FixtureCaption.richCalls==1 && result.count==1,"caption limit retains rich fallback without truncating")
   check(FixtureCaption.lastRichDocument==short,"rich fallback receives original document and media")
  }
  FixtureCaption.context.userLimits.maxCaptionLength=4096;FixtureCaption.richCalls=0
  var heading=short
  if case var .paragraph(p)=heading.blocks[1]{p.style = .heading1;heading.blocks[1] = .paragraph(p)}
  _=buildRichTextMessages(controller,heading,["solo":.file(f)],[:],false)
  check(FixtureCaption.richCalls==1 && FixtureCaption.lastRichDocument==heading,"structural formatting stays rich")
  var styled=short
  if case var .paragraph(p)=styled.blocks[1]{p.runs[0].attributes.highlight=RGBAColor(red:1,green:1,blue:0);styled.blocks[1] = .paragraph(p)}
  FixtureCaption.richCalls=0
  _=buildRichTextMessages(controller,styled,["solo":.file(f)],[:],false)
  check(FixtureCaption.richCalls==1 && FixtureCaption.lastRichDocument==styled,"article-only character formatting stays rich")
  var ambient=short
  if case var .paragraph(p)=ambient.blocks[1]{p.runs[0].attributes.fontSize=17;ambient.blocks[1] = .paragraph(p)}
  FixtureCaption.richCalls=0
  let ambientResult=buildRichTextMessages(controller,ambient,["solo":.file(f)],[:],false)
  check(FixtureCaption.richCalls==0 && ambientResult?.count==1,"editor ambient font size does not force a wider rich post")
  let unresolved=Document(blocks:[solo.blocks[0],.media(MediaBlock(id:BlockID.generate(),mediaID:"missing",kind:.audio,naturalSize:Size2D(width:1,height:1))),short.blocks[1]])
  FixtureCaption.richCalls=0
  _=buildRichTextMessages(controller,unresolved,["solo":.file(f)],[:],false)
  check(FixtureCaption.richCalls==1 && FixtureCaption.lastRichDocument==unresolved,"missing media cannot downgrade a partial post to native caption")
  let two=ChatInputContent(blocks:[medium(file(41,"music")),medium(file(42,"music")),body("text")])
  let batch=nagramiXComposerCaptionMessages(two,caption:NSAttributedString(string:"text"),maxCaptionLength:4096,sendWithoutFormatting:false,threadId:17,replyTo:.init(id:47))!
  check(batch.count==2,"multiple attachments preserve native message count")
  var ids:[Int64]=[],groups:[Int64?]=[],texts:[String]=[]
  for value in batch {if case let .message(text,_,_,reference,_,_,_,group,_,_)=value {ids.append((reference!.media as! TelegramMediaFile).fileId.id);groups.append(group);texts.append(text)}}
  check(ids==[41,42] && texts==["","text"] && groups[0] != nil && groups[0]==groups[1],"native attachment order caption placement and album grouping preserved")
  print("PASS file caption consistency checks: \(checks)")
 }
}
'''


def geometry_fixture(source):
    text=(source/FILE).read_text()
    previous=(ROOT/'ios/file_caption_consistency/Before1.inc').read_text()
    def bottom(t):
        start=t.index('                    var bottomInset = fileInsets.bottom')
        end=t.index('                    return (CGSize(',start)
        return t[start:end]
    constants=(source/COMMON).read_text()
    compact=block(constants,'    public static var compact:')
    lines='\n'.join(x for x in compact.splitlines() if x.strip().startswith(('let file = ChatMessageItemFileLayoutConstants','let text = ChatMessageItemTextLayoutConstants')))
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
enum Neighbour {case text}
enum Spacing {case condensed,other}
enum Relative {case Neighbour(Bool,Neighbour,Spacing),None}
enum Position {case linear(Int,Relative)}
'''
    for name,t in [('measure',text),('original',previous)]:
        code+='func '+name+'''(_ fileSize:CGSize,music:Bool,caption:Bool,isBubbleless:Bool,pixel:CGFloat)->CGSize {
 let layoutConstants=constants(pixel),fileInsets=layoutConstants.file.bubbleInsets
 let selectedFile:File?=File(isMusic:music)
 let voiceRowHeight:CGFloat=38,voiceButtonOverhang:CGFloat=0
 let position=Position.linear(0,caption ? .Neighbour(false,.text,.condensed):.None)
'''+bottom(t)+'''
 return CGSize(width:fileSize.width+fileInsets.left+fileInsets.right,height:fileSize.height+fileInsets.top+bottomInset)
}
'''
    return code+r'''
@main enum CaptionGeometry {
 static func main(){
  var checks=0
  func check(_ value:Bool,_ why:String){if !value{print("FAIL: "+why);exit(96)};checks+=1}
  for width:CGFloat in [170,350,500] {for height:CGFloat in [38,44,80] {for music in [false,true] {for caption in [false,true] {for bubbleless in [false,true] {for pixel:CGFloat in [0.5,1.0/3.0] {
   let size=CGSize(width:width,height:height),c=constants(pixel)
   let now=measure(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel)
   let old=original(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel)
   check(now.width==old.width,"caption spacing never widens bubble")
   if !bubbleless && caption {
    check(now.height>=height+c.file.bubbleInsets.top+c.text.bubbleInsets.top,"visible gap below file is retained")
   }
   if !bubbleless && music && caption {
    check(now.height>old.height,"music caption regression increases vertical gap")
   } else {
    check(now==old,"files without caption documents and bubbleless retain original geometry")
   }
  }}}}}}
  print("PASS file caption geometry checks: \(checks)")
 }
}
'''

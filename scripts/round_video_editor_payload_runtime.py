"""Production сборка файла, JSON-adjustments и обоих путей отправки кружка."""
from validate_quick_format import block
from round_video_editor_runtime import GEOMETRY_BOUNDARY, MODEL, production, clean, SINGLE, MESSAGES, SEND


BOUNDARY=r'''
class UIImage {}
protocol EngineRawMedia {}
protocol TelegramMediaResource {}
struct Resource:TelegramMediaResource {}
struct EngineItemCollectionId:Equatable {let id:Int64}
struct EngineMedia {struct Id:Equatable {let namespace:Int32;let id:Int64}}
enum EngineMediaResource {typealias Id=EngineMedia.Id}
enum Namespaces {enum Media {static let LocalFile:Int32=1}}
struct TelegramMediaImageRepresentation {}
struct TelegramMediaImage:EngineRawMedia {}
struct TelegramMediaFileAttribute {
 enum Kind {case name,video,animated,large,stickers}
 var kind:Kind;var duration:Double=0;var size=PixelDimensions(width:0,height:0);var flags:TelegramMediaVideoFlags=[]
 static func FileName(fileName:String)->Self{Self(kind:.name)}
 static func Video(duration:Double,size:PixelDimensions,flags:TelegramMediaVideoFlags,preloadSize:Int32?,coverTime:Double?,videoCodec:String?)->Self{Self(kind:.video,duration:duration,size:size,flags:flags)}
 static let Animated=Self(kind:.animated);static let hintFileIsLarge=Self(kind:.large);static let HasLinkedStickers=Self(kind:.stickers)
}
final class TelegramMediaFile:EngineRawMedia {
 let resource:TelegramMediaResource;let attributes:[TelegramMediaFileAttribute]
 init(fileId:EngineMedia.Id,partialReference:Int?,resource:TelegramMediaResource,previewRepresentations:[TelegramMediaImageRepresentation],videoThumbnails:[Int],videoCover:TelegramMediaImage?,immediateThumbnailData:Data?,mimeType:String,size:Int64?,attributes:[TelegramMediaFileAttribute],alternativeRepresentations:[TelegramMediaFile]){self.resource=resource;self.attributes=attributes}
 var isInstantVideo:Bool{attributes.contains{$0.kind == .video && $0.flags.contains(.instantRoundVideo)}}
 var isAnimated:Bool{attributes.contains{$0.kind == .animated}}
}
enum TGMediaVideoConversionPreset {case standard,veryLow,low,medium,high,veryHigh,animation,videoMessage}
let TGMediaVideoConversionPresetCompressedDefault=TGMediaVideoConversionPreset.standard
let TGMediaVideoConversionPresetCompressedVeryLow=TGMediaVideoConversionPreset.veryLow
let TGMediaVideoConversionPresetCompressedLow=TGMediaVideoConversionPreset.low
let TGMediaVideoConversionPresetCompressedMedium=TGMediaVideoConversionPreset.medium
let TGMediaVideoConversionPresetCompressedHigh=TGMediaVideoConversionPreset.high
let TGMediaVideoConversionPresetCompressedVeryHigh=TGMediaVideoConversionPreset.veryHigh
let TGMediaVideoConversionPresetAnimation=TGMediaVideoConversionPreset.animation
let TGMediaVideoConversionPresetVideoMessage=TGMediaVideoConversionPreset.videoMessage
enum TGMediaVideoConverter {static func estimatedSize(for preset:TGMediaVideoConversionPreset,duration:Double,hasAudio:Bool)->UInt{UInt(max(0,duration)*120000)}}
func chatMediaSendThumbnailRepresentation(thumbnail:UIImage,fittedTo:CGSize,storeResourceData:(EngineMedia.Id,Data)->Void)->TelegramMediaImageRepresentation?{nil}
func chatMediaSendVideoCover(_ cover:UIImage,storeResourceData:(EngineMedia.Id,Data)->Void)->TelegramMediaImage?{nil}
func chatMediaEditorVideoFileDimensions(values:MediaEditorValues,duration:Double)->PixelDimensions {
 let size=values.cropRect?.size ?? values.originalDimensions.cgSize
 let side=min(480,min(size.width,size.height))
 return values.qualityPreset == .videoMessage ? PixelDimensions(width:Int32(side),height:Int32(side)):values.originalDimensions
}
struct EngineMemoryBuffer {let data:Data;init(data:Data){self.data=data};func md5Digest()->Data{data}}
extension Data {func md5Digest()->Data{self}}
struct VideoMediaResourceAdjustments {let data:EngineMemoryBuffer;let digest:EngineMemoryBuffer;let isStory:Bool}
struct LocalFileVideoMediaResource:TelegramMediaResource {let randomId:Int64;let path:String;let adjustments:VideoMediaResourceAdjustments?}
struct MessageTextEntity:Equatable {let offset:Int;let length:Int;let type:String}
protocol MessageAttribute {}
enum EngineMessage {typealias Attribute=MessageAttribute}
struct TextEntitiesMessageAttribute:MessageAttribute {let entities:[MessageTextEntity]}
struct EmbeddedMediaStickersMessageAttribute:MessageAttribute {let files:[TelegramMediaFile]}
struct AutoremoveTimeoutMessageAttribute:MessageAttribute {let timeout:Int32;let countdownBeginTime:Int32?}
struct MediaSpoilerMessageAttribute:MessageAttribute {}
let viewOnceTimeout:Int32 = .max
enum AnyMediaReference {case standalone(media:EngineRawMedia);var media:EngineRawMedia{switch self{case let .standalone(media):return media}}}
enum EnqueueMessage {
 case message(text:String,attributes:[MessageAttribute],inlineStickers:[Int64:TelegramMediaFile],mediaReference:AnyMediaReference?,threadId:Int64?,replyToMessageId:Int?,replyToStoryId:Int?,localGroupingKey:Int64?,correlationId:Int64?,bubbleUpEmojiOrStickersets:[EngineItemCollectionId])
 var text:String{switch self{case let .message(text,_,_,_,_,_,_,_,_,_):return text}}
 var attributes:[MessageAttribute]{switch self{case let .message(_,v,_,_,_,_,_,_,_,_):return v}}
 var media:EngineRawMedia?{switch self{case let .message(_,_,_,v,_,_,_,_,_,_):return v?.media}}
 var grouping:Int64?{switch self{case let .message(_,_,_,_,_,_,_,v,_,_):return v}}
 var packs:[EngineItemCollectionId]{switch self{case let .message(_,_,_,_,_,_,_,_,_,v):return v}}
}
struct LegacyAssetPickerEnqueueMessage {let message:EnqueueMessage;let uniqueId:String?;let isFile:Bool}
struct ChatMediaSendCaption {let text:String;let entities:[MessageTextEntity];let bubbleUpEmojiOrStickersets:[EngineItemCollectionId]}
let captionEntities=[MessageTextEntity(offset:0,length:4,type:"bold"),MessageTextEntity(offset:5,length:2,type:"customEmoji")]
func chatMediaSendCaption(_ value:NSAttributedString?)->ChatMediaSendCaption{ChatMediaSendCaption(text:value?.string ?? "",entities:(value?.length ?? 0)>0 ? captionEntities:[],bubbleUpEmojiOrStickersets:(value?.length ?? 0)>0 ? [EngineItemCollectionId(id:91)]:[])}
struct ChatMediaEditorResult {
 enum Media {case image(UIImage,PixelDimensions);case video(path:String,values:MediaEditorValues,duration:Double)}
 let media:Media;var thumbnail:UIImage?;var caption=NSAttributedString(string:"");var stickers:[TelegramMediaFile]=[];var isAnimation=false
}
func chatMediaSendRenderedImageMedia(image:UIImage,nominalDimensions:PixelDimensions,thumbnail:UIImage?,stickerFiles:[TelegramMediaFile],forceHd:Bool,storeResourceData:(EngineMedia.Id,Data)->Void)->TelegramMediaImage?{TelegramMediaImage()}
func chatMediaEditorGifSendsOriginal(values:MediaEditorValues?,hasStickers:Bool)->Bool{false}
struct NoError:Error {}
struct Disposable {}
let EmptyDisposable=Disposable()
final class Subscriber<T,E> {var value:T?;var error:E?;func putNext(_ v:T){value=v};func putCompletion(){};func putError(_ e:E){error=e}}
final class Signal<T,E> {let body:(Subscriber<T,E>)->Disposable;init(_ body:@escaping(Subscriber<T,E>)->Disposable){self.body=body};func value()->T?{let s=Subscriber<T,E>();_ = body(s);return s.value}}
enum Queue {static func concurrentDefaultQueue()->Int{0}}
infix operator |> : AdditionPrecedence
func |> <T,U>(v:T,f:(T)->U)->U{f(v)}
func runOn<T,E>(_ queue:Int)->(Signal<T,E>)->Signal<T,E>{{v in v}}
final class Resources{func storeResourceData(id:EngineMedia.Id,data:Data){}}
final class Engine{let resources=Resources()}
final class AccountContext{let engine=Engine()}
struct TelegramMediaPaidContent:EngineRawMedia {enum Extended {case full(media:EngineRawMedia)};let amount:Int64;let extendedMedia:[Extended]}
struct ChatMediaSendItem {var uniqueId:String;var result:EngineRawMedia?;var options=ChatMediaSendItemOptions()}
func chatMediaSendItemMedia(item:ChatMediaSendItem,forceHd:Bool,storeResourceData:(EngineMedia.Id,Data)->Void)->(media:EngineRawMedia,stickerFiles:[TelegramMediaFile])?{item.result.map{($0,[])}}
'''


def fixture(source):
    flags=production(source,'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift','public struct TelegramMediaVideoFlags:')
    parts=[GEOMETRY_BOUNDARY,MODEL,flags,BOUNDARY,
           production(source,MESSAGES,'func chatMediaSendLegacyConversionPreset(',
                      'private func chatMediaSendVideoFile(','func chatMediaSendEditedVideoFile(',
                      'func chatMediaSendVideoSendValues(','func chatMediaSendMessage(',
                      'func nagramiXRoundVideoCaptionMessage(','func chatMediaSendBuildMessagesReportingSkipped('),
           production(source,SINGLE,'public func chatMediaEditorVideoAdjustments(',
                      'public func chatMediaEditorVideoDuration(',
                      'public func nagramiXRoundVideoTrimRange(','public func nagramiXRoundVideoSendValues(',
                      'public func chatMediaEditorEnqueueMessage(','public func chatMediaEditorEnqueueMessages('),
           production(source,SEND+'ChatMediaSendPlan.swift','public struct ChatMediaSendPlannedItem:', 'public struct ChatMediaSendItemOptions:'),
           TESTS]
    return '\n'.join(parts)


def item_fixture(source):
    boundary=BOUNDARY[:BOUNDARY.index('struct ChatMediaSendItem {')]
    stubs='''
enum ChatMediaSendLivePhotoMode {case off,live,loop,bounce}
struct ChatMediaSendConvertedGif {}
struct ChatMediaSendPreparedLivePhoto {}
struct ChatMediaSendPreparedAnimatedPhoto {}
'''
    return '\n'.join([GEOMETRY_BOUNDARY,MODEL,
        production(source,'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift','public struct TelegramMediaVideoFlags:'),boundary,stubs,
        production(source,SEND+'ChatMediaSendPlan.swift','public struct ChatMediaSendItemOptions:'),
        clean((source/(SEND+'ChatMediaSendItem.swift')).read_text()),r'''
@main struct RoundItemStateTests {static func main(){
 let options=ChatMediaSendItemOptions(caption:NSAttributedString(string:"keep"),timer:9,spoiler:true)
 var values=MediaEditorValues();values.qualityPreset = .videoMessage
 var item=ChatMediaSendItem(uniqueId:"one",source:.tempVideo(path:"source",dimensions:values.originalDimensions,duration:90),values:values,options:options)
 check(item.options.nagramiXRoundVideo,"constructor carries round eligibility to album planner")
 check(item.options.caption?.string=="keep" && item.options.timer==9 && item.options.spoiler,"existing item options are preserved")
 item.values=values.withUpdatedQualityPreset(.compressedMedium)
 check(!item.options.nagramiXRoundVideo,"replaced ordinary values clear stale round plan flag")
 item.values=values
 check(item.options.nagramiXRoundVideo,"later round edit updates planner flag")
 var other=item;other.uniqueId="two";other.values=nil
 check(item.options.nagramiXRoundVideo && !other.options.nagramiXRoundVideo,"item copies do not share mutable round selection")
 print("PASS round production item checks: \(checks)")
}}
'''])


TESTS=r'''
@main struct RoundPayloadTests {static func main() throws {
 let store:(EngineMedia.Id,Data)->Void={_,_ in}
 var values=MediaEditorValues();values.qualityPreset = .videoMessage;values.cropRect=CGRect(x:100,y:0,width:1080,height:1080);values.videoTrimRange=12..<130
 for muted in [false,true] {
  var source=values;source.videoIsMuted=muted
  let send=chatMediaSendVideoSendValues(source)
  check(send.qualityPreset == .videoMessage,"muted circle never becomes a GIF")
  let result=ChatMediaEditorResult(media:.video(path:"/tmp/captured.mp4",values:send,duration:180),caption:NSAttributedString(string:"text 🙂"))
  let messages=chatMediaEditorEnqueueMessages(context:AccountContext(),result:result,forceHd:false).value()!
  check(messages.count==2,"camera/single result preserves round and separate caption")
  let message=messages[0].message
  let file=message.media as! TelegramMediaFile
  check(file.isInstantVideo && !file.isAnimated,"real round document attribute; no animated fallback")
  check(message.text.isEmpty && message.grouping==nil,"round file carries no unsupported caption or album")
  let resource=file.resource as! LocalFileVideoMediaResource
  let encoded=try JSONDecoder().decode(MediaEditorValues.self,from:resource.adjustments!.data.data)
  check(encoded.videoTrimRange==12..<72 && encoded.cropRect==values.cropRect,"resource JSON contains chosen crop and exact bounded segment")
  let video=file.attributes.first{$0.kind == .video}!
  check(video.duration==60 && video.size.width==video.size.height,"duration and square size agree with deferred encoder")
  check(messages[1].message.text=="text 🙂" && messages[1].message.media==nil,"caption is preserved as ordinary adjacent text")
  check((messages[1].message.attributes.first as? TextEntitiesMessageAttribute)?.entities==captionEntities,"caption entities and custom emoji preserved")
  check(messages[1].message.packs==[EngineItemCollectionId(id:91)],"custom emoji pack metadata preserved")
  let prepared=nagramiXRoundVideoSendValues(send,duration:180)!
  let galleryFile=chatMediaSendEditedVideoFile(resource:Resource(),values:prepared,duration:180,fileName:"library.mp4",thumbnail:nil,cover:nil,stickerFiles:[],storeResourceData:store)
  check(galleryFile.isInstantVideo && !galleryFile.isAnimated,"gallery edited-file builder retains round flag with sound on or off")
  check(galleryFile.attributes.first{$0.kind == .video}?.duration==60,"gallery duration matches the bounded resource segment")
  let plan=ChatMediaSendPlannedItem(index:0,caption:result.caption,groupingKey:99,timer:viewOnceTimeout,spoiler:false,price:nil)
  let gallery=chatMediaSendBuildMessagesReportingSkipped(items:[ChatMediaSendItem(uniqueId:"library",result:galleryFile)],plan:[plan],forceHd:false,storeResourceData:store)
  check(gallery.messages.count==2 && gallery.skippedIndices.isEmpty,"gallery/batch path preserves whole round and caption")
  check((gallery.messages[0].message.attributes.first as? AutoremoveTimeoutMessageAttribute)?.timeout==viewOnceTimeout,"explicit view-once timer preserved on file")
  check(gallery.messages[1].message.attributes.allSatisfy{!($0 is AutoremoveTimeoutMessageAttribute)},"caption does not inherit view-once lifetime")
  check(gallery.messages[0].message.grouping==nil,"round cannot join an album even with stale plan")
 }
 var ordinary=values;ordinary.qualityPreset = .compressedHigh
 let normal=chatMediaEditorEnqueueMessage(result:ChatMediaEditorResult(media:.video(path:"/tmp/plain.mp4",values:ordinary,duration:180),caption:NSAttributedString(string:"caption")),forceHd:false,storeResourceData:store)!
 check((normal.message.media as? TelegramMediaFile)?.isInstantVideo==false && normal.message.text=="caption","ordinary file/caption path remains native")
 var bad=values;bad.cropRect=CGRect(x:0,y:0,width:1920,height:1080)
 check(chatMediaEditorEnqueueMessage(result:ChatMediaEditorResult(media:.video(path:"/tmp/invalid.mp4",values:bad,duration:180)),forceHd:false,storeResourceData:store)==nil,"invalid round fails before queue instead of sending ordinary video")
 check(chatMediaSendLegacyConversionPreset(.videoMessage) == .videoMessage,"size estimation selects round preset too")
 print("PASS round production payload checks: \(checks)")
}}
'''

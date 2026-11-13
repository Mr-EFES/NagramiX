"""Фактическая маршрутизация gallery send с реальным SwiftSignalKit."""
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
BASE='submodules/TelegramUI/Components/ChatMediaSend/'
HELPER=BASE+'Sources/NagramiXOriginalVideoSend.swift'
RENDER=BASE+'Sources/ChatMediaSendRender.swift'
LEGACY='submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift'
SIGNALS='submodules/SSignalKit/SwiftSignalKit/Source/'


def signal_library(source):
    code='\n'.join((source/(SIGNALS+n)).read_text() for n in ['Atomic.swift','Disposable.swift','Subscriber.swift'])
    code+='\n'+(source/(SIGNALS+'Signal.swift')).read_text().split('@available(iOS 13.0, macOS 10.15, *)',1)[0]
    queue=(source/(SIGNALS+'Queue.swift')).read_text()
    # The Swift6 Dispatch overlay needs WorkItem at the old closure boundary;
    # inline Queue.async/isCurrent behavior remains the exact native code.
    for old,new in [('self.nativeQueue.async(execute: f)','self.nativeQueue.async(execute: DispatchWorkItem(block: f))'),('self.nativeQueue.async(group: nil, qos: qos, flags: [.enforceQoS], execute: f)','self.nativeQueue.async(execute: DispatchWorkItem(qos: qos, flags: [.enforceQoS], block: f))'),('self.nativeQueue.asyncAfter(deadline: time, execute: f)','self.nativeQueue.asyncAfter(deadline: time, execute: DispatchWorkItem(block: f))')]:
        assert old in queue;queue=queue.replace(old,new)
    code+='\n'+queue+'\n'+block((source/(SIGNALS+'Signal_Dispatch.swift')).read_text(),'public func deliverOn<T, E>(_ queue: Queue)')
    definitions=[('Signal_Dispatch.swift','public func deliverOnMainQueue<T, E>'),('Signal_Mapping.swift','public func map<T, E, R>'),('Signal_Catch.swift','public func `catch`<T, E, R>'),('Signal_Take.swift','public func take<T, E>(_ count:'),('Signal_Meta.swift','private final class SignalQueueState<T, E>'),('Signal_Meta.swift','public func switchToLatest<T, E>'),('Signal_Meta.swift','public func mapToSignal<T, R, E>'),('Signal_Meta.swift','public func then<T, E>'),('Signal_Single.swift','public func single<T, E>'),('Signal_Combine.swift','private struct SignalCombineState'),('Signal_Combine.swift','private func combineLatestAny<E, R>'),('Signal_Combine.swift','private func signalOfAny<T, E>'),('Signal_Combine.swift','public func combineLatest<T, E>')]
    for name,marker in definitions:code+='\n'+block((source/(SIGNALS+name)).read_text(),marker)
    code+='\n'+block((source/(BASE+'Sources/ChatMediaSendVideoThumbnail.swift')).read_text(),'public func chatMediaSendBoundedCombine<T>')
    return code


def fixture(source):
    code=signal_library(source)
    for marker in ['public struct ChatMediaSendItemOptions:','public struct ChatMediaSendGlobalOptions:']:
        code+='\n'+block((source/(BASE+'Sources/ChatMediaSendPlan.swift')).read_text(),marker).replace('public ','')
    code+='\n'+BOUNDARY
    item=(source/(BASE+'Sources/ChatMediaSendItem.swift')).read_text();item='\n'.join(l for l in item.splitlines() if not l.startswith('import ')).replace('public ','')
    code+='\n'+item
    code+='\n'+block((source/(BASE+'Sources/ChatMediaEditorItemStore.swift')).read_text(),'public func chatMediaEditorValuesHaveVisualEdits(').replace('public ','')
    code+='\n'+'\n'.join(l for l in (source/HELPER).read_text().splitlines() if not l.startswith('import '))
    stock=(source/(BASE+'Sources/ChatMediaSendMessages.swift')).read_text()
    branch=block(stock,'        if isVideo {')
    code+='\nfunc stockVideoMedia(_ item:ChatMediaSendItem)->(media:EngineRawMedia,stickerFiles:[TelegramMediaFile])? {\nif case let .prebuilt(media)=item.source{return media.map{($0,item.stickers)}}\nguard case let .libraryAsset(identifier,pixelSize,isVideo,duration)=item.source else {return nil}\nlet forceHd=false\nlet storeResourceData:(EngineMediaResource.Id,Data)->Void={_,_ in}\n'+branch+'\n_ = forceHd\nreturn nil\n}\nfunc stockItem(_ item:ChatMediaSendItem)->TelegramMediaFile? {stockVideoMedia(item)?.media as? TelegramMediaFile}\n'
    code+='\n'+block((source/RENDER).read_text(),'public func chatMediaSendMessages(context:').replace('public ','')
    return code+'\n'+CHECKS


BOUNDARY=r'''
class UIImage {}
protocol EngineRawMedia:AnyObject {}
class TelegramMediaImage:EngineRawMedia {}
struct PixelDimensions {var width:Int32=1920;var height:Int32=1080;var cgSize:CGSize{CGSize(width:Int(width),height:Int(height))}}
enum MediaCropOrientation {case up,down}
struct Perspective {var isZero=true}
enum MediaQualityPreset {case compressedDefault,compressedVeryLow,compressedLow,compressedMedium,compressedHigh,compressedVeryHigh,animation,videoMessage,profileLow,profile,profileHigh,profileVeryHigh,sticker,passthrough,quality}
struct MediaEditorValues {
 var originalDimensions=PixelDimensions();var cropRect:CGRect?;var cropOffset=CGPoint.zero;var cropScale:CGFloat=1;var cropRotation:CGFloat=0
 var cropMirroring=false;var videoIsMirrored=false;var cropOrientation:MediaCropOrientation?;var cropPerspective=Perspective();var videoTrimRange:Range<Double>?
 var drawing:UIImage?;var maskDrawing:UIImage?;var entities:[Int]=[];var hasAdjustments=false;var hasTint=false;var hasBlur=false;var hasCurves=false;var audioTrack:Int?
 var videoBounce=false;var videoIsMuted=false;var videoVolume:CGFloat?;var additionalVideoPath:String?;var additionalVideoIsDual=false;var collage:[Int]=[];var qualityPreset:MediaQualityPreset?
}
struct ChatMediaSendConvertedGif {}
struct ChatMediaSendPreparedLivePhoto {}
struct ChatMediaSendPreparedAnimatedPhoto {}
enum ChatMediaSendLivePhotoMode {case off,live,loop}
struct TelegramMediaFile:EngineRawMediaPlaceholder {}
'''
# Native media/resource I/O types are explicit adapters. The actual modern
# .libraryAsset video branch creates .compress(...) resources below.
BOUNDARY=BOUNDARY.replace('struct TelegramMediaFile:EngineRawMediaPlaceholder {}',r'''
class TelegramMediaResource {}
struct VideoMediaResourceAdjustments {let marker:Int}
enum VideoLibraryMediaResourceConversion {case passthrough,compress(VideoMediaResourceAdjustments?)}
final class VideoLibraryMediaResource:TelegramMediaResource {
 let localIdentifier:String;let conversion:VideoLibraryMediaResourceConversion
 init(localIdentifier:String,conversion:VideoLibraryMediaResourceConversion){self.localIdentifier=localIdentifier;self.conversion=conversion}
}
final class TelegramMediaFile:EngineRawMedia {
 let resource:TelegramMediaResource;let original:Bool;let isVideo:Bool;let bytes:Data
 init(resource:TelegramMediaResource=TelegramMediaResource(),original:Bool,isVideo:Bool=true,bytes:Data=Data([1,2,3])){self.resource=resource;self.original=original;self.isVideo=isVideo;self.bytes=bytes}
}
func chatMediaSendVideoSendValues(_ v:MediaEditorValues)->MediaEditorValues{v}
func nagramiXRoundVideoSendValues(_ v:MediaEditorValues,duration:Double)->MediaEditorValues?{v}
func chatMediaEditorVideoAdjustments(values:MediaEditorValues)->VideoMediaResourceAdjustments?{VideoMediaResourceAdjustments(marker:1)}
func chatMediaSendLibraryFileName(_ name:String?)->String{name ?? "video.mp4"}
func chatMediaSendEditedVideoFile(resource:TelegramMediaResource,values:MediaEditorValues,duration:Double,fileName:String,thumbnail:UIImage?,cover:UIImage?,stickerFiles:[TelegramMediaFile],storeResourceData:(EngineMediaResource.Id,Data)->Void)->TelegramMediaFile{TelegramMediaFile(resource:resource,original:false)}
func chatMediaSendUneditedVideoFile(resource:TelegramMediaResource,dimensions:CGSize,duration:Double,fileName:String,thumbnail:UIImage?,cover:UIImage?,stickerFiles:[TelegramMediaFile],storeResourceData:(EngineMediaResource.Id,Data)->Void)->TelegramMediaFile{TelegramMediaFile(resource:resource,original:false)}
struct EngineMediaResource {struct Id {}}
final class Resources {func storeResourceData(id:EngineMediaResource.Id,data:Data){}}
final class Engine {let resources=Resources()}
final class Account {}
final class AccountContext {let account=Account();let engine=Engine()}
protocol ChatMediaSendRendering {}
struct Renderer:ChatMediaSendRendering {}
struct ChatMediaSendEvent {let items:[ChatMediaSendItem];let global:ChatMediaSendGlobalOptions;let files:[TelegramMediaFile?]}
func chatMediaSendMessages(items:[ChatMediaSendItem],global:ChatMediaSendGlobalOptions,renderer:ChatMediaSendRendering,makeGroupingKey:()->Int64,storeResourceData:(EngineMediaResource.Id,Data)->Void)->Signal<ChatMediaSendEvent,NoError>{.single(ChatMediaSendEvent(items:items,global:global,files:items.map(stockItem)))}
struct NagramiXMediaSettings {var originalVideos:Bool;static var current=NagramiXMediaSettings(originalVideos:true)}
struct Subtypes:OptionSet {let rawValue:Int;static let videoHighFrameRate=Subtypes(rawValue:1)}
enum MediaType {case video,image}
final class AssetResult {let firstObject:PHAsset?;init(_ asset:PHAsset?){firstObject=asset}}
final class PHAsset {
 let id:String;var mediaType:MediaType = .video;var mediaSubtypes:Subtypes=[];var originalIsVideo=true;var fails=false;var bytes=Data([9,8,7,6])
 init(_ id:String){self.id=id}
 static var registry:[String:PHAsset]=[:];static var lookups=0
 static func fetchAssets(withLocalIdentifiers ids:[String],options:Int?)->AssetResult{lookups += 1;return AssetResult(ids.first.flatMap{registry[$0]})}
}
enum Export {
 static var calls:[String]=[];static var covers:[UIImage?]=[];static var automatic=true;static var pending:[String:Subscriber<TelegramMediaFile,Void>]=[:];static var cancelled=0
 static func reset(){calls=[];covers=[];automatic=true;pending=[:];cancelled=0;PHAsset.lookups=0;PHAsset.registry=[:]}
 static func finish(_ asset:PHAsset){guard let s=pending.removeValue(forKey:asset.id) else{return};if asset.fails{s.putError(())}else{s.putNext(TelegramMediaFile(original:true,isVideo:asset.originalIsVideo,bytes:asset.bytes));s.putCompletion()}}
}
func nagramiXOriginalVideoFile(account:Account,asset:PHAsset,thumbnail:UIImage,cover:UIImage?)->Signal<TelegramMediaFile,Void>{Signal { s in
 Export.calls.append(asset.id);Export.covers.append(cover);Export.pending[asset.id]=s
 if Export.automatic {Export.finish(asset)}
 return ActionDisposable {if Export.pending.removeValue(forKey:asset.id) != nil {Export.cancelled += 1}}
}}
''')

CHECKS=r'''
var checks=0
func expect(_ value:@autoclosure()->Bool,_ message:String){checks += 1;if !value(){print("FAILED: "+message);exit(96)}}
func video(_ id:String)->ChatMediaSendItem {ChatMediaSendItem(uniqueId:id,source:.libraryAsset(identifier:id,pixelSize:CGSize(width:1920,height:1080),isVideo:true,duration:20),thumbnail:UIImage(),coverImage:UIImage(),options:ChatMediaSendItemOptions(caption:NSAttributedString(string:"caption"),spoiler:true),fileName:"source.mov")}
func send(_ items:[ChatMediaSendItem],enabled:Bool,global:ChatMediaSendGlobalOptions=ChatMediaSendGlobalOptions(grouping:true))->(ChatMediaSendEvent?,Disposable){NagramiXMediaSettings.current.originalVideos=enabled;var result:ChatMediaSendEvent?;let d=chatMediaSendMessages(context:AccountContext(),items:items,global:global,renderer:Renderer()).start(next:{result=$0});return(result,d)}
@main struct OriginalVideoTests {
 static func main(){
  for enabled in [false,true] {
   Export.reset();let a=PHAsset("a");PHAsset.registry["a"]=a;let item=video("a");let global=ChatMediaSendGlobalOptions(grouping:true,forcedCaption:NSAttributedString(string:"forced"),forceHd:true,saveEditedPhotosToCameraRoll:true)
   let (event,d)=send([item],enabled:enabled,global:global);defer{d.dispose()}
   expect(event != nil,"send produces native pipeline outcome")
   expect(event?.files[0]?.original == enabled,"ON original and OFF compression are distinct")
   expect(Export.calls.count == (enabled ? 1 : 0) && PHAsset.lookups == (enabled ? 1 : 0),"OFF never enters original Photos export")
   expect(event?.items[0].options == item.options && event?.global == global && event?.items[0].uniqueId == item.uniqueId,"caption spoiler global and identity preserved")
   if enabled {expect(Export.covers.last! === item.coverImage,"original export receives chosen cover")}
   if !enabled {guard let r=event?.files[0]?.resource as? VideoLibraryMediaResource else{expect(false,"OFF uses real native library resource branch");return};if case .compress(nil)=r.conversion{expect(true,"native default compression")}else{expect(false,"OFF retains stock compress conversion")}}
  }
  // Every content edit or special media stays on its native path.
  for index in 0..<22 {
   Export.reset();PHAsset.registry["a"]=PHAsset("a");var item=video("a");var v=MediaEditorValues()
   switch index {
   case 0:item.thumbnail=nil
   case 1:item.options.timer=1
   case 2:item.options.price=5
   case 3:item.options.isAnimation=true
   case 4:item.options.isMuted=true
   case 5:item.options.hasAnimatedPainting=true
   case 6:item.options.isLivePhoto=true
   case 7:item.options.livePhotoLoopOrBounce=true
   case 8:item.options.nagramiXRoundVideo=true
   case 9:v.cropRotation=1;item.values=v
   case 10:v.videoTrimRange=1..<5;item.values=v
   case 11:v.videoBounce=true;item.values=v
   case 12:v.videoVolume=0.3;item.values=v
   case 13:v.additionalVideoPath="other";item.values=v
   case 14:v.collage=[1];item.values=v
   case 15:v.maskDrawing=UIImage();item.values=v
   case 16:v.audioTrack=1;item.values=v
   case 17:v.videoIsMirrored=true;v.cropMirroring=true;item.values=v
   case 18:v.qualityPreset = .videoMessage;item.values=v
   case 19:item.stickers=[TelegramMediaFile(original:false)]
   case 20:item.source = .tempVideo(path:"capture",dimensions:PixelDimensions(),duration:10)
   default:PHAsset.registry["a"]?.mediaSubtypes = .videoHighFrameRate
   }
   let (event,d)=send([item],enabled:true);d.dispose();expect(event != nil && Export.calls.isEmpty,"edited and special videos retain native conversion")
  }
  Export.reset();let a=PHAsset("a");PHAsset.registry["a"]=a;var quality=video("a");var v=MediaEditorValues();v.qualityPreset = .compressedLow;quality.values=v
  let (qualityResult,qd)=send([quality],enabled:true);qd.dispose();expect(qualityResult?.files[0]?.original == true,"quality-only preference does not alter original ON")
  for missing in [false,true] {Export.reset();let asset=PHAsset("a");asset.fails=true;if !missing{PHAsset.registry["a"]=asset};let (event,d)=send([video("a")],enabled:true);d.dispose();expect(event != nil && event?.files[0] == nil,"failed original export is skipped without compressed fallback")}
  Export.reset();let x=PHAsset("x"),y=PHAsset("y");PHAsset.registry=["x":x,"y":y];x.originalIsVideo=false
  let (mixed,md)=send([video("x"),video("y")],enabled:true);md.dispose();expect(mixed?.items.map{$0.uniqueId} == ["x","y"] && mixed?.global.grouping == false,"unsupported original document keeps order without mixed media album")
  Export.reset();PHAsset.registry=["x":x,"y":y];Export.automatic=false
  NagramiXMediaSettings.current.originalVideos=true
  let pendingSignal=chatMediaSendMessages(context:AccountContext(),items:[video("x"),video("y")],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer())
  NagramiXMediaSettings.current.originalVideos=false
  var completed:ChatMediaSendEvent?;let pd=pendingSignal.start(next:{completed=$0})
  expect(Export.calls == ["x"] && completed == nil,"exports are bounded and wait for ready originals")
  Export.finish(x);expect(Export.calls == ["x","y"] && completed == nil,"next original starts after previous result")
  Export.finish(y);expect(completed?.files.allSatisfy{$0?.original == true} == true,"mode snapshot survives setting change during export");pd.dispose()
  let (next,nd)=send([video("y")],enabled:false);nd.dispose();expect(next?.files[0]?.original == false,"next send reads latest OFF value")
  Export.reset();PHAsset.registry=["x":x,"y":y];Export.automatic=false
  let (_,cd)=send([video("x"),video("y")],enabled:true);cd.dispose();Export.finish(x)
  expect(Export.cancelled == 1 && Export.calls == ["x"],"cancellation releases current request and never starts next export")
  print("Original video send-mode production checks: \(checks)")
 }
}
'''

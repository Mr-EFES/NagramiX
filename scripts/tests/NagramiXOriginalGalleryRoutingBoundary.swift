// Value/model IO boundary. The production trim check uses the real public method contract.
extension MediaEditorValues {
 func withUpdatedVideoTrimRange(_ value:Range<Double>?)->MediaEditorValues{var result=self;result.videoTrimRange=value;return result}
}
struct VideoMediaResourceAdjustments{let marker:Int}
enum VideoLibraryMediaResourceConversion{case passthrough,compress(VideoMediaResourceAdjustments?)}
final class VideoLibraryMediaResource:Resource {
 let localIdentifier:String,conversion:VideoLibraryMediaResourceConversion
 var id:String{"compressed-"+localIdentifier}
 init(localIdentifier:String,conversion:VideoLibraryMediaResourceConversion){self.localIdentifier=localIdentifier;self.conversion=conversion}
}
func chatMediaSendVideoSendValues(_ values:MediaEditorValues)->MediaEditorValues{values}
func nagramiXRoundVideoSendValues(_ values:MediaEditorValues,duration:Double)->MediaEditorValues?{values}
func chatMediaEditorVideoAdjustments(values:MediaEditorValues)->VideoMediaResourceAdjustments?{VideoMediaResourceAdjustments(marker:1)}
func chatMediaSendLibraryFileName(_ name:String?)->String{name ?? "video.mp4"}
final class CompressionBoundary {static var calls=0}
func compressedFile(_ resource:Resource)->TelegramMediaFile {
 CompressionBoundary.calls+=1
 return TelegramMediaFile(fileId:EngineMedia.Id(namespace:1,id:0),partialReference:nil,resource:resource,previewRepresentations:[],videoThumbnails:[],videoCover:nil,immediateThumbnailData:nil,mimeType:"video/mp4",size:nil,attributes:[.Video(duration:0.5,size:PixelDimensions(width:96,height:64),flags:[],preloadSize:nil,coverTime:nil,videoCodec:nil)],alternativeRepresentations:[])
}
func chatMediaSendEditedVideoFile(resource:Resource,values:MediaEditorValues,duration:Double,fileName:String,thumbnail:UIImage?,cover:UIImage?,stickerFiles:[TelegramMediaFile],storeResourceData:(EngineMediaResource.Id,Data)->Void)->TelegramMediaFile{compressedFile(resource)}
func chatMediaSendUneditedVideoFile(resource:Resource,dimensions:CGSize,duration:Double,fileName:String,thumbnail:UIImage?,cover:UIImage?,stickerFiles:[TelegramMediaFile],storeResourceData:(EngineMediaResource.Id,Data)->Void)->TelegramMediaFile{compressedFile(resource)}
final class Engine {let resources:Resources;init(_ account:Account){resources=account.resources}}
final class AccountContext {let account=Account();var engine:Engine{Engine(account)}}
protocol ChatMediaSendRendering{}
struct Renderer:ChatMediaSendRendering{}
struct ChatMediaSendEvent {let items:[ChatMediaSendItem],global:ChatMediaSendGlobalOptions,files:[TelegramMediaFile?]}
func chatMediaSendMessages(items:[ChatMediaSendItem],global:ChatMediaSendGlobalOptions,renderer:ChatMediaSendRendering,makeGroupingKey:()->Int64,storeResourceData:(EngineMediaResource.Id,Data)->Void)->Signal<ChatMediaSendEvent,NoError>{
 .single(ChatMediaSendEvent(items:items,global:global,files:items.map{routedMedia($0)?.media as? TelegramMediaFile}))
}
final class GalleryResult {
 private let lock=NSLock();private var event:ChatMediaSendEvent?
 func next(_ value:ChatMediaSendEvent){lock.lock();event=value;lock.unlock()}
 var value:ChatMediaSendEvent?{lock.lock();defer{lock.unlock()};return event}
}

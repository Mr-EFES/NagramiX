// IO-only boundaries: no VideoToolbox/AVFoundation/Postbox success is claimed on Linux.
let AVVideoCodecKey="AVVideoCodecKey",AVVideoWidthKey="AVVideoWidthKey",AVVideoHeightKey="AVVideoHeightKey"
let AVVideoCompressionPropertiesKey="AVVideoCompressionPropertiesKey",AVVideoAverageBitRateKey="AVVideoAverageBitRateKey"
let AVEncoderBitRateKey="AVEncoderBitRateKey"
public struct AVVideoCodecType:Equatable {public let rawValue:String;public static let h264=Self(rawValue:"avc1"),hevc=Self(rawValue:"hvc1")}
public enum MediaQualityPreset {case videoMessage,compressedDefault}
public struct MediaEditorValues {public var qualityPreset:MediaQualityPreset?;public var nagramiXRoundTuning:[Int]?}
public struct CMTime:Equatable {let value:Int64;let timescale:Int32;static let zero=Self(value:0,timescale:1)}
typealias CMTimeScale=Int32
struct CMTimeRange {let start:CMTime;let duration:CMTime}
let kCMPersistentTrackID_Invalid:Int32=0
let kCMVideoCodecType_H264:UInt32=0x61766331,kCMVideoCodecType_HEVC:UInt32=0x68766331
final class CMFormatDescription {let width:Int32,height:Int32,codec:UInt32;init(_ w:Int32,_ h:Int32,_ c:UInt32){width=w;height=h;codec=c}}
func CMVideoFormatDescriptionGetDimensions(_ d:CMFormatDescription)->(width:Int32,height:Int32){(d.width,d.height)}
func CMFormatDescriptionGetMediaSubType(_ d:CMFormatDescription)->UInt32{d.codec}
public class AVAsset {let fixtureID:String;init(_ id:String="source"){fixtureID=id}}
final class AVAssetTrack {let formatDescriptions:[Any];let nominalFrameRate:Float;let naturalSize:CGSize;let fixtureDuration:Double;init(_ width:Int32,_ height:Int32,_ fps:Float,_ codec:UInt32,duration:Double=60){formatDescriptions=[CMFormatDescription(width,height,codec)];nominalFrameRate=fps;naturalSize=CGSize(width:Int(width),height:Int(height));fixtureDuration=duration}}
struct FixtureDuration {let seconds:Double}
final class AVURLAsset:AVAsset {var duration:FixtureDuration{FixtureDuration(seconds:track?.fixtureDuration ?? .nan)};let track:AVAssetTrack?;init(url:URL){track=EncoderIO.metadata.with{$0[url.path]};super.init(url.path)};func tracks(withMediaType:String)->[AVAssetTrack]{track.map{[$0]} ?? []}}
extension String {static let video="video"}
final class AVMutableVideoComposition {var renderSize=CGSize.zero;var frameDuration=CMTime.zero;var sourceTrackIDForFrameTiming:Int32=0;var instructions:[AVMutableVideoCompositionInstruction]=[]}
final class AVMutableVideoCompositionInstruction {var timeRange=CMTimeRange(start:.zero,duration:.zero);var layerInstructions:[AVMutableVideoCompositionLayerInstruction]=[]}
struct FixtureTransform {static let identity=Self()}
final class AVMutableVideoCompositionLayerInstruction {let track:AVAssetTrack;var usesIdentity=false;init(assetTrack:AVAssetTrack){track=assetTrack};func setTransform(_ t:FixtureTransform,at:CMTime){usesIdentity=true}}
final class AVAssetReaderVideoCompositionOutput {let videoTracks:[AVAssetTrack];let videoSettings:[String:Any];var videoComposition:AVMutableVideoComposition?;init(videoTracks:[AVAssetTrack],videoSettings:[String:Any]){self.videoTracks=videoTracks;self.videoSettings=videoSettings}}
public final class UIImage {}
public final class TelegramMediaFile {}
struct Logger {static let shared=Logger();func log(_ category:String,_ value:String){}}
public struct AppConfiguration {public var data:[String:Any]?;public static let defaultValue=Self(data:nil)}
public struct PreferenceEntry {let value:AppConfiguration;public func get<T>(_ type:T.Type)->T?{value as? T}}
public struct PreferencesView {public var values:[Int:PreferenceEntry]}
public enum PreferencesKeys {public static let appConfiguration=1}
public final class Postbox {
 let encoding:[String:Any]?;let never:Bool
 public init(_ encoding:[String:Any]?=nil,never:Bool=false){self.encoding=encoding;self.never=never}
 public func preferencesView(keys:[Int])->Signal<PreferencesView,NoError>{
  if never{return .never()}
  return .single(PreferencesView(values:[1:PreferenceEntry(value:AppConfiguration(data:encoding.map{["round_video_encoding":$0]}))]))
 }
}
final class FixtureTempFile {let path:String;init(_ path:String){self.path=path}}
final class EngineTempBox {
 static let shared=EngineTempBox();let root=URL(fileURLWithPath:CommandLine.arguments[0]).deletingLastPathComponent().appendingPathComponent("round-encoding-"+UUID().uuidString).path
 let allocated=Atomic<[String]>(value:[])
 init(){try! FileManager.default.createDirectory(atPath:root,withIntermediateDirectories:true)}
 func tempFile(fileName:String)->FixtureTempFile{let p=root+"/"+UUID().uuidString+"-"+fileName;_ = allocated.modify{$0+[p]};return FixtureTempFile(p)}
 func dispose(_ f:FixtureTempFile){try? FileManager.default.removeItem(atPath:f.path)}
}
struct EncoderPlan {var size:Int64;var codec:UInt32?=nil;var fps:Float?=nil;var side:Int32?=nil;var failure=false;var held=false;var duration:Double=60}
enum EncoderIO {
 static let plans=Atomic<[EncoderPlan]>(value:[]),received=Atomic<[MediaEditorVideoExport.Configuration]>(value:[])
 static let metadata=Atomic<[String:AVAssetTrack]>(value:[:])
 static let paths=Atomic<[String]>(value:[])
 static let started=Atomic<(() -> Void)?>(value:nil)
 static let writes=Queue(name:"EncoderIO")
 static func reset(_ value:[EncoderPlan]){_ = plans.swap(value);_ = received.swap([]);_ = metadata.swap([:]);_ = paths.swap([])}
}
public final class MediaEditorVideoExport {
 public enum Subject {case image(image:UIImage);case video(asset:AVAsset,isStory:Bool);case sticker(file:TelegramMediaFile)}
 public struct Configuration {
  public var videoSettings:[String:Any];public var audioSettings:[String:Any];public var values:MediaEditorValues;public var frameRate:Float
  public var useStreamingWriter=false
  // PRODUCTION_ROUND_CONFIG_FLAG
 }
 // PRODUCTION_EXPORT_ERROR
 // PRODUCTION_EXPORT_STATUS
 private let state=Promise<ExportStatus>(.unknown)
 private let cancelled=Atomic<Bool>(value:false)
 public var streamingFileGrowth:((Int64,Int64)->Void)?
 // Drive the encoder IO after the observer/callback wiring, independent of scheduler speed.
 private var startWriting:(() -> Void)?
 public var status:Signal<ExportStatus,NoError>{let begin=startWriting;startWriting=nil;begin?();return state.get()}
 public init(postbox:Postbox,subject:Subject,configuration:Configuration,outputPath:String){
  _ = EncoderIO.received.modify{$0+[configuration]};_ = EncoderIO.paths.modify{$0+[outputPath]}
  var selected:EncoderPlan?
  _ = EncoderIO.plans.modify { value in var next=value;if !next.isEmpty{selected=next.removeFirst()};return next }
  EncoderIO.started.with{$0}?()
  let plan=selected ?? EncoderPlan(size:1024)
  if plan.held{return}
  self.startWriting = { [weak self] in
   guard let self else{return}
   EncoderIO.writes.justDispatch { [self] in
   guard !self.cancelled.with({$0}) else{return}
   if plan.failure{self.state.set(.single(.failed(.writing(nil))));return}
   _ = FileManager.default.createFile(atPath:outputPath,contents:nil)
   let file=try! FileHandle(forWritingTo:URL(fileURLWithPath:outputPath));try! file.truncate(atOffset:UInt64(plan.size));try! file.close()
   let side=plan.side ?? Int32(configuration.videoSettings[AVVideoWidthKey] as? Int ?? 640)
   let requested=(configuration.videoSettings[AVVideoCodecKey] as? AVVideoCodecType) ?? .h264
   let codec=plan.codec ?? (requested == .hevc ? kCMVideoCodecType_HEVC:kCMVideoCodecType_H264)
   _ = EncoderIO.metadata.modify{var v=$0;v[outputPath]=AVAssetTrack(side,side,plan.fps ?? configuration.frameRate,codec,duration:plan.duration);return v}
   self.state.set(.single(.progress(0.5)))
   self.streamingFileGrowth?(plan.size,1024)
   self.state.set(.single(.completed))
   }
  }
 }
 public func cancel(){_ = cancelled.swap(true)}
}

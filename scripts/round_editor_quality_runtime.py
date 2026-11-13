"""Реальные snapshot/copy/export и переключение кружка в явных UI/codec-границах."""
import re
from validate_quick_format import block
import round_video_editor_runtime as native
import round_video_editor_ui_runtime as ui
from validate_round_video_bitrate import export_branch

SCREEN=native.SCREEN
VALUES='submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift'
MODEL='submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift'
VIDEO=native.VIDEO
GALLERY=SCREEN+'ChatMediaEditorScreenGallery.swift'
CONTROLS=SCREEN+'ChatMediaEditorBottomControls.swift'
COMPONENT=SCREEN+'ChatMediaEditorBottomControlsComponent.swift'


def clean(text):
    return native.clean(text)


def copy_model(source):
    """Actual immutable constructor/member declarations/copy methods; graph types adapted."""
    text=(source/VALUES).read_text();init=block(text,'    public init(\n        peerId: EnginePeer.Id,')
    signature=init[:init.index('    ) {')]
    fields=re.findall(r'^        (\w+): ([^\n]+?)(?:,)?$',signature,re.M)
    assert len(fields)==43,len(fields)
    fields=[(n,t.rstrip(',').split(' = ',1)[0]) for n,t in fields]
    props=[]
    for n,t in fields:
        declaration='public let '+n+': '+t
        assert declaration in text,declaration
        props.append('let '+n+': '+t)
    methods=['    public func makeCopy()', '    public func withUpdatedNagramiXRoundTuning(',
             '    public func withUpdatedQualityPreset(', '    public func withUpdatedVideoTrimRange(',
             '    public func withUpdatedVideoIsMuted(', '    public func withUpdatedCrop(rect:']
    model='final class MediaEditorValues {\n'+'\n'.join(props)+'\n'+clean(init)+'\n'+'\n'.join(clean(block(text,m)) for m in methods)+'\n}\n'
    return model


GRAPH=r'''
struct PixelDimensions {let width:Int32;let height:Int32;var cgSize:CGSize{CGSize(width:Int(width),height:Int(height))}}
enum EnginePeer {struct Id {let id:Int}}
struct UIColor {let id:Int}
final class UIImage {let id:Int;init(_ id:Int){self.id=id}}
struct VideoMirroringChange {let id:Int}
struct VideoPositionChange {let id:Int}
struct VideoCollageItem {let id:Int}
struct CodableDrawingEntity {let id:Int}
struct MediaAudioTrack {let id:Int}
struct MediaAudioTrackSamples {let id:Int}
enum EditorToolKey {case exposure}
struct MediaEditorCropPerspective {let id:Int}
enum MediaCropOrientation {case left;var isSideward:Bool{true}}
let hasHEVCHardwareEncoder=false
extension CGSize {func aspectFitted(_ max:CGSize)->CGSize {let s=min(max.width/width,max.height/height);return CGSize(width:width*s,height:height*s)}}
enum AVVideoCodecType {static let h264="h264",hevc="hevc"}
enum MediaEditorVideoExport {struct Configuration {
 let videoSettings:[String:Any];let audioSettings:[String:Any];let values:MediaEditorValues;let frameRate:Float;let preferredDuration:Double?
}}
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Round quality regression: "+message+"\n").utf8));exit(91)};checks+=1}
func sameFields(_ a:MediaEditorValues,_ b:MediaEditorValues,except:Set<String>=[])->Bool {
 let x=Mirror(reflecting:a).children.filter{!except.contains($0.label!)}.map{($0.label!,String(reflecting:$0.value))}
 let y=Mirror(reflecting:b).children.filter{!except.contains($0.label!)}.map{($0.label!,String(reflecting:$0.value))}
 return x.map{$0.0}==y.map{$0.0} && x.map{$0.1}==y.map{$0.1}
}
'''
KEYS=['AVVideoAverageBitRateKey','AVVideoProfileLevelKey','AVVideoProfileLevelH264HighAutoLevel','AVVideoH264EntropyModeKey','AVVideoH264EntropyModeCABAC','AVVideoCodecKey','AVVideoWidthKey','AVVideoHeightKey','AVVideoCompressionPropertiesKey','AVFormatIDKey','kAudioFormatMPEG4AAC','AVSampleRateKey','AVEncoderBitRateKey','AVNumberOfChannelsKey','kVTProfileLevel_HEVC_Main_AutoLevel']


def fixture(source):
    values=(source/VALUES).read_text()
    result='import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'
    result+=GRAPH+'\n'+''.join('let '+k+'="'+k+'"\n' for k in KEYS)
    result+=clean(block(values,'public enum MediaQualityPreset:'))+'\n'
    result+=copy_model(source)+'\n'+clean((source/MODEL).read_text())+'\n'
    result+=clean(block((source/VIDEO).read_text(),'func chatMediaEditorRoundVideoValues('))+'\n'
    for marker in ('func targetSize(', 'private struct VideoMessageExportSettings', 'public func recommendedVideoExportConfiguration('):
        result+=clean(block(values,marker))+'\n'
    # Only tuning's actual encode/decode statements are needed for deferred data here.
    encode=next(l.strip() for l in values.splitlines() if 'try container.encodeIfPresent(self.nagramiXRoundTuning' in l)
    decode=next(l.strip() for l in values.splitlines() if 'self.nagramiXRoundTuning = try container.decodeIfPresent' in l)
    result+='''struct TuningEnvelope:Codable {
 let nagramiXRoundTuning:[Int]?;enum CodingKeys:String,CodingKey{case nagramiXRoundTuning}
 init(_ value:[Int]?){nagramiXRoundTuning=value}
 init(from decoder:Decoder)throws{let container=try decoder.container(keyedBy:CodingKeys.self);'''+decode+'''}
 func encode(to encoder:Encoder)throws{var container=encoder.container(keyedBy:CodingKeys.self);'''+encode+'''}
}\n'''
    result+=BASE+TESTS
    return result


BASE=r'''
func base(_ preset:MediaQualityPreset? = .videoMessage)->MediaEditorValues {
 return MediaEditorValues(peerId:.init(id:7),originalDimensions:.init(width:1920,height:1080),cropOffset:CGPoint(x:1,y:2),cropRect:CGRect(x:100,y:0,width:1080,height:1080),cropScale:1.5,cropRotation:0.2,cropMirroring:true,cropOrientation:.left,cropPerspective:.init(id:4),gradientColors:[.init(id:5)],videoTrimRange:4..<45,videoBounce:false,videoIsMuted:false,videoIsFullHd:true,videoIsMirrored:true,videoVolume:0.7,additionalVideoPath:"keep-path",additionalVideoIsDual:true,additionalVideoMirroringChanges:[.init(id:8)],additionalVideoPosition:CGPoint(x:2,y:3),additionalVideoScale:1.2,additionalVideoRotation:0.4,additionalVideoPositionChanges:[.init(id:9)],additionalVideoTrimRange:1..<8,additionalVideoOffset:2,additionalVideoVolume:0.4,collage:[.init(id:10)],nightTheme:true,drawing:UIImage(11),maskDrawing:UIImage(12),entities:[.init(id:13)],toolValues:[.exposure:14],audioTrack:.init(id:15),audioTrackTrimRange:3..<9,audioTrackOffset:4,audioTrackVolume:0.6,audioTrackSamples:.init(id:16),collageTrackSamples:.init(id:17),coverImageTimestamp:6,coverDimensions:CGSize(width:70,height:80),qualityPreset:preset,imageDuration:7,nagramiXRoundTuning:nil)
}
'''
TESTS=r'''
@main struct RoundQualityTests {static func main()throws {
 for quality in NagramiXRoundVideoSettings.Quality.allCases {for fps in NagramiXRoundVideoSettings.FrameRate.allCases {for codec in NagramiXRoundVideoSettings.Codec.allCases {for rate in stride(from:1_000_000,through:2_000_000,by:100_000) {
  let settings=NagramiXRoundVideoSettings(enabled:true,quality:quality,frameRate:fps,codec:codec,bitRate:rate)
  let before=base();let selected=chatMediaEditorRoundVideoValues(before,settings:settings)
  let snapshot=[quality.rawValue,fps.rawValue,codec.rawValue,rate]
  check(selected.nagramiXRoundTuning==snapshot,"editor snapshots selected side FPS codec and independent bitrate")
  check(sameFields(before,selected,except:["nagramiXRoundTuning"]),"snapshot copy preserves every other constructor field")
  check(before.nagramiXRoundTuning==nil && selected !== before,"immutable source remains independent")
  check(chatMediaEditorRoundVideoValues(selected,settings:.init(enabled:true,quality:.maximum,codec:.h264,bitRate:1_000_000)) === selected,"reopen keeps saved item snapshot after another enabled selection")
  let delayed=chatMediaEditorRoundVideoValues(selected,settings:.init(enabled:false,quality:.standard))
  check(delayed === selected,"reopen keeps saved item snapshot even after global change")
  let trim=delayed.withUpdatedVideoTrimRange(5..<25).withUpdatedVideoIsMuted(true)
  check(trim.nagramiXRoundTuning==snapshot,"native trim mute and copy retain quality snapshot")
  let json=try JSONEncoder().encode(TuningEnvelope(trim.nagramiXRoundTuning))
  let decoded=try JSONDecoder().decode(TuningEnvelope.self,from:json)
  let pending=trim.withUpdatedNagramiXRoundTuning(decoded.nagramiXRoundTuning)
  let config=recommendedVideoExportConfiguration(values:pending,duration:20,frameRate:24)
  check(config.videoSettings[AVVideoWidthKey] as? Int == quality.rawValue && config.videoSettings[AVVideoHeightKey] as? Int == quality.rawValue,"deferred encoder emits selected square resolution")
  check(config.frameRate==Float(fps.rawValue),"selected FPS survives default export argument")
  check(config.videoSettings[AVVideoCodecKey] as? String == (codec == .h264 ? "h264":"hevc"),"encoder uses selected codec")
  let compression=config.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
  check(compression[AVVideoAverageBitRateKey] as? Int == rate,"encoder uses chosen independent bitrate")
  check((compression[AVVideoH264EntropyModeKey] != nil) == (codec == .h264),"HEVC never receives H264 entropy")
  check(pending.makeCopy().nagramiXRoundTuning==snapshot,"native copy retains all tuning")
 }}}}
 let fresh=base();let off=chatMediaEditorRoundVideoValues(fresh,settings:.init(enabled:false,quality:.maximum,codec:.hevc,bitRate:2_000_000))
 check(off === fresh && off.nagramiXRoundTuning==nil,"master OFF retains native default without attaching custom export")
 let standard=recommendedVideoExportConfiguration(values:off,duration:45,frameRate:30)
 check(standard.videoSettings[AVVideoWidthKey] as? Int == 480,"OFF retains native 480 ceiling")
 check(standard.videoSettings[AVVideoCodecKey] as? String == "h264","OFF retains native H264")
 for preset:MediaQualityPreset? in [nil,.compressedHigh,.animation,.sticker,.profile] {
  let ordinary=base(preset);let result=chatMediaEditorRoundVideoValues(ordinary,settings:.init(enabled:true,quality:.maximum))
  check(result === ordinary,"ordinary video photo story and other modes unchanged")
 }
 for legacy in [[512,60,1],[640,30,0,1_800_000],[],[999,30,0]] {
  let saved=base().withUpdatedNagramiXRoundTuning(legacy)
  check(chatMediaEditorRoundVideoValues(saved,settings:.init(enabled:true,quality:.standard)) === saved,"existing tuning never silently rewritten during restore")
 }
 print("Round editor quality production checks: \(checks)")
}}
'''


def ui_fixture(source):
    code=ui.fixture(source)
    code=code.replace(' var originalDimensions=PixelDimensions', ' var nagramiXRoundTuning:[Int]?\n func withUpdatedNagramiXRoundTuning(_ tuning:[Int]?)->Self{var v=self;v.nagramiXRoundTuning=tuning;return v}\n var originalDimensions=PixelDimensions',1)
    assert 'withUpdatedNagramiXRoundTuning(_ tuning' in code
    code=code.replace('@main struct RoundEditorStateTests',clean((source/MODEL).read_text())+'\n'+clean(block((source/VIDEO).read_text(),'func chatMediaEditorRoundVideoValues('))+'\n@main struct RoundEditorStateTests',1)
    insertion=r'''
 let settings=NagramiXRoundVideoSettings(enabled:true,quality:.high,frameRate:.smooth,codec:.hevc,bitRate:1_900_000)
 NagramiXRoundVideoSettings.update(settings)
 let qualified=ChatMediaEditorScreen.Node(first);qualified.nagramiXToggleRoundVideo()
 check(qualified.mediaEditor.values.nagramiXRoundTuning==[512,60,1,1_900_000],"actual round toggle attaches high-quality settings instead of native 480")
 let saved=qualified.mediaEditor.values
 NagramiXRoundVideoSettings.update(.init(enabled:true,quality:.maximum,codec:.h264,bitRate:1_700_000))
 check(qualified.mediaEditor.values==saved,"queued item does not observe later global settings changes")
 qualified.nagramiXToggleRoundVideo()
 check(qualified.mediaEditor.values.nagramiXRoundTuning==first.nagramiXRoundTuning,"exit round restores original tuning without stale values")
 qualified.nagramiXToggleRoundVideo()
 check(qualified.mediaEditor.values.nagramiXRoundTuning==[640,30,0,1_700_000],"new conversion uses latest maximum and bitrate")
 qualified.nagramiXToggleRoundVideo()
 NagramiXRoundVideoSettings.update(.init(enabled:false,quality:.maximum,codec:.hevc))
 qualified.nagramiXToggleRoundVideo()
 check(qualified.mediaEditor.values.nagramiXRoundTuning==nil,"quality master OFF never leaks previous per-item tuning")
'''
    marker=' print("PASS round production editor state checks: '
    assert code.count(marker)==1
    return code.replace(marker,insertion+'\n'+marker,1)


def badge_fixture(source):
    text=(source/CONTROLS).read_text();content=clean(block(text,'public enum ChatMediaEditorBottomControlsContent:'))
    action=block(text,'public func chatMediaEditorBottomControlsItems(')
    start=action.index('            if tab == .qualityTab {');end=action.index('            return ChatMediaEditorBottomControlsMiddleItem(',start)
    body=action[start:end]
    return r'''import Foundation
struct TGPhotoEditorTab:Equatable {let rawValue:Int;static let qualityTab=Self(rawValue:1);static let paintTab=Self(rawValue:2)}
enum ChatMediaEditorPaintTab {case pen}
func chatMediaEditorBottomControlsTabIcon(_ tab:TGPhotoEditorTab)->String{"native"}
'''+content+'''
func chosen(tab:TGPhotoEditorTab,isVideo:Bool,roundVideoSelected:Bool,roundVideoQualitySide:Int?,qualityHighQuality:Bool,qualityPreset:Int)->ChatMediaEditorBottomControlsContent {
 let content:ChatMediaEditorBottomControlsContent
'''+body+'''return content
}
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Round quality regression: "+message+"\\n").utf8));exit(91)};checks+=1}
@main struct RoundQualityBadgeTests {static func main(){
 for side in [384,480,512,640] {check(chosen(tab:.qualityTab,isVideo:true,roundVideoSelected:true,roundVideoQualitySide:side,qualityHighQuality:false,qualityPreset:3) == .roundVideoQuality(side:side),"round badge displays export side instead of legacy preset 480")}
 check(chosen(tab:.qualityTab,isVideo:true,roundVideoSelected:false,roundVideoQualitySide:640,qualityHighQuality:false,qualityPreset:4) == .quality(isPhoto:false,highQuality:false,preset:4),"ordinary preset icon unchanged")
 check(chosen(tab:.qualityTab,isVideo:false,roundVideoSelected:true,roundVideoQualitySide:640,qualityHighQuality:true,qualityPreset:4) == .quality(isPhoto:true,highQuality:true,preset:0),"photo HD badge unchanged")
 check(chosen(tab:.qualityTab,isVideo:true,roundVideoSelected:true,roundVideoQualitySide:nil,qualityHighQuality:false,qualityPreset:3) == .roundVideoQuality(side:480),"legacy default remains 480")
 print("Round editor quality badge checks: \\(checks)")
}}
'''

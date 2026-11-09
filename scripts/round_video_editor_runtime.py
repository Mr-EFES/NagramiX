"""Реальные методы круглого видео в явных границах Foundation/UI/AVFoundation."""
from validate_quick_format import block

SCREEN='submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/'
SEND='submodules/TelegramUI/Components/ChatMediaSend/Sources/'
VIDEO=SCREEN+'ChatMediaEditorScreenVideo.swift'
SINGLE=SEND+'ChatMediaSendSingleItem.swift'
MESSAGES=SEND+'ChatMediaSendMessages.swift'
GEOMETRY='submodules/TelegramUI/Components/MediaCropComponent/Sources/MediaCropGeometry.swift'
SETTINGS='submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift'

GEOMETRY_BOUNDARY='''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
'''


def clean(text):
    return '\n'.join(l for l in text.splitlines() if not l.startswith('import ')).replace('public ','').replace('@objc ','')


def production(source,name,*markers):
    text=(source/name).read_text()
    return '\n'.join(clean(block(text,marker)) for marker in markers)


MODEL=r'''
enum MediaQualityPreset:Int32,Codable {case compressedDefault,compressedVeryLow,compressedLow,compressedMedium,compressedHigh,compressedVeryHigh,animation,videoMessage,passthrough}
struct PixelDimensions:Codable,Equatable {
 var width:Int32;var height:Int32
 init(width:Int32,height:Int32){self.width=width;self.height=height}
 var cgSize:CGSize{CGSize(width:Int(width),height:Int(height))}
}
enum MediaCropOrientation:String,Codable {case up,left,down,right
 var isSideward:Bool{self == .left || self == .right}
 var rotation:CGFloat{switch self{case .up:return 0;case .left:return .pi/2;case .down:return .pi;case .right:return -.pi/2}}
}
struct MediaEditorCropPerspective:Codable,Equatable {var horizontal:CGFloat=0;var vertical:CGFloat=0;static let zero=Self();var isZero:Bool{self == .zero}}
struct MediaEditorValues:Codable,Equatable {
 var originalDimensions=PixelDimensions(width:1920,height:1080)
 var cropRect:CGRect?;var cropRotation:CGFloat=0;var cropOrientation:MediaCropOrientation?
 var cropMirroring=false;var cropPerspective=MediaEditorCropPerspective.zero
 var qualityPreset:MediaQualityPreset? = .compressedHigh
 var videoTrimRange:Range<Double>?;var videoBounce=false;var videoIsMuted=false
 var videoIsMirrored=false;var coverImageTimestamp:Double?;var marker="untouched"
 func withUpdatedVideoTrimRange(_ range:Range<Double>?)->Self{var v=self;v.videoTrimRange=range;return v}
 func withUpdatedQualityPreset(_ preset:MediaQualityPreset?)->Self{var v=self;v.qualityPreset=preset;return v}
 func withUpdatedVideoIsMuted(_ muted:Bool)->Self{var v=self;v.videoIsMuted=muted;return v}
 func withUpdatedCrop(rect:CGRect?,rotation:CGFloat,orientation:MediaCropOrientation?,mirroring:Bool,perspective:MediaEditorCropPerspective)->Self{
  var v=self;v.cropRect=rect;v.cropRotation=rotation;v.cropOrientation=orientation;v.cropMirroring=mirroring;v.cropPerspective=perspective;return v
 }
}
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Round video regression: "+message+"\n").utf8));exit(91)};checks+=1}
'''


def geometry(source):
    # The unchanged native placement, cover-fit and inverse-crop bodies execute.
    # Only CGRect.applying(CGAffineTransform)'s rotated bounding size is adapted
    # for Linux Foundation; video UI has no perspective adjustment controls.
    markers=['public struct MediaCropState:', 'public func mediaCropRectsEqual(',
             'private func mediaCropAvailableRect(', 'public func mediaCropApplyingLockedRatio(',
             'public struct MediaCropContentPlacement:', 'private func mediaCropRotatedVector(',
             'private func mediaCropUnrotatedFrameSize(', 'public func mediaCropContentAngle(',
             'public func mediaCropContentPlacement(', 'public func mediaCropRect(',
             'private func mediaCropScaleToSize(', 'public func mediaCropCoverFit(',
             'public func mediaCropMinimumZoomScale(']
    return production(source,GEOMETRY,*markers)+r'''
let mediaCropFloatEpsilon:CGFloat=0.00001
func mediaCropRotatedContentSize(_ size:CGSize,rotation:CGFloat)->CGSize{
 CGSize(width:abs(size.width*cos(rotation))+abs(size.height*sin(rotation)),height:abs(size.width*sin(rotation))+abs(size.height*cos(rotation)))
}
func mediaCropPerspectiveCoverFit(_ placement:MediaCropContentPlacement,frame:CGRect,state:MediaCropState,allowScale:Bool,rotationStartScale:CGFloat?)->MediaCropContentPlacement{
 preconditionFailure("Perspective rendering is outside this scalar geometry boundary")
}
'''


def range_fixture(source):
    return GEOMETRY_BOUNDARY+MODEL+production(source,SINGLE,'public func nagramiXRoundVideoTrimRange(','public func nagramiXRoundVideoSendValues(')+'\n'+production(source,VIDEO,'func nagramiXRoundVideoTime(')+RANGE_TESTS


RANGE_TESTS=r'''
@main struct RoundRangeTests {static func main() throws {
 for duration in [0.001,0.03,0.5,1,12,59.99,60,60.001,90,3600] {
  let range=nagramiXRoundVideoTrimRange(duration:duration,range:nil)!
  check(range.lowerBound==0 && range.upperBound==min(duration,60),"whole source selects at most 60 seconds without stretching")
 }
 for duration in [0.0,-1.0,Double.nan,Double.infinity] {check(nagramiXRoundVideoTrimRange(duration:duration,range:nil)==nil,"invalid source cannot create a round")}
 for i in 0..<3000 {
  let start=Double(i)/7.0
  let range=nagramiXRoundVideoTrimRange(duration:600,range:start..<(start+90))!
  check(range.lowerBound==start,"selected start never resets to zero")
  check(range.upperBound<=600 && range.upperBound-range.lowerBound<=60,"strict cap including floating point starts")
 }
 check(nagramiXRoundVideoTrimRange(duration:80,range:70..<120)==70..<80,"range clamps only to source end")
 check(nagramiXRoundVideoTrimRange(duration:80,range:90..<120)==nil,"out-of-source selection is rejected rather than silently shifted")
 check(nagramiXRoundVideoTrimRange(duration:80,range:10..<10)==nil,"empty trim rejected")
 var ordinary=MediaEditorValues();ordinary.videoTrimRange=10..<150
 check(nagramiXRoundVideoSendValues(ordinary,duration:180)==ordinary,"ordinary video is byte-value unchanged")
 var round=ordinary;round.qualityPreset = .videoMessage;round.cropRect=CGRect(x:100,y:0,width:1080,height:1080)
 let normalized=nagramiXRoundVideoSendValues(round,duration:180)!
 check(normalized.videoTrimRange==10..<70 && normalized.marker==round.marker,"shared resource and payload range normalized without dropping edits")
 let data=try JSONEncoder().encode(normalized)
 let decoded=try JSONDecoder().decode(MediaEditorValues.self,from:data)
 check(decoded==normalized,"selected crop and segment survive deferred JSON conversion")
 var square=round;square.originalDimensions=PixelDimensions(width:480,height:480);square.cropRect=nil
 check(nagramiXRoundVideoSendValues(square,duration:180) != nil,"already-square full-frame video needs no explicit crop rect")
 var bad=round;bad.cropRect=nil;check(nagramiXRoundVideoSendValues(bad,duration:180)==nil,"rectangle cannot be mislabeled as a round")
 bad=round;bad.cropRect=CGRect(x:0,y:0,width:800,height:600);check(nagramiXRoundVideoSendValues(bad,duration:180)==nil,"non-square crop rejected")
 bad=round;bad.videoBounce=true;check(nagramiXRoundVideoSendValues(bad,duration:180)==nil,"bounce cannot double the minute limit")
 bad=round;bad.cropRotation = .nan;check(nagramiXRoundVideoSendValues(bad,duration:180)==nil,"invalid rotation rejected")
 bad=round;bad.cropRect=CGRect(x:5000,y:0,width:1080,height:1080);check(nagramiXRoundVideoSendValues(bad,duration:180)==nil,"off-source square rejected")
 check(nagramiXRoundVideoTime(12)=="00:12" && nagramiXRoundVideoTime(72)=="01:12","visible selection times")
 check(nagramiXRoundVideoTime(.nan)=="00:00","time display rejects NaN")
 print("PASS round range/resource checks: \(checks)")
}}
'''


def prefs_fixture(source):
    tab=(source/'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
    return GEOMETRY_BOUNDARY+MODEL[MODEL.index('var checks=0'):]+r'''
final class UserDefaults {
 static let standard=UserDefaults();var values:[String:Any]=[:]
 func object(forKey:String)->Any?{values[forKey]}
 func set(_ value:Any,forKey:String){values[forKey]=value}
}
'''+clean((source/SETTINGS).read_text())+'\nstruct NagramiXTabSettings {\n'+clean(block(tab,'    public static var roundVideoEditorEnabled: Bool {'))+'\n}\n'+r'''
@main struct RoundPreferenceTests {static func main(){
 let defaults=UserDefaults.standard
 check(NagramiXMediaSettings.default.roundVideo,"new capability is available on cold install")
 check(NagramiXTabSettings.roundVideoEditorEnabled,"absent key enables the function")
 var value=NagramiXMediaSettings.current;value.roundVideo=false;NagramiXMediaSettings.update(value)
 check(!NagramiXTabSettings.roundVideoEditorEnabled,"saved OFF survives reread")
 value=NagramiXMediaSettings.current;value.photoQuality=88;NagramiXMediaSettings.update(value)
 check(!NagramiXTabSettings.roundVideoEditorEnabled,"unrelated settings update preserves saved OFF")
 value=NagramiXMediaSettings.current;value.roundVideo=true;NagramiXMediaSettings.update(value)
 check(NagramiXTabSettings.roundVideoEditorEnabled,"explicit ON restored")
 check(defaults.values["nagramix.videos.roundVideo"] as? Bool == true,"only explicit new setting persisted")
 print("PASS round preference checks: 6")
}}
'''


def geometry_fixture(source):
    return GEOMETRY_BOUNDARY+MODEL+geometry(source)+production(source,VIDEO,'func nagramiXRoundVideoCrop(')+GEOMETRY_TESTS


GEOMETRY_TESTS=r'''
@main struct RoundGeometryTests {static func main(){
 let frame=CGRect(x:0,y:0,width:300,height:300)
 for size in [CGSize(width:1920,height:1080),CGSize(width:1080,height:1920),CGSize(width:480,height:480),CGSize(width:3840,height:2160)] {
 for orientation in [MediaCropOrientation.up,.left,.down,.right] {for rotation:CGFloat in [0,0.1,-0.3] {for mirrored in [false,true] {
  var state=MediaCropState(originalSize:size);state.orientation=orientation;state.rotation=rotation;state.mirrored=mirrored
  state=mediaCropApplyingLockedRatio(1,to:state)
  for translation in [CGPoint.zero,CGPoint(x:100000,y:100000),CGPoint(x:-100000,y:-100000),CGPoint(x:80,y:-45)] {for scale:CGFloat in [0.001,0.5,1,2,1000] {
   let crop=nagramiXRoundVideoCrop(state:state,frame:frame,translation:translation,scale:scale)
   check(abs(crop.cropRect.width-crop.cropRect.height)<0.0001 && crop.cropRect.width>0,"circle keeps square encoded crop")
   let rotated=mediaCropRotatedContentSize(size,rotation:rotation)
   for point in [CGPoint(x:crop.cropRect.minX,y:crop.cropRect.minY),CGPoint(x:crop.cropRect.maxX,y:crop.cropRect.minY),CGPoint(x:crop.cropRect.minX,y:crop.cropRect.maxY),CGPoint(x:crop.cropRect.maxX,y:crop.cropRect.maxY)] {
    let x=point.x-rotated.width/2,y=point.y-rotated.height/2
    let original=CGPoint(x:x*cos(-rotation)-y*sin(-rotation)+size.width/2,y:x*sin(-rotation)+y*cos(-rotation)+size.height/2)
    check(original.x > -1 && original.y > -1 && original.x<size.width+1 && original.y<size.height+1,"native cover-fit prevents black corners on pan/zoom/rotation")
   }
  }}
 }}}}
 let initial=MediaCropState(originalSize:CGSize(width:1920,height:1080))
 check(nagramiXRoundVideoCrop(state:initial,frame:.zero,translation:.zero,scale:1)==initial,"zero layout is harmless")
 check(nagramiXRoundVideoCrop(state:initial,frame:frame,translation:CGPoint(x:CGFloat.nan,y:0),scale:1)==initial,"invalid gesture rejected")
 print("PASS round native crop checks: \(checks)")
}}
'''


def plan_fixture(source):
    return GEOMETRY_BOUNDARY+MODEL+clean((source/(SEND+'ChatMediaSendPlan.swift')).read_text())+r'''
@main struct RoundPlanTests {static func main(){
 var standard=ChatMediaSendItemOptions(caption:NSAttributedString(string:"caption"))
 var circle=standard;circle.nagramiXRoundVideo=true
 for items in [[standard,standard],[standard,circle],[circle,standard],[circle,circle]] {
  let plan=chatMediaSendPlan(items:items,global:ChatMediaSendGlobalOptions(grouping:true),makeGroupingKey:{51})
  check(plan.count==items.count,"all selected videos retained")
  check(plan.allSatisfy{$0.groupingKey == (items.contains{$0.nagramiXRoundVideo} ? nil:51)},"round messages never enter an album")
  check(plan.map{$0.caption?.string}==items.map{$0.caption?.string},"all captions preserved")
 }
 standard.excludedFromGrouping=true
 let native=chatMediaSendPlan(items:[standard,ChatMediaSendItemOptions(),ChatMediaSendItemOptions()],global:ChatMediaSendGlobalOptions(grouping:true),makeGroupingKey:{52})
 check(native[0].groupingKey==nil && native[1].groupingKey==52 && native[2].groupingKey==52,"existing non-round per-item grouping exclusion unchanged")
 print("PASS round album plan checks: \(checks)")
}}
'''


def toolbar_fixture(source):
    native='submodules/TelegramUI/Components/MediaEditorBottomControls/Sources/MediaEditorBottomControls.swift'
    controls=SCREEN+'ChatMediaEditorBottomControls.swift'
    return GEOMETRY_BOUNDARY+r'''
let mediaEditorBottomControlsButtonSide:CGFloat=44
let chatMediaEditorBottomControlsButtonSide:CGFloat=44
let chatMediaEditorBottomControlsSideInset:CGFloat=26
func floorToScreenPixels(_ v:CGFloat)->CGFloat{floor(v*3)/3}
var checks=0
func check(_ v:@autoclosure()->Bool,_ m:String){if !v(){FileHandle.standardError.write(Data(("Round video regression: "+m+"\n").utf8));exit(91)};checks+=1}
'''+production(source,native,'public struct MediaEditorBottomControlsLayoutSpec:', 'public struct MediaEditorBottomControlsLayout:', 'public func mediaEditorBottomControlsLocalLayout(')+'''
let chatMediaEditorBottomControlsSpec=MediaEditorBottomControlsLayoutSpec(sideInset:26,middleCentering:.screenBand(inset:44),buttonSide:44)
'''+production(source,controls,'func nagramiXRoundVideoToolbarSpec(', 'func nagramiXRoundVideoColumnNeedsBottom(')+r'''
@main struct RoundToolbarTests {static func main(){
 for width:CGFloat in [310,318,320,350,375,390,393,402,414,430,568,667,844,1024] {for count in [4,5] {for right:CGFloat in [44,46] {
  let spec=nagramiXRoundVideoToolbarSpec(width:width,itemCount:count,rightWidth:right,hasRoundVideo:true)
  let layout=mediaEditorBottomControlsLocalLayout(width:width,spec:spec,middleItemWidths:Array(repeating:44,count:count),middleSpacing:0,leftWidth:44,rightWidth:right)
  check(layout.leftFrame.minX>=0 && layout.rightFrame.maxX<=width,"side buttons stay inside viewport")
  check(layout.middleFrame!.minX>=layout.leftFrame.maxX && layout.middleFrame!.maxX<=layout.rightFrame.minX,"five toolbar targets never overlap back/send")
  for i in layout.itemFrames.indices {check(layout.itemFrames[i].width==44 && layout.itemFrames[i].height==44,"real 44 point targets preserved");if i>0 {check(layout.itemFrames[i-1].maxX<=layout.itemFrames[i].minX,"neighbor tool targets never overlap")}}
 }}}
 check(nagramiXRoundVideoToolbarSpec(width:320,itemCount:4,rightWidth:46,hasRoundVideo:false)==chatMediaEditorBottomControlsSpec,"ordinary toolbar retains exact native spec")
 check(nagramiXRoundVideoColumnNeedsBottom(height:268) && nagramiXRoundVideoColumnNeedsBottom(height:311),"short landscape column uses native bottom row")
 check(!nagramiXRoundVideoColumnNeedsBottom(height:312) && !nagramiXRoundVideoColumnNeedsBottom(height:600),"tall column has room for seven native targets")
 print("PASS round toolbar geometry checks: \(checks)")
}}
'''

import Foundation
#if canImport(Glibc)
import Glibc
#else
import Darwin
#endif
var checks=0
func check(_ value:@autoclosure()->Bool,_ why:String){guard value() else{FileHandle.standardError.write(Data((why+"\n").utf8));exit(96)};checks+=1}
typealias CMTimeScale=Int32
struct CMTime {
 let seconds:Double
 init(value:Int64,timescale:Int32){seconds=Double(value)/Double(timescale)}
 init(_ value:Double){seconds=value}
 static let zero=Self(0),invalid=Self(Double.nan)
}
struct CMTimeRange {let start:CMTime;let duration:CMTime}
func CMTimeRangeGetEnd(_ value:CMTimeRange)->CMTime{CMTime(value.start.seconds+value.duration.seconds)}
func CMTimeAdd(_ a:CMTime,_ b:CMTime)->CMTime{CMTime(a.seconds+b.seconds)}
func CMTimeCompare(_ a:CMTime,_ b:CMTime)->Int32{a.seconds<b.seconds ? -1 : a.seconds>b.seconds ? 1 : 0}
struct CMSampleTimingInfo {let duration:CMTime;let presentationTimeStamp:CMTime;let decodeTimeStamp:CMTime}
struct Pixel {let width:Int;let height:Int}
final class CMSampleBuffer {
 let pts:CMTime;let id:Int;let pixel:Pixel?;let count:Int;let duration:CMTime
 init(_ time:Double,_ id:Int,pixel:Pixel?=Pixel(width:848,height:477),count:Int=1,duration:Double=0){pts=CMTime(time);self.id=id;self.pixel=pixel;self.count=count;self.duration=CMTime(duration)}
}
func CMSampleBufferGetPresentationTimeStamp(_ b:CMSampleBuffer)->CMTime{b.pts}
func CMSampleBufferGetNumSamples(_ b:CMSampleBuffer)->Int{b.count}
func CMSampleBufferGetImageBuffer(_ b:CMSampleBuffer)->Pixel?{b.pixel}
let kCFAllocatorDefault=0
enum CopyIO {static var fails=false}
func CMSampleBufferCreateCopyWithNewTiming(allocator:Int,sampleBuffer:CMSampleBuffer,sampleTimingEntryCount:Int,sampleTimingArray:inout CMSampleTimingInfo,sampleBufferOut:inout CMSampleBuffer?)->Int32 {
 if CopyIO.fails{return -1}
 sampleBufferOut=CMSampleBuffer(sampleTimingArray.presentationTimeStamp.seconds,sampleBuffer.id,pixel:sampleBuffer.pixel,count:sampleBuffer.count,duration:sampleTimingArray.duration.seconds);return 0
}
class AVAssetReaderOutput {
 var values:[CMSampleBuffer];var offset=0;var reads=0;var completed=false
    var onEOF:(()->Void)?
 init(_ values:[CMSampleBuffer]){self.values=values}
 func copyNextSampleBuffer()->CMSampleBuffer?{
  reads+=1
  guard offset<values.count else{completed=true;onEOF?();return nil}
  defer{offset+=1};return values[offset]
 }
}

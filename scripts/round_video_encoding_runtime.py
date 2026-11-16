"""Execute rate policy/direct-store/validated exporter with real SignalKit and file IO.

Postbox preferences, AVFoundation metadata and the hardware encoder are explicit IO adapters.
"""
from pathlib import Path
from validate_quick_format import block
from original_video_mode_runtime import signal_library
BASE='submodules/TelegramUI/Components/MediaEditor/Sources/'
POLICY=BASE+'NagramiXRoundVideoEncodingPolicy.swift'
EXPORT=BASE+'NagramiXRoundVideoExport.swift'
VIDEO=BASE+'MediaEditorVideoExport.swift'
SCREEN='submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'
ROOT=Path(__file__).resolve().parents[1]
GEOMETRY_IMPORTS='import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'


def without_imports(value):
    return '\n'.join(line for line in value.splitlines() if not line.startswith('import '))


def fixture(source):
    code=GEOMETRY_IMPORTS+'import CoreFoundation\n'+signal_library(source)+'\n'
    if 'class Bag<' not in code and 'struct Bag<' not in code:code+='\n'+(source/'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift').read_text()
    code+='\n'+(source/'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift').read_text()+'\n'
    boundary=(ROOT/'scripts/tests/NagramiXRoundEncodingBoundary.swift').read_text()
    native=(source/VIDEO).read_text()
    for token,marker in [('PRODUCTION_ROUND_CONFIG_FLAG','        var nagramiXIsCustomRoundVideo:'),('PRODUCTION_EXPORT_ERROR','    public enum ExportError {'),('PRODUCTION_EXPORT_STATUS','    public enum ExportStatus {')]:
        boundary=boundary.replace('// '+token,block(native,marker))
    code+=boundary+'\n'+without_imports((source/POLICY).read_text())+'\n'+without_imports((source/EXPORT).read_text())+'\n'
    code+=block((source/SCREEN).read_text(),'private func storeUneditedVideoMessage(')+'\n'
    code+=block((source/'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift').read_text(),'private func nagramiXRoundVideoResourceExport(')+'\n'
    code+=(ROOT/'scripts/tests/NagramiXRoundEncodingTests.swift').read_text()
    return code


def profile_fixture(source):
    import round_editor_quality_runtime as previous
    code=previous.fixture(source).split('@main struct RoundQualityTests',1)[0]
    code=code.replace('exit(91)','exit(96)')
    code=code.replace('enum AVVideoCodecType {static let h264="h264",hevc="hevc"}', 'enum AVVideoCodecType:Equatable {case h264,hevc}')
    code+='\nlet AVVideoExpectedSourceFrameRateKey="AVVideoExpectedSourceFrameRateKey"\nlet AVVideoMaxKeyFrameIntervalKey="AVVideoMaxKeyFrameIntervalKey"\nlet AVVideoColorPropertiesKey="AVVideoColorPropertiesKey"\n'
    recorder=(source/'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift').read_text()
    a=recorder.index('        var compressionProperties: [String: Any] = [',recorder.index('private func prepareWriterIfNeeded('))
    b=recorder.index('        guard assetWriter.canApply(',a)
    fragment=recorder[a:b].replace('self.processor','processor')
    code+='struct FixtureProcessor {let quality:NagramiXRoundVideoSettings?;var outputWidth:Int{quality?.quality.rawValue ?? 480};var outputHeight:Int{outputWidth}}\nstruct FixtureFrame{let source=0}\nenum RoundVideoFrameProcessor {static func videoColorProperties(from:Int)->[String:Any]{[:]}}\n'
    code+='func actualCaptureSettings(_ quality:NagramiXRoundVideoSettings?)->[String:Any]{let processor=FixtureProcessor(quality:quality);let firstVideoFrame=FixtureFrame()\n'+fragment+'\nreturn videoSettings\n}\n'

    code+='''
@main struct RoundEncoderProfiles {
 static func main(){
  for side in [480,512,640] {for fps in [30,60] {for codec in [0,1] {for rate in [1_000_000,1_100_000,1_200_000,1_300_000] {
   let values=base().withUpdatedNagramiXRoundTuning([side,fps,codec,rate])
   let c=recommendedVideoExportConfiguration(values:values,duration:60,frameRate:120)
   let p=c.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
   check(c.videoSettings[AVVideoCodecKey] as? AVVideoCodecType == (codec==0 ? AVVideoCodecType.h264:AVVideoCodecType.hevc),"real requested H264/HEVC export codec")
   check(c.videoSettings[AVVideoWidthKey] as? Int == side && c.videoSettings[AVVideoHeightKey] as? Int == side,"real square export side")
   check(c.frameRate==Float(fps),"snapshot overrides source120FPS")
   check(p[AVVideoExpectedSourceFrameRateKey] as? Int == fps,"writer receives selected FPS")
   check(p[AVVideoAverageBitRateKey] as? Int == rate,"fixed bitrate is not multiplied by frame rate")
   if codec==0 {check(p[AVVideoH264EntropyModeKey] as? String == AVVideoH264EntropyModeCABAC,"H264 uses CABAC")}else{check(p[AVVideoH264EntropyModeKey]==nil && p[AVVideoProfileLevelKey] as? String == kVTProfileLevel_HEVC_Main_AutoLevel,"HEVC uses its own profile and no H264 entropy mode")}
   let model=NagramiXRoundVideoSettings(enabled:true,quality:.init(rawValue:side)!,frameRate:.init(rawValue:fps)!,codec:.init(rawValue:codec)!,bitRate:rate)
   let capture=actualCaptureSettings(model);let cp=capture[AVVideoCompressionPropertiesKey] as! [String:Any]
   check(capture[AVVideoCodecKey] as? AVVideoCodecType == (codec==0 ? AVVideoCodecType.h264:AVVideoCodecType.hevc),"camera selects a real codec, not a label")
   check(capture[AVVideoWidthKey] as? Int == side && capture[AVVideoHeightKey] as? Int == side,"camera output uses chosen square side")
   check(cp[AVVideoAverageBitRateKey] as? Int == rate && cp[AVVideoExpectedSourceFrameRateKey] as? Int == fps,"camera target bitrate and FPS agree")
   check((cp[AVVideoH264EntropyModeKey] != nil) == (codec==0),"HEVC camera has no H264-only properties")
  }}}}
  print("PASS actual round export profiles: \\(checks)")
 }
}
'''
    return code

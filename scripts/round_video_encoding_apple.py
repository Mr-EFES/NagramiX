"""Real policy module everywhere; full new exporter/reader APIs on iPhoneOS SDK only."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
from original_video_mode_runtime import signal_library
import round_video_encoding_runtime as rt


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    flags=[]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        flags=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*flags]
    def run(args):
        p=subprocess.run(common+[str(x) for x in args],capture_output=True,text=True,timeout=180);assert p.returncode==0,p.stdout+p.stderr
    run(['-emit-module','-parse-as-library','-module-name','NagramiXRoundEncoding','-emit-module-path',folder/'NagramiXRoundEncoding.swiftmodule',source/rt.POLICY])
    caller=folder/'caller.swift';caller.write_text('import NagramiXRoundEncoding\nfunc byteBudget(_ encoding:[String:Any]?)->Int64 {NagramiXRoundVideoEncodingPolicy(encoding:encoding).maximumSize}\n')
    run(['-typecheck','-parse-as-library','-I',folder,caller])
    report={'actual_policy_module_and_public_caller':'passed','complete_exporter_reader_apple_api':'not_run','camera_and_streaming_keys_apple_api':'not_run','full_application_sdk':'not_run','hardware_encoder':'not_run','physical_iphone':'pending'}
    if sys.platform!='darwin':
        report['reason']='Linux: real SignalKit/file IO and explicit encoder/AV metadata/Postbox adapters. No iPhoneOS encoding success claimed.'
        return report
    library='import Foundation\n'+signal_library(source)+'\n'
    if 'class Bag<' not in library and 'struct Bag<' not in library:library+='\n'+(source/'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift').read_text()
    library+='\n'+(source/'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift').read_text()
    lib=folder/'signals.swift';lib.write_text(library)
    run(['-emit-module','-parse-as-library','-module-name','SwiftSignalKit','-emit-module-path',folder/'SwiftSignalKit.swiftmodule',lib])
    native=(source/rt.VIDEO).read_text()
    host='''import Foundation
import UIKit
import AVFoundation
import VideoToolbox
import SwiftSignalKit
public enum MediaQualityPreset {case videoMessage,compressedDefault}
public struct MediaEditorValues {public var qualityPreset:MediaQualityPreset?;public var nagramiXRoundTuning:[Int]?}
public class TelegramMediaFile {}
public struct AppConfiguration {public var data:[String:Any]?;public static var defaultValue:Self{Self(data:nil)}}
public struct PreferenceEntry {public func get<T>(_ t:T.Type)->T?{nil}}
public struct PreferencesView {public var values:[Int:PreferenceEntry]}
public enum PreferencesKeys {public static let appConfiguration=1}
public class Postbox {public func preferencesView(keys:[Int])->Signal<PreferencesView,NoError>{.never()}}
final class EngineTempBoxFile {let path="/tmp/not-executed"}
final class EngineTempBox {static let shared=EngineTempBox();func tempFile(fileName:String)->EngineTempBoxFile{EngineTempBoxFile()};func dispose(_ f:EngineTempBoxFile){}}
struct Logger {static let shared=Logger();func log(_ tag:String,_ value:String){}}
public final class MediaEditorVideoExport {
 public enum Subject {case image(image:UIImage);case video(asset:AVAsset,isStory:Bool);case sticker(file:TelegramMediaFile)}
 public struct Configuration {
  public var videoSettings:[String:Any];public var audioSettings:[String:Any];public var values:MediaEditorValues;public var frameRate:Float;public var useStreamingWriter:Bool
'''+block(native,'        var nagramiXIsCustomRoundVideo:')+'''
 }
'''+block(native,'    public enum ExportError {')+block(native,'    public enum ExportStatus {')+'''
 public init(postbox:Postbox,subject:Subject,configuration:Configuration,outputPath:String){}
 public var streamingFileGrowth:((Int64,Int64)->Void)?
 public var status:Signal<ExportStatus,NoError>{.never()}
 public func cancel(){}
}
'''
    host+='\n'+block((source/'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift').read_text(),'private func nagramiXRoundVideoResourceExport(')+'\n'
    graph=folder/'graph.swift';graph.write_text(host)
    wrapper=folder/'exporter.swift';wrapper.write_text('\n'.join(l for l in (source/rt.EXPORT).read_text().splitlines() if l not in ['import TelegramCore','import Postbox']))
    run(['-typecheck','-parse-as-library','-I',folder,source/rt.POLICY,graph,wrapper])
    recorder=(source/'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift').read_text();a=recorder.index('        var compressionProperties: [String: Any] = [',recorder.index('private func prepareWriterIfNeeded('));b=recorder.index('        guard assetWriter.canApply(',a)
    capture='''import Foundation
import UIKit
import AVFoundation
import VideoToolbox
struct FixtureQuality {let bitRate:Int;let frameRate:FixtureFPS;let codec:FixtureCodec}
struct FixtureFPS {let rawValue:Int}
enum FixtureCodec {case h264,hevc}
struct FixtureProcessor {let quality:FixtureQuality?;let outputWidth=640,outputHeight=640}
struct FixtureFrame {let source=0}
enum RoundVideoFrameProcessor {static func videoColorProperties(from:Int)->[String:Any]{[:]}}
func cameraKeys(_ processor:FixtureProcessor)->[String:Any]{let firstVideoFrame=FixtureFrame()
'''+recorder[a:b].replace('self.processor','processor')+'\nreturn videoSettings\n}\n'
    cap=folder/'capture.swift';cap.write_text(capture)
    streaming=(source/(rt.BASE+'MediaEditorVideoStreamingWriter.swift')).read_text();a=streaming.index('        let compressionSettings = configuration.videoSettings');b=streaming.index('        VTCompressionSessionPrepareToEncodeFrames(session)',a)
    stream='''import AVFoundation
import VideoToolbox
final class MediaEditorVideoStreamingWriter {
 static let maxKeyFrameInterval=30
 func fail(_ text:String){}
 func keys(configuration:MediaEditorVideoExport.Configuration,sourceFrameRate:Float,session:VTCompressionSession){
'''+streaming[a:b]+'\n}\n}\n'
    st=folder/'streaming.swift';st.write_text(stream)
    run(['-typecheck','-parse-as-library','-I',folder,source/rt.POLICY,graph,wrapper,cap,st])
    report['complete_exporter_reader_apple_api']='passed: whole new production exporter/policy/reader against real UIKit/AVFoundation/CoreMedia and actual SignalKit subset; Postbox/exporter graph IO are explicit hosts'
    report['camera_and_streaming_keys_apple_api']='passed: actual capture/VT rate-property bodies, real AVFoundation/VideoToolbox keys/types; no hardware session executed'
    return report

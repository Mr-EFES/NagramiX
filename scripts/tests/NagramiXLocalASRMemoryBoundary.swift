import Foundation

// os_proc_available_memory, autorelease-pool drainage, AVFoundation decoding and
// native inference are explicit platform boundaries. Real file IO/mapping and
// the production budgets/PCM loop/recognizer orchestration execute below.
var boundaryMemory: UInt64 = 8 * 1024 * 1024 * 1024
func os_proc_available_memory() -> UInt64 { boundaryMemory }
func autoreleasepool<T>(invoking body: () throws -> T) rethrows -> T { try body() }
let AVFormatIDKey="format", AVSampleRateKey="rate", AVNumberOfChannelsKey="channels"
let AVLinearPCMBitDepthKey="bits", AVLinearPCMIsFloatKey="float", AVLinearPCMIsNonInterleaved="interleaved", AVLinearPCMIsBigEndianKey="endian"
let kAudioFormatLinearPCM=1, kCMBlockBufferNoErr:Int32=0
final class PCMBlock { let bytes:Data; var length:Int;init(_ bytes:Data,length:Int?=nil){self.bytes=bytes;self.length=length ?? bytes.count} }
final class PCMBoundary {
    static var blocks:[PCMBlock]=[]
    static var copySizes:[Int]=[]
    static var copyFailure=false
    static var readerFailure=false
    static var missingTrack=false
    static var cancelOnCopy:NagramiXTranscriptionCancellation?
    static var memoryOnCopy:UInt64?
    static func reset(_ data:[Data]){blocks=data.map{PCMBlock($0)};copySizes=[];copyFailure=false;readerFailure=false;missingTrack=false;cancelOnCopy=nil;memoryOnCopy=nil}
}
struct AVURLAsset {init(url:URL){};func tracks(withMediaType:String)->[Int]{PCMBoundary.missingTrack ? [] : [1]}}
extension String {static let audio="audio"}
enum ReaderStatus {case reading,completed,failed}
final class AVAssetReader {
    var status=ReaderStatus.reading
    init(asset:AVURLAsset)throws{}
    func canAdd(_ output:AVAssetReaderTrackOutput)->Bool{true}
    func add(_ output:AVAssetReaderTrackOutput){output.reader=self}
    func startReading()->Bool{true}
    func cancelReading(){}
}
final class AVAssetReaderTrackOutput {
    var index=0
    weak var reader:AVAssetReader?
    init(track:Int,outputSettings:[String:Any]){}
    func copyNextSampleBuffer()->PCMBlock?{
        guard index<PCMBoundary.blocks.count else {reader?.status=PCMBoundary.readerFailure ? .failed : .completed;return nil}
        defer{index+=1};return PCMBoundary.blocks[index]
    }
}
func CMSampleBufferGetDataBuffer(_ block:PCMBlock)->PCMBlock?{block}
func CMBlockBufferGetDataLength(_ block:PCMBlock)->Int{block.length}
func CMBlockBufferCopyDataBytes(_ block:PCMBlock,atOffset:Int,dataLength:Int,destination:UnsafeMutableRawPointer)->Int32 {
    PCMBoundary.copySizes.append(dataLength)
    if PCMBoundary.copyFailure{return -1}
    guard atOffset+dataLength<=block.bytes.count else{return -1}
    block.bytes.withUnsafeBytes{bytes in destination.copyMemory(from:bytes.baseAddress!.advanced(by:atOffset),byteCount:dataLength)}
    PCMBoundary.cancelOnCopy?.cancel()
    if let available=PCMBoundary.memoryOnCopy{boundaryMemory=available}
    return 0
}

final class NagramiXTranscriptionMedia {
    let directory:URL
    var audio:URL{directory.appendingPathComponent("audio.m4a")}
    init(_ directory:URL)throws{self.directory=directory;try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)}
    // ACTUAL_WITH_PCM
}
final class NagramiXWhisperModels {
    static let shared=NagramiXWhisperModels()
    var installed=true
    var activeLeases=0
    func withLease<T>(_ model:NagramiXWhisperModel,_ body:(URL)throws->T)throws->T {
        guard installed else {throw NagramiXTranscriptionFailure.missingModel}
        activeLeases+=1;defer{activeLeases-=1};return try body(URL(fileURLWithPath:"/models/"+model.fileName))
    }
}
final class NagramiXVoskModels {
    static let shared=NagramiXVoskModels()
    var path=URL(fileURLWithPath:"/missing")
    var activeLeases=0
    var hasModel=true
    func installed(_ model:NagramiXVoskModel)->Bool{hasModel}
    func withLease<T>(_ model:NagramiXVoskModel,_ body:(URL)throws->T)throws->T {
        guard hasModel else {throw NagramiXTranscriptionFailure.missingModel}
        activeLeases+=1;defer{activeLeases-=1};return try body(path)
    }
}
struct NativeBoundary {
    static var code:Int32=0
    static var calls=0
    static var destroyed=0
    static var freed=0
    static var modelPath=""
    static var language=""
    static var text="hello"
    static var beforeRun:(()->Void)?
    static func reset(){code=0;calls=0;destroyed=0;freed=0;modelPath="";language="";text="hello";beforeRun=nil}
}
func nx_whisper_create()->OpaquePointer?{OpaquePointer(bitPattern:1)}
func nx_whisper_cancel(_ pointer:OpaquePointer){}
func nx_whisper_destroy(_ pointer:OpaquePointer){NativeBoundary.destroyed+=1}
func nx_whisper_free_text(_ pointer:UnsafeMutablePointer<CChar>){NativeBoundary.freed+=1;free(pointer)}
func nx_whisper_transcribe(_ pointer:OpaquePointer,_ path:String,_ samples:UnsafePointer<Float>?,_ count:Int32,_ language:String,_ threads:Int32,_ output:UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>)->Int32 {
    NativeBoundary.calls+=1;NativeBoundary.modelPath=path;NativeBoundary.language=language;NativeBoundary.beforeRun?()
    output.pointee=strdup(NativeBoundary.text);return NativeBoundary.code
}
func nx_vosk_free_text(_ pointer:UnsafeMutablePointer<CChar>){NativeBoundary.freed+=1;free(pointer)}
func nx_vosk_transcribe(_ path:String,_ samples:UnsafePointer<Float>?,_ count:Int32,_ cancelled:(UnsafeMutableRawPointer?)->Int32,_ opaque:UnsafeMutableRawPointer?,_ output:UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>)->Int32 {
    NativeBoundary.calls+=1;NativeBoundary.modelPath=path;NativeBoundary.beforeRun?()
    output.pointee=strdup("[{\"text\":\"first\"},{\"text\":\"second\"}]");return NativeBoundary.code
}

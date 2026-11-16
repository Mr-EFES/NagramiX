private var fixtureChecks=0
private func check(_ condition:Bool,_ message:String){guard condition else{print("FAIL: "+message);exit(96)};fixtureChecks+=1}
private func configuration(side:Int=640,fps:Int=60,hevc:Bool=true,rate:Int=1_300_000,round:Bool=true)->MediaEditorVideoExport.Configuration {
 .init(videoSettings:[AVVideoCodecKey:hevc ? AVVideoCodecType.hevc:.h264,AVVideoWidthKey:side,AVVideoHeightKey:side,AVVideoCompressionPropertiesKey:[AVVideoAverageBitRateKey:rate]],audioSettings:[AVEncoderBitRateKey:64_000],values:MediaEditorValues(qualityPreset:round ? .videoMessage:.compressedDefault,nagramiXRoundTuning:round ? [side,fps,hevc ? 1:0,rate]:nil),frameRate:Float(fps))
}
private func finish(_ config:MediaEditorVideoExport.Configuration,encoding:[String:Any]?=nil,plans:[EncoderPlan],story:Bool=false)->(Bool,String,Int){
 EncoderIO.reset(plans)
 let output=EngineTempBox.shared.root+"/final-"+UUID().uuidString+".mp4"
 let exporter=nagramiXRoundVideoResourceExport(postbox:Postbox(encoding),subject:.video(asset:AVAsset(),isStory:story),configuration:config,outputPath:output)
 let growth=Atomic<Int>(value:0);exporter.streamingFileGrowth={_,_ in _ = growth.modify{$0+1}}
 let done=DispatchSemaphore(value:0),success=Atomic<Bool>(value:false)
 let disposable=exporter.status.start(next:{s in
  switch s{case .completed:_ = success.swap(true);done.signal();case .failed:done.signal();default:break}
 })
 check(done.wait(timeout:.now()+5) == .success,"export reaches a terminal status")
 disposable.dispose();exporter.cancel()
 return(success.with{$0},output,growth.with{$0})
}
@main private enum RoundEncodingTests {
 static func main(){
  defer{try? FileManager.default.removeItem(atPath:EngineTempBox.shared.root)}
  for value:Any in [true,false,"12582912",Double.nan,Double.infinity,-1,0,100,Double.greatestFiniteMagnitude] {
   let p=NagramiXRoundVideoEncodingPolicy(encoding:["max_size":value]);check(p.maximumSize==NagramiXRoundVideoEncodingPolicy.fallbackMaximumSize,"invalid server values do not overflow or erase safe default")
  }
  for maximum:Int64 in [1024,1_048_576,8_388_608,10_485_760,12_582_912,16_777_216] {
   let p=NagramiXRoundVideoEncodingPolicy(encoding:["max_size":NSNumber(value:maximum)])
   check(p.maximumSize==maximum,"account max_size is in bytes")
   check(!p.contains(size:0) && p.contains(size:maximum) && !p.contains(size:maximum+1),"measured file obeys the exact server limit")
   for rate in [1_000_000,1_100_000,1_200_000,1_300_000,1_400_000] {
    if let actual=p.videoBitRate(requested:rate){
     check(actual<=rate,"requested preset is a ceiling, not multiplied by FPS or codec")
     check(Double(actual+64_000)*60/8<=Double(maximum)*0.9+1,"full minute includes AAC and10percent reserve")
    }else{check(maximum<=1_048_576,"impossible minute budget fails instead of inventing a video")}
   }
  }
  let standard=NagramiXRoundVideoEncodingPolicy(encoding:nil)
  check(standard.videoBitRate(requested:1_300_000)==1_300_000,"normal max preset remains1300kbit")
  check(Double(1_300_000+64_000)*60/8==10_230_000,"1300kbit plus AAC is10.23MB per minute")
  check(standard.maximumEncodedSize(videoBitRate:1_300_000,duration:60)!<12_000_000,"rate-derived byte ceiling catches overshoot even with a larger server limit")
  for duration in [0.0,-1.0,Double.nan,Double.infinity,61.0] {check(standard.maximumEncodedSize(videoBitRate:1_300_000,duration:duration)==nil,"invalid or overlong encoded duration cannot be sent as a round")}

  let retry=standard.retryBitRate(current:1_300_000,actualSize:17_000_000)!
  check(retry<1_300_000 && retry>=64_000,"17MB overshoot reduces bitrate with fixed format")
  check(standard.retryBitRate(current:64_000,actualSize:17_000_000)==nil,"retry has a lower bound")
  for side in [480,512,640] {for fps in [30,60] {for hevc in [false,true] {for rate in [1_000_000,1_100_000,1_200_000,1_300_000] {
   let c=configuration(side:side,fps:fps,hevc:hevc,rate:rate)
   let result=finish(c,plans:[EncoderPlan(size:10_000)])
   check(result.0,"all48 resolution/FPS/codec/bitrate presets complete as validated videos")
   check(result.2==0,"custom round exports never expose an unchecked upload prefix")
   let received=EncoderIO.received.with{$0};check(received.count==1,"bounded valid preset needs one pass")
   let actual=received[0];check(actual.frameRate==Float(fps) && (actual.videoSettings[AVVideoWidthKey] as? Int)==side,"export preserves selected dimensions and FPS")
   check((actual.videoSettings[AVVideoCodecKey] as? AVVideoCodecType)==(hevc ? .hevc:.h264),"H264 and HEVC are distinct actual writer settings")
   let props=actual.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
   check((props[AVVideoAverageBitRateKey] as? Int)==rate,"fixed bitrate applies to the whole video stream")
   check((try? FileManager.default.attributesOfItem(atPath:result.1)[.size] as? NSNumber)?.int64Value==10_000,"validated temp file is promoted before completion")
   try? FileManager.default.removeItem(atPath:result.1)
  }}}}
  let retried=finish(configuration(),plans:[EncoderPlan(size:17_000_000),EncoderPlan(size:9_000_000)])
  check(retried.0 && retried.2==0,"oversize attempt is replaced before any media bytes are uploaded")
  let requested=EncoderIO.received.with{$0}
  check(requested.count==2,"measured17MB triggers a fresh export")
  for c in requested{check(c.frameRate==60 && (c.videoSettings[AVVideoWidthKey] as? Int)==640 && (c.videoSettings[AVVideoCodecKey] as? AVVideoCodecType) == .hevc,"size retry keeps640x640/60FPS/HEVC")}
  check(((requested[1].videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any])[AVVideoAverageBitRateKey] as! Int)<1_300_000,"retry adapts to measured overshoot")
  check(Set(EncoderIO.paths.with{$0}).count==2,"attempts use isolated owned paths")
  check(EncoderIO.paths.with{$0}.allSatisfy{!FileManager.default.fileExists(atPath:$0)},"superseded attempt files are disposed")
  try? FileManager.default.removeItem(atPath:retried.1)
  let largeLimit=finish(configuration(),encoding:["max_size":64*1024*1024],plans:[EncoderPlan(size:17_000_000),EncoderPlan(size:9_000_000)])
  check(largeLimit.0 && EncoderIO.received.with{$0.count}==2,"17MB also retries when server limit is above17MB; requested bitrate budget still applies")
  try? FileManager.default.removeItem(atPath:largeLimit.1)
  let short=finish(configuration(),plans:[EncoderPlan(size:1_000_000,duration:3),EncoderPlan(size:400_000,duration:3)])
  check(short.0 && EncoderIO.received.with{$0.count}==2,"short videos use their actual duration in byte control")
  try? FileManager.default.removeItem(atPath:short.1)
  let failure=finish(configuration(),plans:Array(repeating:EncoderPlan(size:17_000_000),count:3))
  check(!failure.0 && EncoderIO.received.with{$0.count}==3,"persistent overshoot fails after3 attempts, never sends an oversized square")
  check(!FileManager.default.fileExists(atPath:failure.1),"failed attempts never become the outgoing file")
  for plan in [EncoderPlan(size:10_000,codec:kCMVideoCodecType_H264),EncoderPlan(size:10_000,fps:30),EncoderPlan(size:10_000,side:480),EncoderPlan(size:10_000,duration:61)] {
   let invalid=finish(configuration(),plans:[plan]);check(!invalid.0,"wrong actual codec/FPS/side rejects mislabeled output")
  }
  var streaming=configuration();streaming.useStreamingWriter=true
  let fallback=finish(streaming,plans:[EncoderPlan(size:0,failure:true),EncoderPlan(size:10_000)])
  check(fallback.0 && EncoderIO.received.with{$0.count}==2,"hardware streaming refusal retries AV writer")
  check(!EncoderIO.received.with{$0.last!.useStreamingWriter},"fallback preserves codec but changes writer backend")
  try? FileManager.default.removeItem(atPath:fallback.1)
  for isStory in [false,true] {
   let ordinary=finish(configuration(round:!isStory ? false:true),plans:[EncoderPlan(size:1000)],story:isStory)
   check(ordinary.0 && ordinary.2==1,"ordinary video/story retains native progressive-upload path")
   try? FileManager.default.removeItem(atPath:ordinary.1)
  }
  let tiny=finish(configuration(),encoding:["max_size":1024],plans:[])
  check(!tiny.0 && EncoderIO.received.with{$0.isEmpty},"impossible server budget never starts hardware writer")
  let low=finish(configuration(),encoding:["max_size":8_388_608],plans:[EncoderPlan(size:1000)])
  check(low.0 && ((EncoderIO.received.with{$0[0]}.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any])[AVVideoAverageBitRateKey] as! Int)<1_000_000,"account size cap can lower encoding without changing stored slider levels")
  try? FileManager.default.removeItem(atPath:low.1)
  EncoderIO.reset([EncoderPlan(size:1000)])
  let cancelled=nagramiXRoundVideoResourceExport(postbox:Postbox(nil,never:true),subject:.video(asset:AVAsset(),isStory:false),configuration:configuration(),outputPath:EngineTempBox.shared.root+"/cancelled.mp4")
  cancelled.cancel();check(EncoderIO.received.with{$0.isEmpty},"cancelled preference wait cannot start a late writer")
  EncoderIO.reset([EncoderPlan(size:0,held:true)])
  let began=DispatchSemaphore(value:0);_ = EncoderIO.started.swap({began.signal()})
  let cancelPath=EngineTempBox.shared.root+"/active-cancel.mp4"
  let active=nagramiXRoundVideoResourceExport(postbox:Postbox(),subject:.video(asset:AVAsset(),isStory:false),configuration:configuration(),outputPath:cancelPath)
  let activeDisposable=active.status.start(next:{_ in})
  check(began.wait(timeout:.now()+5) == .success,"encoder started before cancellation test")
  active.cancel();activeDisposable.dispose();_ = EncoderIO.started.swap(nil)
  check(!FileManager.default.fileExists(atPath:cancelPath),"inflight cancellation never promotes an outgoing file")
  let source=AVAssetTrack(1920,1080,120,kCMVideoCodecType_HEVC)
  for fps:Float in [30,60] {
   let output=nagramiXRoundVideoReaderOutput(track:source,outputSettings:[:],duration:CMTime(value:60,timescale:1),frameRate:fps)
   check(output.videoComposition!.frameDuration==CMTime(value:1,timescale:Int32(fps)),"reader resamples source120FPS at selected30/60FPS")
   check(output.videoComposition!.renderSize==source.naturalSize,"reader leaves rotation/crop to the existing composer")
   check(output.videoComposition!.instructions[0].layerInstructions[0].track===source,"resampler keeps original media track")
   check(output.videoComposition!.instructions[0].layerInstructions[0].usesIdentity,"resampler does not apply preferredTransform twice")
  }
  let raw=EngineTempBox.shared.tempFile(fileName:"camera.mp4")
  _ = FileManager.default.createFile(atPath:raw.path,contents:nil)
  let handle=try! FileHandle(forWritingTo:URL(fileURLWithPath:raw.path));try! handle.truncate(atOffset:17_000_000);try! handle.close()
  var stores=0
  let rejected=storeUneditedVideoMessage(path:raw.path,hasAdjustments:false,liveUploadId:123,maximumSize:standard.maximumSize,store:{_,_ in stores+=1;return true})
  check(rejected==nil && stores==0,"camera17MB bypasses unedited fast path and must use bounded conversion")
  let native=storeUneditedVideoMessage(path:raw.path,hasAdjustments:false,liveUploadId:123,store:{_,d in stores+=1;return d.count==17_000_000})
  check(native==123 && stores==1,"disabled quality path retains existing direct store and live-upload ID")
  EngineTempBox.shared.dispose(raw)
  print("PASS round encoding budget/retry/lifecycle checks: \(fixtureChecks)")
 }
}

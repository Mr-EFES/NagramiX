@main struct GalleryRoundReaderTests {
 static func main(){
  for sourceRate in [24.0,29.97,30,60,120] {for fps:Float in [30,60] {for start in [0.0,4.125] {
   let duration=1.5
   let count=Int(ceil(duration*sourceRate))
   let input=(0..<count).map { CMSampleBuffer(start+Double($0)/sourceRate,$0) }
   let output=AVAssetReaderOutput(input)
   let sampler=NagramiXRoundVideoFrameReader(output:output,range:CMTimeRange(start:CMTime(start),duration:CMTime(duration)),frameRate:fps)!
   var frames:[CMSampleBuffer]=[]
   while let frame=sampler.copyNextSampleBuffer(){frames.append(frame);check(frames.count<=Int(duration*Double(fps))+1,"resampling terminates within requested range")}
   check(frames.count==Int(duration*Double(fps)),"selected FPS yields correct output frame count")
   check(!sampler.failed,"native decoded samples resample successfully")
   for (index,frame) in frames.enumerated(){
    let time=start+Double(index)/Double(fps)
    check(abs(frame.pts.seconds-time)<0.000001,"output timestamps follow selected FPS")
    check(abs(frame.duration.seconds-1/Double(fps))<0.000001,"sample duration follows selected FPS")
    let expected=input.last(where:{$0.pts.seconds<=time+0.0000001})?.id ?? 0
    check(frame.id==expected,"drop/duplicate preserves source content and time")
    check(frame.pixel?.width==848 && frame.pixel?.height==477,"native pixel geometry remains unchanged")
   }
   check(output.reads<=input.count+1,"source is consumed once without an extra renderer")
   check(!sampler.canReadAfterEOF,"completed decoder lease ends at requested endpoint")
  }}}
  let vfr=AVAssetReaderOutput([CMSampleBuffer(0,0),CMSampleBuffer(0.02,1),CMSampleBuffer(0.1,2),CMSampleBuffer(0.2,3)])
  let sampler=NagramiXRoundVideoFrameReader(output:vfr,range:.init(start:.zero,duration:CMTime(0.3)),frameRate:60)!
  var count=0;var hasTail=false
  while let _=sampler.copyNextSampleBuffer(){count+=1;if vfr.completed && sampler.canReadAfterEOF{hasTail=true}}
  check(count==18 && hasTail,"completed reader can still supply upsampled tail frames")
  let export=ExportHost();var exported=0
  while export.step(){exported+=1}
  check(exported==18 && !export.nagramiXRoundSamplingFailed,"actual export guard preserves tail after native reader completes")
  let ordinary=ExportHost();ordinary.configuration.nagramiXIsCustomRoundVideo=false
  var nativeFrames=0;while ordinary.step(){nativeFrames+=1}
  check(nativeFrames==3 && ordinary.nagramiXRoundSampleReader==nil,"ordinary export keeps native reader samples")
  for rate:Float in [0,24,120] {check(NagramiXRoundVideoFrameReader(output:AVAssetReaderOutput([]),range:.init(start:.zero,duration:CMTime(1)),frameRate:rate)==nil,"unsupported requested FPS rejected")}
  for input in [[],[CMSampleBuffer(Double.nan,0)],[CMSampleBuffer(0,0,pixel:nil)],[CMSampleBuffer(0,0,count:2)],[CMSampleBuffer(0.1,0),CMSampleBuffer(0,1)]] {
   let reader=NagramiXRoundVideoFrameReader(output:AVAssetReaderOutput(input),range:.init(start:.zero,duration:CMTime(1)),frameRate:30)!
   _=reader.copyNextSampleBuffer();check(reader.failed,"invalid native sample fails instead of waiting")
  }
  CopyIO.fails=true
  let reader=NagramiXRoundVideoFrameReader(output:AVAssetReaderOutput([CMSampleBuffer(0,0)]),range:.init(start:.zero,duration:CMTime(1)),frameRate:30)!
  check(reader.copyNextSampleBuffer()==nil && reader.failed,"CoreMedia copy refusal becomes terminal failure")
  print("Gallery round reader: \(checks) actual native sample scheduling checks passed; AV/CoreMedia IO hosts")
 }
}

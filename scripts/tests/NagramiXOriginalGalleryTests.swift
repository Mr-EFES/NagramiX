@main enum OriginalGalleryChecks {
 static func main(){
  DispatchQueue.global().async {
   do {try run();exit(0)} catch {print("FAIL original gallery IO: \(error)");exit(96)}
  }
  dispatchMain()
 }
 static func run() throws {
  var checks=0
  func check(_ value:Bool,_ why:String){if !value{print("FAIL: "+why);exit(96)};checks+=1}
  func setMode(_ enabled:Bool){var s=NagramiXMediaSettings.current;s.originalVideos=enabled;NagramiXMediaSettings.update(s)}
  func wait(_ result:GalleryResult){
   let deadline=Date().addingTimeInterval(5)
   while result.value==nil && Date()<deadline {
    PHAssetResourceManager.default().finish();nagramiXOriginalVideoQueue.sync{};Thread.sleep(forTimeInterval:0.003)
   }
   check(result.value != nil,"gallery produces a terminal native-pipeline result")
  }
  func item(_ id:String,thumbnail:Bool=true,values:MediaEditorValues?=nil)->ChatMediaSendItem {
   ChatMediaSendItem(uniqueId:id,source:.libraryAsset(identifier:id,pixelSize:CGSize(width:96,height:64),isVideo:true,duration:0.5),values:values,thumbnail:thumbnail ? UIImage():nil,coverImage:UIImage(),options:ChatMediaSendItemOptions(caption:NSAttributedString(string:"Caption 🎬 https://example.org"),spoiler:true),fileName:"original.mp4")
  }
  let defaults=UserDefaults.standard,old=defaults.dictionaryRepresentation().filter{$0.key.hasPrefix("nagramix.")}
  defer {
   for key in defaults.dictionaryRepresentation().keys where key.hasPrefix("nagramix."){defaults.removeObject(forKey:key)}
   for (key,value) in old{defaults.set(value,forKey:key)}
   _=defaults.synchronize()
  }
  defaults.removeObject(forKey:"nagramix.videos.original")
  check(!NagramiXMediaSettings.current.originalVideos,"fresh original-video mode is OFF")
  let mp4=Data(base64Encoded:"SYNTHETIC_MP4_BASE64")!,mov=Data(base64Encoded:"SYNTHETIC_MOV_BASE64")!
  let h264=Data(base64Encoded:"H264_60_BASE64")!,hevc=Data(base64Encoded:"HEVC_60_BASE64")!
  let sources=[("video.mp4","video/mp4",mp4), ("video.mov","video/quicktime",mov), ("video.m4v","video/m4v",mp4),("h264-60.mp4","video/mp4",h264),("hevc-60.mov","video/quicktime",hevc)]
  for (name,mime,bytes) in sources {for thumbnail in [true,false] {for hfr in [false,true] {for dual in [false,true] {
   let resource=PHAssetResource(name,mime:mime,bytes:bytes)
   let asset=PHAsset(dual ? [PHAssetResource("rendered.mov",mime:"video/quicktime",bytes:bytes==mov ? mp4:mov,full:true),resource]:[resource])
   if hfr{asset.mediaSubtypes=[.videoHighFrameRate]}
   PHAsset.registry["source"]=asset
   for enabled in [false,true,false] {
    setMode(enabled);let context=AccountContext(),result=GalleryResult(),input=item("source",thumbnail:thumbnail)
    let requestCount=PHAssetResourceManager.default().requests,compressCount=CompressionBoundary.calls
    let d=chatMediaSendMessages(context:context,items:[input],global:ChatMediaSendGlobalOptions(grouping:true,forcedCaption:NSAttributedString(string:"forced")),renderer:Renderer()).start(next:result.next)
    wait(result);let event=result.value!
    check(event.items.count==1 && event.items[0].uniqueId=="source","gallery keeps order and unique id")
    check(event.items[0].options.caption?.string==input.options.caption?.string && event.items[0].options.spoiler,"caption and spoiler remain attached")
    check(event.global.grouping && event.global.forcedCaption?.string=="forced","media album and global caption are preserved")
    if enabled {
     check(event.files.first!?.isVideo==true && event.files.first!?.resource is LocalFileMediaResource,"ON retains original playable video")
     let file=event.files[0]!
     check(!file.isInstantVideo && nativeUploadFlags(file)&(1<<4)==0,"original enters native video mode without force_file")
     check(file.size==Int64(bytes.count),"original byte length remains unchanged")
     check(file.mimeType==mime,"original MIME is retained")
     check(CompressionBoundary.calls==compressCount,"ON never reaches the compression boundary")
     check(PHAssetResourceManager.default().requests==requestCount+1,"ON fetches exactly one full Photos original")
     check(context.account.resources.moves.count==1,"original is queued as one complete local resource")
     let pinned=context.account.resources.moves[0].1
     check(try Data(contentsOf:URL(fileURLWithPath:pinned))==bytes,"selected Photos original bytes are unchanged")
     check(file.previewRepresentations.count==(thumbnail ? 1:0),"optional preview never changes media classification")
     context.account.resources.flushMoves()
     let stored=context.account.resources.paths[file.resource.id]!
     check(try Data(contentsOf:URL(fileURLWithPath:stored))==bytes,"native deferred cache move keeps original bytes")
     d.dispose()
     check(try Data(contentsOf:URL(fileURLWithPath:stored))==bytes,"completed export retains bytes after disposal")
    } else {
     if let resource=event.files[0]?.resource as? VideoLibraryMediaResource,case .compress=resource.conversion{check(true,"OFF enters standard Telegram compress route")}else{check(false,"OFF enters standard Telegram compress route")}
     check(PHAssetResourceManager.default().requests==requestCount,"OFF never exports original Photos bytes")
     check(CompressionBoundary.calls==compressCount+1,"OFF delegates to existing compression processing")
     d.dispose()
    }
   }
  }}}}
  let asset=PHAsset([PHAssetResource("source.mp4",mime:"video/mp4",bytes:mp4)]);PHAsset.registry["edited"]=asset
  for range in [0.0..<0.5,0.1..<0.4] {
   var values=MediaEditorValues();values.videoTrimRange=range;values.qualityPreset = .compressedLow
   setMode(true);let result=GalleryResult(),context=AccountContext()
   let d=chatMediaSendMessages(context:context,items:[item("edited",values:values)],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer()).start(next:result.next);wait(result)
   if range.lowerBound==0 {
    check(result.value?.files[0]?.resource is LocalFileMediaResource,"full-duration trim does not trigger recompression")
   } else {
    check(result.value?.files[0]?.resource is VideoLibraryMediaResource,"actual trim retains native edited-video processing")
   }
   context.account.resources.flushMoves();d.dispose()
  }
  do {
   setMode(true);let context=AccountContext(),result=GalleryResult()
   let d=chatMediaSendMessages(context:context,items:[item("source")],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer()).start(next:result.next)
   setMode(false);wait(result)
   check(result.value?.files[0]?.resource is LocalFileMediaResource,"active batch keeps its original-mode snapshot")
   context.account.resources.flushMoves();d.dispose()
   let next=GalleryResult();let n=chatMediaSendMessages(context:context,items:[item("source")],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer()).start(next:next.next);wait(next)
   check(next.value?.files[0]?.resource is VideoLibraryMediaResource,"next batch reads the updated OFF preference");n.dispose()
  }
  do {
   setMode(true);PHAsset.registry["bad"]=PHAsset([PHAssetResource("bad.mp4",mime:"video/mp4",bytes:Data())])
   let context=AccountContext(),result=GalleryResult(),compressCount=CompressionBoundary.calls
   let d=chatMediaSendMessages(context:context,items:[item("bad")],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer()).start(next:result.next);wait(result)
   check(result.value?.files[0]==nil && CompressionBoundary.calls==compressCount,"failed original never silently recompresses")
   check(context.account.resources.moves.isEmpty,"failed original does not enqueue a partial file");d.dispose()
  }
  do {
   setMode(true);let context=AccountContext(),result=GalleryResult(),cancels=PHAssetResourceManager.default().cancelled
   let d=chatMediaSendMessages(context:context,items:[item("source")],global:ChatMediaSendGlobalOptions(grouping:true),renderer:Renderer()).start(next:result.next)
   d.dispose();PHAssetResourceManager.default().finish();nagramiXOriginalVideoQueue.sync{};Thread.sleep(forTimeInterval:0.02)
   check(result.value==nil && context.account.resources.moves.isEmpty,"cancelled original does not publish bytes")
   check(PHAssetResourceManager.default().cancelled>cancels,"cancellation reaches Photos data request")
  }
  for thumbnail in [true,false] {for hfr in [true,false] {for trim in [0,1,2] {
   let asset=PHAsset([PHAssetResource("legacy.mp4",mime:"video/mp4",bytes:h264)])
   if hfr{asset.mediaSubtypes=[.videoHighFrameRate]}
   let adjustments=TGVideoEditAdjustments()
   if trim==1{adjustments.trimEndValue=0.5}
   if trim==2{adjustments.trimStartValue=0.1;adjustments.trimEndValue=0.4}
   let caption=NSAttributedString(string:"Legacy caption 🎬")
   let input=LegacyAssetItemWrapper(item:.video(data:.asset(TGMediaAsset(asset)),thumbnail:thumbnail ? UIImage():nil,cover:UIImage(),adjustments:adjustments,caption:caption,asFile:false,asAnimation:false,stickers:[]),timer:nil,spoiler:true,price:nil,forceHd:true,groupedId:7,uniqueId:"legacy")
   let account=Account(),result=LegacyGalleryResult(),requests=PHAssetResourceManager.default().requests
   let d=nagramiXPrepareOriginalVideoValue(account:account,value:NSDictionary(dictionary:["item":input])).start(next:result.next)
   let deadline=Date().addingTimeInterval(5)
   while result.value==nil && Date()<deadline{PHAssetResourceManager.default().finish();nagramiXOriginalVideoQueue.sync{};Thread.sleep(forTimeInterval:0.003)}
   check(result.value != nil,"legacy original preparation terminates")
   let output=(result.value as! NSDictionary)["item"] as! LegacyAssetItemWrapper
   if trim != 2 {
    if case let .originalVideo(file,savedCaption)=output.item {
     check(file.isVideo && file.size==Int64(h264.count),"legacy full clip keeps original mode")
     check(savedCaption?.string==caption.string && output.spoiler==true && output.forceHd && output.groupedId==7 && output.uniqueId=="legacy","legacy caption and send metadata remain attached")
     check(nativeUploadFlags(file)&(1<<4)==0,"legacy original stays a video instead of force_file")
     account.resources.flushMoves()
     check(try Data(contentsOf:URL(fileURLWithPath:account.resources.paths[file.resource.id]!))==h264,"legacy original keeps all source bytes")
    } else{check(false,"legacy full clip keeps original mode")}
   } else {
    check(output === input && PHAssetResourceManager.default().requests==requests,"legacy actual trim retains edited-video path")
   }
   d.dispose()
  }}}
  do {
   let asset=PHAsset([PHAssetResource("file.mp4",mime:"video/mp4",bytes:mp4)])
   let input=LegacyAssetItemWrapper(item:.video(data:.asset(TGMediaAsset(asset)),thumbnail:nil,cover:nil,adjustments:nil,caption:nil,asFile:true,asAnimation:false,stickers:[]),timer:nil,spoiler:nil,price:nil,groupedId:nil,uniqueId:"file")
   let result=LegacyGalleryResult(),requests=PHAssetResourceManager.default().requests
   let d=nagramiXPrepareOriginalVideoValue(account:Account(),value:NSDictionary(dictionary:["item":input])).start(next:result.next)
   check((result.value as? NSDictionary)?["item"] as? LegacyAssetItemWrapper === input && PHAssetResourceManager.default().requests==requests,"explicit file intent never becomes media implicitly");d.dispose()
  }
  for timer in [0,10] {
   let asset=PHAsset([PHAssetResource("timer.mp4",mime:"video/mp4",bytes:mp4)])
   let input=LegacyAssetItemWrapper(item:.video(data:.asset(TGMediaAsset(asset)),thumbnail:nil,cover:nil,adjustments:nil,caption:nil,asFile:false,asAnimation:false,stickers:[]),timer:timer,spoiler:nil,price:nil,groupedId:nil,uniqueId:"timer")
   let result=LegacyGalleryResult(),account=Account(),requests=PHAssetResourceManager.default().requests
   let d=nagramiXPrepareOriginalVideoValue(account:account,value:NSDictionary(dictionary:["item":input])).start(next:result.next)
   let deadline=Date().addingTimeInterval(5)
   while result.value==nil && Date()<deadline{PHAssetResourceManager.default().finish();nagramiXOriginalVideoQueue.sync{};Thread.sleep(forTimeInterval:0.003)}
   check(result.value != nil,"legacy timer-qualified preparation terminates")
   let output=(result.value as! NSDictionary)["item"] as! LegacyAssetItemWrapper
   if timer==0 {
    if case .originalVideo=output.item{check(true,"disabled zero timer permits original mode")}else{check(false,"disabled zero timer permits original mode")}
    account.resources.flushMoves()
   } else{check(output === input && PHAssetResourceManager.default().requests==requests,"active timers keep their existing processing")}
   d.dispose()
  }
  print("PASS original gallery byte/pipeline checks: \(checks)")
 }
}

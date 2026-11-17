@main struct GalleryRoundProfileTests {
 static func main()throws {
  let original=base()
  let defaults=UserDefaults(suiteName:"NagramiX.GalleryRound."+UUID().uuidString)!
  defaults.set(640,forKey:"nagramix.roundVideo.quality.resolution")
  defaults.set(60,forKey:"nagramix.roundVideo.quality.fps")
  defaults.set(1,forKey:"nagramix.roundVideo.quality.codec")
  defaults.set(true,forKey:"nagramix.roundVideo.quality.enabled")
  let cameraBefore=NagramiXRoundVideoSettings.read(from:defaults)
  let cameraBytes=try JSONSerialization.data(withJSONObject:defaults.dictionaryRepresentation().filter{$0.key.hasPrefix("nagramix.roundVideo.quality.")},options:.sortedKeys)
  let initial=chatMediaEditorRoundVideoValues(original)
  check(initial.nagramiXRoundTuning==[480,30,0,1_000_000],"gallery default is independent of camera preset")
  check(sameFields(original,initial,except:["nagramiXRoundTuning"]),"gallery initialization keeps all43 fields")
  for side in [480,512,640] {for fps in [30,60] {for codec in [0,1] {for rate in stride(from:1_000_000,through:1_300_000,by:100_000) {
   let picked=[side,fps,codec,rate]
   let value=initial.withUpdatedNagramiXRoundTuning(picked)
   let refreshed=chatMediaEditorRoundVideoValues(value)
   check(refreshed.nagramiXRoundTuning==picked,"toolbar/capture refresh keeps local choice")
   let config=recommendedVideoExportConfiguration(values:refreshed,duration:43.5,frameRate:24)
   check(config.videoSettings[AVVideoWidthKey] as? Int==side && config.videoSettings[AVVideoHeightKey] as? Int==side,"selected round size reaches encoder")
   check(config.frameRate==Float(fps),"selected FPS reaches encoder")
   check(config.videoSettings[AVVideoCodecKey] as? String==(codec==0 ? "h264":"hevc"),"selected codec reaches encoder")
   check((config.videoSettings[AVVideoCompressionPropertiesKey] as? [String:Any])?[AVVideoAverageBitRateKey] as? Int==rate,"selected bitrate reaches encoder")
   let restored=try JSONDecoder().decode(TuningEnvelope.self,from:JSONEncoder().encode(TuningEnvelope(picked)))
   check(restored.nagramiXRoundTuning==picked,"deferred snapshot preserves attachment choice")
   check(sameFields(initial,value,except:["nagramiXRoundTuning"]),"quality selection preserves crop/audio/entities/trim")
  }}}}
  check(chatMediaEditorRoundVideoTuning([640,60,1])==[640,60,1,1_300_000],"legacy three-field draft keeps size FPS and codec")
  check(chatMediaEditorRoundVideoTuning([640,60,1,2_000_000])==[640,60,1,1_300_000],"legacy high bitrate clamps without resetting other draft choices")
  for invalid:[Int]? in [nil,[],[999,60,1,1_300_000],[640,120,1,1_300_000],[640,60,9,1_300_000],[640,60,1,1234]] {
   check(chatMediaEditorRoundVideoTuning(invalid)==[480,30,0,1_000_000],"invalid gallery snapshot has independent safe default")
  }
  check(chatMediaEditorRoundVideoValues(base(.compressedHigh)).nagramiXRoundTuning==nil,"ordinary gallery video unchanged")
  check(chatMediaEditorVideoQualityIsEnabled(values:initial.withUpdatedVideoIsMuted(true)),"round quality stays editable for muted video")
  check(!chatMediaEditorVideoQualityIsEnabled(values:base(.compressedHigh).withUpdatedVideoIsMuted(true)),"ordinary muted quality keeps native behavior")
  var applied:[[Int]]=[]
  let sheet=nagramiXRoundQualitySheet(presentationData:PresentationData(),values:initial,updated:{applied.append($0)})
  func rows()->[NagramiXRoundQualitySheetItem]{sheet.groups[0].items.map{$0 as! NagramiXRoundQualitySheetItem}}
  check(rows().count==6,"fifth button presents four editable fields and Apply")
  rows()[1].action?();check(rows()[3].value=="640 × 640","size menu includes Maximum")
  rows()[3].action?();check(applied.isEmpty,"size choice remains draft before Apply")
  rows()[2].action?();rows()[4].action?() // bitrate Maximum1300
  rows()[3].action?();rows()[2].action?() // HEVC
  rows()[4].action?();rows()[2].action?() //60FPS
  check(rows()[1].value.contains("640"),"root shows current attachment size")
  rows()[5].action?();rows()[5].action?()
  check(applied==[[640,60,1,1_300_000]],"Apply commits selected four-field profile exactly once")
  let cancelled=nagramiXRoundQualitySheet(presentationData:PresentationData(),values:initial,updated:{applied.append($0)})
  (cancelled.groups[0].items[0] as! NagramiXRoundQualitySheetItem).close()
  check(applied.count==1 && cancelled.closes==1,"close cancels without applying")
  check(cameraBefore==NagramiXRoundVideoSettings.read(from:defaults),"editor never changes recording defaults")
  let cameraAfterBytes=try JSONSerialization.data(withJSONObject:defaults.dictionaryRepresentation().filter{$0.key.hasPrefix("nagramix.roundVideo.quality.")},options:.sortedKeys)
  check(cameraBytes == cameraAfterBytes,"recording persistence keys remain byte-identical")
  print("Gallery round profile: \(checks) actual snapshot/encoder/menu checks passed")
 }
}

@main struct RoundQualitySummaryTests {
 static func main() throws {
  let strings = PresentationStrings()
  for quality in NagramiXRoundVideoSettings.Quality.allCases { for fps in NagramiXRoundVideoSettings.FrameRate.allCases { for codec in NagramiXRoundVideoSettings.Codec.allCases { for rate in stride(from:1_000_000,through:2_000_000,by:100_000) {
   let settings=NagramiXRoundVideoSettings(enabled:true,quality:quality,frameRate:fps,codec:codec,bitRate:rate)
   let before=base().withUpdatedNagramiXRoundTuning([640,30,1,1_500_000])
   let selected=chatMediaEditorRoundVideoValues(before,settings:settings)
   let expected=[quality.rawValue,fps.rawValue,codec.rawValue,rate]
   check(selected.nagramiXRoundTuning==expected,"live editor takes all four current settings")
   check(sameFields(before,selected,except:["nagramiXRoundTuning"]),"updating quality preserves crop trim audio and all other fields")
   check(chatMediaEditorRoundVideoValues(selected,settings:settings) === selected,"unchanged layout does not allocate or replace values")
   let rows=nagramiXRoundQualityRows(values:selected,strings:strings)
   check(rows.count==5 && rows.allSatisfy{!$0.checked},"enabled summary contains exactly five informational rows")
   let preset=quality == .standard ? "Стандарт" : (quality == .high ? "Высокое" : "Максимум")
   check(rows[0].title=="Пресет" && rows[0].value==preset,"summary shows selected preset")
   check(rows[1].title=="Разрешение" && rows[1].value=="\(quality.rawValue) × \(quality.rawValue)","summary dimensions match selected square")
   check(rows[2].title=="Битрейт" && rows[2].value.contains(",") && rows[2].value.hasSuffix("Мбит/с"),"summary uses locale decimal and rate units")
   check(rows[3].title=="Кодек" && rows[3].value==(codec == .h264 ? "H.264 / AVC":"H.265 / HEVC"),"summary uses selected codec")
   check(rows[4].title=="Частота кадров" && rows[4].value=="\(fps.rawValue) кадров/с","summary uses selected FPS")
   let frozen=try JSONEncoder().encode(TuningEnvelope(selected.nagramiXRoundTuning))
   let off=chatMediaEditorRoundVideoValues(selected,settings:.init(enabled:false,quality:.maximum,frameRate:.smooth,codec:.hevc,bitRate:2_000_000))
   check(off.nagramiXRoundTuning==nil,"OFF clears previous custom tuning in live editor")
   let defaultRows=nagramiXRoundQualityRows(values:off,strings:strings)
   check(defaultRows.count==1 && defaultRows[0].checked && defaultRows[0].title=="По умолчанию Telegram","OFF summary uses native Telegram defaults")
   let native=recommendedVideoExportConfiguration(values:off,duration:40,frameRate:30)
   check(native.videoSettings[AVVideoWidthKey] as? Int == 480 && native.videoSettings[AVVideoCodecKey] as? String == "h264","OFF actually exports native round profile")
   let stored=try JSONDecoder().decode(TuningEnvelope.self,from:frozen)
   let pending=selected.withUpdatedNagramiXRoundTuning(stored.nagramiXRoundTuning)
   let output=recommendedVideoExportConfiguration(values:pending,duration:40,frameRate:24)
   check(output.videoSettings[AVVideoWidthKey] as? Int == quality.rawValue && output.videoSettings[AVVideoHeightKey] as? Int == quality.rawValue,"frozen export resolution matches popup")
   check(output.frameRate==Float(fps.rawValue),"frozen export FPS matches popup after settings changes")
   check(output.videoSettings[AVVideoCodecKey] as? String == (codec == .h264 ? "h264":"hevc"),"frozen export codec matches popup")
   let props=output.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
   check(props[AVVideoAverageBitRateKey] as? Int == rate,"frozen export bitrate matches popup")
  }}}}
  for preset:MediaQualityPreset? in [nil,.compressedHigh,.animation,.sticker,.profile] {
   let ordinary=base(preset).withUpdatedNagramiXRoundTuning([640,60,1,1_700_000])
   for enabled in [false,true] {check(chatMediaEditorRoundVideoValues(ordinary,settings:.init(enabled:enabled)) === ordinary,"ordinary media not affected")}
  }
  let stable=base();check(chatMediaEditorRoundVideoValues(stable,settings:.init(enabled:false)) === stable,"native OFF values are stable")
  var english=PresentationStrings();english.languageCode="en"
  let sample=chatMediaEditorRoundVideoValues(base(),settings:.init(enabled:true,quality:.high,frameRate:.smooth,codec:.hevc,bitRate:1_600_000))
  let en=nagramiXRoundQualityRows(values:sample,strings:english)
  check(en[0].title=="Preset" && en[1].title=="Resolution" && en[2].value=="1.6 Mbps","English summary uses localized fields and decimal")
  var german=PresentationStrings();german.languageCode="de"
  check(nagramiXRoundQualityRows(values:sample,strings:german)[2].value=="1,6 Mbit/s","German rate uses locale comma")
  print("Round quality summary production checks: \(checks)")
 }
}

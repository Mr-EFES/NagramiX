@main struct RoundBitrateLevelsTests {
 static func main() throws {
  let levels=NagramiXRoundVideoSettings.BitRateLevel.allCases
  check(levels.map(\.rawValue)==[1_000_000,1_100_000,1_200_000,1_300_000],"four exact named encoder bitrates")
  let cases:[(Int,Int)]=[(Int.min,1_000_000),(0,1_000_000),(1_049_999,1_000_000),(1_050_000,1_100_000),(1_149_999,1_100_000),(1_150_000,1_200_000),(1_249_999,1_200_000),(1_250_000,1_300_000),(1_300_000,1_300_000),(1_500_000,1_300_000),(2_000_000,1_300_000),(Int.max,1_300_000)]
  for (input,expected) in cases {
   let settings=NagramiXRoundVideoSettings(enabled:true,quality:.maximum,frameRate:.smooth,codec:.hevc,bitRate:input)
   check(settings.bitRate==expected && settings.bitRateLevel.rawValue==expected,"extreme and legacy values stay on four levels")
  }
  let suite="nagramix.round.levels."+UUID().uuidString;let defaults=UserDefaults(suiteName:suite)!
  defer{defaults.removePersistentDomain(forName:suite)}
  let prefix="nagramix.roundVideo.quality."
  check(!NagramiXRoundVideoSettings.read(from:defaults).enabled,"fresh installation remains OFF")
  check(defaults.object(forKey:prefix+"bitrate")==nil,"reading fresh settings does not write preferences")
  for (input,expected) in cases {
   defaults.set(true,forKey:prefix+"enabled");defaults.set(640,forKey:prefix+"resolution");defaults.set(60,forKey:prefix+"fps");defaults.set(1,forKey:prefix+"codec");defaults.set(input,forKey:prefix+"bitrate")
   let persisted=defaults.object(forKey:prefix+"bitrate") as? NSNumber
   let value=NagramiXRoundVideoSettings.read(from:defaults)
   check(value.enabled && value.bitRate==expected && value.quality == .maximum && value.frameRate == .smooth && value.codec == .hevc,"old saved values clamp without losing resolution FPS codec or ON")
   check((defaults.object(forKey:prefix+"bitrate") as? NSNumber)==persisted,"read migration is nondestructive")
  }
  for quality in NagramiXRoundVideoSettings.Quality.allCases {
   for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
    for codec in NagramiXRoundVideoSettings.Codec.allCases {
     for level in levels {
      let settings=NagramiXRoundVideoSettings(enabled:true,quality:quality,frameRate:fps,codec:codec,bitRate:level.rawValue)
      let values=chatMediaEditorRoundVideoValues(base(),settings:settings)
      check(values.nagramiXRoundTuning==[quality.rawValue,fps.rawValue,codec.rawValue,level.rawValue],"all capture/editor profile combinations use exact selected level")
      let configuration=recommendedVideoExportConfiguration(values:values,duration:60,frameRate:30)
      let compression=configuration.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
      check(compression[AVVideoAverageBitRateKey] as? Int == level.rawValue,"selected step reaches actual export settings")
      check(configuration.videoSettings[AVVideoWidthKey] as? Int == quality.rawValue && configuration.videoSettings[AVVideoHeightKey] as? Int == quality.rawValue,"bitrate does not change round dimensions")
      check(configuration.frameRate==Float(fps.rawValue) && configuration.videoSettings[AVVideoCodecKey] as? String == (codec == .hevc ? AVVideoCodecType.hevc : AVVideoCodecType.h264),"bitrate does not change requested FPS or codec")
      NagramiXRoundVideoSettings.update(settings,in:defaults)
      check(NagramiXRoundVideoSettings.read(from:defaults)==settings,"all four steps survive saving and reading")
      let decoded=try JSONDecoder().decode(TuningEnvelope.self,from:JSONEncoder().encode(TuningEnvelope(values.nagramiXRoundTuning)))
      check(decoded.nagramiXRoundTuning==values.nagramiXRoundTuning,"deferred format remains compatible")
     }
     for legacyRate in [1_400_000,1_500_000,1_900_000,2_000_000] {
      let values=base().withUpdatedNagramiXRoundTuning([quality.rawValue,fps.rawValue,codec.rawValue,legacyRate])
      let config=recommendedVideoExportConfiguration(values:values,duration:60,frameRate:30)
      let props=config.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
      check(props[AVVideoAverageBitRateKey] as? Int == 1_300_000,"legacy prepared job cannot exceed new ceiling")
      check(config.frameRate==Float(fps.rawValue) && config.videoSettings[AVVideoCodecKey] as? String == (codec == .hevc ? AVVideoCodecType.hevc : AVVideoCodecType.h264) && config.videoSettings[AVVideoWidthKey] as? Int == quality.rawValue,"legacy profile keeps dimensions FPS codec")
      check(values.nagramiXRoundTuning?.last==legacyRate,"prepared snapshot is not mutated")
     }
     let legacy=base().withUpdatedNagramiXRoundTuning([quality.rawValue,fps.rawValue,codec.rawValue])
     let config=recommendedVideoExportConfiguration(values:legacy,duration:60,frameRate:30)
     let expected=quality == .standard ? 1_000_000 : (quality == .high ? 1_200_000:1_300_000)
     check((config.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any])[AVVideoAverageBitRateKey] as? Int == expected,"three-element legacy snapshot stays supported")
    }
   }
  }
  let disabled=chatMediaEditorRoundVideoValues(base().withUpdatedNagramiXRoundTuning([640,60,1,1_300_000]),settings:.init(enabled:false))
  check(disabled.nagramiXRoundTuning==nil,"OFF still clears custom profile")
  let stock=recommendedVideoExportConfiguration(values:disabled,duration:60,frameRate:30)
  check(stock.frameRate==30 && stock.videoSettings[AVVideoCodecKey] as? String == AVVideoCodecType.h264,"OFF keeps Telegram native codec and frame rate")
  check(fixtureTranslations.count==71,"all languages present")
  for language in fixtureTranslations.keys.sorted() {
   fixtureLanguageCode=language;let strings=PresentationStrings()
   for level in levels {
    let title=strings.nagramiXLocalized(level.localizationKey)
    check(!title.isEmpty && !title.contains(where:{$0.isNumber}) && !title.contains("кбит") && !title.contains("Mbps"),"named levels have no numeric bitrate")
   }
   for fps in NagramiXRoundVideoSettings.FrameRate.allCases {for codec in NagramiXRoundVideoSettings.Codec.allCases {
    let text=nagramiXRoundQualitySubtitle(.init(frameRate:fps,codec:codec),strings:strings)
    check(text.contains(String(fps.rawValue)) && text.contains(codec == .h264 ? "H.264":"H.265") && !text.contains("%") && !text.contains("1000") && !text.contains("Мбит"),"all localized profile subtitles omit bitrate")
   }}
  }
  fixtureLanguageCode="ru"
  check(levels.map{PresentationStrings().nagramiXLocalized($0.localizationKey)}==["Стандарт","Средний","Высокий","Максимум"],"exact approved Russian names")
  print("Round bitrate model/export/localization checks: \(checks)")
 }
}

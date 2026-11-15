var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Round compact: "+message+"\n").utf8));exit(96)};checks+=1}
@main struct Tests {
 static func main() {
  defer{fixtureDefaults.removePersistentDomain(forName:fixtureSuite)}
  let page=Page()
  let fresh=NagramiXRoundVideoSettings.current
  check(!fresh.enabled && !fresh.cinematic,"fresh OFF defaults")
  for quality in NagramiXRoundVideoSettings.Quality.allCases {
   page.cinematicModes[quality.rawValue*100+30]=true
  }
  for quality in NagramiXRoundVideoSettings.Quality.allCases {
   for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
    for codec in NagramiXRoundVideoSettings.Codec.allCases {
     for bitrate in NagramiXRoundVideoSettings.BitRateLevel.allCases {
      let base=NagramiXRoundVideoSettings(enabled:true,quality:quality,frameRate:fps,codec:codec,bitRate:bitrate.rawValue)
      NagramiXRoundVideoSettings.update(base,in:fixtureDefaults)
      page.showsCinematic=page.shouldShowCinematic(base)
      check(page.numberOfSections(in:page.table)==(fps == .standard ? 5:4),"cinematic visibility follows current FPS")
      for section in [NagramiXRoundQualitySection.quality,.frameRate,.codec,.cinematic] {
       let options=page.options(section,value:base)
       check(options.count==(section == .quality ? 3:2),"horizontal option counts")
       check(options.filter{$0.selected}.count==1,"one selection per group")
       check(page.tableView(page.table,numberOfRowsInSection:section.rawValue)==1,"one physical row")
       check(page.tableView(page.table,titleForHeaderInSection:section.rawValue)==page.tableView(page.table,titleForHeaderInSection:section.rawValue)?.uppercased(),"uppercase header")
       for index in options.indices {
        NagramiXRoundVideoSettings.update(base,in:fixtureDefaults)
        page.showsCinematic=page.shouldShowCinematic(base)
        var expected=base
        switch section {
        case .quality:expected.quality=NagramiXRoundVideoSettings.Quality.allCases[index]
        case .frameRate:expected.frameRate=NagramiXRoundVideoSettings.FrameRate.allCases[index]
        case .codec:expected.codec=NagramiXRoundVideoSettings.Codec.allCases[index]
        case .cinematic:expected.cinematic=fps == .standard && index==0
        case .bitRate:break
        }
        page.select(section,index:index)
        check(NagramiXRoundVideoSettings.current==expected,"correct routing preserves other fields")
       }
      }
      NagramiXRoundVideoSettings.update(base,in:fixtureDefaults)
      page.updateBitRate(1_300_000)
      var maximum=base;maximum.bitRate=1_300_000
      check(NagramiXRoundVideoSettings.current==maximum,"bitrate event retains quality FPS codec")
      let stored=NagramiXRoundVideoSettings.current,changes=page.changes
      for section in [NagramiXRoundQualitySection.quality,.frameRate,.codec,.cinematic,.bitRate] {
       page.select(section,index:-1);page.select(section,index:99)
      }
      check(NagramiXRoundVideoSettings.current==stored && page.changes==changes,"invalid and stale indices are inert")
      page.tableView(page.table,didSelectRowAt:IndexPath(section:0,row:0))
      check(NagramiXRoundVideoSettings.current==stored,"row background does not pick an option")
     }
    }
   }
  }
  var base=NagramiXRoundVideoSettings(enabled:true,quality:.standard,frameRate:.standard,codec:.hevc,cinematic:true,bitRate:1_200_000)
  NagramiXRoundVideoSettings.update(base,in:fixtureDefaults);page.showsCinematic=true
  page.cinematicModes[640*100+30]=false
  check(!page.options(.quality,value:base)[2].enabled,"unsupported quality disabled while cinematic active")
  page.select(.quality,index:2)
  check(NagramiXRoundVideoSettings.current==base,"unsupported cinematic quality cannot be chosen")
  page.select(.frameRate,index:1)
  check(!NagramiXRoundVideoSettings.current.cinematic && !page.showsCinematic && page.table.deleted.last==4,"60 FPS clears and removes cinematic")
  page.select(.cinematic,index:0)
  check(!NagramiXRoundVideoSettings.current.cinematic,"stale cinema callback cannot enable at 60")
  page.select(.frameRate,index:0)
  check(page.showsCinematic && page.table.inserted.last==4,"return to supported 30 inserts cinematic")
  page.select(.cinematic,index:1)
  check(!NagramiXRoundVideoSettings.current.cinematic,"No keeps cinematic OFF")
  page.select(.quality,index:2)
  check(!page.showsCinematic && NagramiXRoundVideoSettings.current.quality == .maximum,"unsupported size hides cinema when OFF")
  page.select(.cinematic,index:0)
  check(!NagramiXRoundVideoSettings.current.cinematic,"unsupported device cannot enable cinematic")
  base.enabled=false;NagramiXRoundVideoSettings.update(base,in:fixtureDefaults)
  let changes=page.changes
  for section in [NagramiXRoundQualitySection.quality,.frameRate,.codec,.cinematic] {
   check(page.options(section,value:base).allSatisfy{!$0.enabled},"master OFF disables all segments")
   page.select(section,index:0);page.select(section,index:1)
  }
  page.updateBitRate(1_300_000)
  check(NagramiXRoundVideoSettings.current==base && page.changes==changes,"master OFF blocks delayed events")
  print("\(checks) compact page production checks passed")
 }
}

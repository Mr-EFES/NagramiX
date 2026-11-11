import Foundation

private var fontChecks=0
private func checkFont(_ value:Bool,_ label:String){fontChecks+=1;if !value {fputs("Font regression: \(label)\n",stderr);exit(96)}}
@main struct AppFontSelectionTests {
 static func select(_ id:String){NagramiXFontSettings.update{$0.enabled=true;$0.fontId=id}}
 static func main(){
  let keys=["nagramix.fonts.enabled","nagramix.fonts.selection.v1"]
  let saved=keys.map{UserDefaults.standard.object(forKey:$0)}
  for key in keys {UserDefaults.standard.removeObject(forKey:key)}
  defer {for(i,key)in keys.enumerated(){if let value=saved[i]{UserDefaults.standard.set(value,forKey:key)}else{UserDefaults.standard.removeObject(forKey:key)}}}
  let suite=UserDefaults(suiteName:"nagramix.fonts.fixture")!;suite.removePersistentDomain(forName:"nagramix.fonts.fixture")
  checkFont(NagramiXFontSettings.read(from:suite)==NagramiXFontSettings(),"fresh default is native and enabled")
  checkFont(Font.regular(17).fontName=="System","fresh default is native and enabled")
  checkFont(UIFont.installed==1,"factory initialization is once only")
  checkFont(Set(NagramiXFontEntry.catalog.map{$0.id}).count==32,"catalog identities are unique")
  suite.set(false,forKey:keys[0]);suite.set("ios.georgia",forKey:keys[1]);let off=NagramiXFontSettings.read(from:suite)
  checkFont(!off.enabled && off.fontId=="ios.georgia","saved OFF and selection survive fresh reader")
  suite.set("unknown-font",forKey:keys[1]);checkFont(NagramiXFontSettings.read(from:suite).fontId=="system","unknown identifier safely uses native")
  checkFont(suite.string(forKey:keys[1])=="unknown-font","unknown saved key is not rewritten on read")
  select("ios.georgia");let first=Font.with(size:19)
  checkFont(first.fontName=="Georgia" && first.pointSize==19,"selected family covers composed factory")
  select("ios.arial");checkFont(Font.with(size:19).fontName=="ArialMT","changing family invalidates cached selection")
  NagramiXFontSettings.update{$0.enabled=false};checkFont(Font.regular(17).fontName=="System","OFF restores upstream font")
  checkFont(NagramiXFontSettings.current.fontId=="ios.arial","OFF keeps remembered family")
  NagramiXFontSettings.update{$0.enabled=true};checkFont(Font.medium(17).fontName=="ArialMT","ON restores remembered family")
  checkFont(Font.with(size:17,design:.monospace).fontName=="System" && Font.with(size:17,design:.monospace).fontDescriptor.design == .monospaced,"semantic code preserves native monospace")
  checkFont(Font.monospace(18).fontName=="Menlo-Regular" && Font.monospace(18).pointSize==17,"native monospace helpers keep upstream sizing")
  checkFont(Font.semiboldItalicMonospace(18).fontName=="Menlo-BoldItalic","code bold italic remains semantic")
  checkFont(Font.with(size:18,design:.camera).fontName.hasPrefix("SFCamera"),"camera design remains native")
  let italic=Font.with(size:18,weight:.bold,traits:[.italic])
  checkFont(italic.fontName=="ArialMT" && italic.fontDescriptor.symbolicTraits.contains(.traitItalic),"selected family keeps italic trait")
  checkFont(italic.fontDescriptor.symbolicTraits.contains(.traitBold),"selected family keeps bold trait")
  for create in [Font.regular,Font.medium,Font.semibold,Font.bold,Font.heavy,Font.light,Font.semiboldItalic,Font.mediumItalic,Font.italic] {
   checkFont(create(15).fontName=="ArialMT","all standard factories use selection")
  }
  let features=Font.with(size:15,weight:.semibold,width:.condensed,traits:[.monospacedNumbers,.alternateDollarSign])
  let values=features.fontDescriptor.attributes[.featureSettings] as? [[String:Any]] ?? []
  checkFont(values.contains{($0[UIFontDescriptor.FeatureKey.type.rawValue] as? Int)==kNumberSpacingType},"number feature remains enabled")
  checkFont(values.contains{($0[kCTFontOpenTypeFeatureTag] as? String)=="cv09"},"currency feature remains enabled")
  let traits=features.fontDescriptor.attributes[.traits] as? [UIFontDescriptor.TraitKey:Any]
  checkFont((traits?[.weight] as? UIFont.Weight) == .semibold && (traits?[.width] as? UIFont.Width) == .condensed,"width does not overwrite weight")
  checkFont(features.fontDescriptor.attributes[.cascadeList] != nil,"missing glyphs retain native cascade")
  for(id,design)in [("system.rounded",UIFontDescriptor.SystemDesign.rounded),("system.serif",.serif),("system.monospace",.monospaced)] {
   select(id);checkFont(Font.regular(17).fontDescriptor.design==design,"system designs resolve through native descriptors")
  }
  for prefix in ["astra-sans","astra-serif","roboto"] {
   select("bundled."+prefix)
   let name=prefix=="astra-sans" ? "PTAstraSans" : prefix=="astra-serif" ? "PTAstraSerif" : "Roboto"
   checkFont(Font.regular(17).fontName==name+"-Regular","bundled regular face matches pinned font")
   checkFont(Font.bold(17).fontName==name+"-Bold","bundled bold face matches pinned font")
   checkFont(Font.italic(17).fontName==name+"-Italic","bundled italic face matches pinned font")
   checkFont(Font.semiboldItalic(17).fontName==name+"-BoldItalic","bundled bold italic face matches pinned font")
  }
  checkFont(Font.light(17).fontName=="Roboto-Light" && Font.heavy(17).fontName=="Roboto-Black","Roboto weight range preserved")
  select("ios.georgia")
  let preview=NagramiXFontManager.previewFont(.entry("ios.arial"),size:22)
  checkFont(preview.fontName=="ArialMT" && NagramiXFontSettings.current.fontId=="ios.georgia","preview uses row face without changing selection")
  checkFont(NagramiXFontManager.missingCharacters(.entry("ios.futura"),sample:"Аа Бб"),"missing Cyrillic gets truthful fallback label")
  checkFont(!NagramiXFontManager.missingCharacters(.entry("ios.arial"),sample:"Аа Бб"),"supported script does not get false fallback")
  UIFont.unavailable.insert("Didot");checkFont(!NagramiXFontManager.available(.entry("ios.didot")),"unavailable iOS fonts are excluded")
  NagramiXFontManager.withNativeFonts {
   checkFont(NagramiXFontManager.font(size:17)==nil,"native scope bypasses substitution")
   NagramiXFontManager.withNativeFonts {checkFont(NagramiXFontManager.font(size:17)==nil,"nested native scope remains native")}
   checkFont(NagramiXFontManager.font(size:17)==nil,"nested native scope restores parent")
  }
  checkFont(NagramiXFontManager.font(size:17)?.fontName=="Georgia","native scope restores thread state")
  let semaphore=DispatchSemaphore(value:0)
  NagramiXFontManager.withNativeFonts {
   DispatchQueue.global().async {if Font.regular(16).fontName=="Georgia" {semaphore.signal()}}
   checkFont(semaphore.wait(timeout:.now()+3) == .success,"native bypass is confined to its thread")
  }
  DispatchQueue.concurrentPerform(iterations:128){i in _=Font.with(size:CGFloat(10+i%18),weight:.bold,traits:i%2==0 ? [.italic] : [])}
  checkFont(Font.regular(17).fontName=="Georgia" && UIFont.installed==1,"concurrent font requests remain stable")
  checkFont(NagramiXFontManager.font(size:.nan)==nil && NagramiXFontManager.font(size:0)==nil,"invalid sizes fail safely")
  suite.removePersistentDomain(forName:"nagramix.fonts.fixture")
  print("App font selection checks: \(fontChecks)")
 }
}

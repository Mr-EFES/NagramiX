@main struct SettingsGlassSlidersTests {
 static func main(){
  var checks=0
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  func close(_ a:CGFloat,_ b:CGFloat)->Bool{abs(a-b)<0.00001}
  for available in [false,true] {for dark in [false,true] {
   fixtureGlassAvailable=available
   let slider=NagramiXGlassSlider(frame:CGRect(x:0,y:0,width:280,height:44))
   slider.updateAppearance(isDark:dark,background:.black,foreground:.clear)
   check(slider.intrinsicContentSize.height>=44,"native controls keep a forty-four point height")
   check(slider.minimumTrackTintColor?.alpha==0 && slider.maximumTrackTintColor?.alpha==0,"native opaque decoration is hidden")
   check(slider.images.count==3 && slider.images.values.allSatisfy{!$0.isOpaque && $0.size==CGSize(width:28,height:28)},"all native thumb states use the clear twenty-eight point image")
   let glass=slider.glassThumbView;glass.layoutSubviews()
   check((glass.effectView != nil)==available,"native glass and transparent fallback initialize")
   check(!glass.isUserInteractionEnabled && glass.accessibilityElementsHidden,"decoration cannot intercept gestures or accessibility")
   check(glass.backgroundColor!.alpha<0.03,"glass remains transparent in both themes")
   if let effect=glass.effectView {check(effect.overrideUserInterfaceStyle==(dark ? .dark:.light),"glass uses application theme")}
   for direction in [UIUserInterfaceLayoutDirection.leftToRight,.rightToLeft] {slider.effectiveUserInterfaceLayoutDirection=direction
    for limits:(Float,Float,Float) in [(0,1,0.1),(0,10,1),(0,100,5)] {
     slider.minimumValue=limits.0;slider.maximumValue=limits.1
     for index in 0...20 {
      let value=limits.0+(limits.1-limits.0)*Float(index)/20
      slider.value=value;slider.layoutSubviews()
      let expected=slider.thumbRect(forBounds:slider.bounds,trackRect:slider.trackRect(forBounds:slider.bounds),value:value)
      check(glass.frame==expected,"glass follows the actual native thumb rectangle")
      check(glass.frame.minX>=0 && glass.frame.maxX<=slider.bounds.width,"native thumb endpoints stay inside the row")
      check(close(slider.trackForegroundView.frame.width,slider.trackBackgroundView.frame.width*CGFloat(index)/20),"native track follows its own range")
      if direction == .rightToLeft {check(close(slider.trackForegroundView.frame.maxX,slider.trackBackgroundView.frame.maxX),"right-to-left track fills from the correct edge")}
      check(slider.value==value,"drawing does not change stored parameter")
     }
     slider.setValue(limits.2,animated:true);check(slider.value==limits.2 && glass.frame==slider.thumbRect(forBounds:slider.bounds,trackRect:slider.trackRect(forBounds:slider.bounds),value:limits.2),"animated snap updates value and glass together")
    }
   }
   slider.isEnabled=false;slider.layoutSubviews();check(glass.alpha==0.35 && !slider.isEnabled,"disabled decoration remains disabled and dim")
   slider.isEnabled=true;slider.layoutSubviews();check(glass.alpha==1,"reenabling restores normal material")
  }}
  fixtureGlassAvailable=true
  for width:CGFloat in [230,320,390,768] {for inset:CGFloat in [0,20,44] {for font:CGFloat in [15,17,30] {
   let params=ListViewItemLayoutParams(width:width,leftInset:inset,rightInset:inset)
   for value in stride(from:0,through:100,by:5) {
    var committed:[Int]=[];let node=NagramiXPercentageItemNode();node.didLoad()
    node.asyncLayout()(NagramiXPercentageItem(title:"Параметр",value:value,fontSize:font,updated:{committed.append($0)}),params,ItemListNeighbors()).1()
    let slider=node.sliderView!;slider.layoutSubviews()
    check(node.minimumLabel.frame.minX==inset+16 && node.maximumLabel.frame.maxX==width-inset-15,"percentage labels share the native row edges")
    check(slider.value==CGFloat(value) && node.valueLabel.text=="\(value)%","percentage values survive layout")
    slider.value=0;slider.layoutSubviews();check(close(slider.frame.minX+slider.knobView!.frame.minX,inset+16),"percentage minimum thumb fits the common edge")
    slider.value=100;slider.layoutSubviews();check(close(slider.frame.minX+slider.knobView!.frame.maxX,width-inset-15),"percentage maximum thumb fits the common edge")
    check(slider.trackForegroundView.frame.width==slider.trackBackgroundView.frame.width,"maximum percentage fills whole track")
    check(slider.knobImage?.isOpaque==false,"percentage uses shared transparent material")
    slider.interactionBegan?();slider.value=43;node.sliderValueChanged();node.updateControls()
    check(slider.value==43 && committed.isEmpty,"held percentage is not reset or saved by layout")
    slider.interactionEnded?();check(committed==[43],"percentage commits its own normalized value on release")
    slider.value=CGFloat(value);slider.accessibilityIncrement();check(slider.value==CGFloat(min(100,value+5)),"percentage VoiceOver keeps five percent step")
   }
   var committed:[Int]=[];let density=NagramiXSnowDensityItemNode();density.didLoad()
   density.asyncLayout()(NagramiXSnowDensityItem(title:"Плотность",value:75,fontSize:font,updated:{committed.append($0)}),params,ItemListNeighbors()).1()
   let slider=density.sliderView!
   for value in stride(from:10,through:100,by:5) {slider.density=value;slider.layoutSubviews();check(slider.density==value && slider.value==CGFloat(value-10),"snow retains zero-based legacy adapter and stored density")}
   slider.interactionBegan?();slider.value=43;density.sliderValueChanged();density.updateControls()
   check(slider.value==43 && committed.isEmpty,"held snow density survives external layout")
   slider.interactionEnded?();check(committed==[55],"snow still commits density on release")
  }}}
  let round=NagramiXRoundBitRateCell(presentationData:PresentationData());var rates:[Int]=[];round.changed={rates.append($0)}
  for step in 0...10 {
   var settings=NagramiXRoundVideoSettings();settings.bitRate=NagramiXRoundVideoSettings.minimumBitRate+step*NagramiXRoundVideoSettings.bitRateStep
   round.update(settings);round.valueChanged()
   check(rates.last==settings.bitRate,"bitrate mapping retains all eleven discrete saved values")
   round.slider.isTracking=true;round.slider.value=Float(step)+0.2;round.valueChanged();let raw=round.slider.value;round.update(settings)
   check(round.slider.value==raw,"held bitrate stays continuous through model update")
   round.slider.isTracking=false;round.sliderTrackingEnded();check(round.slider.value==Float(step),"bitrate snaps only after release")
  }
  var disabled=NagramiXRoundVideoSettings();disabled.enabled=false;round.update(disabled);round.slider.layoutSubviews()
  check(!round.slider.isEnabled && round.slider.glassThumbView.alpha==0.35,"quality checkbox disables glass bitrate")
  let asr=FixtureASR();let asrCell=UITableViewCell(style:.default,reuseIdentifier:nil);asr.configure(asrCell)
  let asrStack=asrCell.contentView.subviews.compactMap{$0 as? UIStackView}.first!
  let asrSlider=asrStack.arrangedSubviews.compactMap{$0 as? NagramiXGlassSlider}.first!
  let translation=FixtureTranslation();let translationCell=UITableViewCell(style:.default,reuseIdentifier:nil)
  translation.configureTemperature(translationCell,provider:NagramiXTranslationProvider());let translated=translation.temperatureSlider! as! NagramiXGlassSlider
  for step in 0...10 {
   let input=Float(step)/10
   asrSlider.value=input;asr.temperatureChanged(asrSlider);translated.value=input;translation.temperatureMoved(translated)
   check(abs(asr.selectedTemperature-Double(input))<0.000001,"transcription retains tenths and current draft")
   check(abs(translation.draftTemperature-Double(input))<0.000001,"translation retains tenths and current draft")
   check(asrSlider.minimumValue==0 && asrSlider.maximumValue==1 && translated.minimumValue==0 && translated.maximumValue==1,"temperature keeps the native zero-to-one range")
   check(asr.temperatureLabel?.text=="Температура: \(step*10)%" && translation.temperatureLabel?.text=="Температура: \(step*10)%","temperature labels remain synchronized")
  }
  translation.draftModel="managed";let cell=UITableViewCell(style:.default,reuseIdentifier:nil);translation.configureTemperature(cell,provider:NagramiXTranslationProvider())
  check(translation.temperatureSlider?.isEnabled==false && translation.temperatureLabel?.text=="Температура: управляется моделью","model eligibility still disables temperature")
  print("PASS \(checks) shared glass/control/consumer checks; UIKit native geometry/gestures/AutoLayout and model hosts are explicit boundaries")
 }
}

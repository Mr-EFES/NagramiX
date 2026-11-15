var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Round bitrate control: "+message+"\n").utf8));exit(96)};checks+=1}
@main struct RoundBitrateControlTests {
 static func main() {
  let cell=NagramiXRoundBitRateCell(presentationData:PresentationData())
  let slider=cell.slider
  slider.bounds=CGRect(x:0,y:0,width:300,height:44)
  var sent:[Int]=[];cell.changed={rate in sent.append(rate)};slider.action={cell.valueChanged()}
  for index in 0...3 {
   let value=NagramiXRoundVideoSettings(enabled:true,bitRate:1_000_000+index*100_000)
   cell.update(value)
   check(slider.value==Float(index) && slider.maximumValue==3 && slider.accessibilityStep==1,"four fixed positions")
   check(cell.titleLabel.text==cell.levelLabels[index].text && slider.accessibilityValue==cell.titleLabel.text,"visible and VoiceOver values are the selected name")
   slider.accessibilityIncrement()
   check(slider.value==Float(min(index+1,3)),"VoiceOver increments exactly one step")
   slider.accessibilityDecrement()
   check(slider.value==Float(index==3 ? 2:index),"VoiceOver decrements exactly one step")
  }
  check(sent.allSatisfy{[1_000_000,1_100_000,1_200_000,1_300_000].contains($0)},"no callback can produce an intermediate or unsafe bitrate")
  for raw:Float in [-1,0,0.49,0.5,1,1.5,2.5,3,20] {
   slider.value=raw;cell.valueChanged();check((0...3).contains(slider.value) && slider.value.rounded()==slider.value,"drag snaps even while tracking")
  }
  let previous=sent.count;slider.value=Float.nan;cell.valueChanged();cell.sliderTrackingEnded();check(sent.count==previous,"nonfinite gesture is ignored")
  for rtl in [false,true] {
   slider.effectiveUserInterfaceLayoutDirection=rtl ? .rightToLeft:.leftToRight
   for index in 0...3 {
    slider.value=0;let track=slider.trackRect(forBounds:slider.bounds);let thumb=slider.thumbRect(forBounds:slider.bounds,trackRect:track,value:Float(index))
    let gesture=UITapGestureRecognizer(target:cell,action:"fixture");gesture.locationValue=CGPoint(x:thumb.midX,y:22)
    cell.sliderTapped(gesture);check(slider.value==Float(index) && sent.last==1_000_000+index*100_000,"tap chooses the correct visual stop in both directions")
   }
   cell.update(.init(enabled:true,bitRate:1_300_000));cell.layoutSubviews()
   check(cell.stopViews[3].isHidden && cell.stopViews.filter{!$0.isHidden}.count==3,"glass thumb replaces selected tick")
   let centers=cell.stopViews.map{$0.frame.midX}
   check(rtl ? centers[0]>centers[3]:centers[0]<centers[3],"ticks follow native RTL geometry")
  }
  cell.update(.init(enabled:false));let before=sent.count
  slider.value=2;cell.valueChanged();slider.accessibilityIncrement();cell.sliderTrackingEnded();check(sent.count==before,"master OFF ignores stale gestures and accessibility actions")
  let ordinary=NagramiXGlassSlider(frame:.zero);ordinary.accessibilityIncrement();ordinary.accessibilityDecrement()
  check(ordinary.nativeIncrements==1 && ordinary.nativeDecrements==1,"other sliders keep native accessibility behavior")
  for language in fixtureTranslations.keys.sorted() {
   fixtureLanguageCode=language
   let translated=NagramiXRoundBitRateCell(presentationData:PresentationData())
   translated.update(.init(enabled:true,bitRate:1_300_000))
   check(translated.levelLabels.count==4 && translated.levelLabels.allSatisfy{$0.numberOfLines==0},"all four captions can wrap in every language")
   check(translated.titleLabel.text==fixtureTranslations[language]!["NagramiX.RoundVideo.Bitrate.Maximum"],"localized selected level stays consistent")
  }
  print("Round bitrate control checks: \(checks)")
 }
}

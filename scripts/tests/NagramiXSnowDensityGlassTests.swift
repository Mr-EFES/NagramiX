@main struct SnowDensityGlassTests {
 static func main(){
  var checks=0
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  func close(_ a:CGFloat,_ b:CGFloat)->Bool{abs(a-b)<0.00001}
  for width:CGFloat in [230,280,320,390,430,768] {for safe:CGFloat in [0,20,44] {for font:CGFloat in [15,17,23,30] {for title in ["Плотность",String(repeating:"Плотность снега ",count:6)] {
   var committed:[Int]=[]
   let node=NagramiXSnowDensityItemNode();node.didLoad()
   let params=ListViewItemLayoutParams(width:width,leftInset:safe,rightInset:safe)
   let item=NagramiXSnowDensityItem(title:title,value:75,fontSize:font,updated:{committed.append($0)})
   let result=node.asyncLayout()(item,params,ItemListNeighbors());result.1()
   let slider=node.sliderView!;slider.layoutSubviews()
   let left=16+safe,right=width-safe-15
   check(close(node.titleLabel.frame.minX,left),"density title shares native switch left edge")
   check(close(node.valueLabel.frame.maxX,right),"density value shares native switch right edge")
   check(close(node.minimumLabel.frame.minX,left) && close(node.maximumLabel.frame.maxX,right),"range labels align with switch rows")
   check(close(slider.frame.minX+slider.trackBackgroundView.frame.minX,left) && close(slider.frame.minX+slider.trackBackgroundView.frame.maxX,right),"full visible track shares row content width")
   check(slider.frame.height>=44,"slider preserves 44pt touch height")
   check(result.0.contentSize.height>=node.maximumLabel.frame.maxY+7.9,"long title and range labels fit row height")
   check(slider.minimumValue==0 && slider.maximumValue==90 && slider.startValue==0,"zero-based legacy adapter retains correct positions")
   check(node.valueLabel.text=="75%" && slider.accessibilityValue=="75%","saved density is displayed in percent")
   slider.density=10;slider.layoutSubviews()
   check(close(slider.frame.minX+slider.knobView!.frame.minX,left),"minimum thumb stays within shared left edge")
   check(slider.trackForegroundView.frame.width==0,"minimum does not invent track progress")
   slider.density=100;slider.layoutSubviews()
   check(close(slider.frame.minX+slider.knobView!.frame.maxX,right),"maximum thumb stays within shared right edge")
   check(slider.trackForegroundView.frame.width==slider.trackBackgroundView.frame.width,"100 percent fills the entire visible track")
   check(slider.knobImage!.size==CGSize(width:28,height:28) && !slider.knobImage!.isOpaque,"native knob image is clear rather than white")
   check(!slider.glassThumbView.isUserInteractionEnabled && !slider.glassThumbView.isAccessibilityElement && slider.glassThumbView.accessibilityElementsHidden,"glass decoration never steals touch or VoiceOver")
   check(slider.point(inside:CGPoint(x:-6.5,y:22),with:nil),"visible left track is tappable")
   check(slider.point(inside:CGPoint(x:slider.bounds.width+6.5,y:22),with:nil),"visible right track is tappable")
   check(!slider.point(inside:CGPoint(x:-8,y:22),with:nil),"expanded hit area stays within row content")
   slider.interactionBegan?();slider.value=43;node.sliderValueChanged()
   check(node.valueLabel.text=="55%" && committed.isEmpty,"drag previews snapped density without committing every layout")
   node.updateControls()
   check(slider.value==43,"external layout cannot reset held slider")
   slider.interactionEnded?();check(committed==[55],"release commits displayed stored density once")
  }}}}
  for value in stride(from:10,through:100,by:5) {
   let node=NagramiXSnowDensityItemNode();node.didLoad();var committed:[Int]=[]
   let item=NagramiXSnowDensityItem(title:"Плотность",value:value,updated:{committed.append($0)})
   node.asyncLayout()(item,ListViewItemLayoutParams(width:390,leftInset:21,rightInset:21),ItemListNeighbors()).1()
   let slider=node.sliderView!;check(slider.density==value && slider.value==CGFloat(value-10),"all nineteen stored densities round-trip")
   node.sliderValueChanged();check(committed.isEmpty,"unchanged density is not written again")
   slider.accessibilityIncrement();check(slider.density==min(100,value+5),"VoiceOver increment is five percent")
   slider.density=value;slider.accessibilityDecrement();check(slider.density==max(10,value-5),"VoiceOver decrement is five percent")
  }
  for available in [false,true] {
   fixtureGlassAvailable=available
   let glass=NagramiXSnowDensityGlassThumbView(frame:CGRect(x:0,y:0,width:28,height:28));glass.layoutSubviews()
   check((glass.effectView != nil)==available,"native glass and older-system fallback both initialize")
   if let effect=glass.effectView?.effect as? UIGlassEffect {check(!effect.isInteractive,"native glass has no competing press recognizer")}
   for dark in [false,true] {
    glass.update(isDark:dark);glass.layoutSubviews()
    if let effect=glass.effectView {check(effect.overrideUserInterfaceStyle==(dark ? .dark:.light),"native glass follows the app theme")}
    check(glass.backgroundColor!.alpha<0.03,"glass center stays transparent in both themes")
    check(glass.sheenLayer.masksToBounds && glass.sheenLayer.cornerRadius==14,"sheen is circular rather than square")
    check(glass.rimLayer.lineWidth<1 && glass.rimLayer.strokeColor!.alpha>0.5,"thin rim remains legible")
   }
  }
  print("PASS \(checks) actual density layout/control/glass checks; UIKit rendering/gestures and list/theme/text models are explicit boundaries")
 }
}

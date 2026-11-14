var checks=0
func check(_ condition:@autoclosure()->Bool,_ why:String){checks+=1;if !condition(){print("FAIL: "+why);exit(96)}}
@main struct RoundQualitySummaryUITests {
 static func main(){
  let data=PresentationData()
  for tuning:[Int]? in [nil,[512,60,1,1_600_000]] {
   let sheet=nagramiXRoundQualitySheet(presentationData:data,values:MediaEditorValues(nagramiXRoundTuning:tuning))
   let count=tuning == nil ? 2:6
   check(sheet.groups.count==1 && sheet.groups[0].items.count==count,"factory builds only header and informational rows")
   let theme=ActionSheetControllerTheme(dimColor:UIColor(0.5))
   let nodes=sheet.groups[0].items.map{$0.node(theme:theme) as! NagramiXRoundQualitySheetNode}
   for rtl in [false,true] {for width:CGFloat in [240,320,390,500] {for font:CGFloat in [17,22,26] {for dark in [false,true] {
    var geometryTheme=ActionSheetControllerTheme(dimColor:UIColor(0.5))
    geometryTheme.baseFontSize=font
    geometryTheme.backgroundType=dark ? .dark:.light
    geometryTheme.primaryTextColor=UIColor(dark ? 1:0.1)
    geometryTheme.secondaryTextColor=UIColor(dark ? 0.7:0.3)
    let geometryNodes=sheet.groups[0].items.map{$0.node(theme:geometryTheme) as! NagramiXRoundQualitySheetNode}
    for (index,node) in geometryNodes.enumerated(){
     node.view.effectiveUserInterfaceLayoutDirection=rtl ? .rightToLeft:.leftToRight
     (sheet.groups[0].items[index] as! NagramiXRoundQualitySheetItem).updateNode(node)
     let size=node.updateLayout(constrainedSize:CGSize(width:width,height:1000),transition:.immediate)
     check(size.width==width && size.height>=52,"rows retain natural width and accessible height")
     check(node.nagramiXUsesFloatingGlass && node.backgroundNode.backgroundColor === UIColor.clear,"all summary nodes opt into shared native glass")
     check(node.titleLabel.textColor === geometryTheme.primaryTextColor && node.closeButton.tintColor === geometryTheme.secondaryTextColor,"labels and close use application theme colors")
     check(abs((node.titleLabel.font?.size ?? 0) - font * (index==0 ? 20.0/17.0:1)) < 0.01,"fonts follow sheet theme size")
     if index==0 {
      check(node.closeButton.frame.width==44 && node.closeButton.frame.height==44,"close button retains native 44 point hit target")
      check(node.titleLabel.isAccessibilityElement && node.titleLabel.accessibilityTraits.contains(.header),"title is accessible as header")
      check(!node.view.isAccessibilityElement && !node.closeButton.isHidden,"header keeps close separately accessible")
      check(!node.titleLabel.frame.intersects(node.closeButton.frame),"long title stays clear of close button")
     } else {
      check(node.view.isAccessibilityElement && node.view.accessibilityTraits.contains(.staticText),"rows are informational not selectable buttons")
      check(node.closeButton.isHidden,"rows have no hidden selection or apply actions")
      check(!node.titleLabel.frame.intersects(node.valueLabel.frame),"key and value columns never overlap")
      check(node.titleLabel.frame.minX>=20 && node.valueLabel.frame.maxX<=width-20,"text aligns with sheet insets")
     }
     check(node.titleLabel.frame.maxY<=size.height && node.valueLabel.frame.maxY<=size.height,"large text stays inside measured row")
    }
   }}}}
   nodes[0].closePressed();nodes[0].closePressed()
   check(sheet.dismissals==1,"close commits dismissal exactly once")
   if tuning != nil {for node in nodes.dropFirst(){node.closePressed()};check(sheet.dismissals==1,"informational row cannot invoke callback")}
  }
  print("Round quality sheet actual factory/node checks: \(checks)")
 }
}

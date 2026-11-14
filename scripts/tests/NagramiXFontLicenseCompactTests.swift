@main struct FontLicenseCompactTests {
 static func main(){
  var checks=0
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  func words(_ value:String)->[String]{value.split(whereSeparator:{$0.isWhitespace}).map(String.init)}
  let originals=NagramiXFontManager.licenseDocuments
  let extra:[(name:String,text:String)]=[("Unicode 🫡", "Ж😀\n\nГЛАВА\n\nТекст с кириллицей.\nпродолжение.\n\nEND"),("Empty", ""),("RTL", "ترخيص الخط\n\nنص الترخيص الأصلي")]
  for bodySize:CGFloat in [14,15,16,17,19,21,23,26,30,34,40] {
   var size=FixtureFontSize();size.itemListBaseFontSize=bodySize
   let base=size.itemListBaseHeaderFontSize
   if bodySize==17 {check(base==13,"font licenses use the exact Whisper/Vosk thirteen point size")}
   for docs in [originals,extra,[]] {
    let document=NagramiXFontLicenseDocument(documents:docs,base:base,color:.white)
    check(words(document.text.string)==docs.flatMap{words($0.name)+words($0.text)},"every original legal word copyright and notice remains in order")
    check(!document.text.string.contains("\n\n"),"paragraph spacing is not doubled by empty lines")
    var cursor=0
    for doc in docs {
     let title=doc.name+"\n";let range=NSRange(location:cursor,length:(title as NSString).length)
     let attributes=document.text.attributes(at:range.location,effectiveRange:nil)
     check((attributes[.font] as! UIFont).pointSize==base+base/13,"document headings stay compact and scale with the legal text")
     cursor+=range.length
     for (index,paragraph) in NagramiXFontLicenseLayout.paragraphs(doc.text).enumerated() {
      if index==0 || (paragraph.count<100 && paragraph==paragraph.uppercased()) {
       check(document.separators.contains{$0.range.location==cursor},"separator anchors track original UTF16 paragraph boundaries")
      }
      let attrs=document.text.attributes(at:cursor,effectiveRange:nil)
      let font=attrs[.font] as! UIFont;let style=attrs[.paragraphStyle] as! NSMutableParagraphStyle
      check(font.pointSize==base,"legal paragraphs retain the Whisper/Vosk size at every scale")
      check(style.alignment == .left && style.lineBreakMode == .byWordWrapping,"license text wraps without justification or truncation")
      check(style.paragraphSpacing==8*base/13 && style.lineSpacing==2*base/13,"compact paragraph rhythm scales with accessibility size")
      cursor+=(paragraph+"\n" as NSString).length
     }
    }
    check(cursor==document.text.length,"formatting visits the entire document without hidden omissions")
    for separator in document.separators {check(separator.range.location<document.text.length && separator.spacing>0,"separator anchors use valid utf16 locations and a real paragraph gap")}
   }
  }
  let context=AccountContext();let reader=NagramiXFontLicensesController(context:context)
  reader.loadDisplayNode()
  let bodyStart=(originals[0].name+"\n" as NSString).length
  check((reader.text.attributedText.attributes(at:bodyStart,effectiveRange:nil)[.font] as! UIFont).pointSize==13,"actual controller uses Whisper Vosk body size")
  check(!reader.text.isEditable && reader.text.isSelectable,"license text remains read-only and selectable")
  check(reader.text.textContainer.lineFragmentPadding==0,"text and divider share the same horizontal inset")
  check(reader.title=="NagramiX.Fonts.Licenses","existing localized navigation title is retained")
  let sourceWords=originals.flatMap{words($0.name)+words($0.text)}
  check(words(reader.text.attributedText.string)==sourceWords,"actual controller renders all four complete license originals")
  for width:CGFloat in [230,320,390,430,768] {for safe:CGFloat in [0,20,44] {for height:CGFloat in [320,600,844] {
   var layout=ContainerViewLayout(size:CGSize(width:width,height:height));layout.safeInsets.left=safe;layout.safeInsets.right=safe;layout.safeInsets.bottom=34
   reader.containerLayoutUpdated(layout,transition:.immediate)
   let view=reader.text;view.contentSize=CGSize(width:view.bounds.width,height:8000)
   for (i,separator) in view.separators.enumerated(){view.layoutManager.rects[separator.range.location]=CGRect(x:0,y:CGFloat(i)*60+40,width:8,height:17)}
   view.layoutSubviews();let segments=view.separatorLayer.path!.segments
   check(segments.count==view.separators.count,"every document and chapter divider is rendered")
   check(view.layer.sublayers.filter{$0 === view.separatorLayer}.count==1,"dividers use one noninteractive layer without duplicate overlays")
   for (i,line) in segments.enumerated() {
    let anchor=view.separators[i];let glyph=view.layoutManager.rects[anchor.range.location]!
    let expected=floor((glyph.minY+view.textContainerInset.top-anchor.spacing/2)/UIScreenPixel)*UIScreenPixel
    check(line.0.x==16 && line.1.x==view.bounds.width-16,"divider edges align exactly with text padding")
    check(line.0.y==expected && line.1.y==expected,"dividers stay inside paragraph gaps and align to device pixels")
   }
   let layoutCount=view.layoutManager.ensureCount;let before=view.separatorLayer.path;let offset=CGPoint(x:0,y:1800)
   view.contentOffset=offset;view.layoutSubviews()
   check(view.layoutManager.ensureCount==layoutCount && view.separatorLayer.path === before,"scrolling does not relayout the full long license")
   check(view.separatorLayer.frame.minY==0 && view.separatorLayer.frame.height==8000,"divider layer uses document coordinates rather than sticky viewport coordinates")
   check(view.frame.minX>=safe+12 && view.frame.maxX<=width-safe-12,"safe-area margins fit compact and wide phone layouts")
   check(view.frame.maxY<=height-34-12 && view.frame.height>=0,"reading viewport avoids the navigation and home areas")
  }}}
  for dark in [false,true] {
   reader.presentation.theme.overallDarkAppearance=dark
   let offset=CGPoint(x:0,y:900);reader.text.contentOffset=offset;reader.refreshLicense();reader.text.layoutSubviews()
   check(reader.text.contentOffset==offset,"theme refresh preserves the reading offset")
   check(reader.text.overrideUserInterfaceStyle==(dark ? .dark:.light),"reader follows the application's light or dark theme")
   check(reader.text.separatorLayer.strokeColor === reader.presentation.theme.list.itemBlocksSeparatorColor,"divider color comes from the current app theme")
   check(words(reader.text.attributedText.string)==sourceWords,"theme refresh never replaces full legal text with a summary")
  }
  let view=reader.text
  view.updateSeparators([NagramiXFontLicenseSeparator(range:NSRange(location:view.attributedText.length+1,length:1),spacing:8)],color:.gray);view.layoutSubviews()
  check(view.separatorLayer.path!.segments.isEmpty,"stale out-of-range anchors are ignored safely")
  view.bounds.size = .zero;view.updateSeparators([],color:.gray);let count=view.layoutManager.ensureCount;view.layoutSubviews()
  check(view.layoutManager.ensureCount==count && view.needsSeparatorLayout,"zero-size views defer glyph layout until geometry is valid")
  print("PASS \(checks) actual font-license formatter/controller/geometry checks; UIKit/TextKit metrics, rendering and app host interfaces are explicit boundaries")
 }
}

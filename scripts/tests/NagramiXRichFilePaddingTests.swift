@main struct RichFilePaddingTests {
 static func main(){
  var checks=0
  func check(_ ok:@autoclosure()->Bool,_ why:String){if !ok(){print("FAIL: "+why);exit(96)};checks+=1}
  func equal(_ a:CGFloat,_ b:CGFloat)->Bool{abs(a-b)<0.00001}
  func sameRect(_ a:CGRect,_ b:CGRect)->Bool{equal(a.minX,b.minX) && equal(a.minY,b.minY) && equal(a.width,b.width) && equal(a.height,b.height)}
  func same(_ a:InstantPageV2Layout,_ b:InstantPageV2Layout)->Bool{
   a.contentSize==b.contentSize && a.items.map{$0.frame}==b.items.map{$0.frame} && a.detailsIndices==b.detailsIndices
  }
  let caption=InstantPageCaption(text:.plain("Текст поста 😀 ссылка"))
  for width:CGFloat in [236,280,363,405,768] {for scale:CGFloat in [15/17,1,23/17,30/17] {for document in [false,true] {for prefix in [false,true] {for inset:CGFloat in [0,15,22] {
   let file:InstantPageBlock=document ? .document(1,caption):.audio(1,caption)
   let blocks:[InstantPageBlock]=(prefix ? [.anchor("top"),.anchor("again")]:[])+[file,.paragraph("Продолжение")]
   var context=LayoutContext();context.metrics=InstantPageMetrics(scale:scale);context.leadingFileInset=inset
   var original=context
   let result=layoutBlockSequence(blocks,boundingWidth:width,horizontalInset:9,kind:.topLevel,context:&context)
   let before=originalSequence(blocks,boundingWidth:width,horizontalInset:9,kind:.topLevel,context:&original)
   check(result.items.count==3,"file and all caption/text items remain")
   let top=result.items[0].frame.minY+2
   check(equal(top,max(2,inset)),"top file matches ordinary file padding")
   check(equal(result.items[0].frame.height,document ? 52:44),"player and document geometry unchanged")
   let delta=max(0,inset-2)
   for i in result.items.indices {
    check(sameRect(result.items[i].frame,before.items[i].frame.offsetBy(dx:0,dy:delta)),"caption and following text shift with file")
    check(equal(result.items[i].frame.width,before.items[i].frame.width),"wide/narrow/selection width is retained")
   }
   check(equal(result.contentSize.height,before.contentSize.height+delta),"bubble height includes exactly the added top gap")
   check(result.contentSize.width==before.contentSize.width && context.mediaIndexCounter==original.mediaIndexCounter,"width and media index unchanged")
   let header=nagramiXRichFileHeaderSpacing(blocks:blocks,fileTopInset:inset)
   check(header==(inset>0 ? 0:7),"file header does not double count new padding")
   for kind in [BlockSequenceKind.detail,.cell,.list] {
    var nested=context;var oldNested=context
    check(same(layoutBlockSequence(blocks,boundingWidth:width,horizontalInset:9,kind:kind,context:&nested),originalSequence(blocks,boundingWidth:width,horizontalInset:9,kind:kind,context:&oldNested)),"nested layout preserves native spacing")
   }
  }}}}}
  let photo=InstantPageBlock.image(1,InstantPageCaption(),nil,nil,false)
  let samples:[[InstantPageBlock]]=[[.paragraph("hello")],[photo],[.preformatted],[.paragraph("before"),.audio(1,caption)],[.document(99,caption),.audio(1,caption)]]
  for blocks in samples {
   var context=LayoutContext();var old=context
   let result=layoutBlockSequence(blocks,boundingWidth:363,horizontalInset:9,kind:.topLevel,context:&context)
   if case .document=blocks[0] {
    check(equal(result.items[0].frame.minY+2,15),"missing media cannot steal leading file padding")
   } else {
    check(same(result,originalSequence(blocks,boundingWidth:363,horizontalInset:9,kind:.topLevel,context:&old)),"other first blocks and embedded files retain exact native geometry")
   }
  }
  check(nagramiXRichFileHeaderSpacing(blocks:[photo],fileTopInset:15)==7,"photo keeps native header gap")
  check(nagramiXRichFileHeaderSpacing(blocks:[.paragraph("hello")],fileTopInset:15)==0,"text keeps native header gap")
  check(nagramiXRichFileHeaderSpacing(blocks:[.anchor("only")],fileTopInset:15)==0,"anchor-only has no invented header gap")
  print("PASS \(checks) real rich file layout/spacing/header checks; UIKit/text drawing/media models are explicit boundaries")
 }
}

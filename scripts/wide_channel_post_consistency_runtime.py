"""Выполнить реальный native mosaic вместе с родительским проходом ширины."""
from validate_quick_format import block
import bubble_selection_edge_runtime as edge

BUBBLE=edge.BUBBLE
MOSAIC='submodules/MosaicLayout/Sources/ChatMessageBubbleMosaicLayout.swift'
UTILS='submodules/Display/Source/UIKitUtils.swift'


def fixture(source, previous_code=None):
    code=(source/BUBBLE).read_text() if previous_code is None else previous_code
    native=(source/MOSAIC).read_text()
    # CoreGraphics is present on Apple; Foundation supplies CGRect on Linux.
    native=native.replace('import CoreGraphics\n','#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n',1)
    helper=block(code,'private func nagramiXWideChannelMosaicLayout(') if 'private func nagramiXWideChannelMosaicLayout(' in code else ''
    begin=code.index('        if let mosaicRange = mosaicRange {',code.index('        var calculatedGroupFramesAndSize:'))
    end=code.index('            var hasText = false',begin)
    parent=code[begin:end]+'        }\n'
    fitted=block((source/UTILS).read_text(),'    func fittedToWidthOrSmaller(')
    reaction_start=code.index('            var maximumNodeWidth = maximumNodeWidth',code.index('        var reactionButtonsFinalize:'))
    reaction_end=code.index('            let (minWidth, buttonsLayout)',reaction_start)
    reaction=code[reaction_start:reaction_end].replace('nagramiXWideChannelPost','wide').replace('hasInstantVideo','round')
    final_start=code.index('            var maxContentWidth = maxContentWidth',code.index('        var reactionButtonsSizeAndApply:'))
    final_end=code.index('            reactionButtonsSizeAndApply =',final_start)
    final=code[final_start:final_end].replace('nagramiXWideChannelPost','wide').replace('hasInstantVideo','round')
    reactions='func reactionPrepare(maximumNodeWidth:CGFloat,baseWidth:CGFloat,wide:Bool,round:Bool)->CGFloat {\n'+reaction+'return maximumNodeWidth\n}\n'
    reactions+='func reactionFinalize(maxContentWidth:CGFloat,baseWidth:CGFloat,wide:Bool,round:Bool)->CGFloat {\n'+final+'return maxContentWidth\n}\n'
    return native+'\nextension CGSize {\n'+fitted+'\n}\n'+helper+BOUNDARY+'''
func productionPost(width:CGFloat,wide:Bool,sizes:[CGSize])->(CGFloat,[(CGRect,MosaicItemPosition)],CGSize) {
 let maximumContentWidth=width,nagramiXWideChannelPost=wide
 var maximumNodeWidth=width
 let layoutConstants=Constants()
 let contentPropertiesAndLayouts=sizes.map{(Optional($0),0)}
 let mosaicRange:Range<Int>?=0..<sizes.count
 var calculatedGroupFramesAndSize:([(CGRect,MosaicItemPosition)],CGSize)?
'''+parent+'''
 return (maximumNodeWidth,calculatedGroupFramesAndSize!.0,calculatedGroupFramesAndSize!.1)
}
'''+reactions+TESTS


def selection_fixture(source, previous):
    # Execute existing production selection budget/placement against the NEW
    # full parent, not merely the historical checkpoint.
    return edge.fixture(source,previous)


def negatives(text):
    for name,old,new,why in [
        ('disabled-wide-fill','}, fillWidth: nagramiXWideChannelPost)','}, fillWidth: false)','all album posts fill the shared width'),
        ('native-portrait-shrink','let scale = maxSize.width / nativeWidth','let scale = min(1.0, maxSize.width / nativeWidth)','all album posts fill the shared width'),
        ('caption-budget-shrink','maximumNodeWidth = nagramiXWideChannelPost ? maximumContentWidth : size.width','maximumNodeWidth = min(maximumContentWidth, 280.0)','caption keeps the parent width'),
        ('off-regression','guard fillWidth, maxSize.width.isFinite','guard maxSize.width.isFinite','OFF retains exact native frames'),
        ('round-reaction-shrink','if round && !wide {','if round {','reaction preparation shares the wide budget'),
        ('distorted-height','height: frame.height * scale','height: frame.height','uniform native geometry'),
    ]:
        assert text.count(old)==(2 if name=='round-reaction-shrink' else 1),(name,text.count(old))
        yield name,text.replace(old,new,1),why

BOUNDARY='''
struct Insets {var left:CGFloat=1,right:CGFloat=1,top:CGFloat=1,bottom:CGFloat=1}
struct ImageConstants {var bubbleInsets=Insets();var maxDimensions=CGSize(width:320,height:420)}
struct Constants {var image=ImageConstants()}
'''
TESTS=r'''
@main struct WideChannelPostTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Wide post regression: "+why+"\n").utf8));exit(91)};checks+=1}
  func close(_ a:CGFloat,_ b:CGFloat)->Bool{abs(a-b)<0.00001}
  let inputs:[CGSize]=[CGSize(width:384,height:832),CGSize(width:320,height:640),CGSize(width:640,height:960),CGSize(width:640,height:360),CGSize(width:1000,height:1000),CGSize(width:2400,height:400),CGSize(width:400,height:2400)]
  var sawNarrowNative=false,sawRoundedNativeOverflow=false
  // 2–10 members, portrait-first reproducer, landscape/square/mixed media,
  // reordered albums, phone/tablet/landscape and selected-column budgets.
  for width:CGFloat in [238,280,337,363,405,680,978] {for count in 2...10 {for pattern in 0..<inputs.count {for reversed in [false,true] {
   var sizes=(0..<count).map { inputs[(pattern+$0)%inputs.count] }
   if pattern==0{sizes=Array(repeating:inputs[0],count:count)}
   if reversed{sizes.reverse()}
   let wide=productionPost(width:width,wide:true,sizes:sizes)
   check(close(wide.0,width),"caption keeps the parent width")
   check(close(wide.2.width,width),"all album posts fill the shared width")
   check(wide.1.count==count && wide.2.height>0 && wide.2.height.isFinite,"native album members retained")
   check(close(wide.1.map{$0.0.maxX}.max()!,width-1),"all album posts fill the shared width")
   let budget=CGSize(width:width-2,height:max(width-2,420))
   let native=chatMessageBubbleMosaicLayout(maxSize:budget,itemSizes:sizes,fillWidth:true)
   let nativeWidth=native.0.map{$0.0.maxX}.max()!,scale=(width-2)/nativeWidth
   if nativeWidth<width-3{sawNarrowNative=true}
   if nativeWidth>width-1.9{sawRoundedNativeOverflow=true}
   for index in sizes.indices {
    let frame=wide.1[index].0.offsetBy(dx:-1,dy:-1),original=native.0[index].0
    check(frame.minX>=0 && frame.minY>=0 && frame.maxX<=width-2+0.00001,"safe media edges")
    check(wide.1[index].1==native.0[index].1,"native corner flags and order retained")
    check(close(frame.width,original.width*scale) && close(frame.height,original.height*scale),"uniform native geometry")
    for other in sizes.indices where other>index {
     let intersection=frame.intersection(wide.1[other].0.offsetBy(dx:-1,dy:-1))
     check(intersection.isNull || intersection.width<0.00001 || intersection.height<0.00001,"native frames do not overlap")
    }
   }
   let off=productionPost(width:width,wide:false,sizes:sizes)
   let original=chatMessageBubbleMosaicLayout(maxSize:CGSize(width:320,height:420).fittedToWidthOrSmaller(width-2),itemSizes:sizes)
   check(off.1.count==original.0.count,"OFF member count")
   check(off.2==CGSize(width:original.1.width+2,height:original.1.height+2),"OFF retains exact native frames")
   for index in sizes.indices {check(off.1[index].0==original.0[index].0.offsetBy(dx:1,dy:1) && off.1[index].1==original.0[index].1,"OFF retains exact native frames")}
  }}}}
  for width:CGFloat in [280,337,363,405,680] {for wide in [false,true] {for round in [false,true] {
   let expectedPrepare=round && !wide ? min(CGFloat(309),width+20-84):width
   let expectedFinal=round && !wide ? min(CGFloat(310),width+20-84):width
   check(reactionPrepare(maximumNodeWidth:width,baseWidth:width+20,wide:wide,round:round)==expectedPrepare,"reaction preparation shares the wide budget")
   check(reactionFinalize(maxContentWidth:width,baseWidth:width+20,wide:wide,round:round)==expectedFinal,"reaction finalization shares the wide budget")
  }}}
  check(sawNarrowNative,"portrait regression is exercised")
  check(sawRoundedNativeOverflow,"native ceil overflow is exercised")
  print("wide channel post checks: \(checks)")
 }
}
'''

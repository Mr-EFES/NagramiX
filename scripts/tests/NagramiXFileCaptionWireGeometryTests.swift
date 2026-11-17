@main struct WireCaptionGeometry {
 static func main() {
  var checks=0
  func check(_ v:Bool,_ why:String){if !v{print("Wire caption geometry: "+why);exit(96)};checks+=1}
  check(!nagramiXFileCaptionHasWireSpacing(file:nil,text:"\ncaption"),"missing file has no wire spacing")
  for flag in 0..<5 {
   var file=File(isMusic:false)
   switch flag {case 0:file.isVoice=true;case 1:file.isInstantVideo=true;case 2:file.isVideo=true;case 3:file.isAnimated=true;default:file.isSticker=true}
   check(!nagramiXFileCaptionHasWireSpacing(file:file,text:"\ncaption"),"non-file media retains existing local layout")
  }
  for width:CGFloat in [170,350,500] {for height:CGFloat in [38,44,80] {for music in [false,true] {for caption in [false,true] {for bubbleless in [false,true] {for pixel:CGFloat in [0.5,1.0/3.0] {
   let size=CGSize(width:width,height:height)
   let old=original(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel)
   let legacy=measure(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel,wire:"caption")
   let spaced=measure(size,music:music,caption:caption,isBubbleless:bubbleless,pixel:pixel,wire:"\ncaption")
   check(legacy.0.width==old.0.width && spaced.0.width==old.0.width,"classic width is unchanged")
   check(spaced.1==15 && legacy.1==15,"native file top padding is unchanged")
   if !bubbleless && caption {
    check(abs(legacy.2+captionTop(pixel)-15)<0.00001,"legacy posts retain previous local gap")
    let nativeBottom:CGFloat=15-(music ? 14:7)
    check(spaced.2==nativeBottom,"wire line removes duplicate local padding")
    let optimistic=measure(size,music:music,caption:true,isBubbleless:false,pixel:pixel,wire:"caption",pending:"\ncaption")
    check(optimistic.2==spaced.2,"pending edited caption uses its own spacing")
    let removed=measure(size,music:music,caption:true,isBubbleless:false,pixel:pixel,wire:"\ncaption",pending:"caption")
    check(removed.2==legacy.2,"pending removal restores local spacing")
   } else {check(spaced.0==legacy.0 && spaced.0==old.0,"no-caption and bubbleless geometry unchanged")}
  }}}}}}
  print("File caption wire geometry: \(checks) actual constants/top/bottom/pending checks passed; native glyph height and pixels not claimed")
 }
}

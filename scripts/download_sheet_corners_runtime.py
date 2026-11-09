"""Проверить реальный генератор маски в явной пиксельной границе без UIKit."""
from validate_quick_format import block
from round_video_editor_runtime import GEOMETRY_BOUNDARY

GROUP='submodules/Display/Source/ActionSheetItemGroupNode.swift'
IMAGE='submodules/Display/Source/GenerateImage.swift'

BOUNDARY=r'''
struct Pixel {
 var r:Double=0,g:Double=0,b:Double=0,a:Double=0
 func over(_ other:Pixel,coverage:Double)->Pixel{
  let alpha=a*coverage
  return Pixel(r:r*coverage+other.r*(1-alpha),g:g*coverage+other.g*(1-alpha),b:b*coverage+other.b*(1-alpha),a:alpha+other.a*(1-alpha))
 }
 func multiplied(_ factor:Double)->Pixel{Pixel(r:r*factor,g:g*factor,b:b*factor,a:a*factor)}
}
struct UIColor {let cgColor:Pixel}
struct UIRectCorner:OptionSet {let rawValue:Int;static let topLeft=Self(rawValue:1),topRight=Self(rawValue:2)}
struct Path {
 let rect:CGRect;let corners:UIRectCorner;let radius:CGFloat
 func contains(_ point:CGPoint)->Bool{
  guard rect.contains(point) else{return false}
  let x=point.x-rect.minX,y=point.y-rect.minY
  if y<radius {
   if corners.contains(.topLeft) && x<radius{return pow(x-radius,2)+pow(y-radius,2)<=radius*radius}
   if corners.contains(.topRight) && x>rect.width-radius{return pow(x-(rect.width-radius),2)+pow(y-radius,2)<=radius*radius}
  }
  return true
 }
}
struct UIBezierPath {let cgPath:Path;init(roundedRect:CGRect,byRoundingCorners:UIRectCorner,cornerRadii:CGSize){cgPath=Path(rect:roundedRect,corners:byRoundingCorners,radius:cornerRadii.width)}}
enum BlendMode {case normal,clear}
var testScale:CGFloat=1
var dirtyPixel=Pixel()
final class CGContext {
 let size:CGSize;let scale:CGFloat;let width:Int;let height:Int
 var pixels:[Pixel];var color=Pixel();var mode=BlendMode.normal;var path:Path?
 var ax:CGFloat=1,ay:CGFloat=1,tx:CGFloat=0,ty:CGFloat=0
 init(size:CGSize,scale:CGFloat){self.size=size;self.scale=scale;width=Int(size.width*scale);height=Int(size.height*scale);pixels=Array(repeating:dirtyPixel,count:width*height)}
 func translateBy(x:CGFloat,y:CGFloat){tx+=ax*x;ty+=ay*y}
 func scaleBy(x:CGFloat,y:CGFloat){ax*=x;ay*=y}
 func setFillColor(_ value:Pixel){color=value}
 func setBlendMode(_ value:BlendMode){mode=value}
 func addPath(_ value:Path){path=value}
 func coverage(_ px:Int,_ py:Int,rect:CGRect,path:Path?)->Double{
  var hits=0
  for sy in 0..<4 {for sx in 0..<4 {
   let x=(CGFloat(px)+(CGFloat(sx)+0.5)/4)/scale
   let y=(CGFloat(py)+(CGFloat(sy)+0.5)/4)/scale
   let point=CGPoint(x:(x-tx)/ax,y:(y-ty)/ay)
   if rect.contains(point) && (path?.contains(point) ?? true){hits+=1}
  }}
  return Double(hits)/16
 }
 func paint(_ rect:CGRect,path:Path?,clear:Bool){
  for y in 0..<height {for x in 0..<width{
   let index=y*width+x,c=coverage(x,y,rect:rect,path:path)
   pixels[index]=clear ? pixels[index].multiplied(1-c):color.over(pixels[index],coverage:c)
  }}
 }
 func clear(_ rect:CGRect){paint(rect,path:nil,clear:true)}
 func fill(_ rect:CGRect){paint(rect,path:nil,clear:mode == .clear)}
 func fillPath(){if let path{paint(path.rect,path:path,clear:mode == .clear)};path=nil}
}
struct UIImage {
 let size:CGSize;let scale:CGFloat;let pixels:[Pixel];var leftCap=0,topCap=0
 func stretchableImage(withLeftCapWidth:Int,topCapHeight:Int)->UIImage{var result=self;result.leftCap=withLeftCapWidth;result.topCap=topCapHeight;return result}
 func at(_ x:Int,_ y:Int)->Pixel{pixels[y*Int(size.width*scale)+x]}
 func stretched(_ point:CGPoint,to target:CGSize)->Pixel {
  func mapped(_ p:CGFloat,_ length:CGFloat,_ cap:Int,_ targetLength:CGFloat)->CGFloat{
   let leading=CGFloat(cap),trailing=length-leading-1
   if p<leading{return p}
   if p>=targetLength-trailing{return length-(targetLength-p)}
   return leading+0.5
  }
  let x=mapped(point.x,size.width,leftCap,target.width)
  let y=mapped(point.y,size.height,topCap,target.height)
  return at(min(Int(size.width*scale)-1,max(0,Int(x*scale))),min(Int(size.height*scale)-1,max(0,Int(y*scale))))
 }
}
final class DrawingContext {
 let size:CGSize;let scale:CGFloat;let context:CGContext
 init?(size:CGSize,scale:CGFloat=0,opaque:Bool=false,clear:Bool=false){self.size=size;self.scale=scale==0 ? testScale:scale;context=CGContext(size:size,scale:self.scale);if clear{context.clear(CGRect(origin:.zero,size:size))}}
 // REAL_CONTEXT_METHODS
 func generateImage()->UIImage?{UIImage(size:size,scale:scale,pixels:context.pixels)}
}
var checks=0
func check(_ v:@autoclosure()->Bool,_ message:String){if !v(){FileHandle.standardError.write(Data(("Corner regression: "+message+"\n").utf8));exit(91)};checks+=1}
func same(_ lhs:Pixel,_ rhs:Pixel)->Bool{abs(lhs.r-rhs.r)<0.00000001 && abs(lhs.g-rhs.g)<0.00000001 && abs(lhs.b-rhs.b)<0.00000001 && abs(lhs.a-rhs.a)<0.00000001}
'''


def fixture(source):
    image=(source/IMAGE).read_text()
    context='\n'.join(block(image,m) for m in ['    public func withContext(', '    public func withFlippedContext(']).replace('public ','')
    wrapper='\n'.join(block(image,m) for m in ['public func generateImage(_ size: CGSize, contextGenerator:', 'public func generateImage(_ size: CGSize, opaque:']).replace('public ','')
    helper=block((source/GROUP).read_text(),'private func nagramiXActionSheetTopCornerDimImage(')
    return GEOMETRY_BOUNDARY+BOUNDARY.replace('// REAL_CONTEXT_METHODS',context)+wrapper+'\n'+helper+TESTS


TESTS=r'''
@main struct CornerMaskTests {static func main(){
 for scale:CGFloat in [1,2,3] {testScale=scale
 for alpha in [0.0,0.2,0.45,0.6,1.0] {
 for rgb in [[0.0,0.0,0.0],[0.15,0.25,0.35]] {
  let dim=Pixel(r:rgb[0]*alpha,g:rgb[1]*alpha,b:rgb[2]*alpha,a:alpha)
  dirtyPixel=Pixel();let clean=nagramiXActionSheetTopCornerDimImage(color:UIColor(cgColor:dim))!
  check(clean.size==CGSize(width:33,height:33) && clean.leftCap==16 && clean.topCap==16,"native scale and cap geometry retained")
  check(same(clean.at(0,0),dim),"dim belongs at the top corners, not at the bottom")
  check(clean.at(0,Int(32*scale)).a==0 && clean.at(Int(32*scale),Int(32*scale)).a==0,"both lower corners remain completely clear")
  check(clean.at(Int(16*scale),0).a==0,"top center is clear underneath actual sheet content")
  for seed in [Pixel(r:0.1,g:0.9,b:0.3,a:1),Pixel(r:0.6,g:0.1,b:0.2,a:0.8)] {
   dirtyPixel=seed;let dirty=nagramiXActionSheetTopCornerDimImage(color:UIColor(cgColor:dim))!
   check(zip(clean.pixels,dirty.pixels).allSatisfy{same($0,$1)},"reused malloc bytes never alter the mask or add dark pixels")
  }
  let width=Int(clean.size.width*scale),height=Int(clean.size.height*scale)
  for y in 0..<height {for x in 0..<width {
   let p=clean.at(x,y)
   check(same(p,clean.at(width-1-x,y)),"upper left and right masks are symmetric")
   check(p.a>=0 && p.a<=alpha+0.00000001,"mask never adds an opaque black outline")
  }}
  for target in [CGSize(width:320,height:180),CGSize(width:393,height:420),CGSize(width:430,height:700),CGSize(width:834,height:500)] {
   check(same(clean.stretched(CGPoint(x:0.25,y:0.25),to:target),dim),"top cap stays attached at any panel size")
   check(clean.stretched(CGPoint(x:0.25,y:target.height-0.25),to:target).a==0,"stretching never reintroduces a lower corner patch")
   check(clean.stretched(CGPoint(x:target.width/2,y:0.25),to:target).a==0,"stretched top center leaves content untouched")
  }
 }
 }}
 print("Corner mask bitmap-adapter checks: \(checks)")
}}
'''

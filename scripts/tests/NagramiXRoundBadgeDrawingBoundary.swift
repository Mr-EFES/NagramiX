// Записывающая граница UIKit: проверяет принадлежность рисования контексту,
// но не воспроизводит пиксели, реальные метрики шрифта или растеризацию iPhone.
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

extension NSAttributedString.Key {
 static let font=Self("fixture-font"),foregroundColor=Self("fixture-color")
}
struct UIColor:Equatable {
 let token:String
 init(_ token:String){self.token=token}
 var cgColor:Self{self}
}
enum Font {static func semibold(_ size:CGFloat)->CGFloat{size}}
final class CGContext {
 struct Text {let text:String,point:CGPoint,size:CGSize,color:UIColor}
 var texts:[Text]=[],borders:[CGRect]=[],lineWidth:CGFloat=0
 var strokeColor:UIColor?
 func clear(_ rect:CGRect){}
 func setStrokeColor(_ color:UIColor){strokeColor=color}
 func setLineWidth(_ width:CGFloat){lineWidth=width}
 func addPath(_ path:CGRect){borders.append(path)}
 func strokePath(){}
}
final class UIBezierPath {
 let cgPath:CGRect
 init(roundedRect:CGRect,cornerRadius:CGFloat){cgPath=roundedRect}
}
struct UIImage {let size:CGSize,context:CGContext}
var uiContexts:[CGContext]=[]
func UIGraphicsPushContext(_ context:CGContext){uiContexts.append(context)}
func UIGraphicsPopContext(){uiContexts.removeLast()}
func UIGraphicsGetCurrentContext()->CGContext?{uiContexts.last}

// Как у native Display.generateImage, переданный контекст сам не помещается
// в UIKit stack. NSString.draw использует именно текущий UIKit context.
func generateImage(_ size:CGSize,rotatedContext:(CGSize,CGContext)->Void)->UIImage? {
 let context=CGContext();rotatedContext(size,context)
 return UIImage(size:size,context:context)
}
extension NSString {
 func size(withAttributes attributes:[NSAttributedString.Key:Any]?)->CGSize {
  let size=attributes?[.font] as? CGFloat ?? 10
  return CGSize(width:CGFloat(length)*size*0.6,height:size*1.2)
 }
 func draw(at point:CGPoint,withAttributes attributes:[NSAttributedString.Key:Any]?) {
  guard let current=UIGraphicsGetCurrentContext(),let color=attributes?[.foregroundColor] as? UIColor else{return}
  current.texts.append(CGContext.Text(text:self as String,point:point,size:size(withAttributes:attributes),color:color))
 }
}

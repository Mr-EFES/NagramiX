"""Выполнить реальные theme assignments/bitmap calls с явной границей UIKit."""
from validate_quick_format import block
from font_theme_contrast_apple import native_types,SETTINGS
UI='submodules/SettingsUI/Sources/NagramiXFontsController.swift'


def fixture(source):
    ui=(source/UI).read_text();settings=(source/SETTINGS).read_text()
    main=next(x.strip() for x in ui.splitlines() if 'self.statusBar.statusBarStyle = self.presentation.' in x)
    license=next(x.strip() for x in ui.splitlines() if 'self.statusBar.statusBarStyle = presentation.' in x)
    icon=next(x for x in settings.splitlines() if 'icon: nagramiXFontSettingsIcon(' in x).split('icon: ',1)[1].split(', title:',1)[0]
    helper=block(settings,'private func nagramiXFontSettingsIcon(')
    return BOUNDARY+native_types(source)+helper+'''
struct RootTheme {var statusBarStyle:PresentationThemeStatusBarStyle}
struct ListTheme {var itemPrimaryTextColor:UIColor;var itemAccentColor=UIColor(value:0x2eaaff)}
struct Theme {var rootController:RootTheme;var list:ListTheme}
struct Presentation {var theme:Theme}
final class NativeStatusBarBoundary {var statusBarStyle=StatusBarStyle.Black}
final class FontControllerBoundary {
 var statusBar=NativeStatusBarBoundary()
 var presentation:Presentation
 init(_ value:Presentation){self.presentation=value}
 func refresh(){'''+main+'''}
 func licenses(presentation:Presentation){'''+license+'''}
}
func icon(presentationData:Presentation)->UIImage? {return '''+icon+'''}
'''+TESTS


def negatives(text):
    variants=[
      ('missing-status-update','self.statusBar.statusBarStyle = self.presentation.theme.rootController.statusBarStyle.style','_ = self.presentation.theme.rootController.statusBarStyle.style','font screen follows current theme'),
      ('forced-white-status','self.statusBar.statusBarStyle = self.presentation.theme.rootController.statusBarStyle.style','self.statusBar.statusBarStyle = .White','font screen follows current theme'),
      ('license-default-black','self.statusBar.statusBarStyle = presentation.theme.rootController.statusBarStyle.style','_ = presentation.theme.rootController.statusBarStyle.style','license screen follows current theme'),
      ('accent-instead-of-foreground','nagramiXFontSettingsIcon(color: presentationData.theme.list.itemPrimaryTextColor)','nagramiXFontSettingsIcon(color: presentationData.theme.list.itemAccentColor)','icon uses the theme foreground'),
      ('unresolved-symbol','return UIGraphicsImageRenderer(size: symbol.size).image { _ in\n        symbol.withTintColor(color, renderingMode: .alwaysOriginal).draw(in: CGRect(origin: .zero, size: symbol.size))\n    }','return symbol.withTintColor(color, renderingMode: .alwaysOriginal)','icon becomes a bitmap for ASImageNode'),
    ]
    for name,old,new,why in variants:
      assert text.count(old)==1,(name,text.count(old))
      yield name,text.replace(old,new,1),why

BOUNDARY=r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct UIColor:Equatable {var value:Int}
final class UIImage {
 enum RenderingMode {case alwaysOriginal}
 static var symbolAvailable=true
 static var drawnColor=UIColor(value:0)
 static var draws=0
 var size=CGSize(width:24,height:20)
 let bitmap:Bool
 let color:UIColor
 init(bitmap:Bool,color:UIColor){self.bitmap=bitmap;self.color=color}
 convenience init?(systemName:String){guard Self.symbolAvailable else{return nil};self.init(bitmap:false,color:UIColor(value:0))}
 func withTintColor(_ color:UIColor,renderingMode:RenderingMode)->UIImage{UIImage(bitmap:bitmap,color:color)}
 func draw(in rect:CGRect){Self.drawnColor=color;Self.draws+=1}
}
final class UIGraphicsImageRenderer {
 init(size:CGSize){}
 func image(actions:(Int)->Void)->UIImage{actions(0);return UIImage(bitmap:true,color:UIImage.drawnColor)}
}
'''
TESTS=r'''
@main struct FontThemeTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Font theme regression: "+why+"\n").utf8));exit(91)};checks+=1}
  let p=Presentation(theme:Theme(rootController:RootTheme(statusBarStyle:.white),list:ListTheme(itemPrimaryTextColor:UIColor(value:0xffffff))))
  let controller=FontControllerBoundary(p)
  // Entering, switching themes while open, returning from the licenses screen,
  // repeated refreshes after font selection, custom foreground colors.
  for style:PresentationThemeStatusBarStyle in [.white,.black,.white,.black,.white] {for primary in [0xffffff,0x111111,0xf0d090] {
   let presentation=Presentation(theme:Theme(rootController:RootTheme(statusBarStyle:style),list:ListTheme(itemPrimaryTextColor:UIColor(value:primary))))
   controller.presentation=presentation
   for _ in 0..<3 {
    controller.refresh()
    check(controller.statusBar.statusBarStyle==style.style,"font screen follows current theme")
    controller.statusBar.statusBarStyle = .Black
    controller.licenses(presentation:presentation)
    check(controller.statusBar.statusBarStyle==style.style,"license screen follows current theme")
    let draws=UIImage.draws
    let result=icon(presentationData:presentation)
    check(result?.bitmap==true,"icon becomes a bitmap for ASImageNode")
    check(UIImage.draws==draws+1,"symbol drawn through UIKit boundary")
    check(result?.color==presentation.theme.list.itemPrimaryTextColor,"icon uses the theme foreground")
   }
  }}
  UIImage.symbolAvailable=false
  let draws=UIImage.draws
  check(icon(presentationData:p)==nil,"missing SF Symbol safely yields no icon")
  check(UIImage.draws==draws,"missing symbol does not create a renderer")
  print("font theme production checks: \(checks)")
 }
}
'''

"""Проверить production фабрику шрифтов с явной границей UIKit/CoreText."""
from pathlib import Path
from validate_quick_format import block
ROOT=Path(__file__).resolve().parents[1]
MODEL='submodules/NagramiXMediaSettings/Sources/NagramiXFontSettings.swift'
FONT='submodules/Display/Source/Font.swift'
MANAGER='submodules/Display/Source/NagramiXFontManager.swift'
UI='submodules/SettingsUI/Sources/NagramiXFontsController.swift'

def fixture(source):
    clean=lambda s:'\n'.join(x for x in s.splitlines() if not x.startswith('import ')).replace('public ', '')
    model=clean((source/MODEL).read_text())
    font=clean((source/FONT).read_text()).replace('NSMutableString()','NSMutableString(capacity: 0)')
    manager=clean((source/MANAGER).read_text())
    signal=block(manager,'    static func settingsSignal(')
    bundle=block(manager,'    private static let bundle:')
    manager=manager.replace(bundle+'()','    private static let bundle: Bundle? = nil',1)
    manager=manager.replace(signal,'',1).split('\nprivate extension UIFont {',1)[0]
    return '\n'.join(('import Foundation\n#if os(Linux)\nimport Glibc\n#else\nimport Darwin\n#endif',ADAPTER,model,font,manager,(ROOT/'scripts/tests/NagramiXAppFontSelectionTests.swift').read_text()))

ADAPTER=r'''
// UIKit/CoreText are explicit deterministic adapters. Font.swift, settings and
// resolver execute intact; actual UIKit API typechecking runs on Apple before SDK build.
typealias CFString=String;typealias CFURL=URL
extension NSAttributedString.Key {static let font=Self("font"),foregroundColor=Self("foregroundColor"),paragraphStyle=Self("paragraphStyle")}
enum NSTextAlignment {case left,center,right}
final class NSMutableParagraphStyle:NSObject {var alignment=NSTextAlignment.left}
final class UIColor:NSObject {static let black=UIColor()}
final class UIFontDescriptor {
 struct SymbolicTraits:OptionSet {let rawValue:Int;static let traitBold=Self(rawValue:1),traitItalic=Self(rawValue:2),traitMonoSpace=Self(rawValue:4)}
 enum SystemDesign {case `default`,rounded,serif,monospaced}
 enum TraitKey:String {case weight,width}
 enum AttributeName:String {case traits,featureSettings,cascadeList}
 enum FeatureKey:String {case type,selector}
 let fontName:String;let symbolicTraits:SymbolicTraits;let design:SystemDesign
 let attributes:[AttributeName:Any]
 init(_ name:String,traits:SymbolicTraits=[],design:SystemDesign = .default,attributes:[AttributeName:Any]=[:]) {self.fontName=name;self.symbolicTraits=traits;self.design=design;self.attributes=attributes}
 func withSymbolicTraits(_ traits:SymbolicTraits)->UIFontDescriptor? {UIFontDescriptor(self.fontName,traits:traits,design:self.design,attributes:self.attributes)}
 func withDesign(_ design:SystemDesign)->UIFontDescriptor? {UIFontDescriptor(self.fontName,traits:self.symbolicTraits,design:design,attributes:self.attributes)}
 func addingAttributes(_ values:[AttributeName:Any])->UIFontDescriptor {var merged=self.attributes;for(k,v)in values {merged[k]=v};return UIFontDescriptor(self.fontName,traits:self.symbolicTraits,design:self.design,attributes:merged)}
 func object(forKey key:AttributeName)->Any? {self.attributes[key]}
}
final class UIFont:NSObject {
 struct Weight:Equatable {let rawValue:CGFloat;static let regular=Self(rawValue:0),thin=Self(rawValue:-0.6),light=Self(rawValue:-0.4),medium=Self(rawValue:0.23),semibold=Self(rawValue:0.3),bold=Self(rawValue:0.4),heavy=Self(rawValue:0.56)}
 struct Width:Equatable {let rawValue:CGFloat;static let standard=Self(rawValue:0),condensed=Self(rawValue:-0.2),compressed=Self(rawValue:-0.5),expanded=Self(rawValue:0.2)}
 static var installed=0
 static var unavailable:Set<String>=[]
 let fontDescriptor:UIFontDescriptor;let pointSize:CGFloat
 var fontName:String {fontDescriptor.fontName}
 init(descriptor:UIFontDescriptor,size:CGFloat){self.fontDescriptor=descriptor;self.pointSize=size}
 convenience init?(name:String,size:CGFloat){if Self.unavailable.contains(name){return nil};self.init(descriptor:UIFontDescriptor(name),size:size)}
 static func systemFont(ofSize size:CGFloat,weight:Weight = .regular)->UIFont {UIFont(descriptor:UIFontDescriptor("System",attributes:[.traits:[UIFontDescriptor.TraitKey.weight:weight]]),size:size)}
 static func boldSystemFont(ofSize size:CGFloat)->UIFont {systemFont(ofSize:size,weight:.bold)}
 static func italicSystemFont(ofSize size:CGFloat)->UIFont {UIFont(descriptor:UIFontDescriptor("System",traits:[.traitItalic]),size:size)}
 static func nagramiXInstallFontHooks(){self.installed+=1}
}
let kNumberSpacingType=6;let kMonospacedNumbersSelector=0
let kCTFontOpenTypeFeatureTag="tag";let kCTFontOpenTypeFeatureValue="value"
func CTFontCreateWithName(_ name:CFString,_ size:CGFloat,_ transform:Any?)->UIFont {UIFont(name:name,size:size)!}
func CTFontCopyCharacterSet(_ font:UIFont)->CharacterSet {font.fontName.hasPrefix("Futura") ? CharacterSet(charactersIn:"AaBb0123456789") : .letters}
func CFCharacterSetIsLongCharacterMember(_ set:CharacterSet,_ scalar:UInt32)->Bool {UnicodeScalar(scalar).map{set.contains($0)} ?? false}
func CTFontManagerRegisterFontsForURL(_ url:CFURL,_ scope:FontScope,_ error:Any?)->Bool {true}
enum FontScope {case process}
'''

def negatives(code):
    cases=[
      ('fresh-off','init(enabled: Bool = true,','init(enabled: Bool = false,','fresh default is native and enabled'),
      ('lost-disable','guard selection != nil || settings.enabled','guard true','OFF restores upstream font'),
      ('stale-cache','let key = "\\(entry.id):\\(size):','let key = "\\(size):','changing family invalidates cached selection'),
      ('code-substitution',' || design == .monospace','', 'semantic code preserves native monospace'),
      ('lost-italic','if traits.contains(.italic) { symbolic.insert(.traitItalic) }','if false { symbolic.insert(.traitItalic) }','selected family keeps italic trait'),
      ('no-number-features','if traits.contains(.monospacedNumbers) {\n                features.append','if false {\n                features.append','number feature remains enabled'),
      ('native-scope-leak','else { Thread.current.threadDictionary.removeObject(forKey: self.nativeKey) }','else {}','changing family invalidates cached selection'),
    ]
    for name,before,after,label in cases:
      assert code.count(before)==1,(name,code.count(before))
      yield name,code.replace(before,after,1),label

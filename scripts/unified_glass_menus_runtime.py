"""Complete actual menu factory/rows/native group plus all three caller closures."""
from pathlib import Path
from validate_quick_format import block
import download_sheet_vector_contour_runtime as native
ROOT=Path(__file__).resolve().parents[1]
O='submodules/SettingsUI/Sources/NagramiXOptionSheet.swift';S='submodules/SettingsUI/Sources/NagramiXSettingsController.swift';P='submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift';G=native.GROUP;N='submodules/Display/Source/ActionSheetControllerNode.swift'
def body(text):return '\n'.join(line for line in text.splitlines() if not line.startswith('import '))
def production(source):
 g=body((source/G).read_text());o=body((source/O).read_text());n=(source/N).read_text()
 text=g+'\n'+o+'\nclass ActualInsetsHost {\nvar allowInputInset=false,nagramiXBottomAttached=false\nvar itemGroupsContainerNode=FixtureGroups()\n'+block(n,'    private var nagramiXUsesBottomAttachedLayout:')+'\n'+block(n,'    private var nagramiXContainerInsets:')+'\n}\n'
 settings=(source/S).read_text();proxy=(source/P).read_text()
 text+='\n'+block(settings,'private func nagramiXDownloadModeTitle(')+'\n'+block(proxy,'private func nagramiXDnsTitle(')+'\n'
 for name,t,marker in [('openEffect',settings,'        openInputEffect: {'),('openDownloads',settings,'        openDownloadAccelerationMode: {'),('openDns',proxy,'    selectDnsImpl = {')]:
  code=block(t,marker);code=code[code.index('{')+1:code.rindex('}')];text+='\nfunc '+name+'(){\n'+code+'\n}\n'
 return text

def boundary(source):
 t=native.BOUNDARY
 t=t.replace('    static let black=UIColor(1)','    static let black=UIColor(1),white=UIColor(1),clear=UIColor(0)\n    convenience init(white:CGFloat,alpha:CGFloat){self.init(alpha)}\n    func withAlphaComponent(_ value:CGFloat)->UIColor{UIColor(value)}')
 t=t.replace('var frame=CGRect.zero,mask:CALayer?,isHidden=false','var frame=CGRect.zero,mask:CALayer?,isHidden=false\n    var borderWidth:CGFloat=0,cornerRadius:CGFloat=0;var borderColor:CGColor?')
 t=t.replace('    var clipsToBounds=false','    var clipsToBounds=false,isAccessibilityElement=false,isHidden=false\n    var accessibilityTraits:UIAccessibilityTraits=[];var accessibilityLabel:String?\n    var effectiveUserInterfaceLayoutDirection=UIUserInterfaceLayoutDirection.leftToRight')
 t=t.replace('final class UIImage {}', '''final class UIImage {
 enum Weight {case regular,semibold}
 class SymbolConfiguration {init(pointSize:CGFloat,weight:Weight){};init(paletteColors:[UIColor]){}}
 let symbol:String;let radius:CGFloat
 init(symbol:String="",radius:CGFloat=0){self.symbol=symbol;self.radius=radius}
 convenience init?(systemName:String,withConfiguration:SymbolConfiguration){self.init(symbol:systemName)}
 func withConfiguration(_ config:SymbolConfiguration)->UIImage?{self}
}''')
 t=t.replace('final class UIImageView:UIView {var image:UIImage?}','final class UIImageView:UIView {var image:UIImage?;var tintColor:UIColor?;var contentMode=UIViewContentMode.scaleAspectFit}')
 t=t.replace('final class UIBlurEffect {enum Style {case light,dark};init(style:Style){}}\nfinal class UIVisualEffectView:UIView {init(effect:UIBlurEffect){super.init()}}','''class UIVisualEffect {}
final class UIBlurEffect:UIVisualEffect {enum Style{case light,dark};init(style:Style){}}
final class UIGlassEffect:UIVisualEffect {enum Style{case regular};var isInteractive=true;init(style:Style){}}
final class UIVisualEffectView:UIView {var effect:UIVisualEffect?;let contentView=UIView();var overrideUserInterfaceStyle=UIUserInterfaceStyle.dark;init(effect:UIVisualEffect){self.effect=effect;super.init()}}''')
 t=t.replace('final class ActionSheetItemNode:ASDisplayNode {','class ActionSheetItemNode:ASDisplayNode {\n    let backgroundNode=ASDisplayNode()\n    init(theme:ActionSheetControllerTheme){self.height=52;super.init();view.addSubview(highlight)}\n    func requestLayoutUpdate(){}\n    func updateInternalLayout(_ size:CGSize,constrainedSize:CGSize){}')
 t=t.replace('var dimColor:UIColor,itemBackgroundColor=UIColor(1),backgroundType=Background.dark','''var dimColor=UIColor(0.5),itemBackgroundColor=UIColor(1),backgroundType=Background.dark
    var itemHighlightedBackgroundColor=UIColor(0.2),controlAccentColor=UIColor(1),controlColor=UIColor(0.5),secondaryTextColor=UIColor(0.6),primaryTextColor=UIColor(1)
    var baseFontSize:CGFloat=17''')
 t=t.replace('var frame:CGRect{get{view.frame}set{view.frame=newValue}}','var frame:CGRect{get{view.frame}set{view.frame=newValue}}\n    var backgroundColor:UIColor?{get{view.backgroundColor}set{view.backgroundColor=newValue}}')
 t=t.replace('->UIImage?{UIImage()}','->UIImage?{UIImage(radius:radius)}')
 t+='\n'+(ROOT/'scripts/tests/NagramiXUnifiedMenusBoundary.swift').read_text()+'\n'
 models=[('submodules/NagramiXCore/Sources/NagramiXTabSettings.swift','public enum NagramiXDnsProvider:'),('submodules/NagramiXCore/Sources/NagramiXTypingSettings.swift','public enum NagramiXTypingPreset:'),('submodules/NagramiXMediaSettings/Sources/NagramiXDownloadSettings.swift','public enum NagramiXDownloadAcceleration:')]
 for path,marker in models:t+=block((source/path).read_text(),marker)+'\n'
 return t

def fixture(source):
 import re
 text=production(source).replace('private ','fileprivate ').replace('public ','').replace('@objc ','').replace('if #available(iOS 26.0, *), glass','if fixtureGlassAvailable, glass')
 text=re.sub(r'#selector\(self\.pressed\)','"pressed"',text)
 return boundary(source)+'\n'+text+'\n'+(ROOT/'scripts/tests/NagramiXUnifiedMenusTests.swift').read_text()

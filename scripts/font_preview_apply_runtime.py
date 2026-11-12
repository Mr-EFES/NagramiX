"""Настоящие draft/обработчики/геометрия с явно ограниченными UIKit doubles."""
from validate_quick_format import block
from app_font_selection_runtime import MODEL,UI
from validate_upstream_13_2_release import checked_plan,OVERLAY
import hashlib

IMPORTS='import Foundation\n#if canImport(CoreGraphics)\nimport CoreGraphics\n#endif\n'

def fixture(source):
    ui=(source/UI).read_text();model=(source/MODEL).read_text()
    handlers=[]
    for marker in ['    @objc private func segmentChanged()', '    @objc private func openLicenses()', '    @objc private func applyTapped()', '    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath)']:
        handlers.append(block(ui,marker).replace('@objc private ','').replace('public ',''))
    layout=block(ui,'    private func arrange()').replace('private ','',1)
    card=block(ui,'private final class NagramiXFontPreviewCard: UIView').replace('private ','')
    helper=block(ui,'private func nagramiXFontLabelHeight(').replace('private ','',1)
    viewport=block(ui,'private func nagramiXFontComparisonViewport(').replace('private ','',1)
    plan=checked_plan('font_preview_apply')
    legal=[]
    for name,expected in plan['guards'].items():
        if not name.endswith('.txt'):continue
        path=source/name
        data=path.read_bytes() if path.exists() else (OVERLAY/plan['guard_sources'][name]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==expected,name
        raw=data.decode();legal.append('"'+raw.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t')+'"')
    tests=TESTS.replace('CommandLine.arguments.dropFirst().map{try! String(contentsOfFile:$0,encoding:.utf8)}','['+','.join(legal)+']')
    return IMPORTS+model+BOUNDARY+card+'\n'+helper+'\n'+viewport+'''
let NagramiXFontNumberSample = " · 12345"
func nagramiXFontTitle(_ entry:NagramiXFontEntry,strings:PresentationStrings)->String {entry.name}
final class ActualFontScreenProbe {
 var draft=NagramiXFontSelectionDraft(NagramiXFontSettings.current)
 var entries=NagramiXFontEntry.catalog
 let context=0
 var refreshes=0;var pushes=0
 func refresh(){refreshes+=1}
 func push(_ value:NagramiXFontLicensesController){pushes+=1}
 var presentation=PresentationData()
 var validLayout:ContainerViewLayout?
 let content=UIScrollView();let table=UITableView()
 let currentCard=NagramiXFontPreviewCard();let previewCard=NagramiXFontPreviewCard();let measuringCard=NagramiXFontPreviewCard()
 let comparisonTitle=UILabel();let listTitle=UILabel();let comparison=UIScrollView();let segment=UIView()
 let licenseTitle=UILabel();let licenseButton=UIView();let licenseIcon=UIView();let licenseArrow=UIView()
 func navigationLayout(layout:ContainerViewLayout)->NavigationLayout {NavigationLayout(navigationFrame:CGRect(x:0,y:0,width:layout.size.width,height:layout.navigationHeight))}
'''+'\n'.join(handlers)+'\n'+layout+'\n}\n'+tests

BOUNDARY=r'''
struct UIEdgeInsets {var top:CGFloat=0;var left:CGFloat=0;var bottom:CGFloat=0;var right:CGFloat=0;static let zero=Self()}
class UIView {
 var frame:CGRect;var bounds:CGRect {CGRect(origin:.zero,size:frame.size)}
 var layer=Layer();var backgroundColor:UIColor?;var accessibilityElements:[Any]?
 init(frame:CGRect){self.frame=frame}
 convenience init(){self.init(frame:.zero)}
 func addSubview(_ view:UIView){}
}
final class Layer {var cornerRadius:CGFloat=0}
struct UIColor {func withAlphaComponent(_ value:CGFloat)->UIColor{self}}
final class UIFont {var size:CGFloat;init(_ size:CGFloat){self.size=size};var lineHeight:CGFloat{size*1.2}}
enum Font {static func regular(_ size:CGFloat)->UIFont{UIFont(size)};static func semibold(_ size:CGFloat)->UIFont{UIFont(size)};static func medium(_ size:CGFloat)->UIFont{UIFont(size)}}
final class UILabel:UIView {
 var text:String?;var font=UIFont(17);var textColor=UIColor();var numberOfLines=0
 func sizeThatFits(_ size:CGSize)->CGSize {
  let length=CGFloat((text ?? "").count)*font.size*0.58
  return CGSize(width:min(size.width,length),height:ceil(max(1,length/max(1,size.width)))*font.lineHeight)
 }
}
class UIScrollView:UIView {var contentSize=CGSize.zero;var contentOffset=CGPoint.zero;var isScrollEnabled=true;var contentInset=UIEdgeInsets.zero;var scrollIndicatorInsets=UIEdgeInsets.zero}
final class UITableView:UIScrollView {var deselections=0;func deselectRow(at:IndexPath,animated:Bool){deselections+=1}}
extension IndexPath {init(row:Int,section:Int){self.init(indexes:[section,row])};var row:Int{self[1]}}
struct ContainerViewLayout {var size:CGSize;var navigationHeight:CGFloat;var intrinsicInsets=UIEdgeInsets.zero;var safeInsets=UIEdgeInsets.zero}
struct NavigationLayout {var navigationFrame:CGRect}
struct PresentationStrings {func nagramiXLocalized(_ key:String)->String {
 if key.hasSuffix("PreviewText"){return "Hello! This is NagramiX."}
 if key.hasSuffix("Sample"){return "Aa Bb"};return key
}}
struct CheckColors {var foregroundColor=UIColor()}
struct ListTheme {var itemBlocksBackgroundColor=UIColor();var itemPrimaryTextColor=UIColor();var itemSecondaryTextColor=UIColor();var itemAccentColor=UIColor();var itemCheckColors=CheckColors()}
struct Theme {var list=ListTheme()}
struct ListFontSize {var itemListBaseFontSize:CGFloat=17}
struct PresentationData {var listsFontSize=ListFontSize();var theme=Theme();var strings=PresentationStrings()}
enum NagramiXFontManager {
 static var unavailable:Set<String>=[]
 static func available(_ entry:NagramiXFontEntry)->Bool {!unavailable.contains(entry.id)}
 static func previewFont(_ entry:NagramiXFontEntry,size:CGFloat)->UIFont{UIFont(size)}
}
final class NagramiXFontLicensesController {init(context:Int){}}
'''
TESTS=r'''
@main struct FontPreviewTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Font preview regression: "+why+"\n").utf8));exit(96)};checks+=1}
  let defaults=UserDefaults.standard
  let oldEnabled=defaults.object(forKey:"nagramix.fonts.enabled");let oldID=defaults.object(forKey:"nagramix.fonts.selection.v1")
  defer {defaults.set(oldEnabled,forKey:"nagramix.fonts.enabled");defaults.set(oldID,forKey:"nagramix.fonts.selection.v1")}
  defaults.removeObject(forKey:"nagramix.fonts.enabled");defaults.removeObject(forKey:"nagramix.fonts.selection.v1")
  check(NagramiXFontSettings.current == .init(),"fresh default preserved")
  for enabled in [true,false] {
   defaults.set(enabled,forKey:"nagramix.fonts.enabled");defaults.set("system",forKey:"nagramix.fonts.selection.v1")
   let original=NagramiXFontSettings.current
   let controller=ActualFontScreenProbe();let table=UITableView()
   let notices=NotificationCounter()
   let observer=NotificationCenter.default.addObserver(forName:NagramiXFontSettings.changed,object:nil,queue:nil){_ in notices.count+=1}
   defer {NotificationCenter.default.removeObserver(observer)}
   for (index,entry) in NagramiXFontEntry.catalog.enumerated() {
    controller.tableView(table,didSelectRowAt:IndexPath(row:index,section:0))
    check(controller.draft.fontId==entry.id,"candidate changes")
    check(controller.draft.applied==original,"current card stays applied")
    check(NagramiXFontSettings.current==original && notices.count==0,"row selection never persists or notifies")
    controller.segmentChanged();controller.openLicenses()
    check(controller.draft.fontId==entry.id && NagramiXFontSettings.current==original,"tabs and licenses retain draft without applying")
   }
   let reopened=ActualFontScreenProbe()
   check(reopened.draft.fontId==original.fontId,"back discards draft")
   controller.tableView(table,didSelectRowAt:IndexPath(row:-1,section:0))
   let proposed=controller.draft.proposed
   controller.applyTapped()
   check(NagramiXFontSettings.current==proposed && notices.count==1,"Apply persists once")
   check(!controller.draft.canApply && controller.draft.applied==proposed,"Apply updates current and clears dirty state")
   controller.applyTapped();check(notices.count==1,"unchanged Apply is inert")
   controller.draft.select("bundled.roboto");NagramiXFontManager.unavailable.insert("bundled.roboto")
   controller.applyTapped();check(NagramiXFontSettings.current==proposed && notices.count==1,"unavailable candidate cannot apply")
   let index=NagramiXFontEntry.catalog.firstIndex(where:{$0.id=="bundled.roboto"})!
   let pending=controller.draft.fontId
   controller.tableView(table,didSelectRowAt:IndexPath(row:index,section:0))
   check(controller.draft.fontId==pending,"unavailable row ignored")
   NagramiXFontManager.unavailable.removeAll()
  }
  var draft=NagramiXFontSelectionDraft(.init(enabled:false,fontId:"bundled.astra-sans"))
  check(draft.canApply,"saved OFF can only be enabled by Apply")
  draft.synchronize(.init(fontId:"ios.arial"));check(draft.fontId=="ios.arial","unmodified draft follows external change")
  draft.select("bundled.astra-serif");draft.synchronize(.init(fontId:"system.rounded"))
  check(draft.fontId=="bundled.astra-serif" && draft.applied.fontId=="system.rounded","external change keeps pending candidate")
  draft.select("unknown");check(draft.fontId=="bundled.astra-serif","invalid IDs ignored")
  let inputs=CommandLine.arguments.dropFirst().map{try! String(contentsOfFile:$0,encoding:.utf8)}
  check(inputs.count==4,"all full license originals supplied")
  for raw in inputs {
   let paragraphs=NagramiXFontLicenseLayout.paragraphs(raw)
   let tokens:(String)->[Substring] = {$0.split(whereSeparator:{$0.isWhitespace})}
   check(tokens(paragraphs.joined(separator:" "))==tokens(raw),"every original legal word retained in order")
   check(paragraphs.allSatisfy{!$0.contains("\n") && !$0.isEmpty},"hard wrapping removed inside paragraphs")
   check(paragraphs.count>1,"legal paragraphs remain separate")
  }
  // Execute the actual card and controller layout, not a copied formula.
  for size in [CGSize(width:320,height:568),CGSize(width:390,height:844),CGSize(width:430,height:932),CGSize(width:844,height:390),CGSize(width:1024,height:768)] {
   for base:CGFloat in [17,23,34,53] {
    let c=ActualFontScreenProbe();c.presentation.listsFontSize.itemListBaseFontSize=base
    let layout=ContainerViewLayout(size:size,navigationHeight:88,intrinsicInsets:UIEdgeInsets(bottom:34),safeInsets:UIEdgeInsets(left:size.width>800 ? 44:0,bottom:34,right:0))
    c.validLayout=layout
    c.comparisonTitle.text="COMPARISON";c.listTitle.text="CHOOSE FONT";c.licenseTitle.text=String(repeating:"License ",count:base>30 ? 7:2)
    for label in [c.comparisonTitle,c.listTitle,c.licenseTitle] {label.font=UIFont(base)}
    var stable:CGRect?
    for entry in NagramiXFontEntry.catalog {
     c.currentCard.configure(heading:"Current",entry:.system,presentation:c.presentation)
     c.previewCard.configure(heading:"Preview",entry:entry,presentation:c.presentation)
     c.arrange()
     check(c.currentCard.frame.maxX<=c.comparison.contentSize.width && c.previewCard.frame.maxX<=c.comparison.contentSize.width,"cards stay inside width")
     check(c.currentCard.frame.maxY<=c.comparison.contentSize.height && c.previewCard.frame.maxY<=c.comparison.contentSize.height,"comparison content reaches both cards")
     check(c.table.frame.height>=65,"font list remains accessible")
     check(c.comparison.frame.maxY<=c.segment.frame.minY && c.segment.frame.maxY<=c.listTitle.frame.minY,"pinned areas do not overlap")
     check(c.listTitle.frame.maxY<=c.table.frame.minY && c.table.frame.maxY<c.licenseButton.frame.minY,"list and license never overlap")
     check(c.licenseButton.frame.maxY<=c.content.contentSize.height && c.content.frame.maxY<=size.height-34,"safe bottom retained")
     check(c.table.frame.minX>=20+layout.safeInsets.left-4 && c.table.frame.maxX<=size.width-20,"safe side gutters")
     check(stable==nil || stable==c.table.frame,"candidate does not move list")
     stable=c.table.frame
    }
    if size==CGSize(width:390,height:844) && base==17 {check(!c.content.isScrollEnabled,"normal portrait keeps comparison fixed")}
   }
  }
  print("Font preview production checks: \(checks)")
 }
}
final class NotificationCounter {var count=0}
'''

def negatives(code):
    variants=[
        ('row-immediate-save','self.draft.select(entry.id)','NagramiXFontSettings.update { $0.enabled = true; $0.fontId = entry.id }; self.draft.select(entry.id)','row selection never persists or notifies'),
        ('apply-does-not-save','NagramiXFontSettings.update { $0 = proposed }','_ = proposed','Apply persists once'),
        ('external-overwrites-draft','if !self.edited { self.fontId = settings.fontId }','self.fontId = settings.fontId','external change keeps pending candidate'),
        ('lost-legal-content','result.append(lines.joined(separator: " "))','result.append(lines.dropFirst().joined(separator: " "))','every original legal word retained in order'),
        ('no-accessibility-scroll','fixed + 72 > visibleHeight ? fixed + 72 + min(160, contentHeight) : visibleHeight','visibleHeight','font list remains accessible'),
    ]
    for name,old,new,label in variants:
        assert old in code,name
        yield name,code.replace(old,new),label

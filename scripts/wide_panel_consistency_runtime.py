"""Фактическая геометрия native панелей; UIKit/измерение текста заданы явной границей."""
from validate_quick_format import block
from validate_wide_bottom_bar import NODE, COMP, CORE, ITEMS

ATTACH='submodules/AttachmentUI/Sources/AttachmentPanel.swift'
SELECT='submodules/TelegramUI/Components/TabSelectorComponent/Sources/TabSelectorComponent.swift'
BOUNDARY='''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
#if os(Linux)
import Glibc
#else
import Darwin
#endif
'''

def fixture(source):
    a=(source/ATTACH).read_text();s=(source/SELECT).read_text();t=(source/COMP).read_text()
    constants=a[a.index('private let legacyButtonSize'):a.index('private final class IconComponent:')]
    layout=(source/ITEMS).read_text().replace('import UIKit\n','').replace('import Display\n','')
    root=block((source/NODE).read_text(),'private func nagramiXTabBarFillsAvailableWidth(')
    # Execute the actual production frame arithmetic, not a second geometry formula.
    av=a[a.index('        var width = layout.size.width',a.index('    func updateViews(')):a.index('        var validIds = Set<AnyHashable>()',a.index('    func updateViews('))]
    item=a[a.index('            let originX = floorToScreenPixels(leftNodeOriginX'):a.index('            mostRightX = buttonFrame.maxX',a.index('            let originX = floorToScreenPixels(leftNodeOriginX'))]
    start=t.index('            let itemsLayout: TabBarItemsLayout');end=t.index('            let tabsSize = itemsLayout.size',start)
    tl=t[start:end]
    inset=block(s,'private func nagramiXWideSelectorInset(')
    sl=s[s.index('            let estimatedContentWidth ='):s.index('            var contentWidth: CGFloat = spacing')]
    sf=s[s.index('                if contentWidth > spacing {'):s.index('                let itemTitleFrame =',s.index('                if contentWidth > spacing {'))].replace('var itemBackgroundRect =','let itemBackgroundRect =')
    # Production observer, including weak capture and actual ComponentState API.
    obs=t[t.index('            self.nagramiXWidePanelObserver ='):t.index('\n\n',t.index('            self.nagramiXWidePanelObserver ='))]
    assert obs in s
    native=(source/'submodules/ComponentFlow/Source/Base/Component.swift').read_text()
    state=block(native,'open class ComponentState {')+'\n'+block(native,'public final class EmptyComponentState:')
    return BOUNDARY+'''
public let UIScreenScale: CGFloat = 3
func floorToScreenPixels(_ v: CGFloat) -> CGFloat { floor(v * UIScreenScale) / UIScreenScale }
enum NagramiXTabSettings {
    static var wideTabBarEnabled = true
    static let changedNotification = Notification.Name("widePanelFixture")
}
struct ContainerViewLayout { let size: CGSize; let left: CGFloat; let right: CGFloat
    func bottomEdgeSideInsets() -> (left:CGFloat,right:CGFloat) { (left,right) }
    var safeInsets:(left:CGFloat,right:CGFloat) { (left,right) }
}
enum Style { case glass,legacy }
struct Item { let id: Int }
struct CustomLayout { let fillWidth:Bool }
struct ComponentAdapter {
    let axis:TabBarAxis; let isCompact:Bool; let fillsAvailableWidth:Bool
    let items:[Item]; let style:Style; let customLayout:CustomLayout?
}
public enum ComponentTransition { case immediate }
'''+state+'\n'+constants+layout+root+'\n'+inset+'''
final class ObserverAdapter {
    private weak var state: EmptyComponentState?
    private var nagramiXWidePanelObserver: NSObjectProtocol?
    private var nagramiXLastWidePanel = NagramiXTabSettings.wideTabBarEnabled
    init(_ state:EmptyComponentState) { self.state=state
'''+obs+'''
    }
    deinit { if let observer = self.nagramiXWidePanelObserver { NotificationCenter.default.removeObserver(observer) } }
}
final class AttachmentAdapter {
    let panelStyle:Style
    var buttonSize:CGSize { panelStyle == .glass ? glassButtonSize : legacyButtonSize }
    init(_ style:Style) { self.panelStyle=style }
    func frames(layout:ContainerViewLayout,buttons:[Int]) -> [CGRect] {
'''+av+'''
        var frames:[CGRect]=[]
        for i in 0..<buttons.count {
'''+item+'''
            frames.append(buttonFrame)
        }
        return frames
    }
}
func renderedTabBar(_ titles:[CGFloat],_ budget:CGFloat,_ search:Bool,_ system:Bool,_ compact:Bool,_ axis:TabBarAxis) -> TabBarItemsLayout {
    let component=ComponentAdapter(axis:axis,isCompact:compact,fillsAvailableWidth:false,items:titles.indices.map{Item(id:$0)},style:.glass,customLayout:nil)
    let isSystemLayout=system, titleWidths=titles, availableLength=budget
    let search:Int?=search ? 1:nil
'''+tl+'''
    return itemsLayout
}
func renderedSelector(_ titles:[CGFloat],_ width:CGFloat,_ style:Style = .glass,_ line:Bool = false,_ fill:Bool = false,_ scroll:Bool = true) -> (CGFloat,[CGRect]) {
    let component=ComponentAdapter(axis:.horizontal,isCompact:false,fillsAvailableWidth:false,items:titles.indices.map{Item(id:$0)},style:style,customLayout:CustomLayout(fillWidth:fill))
    let availableSize=CGSize(width:width,height:32), innerContentWidth=titles.reduce(0,+), isLineSelection=line, allowScroll=scroll
    var innerInset:CGFloat=12, spacing:CGFloat=2
'''+sl+'''
    var contentWidth=spacing, frames:[CGRect]=[]
    let verticalInset:CGFloat=0, baseHeight:CGFloat=32
    for title in titles {
        let itemSize=CGSize(width:title,height:18)
'''+sf+'''
        _ = baseItemTitleFrame
        contentWidth=itemBackgroundRect.maxX;frames.append(itemBackgroundRect)
    }
    contentWidth+=spacing
    return (contentWidth,frames)
}
var checks=0
func check(_ value:Bool,_ label:String) { if !value { print("FAIL "+label);exit(91) };checks+=1 }
func near(_ a:CGFloat,_ b:CGFloat)->Bool { abs(a-b)<0.00001 }
@main struct WidePanelChecks {
    static func main() {
        for enabled in [false,true] {
            NagramiXTabSettings.wideTabBarEnabled=enabled
            for count in 0...6 { for search in [false,true] { for side in [false,true] { for compact in [false,true] { for wide in [false,true] {
                check(nagramiXTabBarFillsAvailableWidth(itemCount:count,showSearchButton:search,hasSidePlacement:side,isCompact:compact,isWide:wide,wideTabBar:enabled) == (enabled && count>=2 && !side && !compact && !wide),"root-policy")
            }}}}}
            for width:CGFloat in [320,375,393,430,568,844,1024] { for safe:CGFloat in [0,34,59] { for n in 2...8 {
                let layout=ContainerViewLayout(size:CGSize(width:width,height:900),left:safe,right:0)
                let frame=glassTabBarFrame(layout:layout,buttonCount:n,widePanel:enabled)
                let native=glassTabBarFrame(layout:layout,buttonCount:n)
                check(near(frame.height,62),"native-height")
                if enabled {
                    check(near(frame.width,width-safe-44),"attachment-wide-background")
                    check(near(frame.minX,safe+22),"attachment-safe-inset")
                } else { check(frame==native,"attachment-off-native") }
                let frames=AttachmentAdapter(.glass).frames(layout:layout,buttons:Array(0..<n))
                if enabled && (frame.width-6)/CGFloat(n)>=72 {
                    check(near(frames[0].minX,0),"attachment-first-slot")
                    check(abs(frames.last!.maxX-(frame.width-6))<1.0/UIScreenScale+0.0001,"attachment-full-slots")
                    check(frames.allSatisfy{near($0.width,(frame.width-6)/CGFloat(n))},"attachment-slot-width")
                    for f in frames { check(f.width>=72 && f.height==62,"attachment-touch-target") }
                }
                if enabled && n>5 && (frame.width-6)/CGFloat(n)<72 {
                    check(frames[0].width==72 && near(frames[1].minX-frames[0].minX,62),"attachment-overflow-scroll")
                }
                NagramiXTabSettings.wideTabBarEnabled=false
                let legacyOff=AttachmentAdapter(.legacy).frames(layout:layout,buttons:Array(0..<n))
                NagramiXTabSettings.wideTabBarEnabled=enabled
                check(legacyOff==AttachmentAdapter(.legacy).frames(layout:layout,buttons:Array(0..<n)),"legacy-unchanged")
            }}}
            for width:CGFloat in [278,333,351,388,500,800] { for n in 2...6 { for search in [false,true] {
                let budget=width-(search ? 70:0), titles=Array(repeating:CGFloat(54),count:n)
                let result=renderedTabBar(titles,budget,search,true,false,.horizontal)
                check(result==tabBarSystemItemsLayout(fittedItemWidths:titles,availableLength:budget,hasAccessory:search || enabled),"native-system-layout")
                if enabled { check(near(result.size.width,budget),"all-root-tabs-wide") }
                for axis in [TabBarAxis.horizontal,.vertical] {
                    check(renderedTabBar(titles,budget,search,false,true,axis)==tabBarItemsLayout(axis:axis,isCompact:true,unboundItemWidths:titles.map{$0+20},availableLength:budget),"compact-sidebar-native")
                }
            }}}
            for width:CGFloat in [278,333,351,388,500] { for titles:[CGFloat] in [[25,35],[35,85,40],[30,40,35,50],[240,260],[40]] {
                let result=renderedSelector(titles,width)
                if enabled && titles.count>1 && titles.reduce(0,+)+CGFloat(titles.count)*24+CGFloat(titles.count+1)*2<=width {
                    check(near(result.0,width),"selector-wide")
                    check(result.1.allSatisfy{$0.width>=24 && $0.minX>=0 && $0.maxX<=width},"selector-safe-frames")
                }
                for line in [false,true] { for style in [Style.glass,.legacy] { for fill in [false,true] {
                    NagramiXTabSettings.wideTabBarEnabled=false
                    let off=renderedSelector(titles,width,style,line,fill)
                    NagramiXTabSettings.wideTabBarEnabled=enabled
                    let on=renderedSelector(titles,width,style,line,fill)
                    if line || style == .legacy || titles.count<=1 || titles.reduce(0,+)+CGFloat(titles.count)*24+CGFloat(titles.count+1)*2>width {
                        check(on.0==off.0 && on.1==off.1,"selector-native-fallback")
                    }
                }}}
            }}
        }
        NagramiXTabSettings.wideTabBarEnabled=true
        let state=EmptyComponentState();var notifications=0
        state._updated={_,_ in notifications+=1}
        var observer:ObserverAdapter?=ObserverAdapter(state)
        weak var weakObserver=observer
        NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
        check(notifications==0,"unrelated-setting-no-layout")
        NagramiXTabSettings.wideTabBarEnabled=false
        NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
        check(notifications==1,"live-off-layout")
        NagramiXTabSettings.wideTabBarEnabled=true
        NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
        check(notifications==2,"live-on-layout")
        observer=nil;check(weakObserver==nil,"weak-observer-lifetime")
        NotificationCenter.default.post(name:NagramiXTabSettings.changedNotification,object:nil)
        check(notifications==2,"observer-removed")
        print("PASS wide panel production checks: \\(checks)")
    }
}
'''

def negatives(text):
    for name,old,new,label in [
        ('narrow-attachments','width = max(0.0, availableWidth - glassPanelInset * 2.0)','width = twoButtonPanelWidth','attachment-wide-background'),
        ('narrow-touch-slots','buttonWidth = itemWidth','buttonWidth = self.buttonSize.width','attachment-first-slot'),
        ('narrow-other-root-tabs','itemCount >= 2','itemCount == 2','root-policy'),
        ('missing-shared-bar','NagramiXTabSettings.wideTabBarEnabled && component.items.count > 1','component.items.count > 99','native-system-layout'),
        ('narrow-selector','innerInset = wideInset','innerInset = min(12.0,wideInset)','selector-wide'),
        ('stale-live-layout','self.state?.updated(transition: .immediate)','_ = self.state','live-off-layout'),
    ]:
        assert old in text,name
        yield name,text.replace(old,new,1),'FAIL '+label

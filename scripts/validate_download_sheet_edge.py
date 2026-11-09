#!/usr/bin/env python3
"""Execute native sheet layout and real selection factory in bounded adapters."""
import argparse,json,subprocess,tempfile,resource
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks

ROOT=Path(__file__).resolve().parents[1]
STAGE='download_sheet_edge'
DISPLAY='submodules/Display/Source/'
C=DISPLAY+'ActionSheetController.swift'
N=DISPLAY+'ActionSheetControllerNode.swift'
G=DISPLAY+'ActionSheetItemGroupNode.swift'
GS=DISPLAY+'ActionSheetItemGroupsContainerNode.swift'
O='submodules/SettingsUI/Sources/NagramiXOptionSheet.swift'
S='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'

def clean(text):
    return text.replace('private ','').replace('public ','').replace('fileprivate ','')

def run(command,**kw):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,**kw)
    assert result.returncode==0,result.stdout+result.stderr
    return result

def layout_fixture(source):
    plan=checked_plan(STAGE)
    read=lambda p:(source/p).read_text()
    old=lambda p:(ROOT/'ios'/plan['previous'][p]).read_text()
    result=LAYOUT_BOUNDARY
    for legacy in [False,True]:
        label='Legacy' if legacy else ''
        n,g,gs=(old(p) if legacy else read(p) for p in [N,G,GS])
        group='''
final class GROUP:Node {
    let theme=Theme()
    let centerDimView=ImageView()
    let clippingNode=Node()
    let scrollNode=Node()
    let backgroundEffectView=View()
    let nagramiXBottomPaddingView=View()
    var itemNodes:[ItemNode]=[]
    var leadingVisibleNodeCount:CGFloat=1000
    var validLayout:CGSize?
    var overlayNode:Overlay?
    var nagramiXBottomPadding:CGFloat=0
    PROP
    func updateOverscroll(size:CGSize,transition:ContainedViewLayoutTransition){}
    METHOD
}
'''.replace('GROUP',label+'Group')
        prop='var nagramiXTopCornersOnly=false' if legacy else clean(block(g,'    var nagramiXTopCornersOnly = false {'))
        group=group.replace('PROP',prop).replace('METHOD',clean(block(g,'    func updateLayout(constrainedSize:')))
        groups='''
final class GROUPS:Node {
    var groupNodes:[GROUP]=[]
    var validSize:CGSize?
    var nagramiXBottomPadding:CGFloat=0
    var nagramiXTopCornersOnly=false
    METHOD
}
'''.replace('GROUPS',label+'Groups').replace('GROUP',label+'Group')
        groups=groups.replace('METHOD',clean(block(gs,'    func updateLayout(constrainedSize:')))
        sheet='''
final class SHEET {
    var allowInputInset=false
    var nagramiXBottomAttached=false
    let itemGroupsContainerNode=GROUPS()
    let scrollView=View()
    let dismissTapView=View()
    let leftDimView=View(),rightDimView=View(),topDimView=View(),bottomDimView=View()
    var validLayout:ContainerViewLayout?
    METHODS
}
'''.replace('SHEET',label+'Sheet').replace('GROUPS',label+'Groups')
        methods=[]
        if not legacy:
            methods += [clean(block(n,m)) for m in ['    private var nagramiXUsesBottomAttachedLayout:', '    private var nagramiXContainerInsets:']]
        methods += [clean(block(n,m)) for m in ['    func containerLayoutUpdated(', '    func updateScrollDimViews(', '    func scrollViewDidScroll(']]
        sheet=sheet.replace('METHODS','\n'.join(methods))
        result+='\n'+group+groups+sheet
    return result+LAYOUT_TESTS

LAYOUT_BOUNDARY=r'''
import Foundation
struct UIEdgeInsets:Equatable {
    var top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0
    init(top:CGFloat=0,left:CGFloat=0,bottom:CGFloat=0,right:CGFloat=0){self.top=top;self.left=left;self.bottom=bottom;self.right=right}
}
#if os(Linux)
extension CGRect {func equalTo(_ other:CGRect)->Bool {self==other}}
extension CGSize {func equalTo(_ other:CGSize)->Bool {self==other}}
#endif
struct InsetsOptions:OptionSet {let rawValue:Int;static let statusBar=Self(rawValue:1)}
struct ContainerViewLayout {
    var size:CGSize;var intrinsicInsets=UIEdgeInsets();var safeInsets=UIEdgeInsets();var inputHeight:CGFloat?
    var sideLeft:CGFloat=0,sideRight:CGFloat=0
    func insets(options:InsetsOptions)->UIEdgeInsets {var result=intrinsicInsets;result.top=max(result.top,44);return result}
}
let containerInsets=UIEdgeInsets(top:10,left:10,bottom:10,right:10)
let groupSpacing:CGFloat=8,UIScreenPixel:CGFloat=1.0/3
func actionSheetSideInsets(layout:ContainerViewLayout)->(left:CGFloat,right:CGFloat){(layout.sideLeft,layout.sideRight)}
func floorToScreenPixels(_ v:CGFloat)->CGFloat {floor(v*3)/3}
struct CornerMask:OptionSet {
    let rawValue:Int
    static let layerMinXMinYCorner=Self(rawValue:1),layerMaxXMinYCorner=Self(rawValue:2),layerMinXMaxYCorner=Self(rawValue:4),layerMaxXMaxYCorner=Self(rawValue:8)
}
final class Layer {var maskedCorners:CornerMask=[.layerMinXMinYCorner,.layerMaxXMinYCorner,.layerMinXMaxYCorner,.layerMaxXMaxYCorner]}
class View {
    var frame=CGRect.zero
    var contentSize=CGSize.zero,contentOffset=CGPoint.zero,contentInset=UIEdgeInsets()
    var bounces=true
    let layer=Layer()
}
class ImageView:View {var image:String?}
typealias UIScrollView=View
class Node {
    let view=View();let trailingDimView=View()
    var frame:CGRect {get{view.frame}set{view.frame=newValue}}
    var bounds:CGRect {CGRect(origin:.zero,size:frame.size)}
    var layer:Layer {view.layer}
}
enum ContainedViewLayoutTransition {
    case immediate,animated
    func updateFrame(node:Node,frame:CGRect){node.frame=frame}
    func updateFrame(view:View,frame:CGRect){view.frame=frame}
}
struct Theme {let dimColor=1}
func nagramiXActionSheetTopCornerDimImage(color:Int)->String? {"top"}
func generateStretchableFilledCircleImage(radius:CGFloat,color:Int?,backgroundColor:Int)->String? {"all"}
final class Overlay {func updateLayout(size:CGSize,transition:ContainedViewLayoutTransition){}}
final class ItemNode:Node {
    var height:CGFloat;var hasSeparator=false
    init(_ height:CGFloat){self.height=height}
    func updateLayout(constrainedSize:CGSize,transition:ContainedViewLayoutTransition)->CGSize {CGSize(width:constrainedSize.width,height:height)}
}
'''

LAYOUT_TESTS=r'''
@main struct SheetLayoutTests {
    static func main() {
        var checks=0
        func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Sheet regression: "+s+"\n").utf8));exit(91)};checks+=1}
        for size in [CGSize(width:320,height:568),CGSize(width:393,height:852),CGSize(width:430,height:932),CGSize(width:852,height:393),CGSize(width:834,height:1194)] {
            for safe:CGFloat in [0,21,34] {for heights:[CGFloat] in [[88,84,84,64],[120,140,140,110],[230,400,400,250]] {
                var layout=ContainerViewLayout(size:size);layout.intrinsicInsets.bottom=safe;layout.safeInsets.bottom=safe
                if size.width>size.height {layout.sideLeft=44;layout.sideRight=44}
                let sheet=Sheet(),group=Group();group.itemNodes=heights.map(ItemNode.init);sheet.itemGroupsContainerNode.groupNodes=[group]
                let old=LegacySheet(),oldGroup=LegacyGroup();oldGroup.itemNodes=heights.map(ItemNode.init);old.itemGroupsContainerNode.groupNodes=[oldGroup]
                sheet.containerLayoutUpdated(layout,transition:.immediate);old.containerLayoutUpdated(layout,transition:.immediate)
                check(sheet.itemGroupsContainerNode.frame==old.itemGroupsContainerNode.frame && group.frame==oldGroup.frame,"default floating frames remain native")
                check(group.scrollNode.view.contentSize==oldGroup.scrollNode.view.contentSize && group.scrollNode.view.contentInset==oldGroup.scrollNode.view.contentInset,"default floating scroll geometry remains native")
                sheet.nagramiXBottomAttached=true;sheet.containerLayoutUpdated(layout,transition:.immediate)
                let frame=sheet.itemGroupsContainerNode.frame
                check(abs(frame.maxY-size.height)<0.001,"attached panel reaches screen bottom")
                check(frame.minX==layout.sideLeft && frame.width==size.width-layout.sideLeft-layout.sideRight,"portrait fills width while native landscape safe placement remains")
                check(group.nagramiXBottomPaddingView.frame.height==safe && group.nagramiXBottomPaddingView.frame.minY==heights.reduce(0,+),"safe area follows all measured rows and footer")
                check(group.scrollNode.view.contentSize.height==heights.reduce(0,+)+safe,"safe area included in scrolling content size")
                check(group.scrollNode.view.contentInset.top==0,"safe area does not shift content down from a false leading inset")
                check(group.layer.maskedCorners.rawValue==15,"unrelated group root layer untouched")
                check(group.clippingNode.layer.maskedCorners==[.layerMinXMinYCorner,.layerMaxXMinYCorner] && group.centerDimView.image=="top","only upper corners clipped and dimmed")
                check(!group.scrollNode.view.bounces,"inner overscroll cannot expose a lower strip")
                sheet.scrollView.contentOffset.y=45;sheet.scrollViewDidScroll(sheet.scrollView)
                check(sheet.scrollView.contentOffset.y==0,"upward outer bounce cannot lift attached panel")
                sheet.scrollView.contentOffset.y = -35;sheet.scrollViewDidScroll(sheet.scrollView)
                check(sheet.scrollView.contentOffset.y == -35,"downward native dismiss gesture remains available")
                sheet.nagramiXBottomAttached=false;sheet.containerLayoutUpdated(layout,transition:.immediate)
                check(group.nagramiXBottomPaddingView.frame.height==0 && group.scrollNode.view.bounces,"reused layout resets padding and native bounce")
                check(group.clippingNode.layer.maskedCorners.rawValue==15 && group.centerDimView.image=="all","reused floating layout restores four rounded corners")
            }}
        }
        let keyboard=Sheet(),g=Group();g.itemNodes=[ItemNode(200)];keyboard.itemGroupsContainerNode.groupNodes=[g];keyboard.allowInputInset=true;keyboard.nagramiXBottomAttached=true
        var layout=ContainerViewLayout(size:CGSize(width:393,height:852));layout.inputHeight=300
        keyboard.containerLayoutUpdated(layout,transition:.immediate)
        check(keyboard.itemGroupsContainerNode.frame.maxY==542 && !g.nagramiXTopCornersOnly,"keyboard sheets retain native positioning")
        let multiple=Sheet(),a=Group(),b=Group();a.itemNodes=[ItemNode(100)];b.itemNodes=[ItemNode(60)];multiple.itemGroupsContainerNode.groupNodes=[a,b];multiple.nagramiXBottomAttached=true
        multiple.containerLayoutUpdated(layout,transition:.immediate)
        check(multiple.itemGroupsContainerNode.frame.maxY==842 && !a.nagramiXTopCornersOnly && !b.nagramiXTopCornersOnly,"multiple native groups keep floating layout")
        let explicitSafe=Sheet(),single=Group();single.itemNodes=[ItemNode(200)];explicitSafe.itemGroupsContainerNode.groupNodes=[single];explicitSafe.nagramiXBottomAttached=true;layout.inputHeight=nil;layout.safeInsets.bottom=34
        explicitSafe.containerLayoutUpdated(layout,transition:.immediate)
        check(single.nagramiXBottomPaddingView.frame.height==34,"explicit safe inset is honored even if intrinsic bottom is zero")
        print("Native sheet layout checks: \(checks)")
    }
}
'''

def selection_fixture(source):
    text=(source/O).read_text()
    struct=block(text,'struct NagramiXOptionSheetOption {')
    factory=block(text,'func nagramiXOptionSheet(')
    kind=block(text,'    enum Kind {')
    start=text.index('    init(kind: Kind,')
    initializer=text[start:text.index('\n    func node(theme:',start)].rstrip()
    return SELECTION_BOUNDARY+struct+'\nfinal class NagramiXOptionSheetItem:ActionSheetItem {\n'+kind+'''
    let kind:Kind;let title:String;let subtitle:String;let enabled:Bool;let horizontalInset:CGFloat;let action:()->Void
'''+initializer+'\n}\n'+factory+SELECTION_TESTS

SELECTION_BOUNDARY=r'''
import Foundation
struct Strings {let nagramiXOptionSheetClose="Закрыть"}
struct PresentationData {let strings=Strings()}
protocol ActionSheetItem {}
struct ActionSheetItemGroup {let items:[ActionSheetItem]}
final class ActionSheetController {
    var nagramiXBottomAttached=false
    var dismissed:((Bool)->Void)?
    var groups:[ActionSheetItemGroup]=[]
    var dismissals=0
    init(presentationData:PresentationData){}
    func dismissAnimated(){dismissals+=1;dismissed?(false)}
    func setItemGroups(_ groups:[ActionSheetItemGroup]){self.groups=groups}
}
'''

SELECTION_TESTS=r'''
@main struct SelectionTests {
 static func main(){
    var checks=0
    func check(_ v:@autoclosure()->Bool,_ s:String){if !v(){FileHandle.standardError.write(Data(("Selection regression: "+s+"\n").utf8));exit(92)};checks+=1}
    let options=[NagramiXOptionSheetOption(id:1,title:"Среднее",subtitle:"Умеренная нагрузка на сеть"),NagramiXOptionSheetOption(id:2,title:"Максимум",subtitle:"Повышенная нагрузка на сеть")]
    for attached in [false,true] {for selectedID in [1,2] {
        var callbacks:[Int]=[]
        let sheet=nagramiXOptionSheet(presentationData:PresentationData(),title:"Параметры скачивания",options:options,selectedId:selectedID,footnote:"Следующие загрузки",bottomAttached:attached,selected:{callbacks.append($0)})
        let rows=sheet.groups[0].items.compactMap{$0 as? NagramiXOptionSheetItem}
        check(sheet.nagramiXBottomAttached==attached && rows.count==4,"mode routes to native presentation without changing content")
        check(rows.allSatisfy{$0.horizontalInset == (attached ? 30:20)},"attached sheet preserves previous text and accessory columns")
        for index in 1...2 {if case let .option(selected,_) = rows[index].kind {check(selected==(index==selectedID),"exact saved option remains selected")}else{check(false,"option kind")}}
        rows[selectedID].action();rows[selectedID].action();rows[0].action()
        check(callbacks==[selectedID] && sheet.dismissals==1,"selection saves and dismisses once")
        var cancellations=0
        let cancel=nagramiXOptionSheet(presentationData:PresentationData(),title:"Close",options:options,selectedId:1,footnote:"",bottomAttached:attached,selected:{_ in cancellations+=1})
        let cancelRows=cancel.groups[0].items.compactMap{$0 as? NagramiXOptionSheetItem}
        cancelRows[0].action();cancelRows[1].action()
        check(cancellations==0 && cancel.dismissals==1,"close never changes selected mode")
        let outside=nagramiXOptionSheet(presentationData:PresentationData(),title:"Dismiss",options:options,selectedId:1,footnote:"",bottomAttached:attached,selected:{_ in cancellations+=1})
        outside.dismissed?(true);(outside.groups[0].items[1] as! NagramiXOptionSheetItem).action()
        check(cancellations==0,"outside/swipe dismissal blocks late selection")
    }}
    print("Option sheet selection checks: \(checks)")
 }
}
'''

def api_check(source,swiftc,root):
    root.mkdir();text=(source/C).read_text()
    prop=block(text,'    public var nagramiXBottomAttached: Bool = false {')
    shell='class ActionSheetControllerNode {var nagramiXBottomAttached=false}\npublic class ActionSheetController {public init(){};public var isViewLoaded=false;private let actionSheetNode=ActionSheetControllerNode()\n'+prop+'\n}\n'
    module=root/'Display.swift';module.write_text(shell)
    common=[swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',root/'cache']
    run(common+['-emit-module','-module-name','Display',module,'-emit-module-path',root/'Display.swiftmodule'])
    assignment=next(line.strip() for line in (source/O).read_text().splitlines() if 'controller.nagramiXBottomAttached = ' in line)
    probe=root/'SettingsUI.swift';probe.write_text('import Display\nfunc configure(_ bottomAttached:Bool){let controller=ActionSheetController()\n'+assignment+'\n}\n')
    run(common+['-typecheck','-I',root,probe])
    module.write_text(shell.replace('public var nagramiXBottomAttached: Bool','private var nagramiXBottomAttached: Bool'))
    run(common+['-emit-module','-module-name','Display',module,'-emit-module-path',root/'Display.swiftmodule'])
    result=subprocess.run(list(map(str,common+['-typecheck','-I',root,probe])),capture_output=True,text=True)
    assert result.returncode!=0 and 'inaccessible due to' in result.stderr,result.stderr
    return {'production_public_property_and_caller':'passed','private_property_negative':'rejected','boundary':'Display public setter compiled as its own module against SettingsUI caller; UIKit lifecycle is adapted.'}

def execute(swiftc,root,name,text,negative=None):
    path=root/(name+'.swift');path.write_text(text);runs=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=root/(name+'-'+mode);run([swiftc,'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',root/'cache',*flags,path,'-o',binary])
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
        if negative is None:assert result.returncode==0,result.stdout+result.stderr
        else:assert result.returncode in (91,92) and negative in result.stderr,result.stdout+result.stderr
        runs.append({'name':name,'mode':mode,'exit_code':result.returncode,'output':(result.stdout+result.stderr).strip()});binary.unlink()
    return runs

def source_contract(source):
    plan=checked_plan(STAGE)
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    before=lambda p:(ROOT/'ios'/plan['previous'][p]).read_text()
    assert block((source/O).read_text(),'private final class NagramiXOptionSheetItemNode:')==block(before(O),'private final class NagramiXOptionSheetItemNode:').replace('let inset: CGFloat = 20.0','let inset: CGFloat = item.horizontalInset',1)
    node=(source/N).read_text()
    for marker in ['    func animateIn(', '    func animateOut(', '    @objc func dimNodeTap(', '    func scrollViewDidEndDragging(']:assert block(node,marker)==block(before(N),marker)
    assert (source/S).read_text()==before(S).replace('footnote: presentationData.strings.nagramiXDownloadModeFootnote, selected:', 'footnote: presentationData.strings.nagramiXDownloadModeFootnote, bottomAttached: true, selected:',1)
    assert 'bottomAttached: Bool = false' in (source/O).read_text()
    assert 'import Display\n' in (source/O).read_text()
    assert 'byRoundingCorners: [.topLeft, .topRight]' in (source/G).read_text()
    assert 'self.nagramiXBottomPaddingView.backgroundColor = self.theme.itemBackgroundColor' in (source/G).read_text()
    return plan

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=source_contract(a.source);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='download-sheet-edge-') as d:
        root=Path(d);rejected=guard_checks(a.source,STAGE,plan,root/'guards');layout=layout_fixture(a.source);selection=selection_fixture(a.source)
        runs=execute(a.swiftc,root,'layout',layout)+execute(a.swiftc,root,'selection',selection)
        mutants=[('old-bottom-gap',layout.replace('insets.bottom = 0.0','insets.bottom = 22.0',1),'attached panel reaches screen bottom'),('old-safe-inset',layout.replace('leadingVisibleNodeSize += bottomPadding',''),'safe area does not shift content down'),('old-upward-bounce',layout.replace('scrollView.contentOffset = CGPoint(x: scrollView.contentOffset.x, y: 0.0)','_ = scrollView'),'upward outer bounce'),('old-four-corners',layout.replace('? [.layerMinXMinYCorner, .layerMaxXMinYCorner]','? [.layerMinXMinYCorner, .layerMaxXMinYCorner, .layerMinXMaxYCorner, .layerMaxXMaxYCorner]'),'only upper corners'),('lost-selection-guard',selection.replace('guard let controller, !finished else { return }','guard let controller, (!finished || finished) else { return }'),'selection saves and dismisses once')]
        for name,text,diagnostic in mutants:runs+=execute(a.swiftc,root,name,text,diagnostic)
        api=api_check(a.source,a.swiftc,root/'api')
        for name in plan['outputs']:run([a.swiftc,'-frontend','-parse',a.source/name])
    assert manifest(a.source)==before
    run(['python3',a.source/'build-system/Make/PostboxImportCheck.py',a.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'native_input_proofs':len(plan['native_inputs']),'fail_closed':len(rejected),'executions':runs,'api_boundary':api,'swift_parse':len(plan['outputs']),'source_files':len(before),'source_unchanged_by_checks':True,'native_postbox_imports':'passed','boundary':'Production native layout, group padding/corners, factory and callback bodies execute in explicit UIKit/text-measurement adapters. Native drawing pixels, gestures and UIKit presentation are not exercised.','apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('executions','outputs')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

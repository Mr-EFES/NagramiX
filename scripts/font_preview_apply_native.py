"""Check final Apply node against native ObjC declarations and imported Swift labels."""
import hashlib,subprocess,sys
from font_apply_node_lifecycle_native import no_core
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan,OVERLAY
from app_font_selection_runtime import UI
from font_preview_apply_runtime import IMPORTS
from transcription_compatibility_apple import write_module_map

STAGE='font_apply_node_lifecycle'
HEADER='submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode.h'
SUBCLASSES='submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode+Subclasses.h'
BUTTON='submodules/TelegramUI/Components/NavigationBarNode/Sources/NavigationBarItemContent.swift'
NODE='private final class NagramiXFontApplyNode: ASDisplayNode'


def final_ui(source):
    data=(source/UI).read_bytes();original=hashlib.sha256(data).hexdigest()
    if NODE not in data.decode():return data.decode(),None
    plan=checked_plan(STAGE)
    selector=checked_plan('release_096_font_node_compatibility')
    assert original in {selector['inputs'][UI],selector['outputs'][UI],plan['outputs'][UI]},'Unknown font UI checkpoint'
    if original!=plan['outputs'][UI]:data=(OVERLAY/plan['replacements'][UI]).read_bytes()
    assert hashlib.sha256(data).hexdigest()==plan['outputs'][UI]
    return data.decode(),{'source_ui_sha256':original,'sdk_ui_sha256':plan['outputs'][UI],'late_stage':64,'historical_runtime':'original52/63 source and runtime checkpoints remain exact; native gate checks final64 default initialization and view factory'}


def native_declarations(source):
    plan=checked_plan(STAGE)
    def native(name):
        path=source/name
        data=path.read_bytes() if path.exists() else (OVERLAY/plan['guard_sources'][name]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==plan['guards'][name],name
        return data.decode()
    header=native(HEADER);subclasses=native(SUBCLASSES)
    declarations=['typedef UIView * _Nonnull(^ASDisplayNodeViewBlock)(void);','typedef void (^ASDisplayNodeDidLoadBlock)(__kindof ASDisplayNode * node);','- (instancetype)init NS_DESIGNATED_INITIALIZER;','- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock;','- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock didLoadBlock:(nullable ASDisplayNodeDidLoadBlock)didLoadBlock NS_DESIGNATED_INITIALIZER;']
    for line in declarations:assert header.count(line)==1,line
    setter='- (void)setViewBlock:(ASDisplayNodeViewBlock)viewBlock;';assert header.count(setter)==1
    declarations.append(setter)
    sizing='- (CGSize)calculateSizeThatFits:(CGSize)constrainedSize;';assert subclasses.count(sizing)==1
    objc='#import <UIKit/UIKit.h>\nNS_ASSUME_NONNULL_BEGIN\n@class ASDisplayNode;\n'+'\n'.join(declarations[:2])+'\n@interface ASDisplayNode : NSObject\n'+'\n'.join(declarations[2:])+'\n@end\n@interface ASDisplayNode (NagramiXSizing)\n'+sizing+'\n@end\nNS_ASSUME_NONNULL_END\n'
    return objc,native(BUTTON)


def objc_check(source,swiftc,folder):
    if sys.platform!='darwin':return {'status':'not_run','reason':'Actual Objective-C importer/UIKit requires Apple; pure Swift model separately checks labels'}
    folder.mkdir(parents=True,exist_ok=True);objc,_=native_declarations(source)
    header=folder/'TextureInitializers.h';header.write_text(objc);module=folder/'module'
    write_module_map(module,header,'NagramiXTextureInitializers')
    ui,contract=final_ui(source);node=block(ui,NODE)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    common=[str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'cache'),'-I',str(module)]
    code='import UIKit\nimport NagramiXTextureInitializers\n'+node+'\n'
    path=folder/'node-final64.swift';path.write_text(code)
    result=subprocess.run(common+[str(path)],capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stdout+result.stderr
    old='super.init()\n        self.setViewBlock({ button })';assert code.count(old)==1
    path=folder/'node-original207.swift';path.write_text(code.replace(old,'super.init(viewBlock: { button }, didLoadBlock: nil)',1))
    result=subprocess.run(common+[str(path)],capture_output=True,text=True,timeout=120)
    assert result.returncode!=0 and 'didLoadBlock' in result.stderr and 'didLoad' in result.stderr and ('renamed' in result.stderr or 'incorrect argument label' in result.stderr),result.stdout+result.stderr
    return {'status':'passed','target':'arm64-apple-ios15.0','source_contract':contract,'original207_reproduced_and_rejected':True,'boundary':'Actual typedefs, initializer declarations, designated attributes and sizing declaration copied verbatim from guarded Texture headers, real UIKit and ObjC importer; NSObject class shell omits unrelated protocols/ivars. Full Texture implementation/app SDK remains separate.'}


def check(source,swiftc,folder):
    ui,contract=final_ui(source);node=block(ui,NODE);_,button=native_declarations(source)
    empty=block(button,'func navigationBarItemIsEmpty(')
    code=IMPORTS+'''
class UIView {}
final class UIButton:UIView {var bounds=CGRect(x:0,y:0,width:136,height:40)}
class ASDisplayNode {
 var subnodes:[ASDisplayNode]?
 private var viewFactory:(()->UIView)?
 private var loadedView:UIView?
 var initializations=0
 var usedReentrantInitializer=false
 var view: UIView {if let value=loadedView{return value};let value=viewFactory?() ?? UIView();loadedView=value;return value}
 init(){initializations=1}
 init(viewBlock:@escaping()->UIView,didLoad:((ASDisplayNode)->Void)?){initializations=1;usedReentrantInitializer=true;viewFactory=viewBlock}
 func setViewBlock(_ block:@escaping()->UIView){precondition(loadedView == nil);viewFactory=block}
 convenience init(viewBlock:@escaping()->UIView){self.init(viewBlock:viewBlock,didLoad:nil)}
 @available(*,unavailable,renamed:"init(viewBlock:didLoad:)")
 convenience init(viewBlock:@escaping()->UIView,didLoadBlock:((ASDisplayNode)->Void)?){self.init(viewBlock:viewBlock,didLoad:didLoadBlock)}
 func calculateSizeThatFits(_ constrainedSize:CGSize)->CGSize {.zero}
}
final class UIBarButtonItem {var customDisplayNode:ASDisplayNode?;var image:Int?;var title:String?}
'''+node+'\n'+empty+'''
@main struct NodeContractTests {
 static func main(){
  let button=UIButton();let node=NagramiXFontApplyNode(button:button);let item=UIBarButtonItem();item.customDisplayNode=node
  precondition(node.initializations == 1 && !node.usedReentrantInitializer,"Initializer must not dynamically re-enter init()")
  precondition(node.view === button && node.view === button,"The original UIKit button must remain the single node view")
  precondition(!navigationBarItemIsEmpty(item),"Apply must not disappear as an empty base ASDisplayNode")
  precondition(node.calculateSizeThatFits(CGSize(width:100,height:44)) == button.bounds.size)
  button.bounds.size=CGSize(width:184,height:48)
  precondition(node.calculateSizeThatFits(.zero) == button.bounds.size,"Resizing must track original button bounds")
  item.customDisplayNode=ASDisplayNode();precondition(navigationBarItemIsEmpty(item))
  print("6 native node lifecycle contract checks")
 }
}
'''
    path=folder/'font-apply-native-node.swift';path.write_text(code);reports=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=folder/('native-node-'+mode)
        result=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'node-cache'),*flags,str(path),'-o',str(binary)],capture_output=True,text=True,timeout=60);assert result.returncode==0,result.stdout+result.stderr
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=no_core);assert result.returncode==0,result.stdout+result.stderr
        reports.append({'mode':mode,'checks':6,'result':'passed'});binary.unlink()
    old='super.init()\n        self.setViewBlock({ button })';assert code.count(old)==1
    path.write_text(code.replace(old,'super.init(viewBlock: { button }, didLoadBlock: nil)',1))
    result=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-typecheck','-warnings-as-errors','-module-cache-path',str(folder/'node-cache'),str(path)],capture_output=True,text=True,timeout=60)
    assert result.returncode!=0 and 'renamed' in result.stderr and 'didLoadBlock' in result.stderr,result.stdout+result.stderr
    path.write_text(code.replace(old,'super.init(viewBlock: { button }, didLoad: nil)',1))
    legacy=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=folder/('original208-'+mode)
        result=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'node-cache'),*flags,str(path),'-o',str(binary)],capture_output=True,text=True,timeout=60);assert result.returncode==0,result.stdout+result.stderr
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=no_core)
        assert result.returncode!=0,'Original208 initializer route was accepted'
        legacy.append({'mode':mode,'expected':'initializer-route regression rejected','verified':True})
        binary.unlink()
    apple=objc_check(source,swiftc,folder/'actual-objc')
    from font_apply_node_lifecycle_native import check as lifecycle_check
    lifecycle=lifecycle_check(source,swiftc,folder/'objc-runtime')
    return {'native_headers':'guarded actual Texture declarations; final64 avoids ObjC dynamic self-init in view-block initializer','source_contract':contract,'node_sizing_and_navigation_visibility':reports,'production_uses_default_initializer_and_native_view_factory':True,'original208_initializer_route':legacy,'objc_constructor_runtime':lifecycle,'original207_initializer_label':'rejected','actual_objc_initializer':apple,'real_uikit':'separate mandatory complete font screen Apple precheck; Objective-C initializer runtime gate separately reproduces original208 on macOS'}

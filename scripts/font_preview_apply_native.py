"""Реальные сигнатуры native headers и узел кнопки без выдуманного initializer."""
import hashlib,subprocess
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan,OVERLAY
from app_font_selection_runtime import UI
from font_preview_apply_runtime import IMPORTS


def check(source,swiftc,folder):
    plan=checked_plan('font_preview_apply')
    def native(name):
        path=source/name
        data=path.read_bytes() if path.exists() else (OVERLAY/plan['guard_sources'][name]).read_bytes()
        assert hashlib.sha256(data).hexdigest()==plan['guards'][name],name
        return data.decode()
    header=native('submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode.h')
    subclasses=native('submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode+Subclasses.h')
    assert '- (instancetype)init NS_DESIGNATED_INITIALIZER;' in header
    assert '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock;' in header
    assert '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock didLoadBlock:(nullable ASDisplayNodeDidLoadBlock)didLoadBlock NS_DESIGNATED_INITIALIZER;' in header
    assert '- (CGSize)calculateSizeThatFits:(CGSize)constrainedSize;' in subclasses
    ui=(source/UI).read_text();node=block(ui,'private final class NagramiXFontApplyNode: ASDisplayNode')
    button=native('submodules/TelegramUI/Components/NavigationBarNode/Sources/NavigationBarItemContent.swift')
    empty=block(button,'func navigationBarItemIsEmpty(')
    # The Objective-C designated / convenience distinction is represented exactly.
    # All application bodies below are unmodified. Real UIKit is checked separately.
    code=IMPORTS+'''
class UIView {}
final class UIButton:UIView {var bounds=CGRect(x:0,y:0,width:136,height:40)}
class ASDisplayNode {
 var subnodes:[ASDisplayNode]?
 init(){}
 init(viewBlock:()->UIView,didLoadBlock:(()->Void)?){_ = viewBlock()}
 convenience init(viewBlock:()->UIView){self.init(viewBlock:viewBlock,didLoadBlock:nil)}
 func calculateSizeThatFits(_ constrainedSize:CGSize)->CGSize {.zero}
}
final class UIBarButtonItem {var customDisplayNode:ASDisplayNode?;var image:Int?;var title:String?}
'''+node+'\n'+empty+'''
@main struct NodeContractTests {
 static func main(){
  let button=UIButton();let node=NagramiXFontApplyNode(button:button);let item=UIBarButtonItem();item.customDisplayNode=node
  precondition(!navigationBarItemIsEmpty(item),"Apply must not disappear as an empty base ASDisplayNode")
  precondition(node.calculateSizeThatFits(CGSize(width:100,height:44)) == button.bounds.size)
  item.customDisplayNode=ASDisplayNode();precondition(navigationBarItemIsEmpty(item))
  print("3 native node contract checks")
 }
}
'''
    path=folder/'font-apply-native-node.swift';path.write_text(code);reports=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=folder/('native-node-'+mode)
        result=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'node-cache'),*flags,str(path),'-o',str(binary)],capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stdout+result.stderr
        result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert result.returncode==0,result.stdout+result.stderr
        reports.append({'mode':mode,'checks':3,'result':'passed'});binary.unlink()
    old='super.init(viewBlock: { button }, didLoadBlock: nil)';assert code.count(old)==1
    path.write_text(code.replace(old,'super.init(viewBlock: { button }, didLoad: nil)',1))
    result=subprocess.run([str(swiftc),'-swift-version','5','-parse-as-library','-typecheck','-warnings-as-errors','-module-cache-path',str(folder/'node-cache'),str(path)],capture_output=True,text=True,timeout=60)
    assert result.returncode!=0 and 'didLoadBlock' in result.stderr,result.stdout+result.stderr
    return {'native_headers':'exact guarded actual Texture declarations','node_sizing_and_navigation_visibility':reports,'production_uses_designated_two_argument_initializer':True,'wrong_initializer_label':'rejected','real_uikit':'separate mandatory Apple precheck'}

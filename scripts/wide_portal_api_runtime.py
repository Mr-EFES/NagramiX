"""Actual wide-post helpers with the pinned portal protocol and native frame method."""
from validate_quick_format import block
import feature_wide_post_envelope_runtime as wide

WALLPAPER='submodules/WallpaperBackgroundNode/Sources/WallpaperBackgroundNode.swift'
VIEW=wide.VIEW
BACKGROUND=wide.BACKGROUND


def fixture(source):
    code=wide.fixture(source)
    protocol=block((source/WALLPAPER).read_text(),'public protocol WallpaperBubbleBackgroundNode:')
    old='class WallpaperBubbleBackgroundNode {var lastRect=CGRect.zero;func update(rect:CGRect,within:CGSize,transition:ContainedViewLayoutTransition){lastRect=rect}}'
    assert code.count(old)==1
    code=code.replace(old,protocol+'''\nfinal class PortalProbe:ASDisplayNode,WallpaperBubbleBackgroundNode {
 var implicitContentUpdate=false;var reloads=0;func reloadBindings(){reloads+=1}
}
final class PortalLayer {var frame=CGRect.zero}
final class PortalMask {var frame=CGRect.zero;func updateFrame(_ value:CGRect,transition:ContainedViewLayoutTransition){frame=value}}
private let maskInset:CGFloat=1.0
''',1)
    old='class ASDisplayNode {\n var frame=CGRect.zero;'
    assert code.count(old)==1
    code=code.replace(old,'''public class ASDisplayNode {
 let layer=PortalLayer();public var frame:CGRect {get{layer.frame}set{layer.frame=newValue}}
 ''',1)
    old='enum ContainedViewLayoutTransition {case immediate}'
    code=code.replace(old,'''enum ContainedViewLayoutTransition {case immediate
 func updateFrame(layer:PortalLayer,frame:CGRect){layer.frame=frame}
 func updateFrame(node:ASDisplayNode,frame:CGRect,completion:((Bool)->Void)?){node.frame=frame;completion?(true)}
}''',1)
    code=code.replace('var backgroundContent:WallpaperBubbleBackgroundNode?=WallpaperBubbleBackgroundNode()', 'var maskView:PortalMask?;var backgroundContent:WallpaperBubbleBackgroundNode?=PortalProbe()',1)
    old='func updateFrame(_ value:CGRect,transition:ContainedViewLayoutTransition){frame=value}'
    prefix,backdrop=code.split('class ChatMessageBubbleBackdrop:ASDisplayNode {',1)
    assert backdrop.count(old)==1
    text=(source/BACKGROUND).read_text()
    signature='    public func updateFrame(_ value: CGRect, transition: ContainedViewLayoutTransition, completion: @escaping () -> Void = {}) {'
    assert text.count(signature)==1
    start=text.index(signature);brace=start+len(signature)-1;depth=1;end=brace+1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    native=text[start:end]
    code=prefix+'class ChatMessageBubbleBackdrop:ASDisplayNode {'+backdrop.replace(old,native,1)
    old='''  view.updateNagramiXWidePostAbsoluteRect(CGRect(x:10,y:50,width:393,height:220),within:CGSize(width:393,height:852))
  check(backdrop.backgroundContent!.lastRect==frame.offsetBy(dx:10,dy:50),"wallpaper tracks actual row coordinates")'''
    assert code.count(old)==1
    code=code.replace(old,'''  let portal=backdrop.backgroundContent as! PortalProbe
  check(portal.frame==CGRect(origin:.zero,size:frame.size),"portal receives local bounds through native backdrop frame method")
  backdrop.maskView=PortalMask()
  let shifted=frame.offsetBy(dx:10,dy:50)
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:shifted)
  check(backdrop.frame==shifted && portal.frame==CGRect(origin:.zero,size:frame.size),"scrolling moves backdrop without changing portal local coordinates")
  check(backdrop.maskView!.frame==CGRect(origin:.zero,size:frame.size).insetBy(dx:-1,dy:-1),"native mask keeps correct local bounds")
  check(portal.reloads==0,"scrolling never recreates native portal bindings")
  view.updateNagramiXWidePostContainer(item:item,parent:parent,frame:frame)''',1)
    return code


def original(source,code,before):
    current=(source/VIEW).read_text()
    def members(text):return text[text.index('    public private(set) var nagramiXWidePostFrame:'):text.index('    public let layoutConstants',text.index('    public private(set) var nagramiXWidePostFrame:'))]
    old=members(before).replace('public ','');new=members(current).replace('public ','')
    assert code.count(new)==1
    return code.replace(new,old,1)

"""Early real UIKit/AVKit checks with pinned native image API declarations."""
import re
import subprocess
import sys
from pathlib import Path
from validate_quick_format import block
from validate_pip_swipe_handoff import clean, U
from pip_preview_continuity_runtime import D, POSTER_BOUNDARY, RESTORE_FIELDS

PHOTO = 'submodules/PhotoResources/Sources/PhotoResources.swift'
TRANSFORM = 'submodules/Display/Source/TransformImageNode.swift'
ARGS = 'submodules/Display/Source/TransformImageArguments.swift'
CAPTURE = 'submodules/Display/Source/NagramiXCaptureProtection.swift'
BASE = 'submodules/TelegramUniversalVideoContent/Sources/'


def signature(source, path, prefix):
    lines = [line.strip() for line in (source / path).read_text().splitlines() if line.strip().startswith(prefix)]
    assert lines, (path, prefix)
    return lines[0].rsplit('{', 1)[0].strip().removeprefix('public ')


def public_contract(source):
    result = {}
    for name, members in [('NativeVideoContent', ['userLocation', 'fileReference']),
                          ('HLSVideoContent', ['userLocation', 'fileReference']),
                          ('WebEmbedVideoContent', ['webpageContent'])]:
        body = block((source / (BASE + name + '.swift')).read_text(), 'public final class ' + name + ':')
        for member in members:
            assert re.search(r'public let ' + member + r'\s*:', body), (name, member)
        result[name] = members
    return result


def fixture(source, native):
    b = POSTER_BOUNDARY.replace('import Foundation', 'import Foundation\nimport UIKit\nimport AVKit', 1)
    for marker in ['struct UIEdgeInsets {', 'final class UIColor {', 'struct Image {', 'struct Graphics {',
                   'final class DrawingContext {', 'struct NSValue {', 'final class CALayer {', 'final class UIView {', 'class ASDisplayNode {']:
        b = b.replace(block(b, marker), '')
    b += r'''
final class DrawingContext {
 init?(size:CGSize,clear:Bool){}
 func withContext(_ f:(CGContext)->Void){}
 func generateImage()->UIImage?{nil}
}
extension CALayer {
 func animate(from:Any,to:Any,keyPath:String,timingFunction:String,duration:Double,removeOnCompletion:Bool=false,completion:((Bool)->Void)?=nil){}
}
class ASDisplayNode {
 let view=UIView()
 var layer:CALayer{view.layer}
 var frame:CGRect{get{view.frame}set{view.frame=newValue}}
 var bounds:CGRect{view.bounds}
 var isUserInteractionEnabled:Bool{get{view.isUserInteractionEnabled}set{view.isUserInteractionEnabled=newValue}}
 var clipsToBounds:Bool{get{view.clipsToBounds}set{view.clipsToBounds=newValue}}
 var cornerRadius:CGFloat{get{view.layer.cornerRadius}set{view.layer.cornerRadius=newValue}}
 weak var supernode:ASDisplayNode?
 init(){}
 func addSubnode(_ node:ASDisplayNode){node.supernode=self;view.addSubview(node.view)}
 func removeFromSupernode(){supernode=nil;view.removeFromSuperview()}
}
struct MediaResourceUserContentType {}
struct TransformImageCustomArguments {}
enum TransformImageResizeMode {case fill(UIColor),aspectFill}
'''
    init = signature(native, ARGS, 'public init(corners: ImageCorners, imageSize: CGSize, boundingSize: CGSize,')
    argument = '''struct TransformImageArguments {
 let corners:ImageCorners;let imageSize:CGSize;let boundingSize:CGSize;let intrinsicInsets:UIEdgeInsets
 var drawingRect:CGRect{CGRect(origin:.zero,size:boundingSize)}
 ''' + init + ''' {
 self.corners=corners;self.imageSize=imageSize;self.boundingSize=boundingSize;self.intrinsicInsets=intrinsicInsets
 }
}'''
    b = b.replace(block(b, 'struct TransformImageArguments {'), argument)
    for prefix, body in [('public func mediaGridMessageVideo(', 'return Signal(name:"native-video-api")'),
                         ('public func chatMessagePhoto(postbox:', 'return Signal(name:"native-photo-api")')]:
        name = prefix.split('func ')[1].split('(')[0]
        old = block(b, 'func ' + name + '(')
        b = b.replace(old, signature(native, PHOTO, prefix) + ' {' + body + '}')
    old = block(b, 'func nagramiXSetLayerDisableScreenshots(')
    b = b.replace(old, signature(native, CAPTURE, 'public func nagramiXSetLayerDisableScreenshots(') + ' {}')
    old = block(b, ' func setSignal(')
    b = b.replace(old, ' ' + signature(native, TRANSFORM, 'public func setSignal(') + ' {self.source=signal.name}')
    old = block(b, ' func asyncLayout(')
    b = b.replace(old, ' ' + signature(native, TRANSFORM, 'public func asyncLayout()') + ' {{args in {self.arguments=args}}}')
    poster = clean(block((source / U).read_text(), 'private final class UniversalVideoGalleryItemPictureInPictureNode:'))
    decoration = clean(block((source / D).read_text(), 'public final class GalleryVideoDecoration:'))
    fields = RESTORE_FIELDS.replace('=AVPictureInPictureController()', '=nil')
    names = ['    private func nagramiXCancelInterfaceRestore()', '    private func nagramiXRestoreInterface(',
             '    public func pictureInPictureController(_ pictureInPictureController: AVPictureInPictureController, restoreUserInterfaceForPictureInPictureStopWithCompletionHandler',
             '    public func requestExpand()', '    public func pictureInPictureControllerDidStartPictureInPicture(']
    methods = '\n'.join(clean(block((source / U).read_text(), marker)) for marker in names)
    return b + '\n' + poster + '\n' + decoration + '\n@available(iOS 15.0, *)\nfinal class Restorer:NSObject,AVPictureInPictureControllerDelegate {\n' + fields + methods + '\n}\n'


def check(source, swiftc, folder, native=None):
    native = source if native is None else native
    members = public_contract(native)
    code = fixture(source, native)
    path = folder / 'pip-preview-real-uikit.swift'
    path.write_text(code)
    parsed = subprocess.run([str(swiftc), '-frontend', '-parse', str(path)], capture_output=True, text=True)
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    if sys.platform != 'darwin':
        return {'status': 'not_run', 'reason': 'Actual UIKit/AVKit typechecking requires Apple SDK', 'probe_swift_parse': 'passed', 'native_public_member_contract': members,
                'native_signatures': 'PhotoResources image functions, TransformImageArguments init, TransformImageNode setSignal/asyncLayout and capture hook copied from pinned source declarations'}
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    result = subprocess.run([str(swiftc), '-swift-version', '5', '-typecheck', '-warnings-as-errors', '-sdk', sdk, '-target', 'arm64-apple-ios15.0',
                             '-module-cache-path', str(folder / 'pip-preview-sdk-cache'), str(path)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return {'status': 'passed', 'target': 'arm64-apple-ios15.0', 'native_public_member_contract': members,
            'scope': 'Actual full poster and GalleryVideoDecoration plus restore methods; real UIKit/CoreGraphics/AVKit, pinned native public image API signatures. Texture, SignalKit and Telegram data are explicit adapters, not full framework implementations. Full application SDK and device remain separate.'}

"""Compile actual public clipboard helpers/real model+RTF and an external consumer."""
import subprocess,sys
from validate_quick_format import block
from composer_copy_integrity_runtime import fixture,ROOT


def foundation_check(swiftc,folder):
    """Exercise the actual fixture prefix with Foundation, before large suites.

    macOS has Objective-C Foundation without UIKit. Corelibs' empty attributed
    string initializer must not be added there; CGRect overlays need CoreGraphics.
    """
    from validate_private_temporary_transcription import execute
    boundary=(ROOT/'scripts/tests/NagramiXComposerCopyBoundary.swift').read_text()
    def conditional(marker):
        start=boundary.index(marker)
        return boundary[start:boundary.index('#endif',start)+len('#endif')]
    geometry=conditional('#if canImport(CoreGraphics)')
    initializer=conditional('#if !canImport(')
    code='import Foundation\n'+geometry+'\n'+initializer+'''
@main struct FoundationBoundaryProbe {
 static func main() {
  let text=NSMutableAttributedString()
  text.append(NSAttributedString(string:"baseline"))
  let rect=CGRect(x:1,y:2,width:4,height:3)
  precondition(rect.minY+rect.maxY+CGFloat(text.length)==15)
  print("Foundation fixture boundary: passed")
 }
}
'''
    runs=execute(swiftc,folder,'composer-foundation-boundary',code)
    negatives=[]
    if sys.platform=='darwin':
        for name,mutated,diagnostic in [
            ('missing-coregraphics',code.replace(geometry,''),"has no member 'minY'"),
            ('wrong-uikit-platform-guard',code.replace('canImport(ObjectiveC)','canImport(UIKit)'),"overriding declaration requires an 'override' keyword"),
        ]:
            assert mutated!=code,name
            path=folder/(name+'.swift');path.write_text(mutated)
            result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-typecheck','-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=60)
            assert result.returncode!=0 and diagnostic in result.stderr,result.stdout+result.stderr
            negatives.append(name)
    return {'executions':runs,'native_negative_refusals':negatives,'native_negative_status':'passed' if sys.platform=='darwin' else 'not_run; Objective-C Foundation/CoreGraphics requires Apple',
            'scope':'Actual checked-in platform conditionals with real Foundation attributed string initialization and CGRect operators. No UIKit stand-ins in this probe; separate UIKit gate remains mandatory.'}


def check(source,swiftc,folder,public_api=False):
    if sys.platform!='darwin' and not public_api:return {'status':'not_run','reason':'Real UIKit pasteboard SDK requires macOS'}
    code=fixture(source).split('private var checks=0')[0]
    if sys.platform=='darwin':
        for marker in ['enum UTType {','final class UIPasteboard {']:
            code=code.replace(block(code,marker),'',1)
        code='import UIKit\nimport UniformTypeIdentifiers\n'+code
    production=folder/'composer-copy-public.swift';production.write_text(code)
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'public-cache')]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip();common+=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    result=subprocess.run(common+['-emit-module','-parse-as-library','-module-name','ComposerClipboard','-emit-module-path',str(folder/'ComposerClipboard.swiftmodule'),str(production)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    client=folder/'composer-copy-client.swift';client.write_text('''import Foundation
import ComposerClipboard
@MainActor func copyConsumer(_ text:String,entities:[MessageTextEntity]) {
 _ = messageTextPasteboardItem(text,entities:entities,includeRTF:false)
 storeChatMessageTextInPasteboard(text,entities:entities)
}
''')
    result=subprocess.run(common+['-typecheck','-I',str(folder),str(client)],capture_output=True,text=True,timeout=120);assert result.returncode==0,result.stdout+result.stderr
    return {'status':'passed','scope':'Full changed clipboard helper bodies, native entity Codable/formatting/document/RTF export and external public API consumer. UIKit pasteboard/UTType are real on Apple, explicit IO boundaries on Linux. Unrelated button-action migration/opaque Postbox codecs are outside this fixture. Full application SDK/device remain separate.'}

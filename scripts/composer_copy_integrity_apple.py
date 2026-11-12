"""Compile actual public clipboard helpers/real model+RTF and an external consumer."""
import subprocess,sys
from validate_quick_format import block
from composer_copy_integrity_runtime import fixture


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

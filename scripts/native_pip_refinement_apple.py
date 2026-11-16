"""Future UIKit/AVKit typecheck for the actual added recognizer, selector and clipping lease."""
from pathlib import Path
import subprocess
import sys
from validate_quick_format import block
from validate_pip_swipe_handoff import U, N


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    text = (source / U).read_text()
    code = 'import UIKit\nimport AVKit\n' + '\n'.join(block(text, m) for m in [
        'private final class NagramiXUpwardPiPGestureRecognizer:',
        'private final class NagramiXNativePiPSourceClipping'])
    code += '\n' + block((source / N).read_text(), 'func nagramiXShouldBeginFastPictureInPictureSwipe(')
    registration = text.split('        let pipSwipe = NagramiXUpwardPiPGestureRecognizer', 1)[1].split('        self.footerContentNode.shareMediaParameters', 1)[0]
    code += '''
private final class Scroll {let view=UIScrollView()}
private final class VideoNode {var ownsContentNode=true}
private final class Host:NSObject {
 let scrollNode=Scroll()
 var videoNode:VideoNode?=VideoNode()
 var usesNativePictureInPictureSwipe=true
 override init(){super.init()
        let pipSwipe = NagramiXUpwardPiPGestureRecognizer''' + registration + '''
 }
 func prepareForNativePictureInPictureSwipe(){}
 func nagramiXRequestPictureInPicture()->Bool{true}
''' + block(text, '    @objc private func nagramiXUpwardPiPSwipe(') + '\n}\n'
    path = folder / 'NativePiPAPI.swift'
    path.write_text(code)
    parsed = subprocess.run([str(swiftc), '-frontend', '-parse', str(path)], capture_output=True, text=True)
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    result = {'status': 'not_run', 'swift_parse': 'passed', 'full_application_sdk': 'not_run', 'physical_iphone': 'pending'}
    if sys.platform != 'darwin':
        result['reason'] = 'UIKit/AVKit unavailable on Linux; production handler/clipping logic executes with explicit IO hosts.'
        return result
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    completed = subprocess.run([str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-typecheck', '-parse-as-library',
                                '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-module-cache-path', str(folder / 'cache'), str(path)],
                               capture_output=True, text=True, timeout=180)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result.update(status='passed', scope='Actual new UIPan recognizer/delegate, target selector/registration, handler and CALayer clipping lease; explicit owner and request host.')
    return result

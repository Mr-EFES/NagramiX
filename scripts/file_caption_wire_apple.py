"""Реальная Foundation helper/API между модулями; UIKit geometry обязателен на macOS."""
import subprocess, sys
from validate_quick_format import block
from validate_private_temporary_transcription import save_failed_fixture
import file_caption_wire_runtime as rt


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    flags = []
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        flags = ['-sdk', sdk, '-target', 'arm64-apple-ios15.0']
    common = [str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-parse-as-library', '-module-cache-path', str(folder / 'cache'), *flags]

    def run(args):
        p = subprocess.run(common + [str(x) for x in args], capture_output=True, text=True, timeout=180)
        if p.returncode:
            for name in ['caption.swift', 'caller.swift', 'geometry.swift']:
                if (folder / name).exists():
                    save_failed_fixture(folder / name, 'caption-wire-api-' + name, 'iphoneos' if flags else 'host', 'typecheck', p)
        assert p.returncode == 0, p.stdout + p.stderr

    # Telegram file IO is explicit. Public property names are also guarded
    # against the actual native SyncCore declaration in the normal source plan.
    media = folder / 'media.swift'
    media.write_text('public final class TelegramMediaFile { public var isVoice=false,isInstantVideo=false,isVideo=false,isAnimated=false,isSticker=false; public init() {} }\n')
    run(['-emit-module', '-module-name', 'TelegramCore', '-emit-module-path', folder / 'TelegramCore.swiftmodule', media])
    helper = folder / 'caption.swift'
    helper.write_text('import Foundation\nimport TelegramCore\n' + block((source / rt.T).read_text(), 'public func chatComposerSpacedFileCaption(') + '\n')
    run(['-emit-module', '-module-name', 'CaptionWire', '-I', folder, '-emit-module-path', folder / 'CaptionWire.swiftmodule', helper])
    caller = folder / 'caller.swift'
    caller.write_text('import Foundation\nimport TelegramCore\nimport CaptionWire\nfunc caption(_ file:TelegramMediaFile,_ text:NSAttributedString)->NSAttributedString {chatComposerSpacedFileCaption(text,file:file,maxCaptionLength:1024)}\n')
    run(['-typecheck', '-I', folder, caller])
    geometry = folder / 'geometry.swift'
    code = rt.geometry_fixture(source).replace('import Foundation', 'import Foundation\nimport UIKit', 1)
    code = code.replace('struct UIEdgeInsets {let top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat}\n', '', 1)
    geometry.write_text(code)
    p = subprocess.run([str(swiftc), '-frontend', '-parse', str(geometry)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    report = {'actual_foundation_helper_and_cross_module_caller': 'passed', 'telegram_media_io': 'explicit host;actual properties guarded', 'generated_uikit_geometry_parse': 'passed', 'real_uikit_geometry': 'not_run', 'full_application_sdk': 'not_run', 'physical_iphone': 'pending', 'official_telegram_live_render': 'pending'}
    if flags:
        run(['-typecheck', geometry])
        report['real_uikit_geometry'] = 'passed: actual inset expressions with real UIKit UIEdgeInsets/CGSize; glyph rendering and Telegram view graph remain separate'
    return report

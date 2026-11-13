"""Actual settings module API; real UIKit/Photos typecheck on Apple."""
import subprocess,sys
from pathlib import Path
from original_video_mode_runtime import fixture,LEGACY
from validate_quick_format import block

SETTINGS='submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift'


def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    flags=[]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        flags=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    module=folder/'NagramiXMediaSettings.swiftmodule'
    base=[str(swiftc),'-swift-version','5','-warnings-as-errors','-module-cache-path',str(folder/'module-cache'),*flags]
    r=subprocess.run(base+['-parse-as-library','-emit-module','-module-name','NagramiXMediaSettings','-emit-module-path',str(module),str(source/SETTINGS)],capture_output=True,text=True,timeout=120);assert r.returncode==0,r.stdout+r.stderr
    caller=folder/'settings-caller.swift';caller.write_text('import NagramiXMediaSettings\nfunc readOriginalVideoMode()->Bool{NagramiXMediaSettings.current.originalVideos}\n')
    r=subprocess.run(base+['-typecheck','-I',str(folder),str(caller)],capture_output=True,text=True,timeout=120);assert r.returncode==0,r.stdout+r.stderr
    report={'settings_module':'passed; actual complete production settings source compiled as a module and current.originalVideos imported by caller','uikit_photos':'not_run','device':'pending'}
    if sys.platform!='darwin':
        report['reason']='UIKit and Photos require macOS/iOS SDK; Linux does not simulate SDK success.';return report
    code=fixture(source).split('\nvar checks=0',1)[0]
    for marker in ['class UIImage {','struct Subtypes:','enum MediaType {','final class AssetResult {','final class PHAsset {','enum Export {','func nagramiXOriginalVideoFile(account:','struct NagramiXMediaSettings {']:
        code=code.replace(block(code,marker),'',1)
    declaration=block((source/LEGACY).read_text(),'public func nagramiXOriginalVideoFile(account:').split('{',1)[0].replace('public ','').rstrip()
    code='import UIKit\nimport Photos\nimport NagramiXMediaSettings\n'+code+'\n'+declaration+'{.never()}\n'
    path=folder/'original-video-native-api.swift';path.write_text(code)
    r=subprocess.run(base+['-typecheck','-parse-as-library','-I',str(folder),str(path)],capture_output=True,text=True,timeout=120);assert r.returncode==0,r.stdout+r.stderr
    report['uikit_photos']='passed; entire actual new helper and context wrapper with real UIKit/Photos/current settings module; original exporter declaration extracted verbatim, Telegram/media/model I/O adapters explicit'
    return report

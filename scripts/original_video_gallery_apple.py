"""Проверить real settings API; UIKit/Photos producer и gallery helper — только на macOS."""
from pathlib import Path
import subprocess,sys
from validate_quick_format import block
from original_video_media_apple import check as exporter_check
import original_video_mode_runtime as mode


def check(source,swiftc,folder):
    report=exporter_check(source,swiftc,folder/'exporter')
    report['gallery_uikit_photos']='not_run'
    if sys.platform!='darwin':return report
    code=mode.fixture(source).split('\nvar checks=0',1)[0]
    code+='\nextension MediaEditorValues {func withUpdatedVideoTrimRange(_ value:Range<Double>?)->MediaEditorValues {var result=self;result.videoTrimRange=value;return result}}\n'
    for marker in ['class UIImage {','struct Subtypes:','enum MediaType {','final class AssetResult {','final class PHAsset {','enum Export {','func nagramiXOriginalVideoFile(account:','struct NagramiXMediaSettings {']:
        code=code.replace(block(code,marker),'',1)
    declaration=block((source/mode.LEGACY).read_text(),'public func nagramiXOriginalVideoFile(account:').split('{',1)[0].replace('public ','').rstrip()
    code='import UIKit\nimport Photos\nimport NagramiXMediaSettings\n'+code+'\n'+declaration+'{.never()}\n'
    path=folder/'gallery-native-api.swift';path.write_text(code)
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    result=subprocess.run([str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-typecheck','-sdk',sdk,'-target','arm64-apple-ios15.0','-I',str(folder/'exporter'),'-module-cache-path',str(folder/'cache'),str(path)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    report['gallery_uikit_photos']='passed; actual whole helper/context with real Photos/UIKit and current settings module; exporter signature extracted from production. MediaEditor/Telegram data are explicit model boundaries; public trim-updater declaration is pinned.'
    return report

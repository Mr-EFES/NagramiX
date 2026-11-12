"""Ранний typecheck настоящих новых мостов против AVKit/WebKit SDK."""
import subprocess,sys
from validate_quick_format import block
from system_web_picture_in_picture_runtime import AV,WEB


def check(source,swiftc,folder):
 if sys.platform!='darwin':return {'status':'not_run','reason':'Real AVKit/WebKit/AVFoundation SDK requires macOS'}
 code='import Foundation\nimport UIKit\nimport AVKit\nimport AVFoundation\n@preconcurrency import WebKit\n'
 code+='final class ValuePromise<T> {init(_ value:T,ignoreRepeated:Bool){};func set(_ value:T){}}\n'
 code+=block((source/AV).read_text(),'final class NagramiXAVPlayerPictureInPicture:')+'\n'
 code+=block((source/WEB).read_text(),'private final class NagramiXWebSystemPictureInPicture:')+'\n'
 path=folder/'system-web-real-sdk.swift';path.write_text(code)
 sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
 p=subprocess.run([str(swiftc),'-swift-version','5','-typecheck','-warnings-as-errors','-sdk',sdk,'-target','arm64-apple-ios15.0','-module-cache-path',str(folder/'system-web-sdk-cache'),str(path)],capture_output=True,text=True,timeout=120)
 assert p.returncode==0,p.stdout+p.stderr
 return {'status':'passed','target':'arm64-apple-ios15.0','scope':'Entire actual AVPlayer PiP owner and WKWebView frame/message bridge; real framework constructors, delegates, JS dispatch and background policy. ValuePromise ownership is an explicit SignalKit adapter. No iPhone or stream execution.'}

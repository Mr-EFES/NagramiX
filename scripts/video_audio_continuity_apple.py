"""Compile final production WebKit bridge and audio repair against the actual iOS SDK."""
import subprocess
import sys
from system_web_picture_in_picture_apple import check as bridge_check
from validate_quick_format import block
from video_audio_continuity_runtime import AUDIO


def check(source, swiftc, folder):
    if sys.platform != 'darwin':
        return {'status': 'not_run', 'reason': 'AVFoundation/AVKit/WebKit require macOS with iOS SDK'}
    bridge = bridge_check(source, swiftc, folder)
    audio = (source / AUDIO).read_text()
    start = audio.index('        let nagramiXPlaybackNeedsConfiguration: Bool')
    end = audio.index('            self.currentTypeAndOutputMode = (type, outputMode)', start)
    repair = audio[start:end] + 'return true\n}\nreturn false\n'
    start = audio.index('                    let nagramiXConfigureAtomically: Bool')
    end = audio.index('                    if nagramiXConfigureAtomically {', start)
    configure = audio[start:end] + block(audio, '                    if nagramiXConfigureAtomically {')
    code = '''import AVFoundation
enum Session: Equatable {case play(mixWithOthers:Bool);case record(Bool,Bool,Bool)}
enum Output: Equatable {case system}
final class AudioRepair {
 var currentTypeAndOutputMode:(Session,Output)?
 func needsSetup(type:Session,outputMode:Output)->Bool {
''' + repair + '''
 }
 func configure(type:Session,nagramiXRestoringMixedPlayback:Bool,nativeCategory:AVAudioSession.Category,mode:AVAudioSession.Mode,options:AVAudioSession.CategoryOptions) throws {
''' + configure + '''
 }
}
'''
    path = folder / 'video-audio-actual-avfoundation.swift'
    path.write_text(code)
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    result = subprocess.run([str(swiftc), '-swift-version', '5', '-typecheck', '-warnings-as-errors',
                             '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-module-cache-path',
                             str(folder / 'video-audio-sdk-cache'), str(path)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return {'status': 'passed', 'bridge': bridge, 'audio_repair': 'Actual production category/mode/options reconciliation and atomic AVAudioSession configuration; real AVFoundation declarations, arm64 iOS15. Session/holder identity are explicit local adapters.', 'device': 'pending'}

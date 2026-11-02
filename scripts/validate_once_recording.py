#!/usr/bin/env python3
"""Check native view-once initialization without building the iOS application."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
ROOT = Path(__file__).resolve().parents[1]
SETTINGS = 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
PANEL = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift'
CAMERA = 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'
RECORDING = 'submodules/TelegramUI/Sources/Chat/ChatControllerMediaRecording.swift'
HELPER = 'submodules/NagramiXCore/Sources/NagramiXRecordingSettings.swift'

def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def block(text, marker):
    assert text.count(marker) == 1, marker
    start = text.index(marker)
    brace = text.index('{', start)
    depth = 1
    for i in range(brace + 1, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0: return text[start:i+1]
    raise AssertionError('unclosed ' + marker)

def attribute_block(text, marker):
    start = text.index(marker)
    return textwrap.dedent('\n'.join(text[start:].splitlines()[:4]))

def generated_native(after):
    panel = (after/PANEL).read_text(); camera = (after/CAMERA).read_text(); recording = (after/RECORDING).read_text()
    prepare = block(panel, '    public func nagramiXPrepareAudioViewOnce(')
    toggle = block(panel, '    @objc private func viewOncePressed()').replace('@objc private ', '')
    end = block(panel, '        self.mediaActionButtons.micButton.endRecording =')
    callback = end.replace('self.mediaActionButtons.micButton.endRecording =', 'let callback: (Bool) -> Void =', 1)
    camera_state = block(camera, 'struct CameraState: Equatable')
    camera_init = camera[camera.index('            self.cameraState = CameraState('):]
    camera_init = camera_init[:camera_init.index('\n            )')+len('\n            )')].replace('self.cameraState = ', 'return ', 1)
    camera_toggle = block(camera, '        func toggleViewOnce()')
    selection = recording[recording.index('        let viewOnce = scheduleTime == nil'):recording.index('        switch recordedMediaPreview {')]
    audio_direct = attribute_block(recording, '                            var attributes: [EngineMessage.Attribute] = []\n                            if viewOnce {')
    audio_preview = attribute_block(recording, '            var attributes: [EngineMessage.Attribute] = []\n            if viewOnce {')
    video_attrs = attribute_block(camera, '                var attributes: [EngineMessage.Attribute] = []\n                if self.cameraState.isViewOnceEnabled')
    return '\n'.join([
        'import Foundation',camera_state,
        'extension InputPanel {',prepare,toggle,
        'func endRecording(sendMedia: Bool) {',callback,'callback(sendMedia)','}','}',
        'func makeInitialCameraState(controller: AvailabilityController, isFrontPosition: Bool = false, isDualCameraEnabled: Bool = false) -> CameraState {',
        camera_init,'}',
        'extension VideoController {',camera_toggle,
        'func attributes(scheduleTime: Int32? = nil, repeatPeriod: Int32? = nil) -> [EngineMessage.Attribute] {',video_attrs,'return attributes','}','}',
        'func directAudioAttributes(viewOnce: Bool) -> [EngineMessage.Attribute] {',audio_direct,'return attributes','}',
        'extension AudioController {',
        'func previewAttributes(viewOnce: Bool? = nil, scheduleTime: Int32? = nil, repeatPeriod: Int32? = nil) -> [EngineMessage.Attribute] {',
        selection,audio_preview,'return attributes','}','}'
    ])+'\n'

def validate(before, after, swiftc):
    plan = json.loads((ROOT/'ios/once_recording_patches.json').read_text())
    a,b = manifest(before),manifest(after)
    changed = {n for n in a if a[n] != b.get(n)}
    expected = {p[0] for p in plan['patches']} | {
        'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',
        *[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru','en']]}
    assert changed == expected, changed ^ expected
    assert b.keys()-a.keys() == {HELPER} and not a.keys()-b.keys()
    texts = {n:(before/n).read_text() for n in plan['hashes']}
    assert all(a[n] == sha for n,sha in plan['hashes'].items())
    for n,old,new,count in plan['patches']:
        assert texts[n].count(old) == count
        texts[n] = texts[n].replace(old,new,count)
    assert all((after/n).read_bytes() == v.encode() for n,v in texts.items())
    for src,dst in plan['provided'].items(): assert (after/dst).read_bytes() == (ROOT/'ios'/src).read_bytes()
    spec = importlib.util.spec_from_file_location('once',ROOT/'ios/once_recording.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        def seed(p):
            for n in plan['hashes']:
                q=p/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before/n,q)
            for src,n in plan['provided'].items():
                q=p/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ios'/src,q)
        def reject(p,label,overlay=ROOT/'ios'):
            original=manifest(p)
            try: module.apply_once_recording(p,overlay)
            except (SystemExit,FileNotFoundError): pass
            else: raise AssertionError(label)
            assert manifest(p)==original,'partial write: '+label
            rejected.append(label)
        p=folder/'valid';seed(p);module.apply_once_recording(p,ROOT/'ios')
        assert all((p/n).read_bytes()==(after/n).read_bytes() for n in plan['hashes'])
        reject(p,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                p=folder/(kind+str(i));seed(p)
                if kind=='missing': (p/n).unlink()
                else: (p/n).write_bytes((p/n).read_bytes()+b'\n// drift\n')
                reject(p,kind+' '+n)
        for src,n in plan['provided'].items():
            for kind in ['missing','drift']:
                p=folder/(kind+'-helper');seed(p)
                if kind=='missing': (p/n).unlink()
                else: (p/n).write_text('// stale helper')
                reject(p,kind+' helper')
            p=folder/'template';seed(p);overlay=folder/'overlay';overlay.mkdir();shutil.copy2(ROOT/'ios/once_recording_patches.json',overlay)
            reject(p,'missing canonical helper',overlay)
    execution=[]
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp);native=folder/'GeneratedNative.swift';native.write_text(generated_native(after))
        for mode in ['debug','optimized']:
            binary=folder/('once-'+mode)
            command=[str(swiftc),'-warnings-as-errors','-module-cache-path',str(folder/'module-cache'),str(after/HELPER),str(native),str(ROOT/'scripts/tests/NagramiXOnceRecordingTests.swift'),'-o',str(binary)]
            if mode=='optimized': command.insert(1,'-O')
            subprocess.run(command,check=True)
            env=dict(os.environ,XDG_CONFIG_HOME=str(folder/('preferences-'+mode)))
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,env=env,timeout=30).strip())
            for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:
                subprocess.run([str(binary),command,value],env=env,check=True,stdout=subprocess.PIPE,timeout=15)
            execution.append(mode+': PASS 6 separate cold processes')
        subprocess.run([str(swiftc),'-frontend','-parse',*[str(after/n) for n in sorted(changed|{HELPER}) if n.endswith('.swift')]],check=True)
    settings=(after/SETTINGS).read_text();panel=(after/PANEL).read_text();recording=(after/RECORDING).read_text();camera=(after/CAMERA).read_text()
    args=block(settings,'private struct NagramiXSettingsControllerArguments')
    initializer=settings[settings.index('    let arguments = NagramiXSettingsControllerArguments('):settings.index('    let mediaInputSettings = context.sharedContext.accountManager.sharedData(')]
    # Memberwise initialization must preserve declaration order.
    declared=re.findall(r'^    let (\w+):',args,re.M)
    called=re.findall(r'^        (\w+):',initializer,re.M)
    assert declared==called,(declared,called)
    assert settings.count('case .viewOnceRecording: return 155')==1
    assert settings.count('case .viewOnceRecording: return 112')==1
    assert '.keepMusicPlayingWhileRecording, .viewOnceRecording, .keepMusicPlayingWhileRecordingInfo' in settings
    assert '.viewOnceRecording(NagramiXRecordingSettings.viewOnceEnabled)' in settings
    assert 'maximumNumberOfLines: 0' in settings[settings.index('case let .viewOnceRecording(value):'):][:400]
    assert 'return strings.nagramiXViewOnceRecordingSearchTerms' in settings
    assert 'viewOnceAvailable: viewOnceAvailable && !isBot' in recording
    assert 'nagramiXPrepareAudioViewOnce(resuming: existingDraft != nil)' in recording
    assert 'sendRecordedMedia(false, strongSelf.chatDisplayNode.textInputPanelNode?.viewOnce ?? false)' in recording
    assert 'viewOnce: Bool? = nil' in recording
    assert 'viewOnce = NagramiXRecordingSettings' not in block(panel,'    @objc private func viewOncePressed()')
    assert block(camera,'        func toggleViewOnce()') == block((before/CAMERA).read_text(),'        func toggleViewOnce()')
    assert '"//submodules/NagramiXCore:NagramiXCore"' in (after/'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/BUILD').read_text()
    for lang,title in [('ru','Одноразовая запись медиа'),('en','One-Time Media Recording')]:
        s=(after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert s.count('"NagramiX.Recording.ViewOnce.Title" = "'+title+'";')==1
        assert s.count('"NagramiX.Recording.ViewOnce.SearchTerms" = ')==1
    for n in ['ios/apply_features.py','ios/once_recording.py','scripts/validate_once_recording.py']:ast.parse((ROOT/n).read_text())
    return {'outputs':len(b),'changed':sorted(changed),'added':sorted(b.keys()-a.keys()),'unchanged':len(a)-len(changed),'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,'execution':execution,'apple_sdk':'not run: no build authorization','physical_iphone':'pending'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args.before,args.after,args.swiftc)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

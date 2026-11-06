#!/usr/bin/env python3
"""Проверить расшифровку одноразовых голосовых без потребления и потери архива."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from validate_quick_format import block, manifest

ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'temporary_voice_transcription_patches.json').read_text())
R='submodules/NagramiXTranscription/Sources/Runtime.swift'
A='submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift'
E='submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift'
F='submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift'

def sha(data):return hashlib.sha256(data).hexdigest()

def runtime_checks(source,swiftc,temp):
    root=ROOT
    def clean(s):return '\n'.join(l for l in s.splitlines() if not l.startswith('import ')).replace('public ','')
    r=R; a=A; e=E; f=F
    (temp/'Runtime.swift').write_text('import Foundation\n'+clean((source/r).read_text()))
    (temp/'Engine.swift').write_text('import Foundation\n'+clean((source/e).read_text()))
    policy=(source/'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift').read_text();policy=block(policy,'public func nagramiXCanPlayTemporaryVoiceInline(')
    (temp/'Policy.swift').write_text('import Foundation\n'+clean(policy))
    boundary=(root/'scripts/tests/NagramiXTemporaryTranscriptionBoundary.swift').read_text()
    archive=(source/a).read_text()
    methods='\n'.join(clean(block(archive, anchor)) for anchor in ['    public func transcriptionMessage(', '    public func updateTranscriptionAttributes('])
    boundary=boundary.replace('// PRODUCTION_ARCHIVE_METHODS',methods)
    start=archive.index('        var attributes: [MessageAttribute] = (record.transcriptionAttributes')
    end=archive.index('        if !record.content.entities.isEmpty',start)
    boundary=boundary.replace('// PRODUCTION_RENDER_ATTRIBUTES',archive[start:end])
    boundary=boundary.replace('// PRODUCTION_ARCHIVE_RECORD',block(archive,'private struct NagramiXArchivedRecord:').replace('private ',''))
    node=(source/f).read_text();start=node.index('                var displayTranscribe = false');end=node.index('                let transcribedText =',start)
    decision_start=node.index('        var shouldBeginTranscription = false')
    decision_end=node.index('        if shouldBeginTranscription {',decision_start)
    boundary=boundary.replace('// PRODUCTION_NATIVE_REQUEST_DECISION',node[decision_start:decision_end])
    (temp/'Boundary.swift').write_text(boundary)
    ui='''
    import Foundation
    struct PresentationBoundary { var isPreview=false }
    struct BoostBoundary {var providedByGroupBoost=false;var canBeDisplayed=false;var displayForNotConsumed=false}
    struct AssociatedBoundary {var isPremium=false;var alwaysDisplayTranscribeButton=BoostBoundary()}
    struct ArgumentsBoundary {let message:Message;let context:AccountContext;var incoming=true;var presentationData=PresentationBoundary();var associatedData=AssociatedBoundary()}
    struct PremiumConfiguration {var audioTransciptionTrialCount=0;var audioTransciptionTrialMaxDuration=60;static func with(appConfiguration:Int)->Self {Self()}}
    struct CurrentConfiguration {func with(_ transform:(Int)->Int)->Int{transform(0)}}
    extension AccountContext {var currentAppConfiguration:CurrentConfiguration{CurrentConfiguration()}}
    func displayButton(_ message:Message,premium:Bool,preview:Bool=false,audioDuration:Int=10)->Bool {
     var arguments=ArgumentsBoundary(message:message,context:AccountContext());arguments.associatedData.isPremium=premium;arguments.presentationData.isPreview=preview
     let isViewOnceMessage=(message.media[0] as! TelegramMediaFile).isVoice && (message.minAutoremoveOrClearTimeout == viewOnceTimeout || nagramiXCanPlayTemporaryVoiceInline(message))
     let isConsumed=false
    '''+node[start:end]+'''return displayTranscribe
    }
    '''
    (temp/'UI.swift').write_text(ui)
    files=[]
    for name in ['Settings','Coordinator']:
     p=temp/(name+'.swift');p.write_text('import Foundation\n'+clean((source/('submodules/NagramiXTranscription/Sources/'+name+'.swift')).read_text()));files.append(p)
    files += [temp/'Boundary.swift',temp/'Runtime.swift',temp/'Engine.swift',temp/'Policy.swift',temp/'UI.swift',root/'scripts/tests/NagramiXTemporaryTranscriptionTests.swift']
    for optimized in [False, True]:
        binary=temp/('checks-O' if optimized else 'checks-debug')
        subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*[str(p) for p in files],'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location('temporary_voice_transcription',OVERLAY/'temporary_voice_transcription.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    def seed(label):
        target=temp/label
        for name in {**PLAN['inputs'],**PLAN['guards']}:
            data=(OVERLAY/PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source/name).read_bytes()
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return target
    def reject(target,label):
        before=manifest(target)
        try:module.apply_temporary_voice_transcription(target,OVERLAY)
        except (OSError,SystemExit):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(target)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');module.apply_temporary_voice_transcription(valid,OVERLAY)
    for name,digest in PLAN['outputs'].items():assert sha((valid/name).read_bytes())==digest
    reject(valid,'repeat')
    for i,name in enumerate({**PLAN['inputs'],**PLAN['guards']}):
        for kind in ['missing','drift']:
            target=seed(str(i)+kind)
            if kind=='missing':(target/name).unlink()
            else:(target/name).write_bytes(b'drift')
            reject(target,name+':'+kind)
    broken=temp/'broken-overlay'
    for name in PLAN['templates']:
        path=broken/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((OVERLAY/name).read_bytes())
    (broken/'temporary_voice_transcription_patches.json').write_text(json.dumps(PLAN))
    last=next(reversed(PLAN['replacements'].values()))
    (broken/last).write_bytes(b'bad final output template')
    target=seed('bad-template');before=manifest(target)
    try:module.apply_temporary_voice_transcription(target,broken)
    except SystemExit:pass
    else:raise AssertionError('Bad output template accepted')
    assert manifest(target)==before,'Output template caused partial write'
    rejected.append('bad final output template')
    return len(rejected)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path)
    args=parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    for stage in ('pip_transition_geometry', 'transfer_consistency', 'editor_attachment_delivery', 'local_model_size', 'archive_deletion_effect', 'pip_visual_handoff', 'local_model_menu', 'archive_deletion_visibility', 'temporary_media_actions', 'message_copy_availability', 'vosk_model_naming', 'local_asr_memory', 'archive_post_lifecycle'):
        if delegate_icon_stage_if_applied(args, Path(__file__), stage):
            return
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((args.source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    with tempfile.TemporaryDirectory(prefix='temporary-asr-checks-') as folder:
        temp=Path(folder)
        rejected=guard_checks(args.source,temp/'guards')
        if args.swiftc:
            runtime=temp/'runtime';runtime.mkdir()
            runtime_checks(args.source,args.swiftc,runtime)
            for name in PLAN['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/name)],check=True)
    print(f'PASS: temporary ASR outputs/guards/templates, {rejected} invalid inputs rejected before writes. Apple SDK/device pending.')

if __name__=='__main__':main()

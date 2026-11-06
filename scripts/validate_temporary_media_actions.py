#!/usr/bin/env python3
"""Validate retained temporary media actions, ASR persistence and ON/OFF boundaries."""
import argparse, copy, hashlib, importlib.util, json, resource, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block, manifest
ROOT=Path(__file__).resolve().parents[1]
OVERLAY=ROOT/'ios'
PLAN=json.loads((OVERLAY/'temporary_media_actions_patches.json').read_text())
P,A,R,F,ROUND,C,O,M,FW,S,SAVE,CONTROLLER,LOAD,NATIVE,STATE=PLAN['inputs']
E='submodules/TelegramCore/Sources/TelegramEngine/Messages/NagramiXLocalMessageData.swift'
def sha(data):return hashlib.sha256(data).hexdigest()

def runtime_checks(source,swiftc,temp):
    root=ROOT
    def clean(s):return '\n'.join(l for l in s.splitlines() if not l.startswith('import ')).replace('public ','')
    r=R; a=A; e=E; f=F
    (temp/'Runtime.swift').write_text('import Foundation\n'+clean((source/r).read_text()))
    engine=(source/e).read_text()
    engine=engine.replace(block(engine,'    func nagramiXArchivePostDeletionPlan('), '')
    (temp/'Engine.swift').write_text('import Foundation\n'+clean(engine))
    policy=(source/'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift').read_text();policy='\n'.join(block(policy, a) for a in ['public func nagramiXCanPlayTemporaryVoiceInline(', 'public func nagramiXCanUseTemporaryMediaActions(', 'public func nagramiXCanTranscribeTemporaryMedia('])
    (temp/'Policy.swift').write_text('import Foundation\n'+clean(policy))
    boundary=(root/'scripts/tests/NagramiXTemporaryMediaBoundary.swift').read_text()
    archive=(source/a).read_text()
    methods='\n'.join(clean(block(archive, anchor)) for anchor in ['    public func transcriptionMessage(', '    public func updateTranscriptionAttributes(', '    public func archiveServerDeletion(messageIds:', '    public func archiveServerDeletion(globalIds:', '    func retainTelegramTranscription('])
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
    round_node=(source/ROUND).read_text()
    a=round_node.index('                    var displayTranscribe = false')
    b=round_node.index('                    if displayTranscribe,',a)
    round_ui="""
    enum StatusDisplayType {case free,other}
    func displayRoundButton(_ message:Message,premium:Bool,preview:Bool=false)->Bool {
     var item=ArgumentsBoundary(message:message,context:AccountContext());item.associatedData.isPremium=premium;item.presentationData.isPreview=preview
     let statusDisplayType=StatusDisplayType.free, incoming=true, notConsumed=true
     let isViewOnceMessage=message.minAutoremoveOrClearTimeout == viewOnceTimeout
    """+round_node[a:b]+"return displayTranscribe\n}\n"
    (temp/'UI.swift').write_text(ui+round_ui)
    files=[]
    for name in ['Settings','Coordinator']:
     p=temp/(name+'.swift');p.write_text('import Foundation\n'+clean((source/('submodules/NagramiXTranscription/Sources/'+name+'.swift')).read_text()));files.append(p)
    files += [temp/'Boundary.swift',temp/'Runtime.swift',temp/'Engine.swift',temp/'Policy.swift',temp/'UI.swift',root/'scripts/tests/NagramiXTemporaryMediaTests.swift']
    for optimized in [False, True]:
        binary=temp/('checks-O' if optimized else 'checks-debug')
        subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*[str(p) for p in files],'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)



    originals={name:(temp/name).read_text() for name in ['Runtime.swift','UI.swift','Boundary.swift']}
    mutants={
        'voice-only-asr':('Runtime.swift',originals['Runtime.swift'].replace('nagramiXCanTranscribeTemporaryMedia(message)','nagramiXCanPlayTemporaryVoiceInline(message)')),
        'disappearing-icon':('UI.swift',originals['UI.swift'].replace('|| nagramiXCanTranscribeTemporaryMedia(arguments.message)','|| NagramiXTranscriptionRuntime.hasTemporaryTranscript(arguments.message)')),
        'server-demotion':('Boundary.swift',originals['Boundary.swift'].replace('record.deletedAt = deletedAt','record.temporary = false; record.viewOnceReplay = nil; record.deletedAt = deletedAt')),
        'lost-native-text':('Boundary.swift',originals['Boundary.swift'].replace('guard attribute.error == nil else { return }','return\n        guard attribute.error == nil else { return }')),
    }
    # The native no-op mutation is a complete body replacement, without unreachable code warnings.
    bad=originals['Boundary.swift'];method=block(bad,'    func retainTelegramTranscription(')
    mutants['lost-native-text']=('Boundary.swift',bad.replace(method,'    func retainTelegramTranscription(id: MessageId, attribute: AudioTranscriptionMessageAttribute) {}'))
    for label,(name,mutated) in mutants.items():
        assert mutated != originals[name], label
        for key,text in originals.items():(temp/key).write_text(text)
        (temp/name).write_text(mutated)
        for optimized in [False, True]:
            binary=temp/(label+('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*[str(p) for p in files],'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            assert result.returncode != 0 and 'Temporary media regression:' in result.stderr, label+result.stdout+result.stderr
        print('PASS: rejected previous behavior '+label,flush=True)


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('copy_availability', OVERLAY / 'temporary_media_actions.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            p = tree / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree
    rejected = []
    def reject(tree, label, overlay=OVERLAY):
        start = manifest(tree)
        try:
            module.apply_temporary_media_actions(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == start, 'Partial write: ' + label
        rejected.append(label)
    valid = seed('valid'); module.apply_temporary_media_actions(valid, OVERLAY)
    assert all((valid / n).read_bytes() == (source / n).read_bytes() for n in PLAN['outputs'])
    reject(valid, 'repeat')
    for i, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(f'{i}-{kind}')
            if kind == 'missing': (tree / name).unlink()
            else: (tree / name).write_bytes(b'drift')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN); bad[field][next(iter(bad[field]))] = '0' * 64; variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN); bad[field][A] = '../outside.swift'; variants.append((field, bad))
    bad = copy.deepcopy(PLAN); bad['outputs'].clear(); variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            p = overlay / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'temporary_media_actions_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for i, name in enumerate([A, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(i)); p = tree / name; outside = temp / ('outside-' + str(i))
        outside.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(outside); reject(tree, 'external symlink ' + name)
    return rejected


def copy_checks(source, swiftc, temp):
    from validate_recipient_copy_isolation import common_source
    from validate_message_copy_availability import poll_boundary, stripped
    common=common_source(source).replace('    var id = MessageId(); var text','    var peers: [PeerId: Any] = [:]\n    var id = MessageId(); var text')+'\n'+poll_boundary(source)
    common=common.replace('struct NagramiXArchivedMessageAttribute: MessageAttribute {}','struct NagramiXArchivedMessageAttribute: MessageAttribute {var isTemporary=false}')
    common=common.replace('    func isCopyProtected() -> Bool { protected }','    var isSelfExpiring: Bool { minAutoremoveOrClearTimeout != nil }; var paidContent: Media? {media.first{$0 is TelegramMediaPaidContent}}\n    func isCopyProtected() -> Bool { protected }')
    common=common.replace('    var isVoice: Bool {','    var isVideo: Bool {attributes.contains("video")}\n    var isVoice: Bool {')
    helpers=[]
    for n in [P,C,O,'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaCopy.swift']:
        text=(source/n).read_text()
        if n==P:text=block(text,'public func nagramiXCanUseTemporaryMediaActions(')
        p=temp/Path(n).name;p.write_text('import Foundation\n'+stripped(text));helpers.append(p)
    suite=temp/'copy-suite.swift';suite.write_text(common+'\n'+(ROOT/'scripts/tests/NagramiXTemporaryCopyTests.swift').read_text())
    for optimized in [False, True]:
        binary=temp/('copy-O' if optimized else 'copy-debug')
        subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*map(str,helpers),str(suite),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
    for label, fixture in [('recipient','NagramiXRecipientCopyTests.swift'),('rich','NagramiXRichContentCopyTests.swift')]:
        tests=(ROOT/'scripts/tests'/fixture).read_text()
        if label=='rich':tests='@main struct RichContentCopyTests'+tests.split('@main struct RichContentCopyTests',1)[1]
        tests=tests.replace('var checks = 0','NagramiXPrivacySettings.current.bypassScreenshots = true\n        var checks = 0',1)
        suite.write_text(common+'\n'+tests)
        for optimized in [False, True]:
            binary=temp/(label+('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*map(str,helpers),str(suite),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)


def verify(source):
    for n,h in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/n).read_bytes())==h,n
    for n,h in PLAN['templates'].items():assert sha((OVERLAY/n).read_bytes())==h,n
    archive=(source/A).read_text(); menu=(source/M).read_text(); fw=(source/FW).read_text()
    assert 'record.temporary = false' not in archive and 'record.viewOnceReplay = nil' not in archive
    assert archive.count('let visibleForReplay = settings.replayViewOnce && record.wasTemporary')==2
    assert 'if archivedAttribute != nil && !nagramiXTemporaryActions {' in menu
    assert 'forward(copies)' in menu and 'original.withUpdatedText(prefix + original.text)' in menu
    assert 'prefix.utf16.count' in menu
    assert 'if nagramiXRetainedTemporary ||' in menu and 'nagramiXArchivedSaveMediaActions' in menu
    assert 'context.engine.messages.nagramiXTranscriptionMessages([messageId])' in (source/CONTROLLER).read_text()
    assert 'retainTelegramTranscription' in (source/NATIVE).read_text() and 'retainTelegramTranscription' in (source/STATE).read_text()
    assert fw.count('nagramiXCanCopyMessagesAsNew(messages, accountPeerId:')>=4
    pipeline=(OVERLAY/'apply_overlay.py').read_text()
    assert pipeline.index('    apply_message_copy_availability(')<pipeline.index('    apply_temporary_media_actions(')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path);p.add_argument('--report',type=Path)
    args=p.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_playback_commands'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'round_caption_transport'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'repost_copy_integrity'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'native_pip_baseline'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'copy_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_visibility'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-temporary-media-') as directory:
        temp=Path(directory);rejected=guard_checks(args.source,temp/'guards')
        if args.swiftc:
            runtime=temp/'runtime';runtime.mkdir();runtime_checks(args.source,args.swiftc,runtime)
            copies=temp/'copies';copies.mkdir();copy_checks(args.source,args.swiftc,copies)
            for n in PLAN['outputs']:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/n)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'fail_closed_cases':len(rejected),'sdk':'not run','device':'pending','boundaries':'Actual runtime, archive deletion/ASR persistence, Engine mutations and extracted voice/round button decisions. Postbox, disk, HTTP, Speech and UIKit rendering are doubles.'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

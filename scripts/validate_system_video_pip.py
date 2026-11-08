#!/usr/bin/env python3
"""Проверить жизненный цикл системного PiP и привязку галереи."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'system_video_pip_patches.json').read_text())
I = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'


def historical_late_source(source):
    """Guarded inverse for legacy runtime fixtures after source-only fixes.

    The old standalone validators keep their pre-migration CI checkpoints.
    The final 13.2 gate verifies current outputs before using this view for its
    historical R1/R2/R3 fixture bodies; no current code is replaced on disk.
    """
    from late_source_stages import historical_source
    return historical_source(source)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'System video PiP outputs differ'
    for name, digest in PLAN['guards'].items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name


def reverse(source, prior, plan=PLAN):
    names = set(plan['inputs'])
    for path in OVERLAY.glob('*_patches.json'):
        item = json.loads(path.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings',
                  'submodules/TelegramPresentationData/Sources/PresentationData.swift',
                  'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift'])
    for name in names - set(plan.get('copies', {})):
        path = OVERLAY / plan['previous'][name] if name in plan['previous'] else source / name
        if path.is_file():
            target = prior / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def delegate_icon_stage_if_applied(args, script, stage):
    plan = json.loads((OVERLAY / (stage + '_patches.json')).read_text())
    expected = {**plan['outputs'], **{name: item['sha256'] for name, item in plan.get('copies', {}).items()}}
    # Copy-only stages must be recognized by their resources; all({}) must
    # never mistake an unapplied stage for an applied one.
    if not expected or not all((args.source / name).is_file() and sha((args.source / name).read_bytes()) == digest
                              for name, digest in expected.items()):
        return False
    for name, digest in plan['guards'].items():
        assert sha((args.source / name).read_bytes()) == digest, name
    for name, digest in plan['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    for name, item in plan.get('copies', {}).items():
        assert sha((args.source / name).read_bytes()) == item['sha256'], name
    with tempfile.TemporaryDirectory(prefix=stage + '-prior-') as folder:
        prior = Path(folder)
        reverse(args.source, prior, plan)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def delegate_icons_if_applied(args, script):
    for stage in ('pip_playback_commands', 'round_caption_transport', 'repost_copy_integrity', 'native_pip_baseline', 'copy_delivery', 'rich_draft_upload_retry', 'pip_transition_geometry', 'transfer_consistency', 'editor_attachment_delivery', 'local_model_size', 'archive_deletion_effect', 'pip_visual_handoff', 'local_model_menu', 'archive_deletion_visibility', 'temporary_media_actions', 'message_copy_availability', 'pip_first_request', 'vosk_model_naming', 'local_asr_memory', 'archive_post_lifecycle', 'expanded_keyboard_timing', 'expanded_panel_animation', 'all_language_catalogs', 'localization_standard', 'temporary_voice_transcription', 'app_language_localization', 'broadcast_icon_order', 'author_head_alignment'):
        if delegate_icon_stage_if_applied(args, script, stage):
            return True
    return False


def delegate_if_applied(args, script):
    if delegate_icons_if_applied(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='system-video-pip-prior-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('system_video_pip', OVERLAY / 'system_video_pip.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def seed(label):
        target = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            data = (OVERLAY / PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source / name).read_bytes()
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return target
    rejected = []
    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_system_video_pip(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_system_video_pip(valid, OVERLAY)
    assert all((valid / name).read_bytes() == (source / name).read_bytes() for name in PLAN['outputs'])
    reject(valid, 'повторное применение')
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ('missing', 'drift'):
            target = seed(str(len(rejected)))
            path = target / name
            if kind == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, kind + ' ' + name)
    mutations = []
    for field in ('inputs', 'outputs', 'guards', 'templates'):
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field + '-SHA', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations'][I][0][0] += ' broken'
    mutations.append(('anchor', bad))
    bad = copy.deepcopy(PLAN)
    bad['previous'][I] = '../outside.swift'
    mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ('inputs', 'outputs', 'previous', 'operations'):
        bad[field]['../outside.swift'] = bad[field].pop(I)
    mutations.append(('source-traversal', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations']['/outside.swift'] = bad['operations'].pop(I)
    mutations.append(('operation-path', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for path in PLAN['templates']:
            destination = overlay / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OVERLAY / path).read_bytes())
        (overlay / 'system_video_pip_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    for label, name in [('input-symlink', I), ('guard-symlink', next(iter(PLAN['guards'])))]:
        target = seed(label)
        path = target / name
        external = temp / (label + '.swift')
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(target, label)
    return rejected


def runtime_source(source,mode='current'):
    text=(source/I).read_text();before=(OVERLAY/PLAN['previous'][I]).read_text()
    controller=block(before if mode=='old-lifecycle' else text,'private final class NativePictureInPictureContentImpl:')
    setup=block(before if mode=='old-admission' else text,'private func setupNativePictureInPicture(')
    central=block(block(text,'override func centralityUpdated('),'if #available(iOS 15.0, *)')
    methods='\n'.join(block(text,marker) for marker in ['func pictureInPictureButtonPressed(','func expandPIP(','override func maybePerformActionForSwipeDismiss(','override func maybePerformActionForSwipeDownDismiss(']).replace('UniversalVideoGalleryItemNode','GalleryHarness')
    return '\n'.join([(ROOT/'scripts/tests/NagramiXSystemVideoPiPBoundary.swift').read_text(),controller.replace('private ','').replace('public ',''),'''final class GalleryHarness: GalleryBase {
    let context = AccountContext()
    let footerContentNode = Footer()
    let gallery = GalleryController()
    let navigation = NavigationController()
    var item: Item? = Item()
    var videoNode: UniversalVideoNode? = UniversalVideoNode()
    var nativePictureInPictureContent: AnyObject?
    var activePictureInPictureController: BaseController?
    var activePictureInPictureNavigationController: NavigationController?
    var isCentral: Bool?
    var hasPictureInPicture = true
    var settingsButtonState = 0
    var displayStickersButton = false
    var dismissals = 0
    func galleryController() -> BaseController? { gallery }
    func baseNavigationController() -> NavigationController? { navigation }
    func beginCustomDismiss(_ type: Dismiss) {}
    func completeCustomDismiss(_ active: Bool) { dismissals += 1 }
    func updateControlsVisibility(_ visible: Bool) {}
''',setup.replace('private ',''),methods,'''func updateCentral(_ isCentral: Bool) {
    self.isCentral = isCentral
''',central,'}\n}',(ROOT/'scripts/tests/NagramiXSystemVideoPiPTests.swift').read_text()])


def run_swift(source,swiftc,temp):
    runs=[]
    for mode in ['current','old-lifecycle','old-admission']:
        suite=temp/(mode+'.swift');suite.write_text(runtime_source(source,mode))
        for optimized in [False,True]:
            binary=temp/(mode+('-O' if optimized else '-debug'))
            command=[str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache')]
            if optimized:command+=['-O']
            subprocess.run([*command,str(suite),'-o',str(binary)],check=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if mode=='current':
                assert result.returncode==0,result.stdout+result.stderr
                runs.append(binary.name+': '+result.stdout.strip())
            else:
                assert result.returncode!=0 and 'system PiP regression:' in result.stderr,result.stdout+result.stderr
                runs.append(binary.name+': прежнее отсутствие readiness/ownership воспроизведено и отвергнуто')
            print(runs[-1],flush=True)
    return runs


def contracts(source):
    text=(source/I).read_text()
    for marker,path in PLAN['reviewed'].items():
        assert block(text,marker)==(OVERLAY/path).read_text().removesuffix('\n'),marker
    assert 'MARK: NAGRAM' not in ''.join((OVERLAY/path).read_text() for path in PLAN['reviewed'].values())
    assert text.count('private final class NativePictureInPictureContentImpl:')==1
    assert 'NagramiXNativePlayerPiP' not in text
    assert 'private let moreButtonImage' in text and text.count('private let moreButtonImage')==1
    assert 'import AVKit' in text
    removed=json.loads((OVERLAY/'ghostgram_pip_cleanup_patches.json').read_text())['deletions']
    for name in removed:
        assert not (source/name).exists(),name
    calls=(OVERLAY/'apply_overlay.py').read_text()
    assert calls.index('    apply_avatar_preview_navigation(')<calls.index('    apply_system_video_pip(')
    # Unrelated export, archive and background controls are outside the five replacements.
    before=(OVERLAY/PLAN['previous'][I]).read_text()
    reversed_text=text
    for old,new,_ in reversed(PLAN['operations'][I]):reversed_text=reversed_text.replace(new,old)
    assert reversed_text==before


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if delegate_icons_if_applied(args, Path(__file__)):
        return
    verify(args.source);contracts(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-system-video-pip-') as folder:
        temp=Path(folder);rejected=guard_checks(args.source,temp)
        runs=run_swift(args.source,args.swiftc,temp) if args.swiftc else []
    if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',str(args.source/I)],check=True)
    result={'changed_files':len(PLAN['outputs']),'guards':len(PLAN['guards']),'reviewed_blocks':len(PLAN['reviewed']),'fail_closed':rejected,'executions':runs,'sdk':'не запускалась','device':'ожидает проверки на iPhone','runtime':'full actual controller/playback delegate, setup, centrality, button, swipe and restore; AVKit/KVO/UIKit/account/scheduling boundaries'}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

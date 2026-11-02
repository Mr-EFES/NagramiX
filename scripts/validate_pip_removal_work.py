#!/usr/bin/env python3
"""Проверить удаление PiP и сохранение независимых обработчиков видео."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=json.loads((ROOT/'ios/pip_removal_work_patches.json').read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def is_applied(source):return all((source/n).is_file() and digest(source/n)==h for n,h in PLAN['outputs'].items())
def delegate_if_applied(args):
    from validate_native_player_pip import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,__file__,'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True);return True
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--standalone',action='store_true');args=parser.parse_args()
    from validate_native_player_pip import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    assert is_applied(args.source)
    video=(args.source/'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text();gallery=(args.source/'submodules/GalleryUI/Sources/GalleryControllerNode.swift').read_text();settings=(args.source/'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert 'self.hasPictureInPicture = true' not in video and 'self.footerContentNode.nagramiXPictureInPictureRequested = ' not in video
    assert '        self.nagramiXInstallDirectionalPiPGesture()' not in gallery
    assert '.otherVideoHeader, .videoPiPSwipe(settings.videoPiPSwipe)' not in settings
    assert '                item.performAction(action)' in video
    assert 'NagramiXSystemPiPController' not in video and 'startPictureInPicture' not in video
    assert 'videoPiPSwipe' not in settings
    assert all(not (args.source/n).exists() for n in PLAN.get('deletions', {}))
    from validate_quick_format import block
    before=(ROOT/'ios/pip_removal_work/Before-Video.swift.inc').read_text()
    for marker in ['    @objc func statusButtonPressed()', '    private func shouldAutoplayOnCentrality()', '    private func nagramiXVideoPlaybackRateSliderTapped']:
        if marker in before: assert block(before,marker)==block(video,marker), marker
    assert 'if value && strongSelf.playOnContentOwnership {' in video and 'playOnContentOwnership' in video
    assert 'setNagramiXBackgroundVideoPlayback' in video and 'setNagramiXVideoNowPlaying' in video
    spec=importlib.util.spec_from_file_location('pip_removal_work',ROOT/'ios/pip_removal_work.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-removal-') as d:
        root=Path(d)/'input'
        for n,f in PLAN['previous'].items():
            p=root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/f,p)
        for n,item in PLAN.get('deletions', {}).items():
            path=root/n;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item['source'],path)
        m.apply_pip_removal_work(root,ROOT/'ios');assert is_applied(root)
        if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(root/n) for n in PLAN['outputs']]],check=True)
        if not args.standalone:
            prior=Path(d)/'prior';names=set(PLAN['inputs'])
            for f in (ROOT/'ios').glob('*_patches.json'):
                x=json.loads(f.read_text())
                for field in ('inputs','outputs','guards','copies'):names.update(x.get(field,{}))
            names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
            for n in names:
                src=args.source/n
                if not src.is_file():continue
                dest=prior/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/PLAN['previous'][n] if n in PLAN['previous'] else src,dest)
            for n,item in PLAN.get('deletions', {}).items():
                path=prior/n;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item['source'],path)
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_translation_sdk_fix.py'),'--source',str(prior),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    print('PASS: video PiP implementation removed; playback controls preserved')
if __name__=='__main__':main()

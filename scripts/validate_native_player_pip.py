#!/usr/bin/env python3
"""Проверить новую системную PiP-сессию и обратную совместимость overlay."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=json.loads((ROOT/'ios/native_player_pip_patches.json').read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def is_applied(source):return all((source/n).is_file() and digest(source/n)==h for n,h in PLAN['outputs'].items()) and all((source/n).is_file() and digest(source/n)==x['sha256'] for n,x in PLAN['copies'].items())
def delegate_if_applied(args):
    from validate_media_privacy_fixes import delegate_if_applied as media_delegate
    if media_delegate(args, __file__): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,__file__,'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True);return True
def reverse(source,target):
    names=set(PLAN['inputs'])
    for manifest in (ROOT/'ios').glob('*_patches.json'):
        plan=json.loads(manifest.read_text())
        for field in ('inputs','outputs','guards','copies'):names.update(plan.get(field,{}))
    names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings')
    for name in names-set(PLAN['copies']):
        src=source/name
        if not src.is_file():continue
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'ios'/PLAN['previous'][name] if name in PLAN['previous'] else src,dest)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--standalone',action='store_true');args=parser.parse_args()
    from validate_media_privacy_fixes import delegate_if_applied as media_delegate
    if media_delegate(args, __file__): return
    assert is_applied(args.source)
    prefix=args.source/'submodules/GalleryUI/Sources'
    player=(prefix/'NagramiXNativePlayerPiP.swift').read_text();video=(prefix/'Items/UniversalVideoGalleryItem.swift').read_text()
    assert 'AVPictureInPictureController(playerLayer:' in player and 'AVPictureInPictureSampleBufferPlaybackDelegate' not in player
    assert 'resources.dispose()' in player and 'self.audioLease?.dispose()' in player
    assert player.count('self.controller?.startPictureInPicture()')==1
    assert 'self.view.playerLayer.isReadyForDisplay' in player and 'isPictureInPicturePossible == true' in player
    assert 'data.offset == 0, data.size > 0' in video and 'filter { $0.complete }' in video
    assert 'self.nagramiXPiPFileToken == token' in video and 'video.ownsContentNode' in video
    assert 'videoPiPSwipeEnabled' in video and 'isInstantVideo' in video and 'peerIsCopyProtected' in video
    from validate_quick_format import block
    before=(ROOT/'ios/native_player_pip/Before-Video.swift.inc').read_text()
    for marker in ['    @objc func statusButtonPressed()', '    private func shouldAutoplayOnCentrality()', '    private func nagramiXUpdateBackgroundVideoPlayback()']:
        assert block(before,marker)==block(video,marker), marker
    spec=importlib.util.spec_from_file_location('native_player_pip',ROOT/'ios/native_player_pip.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='nagramix-native-player-') as directory:
        temp=Path(directory)
        def seed():
            base=temp/'input'
            for n,f in PLAN['previous'].items():
                path=base/n;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/f,path)
            return base
        base=seed();module.apply_native_player_pip(base,ROOT/'ios');assert is_applied(base);shutil.rmtree(base)
        for bad in PLAN['inputs']:
            base=seed();path=base/bad;path.write_bytes(path.read_bytes()+b'//drift');snapshot={n:(base/n).read_bytes() for n in PLAN['inputs']}
            try:module.apply_native_player_pip(base,ROOT/'ios')
            except SystemExit:pass
            else:raise AssertionError(bad)
            assert snapshot=={n:(base/n).read_bytes() for n in PLAN['inputs']}
            assert not any((base/n).exists() for n in PLAN['copies']);shutil.rmtree(base)
        if args.swiftc:subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.source/n) for n in [*PLAN['outputs'],*PLAN['copies']]]],check=True)
        if not args.standalone:
            prior=temp/'prior';reverse(args.source,prior)
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_pip_removal_work.py'),'--source',str(prior)],check=True)
    print('PASS: native AVPlayer PiP source / resource and playback guards')
if __name__=='__main__':main()

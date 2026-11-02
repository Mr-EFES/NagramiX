#!/usr/bin/env python3
"""Exercise production video registry, MediaManager writer and remote routing.

Apple MediaPlayer/UI dispatch surfaces are explicit test boundaries, not iOS.
"""
import argparse,json,os,re,subprocess,tempfile,sys,copy
from pathlib import Path
from validate_quick_format import ROOT,manifest,block

MANAGER='submodules/TelegramUI/Sources/MediaManager.swift'
API='submodules/AccountContext/Sources/MediaManager.swift'
GALLERY='submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
HELPER='submodules/TelegramUI/Sources/NagramiXVideoNowPlaying.swift'


def guard_tests(before, plan):
    sys.path.insert(0, str(ROOT / 'ios'))
    from video_now_playing import apply_video_now_playing
    count = 0

    def rejected(change_plan=None, change_source=None, change_overlay=None):
        nonlocal count
        with tempfile.TemporaryDirectory(prefix='video-now-playing-guards-') as directory:
            root = Path(directory)
            source, overlay = root / 'source', root / 'overlay'
            for name in set(plan['inputs']) | set(plan['guards']):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((before / name).read_bytes())
            candidate = copy.deepcopy(plan)
            for item in plan['copies'].values():
                path = overlay / item['source']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / 'ios' / item['source']).read_bytes())
            if change_plan:
                change_plan(candidate)
            (overlay / 'video_now_playing_patches.json').write_text(json.dumps(candidate))
            if change_source:
                change_source(source)
            if change_overlay:
                change_overlay(overlay)
            snapshot = manifest(source)
            try:
                apply_video_now_playing(source, overlay)
            except SystemExit:
                pass
            else:
                raise AssertionError('Invalid video Now Playing plan/source was accepted')
            assert manifest(source) == snapshot, 'Partial mutation on failed guard'
            count += 1

    for name in set(plan['inputs']) | set(plan['guards']):
        rejected(change_source=lambda root, n=name: (root / n).write_bytes(b'drift'))
        rejected(change_source=lambda root, n=name: (root / n).unlink())
    for index in range(len(plan['patches'])):
        rejected(change_plan=lambda p, i=index: p['patches'][i].__setitem__(1, 'missing-anchor'))
    name = next(iter(plan['outputs']))
    rejected(change_plan=lambda p: p['outputs'].__setitem__(name, 'bad-sha'))
    rejected(change_plan=lambda p: p['outputs'].pop(name))
    rejected(change_plan=lambda p: p['inputs'].__setitem__('../escape', 'bad'))
    rejected(change_plan=lambda p: (p['inputs'].__setitem__('../escape', 'bad'), p['outputs'].__setitem__('../escape', 'bad')))
    dest, item = next(iter(plan['copies'].items()))
    rejected(change_source=lambda root: (root / dest).write_bytes(b'collision'))
    rejected(change_overlay=lambda root: (root / item['source']).unlink())
    rejected(change_overlay=lambda root: (root / item['source']).write_bytes(b'drift'))
    rejected(change_plan=lambda p: p['copies'][dest].__setitem__('source', '../escape'))
    rejected(change_plan=lambda p: p['copies'].__setitem__('/tmp/escape', p['copies'].pop(dest)))
    return count


def native_manager(text):
    marker='startStrict(next: { stateAndType, presentationData, videoEntry in'
    start=text.index(marker)+len(marker)
    begin=text.index('            var sharedPlayerIsPlaying = false',start)
    end=text.index('\n        }))',begin)
    writer=text[begin:end]
    writer=re.sub(r'#selector\(self\.[A-Za-z]+\(_:\)\)', '"selector"',writer)
    artwork=block(text,'startStrict(next: { image in').split('image in',1)[1].rsplit('}',1)[0]
    status_body=block(text,'startStrict(next: { next in').split('next in',1)[1].rsplit('}',1)[0]
    code='''
final class NativeManager {
    var baseNowPlayingInfo: [String: Any]?
    var previousState: SharedMediaPlayerItemPlaybackState?
    var previousDisplayData: SharedMediaPlaybackDisplayData?
    let globalControlsArtwork = Promise<(Account, SharedMediaPlaybackAlbumArt)?>()
    let globalControlsStatus = Promise<MediaPlayerStatus?>()
    var currentGlobalControlsOptions = GlobalControlOptions()
    let nagramiXCurrentVideoNowPlaying = Atomic<NagramiXVideoNowPlayingEntry?>(value: nil)
    let nagramiXVideoNowPlayingRegistry = NagramiXVideoNowPlayingRegistry()
    let nagramiXNowPlayingArbitration = NagramiXNowPlayingArbitration()
    let nagramiXVideoNowPlayingValue = Promise<NagramiXVideoNowPlayingEntry?>(nil)
    var nativeCommands: [String] = []
    func playlistControl(_ action: SharedMediaPlayerControlAction, type: MediaManagerPlayerType?) { nativeCommands.append(actionName(action)) }
    func remote(_ action: SharedMediaPlayerControlAction) { self.nagramiXRemoteControl(action) }
    func render(_ stateAndType: (Account,SharedMediaPlayerItemPlaybackStateOrLoading,MediaManagerPlayerType)?, _ presentationData: PresentationData, _ videoEntry: NagramiXVideoNowPlayingEntry?) {
''' + writer + '\n    }\n'
    code+='    func applyArtwork(_ image: UIImage?) {\n'+artwork+'\n    }\n'
    code+='    func applyStatus(_ next: MediaPlayerStatus?) {\n'+status_body+'\n    }\n'
    for marker in ['public func setNagramiXVideoNowPlaying(', 'private func nagramiXRefreshVideoNowPlaying()', 'private func nagramiXRemoteControl(']:code+=block(text,marker)+'\n'
    return code+'}\n'


def validate(args):
    plan=json.loads((ROOT/'ios/video_now_playing_patches.json').read_text())
    before,after=manifest(args.before),manifest(args.after)
    assert {n for n in before if before[n]!=after.get(n)}==set(plan['inputs'])
    assert set(after)-set(before)==set(plan['copies']) and not set(before)-set(after)
    assert all(before[n]==v for n,v in plan['inputs'].items())
    assert all(after[n]==v for n,v in plan['outputs'].items())
    manager=(args.after/MANAGER).read_text();api=(args.after/API).read_text();gallery=(args.after/GALLERY).read_text()
    assert 'self.nagramiXCurrentVideoNowPlaying.with({ $0 == nil })' in manager
    assert manager.count('self.nagramiXRemoteControl(')==6
    assert (args.before/MANAGER).read_text().count('self.nagramiXRemoteControl(')==0
    assert 'nagramiXVideoNowPlayingValue' not in (args.before/MANAGER).read_text()
    # No server read calls, new player/decoder or replacement of native PiP.
    for needle in ['new MediaPlayer','MPNowPlayingInfoCenter','MPRemoteCommandCenter']:
        if needle.startswith('MP'):assert needle not in (args.after/HELPER).read_text() and needle not in gallery
    assert gallery.count('setNagramiXVideoNowPlaying(id: self.playbackOwner, state: nil)')==3
    assert gallery.count('self.updateNowPlaying()')==2
    assert 'nowPlayingTitle: self.nagramiXVideoNowPlayingTitle' in gallery
    assert 'state: NagramiXTabSettings.backgroundVideoPlaybackEnabled ? nowPlaying : nil' in gallery
    assert gallery.count('MediaPlayer(')==(args.before/GALLERY).read_text().count('MediaPlayer(')
    executions=[]
    with tempfile.TemporaryDirectory(prefix='video-now-playing-') as directory:
        tmp=Path(directory)
        native=(args.after/'submodules/MediaPlayer/Sources/MediaPlayer.swift').read_text()
        declarations=block(native,'public enum MediaPlayerPlaybackStatus: Equatable')+'\n'+block(native,'public struct MediaPlayerStatus: Equatable')
        actions=(args.after/'submodules/AccountContext/Sources/SharedMediaPlayer.swift').read_text()
        declarations+='\n'+block(actions,'public enum SharedMediaPlayerPlaybackControlAction')+'\n'+block(actions,'public enum SharedMediaPlayerControlAction')
        declarations+='\n'+block(api,'public struct NagramiXVideoNowPlayingState')
        declarations+='\n'+block(manager,'private struct GlobalControlOptions: OptionSet').replace('private struct','struct',1)
        declarations='import Foundation\ntypealias SharedMediaPlaybackAlbumArt = String\n'+declarations
        helper=(args.after/HELPER).read_text();helper='\n'.join(l for l in helper.splitlines() if not l.startswith('import '))
        (tmp/'Production.swift').write_text(declarations.replace('public ', '')+'\n'+helper+'\n'+native_manager(manager))
        for mode in ['debug','optimized']:
            binary=tmp/mode
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(tmp/'cache'),str(tmp/'Production.swift'),str(ROOT/'scripts/tests/NagramiXVideoNowPlayingBoundary.swift'),str(ROOT/'scripts/tests/NagramiXVideoNowPlayingTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            run=subprocess.run([str(binary)],text=True,capture_output=True,timeout=30)
            assert run.returncode==0,run.stdout+run.stderr
            executions.append({'mode':mode,'output':run.stdout.strip()})
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in list(plan['inputs'])+list(plan['copies']) if n.endswith('.swift')]],check=True)
    # Run the real pinned architectural guard which stopped build124.
    subprocess.run(['python3',str(args.after/'build-system/Make/PostboxImportCheck.py'),str(args.after)],check=True)
    return {'execution':executions,'full_overlay':'PASS','modified':list(plan['inputs']),'added':list(plan['copies']),'other_files_byte_identical':len(before)-len(plan['inputs']),'PostboxImportCheck':'PASS','guards_rejected_without_writes':guard_tests(args.before,plan),'Apple_SDK':'pending','physical_iPhone':'pending; MediaPlayer/UIKit/queues are explicit boundaries'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();result=validate(a);a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

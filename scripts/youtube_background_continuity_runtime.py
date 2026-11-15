"""Actual WebKit bridge, status reconciliation and managed ownership; explicit hosts."""
from validate_quick_format import block
from system_web_picture_in_picture_runtime import WEB,CONTENT,BOUNDARY as WEB_BOUNDARY
from video_audio_continuity_runtime import BOUNDARY as AUDIO_BOUNDARY


def parts(source):
    web=(source/WEB).read_text();content=(source/CONTENT).read_text()
    model=(source/'submodules/MediaPlayer/Sources/MediaPlayer.swift').read_text()
    models='\n'.join(block(model,m) for m in ['public enum MediaPlayerPlaybackStatus:', 'public struct MediaPlayerStatus:'])
    bridge=block(web,'private final class NagramiXWebSystemPictureInPicture:').replace('private final class','final class',1)
    node=block(web,'final class WebEmbedPlayerNode:')
    player=node[node.index('    private var nagramiXLastImplementationStatus:'):node.index('    func play() {')].replace('private ','')
    player+='\n'+'\n'.join(block(node,m) for m in ['    func play()', '    func pause()', '    var nagramiXIsSystemPiPActive:', '    func setNagramiXBackgroundPlayback('])
    binding=block(node,'        self.nagramiXSystemPiP.actualMediaChanged = ')
    fields=content[content.index('    private var nagramiXPlaybackRequested'):content.index('    private var readyDisposable')].replace('private ','')
    methods='\n'.join(block(content,m) for m in ['    func play()', '    func pause()', '    func togglePlayPause()', '    func setNagramiXBackgroundPlayback(', '    private func nagramiXUpdateManagedPlayback()']).replace('private func','func')
    start=content.index('            switch status.status {');end=content.index('            self.nagramiXUpdateManagedPlayback()',start)
    status='func status(_ status: MediaPlayerStatus) {\n'+content[start:end]+'self.nagramiXUpdateManagedPlayback()\n}'
    paused=block(content,'        self.playerNode.nagramiXActualPlaybackPaused = ')
    observers='\n'.join(block(content,'        self.'+name+' = NotificationCenter.default.addObserver(') for name in ['nagramiXInactiveObserver','nagramiXBackgroundObserver','nagramiXForegroundObserver'])
    return models,bridge,player,binding,fields,methods,status,paused,observers


def fixture(source,apple=False):
    models,bridge,player,binding,fields,methods,status,paused,observers=parts(source)
    boundary=WEB_BOUNDARY.split('enum NoError{}',1)[0]
    boundary=boundary.replace('enum Time {case atDocumentEnd}', 'enum Time {case atDocumentEnd,atDocumentStart}')
    boundary=boundary.replace('static let willEnterForegroundNotification=', 'static let didBecomeActiveNotification=Notification.Name("fixture-active")\n static let willResignActiveNotification=Notification.Name("fixture-inactive")\n static let willEnterForegroundNotification=')
    boundary=boundary.replace('var value:T','var onSet:((T)->Void)?\n var value:T').replace('self.value=value}\n}', 'self.value=value;onSet?(value)}\n}',1)
    audio=AUDIO_BOUNDARY.split('enum NoError:',1)[1].split('final class Player {',1)[0]
    audio='enum NoError:'+audio+'enum NagramiXTabSettings {static var backgroundVideoPlaybackEnabled=true}\n'
    if apple:
        boundary='import Foundation\nimport UIKit\n@preconcurrency import WebKit\nfinal class ValuePromise<T> {var onSet:((T)->Void)?;var value:T;init(_ value:T,ignoreRepeated:Bool){self.value=value};func set(_ value:T){self.value=value;onSet?(value)}}\n'
    return boundary+audio+models+'\n'+bridge+'''
class EmbedImplementation {var plays=0,pauses=0;func play(){plays+=1};func pause(){pauses+=1}}
final class YoutubeEmbedImplementation:EmbedImplementation {}
final class Player {
 let impl:EmbedImplementation
 let statusValue=ValuePromise<MediaPlayerStatus>(sample(.paused),ignoreRepeated:true)
 let nagramiXSystemPiP:NagramiXWebSystemPictureInPicture
 let controller=WKUserContentController(),view=WKWebView()
 init(youtube:Bool=true,pip:Bool=false,bg:Bool=true){
  impl=youtube ? YoutubeEmbedImplementation():EmbedImplementation()
  nagramiXSystemPiP=NagramiXWebSystemPictureInPicture(controller:controller,isYouTube:youtube,pipEnabled:pip,backgroundEnabled:bg)
  nagramiXSystemPiP.webView=view
'''+binding+'''
 }
'''+player+'''
}
final class WebPolicy {
 let playerNode:Player
 let audioSessionManager=Manager(),audioSessionDisposable=MetaDisposable()
'''+fields+'''
 init(youtube:Bool=true){playerNode=Player(youtube:youtube)
'''+paused+'\n'+observers+'''
  playerNode.statusValue.onSet={ [weak self] value in self?.status(value) }
 }
 deinit {
  for observer in [nagramiXInactiveObserver,nagramiXBackgroundObserver,nagramiXForegroundObserver] {if let observer{NotificationCenter.default.removeObserver(observer)}}
 }
'''+methods+'\n'+status+'''
}
func sample(_ state:MediaPlayerPlaybackStatus)->MediaPlayerStatus {MediaPlayerStatus(generationTimestamp:23,duration:137,dimensions:CGSize(width:640,height:360),timestamp:37,baseRate:1.25,seekId:7,status:state,soundEnabled:true)}
'''+('' if apple else (__import__('pathlib').Path(__file__).parent/'tests/NagramiXYoutubeBackgroundTests.swift').read_text())

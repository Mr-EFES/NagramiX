"""Execute the actual archive action, native identities/models and SignalKit operators."""
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
ACTION='submodules/AccountContext/Sources/NagramiXArchivedPlaybackAction.swift'
ROUND='submodules/TelegramUI/Components/Chat/ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'
SHARED='submodules/TelegramUI/Sources/SharedMediaPlayer.swift'
ACCOUNT='submodules/AccountContext/Sources/'
SK='submodules/SSignalKit/SwiftSignalKit/Source/'


def fixture(source):
    parts=[(ROOT/'scripts/tests/NagramiXArchivedRoundControlsBoundary.swift').read_text()]
    for name in ['Atomic','Disposable','Subscriber']:
        parts.append((source/(SK+name+'.swift')).read_text())
    signal=(source/(SK+'Signal.swift')).read_text()
    parts.append(signal[:signal.index('@available(iOS 13.0')])
    for name,markers in [
        ('Signal_Take',['public func take<T, E>(_ count:']),
        ('Signal_Mapping',['public func filter<T, E>(']),
        ('Signal_Timing',['public func timeout<T, E>(']),
        ('Signal_Dispatch',['public func deliverOn<T, E>(_ queue:', 'public func deliverOnMainQueue<'])
    ]:
        text=(source/(SK+name+'.swift')).read_text()
        parts.extend(block(text,marker) for marker in markers)
    shared=(source/(ACCOUNT+'SharedMediaPlayer.swift')).read_text()
    markers=['public enum SharedMediaPlaybackDataType','public enum SharedMediaPlaybackDataSource:',
             'public struct SharedMediaPlaybackData:', 'public protocol SharedMediaPlaylistItem {',
             'public func arePlaylistItemsEqual(', 'public protocol SharedMediaPlaylistId {',
             'public protocol SharedMediaPlaylistItemId {', 'public protocol InstantPagePlaylistIdProviding {',
             'public struct RichMessagePlaylistId:', 'public struct RichMessagePlaylistItemId:',
             'public struct PeerMessagesMediaPlaylistItemId:', 'public protocol SharedMediaPlaylistLocation {',
             'public enum SharedMediaPlayerPlaybackControlAction', 'public enum SharedMediaPlayerControlAction',
             'public final class SharedMediaPlayerItemPlaybackState:', 'public enum SharedMediaPlayerItemPlaybackStateOrLoading:']
    parts.extend(block(shared,m) for m in markers)
    manager=(source/(ACCOUNT+'MediaManager.swift')).read_text()
    parts.extend(block(manager,m) for m in ['public enum PeerMessagesMediaPlaylistId:', 'public enum MediaManagerPlayerType', 'public func peerMessagesMediaPlaylistAndItemId('])
    # The declarations are the native bridge, not a replacement for their UIKit implementations.
    action=(source/ACTION).read_text()
    # Only the monotonic clock input is adapted; the production extrapolation executes unchanged.
    action=action.replace('CACurrentMediaTime()', 'testMediaTime()')
    parts.append('\n'.join(line for line in action.splitlines() if not line.startswith('import ')))
    row=block((source/ROUND).read_text(),'    private func activateVideoPlayback(')
    row=row[:row.index('        if self.infoBackgroundNode.alpha.isZero {')]+'        self.nativeActivations += 1\n    }'
    parts.append('extension TestRoundRow {\n'+row+'\n}')
    player=(source/SHARED).read_text()
    completion=block(player,'    private func nagramiXInstallPlaybackCompletion(').replace('private func','func',1)
    policy=block(player,'    private var nagramiXIsArchivedRoundPlayer:').replace('private var','var',1)
    control=block(player,'    func control(_ action: SharedMediaPlayerControlAction)')
    start=control.index('            case let .seek(timestamp):\n')+len('            case let .seek(timestamp):\n')
    seek=control[start:control.index('            case let .setOrder',start)]
    parts.append('extension NativeReplayProbe {\n'+policy+'\n'+completion+'\nfunc userSeek(_ timestamp:Double){\n'+seek+'\n}\n}')
    parts.append((ROOT/'scripts/tests/NagramiXArchivedRoundControlsTests.swift').read_text())
    return '\n'.join(parts)


def negatives(text):
    cases=[
        ('loading-is-absent','case .voice = type, case .loading = state {\n                return false', 'case .voice = type, case .loading = state {\n                return true', 'loading never reopens'),
        ('reopen-current', 'manager.playlistControl(.playback(.togglePlayPause), type: .voice)', 'open()', 'pause keeps native player'),
        ('reopen-ended','manager.playlistControl(.seek(0.0), type: .voice)', 'open()', 'repeat keeps native player'),
        ('drop-item-identity','state.item.id.isEqual(to: itemId),', 'true,', 'other message opens selected copy'),
        ('drop-account','account.id == accountId,\n                  case .voice', 'account.id == account.id,\n                  case .voice', 'other account not controlled'),
        ('drop-resource-migration','if reference.media.resource.id == file.resource.id {', 'if reference.media.fileId == file.fileId {', 'migration retains playback position'),
        ('reset-migration','openAt(timestamp)', '_ = timestamp; openAt(0.0)', 'migration retains playback position'),
        ('ignore-stale','guard let self, self.generation == generation, isCurrent() else', 'guard let self, self.generation == generation else', 'stale row has no side effects'),
        ('old-end-stops-repeat','self.nagramiXPlaybackGeneration &+= 1','_ = self.nagramiXPlaybackGeneration','queued old completion cannot stop replay'),
        ('missing-rearm','self.currentPlayedToEnd = false\n                        self.nagramiXInstallPlaybackCompletion()', 'self.currentPlayedToEnd = false', 'new replay completion works'),
        ('keep-ended-flag','self.currentPlayedToEnd = false\n                        self.nagramiXInstallPlaybackCompletion()', '_ = self.currentPlayedToEnd\n                        self.nagramiXInstallPlaybackCompletion()', 'second replay completion works'),
    ]
    for name,old,new,diagnostic in cases:
        # toggle and stale guard also occur in the unchanged voice action.
        count=text.count(old)
        assert count in (1,2),(name,count)
        yield name,text.replace(old,new),diagnostic

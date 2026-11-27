"""Execute recording completion and touch callbacks with native SwiftSignalKit."""
from pathlib import Path

from original_video_mode_runtime import signal_library
from validate_quick_format import block

BASE = 'submodules/TelegramUI/'
SCREEN = BASE + 'Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift'
PANEL = BASE + 'Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift'
CHAT = BASE + 'Sources/Chat/ChatControllerMediaRecording.swift'
TESTS = Path(__file__).with_name('tests')
SK = 'submodules/SSignalKit/SwiftSignalKit/Source/'


def fixture(source, group='all', callers=None):
    callers = callers or {name: (source / name).read_text() for name in (SCREEN, PANEL, CHAT)}
    screen, panel, chat = (callers[name] for name in (SCREEN, PANEL, CHAT))
    code = 'import Foundation\n' + signal_library(source)
    for name, marker in [('Bag.swift', None), ('Promise.swift', 'public final class Promise<T> {'),
                         ('Signal_Mapping.swift', 'public func filter<T, E>('),
                         ('Signal_Combine.swift', 'public func combineLatest<T1, T2, E>(queue: Queue? = nil, _ s1: Signal<T1, E>, _ s2: Signal<T2, E>)')]:
        value = (source / SK / name).read_text()
        code += '\n' + (value if marker is None else block(value, marker))
    code += '\n' + (TESTS / 'NagramiXRoundRecordingCompletionBoundary.swift').read_text()
    replacements = {
        'RECORDING_STATE': block(screen, '    enum Recording: Equatable {'),
        'RESULTS': block(screen, '    private var currentResults:'),
        'WAITING': block(screen, '    private var waitingForNextResult ='),
        'RECORDED_DATA': block(screen, '    public struct RecordedVideoData {'),
        'TAKEN_DATA': block(screen, '    public func takenRecordedData()'),
        'STOP': block(screen, '    public func stopVideoRecording() -> Bool {'),
        'END_RECORDING': block(panel, '        self.mediaActionButtons.micButton.endRecording = {'),
        'VIDEO_DISMISS': block(block(chat, '    func dismissMediaRecorder('),
                              '        } else if let videoRecorderValue = self.videoRecorderValue {').split('{', 1)[1][:-1],
    }
    send = block(screen, '    public func sendVideoRecording(')
    # The production export/enqueue body starts at videoPaths. Capture the result
    # at that boundary while keeping the entry, native signal and subscription.
    prefix = send.split('            var videoPaths: [String] = []', 1)[0]
    replacements['SEND'] = prefix + '''
            self.sentPaths.append(video.videoPath)
            self.sentOptions.append((silentPosting, scheduleTime, repeatPeriod))
        })
    }
'''
    for token, value in replacements.items():
        marker = '// PRODUCTION_' + token + '\n'
        assert code.count(marker) == 1, token
        code = code.replace(marker, value + '\n')
    tests = (TESTS / 'NagramiXRoundRecordingCompletionTests.swift').read_text()
    return code + '\n' + tests.replace('__TEST_GROUP__', group)

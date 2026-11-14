"""Execute the complete original exporter with real files/SignalKit and media flags.

Photos callbacks, UIKit thumbnail encoding and Telegram MediaBox are explicit
adapters. The exporter, stream parser, settings and native video classification
come verbatim from guarded source. Source movie bytes are genuine synthetic
H.264/AAC samples, never user media.
"""
from pathlib import Path
import base64
import hashlib
import json
from validate_quick_format import block
from original_video_mode_runtime import signal_library

ROOT = Path(__file__).resolve().parents[1]
MEDIA = 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift'
LEGACY = 'submodules/LegacyMediaPickerUI/Sources/LegacyMediaPickers.swift'
FILE = 'submodules/TelegramCore/Sources/SyncCore/SyncCore_TelegramMediaFile.swift'
UPLOAD = 'submodules/TelegramCore/Sources/PendingMessages/PendingMessageUploadedContent.swift'
FIXTURES = ROOT / 'scripts/tests/fixtures/original-video-media'


def parts(source):
    movie_files = json.loads((FIXTURES / 'manifest.json').read_text())['files']
    data = {}
    for name, sha in movie_files.items():
        value = (FIXTURES / name).read_bytes()
        assert hashlib.sha256(value).hexdigest() == sha, name
        data[name] = base64.b64encode(value).decode()
    legacy = (source / LEGACY).read_text()
    native = (source / FILE).read_text()
    upload = block((source / UPLOAD).read_text(), '                        if !file.isVideo && file.mimeType.hasPrefix("video/") {')
    core = signal_library(source) + '\n' + (source / MEDIA).read_text()
    core += '\n' + block(native, 'public struct TelegramMediaVideoFlags: OptionSet {')
    boundary = (ROOT / 'scripts/tests/NagramiXOriginalVideoMediaBoundary.swift').read_text()
    methods = '\n'.join(block(native, marker) for marker in ['    public var isVideo: Bool {', '    public var isInstantVideo: Bool {'])
    boundary = boundary.replace('// NATIVE_FILE_CLASSIFICATION', methods)
    actual = '\nprivate let nagramiXOriginalVideoQueue = Queue(name: "OriginalVideoMediaFixture")\n'
    actual += '\n' + block(legacy, 'private func nagramiXOriginalVideoSupportsStreaming(')
    actual += '\n' + block(legacy, 'public func nagramiXOriginalVideoFile(')
    actual += '\nfunc nativeUploadFlags(_ file: TelegramMediaFile) -> Int32 {\nvar flags: Int32 = 0\n' + upload + '\nreturn flags\n}\n'
    tests = (ROOT / 'scripts/tests/NagramiXOriginalVideoMediaTests.swift').read_text()
    tests = tests.replace('SYNTHETIC_MP4_BASE64', data['video.mp4']).replace('SYNTHETIC_MOV_BASE64', data['video.mov'])
    return core, boundary, actual, tests


def fixture(source):
    return '\n'.join(parts(source))


def routing_fixture(source):
    # Upgrade the previous routing regression to read/write the real persisted
    # settings, rather than a stand-in current.originalVideos variable. Photos
    # and converter I/O remain explicit edges; the other fixture executes the
    # complete original exporter and real files independently.
    from original_video_mode_runtime import fixture as original_fixture
    code = original_fixture(source)
    marker = 'struct NagramiXMediaSettings {'
    code = code.replace(block(code, marker), (source / MEDIA).read_text(), 1)
    for value in ['enabled', 'true', 'false']:
        old = 'NagramiXMediaSettings.current.originalVideos=' + value
        assert code.count(old) == 1
        code = code.replace(old, 'setOriginalVideoMode(' + value + ')', 1)
    helper = '''
func setOriginalVideoMode(_ enabled: Bool) {
    var settings = NagramiXMediaSettings.current
    settings.originalVideos = enabled
    NagramiXMediaSettings.update(settings)
}
'''
    code = code.replace('var checks=0', helper + '\nvar checks=0', 1)
    start = ''' static func main(){
  let defaults = UserDefaults.standard
  let saved = defaults.dictionaryRepresentation().filter { $0.key.hasPrefix("nagramix.") }
  defer {
   for key in defaults.dictionaryRepresentation().keys where key.hasPrefix("nagramix.") { defaults.removeObject(forKey: key) }
   for (key,value) in saved { defaults.set(value, forKey: key) }
   _ = defaults.synchronize()
  }
  defaults.removeObject(forKey: "nagramix.videos.original")
  expect(!NagramiXMediaSettings.current.originalVideos, "real persisted cold default is OFF before Gallery send")
'''
    assert code.count(' static func main(){\n') == 1
    return code.replace(' static func main(){\n', start, 1)

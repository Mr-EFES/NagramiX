#!/usr/bin/env python3
"""Exercise manual transcription for archived rows, including their final menu and both controls."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_retained_voice_transcription import fixture
from validate_upstream_13_2_release import checked_plan, digest


STAGE = 'archived_transcription_actions'


def check(source, swiftc, work):
    plan = checked_plan(STAGE)
    files = {}
    for name, sha in plan['outputs'].items():
        path = source / name
        assert digest(path) == sha, name
        subprocess.run([swiftc, '-frontend', '-parse', path], check=True)
        files[path.stem] = path.read_text()
    menu = files['ChatInterfaceStateContextMenus']
    rebuilt = block(menu, '        if archivedAttribute != nil && !nagramiXTemporaryActions {')
    assert rebuilt.index('actions.removeAll()') < rebuilt.index('actions.append(transcriptionAction)')
    assert rebuilt.count('actions.append(transcriptionAction)') == 1
    assert menu.count('actions.append(transcriptionAction)') == 2
    assert 'NagramiXTranscriptionRuntime.toggleContext(context: context, messageId: message.id)' in menu
    assert 'object(forKey: "nagramix.context.transcribe") as? Bool ?? true' in menu
    for name in ['ChatMessageInteractiveFileNode', 'ChatMessageInteractiveInstantVideoNode']:
        node = files[name]
        assert 'NagramiXTranscriptionRuntime.showsRetainedTranscriptionButton(' in node
        assert 'case .locked = audioTranscriptionState' in node
        tap = block(node, '    private func transcribe()')
        assert tap.index('if fileOnly && !NagramiXTranscriptionRuntime.handles(') < tap.index('messages.transcribeAudio(')
        assert 'NagramiXTranscriptionRuntime.transcribe(' in tap
    voice = files['ChatMessageInteractiveFileNode']
    hit = block(voice, '    override public func hitTest(')
    assert hit.index('audioTranscriptionButton.hitTest') < hit.index('dateAndStatusNode.hitTest')
    circle = files['ChatMessageInteractiveInstantVideoNode']
    assert 'button.hitTest' in block(circle, '        recognizer.tapActionAtPoint = ')
    assert 'return hit' in block(circle, '    override public func hitTest(')
    assert 'self.isUserInteractionEnabled = false' not in circle
    # Compile the exact row layout expressions, including the no-transcript narrow-row case.
    width = next(line.strip() for line in voice.splitlines() if 'let controlWidth = retainedAudio' in line)
    frame = next(line.strip() for line in voice.splitlines() if 'let audioTranscriptionButtonFrame = CGRect(' in line)
    geometry = '''import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
func button(_ retainedAudio: Bool, _ boundingWidth: CGFloat, _ fittedLayoutSize: CGSize) -> CGRect {
    let audioTranscriptionButtonSize = CGSize(width: 30, height: 30)
''' + width + '\n' + frame + '''
    return audioTranscriptionButtonFrame
}
@main enum Check { static func main() {
    for width: CGFloat in [110, 160, 240] {
        let row = CGSize(width: width, height: 38)
        for parent in [width, width + 110] {
            precondition(CGRect(origin: .zero, size: row).contains(button(true, parent, row)))
        }
    }
    precondition(button(false, 160, CGSize(width: 120, height: 38)).origin == CGPoint(x: 133, y: -6))
} }
'''
    execute(swiftc, work, 'ArchivedButtonGeometry', geometry)
    swift = fixture(source)
    # The current archive also distinguishes retained rows hidden after a local deletion.
    swift = swift.replace('struct ArchiveRecord {', 'struct ArchiveRecord { var hiddenFromChat = false;')
    start = '                    fixtureInputPath = ""'
    assert swift.count(start) == 1
    swift = swift.replace(start, '''                    guard let row = archive.transcriptionMessage(id: m.id, liveMessage: nil) else { fatalError("missing archived audio") }
                    expectFile(!NagramiXTranscriptionRuntime.hasReadyTranscript(row), "no prior transcript")
                    expectFile(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(row, context: c, expanded: true), "reused cell can start its first transcript")
                    expectFile(NagramiXTranscriptionRuntime.showsRetainedTranscriptionButton(row, isPreview: false), "first use shows A")
                    expectFile(!NagramiXTranscriptionRuntime.showsRetainedTranscriptionButton(row, isPreview: true), "preview is inert")
                    expectFile(NagramiXTranscriptionRuntime.handlesContext(row, context: c), "menu before first transcript")
''' + start)
    change = '                    keepDeleted(false)'
    assert swift.count(change) == 1
    swift = swift.replace(change, '''                    expectFile(NagramiXTranscriptionRuntime.hasTemporaryTranscript(displayed, context: c), "matching dictionary opens the saved result")
                    configure(.apple)
                    expectFile(NagramiXTranscriptionRuntime.hasTemporaryTranscript(displayed, context: c, expanded: true), "an open cached text can be collapsed")
                    expectFile(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(displayed, context: c), "new provider can transcribe again")
                    if ttl == nil && menu {
                        AudioBoundary.started = DispatchSemaphore(value: 0)
                        let changed = run(c, displayed, true) {
                            wait(AudioBoundary.started, "menu started the new provider")
                            expectFile(AudioBoundary.provider == .apple, "selected Apple after Telegram")
                            AudioBoundary.finish(.success("updated text"))
                        }
                        expectFile(changed == .success("updated text") && c.account.network.file.calls == 1, "refresh uses saved audio")
                        let refreshed = archive.transcriptionMessage(id: m.id, liveMessage: nil)!
                        expectFile(NagramiXTranscriptionRuntime.cached(refreshed, context: c) == "updated text", "new result saved")
                        NagramiXTranscriptionSettings.update { $0.language = "ru-RU" }
                        expectFile(!NagramiXTranscriptionRuntime.hasTemporaryTranscript(refreshed, context: c), "changed language invalidates old text for recognition")
                    }
                    NagramiXTranscriptionSettings.update { $0.enabled = false }
                    expectFile(!NagramiXTranscriptionRuntime.showsRetainedTranscriptionButton(row, isPreview: false), "explicit off prevents new requests")
                    expectFile(NagramiXTranscriptionRuntime.showsRetainedTranscriptionButton(displayed, isPreview: false), "explicit off allows reading existing text")
                    configure()
''' + change)
    for report in execute(swiftc, work, 'ArchivedTranscriptionActions', swift):
        print(report['mode'], report['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-archived-actions-') as tmp:
        work = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = work / 'source'
            canonical_projection(source, STAGE)
        check(source, args.swiftc, work)

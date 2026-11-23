#!/usr/bin/env python3
"""Check the retained audio file route and durable archive write with the production ASR coordinator."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from private_temporary_transcription_runtime import A, P, clean
from transcription_compatibility_runtime import fixture as premium_fixture
from validate_quick_format import block
from validate_private_temporary_transcription import execute
from validate_upstream_13_2_release import checked_plan, digest

STAGE = 'retained_voice_transcription'
TESTS = Path(__file__).with_name('tests')


def fixture(source):
    code = premium_fixture(source)
    code = code.replace('URL(fileURLWithPath:"/tmp/nagramix-asr-boundary-audio.m4a")', 'retainedAudioTestURL')
    code += '\nlet retainedAudioTestURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)\n'
    archive = (source / A).read_text()
    predicate = clean(block((source / P).read_text(), 'public func nagramiXTranscriptionUsesFile('))
    code += '\n' + predicate.replace('UserDefaults.standard', 'fileTestDefaults')
    # Supply real local paths independently of the mocked MediaBox cache.
    code = code.replace('struct Resource{let id:ResourceId}', '''
class Resource { let id:ResourceId; init(id:ResourceId){self.id=id} }
final class LocalFileReferenceMediaResource: Resource {
 let localFilePath:String; let size:Int64?
 init(_ path:String, size:Int64) { self.localFilePath=path; self.size=size; super.init(id:ResourceId(stringRepresentation:"archive:"+path)) }
}''')
    code = code.replace('final class TelegramMediaFile{let resource:Resource;', 'final class TelegramMediaFile{var resource:Resource;')
    code = code.replace('preparations+=1;completion', 'fixtureInputPath=path;preparations+=1;completion')
    code += '\nvar fixtureInputPath = ""\n'
    old = block(code, ' func transcriptionMessage(id:MessageId,liveMessage:Message?)')
    code = code.replace(old, clean(block(archive, '    public func transcriptionMessage(')))
    code = code.replace('func renderDeletedRecord(_ record:ArchiveRecord,requireCompleteMedia:Bool)', 'func renderDeletedRecord(_ record:ArchiveRecord,requireCompleteMedia:Bool,forTranscription:Bool=false)')
    code = code.replace('struct ArchiveRecord {', 'struct ArchiveRecord { var mediaExpiredAt:Int32?; var viewOnceReplay:Bool?; var sourceWasTemporary:Bool?; ' + block(archive, '    var wasTemporary: Bool') + '\n')
    code = code.replace('let original=record.message', '''guard (record.temporary == true && nagramiXTemporaryMessagesEnabled()) || NagramiXMessageArchiveSettings.current.showDeletedMessages else {return nil}
  let original=record.message''')
    # The stamp, archive lookup/save, providers, file-upload builder and native
    # message-ID gates above come from the overlaid sources.
    tests = (TESTS / 'NagramiXRetainedVoiceTranscription.swift').read_text()
    code += '\n' + tests
    return code.replace('  print("PASS Premium file transcription checks:', '  self.verifyRetainedAudio()\n  print("PASS Premium file transcription checks:')


def check(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for path, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / path) == expected, path
    for path in plan['outputs']:
        subprocess.run([swiftc, '-frontend', '-parse', source / path], check=True)
    for name in ('ChatMessageInteractiveFileNode.swift', 'ChatMessageInteractiveInstantVideoNode.swift'):
        path = next(path for path in plan['outputs'] if path.endswith('/' + name))
        node = (source / path).read_text()
        tap = block(node, '    private func transcribe()')
        assert 'if fileOnly && !NagramiXTranscriptionRuntime.handles(' in tap
        assert tap.index('NagramiXTranscriptionRuntime.transcribe(') < tap.index('messages.transcribeAudio(')
        assert 'nagramiXTranscriptionUsesFile(' in node
    for result in execute(swiftc, folder, 'RetainedVoiceTranscription', fixture(source)):
        print(result['mode'], result['output'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source', type=Path)
    group.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', default='swiftc')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = folder / 'source'
            canonical_projection(source, STAGE)
        check(source, args.swiftc, folder)


if __name__ == '__main__':
    main()

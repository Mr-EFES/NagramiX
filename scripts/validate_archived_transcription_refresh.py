#!/usr/bin/env python3
"""Exercise the archived inline read, explicit refresh, persistence and stale UI callbacks."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from private_temporary_transcription_runtime import A, clean
from validate_private_temporary_transcription import execute
from validate_quick_format import block
from validate_retained_voice_transcription import fixture
from validate_upstream_13_2_release import checked_plan, digest


STAGE = 'archived_transcription_refresh'


def check(source, swiftc, work):
    plan = checked_plan(STAGE)
    files = {}
    for name, expected in plan['outputs'].items():
        file = source / name
        assert digest(file) == expected, name
        files[file.stem] = file.read_text()
        subprocess.run([swiftc, '-frontend', '-parse', file], check=True)
    menu = files['ChatInterfaceStateContextMenus']
    refresh = block(menu, '            if archivedAudio || cancel == nil {')
    assert 'strings.nagramiXUILocalized("Расшифровать")' in refresh
    assert 'NagramiXTranscriptionRuntime.startContext(context: context, messageId: message.id)' in refresh
    assert 'toggleContext(' not in menu
    assert 'actions.append(contentsOf: transcriptionActions)' in block(menu, '        if archivedAttribute != nil && !nagramiXTemporaryActions {')
    for name in [*plan['outputs'], *plan['guards']]:
        if Path(name).stem in ('ChatMessageInteractiveFileNode', 'ChatMessageInteractiveInstantVideoNode'):
            tap = block((source / name).read_text(), '    private func transcribe()')
            saved = tap.index('if NagramiXTranscriptionRuntime.hasTemporaryTranscript(')
            assert saved < tap.index('return', saved) < tap.index('NagramiXTranscriptionRuntime.transcribe(')

    code = fixture(source)
    code = code.replace('struct ArchiveRecord {', 'struct ArchiveRecord { var hiddenFromChat = false;')
    old = 'func retainTelegramTranscription(id:MessageId,attribute:AudioTranscriptionMessageAttribute){}'
    assert code.count(old) == 1
    code = code.replace(old, clean(block((source / A).read_text(), '    func retainTelegramTranscription(')))
    # Use the same public entry point as the selected menu item.
    old = 'if menu {NagramiXTranscriptionRuntime.toggleContext(context:c,messageId:m.id)'
    assert code.count(old) == 1
    code = code.replace(old, old.replace('toggleContext', 'startContext'))
    anchor = '                    keepDeleted(false)'
    assert code.count(anchor) == 1
    code = code.replace(anchor, '                    if ttl == nil && menu { verifyArchiveRefresh(c, m, archive) }\n' + anchor)
    # Compile the actual UI text selector and Telegram message reader against the host boundary.
    common = (source / 'submodules/TelegramUI/Components/Chat/ChatMessageItemCommon/Sources/ChatMessageItemCommon.swift').read_text()
    code += '\nextension EngineMessage { var attributes: [MessageAttribute] { raw.attributes } }\n'
    code += clean(block(common, 'public enum TranscribedText:')) + '\n'
    code += clean(block(common, 'public func transcribedText(message:')) + '\n'
    code += block(files['ChatMessageInteractiveFileNode'], 'private func nagramiXDisplayedTranscription(') + '\n'
    code += (Path(__file__).with_name('tests') / 'NagramiXArchivedTranscriptionRefresh.swift').read_text()
    for result in execute(swiftc, work, 'ArchivedTranscriptionRefresh', code):
        print(result['mode'], result['output'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-archived-refresh-') as tmp:
        work = Path(tmp)
        source = args.source
        if args.canonical:
            from validate_release_095_apple_preflight import canonical_projection
            source = work / 'source'
            canonical_projection(source, STAGE)
        check(source, args.swiftc, work)

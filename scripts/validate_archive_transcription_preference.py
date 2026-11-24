#!/usr/bin/env python3
"""Compile the archive and transcription preference reads in separate Swift source files."""
import argparse
from pathlib import Path
import subprocess
import tempfile

from validate_quick_format import block
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest


def check(source, swiftc, folder):
    plan = checked_plan('archive_transcription_preference')
    policy, = plan['outputs']
    archive, = plan['guards']

    def read(path, table):
        file = source / path if source else OVERLAY / plan[table][path]
        expected = plan['outputs'] if table == 'replacements' else plan['guards']
        assert digest(file) == expected[path], path
        return file.read_text()

    settings = block(read(archive, 'guard_sources'), 'private struct NagramiXMessageArchiveSettings')
    archive_file = folder / 'Archive.swift'
    archive_file.write_text('import Foundation\n' + settings.replace('UserDefaults.standard', 'testDefaults') + '''
func archiveShowsDeleted() -> Bool { NagramiXMessageArchiveSettings.current.showDeletedMessages }
''')
    policy_file = folder / 'Transcription.swift'

    def write_read(code):
        predicate = block(code, 'public func nagramiXTranscriptionUsesFile(')
        getter, = [line for line in predicate.splitlines() if line.strip().startswith('let showDeleted = ')]
        policy_file.write_text('import Foundation\nfunc transcriptionShowsDeleted() -> Bool {\n'
                               + getter.replace('UserDefaults.standard', 'testDefaults') + '\nreturn showDeleted\n}\n')

    main = folder / 'main.swift'
    main.write_text('''import Foundation
let suite = UUID().uuidString
let testDefaults = UserDefaults(suiteName: suite)!
defer { testDefaults.removePersistentDomain(forName: suite) }
let key = "nagramix.messages.showDeletedMessages"
for value: Bool? in [nil, true, false, true, nil] {
    if let value { testDefaults.set(value, forKey: key) } else { testDefaults.removeObject(forKey: key) }
    precondition(archiveShowsDeleted() == (value ?? false))
    precondition(transcriptionShowsDeleted() == archiveShowsDeleted())
}
''')
    compile_args = [swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path',
                    folder / 'cache', archive_file, policy_file, main]
    write_read((OVERLAY / plan['previous'][policy]).read_text())
    old = subprocess.run([*compile_args, '-typecheck'], text=True, capture_output=True)
    assert old.returncode and 'NagramiXMessageArchiveSettings' in old.stderr and (
        'inaccessible' in old.stderr or 'cannot find' in old.stderr), old.stderr
    write_read(read(policy, 'replacements'))
    executable = folder / 'check'
    subprocess.run([*compile_args, '-O', '-o', executable], check=True)
    subprocess.run([executable], check=True)
    print('PASS: original cross-file reference rejected; archive and transcription agree on absent, on and off')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-archive-preference-') as directory:
        check(args.source, args.swiftc, Path(directory))

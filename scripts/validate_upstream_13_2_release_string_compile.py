#!/usr/bin/env python3
"""Compile real custom string extensions with the actual ACK handler/caller.

Only the native PresentationStrings component storage and UI/transport are
boundaries. Every custom string member and its getter body comes from source.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from validate_custom_member_references import STRINGS, RESOLVER, audit, canonical_texts
from validate_localization_standard import strings
from validate_upstream_13_2_release import OVERLAY, checked_plan, digest, guard_checks
from validate_upstream_13_2_release_ack_compile import COPY, FORWARD, fixture

STAGE = 'upstream_13_2_release_string_compile'
BAD = 'nagramiXArchiveCopyUnavailable'
GOOD = 'nagramiXArchivedCopyUnavailable'
KEY = 'NagramiX.Archive.CopyUnavailable'


def real_extensions(source):
    # The only replacement removes an unavailable Linux module import. All
    # custom properties/functions and localization resolver bodies are real.
    text = '\n'.join((source / name).read_text().replace('import TelegramPresentationData\n', '') for name in (STRINGS, RESOLVER))
    return r'''
import Foundation
public struct PresentationStringsComponent {
    public let dict: [String: String]
    public let languageCode: String
}
public final class PresentationStrings {
    public let primaryComponent: PresentationStringsComponent
    public let secondaryComponent: PresentationStringsComponent? = nil
    public let Common_OK = "OK"
    public init(language: String = "en", dictionary: [String: String] = ["NagramiX.Archive.CopyUnavailable": "unavailable"]) {
        self.primaryComponent = PresentationStringsComponent(dict: dictionary, languageCode: language)
    }
}
typealias Strings = PresentationStrings
''' + text


def retry_expression(forward):
    at = forward.index('if !cancelled, let self {')
    expression = re.search(r'text: (strings\.nagramiX\w+), actions:', forward[at:])
    assert expression
    return 'func retryText(_ strings: PresentationStrings) -> String { return ' + expression.group(1) + ' }\n'


def actual_handler(source, copy, forward):
    current = fixture(copy, forward)
    old_boundary = 'struct Strings { let nagramiXArchiveCopyUnavailable = "unavailable"; let Common_OK = "OK" }'
    assert current.count(old_boundary) == 1
    current = current.replace(old_boundary, '')
    return real_extensions(source) + '\n' + retry_expression(forward) + current


def getter_probe(source):
    resources = source / 'submodules/NagramiXCore/Resources'
    english = strings(resources / 'en.lproj/Localizable.strings')
    declaration = (source / STRINGS).read_text()
    getters = re.findall(r'^    var (nagramiX\w+): String', declaration, re.M)
    assert len(getters) >= 220
    literal = lambda value: json.dumps(value, ensure_ascii=False)
    code = real_extensions(source) + '\n'
    code += 'let keys: [String] = ' + literal(sorted(english)) + '\n'
    code += 'let values = Dictionary(uniqueKeysWithValues: keys.map { ($0, $0) })\nlet actual = PresentationStrings(dictionary: values)\n'
    code += '\n'.join('precondition(!actual.' + name + '.isEmpty)' for name in getters) + '\n'
    calls = []
    for signature in re.finditer(r'    func (nagramiX\w+)\(([^\n]*)\) -> String', declaration):
        name, parameters = signature.groups()
        args = []
        for field in parameters.split(','):
            label, kind = field.strip().split(':', 1)
            label = label.split()[0]
            value = '1' if kind.strip() == 'Int' else literal(KEY if name == 'nagramiXLocalized' else 'probe')
            args.append(('' if label == '_' else label + ': ') + value)
        calls.append('_ = actual.' + name + '(' + ', '.join(args) + ')')
    code += '\n'.join(calls) + '\n'
    locales = []
    for path in sorted(resources.glob('*.lproj/Localizable.strings')):
        code_name = path.parent.name.removesuffix('.lproj')
        value = strings(path)[KEY]
        locales.append((code_name, value))
        code += 'precondition(PresentationStrings(language: ' + literal(code_name) + ', dictionary: [' + literal(KEY) + ': ' + literal(value) + ']).' + GOOD + ' == ' + literal(value) + ')\n'
    assert len(locales) == 71
    code += 'print("PASS: real PresentationStrings extensions; ' + str(len(getters)) + ' properties, ' + str(len(calls)) + ' functions and 71 translated archive errors")\n'
    return code, len(getters), len(calls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(args.source / name) == expected, name
    before = {name: (OVERLAY / template).read_text() for name, template in plan['previous'].items()}
    after = {name: (args.source / name).read_text() for name in plan['outputs']}
    for name in before:
        assert before[name].count(BAD) == 1
        assert before[name].replace(BAD, GOOD) == after[name]
    texts = {str(path.relative_to(args.source)): path.read_text() for path in args.source.rglob('*.swift') if not path.is_symlink()}
    coverage = audit(texts, full=True)
    early = canonical_texts(); audit(early)
    broken = dict(early); broken.update(before)
    try:
        audit(broken)
    except ValueError as error:
        assert BAD in str(error) and COPY in str(error) and FORWARD in str(error)
    else:
        raise AssertionError('SDK184 missing-member regression passed early audit')
    getters, property_count, function_count = getter_probe(args.source)
    handler = actual_handler(args.source, after[COPY], after[FORWARD])
    old_handler = actual_handler(args.source, before[COPY], before[FORWARD])
    old_retry = real_extensions(args.source) + retry_expression(before[FORWARD])
    with tempfile.TemporaryDirectory(prefix='nagramix-real-strings-') as temporary:
        folder = Path(temporary)
        guard_folder = folder / 'guards'; guard_folder.mkdir()
        rejected = guard_checks(args.source, STAGE, plan, guard_folder)
        file = folder / 'Probe.swift'; binary = folder / 'probe'
        for flags in ([], ['-O']):
            common = [str(args.swiftc), '-module-cache-path', str(folder / 'cache'), *flags]
            for production in (getters, handler):
                file.write_text(production)
                subprocess.run([*common, '-warnings-as-errors', str(file), '-o', str(binary)], check=True)
                subprocess.run([str(binary)], check=True)
            for broken_scope in (old_handler, old_retry):
                file.write_text(broken_scope)
                result = subprocess.run([*common, '-typecheck', str(file)], capture_output=True, text=True)
                assert result.returncode != 0 and "has no member '" + BAD + "'" in result.stderr, result.stderr
        for name in plan['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'replacements': 2, 'guards': 4, 'fail_closed': len(rejected), 'real_extension_runtime_executions': 4,
              'real_properties': property_count, 'real_functions': function_count, 'languages': 71,
              'old_missing_member_compiler_failures': 4, 'early_rejection_of_original_two_errors': 'passed',
              'source_reference_audit': coverage, 'apple_sdk': 'pending', 'device': 'pending'}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Проверить утверждённые названия моделей, проценты и одиночную галочку выбора."""
import argparse
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile

from validate_quick_format import block, manifest
from validate_app_language_localization import strings
from validate_localization_standard import UI_CATALOG, catalog_contract, source_contract

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'local_model_menu_patches.json').read_text())
PREFERENCES = next(iter(PLAN['inputs']))
MODELS = 'submodules/NagramiXTranscription/Sources/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def clean(text):
    return text.replace('private ', '').replace('public ', '')


def verify(source):
    for name, digest in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    before = (OVERLAY / PLAN['previous'][PREFERENCES]).read_text()
    after = (source / PREFERENCES).read_text()

    def collapse(text):
        start = text.index('    private func whisperModelTitle(')
        end = text.index('    private static let whisperLanguages', start)
        text = text[:start] + '// LOCAL MODEL PRESENTATION\n' + text[end:]
        targets = [
            ('    private func makeSections(', '        case .whisper:', '        case .voskLanguages:'),
            ('    public func tableView(_ tableView: UITableView, titleForFooterInSection', '        case .whisper', '        case .credential:'),
            ('    public func tableView(_ tableView: UITableView, cellForRowAt', '        case let .model(model):', '        case let .voskLanguage(code):'),
        ]
        for method, start_marker, end_marker in targets:
            body = block(text, method)
            start = body.index(start_marker)
            end = body.index(end_marker, start)
            text = text.replace(body, body[:start] + '// LOCAL MODEL ROWS\n' + body[end:])
        return text

    assert collapse(before) == collapse(after), 'Unrelated provider/download/selection/swipe/license code changed'
    assert 'model.title' not in block(after, '    private func whisperModelTitle(')
    assert 'shared.status(' not in block(after, '    private func makeSections(')
    footer = block(after, '    public func tableView(_ tableView: UITableView, titleForFooterInSection')
    assert 'case .whisper, .vosk: return nil' in footer
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_archive_deletion_visibility(') < pipeline.index('    apply_local_model_menu(')
    assert catalog_contract(source) == (71, 613)
    source_contract(source)


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('local_model_menu', OVERLAY / 'local_model_menu.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rejected = []

    def seed(label):
        tree = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name).read_bytes())
        return tree

    def reject(tree, label, overlay=OVERLAY):
        previous = manifest(tree)
        try:
            module.apply_local_model_menu(tree, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + label)
        assert manifest(tree) == previous, 'Partial mutation: ' + label
        rejected.append(label)

    valid = seed('valid')
    module.apply_local_model_menu(valid, OVERLAY)
    assert (valid / PREFERENCES).read_bytes() == (source / PREFERENCES).read_bytes()
    reject(valid, 'repeat')
    for i, name in enumerate({**PLAN['inputs'], **PLAN['guards']}):
        for kind in ['missing', 'drift']:
            tree = seed(str(i) + '-' + kind)
            if kind == 'missing':
                (tree / name).unlink()
            else:
                (tree / name).write_bytes(b'changed')
            reject(tree, kind + ' ' + name)
    variants = []
    for field in ['inputs', 'outputs', 'guards', 'templates']:
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        variants.append((field, bad))
    for field in ['previous', 'replacements']:
        bad = copy.deepcopy(PLAN)
        bad[field][PREFERENCES] = '../outside.swift'
        variants.append((field, bad))
    bad = copy.deepcopy(PLAN)
    bad['outputs'].clear()
    variants.append(('inconsistent', bad))
    for label, bad in variants:
        overlay = temp / ('overlay-' + label)
        for name in PLAN['templates']:
            path = overlay / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((OVERLAY / name).read_bytes())
        (overlay / 'local_model_menu_patches.json').write_text(json.dumps(bad))
        reject(seed('source-' + label), label, overlay)
    for i, name in enumerate([PREFERENCES, next(iter(PLAN['guards']))]):
        tree = seed('symlink-' + str(i))
        path = tree / name
        outside = temp / ('external-' + str(i))
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        reject(tree, 'external symlink ' + name)
    return rejected


def runtime_checks(source, swiftc, temp):
    preferences = (source / PREFERENCES).read_text()
    before = (OVERLAY / PLAN['previous'][PREFERENCES]).read_text()
    settings = (source / (MODELS + 'Settings.swift')).read_text()
    vosk = (source / (MODELS + 'VoskModels.swift')).read_text()
    memory = (source / (MODELS + 'LocalInferenceMemory.swift')).read_text()
    resolver = (source / (MODELS + 'VoskRecognizer.swift')).read_text()
    models = temp / 'Models.swift'
    models.write_text('import Foundation\n' + clean(block(settings, 'public enum NagramiXTranscriptionProvider:')) + '\n' + clean(block(settings, 'public enum NagramiXWhisperModel:')) + '\n' + block(vosk, 'struct NagramiXVoskModel:'))
    boundary = (ROOT / 'scripts/tests/NagramiXLocalModelMenuBoundary.swift').read_text()
    declarations = '\n'.join(clean(block(preferences, marker)) for marker in ['    private enum Page ', '    private struct Row ', '    private enum Action '])
    boundary = boundary.replace('// PRODUCTION_PAGE_ROW_ACTION', declarations)
    offerings = next(line for line in memory.splitlines() if 'static let whisperModels:' in line) + '\n'
    offerings += '\n'.join(block(memory, marker) for marker in ['    static func isMobileVosk(', '    static func voskModels(', '    static var voskLanguages:'])
    boundary = boundary.replace('// PRODUCTION_MODEL_OFFERINGS', offerings)
    boundary = boundary.replace('// PRODUCTION_VOSK_RESOLVER', block(resolver, '    static func model('))
    boundary = boundary.replace('// PRODUCTION_LANGUAGE_LABEL', clean(block(preferences, '    private func label(')))
    start = preferences.index('    private func whisperModelTitle(')
    end = preferences.index('    private static let whisperLanguages', start)
    helpers = clean(preferences[start:end])
    sections = block(preferences, '    private func makeSections(')
    sections = sections[sections.index('        case .whisper:'):sections.index('        case .voskLanguages:')]
    old_sections = block(before, '    private func makeSections(')
    old_sections = old_sections[old_sections.index('        case .whisper:'):old_sections.index('        case .voskLanguages:')]
    footer_marker = '    public func tableView(_ tableView: UITableView, titleForFooterInSection'
    footer = clean(block(preferences, footer_marker))
    accessories = block(preferences, '    public func tableView(_ tableView: UITableView, cellForRowAt')
    accessories = accessories[accessories.index('        case let .model(model):'):accessories.index('        case let .voskLanguage(code):')]
    old_title = clean(block(before, '    private func whisperModelTitle('))
    modes = {
        'current': (helpers, sections, footer, accessories),
        'technical-titles': (helpers.replace(block(helpers, '    func whisperModelTitle('), old_title), sections, footer, accessories),
        'technical-footer': (helpers, sections, clean(block(before, footer_marker)), accessories),
        'status-captions': (helpers, old_sections, footer, accessories),
        'wrapping': (helpers.replace('numberOfLines = 1', 'numberOfLines = 0'), sections, footer, accessories),
        'installed-percent': (helpers.replace('guard !installed, let progress', 'guard let progress'), sections, footer, accessories),
        'wrong-selection': (helpers, sections, footer, accessories.replace('value.whisper == model', 'true')),
    }
    catalog = []
    languages = json.loads((OVERLAY / 'app_language_localization/languages.json').read_text())['languages']
    for item in languages:
        code = item['code']
        real = strings(source / ('submodules/NagramiXCore/Resources/' + code + '.lproj/Localizable.strings'))
        values = dict(real)
        values.update({raw: real[metadata['key']] for raw, metadata in UI_CATALOG.items()})
        expected = [real[UI_CATALOG[key]['key']] for key in ['Базовая', 'Средняя', 'Максимальная']]
        expected.append(real['NagramiX.Transcription.Vosk.Alternative'])
        catalog.append({'code': code, 'values': values, 'expected': expected})
    fixture_data = temp / 'languages.json'
    fixture_data.write_text(json.dumps(catalog, ensure_ascii=False))
    tests = ROOT / 'scripts/tests/NagramiXLocalModelMenuTests.swift'
    runs = []
    for label, (helper_code, row_code, footer_code, accessory_code) in modes.items():
        fixture = temp / (label + '.swift')
        text = boundary.replace('// PRODUCTION_PRESENTATION_HELPERS', helper_code).replace('// PRODUCTION_LOCAL_SECTIONS', row_code).replace('// PRODUCTION_FOOTER', footer_code).replace('// PRODUCTION_ACCESSORIES', accessory_code)
        fixture.write_text(text)
        for optimized in [False, True]:
            binary = temp / (label + ('-O' if optimized else '-debug'))
            subprocess.run([str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), *(['-O'] if optimized else []), str(models), str(fixture), str(tests), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary), str(fixture_data)], capture_output=True, text=True, timeout=30, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                status = result.stdout.strip()
            else:
                assert result.returncode != 0 and 'Local model menu regression:' in result.stderr, label + result.stdout + result.stderr
                status = 'regression reproduced and rejected'
            runs.append(binary.name + ': ' + status)
            print(runs[-1], flush=True)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-local-model-menu-') as directory:
        temp = Path(directory)
        rejected = guard_checks(args.source, temp / 'guards')
        runtime = temp / 'runtime'
        runtime.mkdir()
        runs = runtime_checks(args.source, args.swiftc, runtime) if args.swiftc else []
        if args.swiftc:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / PREFERENCES)], check=True)
    report = {'replacements': len(PLAN['outputs']), 'guards': len(PLAN['guards']), 'fail_closed': len(rejected), 'executions': runs, 'localization': '71 languages × 613 keys', 'sdk': 'not run', 'device': 'pending', 'boundaries': 'Actual presentation/row/footer/accessory functions and real model catalog IDs and translations. UIKit rendering and download IO are doubles; download/activation/selection/storage and unrelated provider methods remain byte-identical.'}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

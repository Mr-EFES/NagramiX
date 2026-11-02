#!/usr/bin/env python3
"""Verify the real formatting helper and native command/keyboard routing."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PANEL = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelNode.swift'
HELPER = 'submodules/NagramiXCore/Sources/NagramiXFormattingSettings.swift'
UI = 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def block(text, marker):
    assert text.count(marker) == 1, marker
    start = text.index(marker)
    brace = text.index('{', start)
    depth = 1
    for i in range(brace + 1, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0: return text[start:i + 1]
    raise AssertionError(marker)


def validate(before, after, swiftc):
    plan = json.loads((ROOT / 'ios/quick_format_patches.json').read_text())
    a, b = manifest(before), manifest(after)
    changed = {n for n in a if a[n] != b.get(n)}
    added = set(plan['copies'].values()) | {HELPER}
    assert changed == {p[0] for p in plan['patches']}, changed
    assert b.keys() - a.keys() == added and not a.keys() - b.keys()
    texts = {n: (before / n).read_text() for n in plan['hashes']}
    assert all(a[n] == sha for n, sha in plan['hashes'].items())
    templates = {marker: (ROOT / 'ios' / name).read_text().rstrip('\n') for marker, name in plan['templates'].items()}
    for n, old, new, count in plan['patches']:
        for marker, template in templates.items(): new = new.replace(marker, template)
        assert texts[n].count(old) == count
        texts[n] = texts[n].replace(old, new, count)
    assert all((after / n).read_text() == text for n, text in texts.items())
    for template, n in {**plan['provided'], **plan['copies']}.items():
        assert (after / n).read_bytes() == (ROOT / 'ios' / template).read_bytes()
    spec = importlib.util.spec_from_file_location('quick_format', ROOT / 'ios/quick_format.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected = []
    execution = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)

        def seed(path):
            for n in plan['hashes']:
                target = path / n; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(before / n, target)
            for template, n in plan['provided'].items():
                target = path / n; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'ios' / template, target)

        def reject(path, label, overlay=ROOT / 'ios'):
            old = manifest(path)
            try: module.apply_quick_format(path, overlay)
            except (SystemExit, FileNotFoundError): pass
            else: raise AssertionError(label)
            assert old == manifest(path), 'partial writes: ' + label
            rejected.append(label)

        path = folder / 'valid'; seed(path); module.apply_quick_format(path, ROOT / 'ios')
        assert all((path / n).read_bytes() == (after / n).read_bytes() for n in plan['hashes'])
        reject(path, 'reapply')
        for i, n in enumerate(plan['hashes']):
            for kind in ['missing', 'drift']:
                path = folder / (kind + str(i)); seed(path)
                if kind == 'missing': (path / n).unlink()
                else: (path / n).write_bytes((path / n).read_bytes() + b'\n// drift\n')
                reject(path, kind + ' ' + n)
        for template, n in plan['provided'].items():
            for kind in ['missing', 'drift']:
                path = folder / (kind + '-provided'); seed(path)
                if kind == 'missing': (path / n).unlink()
                else: (path / n).write_bytes(b'// stale helper')
                reject(path, kind + ' provided')
        for scenario in ['missing-template', 'empty-template', 'missing-copy', 'collision', 'anchor', 'glob']:
            path = folder / scenario; seed(path)
            overlay = folder / (scenario + '-overlay'); overlay.mkdir()
            custom_plan = json.loads(json.dumps(plan))
            for name in [*plan['templates'].values(), *plan['copies'], *plan['provided']]:
                target = overlay / name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'ios' / name, target)
            template = overlay / next(iter(plan['templates'].values()))
            if scenario == 'missing-template': template.unlink()
            elif scenario == 'empty-template': template.write_text(' ')
            elif scenario == 'missing-copy': (overlay / next(iter(plan['copies']))).unlink()
            elif scenario == 'collision': (path / next(iter(plan['copies'].values()))).write_text('// existing user file')
            elif scenario == 'anchor': custom_plan['patches'][-1][1] = 'missing exact anchor'
            elif scenario == 'glob':
                n = plan['source_globs'][0]
                (path / n).write_text((path / n).read_text().replace('Sources/**/*.swift', 'Sources/old.swift'))
                custom_plan['hashes'][n] = hashlib.sha256((path / n).read_bytes()).hexdigest()
            (overlay / 'quick_format_patches.json').write_text(json.dumps(custom_plan))
            reject(path, scenario, overlay)

        production = (after / PANEL).read_text()
        old_panel = (before / PANEL).read_text()
        # All original transformations and both native context menus are untouched.
        for marker in ['@objc public func formatAttributes' + name + '('
                       for name in ['Bold', 'Italic', 'Monospace', 'Link', 'Date', 'Strikethrough', 'Underline', 'Quote', 'CodeBlock', 'Spoiler']]:
            assert block(production, marker) == block(old_panel, marker), marker
        for marker in ['public func chatInputTextNodeMenu(', 'private func buildRichTextContextMenuElements(']:
            assert block(production, marker) == block(old_panel, marker), marker
        template = next(iter(templates.values()))
        names = ['nagramiXFormattingWidth', 'nagramiXFormattingInputView', 'nagramiXCloseFormatting',
                 'nagramiXToggleFormatting', 'nagramiXFormattingSelection', 'nagramiXFormattingAvailable',
                 'nagramiXFormattingSelected', 'nagramiXApplyFormatting']
        methods = [block(template, 'func ' + n + '(').replace('@objc ', '') for n in names]
        boundary = (ROOT / 'scripts/tests/NagramiXQuickFormattingBoundary.swift').read_text()
        panel = '''final class FormattingPanel {
    var sendingTextDisabled = false, extendedSearchLayout = false, nagramiXFormattingActive = false
    var nagramiXFormattingKeyboard: NagramiXFormattingKeyboard?
    var richTextInputNode: Editor? = Editor()
    var presentationInterfaceState: ChatPresentationInterfaceState? = ChatPresentationInterfaceState()
    lazy var interfaceInteraction: Interaction? = Interaction(self.presentationInterfaceState!)
    var legacy: [String] = [], updates = 0
    func loadTextInputNodeIfNeeded() {}
    func ensureFocused() { self.richTextInputNode?.makeInputFirstResponder() }
    func nagramiXUpdateFormatting() { updates += 1 }
    func requestLayout(transition: Transition) {}
'''
        for action, name in [('quote', 'Quote'), ('spoiler', 'Spoiler'), ('bold', 'Bold'), ('italic', 'Italic'), ('monospace', 'Monospace'), ('link', 'Link'), ('date', 'Date'), ('strikethrough', 'Strikethrough'), ('underline', 'Underline'), ('code', 'CodeBlock')]:
            panel += '    func formatAttributes' + name + '(_ sender: Any) { legacy.append("' + action + '") }\n'
        panel += '\n'.join(methods) + '\n}\n'
        generated = folder / 'FormattingBoundary.swift'
        generated.write_text(boundary.replace('// FORMATTING_PANEL', panel))
        for mode in ['debug', 'optimized']:
            binary = folder / ('formatting-' + mode)
            cmd = [str(swiftc), '-warnings-as-errors', '-module-cache-path', str(folder / 'modules'), str(after / HELPER), str(generated), str(ROOT / 'scripts/tests/NagramiXQuickFormattingTests.swift'), '-o', str(binary)]
            if mode == 'optimized': cmd.insert(1, '-O')
            subprocess.run(cmd, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(folder / ('preferences-' + mode)))
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, env=env, timeout=30).strip())
            for command, value in [('fresh', 'false'), ('set', 'true'), ('read', 'true'), ('set', 'false'), ('read', 'false'), ('read', 'false')]:
                subprocess.run([str(binary), command, value], check=True, env=env, stdout=subprocess.PIPE, timeout=15)
            execution.append(mode + ': PASS 6 separate cold processes')
        subprocess.run([str(swiftc), '-frontend', '-parse', *[str(after / n) for n in sorted(changed | added) if n.endswith('.swift')]], check=True)
    ui = (after / UI).read_text()
    arguments = block(ui, 'private struct NagramiXSettingsControllerArguments')
    call = ui[ui.index('    let arguments = NagramiXSettingsControllerArguments('):ui.index('    let mediaInputSettings = context.sharedContext.accountManager.sharedData(')]
    assert re.findall(r'^    let (\w+):', arguments, re.M) == re.findall(r'^        (\w+):', call, re.M)
    assert 'case .quickFormatting: return 157' in ui and 'case .quickFormatting: return 348' in ui
    assert ui.count('case .quickFormatting, .autoRevealSpoilers, .hideBlockedMessages,') == 2
    assert ui.count('.quickFormatting(NagramiXFormattingSettings.enabled)') == 1
    assert 'updateQuickFormatting: { value in NagramiXFormattingSettings.setEnabled(value) }' in ui
    assert 'maximumNumberOfLines: 0' in ui[ui.index('case let .quickFormatting(value):'):][:400]
    assert 'return strings.nagramiXQuickFormattingSearchTerms' in ui
    for lang in ['ru', 'en']:
        strings = (after / f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        for key in ['Title', 'SearchTerms', 'Keyboard']:
            assert strings.count('"NagramiX.QuickFormatting.' + key + '" = ') == 1
    for name in ['ios/apply_features.py', 'ios/quick_format.py', 'scripts/validate_quick_format.py']:
        ast.parse((ROOT / name).read_text())
    return dict(outputs=len(b), changed=sorted(changed), added=sorted(added), unchanged=len(a)-len(changed), sha_guards=len(plan['hashes']), exact_operations=len(plan['patches']), fail_closed=rejected, execution=execution, apple_sdk='not run: no build authorization', physical_iphone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'swiftc', 'report']: parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.before, args.after, args.swiftc)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

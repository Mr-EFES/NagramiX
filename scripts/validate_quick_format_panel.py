#!/usr/bin/env python3
"""Check the approved panel/native-host integration; never claim UIKit execution."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from validate_quick_format import block, manifest, PANEL, HELPER
from validate_quick_format_visual import runtime_boundary, KEYBOARD, GEOMETRY

ROOT = Path(__file__).resolve().parents[1]
FACTORY = 'submodules/TelegramUI/Sources/ChatInterfaceInputNodes.swift'
CONTROLLER = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'
EXPANDED = 'submodules/TelegramUI/Components/RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
COMPONENT = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/ChatTextInputPanelComponent.swift'


def boundaries(after):
    panel = (after / PANEL).read_text()
    s = runtime_boundary(panel, (after / KEYBOARD).read_text())
    s = s.replace('class UIView {', '''class UIView {
    let layer = Layer()
    var clipsToBounds = false
    var subviews: [UIView] = []
    weak var superview: UIView?
    func addSubview(_ view: UIView) {
        view.superview?.subviews.removeAll(where: { $0 === view })
        view.superview = self
        self.subviews.append(view)
    }
''', 1)
    s = s.replace('case text, media, none', 'case text, media, none, inputButtons')
    s = s.replace('var inputTextPanelState =', 'var forceInputCommandsHidden = false\n    var inputTextPanelState =')
    s = s.replace('var keyboardInputView: UIView?', '''var nilInputWrites = 0
    var keyboardInputView: UIView? { didSet { if keyboardInputView == nil { nilInputWrites += 1 } } }''')
    s = s.replace('    var action: ((NagramiXFormattingAction) -> Void)?', '''    enum ExtraAction { case pullQuote, selectAll }
    var extraAction: ((ExtraAction) -> Void)?
    var action: ((NagramiXFormattingAction) -> Void)?''')
    extras = '''    var nagramiXFormattingHostInputView: UIView?
    var nagramiXFormattingRequestLayout: (() -> Void)?
    func nagramiXApplyExtraFormatting(_ action: NagramiXFormattingKeyboard.ExtraAction) {}
'''
    for marker in ['func nagramiXConfigureFormattingHost(', 'var nagramiXFormattingOwnedInputView:', 'func nagramiXFormattingPanelView(']:
        extras += block(panel, marker) + '\n'
    s = s.replace('final class FormattingPanel {', 'final class FormattingPanel {\n' + extras)
    native = (ROOT / 'scripts/tests/NagramiXFormattingPanelBoundary.swift').read_text()
    factory = (after / FACTORY).read_text()
    native = native.replace('// NATIVE_INPUT_FACTORY',
        block(factory, 'private final class NagramiXFormattingInputNode:') + '\n' + block(factory, 'func inputNodeForChatPresentationIntefaceState('))
    component = (after / COMPONENT).read_text()
    native = native.replace('// COMPONENT_INPUT_VIEW', block(component,
        'if let richTextInputNode = panelNode.richTextInputNode {\n                // Do not discard'))
    return s, native


def validate(args):
    plan = json.loads((ROOT / 'ios/quick_format_panel_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    changed = {n for n in before if before[n] != after.get(n)}
    assert changed == set(plan['inputs']) and before.keys() == after.keys()
    assert before == plan['inputs'] and after == plan['outputs']
    panel_before, panel_after = (args.before / PANEL).read_text(), (args.after / PANEL).read_text()
    for name in ['nagramiXFormattingWidth', 'nagramiXFormattingSelection', 'nagramiXFormattingAvailable',
                 'nagramiXFormattingSelected', 'nagramiXApplyFormatting', 'nagramiXExtraFormattingAvailable', 'nagramiXApplyExtraFormatting']:
        assert block(panel_before, 'func ' + name + '(') == block(panel_after, 'func ' + name + '('), name
    for name in ['Bold', 'Italic', 'Monospace', 'Link', 'Date', 'Strikethrough', 'Underline', 'Quote', 'CodeBlock', 'Spoiler']:
        assert block(panel_before, 'func formatAttributes' + name + '(') == block(panel_after, 'func formatAttributes' + name + '(')
    for name in ['nagramiXApplyExpandedFormatting', 'nagramiXApplyExpandedExtra', 'presentLinkPrompt', 'reconcilePreupload', 'complete']:
        assert block((args.before / EXPANDED).read_text(), 'func ' + name + '(') == block((args.after / EXPANDED).read_text(), 'func ' + name + '(')
    assert block((args.before / CONTROLLER).read_text(), 'func sendCurrentMessage(') == block((args.after / CONTROLLER).read_text(), 'func sendCurrentMessage(')
    expanded = (args.after / EXPANDED).read_text()
    helper = block(expanded, 'func nagramiXRequestInputPanelLayout(')
    assert 'UIAccessibility.isReduceMotionEnabled ? .immediate : .spring(duration: 0.4)' in helper
    assert expanded.count('self.nagramiXRequestInputPanelLayout()') == 2
    assert 'self.emptyInputView' in (args.after / CONTROLLER).read_text()
    assert '.animated(duration: 0.4, curve: .spring)' in (args.after / CONTROLLER).read_text()
    assert 'UIView.animate' not in block((args.after / KEYBOARD).read_text(), 'override func didMoveToWindow(')
    assert 'self.frame.size.height =' not in block((args.after / KEYBOARD).read_text(), 'func updateHeight(')

    spec = importlib.util.spec_from_file_location('quick_format_panel', ROOT / 'ios/quick_format_panel.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected, execution = [], []
    with tempfile.TemporaryDirectory(prefix='format-panel-') as directory:
        tmp = Path(directory)

        def seed(target):
            for n in plan['inputs']:
                f = target / n; f.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(args.before / n, f)

        def reject(target, name, overlay=ROOT / 'ios'):
            saved = manifest(target)
            try:
                module.apply_quick_format_panel(target, overlay)
            except (SystemExit, FileNotFoundError):
                pass
            else:
                raise AssertionError(name)
            assert saved == manifest(target), name
            rejected.append(name)

        valid = tmp / 'valid'; seed(valid); module.apply_quick_format_panel(valid, ROOT / 'ios')
        assert manifest(valid) == after
        reject(valid, 'reapply')
        for i, n in enumerate(plan['inputs']):
            for kind in ['missing', 'drift']:
                target = tmp / (kind + str(i)); seed(target)
                if kind == 'missing': (target / n).unlink()
                else: (target / n).write_text((target / n).read_text() + '\n// drift')
                reject(target, kind + ' ' + n)
        for kind in ['anchor', 'output', 'unsafe']:
            target = tmp / kind; seed(target); overlay = tmp / (kind + '-overlay'); overlay.mkdir()
            custom = json.loads(json.dumps(plan))
            if kind == 'anchor': custom['patches'][-1][1] += '// missing anchor'
            elif kind == 'output': custom['outputs'][next(iter(custom['outputs']))] = '0' * 64
            else: custom['inputs']['../escape.swift'] = '0' * 64
            (overlay / 'quick_format_panel_patches.json').write_text(json.dumps(custom))
            reject(target, kind, overlay)

        first, second = boundaries(args.after)
        (tmp / 'Boundary.swift').write_text(first)
        (tmp / 'NativeBoundary.swift').write_text(second)
        (tmp / 'OldTests.swift').write_text((ROOT / 'scripts/tests/NagramiXQuickFormattingTests.swift').read_text().replace('@main struct QuickFormattingTests', 'struct QuickFormattingTests', 1))
        for mode in ['debug', 'optimized']:
            binary = tmp / mode
            cmd = [str(args.swiftc), '-warnings-as-errors', '-module-cache-path', str(tmp / 'cache'),
                str(tmp / 'Boundary.swift'), str(tmp / 'NativeBoundary.swift'), str(tmp / 'OldTests.swift'),
                str(args.helper), str(args.after / GEOMETRY), str(ROOT / 'scripts/tests/NagramiXFormattingPanelTests.swift'), '-o', str(binary)]
            if mode == 'optimized': cmd.insert(1, '-O')
            subprocess.run(cmd, check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(tmp / ('prefs-' + mode)))
            execution.append(mode + ': ' + subprocess.check_output([str(binary)], text=True, env=env, timeout=30).strip())
            for command, value in [('fresh', 'false'), ('set', 'true'), ('read', 'true'), ('set', 'false'), ('read', 'false'), ('read', 'false')]:
                subprocess.run([str(binary), command, value], env=env, check=True, stdout=subprocess.PIPE, timeout=15)
            execution.append(mode + ': 6 cold preference processes PASS')
        subprocess.run([str(args.swiftc), '-frontend', '-parse', *[str(args.after / n) for n in sorted(changed)]], check=True)
    for n in ['ios/quick_format_panel.py', 'ios/apply_overlay.py', 'scripts/validate_quick_format_panel.py']:
        ast.parse((ROOT / n).read_text())
    return dict(changed=sorted(changed), operations=len(plan['patches']), fail_closed=rejected, execution=execution,
        UIKit='boundaries; actual iOS animation and layout not executed', Apple_SDK='pending separate build', physical_iPhone='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'helper', 'swiftc', 'report']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = validate(args)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

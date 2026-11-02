#!/usr/bin/env python3
"""Verify keyboard-matched formatting geometry and preserved native commands."""
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
from validate_quick_format import block, manifest, PANEL, HELPER

ROOT = Path(__file__).resolve().parents[1]
UI = 'submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode/Sources/'
KEYBOARD = UI + 'NagramiXFormattingKeyboard.swift'
GEOMETRY = UI + 'NagramiXFormattingGeometry.swift'
CONTROLLER = 'submodules/TelegramUI/Sources/ChatControllerNode.swift'


def runtime_boundary(template, keyboard):
    names = ['nagramiXFormattingWidth', 'nagramiXFormattingInputView', 'nagramiXUpdateFormattingKeyboardGeometry',
             'nagramiXCloseFormatting', 'nagramiXToggleFormatting', 'nagramiXFormattingSelection',
             'nagramiXFormattingAvailable', 'nagramiXFormattingSelected', 'nagramiXApplyFormatting']
    methods = [block(template, 'func ' + n + '(').replace('@objc ', '') for n in names]
    boundary = (ROOT / 'scripts/tests/NagramiXQuickFormattingBoundary.swift').read_text()
    boundary = boundary.replace('class UIView {}', '''class UIView {
    static let noIntrinsicMetric: CGFloat = -1
    var frame = CGRect.zero
    var intrinsicInvalidations = 0, layoutInvalidations = 0
    func invalidateIntrinsicContentSize() { intrinsicInvalidations += 1 }
    func setNeedsLayout() { layoutInvalidations += 1 }
}''')
    resize = block(keyboard, 'func updateHeight(')
    intrinsic = block(keyboard, 'var intrinsicContentSize:')
    boundary = boundary.replace('    init(title: String) {}', '''    var preferredHeight: CGFloat
    init(title: String, height: CGFloat) { self.preferredHeight = height; super.init(); self.frame = CGRect(x:0,y:0,width:393,height:height) }
''' + resize + '\n' + intrinsic)
    boundary = boundary.replace('var TextFormat_Format = "Format"', 'var TextFormat_Format = "Format", nagramiXFormattingPanelTitle = "Formatting"')
    panel = '''final class FormattingPanel {
    var sendingTextDisabled = false, extendedSearchLayout = false, nagramiXFormattingActive = false
    var nagramiXFormattingGeometry = NagramiXFormattingKeyboardGeometry()
    var nagramiXFormattingKeyboard: NagramiXFormattingKeyboard?
    var richTextInputNode: Editor? = Editor()
    var presentationInterfaceState: ChatPresentationInterfaceState? = ChatPresentationInterfaceState()
    lazy var interfaceInteraction: Interaction? = Interaction(self.presentationInterfaceState!)
    var legacy: [String] = [], updates = 0, layoutRequests = 0
    init() { self.nagramiXFormattingGeometry.update(container: CGSize(width:393,height:844), keyboardHeight:350, standardHeight:346, canMeasureSystem:true, interactive:false) }
    func loadTextInputNodeIfNeeded() {}
    func ensureFocused() { self.richTextInputNode?.makeInputFirstResponder() }
    func nagramiXUpdateFormatting() { updates += 1 }
    func requestLayout(transition: Transition) { layoutRequests += 1 }
'''
    for action,name in [('quote','Quote'),('spoiler','Spoiler'),('bold','Bold'),('italic','Italic'),('monospace','Monospace'),('link','Link'),('date','Date'),('strikethrough','Strikethrough'),('underline','Underline'),('code','CodeBlock')]:
        panel += '    func formatAttributes'+name+'(_ sender: Any) { legacy.append("'+action+'") }\n'
    panel += '\n'.join(methods) + '\n}\n'
    return boundary.replace('// FORMATTING_PANEL', panel)


def validate(args):
    plan = json.loads((ROOT / 'ios/quick_format_visual_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    patched = {p[0] for p in plan['patches']}
    changed = patched | set(plan['replacements'].values())
    added = set(plan['copies'].values())
    assert {n for n in before if before[n] != after.get(n)} == changed
    assert after.keys() - before.keys() == added and not before.keys() - after.keys()
    assert all(before[n] == sha for n,sha in plan['hashes'].items())
    texts = {n:(args.before/n).read_text() for n in plan['hashes']}
    templates = {marker:(ROOT/'ios'/n).read_text().rstrip('\n') for marker,n in plan['templates'].items()}
    for n,old,new,count in plan['patches']:
        for marker,value in templates.items():new=new.replace(marker,value)
        assert texts[n].count(old)==count
        texts[n]=texts[n].replace(old,new,count)
    assert all(texts[n] == (args.after/n).read_text() for n in patched)
    for template,n in {**plan['replacements'],**plan['copies']}.items():
        assert (ROOT/'ios'/template).read_bytes() == (args.after/n).read_bytes()
    # Old format transformations, rich document routing, post113 forwarding and
    # contacts behavior remain byte-identical outside this presentation stage.
    old_panel, panel = (args.before/PANEL).read_text(), (args.after/PANEL).read_text()
    for marker in ['@objc public func formatAttributes'+n+'(' for n in ['Bold','Italic','Monospace','Link','Date','Strikethrough','Underline','Quote','CodeBlock','Spoiler']]+['public func chatInputTextNodeMenu(', 'private func buildRichTextContextMenuElements(']:
        assert block(old_panel,marker) == block(panel,marker),marker
    for n in ['nagramiXFormattingAvailable','nagramiXFormattingSelection','nagramiXFormattingSelected','nagramiXApplyFormatting','nagramiXCloseFormatting']:
        assert block(old_panel,'func '+n+'(') == block(panel,'func '+n+'('),n
    assert (args.before/HELPER).read_bytes() == (args.after/HELPER).read_bytes()
    assert block((args.before/CONTROLLER).read_text(),'func sendCurrentMessage(') == block((args.after/CONTROLLER).read_text(),'func sendCurrentMessage(')
    keyboard = (args.after/KEYBOARD).read_text()
    assert 'UIScreen.main.bounds.height' not in keyboard and 'height: 320' not in keyboard
    assert 'inputViewStyle: .keyboard' in keyboard and 'self.backgroundColor =' not in keyboard
    assert 'caption.numberOfLines = 1' in keyboard and 'accessibilityLabel = item.accessibilityTitle' in keyboard
    assert '.alwaysTemplate' in panel and 'state.theme.chat.inputPanel.inputControlColor' in block(panel,'func nagramiXUpdateFormatting(')
    assert 'panelControlColor' not in block(panel,'func nagramiXUpdateFormatting(')
    assert 'requestLayout(transition: .immediate)' not in block(panel,'func nagramiXToggleFormatting(')
    assert 'UIAccessibility.isReduceMotionEnabled' in keyboard and 'self.safeAreaInsets.bottom' in keyboard
    assert 'self.safeAreaInsets.left' in keyboard and 'self.safeAreaInsets.right' in keyboard
    assert 'keyboardHeight: layout.inputHeight, standardHeight: layout.standardInputHeight' in (args.after/CONTROLLER).read_text()
    assert 'interactive: layout.inputHeightIsInteractivellyChanging' in (args.after/CONTROLLER).read_text()
    loc_keys=['PanelTitle','MonospaceShort','SpoilerShort','StrikethroughShort','UnderlineShort']
    for lang in ['ru','en']:
        text=(args.after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        keys=re.findall(r'^"([^"]+)"\s*=',text,re.M)
        assert len(keys)==len(set(keys))
        for key in loc_keys:assert text.count('"NagramiX.QuickFormatting.'+key+'" = ')==1
    spec=importlib.util.spec_from_file_location('quick_format_visual',ROOT/'ios/quick_format_visual.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[];execution=[]
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        def seed(target):
            for n in plan['hashes']:
                p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,p)
        def reject(target,label,overlay=ROOT/'ios'):
            saved=manifest(target)
            try:module.apply_quick_format_visual(target,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(target)==saved,label
            rejected.append(label)
        target=temp/'valid';seed(target);module.apply_quick_format_visual(target,ROOT/'ios')
        assert all((target/n).read_bytes()==(args.after/n).read_bytes() for n in changed|added)
        reject(target,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                target=temp/(kind+str(i));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift\n')
                reject(target,kind+' '+n)
        for scenario in ['missing-template','empty-template','missing-replacement','empty-replacement','missing-copy','empty-copy','collision','anchor','glob']:
            target=temp/scenario;seed(target);overlay=temp/(scenario+'-overlay');overlay.mkdir()
            for n in [*plan['templates'].values(),*plan['replacements'],*plan['copies']]:
                p=overlay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/n,p)
            custom=json.loads(json.dumps(plan))
            if scenario.startswith(('missing-','empty-')):
                group=scenario.split('-',1)[1]
                n=next(iter(plan['templates'].values())) if group=='template' else next(iter(plan['replacements'] if group=='replacement' else plan['copies']))
                if scenario.startswith('missing-'):(overlay/n).unlink()
                else:(overlay/n).write_text(' ')
            elif scenario=='collision':(target/next(iter(plan['copies'].values()))).write_text('// conflict')
            elif scenario=='anchor':custom['patches'][-1][1]+='// missing anchor'
            else:
                n=plan['source_globs'][0];p=target/n;p.write_text(p.read_text().replace('Sources/**/*.swift','Sources/old.swift'))
                custom['hashes'][n]=hashlib.sha256(p.read_bytes()).hexdigest()
            (overlay/'quick_format_visual_patches.json').write_text(json.dumps(custom));reject(target,scenario,overlay)
        p=temp/'Boundary.swift';p.write_text(runtime_boundary(next(iter(templates.values())), keyboard))
        old_tests=temp/'ExistingTests.swift';old_tests.write_text((ROOT/'scripts/tests/NagramiXQuickFormattingTests.swift').read_text().replace('@main struct QuickFormattingTests','struct QuickFormattingTests',1))
        for mode in ['debug','optimized']:
            binary=temp/('tests-'+mode)
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(temp/'cache'),str(args.after/HELPER),str(args.after/GEOMETRY),str(p),str(old_tests),str(ROOT/'scripts/tests/NagramiXFormattingVisualTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            env=dict(os.environ,XDG_CONFIG_HOME=str(temp/('preferences-'+mode)))
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,env=env,timeout=45).strip())
            for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:
                subprocess.run([str(binary),command,value],check=True,env=env,stdout=subprocess.PIPE,timeout=15)
            execution.append(mode+': PASS 6 cold processes')
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed|added) if n.endswith('.swift')]],check=True)
    for n in ['ios/apply_features.py','ios/quick_format_visual.py','scripts/validate_quick_format_visual.py']:ast.parse((ROOT/n).read_text())
    return {'native_outputs':len(after),'changed':sorted(changed),'added':sorted(added),'unchanged':len(before)-len(changed),
            'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'templates':len(plan['templates']),
            'replacements':len(plan['replacements']),'copies':len(plan['copies']),'fail_closed':rejected,'execution':execution,
            'native_sdk':'not run: separate build command required','UIKit_rendering_and_keyboard_animation':'physical device pending'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

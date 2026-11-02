#!/usr/bin/env python3
"""Verify shared formatting/footer integration without pretending to run UIKit."""
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
BASE = 'submodules/TelegramUI/Components/'
SCREEN = BASE+'RichTextAttachmentScreen/Sources/RichTextAttachmentScreen.swift'
EMOJI = BASE+'RichTextAttachmentScreen/Sources/RichTextEmojiKeyboardController.swift'
PROTOCOL = BASE+'Chat/ChatInputTextNode/Sources/ChatRichTextInputNode.swift'
NATIVE = BASE+'Chat/ChatRichTextEditorComposer/Sources/RichTextEditorChatInputNode.swift'
FACADE = BASE+'RichTextEditor/Sources/RichTextEditorUIKit/RichTextEditorView.swift'
BAR = BASE+'RichTextAttachmentScreen/Sources/RichTextActionBarComponent.swift'


def boundaries(after):
    panel = (after/PANEL).read_text()
    keyboard = (after/KEYBOARD).read_text()
    boundary = runtime_boundary(panel, keyboard)
    extra = block(keyboard, 'enum ExtraAction ')
    boundary = boundary.replace('final class NagramiXFormattingKeyboard: UIView {', 'final class NagramiXFormattingKeyboard: UIView {\n'+extra+'\nvar extraAction: ((ExtraAction) -> Void)?')
    boundary = boundary.replace('enum ChatRichTextFormatAction: String { case quote,', 'enum ChatRichTextFormatAction: String { case pullQuote, quote,')
    boundary = boundary.replace('final class Editor {', '''final class Editor {
    let nativeSelection = NativeSelectionBoundary()
    let legacySelection = LegacySelectionBoundary()
    var inputContentIsEmpty: Bool { self.content.length == 0 }
    var nagramiXIsPullQuote: Bool { self.nativeSelection.nagramiXIsPullQuote }
    func nagramiXSelectAll() {
        if self.usesNativeRichTextEngine { self.nativeSelection.nagramiXSelectAll() }
        else { self.legacySelection.content = self.content; self.legacySelection.nagramiXSelectAll(); self.selectedRange = self.legacySelection.selectedRange }
    }
''')
    methods = '\n'.join(block(panel, 'func '+n+'(') for n in ['nagramiXExtraFormattingAvailable','nagramiXApplyExtraFormatting'])
    boundary = boundary.replace('final class FormattingPanel {', 'final class FormattingPanel {\n'+methods)
    second = (ROOT/'scripts/tests/NagramiXExpandedFormattingBoundary.swift').read_text()
    second = second.replace('// NATIVE_SELECT_ALL', block((after/FACADE).read_text(), 'func selectAll('))
    second = second.replace('// LEGACY_SELECT_ALL', block((after/PROTOCOL).read_text(), 'func nagramiXSelectAll() {'))
    native = (after/NATIVE).read_text()
    second = second.replace('// NATIVE_SELECTION_ADAPTER', block(native,'func nagramiXSelectAll(')+'\n'+block(native,'var nagramiXIsPullQuote:'))
    second = second.replace('// EMOJI_MODE',block((after/EMOJI).read_text(),'func setEmojiMode('))
    source = (after/SCREEN).read_text()
    names=['nagramiXSetFormattingMode','nagramiXToggleFormatting','nagramiXToggleEmoji','nagramiXExpandedHasContent','nagramiXExpandedFormattingAvailable','nagramiXApplyExpandedFormatting','nagramiXApplyExpandedExtra']
    second = second.replace('// EXPANDED_METHODS', '\n'.join(block(source,'func '+n+'(') for n in names))
    return boundary, second


def validate(args):
    plan = json.loads((ROOT/'ios/quick_format_expanded_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    changed={n for n in before if before[n]!=after.get(n)}
    assert before.keys()==after.keys() and changed==set(plan['hashes'])
    assert all(before[n]==sha for n,sha in plan['hashes'].items())
    texts={n:(args.before/n).read_text() for n in plan['hashes']}
    templates={marker:(ROOT/'ios'/n).read_text().rstrip('\n') for marker,n in plan['templates'].items()}
    for n,old,new,count in plan['patches']:
        for marker,value in templates.items():new=new.replace(marker,value)
        assert texts[n].count(old)==count
        texts[n]=texts[n].replace(old,new,count)
    assert all(text==(args.after/n).read_text() for n,text in texts.items())
    assert (args.before/HELPER).read_bytes()==(args.after/HELPER).read_bytes()
    for n in ['nagramiXFormattingWidth','nagramiXFormattingSelection','nagramiXFormattingAvailable','nagramiXFormattingSelected','nagramiXApplyFormatting','nagramiXCloseFormatting']:
        assert block((args.before/PANEL).read_text(),'func '+n+'(')==block((args.after/PANEL).read_text(),'func '+n+'('),n
    for n in ['Bold','Italic','Monospace','Link','Date','Strikethrough','Underline','Quote','CodeBlock','Spoiler']:
        marker='func formatAttributes'+n+'('
        assert block((args.before/PANEL).read_text(),marker)==block((args.after/PANEL).read_text(),marker)
    for marker in ['func chatInputTextNodeMenu(', 'func buildRichTextContextMenuElements(']:
        assert block((args.before/PANEL).read_text(),marker)==block((args.after/PANEL).read_text(),marker)
    for n in [NATIVE]:
        for marker in ['func performFormatAction(', 'var attributedText:', 'func currentInputContent(']:
            assert block((args.before/n).read_text(),marker)==block((args.after/n).read_text(),marker)
    for marker in ['func presentLinkPrompt(', 'func reconcilePreupload(', 'func complete(']:
        assert block((args.before/SCREEN).read_text(),marker)==block((args.after/SCREEN).read_text(),marker)
    screen=(args.after/SCREEN).read_text();emoji=(args.after/EMOJI).read_text();keyboard=(args.after/KEYBOARD).read_text()
    assert 'measureOnly: self.nagramiXFormattingActive' in screen
    assert 'height: emojiPanelHeight, environment: environment' in screen
    assert 'firstIndex(where: { $0.id == AnyHashable("emoji") })' in screen
    assert 'restoringKeyboard: false, notifyLayout: false' in screen
    assert 'preserveInputView: true, notifyLayout: false' in screen
    assert 'nagramiXFormattingGeneration == generation' in screen
    assert 'self.editor.document =' not in '\n'.join(templates.values())
    assert 'NotificationCenter.default.removeObserver(observer)' in screen
    assert 'node.view.isHidden = measureOnly' in emoji and 'return panelHeight' in emoji
    assert 'isVisible: !measureOnly' in emoji
    assert 'footerMinimumLabelWidth:' in keyboard and 'caption.numberOfLines = 1' in keyboard
    assert 'nagramix_formatting_keyboard_sources' in (args.after/(BASE+'Chat/ChatTextInputPanelNode/BUILD')).read_text()
    build=(args.after/(BASE+'RichTextAttachmentScreen/BUILD')).read_text()
    assert 'ChatTextInputPanelNode:nagramix_formatting_keyboard_sources' in build and '//submodules/NagramiXCore:NagramiXCore' in build
    assert '"//submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode"' not in build
    assert 'let foregroundColor: UIColor' in (args.after/BAR).read_text()
    for lang,value in [('ru','Выделить всё'),('en','Select all')]:
        s=(args.after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert s.count('"NagramiX.QuickFormatting.SelectAll" = "'+value+'";')==1
    spec=importlib.util.spec_from_file_location('expanded',ROOT/'ios/quick_format_expanded.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[];execution=[]
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        def seed(target):
            for n in plan['hashes']:
                p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,p)
        def reject(target,label,overlay=ROOT/'ios'):
            saved=manifest(target)
            try:module.apply_quick_format_expanded(target,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(target)==saved
            rejected.append(label)
        valid=tmp/'valid';seed(valid);module.apply_quick_format_expanded(valid,ROOT/'ios');reject(valid,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                target=tmp/(kind+str(i));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift')
                reject(target,kind+' '+n)
        scenarios=[(kind,n) for n in plan['templates'].values() for kind in ['missing','empty']]+[('anchor',None)]+[('glob',n) for n in plan['source_globs']]
        for i,(kind,n) in enumerate(scenarios):
            target=tmp/('scenario'+str(i));seed(target);overlay=tmp/('overlay'+str(i));overlay.mkdir()
            for path in plan['templates'].values():
                p=overlay/path;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/path,p)
            custom=json.loads(json.dumps(plan))
            if kind=='missing':(overlay/n).unlink()
            elif kind=='empty':(overlay/n).write_text(' ')
            elif kind=='anchor':custom['patches'][-1][1]+='// invalid anchor'
            else:
                p=target/n;p.write_text(p.read_text().replace('Sources/**/*.swift','Sources/stale.swift'))
                custom['hashes'][n]=hashlib.sha256(p.read_bytes()).hexdigest()
            (overlay/'quick_format_expanded_patches.json').write_text(json.dumps(custom));reject(target,kind+' '+str(n),overlay)
        first,second=boundaries(args.after)
        boundary=tmp/'Boundary.swift';boundary.write_text(first)
        expanded=tmp/'ExpandedBoundary.swift';expanded.write_text(second)
        old=tmp/'OldTests.swift';old.write_text((ROOT/'scripts/tests/NagramiXQuickFormattingTests.swift').read_text().replace('@main struct QuickFormattingTests','struct QuickFormattingTests',1))
        visual=tmp/'VisualTests.swift';visual.write_text((ROOT/'scripts/tests/NagramiXFormattingVisualTests.swift').read_text().replace('@main struct FormattingVisualTests','struct FormattingVisualTests',1))
        for mode in ['debug','optimized']:
            binary=tmp/('tests-'+mode)
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(tmp/'cache'),str(boundary),str(expanded),str(args.after/HELPER),str(args.after/GEOMETRY),str(old),str(visual),str(ROOT/'scripts/tests/NagramiXExpandedFormattingTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            env=dict(os.environ,XDG_CONFIG_HOME=str(tmp/('prefs-'+mode)))
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,env=env,timeout=30).strip())
            for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:
                subprocess.run([str(binary),command,value],check=True,env=env,stdout=subprocess.PIPE,timeout=15)
            execution.append(mode+': PASS 6 cold processes')
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed) if n.endswith('.swift')]],check=True)
    for n in ['ios/quick_format_expanded.py','ios/apply_features.py','scripts/validate_quick_format_expanded.py']:ast.parse((ROOT/n).read_text())
    return {'native_outputs':len(after),'changed':sorted(changed),'unchanged':len(after)-len(changed),'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'templates':len(templates),'fail_closed':rejected,'execution':execution,'UIKit_and_document_engine':'boundaries; native selectAll facade and host bodies extracted','Apple_SDK':'pending separate build command','physical_iPhone':'pending'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

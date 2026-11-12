#!/usr/bin/env python3
"""Проверить утверждённый экран сравнения шрифтов и явное применение."""
import argparse,hashlib,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,guard_checks
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from app_font_selection_runtime import MODEL,MANAGER,UI
from app_font_selection_apple import check as apple_check,navigation_check,access_check
import font_preview_apply_runtime as runtime
import app_font_selection_runtime as fonts
from font_preview_apply_native import check as native_node_check

ROOT=Path(__file__).resolve().parents[1];STAGE='font_preview_apply'

def source_contract(source,plan):
    assert plan['required_previous_stage']=='premium_temporary_transcription'
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
    model=(source/MODEL).read_text();before=(ROOT/'ios'/plan['previous'][MODEL]).read_text()
    assert model.startswith(before+'\n'),'Existing font keys/catalogue/defaults changed'
    manager=(source/MANAGER).read_text();old=(ROOT/'ios'/plan['previous'][MANAGER]).read_text()
    assert manager[:manager.index('    public static var licenseDocuments:')]==old[:old.index('    public static var licenseText:')]
    assert manager[manager.index('\nprivate extension UIFont {'):]==old[old.index('\nprivate extension UIFont {'):],'Global font hooks changed'
    ui=(source/UI).read_text()
    select=block(ui,'    public func tableView(_ tableView: UITableView, didSelectRowAt path: IndexPath)')
    assert 'NagramiXFontSettings.update' not in select and 'self.draft.select(entry.id)' in select
    assert ui.count('NagramiXFontSettings.update')==1
    assert 'private let content = UIScrollView()' in ui and 'self.content.isScrollEnabled = bottom > visibleHeight' in ui
    assert 'self.table.tableHeaderView' not in ui and 'self.table.tableFooterView' not in ui
    assert ui.count('statusBar.statusBarStyle =')==2 and ui.count('transition: .immediate)')==2
    assert '.uppercased()' in ui and 'self.draft.synchronize(NagramiXFontSettings.current)' in ui
    assert 'private final class NagramiXFontApplyNode: ASDisplayNode' in ui and 'override func calculateSizeThatFits(' in ui
    license=block(ui,'private final class NagramiXFontLicensesController: ViewController')
    assert 'Font.monospace' not in license and 'Font.regular(base)' in license and '.paragraphStyle: style' in license
    assert 'self.text.isEditable = false; self.text.isSelectable = true' in license
    native=(source/'submodules/UIKitRuntimeUtils/Source/UIKitRuntimeUtils/UIBarButtonItem+Proxy.h').read_text()
    assert '- (instancetype)initWithCustomDisplayNode:(ASDisplayNode *)customDisplayNode;' in native and '@property (nonatomic) bool staysInRow;' in native
    node=(source/'submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode.h').read_text()
    subclasses=(source/'submodules/AsyncDisplayKit/Source/PublicHeaders/AsyncDisplayKit/ASDisplayNode+Subclasses.h').read_text()
    assert '- (instancetype)initWithViewBlock:(ASDisplayNodeViewBlock)viewBlock;' in node
    assert '- (CGSize)calculateSizeThatFits:(CGSize)constrainedSize;' in subclasses and '- (void)invalidateCalculatedLayout;' in subclasses
    theme=(source/'submodules/TelegramPresentationData/Sources/PresentationTheme.swift').read_text()
    assert 'public let itemCheckColors: PresentationThemeFillStrokeForeground' in theme and 'public let foregroundColor: UIColor' in theme
    return {'original_model_and_settings_preserved':True,'original_font_factory_hooks_preserved':True,'native_node_and_bar_item_contracts':'verified against pinned actual headers','license_resources':'four exact originals guarded','theme_and_status':'two live presentation subscriptions'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);contract=source_contract(a.source,plan);initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='font-preview-apply-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'font-preview',code)
        runs+=execute(a.swiftc,folder,'final-font-resolver',fonts.fixture(a.source))
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        for n in [MODEL,MANAGER,UI]:run([a.swiftc,'-frontend','-parse',a.source/n])
        node=native_node_check(a.source,a.swiftc,folder)
        navigation=navigation_check(a.source,a.swiftc,folder);access=access_check(a.source,a.swiftc,folder)
        apple=apple_check(a.source,a.swiftc,folder)
    assert manifest(a.source)==initial
    report={'stage':STAGE,'source_contract':contract,'inputs':len(plan['inputs']),'guards':len(plan['guards']),'loader_refusals':len(refused),'executions':runs,'parsed_swift':3,'warnings_as_errors':True,'native_node':node,'native_navigation':navigation,'public_adapter_access':access,'apple_uikit':apple,'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','device':'pending','boundary':'Actual full draft/settings, row/apply/tab/license handlers, preview-card layout and controller layout run with explicit UIKit/font-metric doubles. This is not pixel fidelity or physical iPhone acceptance; full real UIKit APIs are mandatory in the Apple preflight.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='executions'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

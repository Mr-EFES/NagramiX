#!/usr/bin/env python3
"""Проверить узкую замену кнопки, штатный glass маршрут и прежний draft/apply."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from font_apply_glass_apple import UI,check as apple_check,item_code
import font_preview_apply_runtime as preview

STAGE='font_apply_glass'
def contracts(source,plan):
    assert plan['required_previous_stage']=='round_quality_summary'
    assert set(plan['inputs'])=={UI} and len(plan['guards'])==8 and not plan['copies'] and not plan['deletions']
    before=(OVERLAY/plan['previous'][UI]).read_text();after=(source/UI).read_text()
    expected=before.replace(block(before,'private final class NagramiXFontApplyNode: ASDisplayNode')+'\n\n','',1)
    expected=expected.replace('    private let applyButton = UIButton(type: .system)\n    private var applyNode: ASDisplayNode?\n','',1)
    a=expected.index('        self.applyButton.addTarget(');b=expected.index('        self.licenseButton.addTarget(',a);expected=expected[:a]+expected[b:]
    a=expected.index('        self.applyButton.setTitle(');b=expected.index('        self.licenseTitle.text =',a)
    assert after==expected[:a]+item_code(source)+'\n'+expected[b:],'Changed unrelated preview, apply, layout or license behavior'
    code=item_code(source)
    assert 'style: .plain, target: self, action: #selector(applyTapped)' in code
    assert 'applyItem.isEnabled = self.draft.canApply' in code and 'applyItem.staysInRow = true' in code
    assert 'self.navigationItem.rightBarButtonItem = applyItem' in code
    mapper=(source/'submodules/TelegramUI/Components/NavigationBarNode/Sources/NavigationBarItemContent.swift').read_text()
    assert 'var tint: NavigationBarComponent.Button.Tint = .generic' in block(mapper,'func navigationBarButton(for')
    assert 'content = .text(title: item.title ?? "", isBold: item.style == .done)' in mapper
    layout=(source/'submodules/TelegramUI/Components/NavigationBarComponent/Sources/NavigationBarRowLayout.swift').read_text()
    assert 'return (isText && !isEnabled) ? theme.disabledButtonColor : theme.buttonColor' in layout
    assert 'return .init(kind: theme.glassStyle == .clear ? .clear : .panel)' in layout
    return {'unrelated_source_preserved':True,'native_generic_glass':True,'native_disabled_text':True,'draft_canApply_preserved':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    contract=contracts(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='font-apply-glass-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');apple=apple_check(a.source,a.swiftc,root/'apple')
        runs=execute(a.swiftc,root,'font-preview-apply-final87',preview.fixture(a.source))
        run([a.swiftc,'-frontend','-parse',a.source/UI])
    assert before==manifest(a.source)
    report={'stage':87,'name':STAGE,'contracts':contract,'existing_preview_apply_executions':runs,'loader_refusals':len(refused),'apple_api':apple,'full_application_sdk':'not_run','physical_iphone':'pending','source_unchanged_by_checks':True}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Проверить эффекты ввода, локализацию, исходные редакторы и guarded stage55."""
import argparse,ast,hashlib,json,tempfile
from pathlib import Path
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
from validate_quick_format import block,manifest
from late_source_stages import verified_prefix,LATE_SOURCE_STAGES
from validate_app_language_localization import strings
import input_effects_runtime as runtime
from input_effects_apple import check as apple_check, public_api_check

ROOT=Path(__file__).resolve().parents[1];STAGE='input_effects'


def contract(source,plan):
    assert plan['required_previous_stage']=='youtube_playback_policy' and len(plan['inputs'])==75 and len(plan['guards'])==10
    assert set(plan['copies'])=={runtime.SETTINGS,runtime.ANIMATION}
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards'],**{n:r['sha256'] for n,r in plan['copies'].items()}}.items():assert digest(source/n)==h,n
    # Real upstream public types: UIView, not ASDisplayNode. This guards both
    # native call sites against the unsupported extra .view seen in early drafts.
    before=(ROOT/'ios'/plan['previous'][runtime.CHAT]).read_text();after=(source/runtime.CHAT).read_text()
    assert 'public let textInputNodeClippingContainer: UIView' in before and 'public let attachmentButton: HighlightTrackingButton' in before
    assert 'open class HighlightTrackingButton: UIButton' in (source/'submodules/Display/Source/HighlightTrackingButton.swift').read_text()
    call='            self.nagramiXTypingAnimation.play(target: self.textInputNodeClippingContainer, companions: [self.attachmentButton], color: presentationInterfaceState.theme.chat.inputPanel.panelControlAccentColor)\n'
    declaration='    private let nagramiXTypingAnimation = NagramiXTypingAnimation()\n\n'
    assert after.replace(call,'',1).replace(declaration,'',1)==before,'Chat composer changed beyond decoration hook'
    before=(ROOT/'ios'/plan['previous'][runtime.ATTACHMENT]).read_text();after=(source/runtime.ATTACHMENT).read_text()
    assert 'public let textInputContainer: ASDisplayNode' in before
    call='            self.nagramiXTypingAnimation.play(target: self.textInputContainer.view, color: presentationInterfaceState.theme.chat.inputPanel.panelControlAccentColor)\n'
    assert after.replace('import NagramiXCore\n','',1).replace('    private let nagramiXTypingAnimation = NagramiXTypingAnimation()\n','',1).replace(call,'',1)==before,'Attachment composer changed beyond decoration hook'
    build=(source/'submodules/AttachmentTextInputPanelNode/BUILD').read_text();assert build.count('"//submodules/NagramiXCore:NagramiXCore"')==1
    core=(source/'submodules/NagramiXCore/BUILD').read_text();assert '"Sources/**/*.swift"' in core and 'AttachmentTextInputPanelNode' not in core
    ui=(source/runtime.UI).read_text();assert 'case inputEffects' in ui and 'return 6100' in ui and 'return 6101' in ui and 'return 6102' in ui
    assert 'maximumNumberOfLines: 0' in ui[ui.index('        case let .inputEffectsEnabled(enabled):'):ui.index('        case let .inputEffectsPreset(preset):')]
    assert 'guard let preset = NagramiXTypingPreset(rawValue: id), NagramiXTypingSettings.current.enabled else { return }' in ui
    assert 'guard NagramiXTypingSettings.current.enabled, NagramiXTypingSettings.current.preset == .custom else { return }' in ui
    from settings_header_contract import check
    headers=check(ui)
    animation=(source/runtime.ANIMATION).read_text();settings=(source/runtime.SETTINGS).read_text()
    for forbidden in ['.text =','.attributedText =','.selectedRange =','.transform =','removeAllAnimations','Timer(','CADisplayLink','ghostgram','GGTyping']:
        assert forbidden not in animation+settings,forbidden
    loc=json.loads((ROOT/'ios/input_effects/localization.json').read_text())
    assert hashlib.sha256((ROOT/'ios/input_effects/localization.json').read_bytes()).hexdigest()==plan['templates']['input_effects/localization.json']
    codes={x['code'] for x in json.loads((ROOT/'ios/app_language_localization/languages.json').read_text())['languages']}
    assert set(loc['translations'])==codes and len(loc['keys'])==14
    for code in codes:
        n='submodules/NagramiXCore/Resources/'+code+'.lproj/Localizable.strings'
        before=strings(ROOT/'ios'/plan['previous'][n]);after=strings(source/n)
        assert len(before)==650 and after=={**before,**dict(zip(loc['keys'],loc['translations'][code]))}
        assert len(loc['translations'][code])==14 and all(loc['translations'][code])
    assert loc['translations']['ru'][:2]==['Эффекты ввода','Анимация при наборе']
    return {'native_input_origins':plan['native_inputs'],'dependencies':dependency_check(source),'same_composer_text_formatting_selection_and_layout':True,'actual_native_view_types_verified':True,'scope':'Chat composer and attachment captions; other unrelated composers unchanged','settings':'independent persisted OFF by default; live cleanup; six presets/five custom parameters','locales':71,'keys':664,'header_contract':headers,'build_dependency':'Core glob discovers two public helpers; attachment adds existing Core dependency without a reverse edge'}


def dependency_check(source):
    def canonical(label):
        package, _, target = label.removeprefix('//').partition(':')
        return '//' + package + ':' + (target or package.rsplit('/', 1)[-1])
    def deps(label):
        package, _, target = label.removeprefix('//').partition(':')
        build = source/package/'BUILD'
        if not build.is_file(): return []
        for call in ast.walk(ast.parse(build.read_text())):
            if not isinstance(call, ast.Call): continue
            keywords = {k.arg:k.value for k in call.keywords}
            name = keywords.get('name')
            if not isinstance(name, ast.Constant) or name.value != target: continue
            dependency = keywords.get('deps')
            if dependency is None: return []
            labels = [v.value for v in ast.walk(dependency) if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            return [v if v.startswith('//') else '//'+package+v for v in labels if v.startswith('//') or v.startswith(':')]
        return []
    forbidden = {'//submodules/AttachmentTextInputPanelNode:AttachmentTextInputPanelNode', '//submodules/TelegramUI/Components/Chat/ChatTextInputPanelNode:ChatTextInputPanelNode'}
    seen = set(); queue = ['//submodules/NagramiXCore:NagramiXCore']
    while queue:
        label = canonical(queue.pop())
        if label in seen: continue
        assert label not in forbidden, 'Typing Core dependency cycle: '+label
        seen.add(label); queue.extend(deps(label))
    return {'literal_dependency_graph':'passed','core_reachable_labels':len(seen)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE);result=contract(a.source,plan);before=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='input-effects-check-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');code=runtime.fixture(a.source)
        runs=execute(a.swiftc,folder,'input-effects',code)
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        apple=apple_check(a.source,a.swiftc,folder)
        api=public_api_check(a.source,a.swiftc,folder)
        for n in [runtime.UI,runtime.CHAT,runtime.ATTACHMENT,runtime.SETTINGS,runtime.ANIMATION]:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert before==manifest(a.source)
    report={'stage':STAGE,'source_contract':result,'loader_refusals':len(refused),'executions':runs,'apple_sdk_precheck':apple,'public_api_boundary':api,'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','device':'pending','boundary':'Actual full settings/animator/entries with explicit UIKit/CA event adapters. Does not render pixels, simulate native keyboard/IME/autocorrection, or replace the mandatory real Apple SDK and physical iPhone checks.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

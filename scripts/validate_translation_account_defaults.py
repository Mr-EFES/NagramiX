#!/usr/bin/env python3
"""Проверить начальные настройки переводчика и приоритет ручного выбора."""
import argparse,json,subprocess,tempfile,os,uuid
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import translation_account_defaults_runtime as runtime
STAGE='translation_account_defaults'

def modules(source,swiftc,temp):
 temp.mkdir(parents=True);producer=temp/'TranslateUI.swift';producer.write_bytes((source/runtime.M).read_bytes())
 consumer=temp/'Client.swift';consumer.write_text('''import TranslateUI
func accountDefault(_ id: Int64, _ premium: Bool) {
 NagramiXTranslationSettings.registerAccountDefault(accountId: id, isPremium: premium)
 let configuration = NagramiXTranslationSettings.configuration(accountId: id)
 let _: String = configuration.provider.settingsTitle
 let _: String = configuration.provider.title
 NagramiXTranslationSettings.update { $0.usesAccountDefaultProvider = false }
}
''')
 cmd=[swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',temp/'cache','-emit-module','-module-name','TranslateUI',producer,'-emit-module-path',temp/'TranslateUI.swiftmodule']
 run(cmd);run([swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',temp/'cache','-typecheck','-I',temp,consumer])
 producer.write_text(producer.read_text().replace('public var settingsTitle:','var settingsTitle:',1));run(cmd)
 rejected=subprocess.run([str(x) for x in [swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',temp/'cache','-typecheck','-I',temp,consumer]],capture_output=True,text=True)
 assert rejected.returncode!=0 and 'inaccessible' in rejected.stderr and 'settingsTitle' in rejected.stderr,rejected.stderr
 return {'status':'passed','production_model':'complete; genuine Foundation and Swift module export/import','negative':'internal settingsTitle rejected','UIKit_and_whole_app':'not_run'}

def contracts(source,plan):
 assert plan['required_previous_stage']=='unified_glass_menus' and set(plan['inputs'])=={runtime.M,runtime.P,runtime.R,runtime.I,runtime.V,runtime.S,runtime.A,runtime.H}
 assert len(plan['guards'])==9 and not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
 before=lambda n:(OVERLAY/plan['previous'][n]).read_text()
 after=lambda n:(source/n).read_text()
 for n,old,new in [(runtime.R,'let configuration = configuration ?? NagramiXTranslationSettings.current','let configuration = configuration ?? NagramiXTranslationSettings.configuration(accountId: context.account.id.int64)'),(runtime.I,'        let configuration = NagramiXTranslationSettings.current','        let configuration = NagramiXTranslationSettings.configuration(accountId: context.account.id.int64)'),(runtime.V,'        let configuration = NagramiXTranslationSettings.current','        let configuration = NagramiXTranslationSettings.configuration(accountId: self.context.account.id.int64)'),(runtime.H,'NagramiXTranslationSettings.current.provider.title','NagramiXTranslationSettings.configuration(accountId: self.context.account.id.int64).provider.title')]:
  expected=before(n).replace(old,new,1)
  if n==runtime.R:expected=expected.replace('        let configuration = NagramiXTranslationSettings.current','        let configuration = NagramiXTranslationSettings.configuration(accountId: context.account.id.int64)',1)
  assert after(n)==expected,'Unrelated runtime/provider/network logic changed: '+n
 expected=before(runtime.A).replace('import NagramiXTranscription\n','import NagramiXTranscription\nimport TranslateUI\n',1).replace('                NagramiXTranscriptionSettings.registerAccountDefault(accountId: account.id.int64, isPremium: peer.isPremium)','                NagramiXTranscriptionSettings.registerAccountDefault(accountId: account.id.int64, isPremium: peer.isPremium)\n                NagramiXTranslationSettings.registerAccountDefault(accountId: account.id.int64, isPremium: peer.isPremium)',1)
 assert after(runtime.A)==expected,'Unrelated account/audio/recording logic changed'
 p=after(runtime.P);assert 'self.isPremium == true ? [0, 1, 2, 3] : [0, 2, 3]' in p
 assert 'self.presentationData.strings.nagramiXUILocalized(provider.title)' in p
 assert 'nagramiXUILocalized(provider.settingsTitle)' in after(runtime.S)
 for b in ['submodules/SettingsUI/BUILD','submodules/TelegramUI/BUILD','submodules/TelegramUI/Components/TranslateHeaderPanelComponent/BUILD']:
  build=(source/b).read_text();assert '"//submodules/TranslateUI:TranslateUI"' in build or '"//submodules/TranslateUI"' in build,b
 # Existing panel visibility formula and peer overrides remain untouched.
 node=(source/'submodules/TelegramUI/Sources/ChatControllerNode.swift').read_text();assert 'private func nagramiXTranslationPanelAllowed(' in node
 assert block(after(runtime.M),'    public static func chatKey(')==block(before(runtime.M),'    public static func chatKey(')
 assert after(runtime.M)[after(runtime.M).index('    public static func chatKey('):]==before(runtime.M)[before(runtime.M).index('    public static func chatKey('):]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
 assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
 contracts(a.source,plan);state=manifest(a.source)
 with tempfile.TemporaryDirectory(prefix='translation-account-defaults-') as d:
  temp=Path(d);refused=guard_checks(a.source,STAGE,plan,temp/'guards');module=modules(a.source,a.swiftc,temp/'modules');text=runtime.fixture(a.source);runs=execute(a.swiftc,temp,STAGE,text)
  variants=[
   ('master-off','public var enabled = true','public var enabled = false','fresh master on and both optional switches off'),
   ('panel-on','self.showTranslateButton ?? false','self.showTranslateButton ?? true','fresh master on and both optional switches off'),
   ('premium-default','isPremium ? .telegram : .apple','isPremium ? .apple : .apple','two accounts resolve their own Premium defaults'),
   ('explicit-apple','; $0.usesAccountDefaultProvider = false','; $0.usesAccountDefaultProvider = true','selecting same raw Apple explicitly exits automatic provider'),
   ('old-provider-overwritten','?? !values.contains(.provider)','?? true','legacy saved switches and provider remain exact'),
   ('inline-wrong-provider','func capture0(context: TestContext) -> NagramiXTranslationProvider {\nlet configuration = NagramiXTranslationSettings.configuration(accountId: context.account.id.int64)','func capture0(context: TestContext) -> NagramiXTranslationProvider {\nlet configuration = NagramiXTranslationSettings.current','inline route uses account provider'),
  ]
  for name,old,new,why in variants:
   assert text.count(old)==1,(name,text.count(old));runs+=execute(a.swiftc,temp,name,text.replace(old,new,1),why)
  cold=[];fixture=temp/'cold.swift';fixture.write_text(text)
  for mode,flags in [('debug',[]),('optimized',['-O'])]:
   binary=temp/('cold-'+mode);run([a.swiftc,'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',temp/'cache',*flags,fixture,'-o',binary]);env=dict(os.environ,NAGRAMIX_TRANSLATION_TEST_SUITE=str(uuid.uuid4()),XDG_CONFIG_HOME=str(temp/"preferences"))
   try:
    for arg in ['--cold-write','--cold-read','--cold-read']:
     c=subprocess.run([str(binary),arg],env=env,capture_output=True,text=True,timeout=30);assert c.returncode==0,c.stdout+c.stderr;cold.append({'mode':mode,'argument':arg,'exit_code':c.returncode,'output':c.stdout.strip()})
   finally:
    c=subprocess.run([str(binary),'--cleanup'],env=env,capture_output=True,text=True,timeout=30);assert c.returncode==0;cold.append({'mode':mode,'argument':'--cleanup','exit_code':c.returncode})
   binary.unlink()
  for path in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/path])
 assert manifest(a.source)==state
 report={'stage':85,'name':STAGE,'inputs':8,'guards':9,'loader_refusals':len(refused),'executions':runs,'cold_processes':cold,'actual_module_import':module,'source_unchanged_by_checks':True,'scope':'Начальный master ON, panel/whole-chat OFF, known Premium account uses Telegram and non-Premium Apple. Saved explicit provider/OFF/other preferences retained. Outer label Telegram, internal Telegram Premium. Shared revision invalidates stale work on effective default changes; idempotent/manual-provider events do not cancel requests. No provider/network/audio/recording code changed.','boundaries':'Full production settings model with genuine Foundation/Codable/locks; only UserDefaults instance substituted with isolated suite. Actual modified capture/selection/entry/peer registration statements execute with account/peer/row adapters. Separate real model module checks new public exports/imports. UIKit layout, full app, live Telegram/Apple translation and device are pending.','full_application_sdk':'not_run','physical_iphone':'pending','new_actions_or_ipa_started':False}
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

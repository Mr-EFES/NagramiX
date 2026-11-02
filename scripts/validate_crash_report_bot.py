#!/usr/bin/env python3
"""Проверки маршрута отчёта; не отправляет сообщения и не вызывает реальный сбой."""
import argparse,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
 plan=json.loads((ROOT/'ios/crash_report_bot_patches.json').read_text())
 spec=importlib.util.spec_from_file_location('crash_bot',ROOT/'ios/crash_report_bot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with tempfile.TemporaryDirectory() as directory:
  temp=Path(directory);native=temp/'native';before={}
  for n,sha in plan['inputs'].items():
   data=(a.source/n).read_bytes();assert hashlib.sha256(data).hexdigest()==sha
   before[n]=data;p=native/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  m.apply_crash_report_bot(native,ROOT/'ios')
  for n in before:
   text=(native/n).read_text();assert hashlib.sha256(text.encode()).hexdigest()==plan['outputs'][n]
   for path,old,new,count in reversed(plan['patches']):
    if path==n:assert text.count(new)==count;text=text.replace(new,old,count)
   assert text.encode()==before[n]
  guards=0
  def snapshot():return {str(p.relative_to(native)):p.read_bytes() for p in native.rglob('*') if p.is_file()}
  def rejected(overlay):
   nonlocal guards
   initial=snapshot()
   try:m.apply_crash_report_bot(native,overlay)
   except SystemExit:pass
   else:raise AssertionError('guard accepted invalid input')
   assert snapshot()==initial;guards+=1
  def reset():
   for n,data in before.items():(native/n).write_bytes(data)
  rejected(ROOT/'ios')
  for n in before:
   reset();p=native/n;p.write_bytes(before[n]+b'\n');rejected(ROOT/'ios')
   reset();p.unlink();rejected(ROOT/'ios')
  overlay=temp/'overlay';overlay.mkdir()
  for kind in ['output','anchor']:
   reset();wrong=json.loads(json.dumps(plan))
   if kind=='output':wrong['outputs'][next(iter(before))]='0'*64
   else:wrong['patches'][-1][1]+='// invalid'
   (overlay/'crash_report_bot_patches.json').write_text(json.dumps(wrong));rejected(overlay)
  reset();m.apply_crash_report_bot(native,ROOT/'ios')
  controller=native/'submodules/DebugSettingsUI/Sources/CrashReportsController.swift';text=controller.read_text();original=before[str(controller.relative_to(native))].decode()
  assert 'iOSCrashReportsBot' not in text
  assert 'private let crashReportBot = "NagramiX_bot"' in text
  # ZIP contents and local retention stay byte-identical.
  archive=lambda s:s.split('private func crashReportArchive(',1)[1].split('/// The sender',1)[0]
  assert archive(text)==archive(original)
  assert 'CrashReportStore.shared.remove' not in text.split('    func send(',1)[1]
  send=text.split('    func send(',1)[1].split('private enum CrashReportEntry',1)[0]
  assert send.index('nagramiXCrashReportBotId else')<send.index('self.checkBlockedAndEnqueue')
  assert send.index('if case .known(true) = blocked')<send.index('crashReportArchive(report)')<send.index('enqueueMessages(')
  assert send.index('ids.contains(where: { $0 != nil })')<send.index('self.sharedContext.navigateToChat')
  assert 'accountId: context.account.id, peerId: peerId' in send
  assert 'if self.canPresent {\n                                self.sharedContext.navigateToChat' in send
  prompt=text.split('public func setupCrashReportPrompt',1)[1]
  assert prompt.count('actions.send(')==1 and prompt.index('TextAlertAction(type: .defaultAction')<prompt.index('actions.send(')
  assert 'guard active && !locked else' in prompt
  assert 'crashReportAlertsEnabled(override: settings.showCrashReportAlerts' in prompt
  # Compile the exact native recipient predicate and defaults function, preserving Int64.
  guard=text.split('            guard let peer, case let .user(user) = peer,',1)[1].split(' else {',1)[0]
  policy=(native/'submodules/CrashReporting/Sources/CrashReport.swift').read_text().split('public func crashReportAlertsEnabled(',1)[1]
  policy='public func crashReportAlertsEnabled('+policy
  swift='''import Foundation
struct PeerId {
 struct Id { let value: Int64; func _internalGetInt64Value() -> Int64 { value } }
 let namespace: Int32; let id: Id
}
enum Namespaces { enum Peer { static let CloudUser: Int32 = 0 } }
struct User { let id: PeerId; let botInfo: Bool? }
enum EnginePeer { case user(User); case channel }
private let nagramiXCrashReportBotId: Int64 = 8868652150
func accepts(_ peer: EnginePeer?) -> Bool {
 guard let peer, case let .user(user) = peer,GUARD else { return false }
 return true
}
POLICY
@main struct Tests {
 static func main() {
  func peer(_ id: Int64, _ ns: Int32 = 0, _ bot: Bool? = true) -> EnginePeer {
   .user(User(id: PeerId(namespace: ns, id: .init(value: id)), botInfo: bot))
  }
  precondition(accepts(peer(8868652150)))
  for invalid in [nil, EnginePeer.channel, peer(8868652151), peer(8868652150, 1), peer(8868652150, 0, nil), peer(Int64(Int32(truncatingIfNeeded: 8868652150)))] {
   precondition(!accepts(invalid))
  }
  for internalBuild in [true,false] {
   precondition(crashReportAlertsEnabled(override: nil, isInternalBuild: internalBuild))
   precondition(crashReportAlertsEnabled(override: true, isInternalBuild: internalBuild))
   precondition(!crashReportAlertsEnabled(override: false, isInternalBuild: internalBuild))
  }
  print("PASS: 13 native recipient/default cases; Int64, namespace, bot type and saved OFF")
 }
}
'''.replace('GUARD',guard).replace('POLICY',policy)
  swiftpath=temp/'Policy.swift';swiftpath.write_text(swift)
  for mode in [[],['-O']]:
   exe=temp/('policy-opt' if mode else 'policy')
   subprocess.run([a.swiftc,'-parse-as-library','-module-cache-path',str(temp/'cache'),*mode,str(swiftpath),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
  for n in before:
   if n.endswith('.swift'):subprocess.run([a.swiftc,'-frontend','-parse',str(native/n)],check=True)
  # Check exact resource keys/values and placeholders without touching canonical resources.
  for n in before:
   if n.endswith('.strings'):
    data=(native/n).read_text()
    assert 'NagramiX.Debug.NagramiX Crash Report' in data
    assert 'NagramiX.Debug.Crash report queued for @NagramiX_bot.' in data
  # Prove compatibility with the preceding, still-unreleased video fix.
  reset()
  rotation_spec=importlib.util.spec_from_file_location('rotation',ROOT/'ios/video_rotation_registration.py')
  rotation=importlib.util.module_from_spec(rotation_spec);rotation_spec.loader.exec_module(rotation)
  rotation_plan=json.loads((ROOT/'ios/video_rotation_registration_patches.json').read_text())
  for name,sha in rotation_plan['inputs'].items():
   data=(a.source/name).read_bytes();assert hashlib.sha256(data).hexdigest()==sha
   out=native/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
  rotation.apply_video_rotation_registration(native,ROOT/'ios')
  m.apply_crash_report_bot(native,ROOT/'ios')
  expected={**rotation_plan['outputs'],**plan['outputs']}
  assert {str(x.relative_to(native)) for x in native.rglob('*') if x.is_file()}==set(expected)
  for name,sha in expected.items():assert hashlib.sha256((native/name).read_bytes()).hexdigest()==sha
  pipeline=(ROOT/'ios/apply_overlay.py').read_text()
  assert pipeline.index('    apply_video_rotation_registration(')<pipeline.index('    apply_crash_report_bot(')
  print(f'PASS: {guards} fail-closed cases; inverse, consent/queue/navigation/ZIP preservation; Swift parse; combined video+bot stages')
if __name__=='__main__':main()

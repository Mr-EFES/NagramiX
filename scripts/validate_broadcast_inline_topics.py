#!/usr/bin/env python3
"""Проверить native дерево тем, выбор и прежний RPC route без Apple SDK."""
import argparse, hashlib, importlib.util, json, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block
from validate_broadcast_topics import production as routing
from validate_broadcast_containers import row_production
ROOT=Path(__file__).resolve().parents[1]
N='submodules/ChatListUI/Sources/Node/ChatListNode.swift'
E='submodules/ChatListUI/Sources/Node/ChatListNodeEntries.swift'
P='submodules/TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift'
A='submodules/AccountContext/Sources/PeerSelectionController.swift'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--routing-before',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
 plan=json.loads((ROOT/'ios/broadcast_inline_topics_patches.json').read_text())
 spec=importlib.util.spec_from_file_location('inline',ROOT/'ios/broadcast_inline_topics.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with tempfile.TemporaryDirectory() as folder:
  t=Path(folder);native=t/'native';before={n:(a.source/n).read_bytes() for n in plan['inputs']}
  for n,data in before.items():f=native/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  m.apply_broadcast_inline_topics(native,ROOT/'ios')
  after={n:(native/n).read_bytes() for n in before}
  for n,data in after.items():
   assert hashlib.sha256(data).hexdigest()==plan['outputs'][n]
   restored=data.decode()
   for path,old,new,count in reversed(plan['patches']):
    if path==n:assert restored.count(new)==count;restored=restored.replace(new,old,count)
   assert restored.encode()==before[n]
  failures=0
  def reject(overlay):
   nonlocal failures
   snap={n:(native/n).read_bytes() if (native/n).exists() else None for n in before}
   try:m.apply_broadcast_inline_topics(native,overlay)
   except SystemExit:pass
   else:raise AssertionError('invalid overlay accepted')
   assert snap=={n:(native/n).read_bytes() if (native/n).exists() else None for n in before};failures+=1
  reject(ROOT/'ios')
  for name in before:
   for n,data in before.items():(native/n).write_bytes(data)
   (native/name).write_bytes(before[name]+b'\n');reject(ROOT/'ios')
   (native/name).unlink();reject(ROOT/'ios')
  overlay=t/'overlay';overlay.mkdir()
  for kind in ['anchor','output','path']:
   for n,data in before.items():(native/n).write_bytes(data)
   broken=json.loads(json.dumps(plan))
   if kind=='anchor':broken['patches'][-1][1]+='//drift'
   elif kind=='output':broken['outputs'][name]='0'*64
   else:broken['guards']['../unsafe']='0'*64
   (overlay/'broadcast_inline_topics_patches.json').write_text(json.dumps(broken));reject(overlay)
  # Restore final native files after guard probes.
  for n,data in after.items():(native/n).write_bytes(data)
  text=(native/N).read_text()
  generated='import Foundation\n'+block((native/A).read_text(),'public struct ChatListNodePeersFilter:')+'\n'
  generated+=block(text,'private func isIncludedCommunityContainer(')+'\n'
  # Both native row construction paths, with real inline entry metadata.
  generated+=row_production(text,'inline').replace('    var enabled = permitted','    let peerEntry = InlineRow(nagramiXInlineParentIndex: threadId == nil ? nil : 1)\n    var enabled = permitted')
  tree=block(text,'entries = entries.flatMap')
  branch=block(text,'if let threadId, case let .peers(filter, _, _, _, _, _, _) = strongSelf.mode,')
  generated+='''
func makeTree(_ input: [ChatListNodeEntry], lists: [Int:EngineChatList], state: SelectionState) -> [ChatListNodeEntry] {
 var entries = input
 let inlineState = (false, lists)
 let mode = TreeMode.peers(.nagramiXCopyDestinations, false, 0, 0, 0, 0, 0)
 let accountPeerId = 999
TREE
 return entries
}
extension TopicHost {
 func tap(_ peer: EnginePeer, threadId: Int64?) {
  let strongSelf = self
BRANCH
 }
}
'''.replace('TREE',tree).replace('BRANCH',branch)
  comparison=block((native/E).read_text(), 'if case let .PeerEntry(left) = lhs, case let .PeerEntry(right) = rhs,\n           left.nagramiXInlineParentIndex != nil')
  generated+='\nfunc inlineLess(_ lhs:ChatListNodeEntry,_ rhs:ChatListNodeEntry)->Bool {\n'+comparison+'\n if case let .PeerEntry(a)=lhs, case let .PeerEntry(b)=rhs { return a.index < b.index }; return false\n}\n'
  # Previous 107 routing/folder tests execute production code too.
  enqueue='submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
  support=native/enqueue;support.parent.mkdir(parents=True,exist_ok=True);support.write_bytes((a.source/enqueue).read_bytes())
  generated+=routing(a.routing_before,native)
  (t/'Production.swift').write_text(generated)
  old=(ROOT/'scripts/tests/NagramiXBroadcastTopicsTests.swift').read_text().replace('@main struct Tests','struct Tests').replace('    var editing = false','    var nagramiXCopyThreadIds: [Int:Int64] = [:]\n    var editing = false')
  (t/'OldTests.swift').write_text(old)
  for mode in [[],['-O']]:
   exe=t/('opt' if mode else 'debug')
   subprocess.run([a.swiftc,'-module-cache-path',str(t/'cache'),*mode,str(t/'OldTests.swift'),str(t/'Production.swift'),str(ROOT/'scripts/tests/NagramiXBroadcastInlineTests.swift'),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
  subprocess.run([a.swiftc,'-frontend','-parse',*[str(native/n) for n in after]],check=True)
  assert 'return .nagramiXInlineTopic(peerEntry.peer.peerId, threadId)' in (native/E).read_text()
  print(f'PASS: {failures} atomic fail-closed cases; inverse; all native Swift parsed; scoped topic stable IDs')
if __name__=='__main__':main()

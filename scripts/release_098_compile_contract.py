"""Compile actual footer scope and caption producer/caller across separate files.

UIKit, account storage and layout callbacks are explicit recording boundaries.
The changed expression, weak capture, actual caption declaration/body, private
update body and cross-file call spelling come from guarded application source.
"""
import subprocess
from pathlib import Path
from validate_quick_format import block

H='submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift'
S='submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreen.swift'
Q='submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/ChatMediaEditorScreenQuality.swift'


def footer(source):
    text=block((source/H).read_text(),'    @objc private func morePressed(')
    assert 'let context = self.context' in text and '|> map { [weak self] sharedData -> ContextController.Items in' in text
    lines=[l for l in text.splitlines() if 'items.append(.action(' in l and '"Перевод: "' in l]
    assert len(lines)==1
    expression=lines[0].split('ContextMenuActionItem(text: ',1)[1].split(', textFont: .small',1)[0]
    return '''import Foundation
struct AccountId {let int64:Int64}
struct Account {let id:AccountId}
final class AccountContext {let account:Account;init(_ id:Int64){account=Account(id:AccountId(int64:id))}}
struct Strings {func nagramiXUILocalized(_ s:String)->String{s}}
struct PresentationData {let strings=Strings()}
enum NagramiXTranslationSettings {
 struct Provider {let title:String};struct Configuration {let provider:Provider}
 static var ids:[Int64]=[]
 static func configuration(accountId:Int64)->Configuration {ids.append(accountId);return Configuration(provider:Provider(title:"account-\\(accountId)"))}
}
final class ChatTranslationPanelNode {
 let context:AccountContext;static var released=0,observedMissingOwner=0
 init(_ id:Int64){context=AccountContext(id)}
 deinit{ChatTranslationPanelNode.released+=1}
 func footer()->()->String {
  let context = self.context
  let presentationData=PresentationData()
  return { [weak self] in
   if self == nil { ChatTranslationPanelNode.observedMissingOwner+=1 }
   return '''+expression+'''
  }
 }
}
@main enum FooterScopeChecks {static func main(){
 func detached(_ id:Int64)->()->String {
  let owner=ChatTranslationPanelNode(id)
  let callback=owner.footer()
  precondition(callback()=="Перевод: account-\\(id)")
  return callback
 }
 for id:Int64 in [41,92] {
  let callback=detached(id)
  precondition(callback()=="Перевод: account-\\(id)")
 }
 precondition(ChatTranslationPanelNode.released==2)
 precondition(ChatTranslationPanelNode.observedMissingOwner==2)
 precondition(NagramiXTranslationSettings.ids==[41,41,92,92])
 print("7 footer scope/account identity/weak ownership checks passed")
}}
'''


def editor(source):
    text=(source/S).read_text();caller=(source/Q).read_text()
    assert '    final class Node: ASDisplayNode {' in text
    method=block(text,'        func endCaptionEditing() -> Bool {')
    update=block(text,'        private func updateIsEditingCaption(')
    route=block(caller,'    private func nagramiXPresentRoundQuality(')
    assert route.count('self.endCaptionEditing()')==1
    storage='\n'.join(next(l for l in text.splitlines() if l.strip().startswith(prefix)) for prefix in ['private(set) var captionPanelView:','private(set) var isEditingCaption ='])
    provider='''import Foundation
enum Curve {case easeInOut}
enum ContainedViewLayoutTransition {case animated(duration:Double,curve:Curve)}
final class TGCaptionPanelView {var allowed:Bool;var calls=0;init(_ allowed:Bool){self.allowed=allowed};func dismissInput()->Bool{calls+=1;return allowed}}
final class ChatMediaEditorScreen {
 final class Node {
'''+storage+'''
  var observations:[Bool]=[];var layouts=0
  init(editing:Bool,panel:TGCaptionPanelView?){isEditingCaption=editing;captionPanelView=panel}
  func captionEditingUpdated(_ value:Bool){observations.append(value)}
  func requestLayout(transition:ContainedViewLayoutTransition){layouts+=1}
'''+method+'\n'+update+'''
 }
}
'''
    consumer='''import Foundation
// Separate source file, as in the real quality extension. Rendering is outside
// this scope probe; the actual gate call must reach the actual producer above.
extension ChatMediaEditorScreen.Node {
 func fixtureRoundQualityCaptionGate()->Bool {return self.endCaptionEditing()}
}
@main enum CaptionScopeChecks {static func main(){
 let panel=TGCaptionPanelView(false)
 let node=ChatMediaEditorScreen.Node(editing:true,panel:panel)
 precondition(!node.fixtureRoundQualityCaptionGate())
 precondition(node.isEditingCaption && node.layouts==0 && node.observations.isEmpty && panel.calls==1)
 panel.allowed=true
 precondition(node.fixtureRoundQualityCaptionGate())
 precondition(!node.isEditingCaption && node.layouts==1 && node.observations==[false] && panel.calls==2)
 precondition(node.fixtureRoundQualityCaptionGate() && panel.calls==2 && node.layouts==1)
 let idle=ChatMediaEditorScreen.Node(editing:false,panel:TGCaptionPanelView(false))
 precondition(idle.fixtureRoundQualityCaptionGate() && idle.captionPanelView!.calls==0 && idle.layouts==0)
 let missing=ChatMediaEditorScreen.Node(editing:true,panel:nil)
 precondition(missing.fixtureRoundQualityCaptionGate() && !missing.isEditingCaption && missing.observations==[false])
 print("7 actual caption gate/update checks across separate Swift files passed")
}}
'''
    return provider,consumer


def check(source,swiftc,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    f=footer(source);a,b=editor(source);runs=[]
    assert f.count('configuration(accountId: context.account.id.int64)')==1
    assert a.count('        func endCaptionEditing() -> Bool {')==1
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        common=[str(swiftc),'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',str(folder/'cache'),*flags]
        for name,parts in [('footer',[f]),('caption',[a,b])]:
            paths=[]
            for index,code in enumerate(parts):
                path=folder/f'{name}{index}.swift';path.write_text(code);paths.append(str(path))
            binary=folder/f'{name}-{mode}'
            compiled=subprocess.run(common+paths+['-o',str(binary)],capture_output=True,text=True,timeout=180)
            assert compiled.returncode==0,compiled.stdout+compiled.stderr
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
            assert result.returncode==0,result.stdout+result.stderr
            runs.append({'name':name,'mode':mode,'exit_code':result.returncode,'output':result.stdout.strip()})
        for name,code,needle,other in [
          ('original218-optional-self',f.replace('configuration(accountId: context.account.id.int64)','configuration(accountId: self.context.account.id.int64)',1),"must be unwrapped to refer to member 'context'",None),
          ('original218-private-caption',a.replace('        func endCaptionEditing() -> Bool {','        private func endCaptionEditing() -> Bool {',1),"'endCaptionEditing' is inaccessible due to 'private' protection level",b),
        ]:
            path=folder/(name+'.swift');path.write_text(code);paths=[str(path)]
            if other:
                extra=folder/(name+'-caller.swift');extra.write_text(other);paths.append(str(extra))
            result=subprocess.run(common+['-typecheck',*paths],capture_output=True,text=True,timeout=180)
            assert result.returncode!=0 and needle in result.stderr and ('endCaptionEditing' in result.stderr if other else 'context' in result.stderr),result.stdout+result.stderr
            runs.append({'name':name,'mode':mode,'original218_rejected':True,'diagnostic':result.stderr.strip()})
    return {'executions':runs,'scope':'Actual changed footer expression in weak-self closure with native local context. Actual caption declaration/body and private update body compiled with caller in a separate Swift file. Account configuration/menu, UIKit/input panel/layout graph are explicit recording boundaries. Both original218 compiler defects must be rejected; no warning suppression.','full_application_sdk':'not_run','physical_iphone':'pending'}

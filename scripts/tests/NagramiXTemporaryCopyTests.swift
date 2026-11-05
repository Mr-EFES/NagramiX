@main struct TemporaryCopyTests {
 static func main() throws {
  var checks=0
  func check(_ value:@autoclosure ()->Bool,_ label:String){precondition(value(),label);checks+=1}
  let keys=["nagramix.messages.saveTemporaryMessages","nagramix.messages.replayViewOnce"]
  func enabled(_ b:Bool){keys.forEach{UserDefaults.standard.set(b,forKey:$0)}}
  defer{keys.forEach{UserDefaults.standard.removeObject(forKey:$0)}}
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
  defer{try? FileManager.default.removeItem(at:root)}
  let box=MediaBox(), account=Account(box), bytes=Data([1,2,3,4])
  NagramiXPrivacySettings.current.bypassScreenshots=false
  var messages:[Message]=[]
  for kind in 0..<4 {
   let name="media-\(kind)", path=root.appendingPathComponent("media-\(kind)")
   try bytes.write(to:path);box.paths[name]=path.path;box.complete.insert(name)
   var m=Message();m.id.value=kind+1;m.text="";m.flags=[.Incoming];m.protected=true;m.containsSecretMedia=true;m.minAutoremoveOrClearTimeout=viewOnceTimeout;m.groupingKey=777
   if kind==3 {m.media=[TelegramMediaImage(representations:[TelegramMediaImageRepresentation(dimensions:Dimensions(width:50,height:50),resource:CloudResource(name))])]}
   else {m.media=[TelegramMediaFile(resource:CloudResource(name),size:4,attributes:[kind==0 ? "voice" : kind==1 ? "round" : "video"])]}
   enabled(false);check(!nagramiXCanCopyMessagesAsNew([m]),"OFF hides incoming one-shot copying")
   enabled(true);check(nagramiXCanCopyMessagesAsNew([m]),"Temporary ON grants four kinds independently of Free Content")
   let result=nagramiXCopyMessagesAsNew([m],account:account)!
   check(result.count==1,"One complete payload per media")
   check(!result[0].attributes.contains{$0 is AutoremoveTimeoutMessageAttribute},"A retained incoming copy carries no consumed timer")
   if case .standalone?=result[0].mediaReference{checks+=1}else{preconditionFailure("No stale native source reference")}
   var retained=m;retained.containsSecretMedia=false;retained.minAutoremoveOrClearTimeout=nil;retained.protected=false;retained.attributes=[NagramiXArchivedMessageAttribute(isTemporary:true)]
   enabled(false);NagramiXPrivacySettings.current.bypassScreenshots=true
   check(!nagramiXCanCopyMessagesAsNew([retained]),"Free Content does not bypass disabled temporary policy")
   NagramiXPrivacySettings.current.bypassScreenshots=false;enabled(true)
   check(nagramiXCanCopyMessagesAsNew([retained]),"Retained temporary independent of Free Content")
   messages.append(m)
  }
  let batch=nagramiXPrepareRecipientCopies(messages,account:account,recipientCount:2)!
  check(batch.recipientMessages.count==2,"Prepare every recipient before enqueue")
  for list in batch.recipientMessages{check(list.count==4,"All four attachments preserved");check(Set(list.compactMap{$0.localGroupingKey}).count==1,"Album stays grouped")}
  check(batch.recipientMessages[0][0].localGroupingKey != batch.recipientMessages[1][0].localGroupingKey,"Recipient groups isolated")
  var round=messages[1];round.text="Юра 😀:\n";round.groupingKey=nil
  let repost=nagramiXCopyMessagesAsNew([round],account:account)!
  check(repost.count==2 && repost[0].text==round.text && repost[0].mediaReference==nil,"Author signature visible beside round video")
  check(repost[1].text.isEmpty && repost[1].mediaReference != nil,"Round video follows signature without invisible caption")
  var unavailable=messages[0];unavailable.media=[TelegramMediaFile(resource:CloudResource("absent"),attributes:["voice"])]
  check(nagramiXCopyMessagesAsNew([messages[0],unavailable],account:account)==nil,"Missing bytes fail the complete selection")
  enabled(false);check(nagramiXPrepareRecipientCopies(messages,account:account,recipientCount:2)==nil,"OFF blocks preparation before enqueue")
  print("PASS: \(checks) temporary media copy checks")
 }
}

  // The source server ID may already be gone; these actions use retained media.
  enabled(true)
  for (index, original) in messages.enumerated() {
   var original=original
   original.author=TestUser(id:PeerId(),name:"Юра 😀")
   original.text="ab";original.attributes=[NagramiXArchivedMessageAttribute(isTemporary:true),TextEntitiesMessageAttribute(entities:[Entity(value:"bold")])]
   let authored=authoredTemporaryCopies([original])[0]
   let prefix="Юра 😀:\n"
   check(authored.text==prefix+original.text,"Original author included for each temporary media kind")
   let entity=(authored.attributes.first{$0 is TextEntitiesMessageAttribute} as! TextEntitiesMessageAttribute).entities[0]
   check(entity.range==(prefix.utf16.count..<(prefix.utf16.count+2)),"Author prefix preserves UTF-16 entity offsets")
   check(authored.media.count==1 && authored.id==original.id,"Author mapping retains original media identity for archive lookup")
   let copied=nagramiXCopyMessagesAsNew([authored],account:account)!
   check(copied.count==(index==1 ? 2:1),"All temporary media types use the complete new-copy sender")
   check(copied[0].text==authored.text,"Author remains visible, including beside round video")
   let anonymous=nagramiXCopyMessagesAsNew([original],account:account)!
   check(anonymous[0].text=="ab","Ordinary forward/broadcast does not add an author")
   let reply=TemporaryReplyHarness();reply.reply([original])
   check(!reply.usedServerReply && reply.interfaceInteraction.state.inputText.string.contains("Юра 😀"),"Deleted temporary reply uses a local author quote instead of missing server ID")
   let live=TemporaryReplyHarness();live.context.account.nagramiXMessageArchive.deleted=false;live.reply([original])
   check(live.usedServerReply,"Live temporary original retains native reply routing")
   if index < 2 {
    var outgoing=original;outgoing.flags=[];outgoing.author=TestUser(id:account.peerId,name:"Юра 😀");outgoing.id.peerId=PeerId(value:200)
    check(!outgoing.nagramiXAllowsOwnViewOnceCopy(accountPeerId:account.peerId),"Temporary ON routes own recordings through full retained-copy actions")
    let ownCopies=nagramiXPrepareRecipientCopies([outgoing],account:account,recipientCount:2)!
    check(ownCopies.recipientMessages.flatMap{$0}.allSatisfy{!$0.attributes.contains{$0 is AutoremoveTimeoutMessageAttribute}},"Own retained copies also receive no new one-shot timer")
    enabled(false)
    check(outgoing.nagramiXAllowsOwnViewOnceCopy(accountPeerId:account.peerId),"Temporary OFF preserves the existing restricted own-recording exception")
    enabled(true)
   }
   let broadcasts=nagramiXPrepareRecipientCopies([original],account:account,recipientCount:2)!
   check(broadcasts.recipientMessages.count==2 && broadcasts.recipientMessages.allSatisfy{!$0.isEmpty},"Saved temporary payload prepared for all recipients")
   check(broadcasts.recipientMessages.flatMap{$0}.allSatisfy{!$0.attributes.contains{$0 is AutoremoveTimeoutMessageAttribute || $0 is AutoclearTimeoutMessageAttribute}},"New copies do not inherit the consumed original timer")
  }

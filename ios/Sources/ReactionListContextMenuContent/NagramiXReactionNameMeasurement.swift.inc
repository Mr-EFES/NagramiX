// Match the sizes returned by the existing EmojiStatusComponent without
// creating offscreen animated status views or fetching emoji while measuring.
private func nagramiXReactionCredibilityInset(peer: EnginePeer, presentationData: PresentationData, premiumDisabled: Bool) -> CGFloat {
    let badgeWidth: CGFloat
    if peer.isScam || peer.isFake {
        let text = peer.isScam ? presentationData.strings.Message_ScamAccount : presentationData.strings.Message_FakeAccount
        let title = NSAttributedString(string: text.uppercased(), font: Font.bold(10.0), textColor: presentationData.theme.chat.message.incoming.scamColor, paragraphAlignment: .center)
        badgeWidth = floor(title.boundingRect(with: CGSize(width: 100.0, height: 16.0), options: .usesLineFragmentOrigin, context: nil).width) + 11.0
    } else if peer.emojiStatus != nil {
        badgeWidth = 24.0
    } else if peer.isVerified {
        badgeWidth = UIImage(bundleImageName: "Chat List/PeerVerifiedIconBackground")?.size.width ?? 0.0
    } else if peer.isPremium && !premiumDisabled {
        badgeWidth = UIImage(bundleImageName: "Chat/Input/Media/EntityInputPremiumIcon")?.size.aspectFilled(CGSize(width: 24.0, height: 24.0)).width ?? 0.0
    } else {
        return 0.0
    }
    return badgeWidth > 0.0 ? 3.0 + badgeWidth : 0.0
}

private func nagramiXReactionNameWidth(width: CGFloat, hasReaction: Bool, credibilityInset: CGFloat) -> CGFloat {
    // Existing avatar inset/size/spacing, trailing inset and reaction column.
    return max(1.0, width - 20.0 - 30.0 - 10.0 - 16.0 - credibilityInset - (hasReaction ? 32.0 : 0.0))
}

public import TelegramCore

// The constructor shape is pinned to AccountContext.swift in Telegram 13.1.2.
public struct ChatAvailableMessageActionOptions: OptionSet {
    public let rawValue: Int
    public init(rawValue: Int) { self.rawValue = rawValue }
    public static let deleteLocally = Self(rawValue: 1)
}
public struct ChatAvailableMessageActions {
    public init(options: ChatAvailableMessageActionOptions, banAuthor: EnginePeer?, banAuthors: [EnginePeer], disableDelete: Bool, isCopyProtected: Bool, setTag: Bool, editTags: Set<MessageReaction.Reaction>) {}
}

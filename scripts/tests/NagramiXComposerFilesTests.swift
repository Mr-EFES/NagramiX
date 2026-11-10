private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ name: String) {
    checks += 1
    if !value() { print(name); exit(91) }
}
private func body(_ text: String) -> ChatInputBlock { .paragraph(ChatInputParagraph(runs: [ChatInputRun(text: text)])) }
private func file(_ id: Int64, _ type: String = "document") -> TelegramMediaFile {
    let result = TelegramMediaFile(id)
    result.isVideo = type == "video" || type == "round"
    result.isInstantVideo = type == "round"
    result.isMusic = type == "music"
    result.isVoice = type == "voice"
    result.dimensions = PixelDimensions(width: 640, height: 480)
    result.partialReference = id + 100
    return result
}
private func mediaBlock(_ file: TelegramMediaFile) -> ChatInputBlock { .media(ChatInputMedia(media: file, kind: .document, naturalSize: .init(width: 1, height: 1))) }

@main struct ComposerFileTests {
    static func main() {
        let document = file(1)
        let initial = ChatTextInputState(content: ChatInputContent(blocks: [body("Пост 📎")]), selectionRange: 5..<5)
        let richState = ChatTextInputState(content: ChatInputContent(blocks: [
            .paragraph(ChatInputParagraph(style: .heading1, runs: [ChatInputRun(text: "Заголовок", attributes: .init(bold: true))])),
            body("Подпись"),
        ]), selectionRange: 2..<4)
        let draft = nagramiXComposerFileDraft(initial, files: [document], caption: nil, initialState: nil)!
        check(draft.content.blocks.count == 2, "all files attached")
        let richDraft = nagramiXComposerFileDraft(richState, files: [document], caption: nil, initialState: nil)!
        check(Array(richDraft.content.blocks.prefix(2)) == richState.content.blocks, "structure preserved")
        check(richDraft.selection == richState.selection, "caret preserved")
        check(richState.content.blocks.count == 2, "input immutable")
        check(nagramiXComposerFileDraft(initial, files: [], caption: nil, initialState: nil) == nil, "cancel unchanged")
        let edited = nagramiXComposerFileDraft(initial, files: [document], caption: NSAttributedString(string: "Новый текст"), initialState: initial)!
        check(edited.content.plainText == "Новый текст", "picker caption applied")
        check(nagramiXComposerFileDraft(richState, files: [document], caption: NSAttributedString(string: "Старый текст"), initialState: initial) == nil, "stale caption rejected")
        check(nagramiXComposerFileDraft(richState, files: [document], caption: initial.inputText, initialState: initial)!.content.blocks.first == richState.content.blocks.first, "unchanged picker caption preserves latest draft")
        let repeated = nagramiXComposerFileDraft(draft, files: [document], caption: nil, initialState: nil)!
        check(repeated.content.allMedia.count == 2, "second attachment retained")
        let recap = nagramiXComposerFileDraft(draft, files: [file(2)], caption: NSAttributedString(string: "Заменённая подпись"), initialState: draft)!
        check(recap.content.allMedia.count == 2, "caption edit preserves existing file")

        let controller = ChatControllerImpl(initial)
        check(controller.nagramiXAttachFilesToComposer([.message(origin: 812, media: document)]), "recent file accepted")
        check(controller.chatDisplayNode.sends.isEmpty, "selection never sends")
        check(controller.presentationInterfaceState.interfaceState.composeInputState.content.allMedia.count == 1, "file in unsent draft")
        guard case let .file(staged) = controller.presentationInterfaceState.interfaceState.composeInputState.content.allMedia[0] else { fatalError() }
        check(staged.partialReference == 812, "recent origin preserved")
        check(staged.payload == document.payload && staged.fileId == document.fileId, "recent payload preserved")
        check(controller.presentationInterfaceState.interfaceState.reply == 47, "draft reply not cleared")
        check(!controller.nagramiXAttachFilesToComposer([]), "cancel rejected")
        let previous = controller.presentationInterfaceState
        check(!controller.nagramiXAttachFilesToComposer([.standalone(media: TelegramMediaImage())]), "unsupported not partially attached")
        check(controller.presentationInterfaceState.interfaceState.composeInputState == previous.interfaceState.composeInputState, "failure draft preserved")
        controller.presentationInterfaceState.interfaceState.editMessage = true
        check(!controller.nagramiXAttachFilesToComposer([.standalone(media: document)]), "stale edit never hijacked")
        check(controller.chatDisplayNode.sends.isEmpty, "failure never sends")
        controller.presentationInterfaceState.interfaceState.editMessage = nil
        check(controller.nagramiXAttachFilesToComposer([.standalone(media: document)], silentPosting: true, scheduleTime: 91), "explicit picker mode accepted")
        check(controller.chatDisplayNode.sends.count == 1, "explicit mode send once")
        check(controller.chatDisplayNode.sends[0].0 == true && controller.chatDisplayNode.sends[0].1 == 91, "schedule and silence retained")

        let types = ["document", "video", "round", "music", "voice", "pdf", "ipa", "zip", "image-as-file", "unknown"]
        for (i, type) in types.enumerated() {
            let attached = file(Int64(i + 10), type)
            attached.mimeType = type
            let draft = nagramiXComposerFileDraft(initial, files: [attached], caption: nil, initialState: nil)!
            check(draft.content.allMedia.count == 1, "all files attached")
            guard case let .media(block) = draft.content.blocks.last else { fatalError() }
            check((block.media as? TelegramMediaFile) === attached, "resource identity preserved")
            check((block.media as? TelegramMediaFile)?.partialReference == attached.partialReference, "cloud origin retained")
            check(block.kind == (attached.isVideo ? .video : (attached.isMusic || attached.isVoice ? .audio : .document)), "same expanded kind")
            let captionFiles = nagramiXComposerCaptionFiles(draft.content, maxCaptionLength: 1024, sendWithoutFormatting: false)
            check(type == "round" ? captionFiles == nil : captionFiles?.count == 1, "ordinary caption no rich gate")
            let reply = EngineMessageReplySubject(id: 91)
            let messages = nagramiXComposerFileMessages(files: [attached], caption: initial.inputText, inlineStickers: [MediaId(99): document], threadId: 17, replyTo: reply)
            check(messages.count == 1, "one file one post")
            guard case let .message(text, attributes, stickers, reference, thread, replyValue, _, group, _, _) = messages[0] else { fatalError() }
            check(text == initial.inputText.string, "caption retained")
            check((attributes.first as? TextEntitiesMessageAttribute)?.entities == [.init(marker: "preserved")], "entities retained")
            check(stickers[MediaId(99)] === document, "custom emoji files retained")
            check(thread == 17, "thread retained")
            check(replyValue == reply, "reply retained")
            check(group == nil, "single file no album")
            guard case let .standalone(media)? = reference else { fatalError() }
            check((media as? TelegramMediaFile) === attached, "payload retained")
        }
        for limit in [0, 1, 1024, 2048, 4096, 10000] {
            for length in [limit, limit + 1, limit + 4096] {
                let state = ChatTextInputState(content: ChatInputContent(blocks: [body(String(repeating: "Т", count: length))]), selectionRange: 0..<0)
                let draft = nagramiXComposerFileDraft(state, files: [document], caption: nil, initialState: nil)!
                check(draft.content.plainText == state.content.plainText, "long text not truncated")
                let normal = nagramiXComposerCaptionFiles(draft.content, maxCaptionLength: min(4096, limit), sendWithoutFormatting: false)
                check((normal != nil) == (length <= min(limit, 4096)), "long caption stays rich")
                check(chatComposerSendRoute(content: draft.content, isNewMessage: true, sendWithoutFormatting: false) == .rich, "rich route preserves long media")
            }
        }
        check(nagramiXComposerCaptionFiles(richDraft.content, maxCaptionLength: 2048, sendWithoutFormatting: false) == nil, "headings keep rich route")
        check(nagramiXComposerCaptionFiles(richDraft.content, maxCaptionLength: 2048, sendWithoutFormatting: true)?.count == 1, "explicit flatten retains file")
        let unformatted = nagramiXComposerSendContent(richDraft.content, fallbackText: richDraft.inputText, sendWithoutFormatting: true)
        check(unformatted.allMedia.count == 1, "format removal retains files")
        check(unformatted.plainText == richDraft.content.plainText, "format removal retains text")
        check(nagramiXComposerCaptionFiles(unformatted, maxCaptionLength: 2048, sendWithoutFormatting: false)?.count == 1, "format removal ordinary caption")
        let untouched = nagramiXComposerSendContent(richDraft.content, fallbackText: richDraft.inputText, sendWithoutFormatting: false)
        check(untouched == richDraft.content, "normal send retains rich structure")
        let longStyled = ChatInputContent(blocks: [.paragraph(ChatInputParagraph(style: .heading1, runs: [ChatInputRun(text: String(repeating: "Я", count: 9000))])), mediaBlock(document)])
        let longUnformatted = nagramiXComposerSendContent(longStyled, fallbackText: NSAttributedString(string: longStyled.plainText), sendWithoutFormatting: true)
        check(longUnformatted.allMedia.count == 1 && longUnformatted.plainText == longStyled.plainText, "long format removal retains all content")
        guard case let .paragraph(plainParagraph) = longUnformatted.blocks.first else { fatalError() }
        check(plainParagraph.style == .body, "long format removal plain text")
        let nested = ChatInputContent(blocks: [.blockQuote(ChatInputBlockQuote(content: ChatInputContent(blocks: [mediaBlock(file(77))]), collapsed: false)), mediaBlock(document)])
        check(nagramiXComposerCaptionFiles(nested, maxCaptionLength: 2048, sendWithoutFormatting: true) == nil, "nested attachment not dropped")
        check(nagramiXComposerSendContent(nested, fallbackText: NSAttributedString(string: nested.plainText), sendWithoutFormatting: true).allMedia.count == 2, "nested fallback retains files")
        let interleaved = ChatInputContent(blocks: [body("До"), mediaBlock(document), body("После")])
        check(nagramiXComposerCaptionFiles(interleaved, maxCaptionLength: 2048, sendWithoutFormatting: false) == nil, "inline order stays rich")
        var special = ChatInputMedia(media: document, kind: .document, naturalSize: .init(width: 1, height: 1))
        special.items[0].isSpoiler = true
        check(nagramiXComposerCaptionFiles(.init(blocks: [.media(special)]), maxCaptionLength: 2048, sendWithoutFormatting: false) == nil, "spoiler stays rich")
        special.items[0].isSpoiler = false
        special.caption = [ChatInputRun(text: "Подпись внутри")]
        check(nagramiXComposerCaptionFiles(.init(blocks: [.media(special)]), maxCaptionLength: 2048, sendWithoutFormatting: false) == nil, "inline caption stays rich")
        for count in [1, 2, 10, 11, 20, 21] {
            for type in ["document", "music", "voice"] {
                let files = (0..<count).map { file(Int64($0), type) }
                let messages = nagramiXComposerFileMessages(files: files, caption: initial.inputText, inlineStickers: [:], threadId: 3, replyTo: nil)
                check(messages.count == count, "no separate text enqueue")
                var groups: [Int64: Int] = [:]
                var nonemptyCaptions = 0
                for (i, message) in messages.enumerated() {
                    guard case let .message(text, _, _, reference, thread, _, _, group, _, _) = message else { fatalError() }
                    check(thread == 3, "album thread retained")
                    if !text.isEmpty { nonemptyCaptions += 1; check(i == count - 1, "caption with last file") }
                    if let group { groups[group, default: 0] += 1 }
                    guard case let .standalone(media)? = reference else { fatalError() }
                    check((media as? TelegramMediaFile) === files[i], "album order retained")
                }
                check(nonemptyCaptions == 1, "caption not duplicated")
                check(groups.values.allSatisfy { $0 <= 10 }, "album limit ten")
                check(type != "voice" || groups.isEmpty, "voice not invalid album")
            }
        }
        print("\(checks) production composer-file checks passed")
    }
}

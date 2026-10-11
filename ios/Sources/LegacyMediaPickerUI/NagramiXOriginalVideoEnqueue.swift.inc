                        case let .originalVideo(file, caption):
                            var attributes: [EngineMessage.Attribute] = []
                            if item.spoiler == true { attributes.append(MediaSpoilerMessageAttribute()) }
                            let text = trimChatInputText(convertMarkdownToAttributes(caption ?? NSAttributedString()))
                            let entities = generateTextEntities(text.string, enabledTypes: .all, currentEntities: generateChatInputTextEntities(text))
                            if !entities.isEmpty {
                                attributes.append(TextEntitiesMessageAttribute(entities: entities))
                            }

                            var bubbleUpEmojiOrStickersetsById: [Int64: EngineItemCollectionId] = [:]
                            text.enumerateAttribute(ChatTextInputAttributes.customEmoji, in: NSRange(location: 0, length: text.length), using: { value, _, _ in
                                if let value = value as? ChatTextInputTextCustomEmojiAttribute {
                                    if let file = value.file {
                                        if let packId = value.interactivelySelectedFromPackId {
                                            bubbleUpEmojiOrStickersetsById[file.fileId.id] = packId
                                        }
                                    }
                                }
                            })
                            var bubbleUpEmojiOrStickersets: [EngineItemCollectionId] = []
                            for entity in entities {
                                if case let .CustomEmoji(_, fileId) = entity.type {
                                    if let packId = bubbleUpEmojiOrStickersetsById[fileId] {
                                        if !bubbleUpEmojiOrStickersets.contains(packId) {
                                            bubbleUpEmojiOrStickersets.append(packId)
                                        }
                                    }
                                }
                            }

                            messages.append(LegacyAssetPickerEnqueueMessage(message: .message(text: text.string, attributes: attributes, inlineStickers: [:], mediaReference: .standalone(media: file), threadId: nil, replyToMessageId: nil, replyToStoryId: nil, localGroupingKey: item.groupedId, correlationId: nil, bubbleUpEmojiOrStickersets: bubbleUpEmojiOrStickersets), uniqueId: item.uniqueId, isFile: !file.isVideo))

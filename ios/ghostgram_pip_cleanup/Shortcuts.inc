        if self.hasPictureInPicture {
            keyShortcuts.append(
                KeyShortcut(
                    title: strings.KeyCommand_SwitchToPIP,
                    input: "P",
                    modifiers: [.command],
                    action: { [weak self] in
                        self?.pictureInPictureButtonPressed()
                    }
                )
            )
        }

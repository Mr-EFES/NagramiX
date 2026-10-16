    if displaySounds {
        let defaultSound = isStories == true ? state.defaultStoriesSound : state.defaultSound
        let modernSounds = builtinNotificationSounds.filter {
            if case let .cloud(fileId) = $0 { return CloudSoundBuiltinCategory(id: fileId) == .modern }
            return false
        }
        let classicSounds = builtinNotificationSounds.filter {
            if case let .cloud(fileId) = $0 { return CloudSoundBuiltinCategory(id: fileId) == .classic }
            return false
        }

        entries.append(.cloudHeader(index: index, text: presentationData.strings.Notifications_TelegramTones))
        index += 1

        index = 1000
        if let notificationSoundList = notificationSoundList {
            let cloudSounds = notificationSoundList.sounds.filter({ CloudSoundBuiltinCategory(id: $0.file.fileId.id) == nil })
            for listSound in cloudSounds {
                let sound: PeerMessageSound = .cloud(fileId: listSound.file.fileId.id)
                if state.removedSounds.contains(where: { $0.id == sound.id }) {
                    continue
                }
                entries.append(.sound(index: index, section: .soundCloud, theme: presentationData.theme, text: localizedPeerNotificationSoundString(strings: presentationData.strings, notificationSoundList: notificationSoundList, sound: sound), sound: sound, selected: selectedSound.id == sound.id, canBeDeleted: true))
                index += 1
            }
        }

        index = 2000
        entries.append(.uploadSound(index: index, text: presentationData.strings.Notifications_UploadSound))
        index += 1
        entries.append(.cloudInfo(index: index, text: presentationData.strings.Notifications_MessageSoundInfo))
        index += 1
        entries.append(.soundModernHeader(index: index, theme: presentationData.theme, title: presentationData.strings.Notifications_AlertTones))

        index = 3000
        entries.append(.default(index: index, section: .soundModern, theme: presentationData.theme, text: localizedPeerNotificationSoundString(strings: presentationData.strings, notificationSoundList: notificationSoundList, sound: .default, default: defaultSound), selected: selectedSound == .default))
        index += 1
        entries.append(.none(index: index, section: .soundModern, theme: presentationData.theme, text: localizedPeerNotificationSoundString(strings: presentationData.strings, notificationSoundList: notificationSoundList, sound: .none), selected: selectedSound == .none))
        index += 1

        for sound in modernSounds {
            entries.append(.sound(index: index, section: .soundModern, theme: presentationData.theme, text: localizedPeerNotificationSoundString(strings: presentationData.strings, notificationSoundList: notificationSoundList, sound: sound), sound: sound, selected: sound.id == selectedSound.id, canBeDeleted: false))
            index += 1
        }
        entries.append(.soundClassicHeader(index: index, theme: presentationData.theme, title: presentationData.strings.Notifications_ClassicTones))
        index += 1
        for sound in classicSounds {
            entries.append(.sound(index: index, section: .soundClassic, theme: presentationData.theme, text: localizedPeerNotificationSoundString(strings: presentationData.strings, notificationSoundList: notificationSoundList, sound: sound), sound: sound, selected: sound.id == selectedSound.id, canBeDeleted: false))
            index += 1
        }
    }

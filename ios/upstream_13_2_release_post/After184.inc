import Foundation
import NagramiXMediaSettings
import AppBundle
import PresentationStrings

public typealias PresentationStrings = _PresentationStrings

public extension PresentationStrings {
    typealias FormattedString = _FormattedString
    typealias Component = _PresentationStringsComponent
}

public extension _FormattedString {
    typealias Range = _FormattedStringRange

    var _tuple: (String, [(Int, NSRange)]) {
        return (self.string, self.ranges.map { item -> (Int, NSRange) in
            return (item.index, item.range)
        })
    }
}

public func formatWithArgumentRanges(_ value: String, _ ranges: [(Int, NSRange)], _ arguments: [String]) -> (String, [(Int, NSRange)]) {
    let string = value as NSString

    var resultingRanges: [(Int, NSRange)] = []

    var currentLocation = 0

    let result = NSMutableString()
    for (index, range) in ranges {
        if currentLocation < range.location {
            result.append(string.substring(with: NSRange(location: currentLocation, length: range.location - currentLocation)))
        }
        resultingRanges.append((index, NSRange(location: result.length, length: (arguments[index] as NSString).length)))
        result.append(arguments[index])
        currentLocation = range.location + range.length
    }
    if currentLocation != string.length {
        result.append(string.substring(with: NSRange(location: currentLocation, length: string.length - currentLocation)))
    }
    return (result as String, resultingRanges)
}

let nagramiXFullRussianControlLabels: [String: String] = [
    "Common.Edit": "Изменить",
    "Calls.Missed": "Пропущенные",
    "Conversation.Unmute": "Включить звук",
    "ChatList.Unmute": "Включить звук",
    "Conversation.TitleUnmute": "Включить звук",
    "BlockedUsers.Unblock": "Разблокировать",
    "Settings.EditPhoto": "Изменить",
    "Settings.EditVideo": "Изменить",
    "Settings.SaveEditedPhotos": "Сохранять отредактированные фотографии",
    "NetworkUsageSettings.Cellular": "Мобильная сеть",
    "AutoDownloadSettings.CellularTitle": "Через мобильную сеть",
    "AutoDownloadSettings.OnForContacts": "Включено для контактов",
    "UserInfo.NotificationsEnabled": "Включены",
    "UserInfo.NotificationsDisabled": "Выключены",
    "UserInfo.NotificationsDefaultEnabled": "По умолчанию (включены)",
    "UserInfo.NotificationsDefaultDisabled": "По умолчанию (выключены)",
    "Camera.FlashOff": "Выключена",
    "Camera.FlashOn": "Включена",
    "VoiceChat.Unmute": "Включить звук",
    "VoiceChat.Mute": "Выключить микрофон",
    "VoiceChat.UnmuteForMe": "Включить звук для меня",
    "VoiceChat.MuteForMe": "Выключить звук для меня",
    "VoiceChat.MuteShort": "Выключить звук",
    "Notifications.On": "Включены",
    "Notifications.Off": "Выключены",
    "PeerInfo.MuteForever": "Выключить уведомления",
    "ChatList.ContextMuteAll": "Выключить уведомления",
    "ChatList.ContextUnmuteAll": "Включить уведомления",
    "Settings.AutosaveMediaOn": "Включено",
    "Settings.PowerSavingOn": "Включено",
    "Settings.PowerSavingOff": "Выключено",
    "PowerSaving.BatteryLevelLimit.Off": "Выключено",
    "PowerSaving.BatteryLevelLimit.On": "Включено",
    "PowerSavingScreen.ToggleHeaderOn": "РЕЖИМ ЭНЕРГОСБЕРЕЖЕНИЯ (ВКЛЮЧЁН)",
    "PowerSavingScreen.ToggleHeaderOff": "РЕЖИМ ЭНЕРГОСБЕРЕЖЕНИЯ (ВЫКЛЮЧЕН)",
    "ArchiveSettings.UnmutedChatsHeader": "ЧАТЫ С ВКЛЮЧЁННЫМИ УВЕДОМЛЕНИЯМИ",
    "Story.Editor.Tool.Saturation": "Насыщенность",
    "PeerInfo.AllowChannelMessages.Free": "Бесплатно",
    "PeerInfo.AllowChannelMessages.Off": "Выключено",
    "MediaPicker.LivePhoto.LiveOff": "Live выключено",
    "Settings.ChatAutomationOff": "Выключено",
    "WelcomeMessages.Off": "Выключено",
    "PrivacySettings.PasscodeOn": "Включён",
    "Contacts.AccessDeniedHelpON": "ВКЛЮЧЕНО",
    "Watch.UserInfo.Unmute": "Включить звук",
    "Camera.FlashAuto": "Автоматически",
    "SocksProxySetup.UseForCalls": "Использовать прокси для звонков",
    "ContactInfo.PhoneLabelMobile": "Мобильный",
    "Profile.Username": "Имя пользователя",
    "Profile.About": "О себе",
    "ContactInfo.BirthdayLabel": "День рождения",
    "UserInfo.Birthday": "День рождения",
    "UserInfo.BirthdayToday": "День рождения сегодня",
]

let nagramiXDefaultRussianDictionary: [String: String] = {
    var dictionary = NSDictionary(contentsOf: URL(fileURLWithPath: getAppBundle().path(forResource: "Localizable", ofType: "strings", inDirectory: nil, forLocalization: "ru")!)) as! [String: String]
    dictionary.merge(nagramiXFullRussianControlLabels, uniquingKeysWith: { _, fullLabel in fullLabel })
    return dictionary
}()

public let defaultPresentationStrings = PresentationStrings(primaryComponent: PresentationStrings.Component(languageCode: "ru", localizedName: "Русский", pluralizationRulesCode: nil, dict: nagramiXDefaultRussianDictionary), secondaryComponent: nil, groupingSeparator: "")

public func dataSizeString(_ size: Int, forceDecimal: Bool = false, compact: Bool = false, formatting: DataSizeStringFormatting) -> String {
    return dataSizeString(Int64(size), forceDecimal: forceDecimal, compact: compact, formatting: formatting)
}

public struct DataSizeStringFormatting {
    let decimalSeparator: String
    let byte: (String) -> PresentationStrings.FormattedString
    let kilobyte: (String) -> PresentationStrings.FormattedString
    let megabyte: (String) -> PresentationStrings.FormattedString
    let gigabyte: (String) -> PresentationStrings.FormattedString

    public init(
        decimalSeparator: String,
        byte: @escaping (String) -> PresentationStrings.FormattedString,
        kilobyte: @escaping (String) -> PresentationStrings.FormattedString,
        megabyte: @escaping (String) -> PresentationStrings.FormattedString,
        gigabyte: @escaping (String) -> PresentationStrings.FormattedString
    ) {
        self.decimalSeparator = decimalSeparator
        self.byte = byte
        self.kilobyte = kilobyte
        self.megabyte = megabyte
        self.gigabyte = gigabyte
    }
}

/// `compact` keeps a size short (at most three digits below 1000 GB) for a value that has to fit beside a long title,
/// as on Data and Storage's usage rows: see `compactDataSizeString`. `forceDecimal` takes precedence.
public func dataSizeString(_ size: Int64, forceDecimal: Bool = false, compact: Bool = false, formatting: DataSizeStringFormatting) -> String {
    if compact && !forceDecimal {
        return compactDataSizeString(size, formatting: formatting)
    }
    if size >= 1024 * 1024 * 1024 {
        let remainder = Int64((Double(size % (1024 * 1024 * 1024)) / (1024 * 1024 * 102.4)).rounded(.down))
        if remainder != 0 || forceDecimal {
            return formatting.gigabyte("\(size / (1024 * 1024 * 1024))\(formatting.decimalSeparator)\(remainder)").string
        } else {
            return formatting.gigabyte("\(size / (1024 * 1024 * 1024))").string
        }
    } else if size >= 1024 * 1024 {
        let remainder = Int64((Double(size % (1024 * 1024)) / (1024.0 * 102.4)).rounded(.down))
        if remainder != 0 || forceDecimal {
            return formatting.megabyte( "\(size / (1024 * 1024))\(formatting.decimalSeparator)\(remainder)").string
        } else {
            return formatting.megabyte("\(size / (1024 * 1024))").string
        }
    } else if size >= 1024 {
        let remainder = (size % (1024)) / (102)
        if remainder != 0 || forceDecimal {
            return formatting.kilobyte("\(size / 1024)\(formatting.decimalSeparator)\(remainder)").string
        } else {
            return formatting.kilobyte("\(size / 1024)").string
        }
    } else {
        return formatting.byte("\(size)").string
    }
}

/// KB and MB show a decimal only below 10 ("9,5 MB", "48 MB", "131 MB"), GB below 100 ("27,2 GB", "131 GB"), and from
/// 1000 units up a size shows in the next unit, rounded to one decimal ("1000 MB" is "1 GB"). Other decimals are rounded
/// down, as in the default format.
private func compactDataSizeString(_ size: Int64, formatting: DataSizeStringFormatting) -> String {
    let units: [(size: Int64, format: (String) -> PresentationStrings.FormattedString)] = [
        (1, formatting.byte),
        (1024, formatting.kilobyte),
        (1024 * 1024, formatting.megabyte),
        (1024 * 1024 * 1024, formatting.gigabyte)
    ]
    var index = 0
    while index + 1 < units.count && size >= units[index + 1].size {
        index += 1
    }
    let unit = units[index]
    let whole = size / unit.size
    if whole >= 1000 && index + 1 < units.count {
        let nextUnit = units[index + 1]
        let tenths = Int64((Double(size) / Double(nextUnit.size) * 10.0).rounded())
        if tenths % 10 == 0 {
            return nextUnit.format("\(tenths / 10)").string
        }
        return nextUnit.format("\(tenths / 10)\(formatting.decimalSeparator)\(tenths % 10)").string
    }
    let decimalBelow: Int64 = index == units.count - 1 ? 100 : 10
    let remainder = Int64((Double(size % unit.size) / (Double(unit.size) / 10.0)).rounded(.down))
    if index == 0 || whole >= decimalBelow || remainder == 0 {
        return unit.format("\(whole)").string
    }
    return unit.format("\(whole)\(formatting.decimalSeparator)\(remainder)").string
}

public func countString(_ count: Int64, forceDecimal: Bool = false) -> String {
    if !NagramiXNumberSettings.roundingEnabled {
        return NagramiXNumberSettings.fullCountString(count)
    }
    let decimalSeparator = "."
    if count >= 1000 * 1000 * 1000 {
        let remainder = Int64((Double(count % (1000 * 1000 * 1000)) / (1000 * 1000 * 100.0)).rounded(.down))
        if remainder != 0 || forceDecimal {
            return "\(count / (1000 * 1000 * 1000))\(decimalSeparator)\(remainder)T"
        } else {
            return "\(count / (1000 * 1000 * 1000))T"
        }
    } else if count >= 1000 * 1000 {
        let remainder = Int64((Double(count % (1000 * 1000)) / (1000.0 * 100.0)).rounded(.down))
        if remainder != 0 || forceDecimal {
            return "\(count / (1000 * 1000))\(decimalSeparator)\(remainder)M"
        } else {
            return "\(count / (1000 * 1000))M"
        }
    } else if count >= 1000 {
        let remainder = (count % (1000)) / (102)
        if remainder != 0 || forceDecimal {
            return "\(count / 1000)\(decimalSeparator)\(remainder)K"
        } else {
            return "\(count / 1000)K"
        }
    } else {
        return "\(count)"
    }
}

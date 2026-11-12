import Foundation

public enum NagramiXSnowHolidays {
    public enum Kind: String { case christmas, newYear, orthodoxChristmas, oldNewYear, chineseNewYear }
    public struct Window: Equatable {
        public let kind: Kind
        public let start: Date
        public let end: Date
    }

    public static func dayInterval(at date: Date, timeZone: TimeZone) -> DateInterval? {
        guard date.timeIntervalSinceReferenceDate.isFinite else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        return calendar.dateInterval(of: .day, for: date)
    }

    public static func window(at date: Date, timeZone: TimeZone) -> Window? {
        guard let day = self.dayInterval(at: date, timeZone: timeZone) else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = timeZone
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        guard let year = components.year, let month = components.month, let number = components.day else { return nil }
        if month == 12 && number == 25 { return Window(kind: .christmas, start: day.start, end: day.end) }
        if month == 1 && number == 7 { return Window(kind: .orthodoxChristmas, start: day.start, end: day.end) }
        if (month == 12 && number == 31) || (month == 1 && number == 1) {
            let endingYear = month == 12 ? year + 1 : year
            guard let start = calendar.date(from: DateComponents(year: endingYear - 1, month: 12, day: 31)),
                  let end = calendar.date(from: DateComponents(year: endingYear, month: 1, day: 2)) else { return nil }
            return Window(kind: .newYear, start: start, end: end)
        }
        if month == 1 && (number == 13 || number == 14) {
            guard let start = calendar.date(from: DateComponents(year: year, month: 1, day: 13)),
                  let end = calendar.date(from: DateComponents(year: year, month: 1, day: 15)) else { return nil }
            return Window(kind: .oldNewYear, start: start, end: end)
        }
        // Determine the Chinese holiday's civil Gregorian date in its calendar's
        // reference zone, then celebrate that date using the phone's local day.
        if month == 1 || month == 2, let referenceZone = TimeZone(identifier: "Asia/Shanghai") {
            var reference = Calendar(identifier: .gregorian)
            reference.timeZone = referenceZone
            if let noon = reference.date(from: DateComponents(year: year, month: month, day: number, hour: 12)) {
                var chinese = Calendar(identifier: .chinese)
                chinese.timeZone = referenceZone
                let lunar = chinese.dateComponents(in: referenceZone, from: noon)
                if lunar.month == 1 && lunar.day == 1 && lunar.isLeapMonth != true {
                    return Window(kind: .chineseNewYear, start: day.start, end: day.end)
                }
            }
        }
        return nil
    }

    public static func configuration(_ manual: NagramiXSnowConfiguration, during window: Window?) -> NagramiXSnowConfiguration {
        guard window != nil else { return manual }
        var result = manual
        result.enabled = true
        result.density = 75
        return result
    }
}

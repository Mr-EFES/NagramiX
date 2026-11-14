import Foundation
import UIKit

final class NagramiXSnowSchedule {
    typealias TimerFactory = (Date, @escaping () -> Void) -> Timer
    static let shared = NagramiXSnowSchedule()
    private let now: () -> Date
    private let timeZone: () -> TimeZone
    private let makeTimer: TimerFactory
    private var timer: Timer?
    private var observers: [NSObjectProtocol] = []
    private var started = false
    private var active = true

    init(now: @escaping () -> Date = { Date() }, timeZone: @escaping () -> TimeZone = { .autoupdatingCurrent }, makeTimer: @escaping TimerFactory = { date, action in
        let timer = Timer(fire: date, interval: 0.0, repeats: false) { _ in action() }
        RunLoop.main.add(timer, forMode: .common)
        return timer
    }) {
        self.now = now
        self.timeZone = timeZone
        self.makeTimer = makeTimer
    }

    func start() {
        guard !self.started else { return }
        self.started = true
        for name in [Notification.Name.NSCalendarDayChanged, .NSSystemTimeZoneDidChange, UIApplication.significantTimeChangeNotification, UIApplication.didBecomeActiveNotification, UIApplication.willResignActiveNotification] {
            self.observers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] note in
                guard let self else { return }
                if note.name == UIApplication.willResignActiveNotification {
                    self.active = false
                    self.timer?.invalidate()
                    self.timer = nil
                    return
                }
                if note.name == UIApplication.didBecomeActiveNotification { self.active = true }
                self.refresh()
            })
        }
        self.refresh()
    }

    private func refresh() {
        let date = self.now(), zone = self.timeZone()
        NagramiXSnowSettings.refreshSchedule(at: date, timeZone: zone)
        self.timer?.invalidate()
        self.timer = nil
        guard self.active, let day = NagramiXSnowHolidays.dayInterval(at: date, timeZone: zone) else { return }
        self.timer = self.makeTimer(day.end) { [weak self] in self?.refresh() }
    }

    deinit {
        self.timer?.invalidate()
        for observer in self.observers { NotificationCenter.default.removeObserver(observer) }
    }
}

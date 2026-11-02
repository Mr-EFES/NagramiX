// Чистая политика отпускания пальца; одинаковая для всех пропорций видео.
enum NagramiXPiPReleaseKind: Equatable {
    case cancel
    case swipe
    case drag
}

struct NagramiXPiPReleaseDecision: Equatable {
    let kind: NagramiXPiPReleaseKind
    let x: Double
    let y: Double

    func destination(travel: Double) -> Self {
        guard self.kind == .swipe, travel.isFinite, travel > 0.0 else { return self }
        let distance = (self.x * self.x + self.y * self.y).squareRoot()
        guard distance.isFinite, distance > 0.0 else { return self }
        // Бросок продолжается от точки отпускания, всегда наружу.
        let nextX = self.x + self.x / distance * travel
        let nextY = self.y + self.y / distance * travel
        guard nextX.isFinite, nextY.isFinite else { return self }
        return Self(kind: self.kind, x: nextX, y: nextY)
    }

    static func resolve(x: Double, y: Double, velocityX: Double, velocityY: Double, elapsed: Double) -> Self {
        guard x.isFinite, y.isFinite, velocityX.isFinite, velocityY.isFinite,
              elapsed.isFinite, elapsed >= 0.0 else {
            return Self(kind: .cancel, x: 0.0, y: 0.0)
        }
        let distance = (x * x + y * y).squareRoot()
        let speed = (velocityX * velocityX + velocityY * velocityY).squareRoot()
        guard distance.isFinite, speed.isFinite else {
            return Self(kind: .cancel, x: 0.0, y: 0.0)
        }
        // Время считается с касания, включая удерживание до начала движения.
        let alignedFlick = speed >= 600.0 && x * velocityX + y * velocityY > 0.0
        let quickTravel = distance >= 48.0 && distance / max(0.001, elapsed) >= 500.0
            && (speed < 600.0 || alignedFlick)
        if elapsed <= 0.35, distance >= 12.0, alignedFlick || quickTravel {
            return Self(kind: .swipe, x: x, y: y)
        }
        if distance >= 48.0 || (elapsed > 0.35 && distance >= 12.0) {
            return Self(kind: .drag, x: x, y: y)
        }
        return Self(kind: .cancel, x: 0.0, y: 0.0)
    }
}

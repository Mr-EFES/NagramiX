// Исполняется вместе с реальным NagramiXPiPReleaseDecision.swift без UIKit.
@main
struct NagramiXPiPReleaseDecisionTests {
    static func main() {
        var checks = 0
        func expect(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ time: Double,
                    _ kind: NagramiXPiPReleaseKind, _ label: String) {
            let result = NagramiXPiPReleaseDecision.resolve(x: x, y: y, velocityX: vx, velocityY: vy, elapsed: time)
            precondition(result.kind == kind, label)
            if kind != .cancel {
                precondition(result.x == x && result.y == y, "Потеря направления/координат: " + label)
            } else {
                precondition(result.x == 0.0 && result.y == 0.0, "Отмена содержит смещение: " + label)
            }
            checks += 1
        }
        // Восемь направлений: быстрый свайп и такое же движение после удерживания.
        for (x, y) in [(80.0, 0.0), (-80.0, 0.0), (0.0, 80.0), (0.0, -80.0),
                       (80.0, 80.0), (-80.0, 80.0), (80.0, -80.0), (-80.0, -80.0)] {
            expect(x, y, x * 10.0, y * 10.0, 0.15, .swipe, "Свайп")
            expect(x, y, x * 10.0, y * 10.0, 1.5, .drag, "Удерживание до движения")
            expect(x, y, 0.0, 0.0, 1.0, .drag, "Медленное перетаскивание")
            expect(x, y, 0.0, 0.0, 0.1, .swipe, "Быстрый жест с нулевой конечной скоростью")
            let source = NagramiXPiPReleaseDecision(kind: .swipe, x: x, y: y)
            let target = source.destination(travel: 1000.0)
            precondition((target.x - x) * x + (target.y - y) * y > 0.0, "Бросок вернулся назад")
            precondition(abs(target.x * y - target.y * x) < 0.0001, "Бросок изменил направление")
            if x == 0.0 { precondition(target.x == 0.0, "Появилась горизонтальная составляющая") }
            if y == 0.0 { precondition(target.y == 0.0, "Появилась вертикальная составляющая") }
            let drag = NagramiXPiPReleaseDecision(kind: .drag, x: x, y: y)
            precondition(drag.destination(travel: 1000.0) == drag, "Удерживание не осталось в точке отпускания")
            checks += 2
        }
        expect(0, 0, 0, 0, 0.1, .cancel, "Неподвижное касание")
        expect(8, 0, 2000, 0, 0.1, .cancel, "Дрожание пальца")
        expect(11.999, 0, 1000, 0, 0.1, .cancel, "До порога короткого свайпа")
        expect(12, 0, 600, 0, 0.35, .swipe, "Границы короткого свайпа")
        expect(12, 0, -1000, 0, 0.2, .cancel, "Обратный flick не бросает вправо")
        expect(20, 0, 800, 0, 1.0, .drag, "Удерживание не становится коротким свайпом")
        expect(11.999, 0, 0, 0, 1.0, .cancel, "Дрожание после удерживания")
        expect(12, 0, 0, 0, 1.0, .drag, "Короткое намеренное перетаскивание")
        expect(100, 0, -800, 0, 0.1, .drag, "Разворот в конце не бросает в обратную сторону")
        expect(47.999, 0, 0, 0, 0.3, .cancel, "Короткое медленное движение без удерживания")
        expect(48, 0, 0, 0, 1.0, .drag, "Граница перетаскивания")
        expect(100, 0, 1000, 0, 0.35001, .drag, "Удерживание дольше окна свайпа")
        expect(100, 0, 0, 0, 0.2, .swipe, "Граница средней скорости")
        expect(100, 0, 0, 0, 0.20001, .drag, "Медленное движение")
        expect(120, -60, 0, 0, 1.0, .drag, "Отпускание сохраняет обе координаты")
        for invalid in [Double.nan, Double.infinity, -Double.infinity] {
            expect(invalid, 80, 800, 0, 0.1, .cancel, "Некорректный x")
            expect(80, invalid, 800, 0, 0.1, .cancel, "Некорректный y")
            expect(80, 0, invalid, 0, 0.1, .cancel, "Некорректный vx")
            expect(80, 0, 800, invalid, 0.1, .cancel, "Некорректный vy")
            expect(80, 0, 800, 0, invalid, .cancel, "Некорректное время")
        }
        expect(80, 0, 800, 0, -1, .cancel, "Отрицательное время")
        expect(1e308, 1e308, 0, 0, 0.1, .cancel, "Переполнение расстояния")
        expect(80, 0, 1e308, 1e308, 0.1, .cancel, "Переполнение скорости")
        let far = NagramiXPiPReleaseDecision(kind: .swipe, x: 1000.0, y: 1000.0)
        let farTarget = far.destination(travel: 500.0)
        precondition(farTarget.x > far.x && farTarget.y > far.y, "Диагональ длиннее экрана вернулась назад")
        precondition(far.destination(travel: .nan) == far && far.destination(travel: -1.0) == far)
        checks += 2
        print("PASS: \(checks) проверок реальной Swift-политики отпускания; UIKit/AVKit не исполнялись")
    }
}

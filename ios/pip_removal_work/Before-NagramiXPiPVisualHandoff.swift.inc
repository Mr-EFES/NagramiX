// Coordinates presentation only. NagramiXPiPLifecycle remains the sole owner
// of playback, native success, resources and restoration completions.
final class NagramiXPiPVisualHandoff {
    private let preview: (Bool) -> Void
    private let fadeOut: (@escaping () -> Void) -> Void
    private let fadeIn: (Bool, @escaping () -> Void) -> Void
    private let dismiss: () -> Void
    private var generation = 0
    private var began = false
    private var faded = false
    private var active = false
    private var dismissed = false
    private var restoring = false

    init(preview: @escaping (Bool) -> Void,
         fadeOut: @escaping (@escaping () -> Void) -> Void,
         fadeIn: @escaping (Bool, @escaping () -> Void) -> Void,
         dismiss: @escaping () -> Void) {
        self.preview = preview; self.fadeOut = fadeOut
        self.fadeIn = fadeIn; self.dismiss = dismiss
    }

    func willStart() {
        guard !self.began, !self.restoring else { return }
        self.began = true
        self.preview(true)
        let generation = self.generation
        self.fadeOut { [weak self] in
            guard let self, self.generation == generation, !self.restoring else { return }
            self.faded = true
            self.finishIfReady()
        }
    }

    func commit() {
        guard !self.active, !self.restoring else { return }
        self.active = true
        // AVKit normally calls willStart first. A didStart-only sequence must
        // still use the same presentation path, never a second dismissal.
        self.willStart()
        self.finishIfReady()
    }

    func cancel() {
        guard !self.active, self.began else { return }
        self.generation += 1
        self.began = false; self.faded = false
        let generation = self.generation
        self.fadeIn(true) { [weak self] in
            guard let self, self.generation == generation, !self.began else { return }
            self.preview(false)
        }
    }

    func restore() {
        self.generation += 1
        self.restoring = true
        self.preview(false)
        self.fadeIn(false, {})
    }

    private func finishIfReady() {
        // didStart подтверждает завершённый системный переход. Локальная
        // fade-анимация могла прерваться поворотом; её callback не блокирует dismiss.
        guard self.active, !self.restoring, !self.dismissed else { return }
        self.dismissed = true
        self.dismiss()
        self.preview(false)
    }
}

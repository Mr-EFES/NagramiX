// Capture graph configuration and preview attachment share one serial owner.
// In particular, never call AVCaptureVideoPreviewLayer.setSession on main
// while AVFoundation may hold its session configuration locks on another queue.
let nagramiXCameraSessionQueue = DispatchQueue(label: "Camera.Session", qos: .userInitiated)

final class NagramiXCameraPreviewSession {
    let layer: AVCaptureVideoPreviewLayer
    private var session: AVCaptureSession?
    private let orientation = Atomic<AVCaptureVideoOrientation>(value: .portrait)

    init(layer: AVCaptureVideoPreviewLayer) {
        self.layer = layer
    }

    deinit {
        // Retain the native layer until it has detached, even when its UIView
        // or camera owner goes away on main. Do not capture deinitializing self.
        let layer = self.layer
        let session = self.session
        nagramiXCameraSessionQueue.async {
            if let session, layer.session === session {
                layer.session = nil
            }
        }
    }

    func bind(_ session: AVCaptureSession, automaticallyConnect: Bool) {
        nagramiXCameraSessionQueue.async { [self] in
            if automaticallyConnect {
                self.layer.session = session
            } else {
                self.layer.setSessionWithNoConnection(session)
            }
            self.session = session
        }
    }

    func detach(from session: AVCaptureSession) {
        dispatchPrecondition(condition: .onQueue(nagramiXCameraSessionQueue))
        // A delayed cleanup of an old camera must not detach a reused preview
        // that has already been bound to a newer camera on the same queue.
        guard self.session === session else { return }
        self.layer.session = nil
        self.session = nil
    }

    func invalidate() {
        nagramiXCameraSessionQueue.async { [self] in
            if let session = self.session {
                self.detach(from: session)
            }
        }
    }

    func updateOrientation(_ orientation: AVCaptureVideoOrientation) {
        nagramiXCameraSessionQueue.async { [self] in
            guard let connection = self.layer.connection, connection.isVideoOrientationSupported else { return }
            connection.videoOrientation = orientation
            let _ = self.orientation.swap(orientation)
        }
    }

    var captureOrientation: AVCaptureVideoOrientation {
        return self.orientation.with { $0 }
    }

    func setEnabled(_ enabled: Bool) {
        nagramiXCameraSessionQueue.async { [self] in
            self.layer.connection?.isEnabled = enabled
        }
    }
}


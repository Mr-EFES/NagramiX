import Foundation
import UIKit
import AVFoundation
import SwiftSignalKit
import Display
import Camera

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


final class CameraPreviewView: UIView, CameraSimplePreviewView {
    private let placeholderView = UIImageView()
    private(set) lazy var nagramiXSessionBinding = NagramiXCameraPreviewSession(layer: self.videoPreviewLayer)

    init(frame: CGRect, main: Bool, roundVideo: Bool) {
        super.init(frame: frame)
        // Establish native-layer ownership on main before attaching a session.
        _ = self.nagramiXSessionBinding

        if roundVideo {
            self.videoPreviewLayer.videoGravity = .resizeAspectFill
            self.placeholderView.contentMode = .scaleAspectFill
        } else {
            self.videoPreviewLayer.videoGravity = main ? .resizeAspectFill : .resizeAspect
            self.placeholderView.contentMode = main ? .scaleAspectFill : .scaleAspectFit
        }
        self.placeholderView.backgroundColor = .black
        self.addSubview(self.placeholderView)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override class var layerClass: AnyClass {
        return AVCaptureVideoPreviewLayer.self
    }

    var videoPreviewLayer: AVCaptureVideoPreviewLayer {
        guard let layer = self.layer as? AVCaptureVideoPreviewLayer else {
            preconditionFailure("Unexpected preview layer type")
        }
        return layer
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        self.placeholderView.frame = self.bounds.insetBy(dx: -1.0, dy: -1.0)
        self.updateOrientation()
    }

    func updateOrientation() {
        let interfaceOrientation = self.window?.windowScene?.interfaceOrientation ?? .portrait
        // The window's orientation is measured against its screen, the connection's against the body that holds the
        // camera: a quarter turn apart on iPhone Duo's inner screen.
        let screenPortrait = screenPortraitDeviceOrientationForWindow(size: self.window?.bounds.size ?? .zero)
        let videoOrientation = CameraVideoOrientation(interfaceOrientation: CameraVideoOrientation(interfaceOrientation), screenPortrait: CameraVideoOrientation(screenPortrait))
        self.nagramiXSessionBinding.updateOrientation(videoOrientation.avCaptureVideoOrientation)
        self.videoPreviewLayer.removeAllAnimations()
    }

    func setSession(_ session: AVCaptureSession, automaticallyConnect: Bool) {
        self.nagramiXSessionBinding.bind(session, automaticallyConnect: automaticallyConnect)
    }

    func invalidate() {
        self.nagramiXSessionBinding.invalidate()
    }

    var captureOrientation: AVCaptureVideoOrientation {
        return self.nagramiXSessionBinding.captureOrientation
    }

    var isEnabled: Bool = true {
        didSet {
            self.nagramiXSessionBinding.setEnabled(self.isEnabled)
        }
    }

    @available(iOS 13.0, *)
    var isPreviewing: Signal<Bool, NoError> {
        return Signal { [weak self] subscriber in
            guard let self else {
                return EmptyDisposable
            }
            subscriber.putNext(self.videoPreviewLayer.isPreviewing)
            let observer = self.videoPreviewLayer.observe(\.isPreviewing, options: [.new]) { layer, _ in
                subscriber.putNext(layer.isPreviewing)
            }
            return ActionDisposable {
                observer.invalidate()
            }
        }
        |> distinctUntilChanged
    }

    func removePlaceholder(delay: Double) {
        UIView.animate(withDuration: 0.3, delay: delay) {
            self.placeholderView.alpha = 0.0
        }
    }

    func resetPlaceholder(front: Bool) {
        let fileName = front ? "frontCameraImage.jpg" : "backCameraImage.jpg"
        let fileUrl = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(fileName)
        if let data = try? Data(contentsOf: fileUrl), let image = UIImage(data: data) {
            self.placeholderView.image = image
        } else {
            let imageName = front ? "Camera/SelfiePlaceholder" : "Camera/Placeholder"
            self.placeholderView.image = UIImage(named: imageName)
        }
        self.placeholderView.alpha = 1.0
    }

    func cameraPoint(for location: CGPoint) -> CGPoint {
        return self.videoPreviewLayer.captureDevicePointConverted(fromLayerPoint: location)
    }
}

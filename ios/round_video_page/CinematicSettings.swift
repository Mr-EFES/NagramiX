import Foundation
import NagramiXMediaSettings
import AVFoundation
import CoreMedia
import CoreVideo

public enum NagramiXCinematicCapture {
    public static func device(position: AVCaptureDevice.Position, settings: NagramiXRoundVideoSettings) -> AVCaptureDevice? {
        guard #available(iOS 26.0, *) else { return nil }
        let types: [AVCaptureDevice.DeviceType] = position == .front
            ? [.builtInTrueDepthCamera, .builtInWideAngleCamera]
            : [.builtInDualWideCamera, .builtInTripleCamera, .builtInWideAngleCamera]
        let devices = AVCaptureDevice.DiscoverySession(deviceTypes: types, mediaType: .video, position: position).devices
        // Проверяем реальные форматы всех кандидатов, а не название первой камеры.
        return devices.first { self.format(device: $0, settings: settings) != nil }
    }
    public static func format(device: AVCaptureDevice, settings: NagramiXRoundVideoSettings) -> AVCaptureDevice.Format? {
        guard #available(iOS 26.0, *) else { return nil }
        return device.formats.filter { format in
            let size = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
            let subtype = CMFormatDescriptionGetMediaSubType(format.formatDescription)
            guard format.isCinematicVideoCaptureSupported,
                  let range = format.videoFrameRateRangeForCinematicVideo else { return false }
            let fps = Double(settings.frameRate.rawValue)
            return min(size.width, size.height) >= Int32(settings.quality.rawValue)
                && (subtype == kCVPixelFormatType_420YpCbCr8BiPlanarFullRange || subtype == kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange)
                && range.minFrameRate <= fps && range.maxFrameRate >= fps
        }.min {
            let a = CMVideoFormatDescriptionGetDimensions($0.formatDescription)
            let b = CMVideoFormatDescriptionGetDimensions($1.formatDescription)
            return Int64(a.width) * Int64(a.height) < Int64(b.width) * Int64(b.height)
        }
    }
    public static func supports(_ settings: NagramiXRoundVideoSettings) -> Bool {
        return [AVCaptureDevice.Position.front, .back].allSatisfy { position in
            guard let device = self.device(position: position, settings: settings) else { return false }
            return self.format(device: device, settings: settings) != nil
        }
    }
}

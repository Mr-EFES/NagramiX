import Foundation
struct FormatDescription { let width: Int32; let height: Int32; let subtype: Int }
func CMVideoFormatDescriptionGetDimensions(_ d: FormatDescription) -> FormatDescription { d }
func CMFormatDescriptionGetMediaSubType(_ d: FormatDescription) -> Int { d.subtype }
let kCVPixelFormatType_420YpCbCr8BiPlanarFullRange = 1
let kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange = 2
class AVCaptureDevice {
 enum Position: Hashable { case front, back }
 enum DeviceType { case builtInTrueDepthCamera, builtInDualWideCamera }
 struct MediaType { static let video = MediaType() }
 struct Range { let minFrameRate: Double; let maxFrameRate: Double }
 class Format {
  let formatDescription: FormatDescription
  let isCinematicVideoCaptureSupported: Bool
  let videoFrameRateRangeForCinematicVideo: Range?
  init(_ width: Int32 = 1920, _ height: Int32 = 1080, subtype: Int = 1, supported: Bool = true, fps: Double = 30) {
   formatDescription = .init(width: width, height: height, subtype: subtype)
   isCinematicVideoCaptureSupported = supported
   videoFrameRateRangeForCinematicVideo = supported ? .init(minFrameRate: 24, maxFrameRate: fps) : nil
  }
 }
 var formats: [Format]
 init(_ formats: [Format]) { self.formats = formats }
 static var cameras: [Position: AVCaptureDevice] = [:]
 class DiscoverySession {
  var devices: [AVCaptureDevice]
  init(deviceTypes: [DeviceType], mediaType: MediaType, position: Position) {
   devices = AVCaptureDevice.cameras[position].map { [$0] } ?? []
  }
 }
}
@main struct Tests {
 static func main() {
  var tested = 0
  for quality in NagramiXRoundVideoSettings.Quality.allCases {
   for fps in NagramiXRoundVideoSettings.FrameRate.allCases {
    let value = NagramiXRoundVideoSettings(enabled: true, quality: quality, frameRate: fps, cinematic: true)
    for format in [AVCaptureDevice.Format(), .init(fps: 60), .init(supported: false), .init(3840,2160), .init(320,240), .init(subtype: 9)] {
     AVCaptureDevice.cameras = [.front: .init([format]), .back: .init([format])]
     let d = format.formatDescription
     let expected = format.isCinematicVideoCaptureSupported && d.width <= 1920 && d.height >= 640 && d.subtype == 1 && format.videoFrameRateRangeForCinematicVideo!.maxFrameRate >= Double(fps.rawValue)
     precondition(NagramiXCinematicCapture.supports(value) == expected)
     tested += 1
    }
    AVCaptureDevice.cameras = [.front: .init([.init(fps: 60)])]
    precondition(!NagramiXCinematicCapture.supports(value))
   }
  }
  print("PASS: \(tested) actual Cinematic format/FPS/NV12/size predicates; both cameras required; AVFoundation boundary only")
 }
}

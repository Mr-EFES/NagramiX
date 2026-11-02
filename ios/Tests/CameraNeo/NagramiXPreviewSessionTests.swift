import XCTest
import UIKit
import AVFoundation

// This test module compiles the actual production CameraPreviewView.swift.
// No camera permissions, physical inputs, recorder, or Metal are required.
final class NagramiXPreviewSessionTests: XCTestCase {
    private func drainCaptureQueue() {
        let drained = self.expectation(description: "Capture owner drained")
        nagramiXCameraSessionQueue.async {
            drained.fulfill()
        }
        self.wait(for: [drained], timeout: 3.0)
    }

    func testInvalidateIsQueuedWhileCaptureOwnerIsBusy() {
        XCTAssertTrue(Thread.isMainThread)
        let preview = CameraPreviewView(frame: .zero, main: true, roundVideo: true)
        let session = AVCaptureSession()
        let layer = preview.videoPreviewLayer
        preview.setSession(session, automaticallyConnect: true)
        self.drainCaptureQueue()
        XCTAssertTrue(layer.session === session)

        let entered = DispatchSemaphore(value: 0)
        let release = DispatchSemaphore(value: 0)
        nagramiXCameraSessionQueue.async {
            entered.signal()
            // A bounded gate, not an actual AVFoundation lock inversion.
            _ = release.wait(timeout: .now() + 2.0)
        }
        guard entered.wait(timeout: .now() + 2.0) == .success else {
            release.signal()
            return XCTFail("Capture owner did not enter the gate")
        }
        // Main must return without touching the session attachment. The old
        // implementation detached immediately on main and fails this check.
        preview.invalidate()
        XCTAssertTrue(layer.session === session)
        release.signal()
        self.drainCaptureQueue()
        XCTAssertNil(layer.session)
    }

    func testOldCameraCleanupDoesNotDetachReboundPreview() {
        XCTAssertTrue(Thread.isMainThread)
        let preview = CameraPreviewView(frame: .zero, main: true, roundVideo: true)
        let first = AVCaptureSession()
        let second = AVCaptureSession()
        let binding = preview.nagramiXSessionBinding
        let checked = self.expectation(description: "Stale cleanup checked")
        preview.setSession(first, automaticallyConnect: true)
        preview.setSession(second, automaticallyConnect: true)
        nagramiXCameraSessionQueue.async {
            binding.detach(from: first)
            XCTAssertTrue(binding.layer.session === second)
            binding.detach(from: second)
            XCTAssertNil(binding.layer.session)
            checked.fulfill()
        }
        self.wait(for: [checked], timeout: 3.0)
    }

    func testViewDestructionSchedulesDetachWithoutCameraOwner() {
        XCTAssertTrue(Thread.isMainThread)
        var preview: CameraPreviewView? = CameraPreviewView(frame: .zero, main: true, roundVideo: true)
        let session = AVCaptureSession()
        let layer = preview!.videoPreviewLayer
        weak var binding = preview!.nagramiXSessionBinding
        preview!.setSession(session, automaticallyConnect: true)
        self.drainCaptureQueue()
        XCTAssertTrue(layer.session === session)
        autoreleasepool {
            preview = nil
        }
        self.drainCaptureQueue()
        XCTAssertNil(binding)
        XCTAssertNil(layer.session)
    }

    func testCameraOwnerKeepsLayerAliveAfterViewDestruction() {
        XCTAssertTrue(Thread.isMainThread)
        var preview: CameraPreviewView? = CameraPreviewView(frame: .zero, main: true, roundVideo: true)
        let session = AVCaptureSession()
        let binding = preview!.nagramiXSessionBinding
        weak var layer = preview!.videoPreviewLayer
        preview!.setSession(session, automaticallyConnect: true)
        self.drainCaptureQueue()
        autoreleasepool {
            preview = nil
        }
        XCTAssertNotNil(layer)
        let detached = self.expectation(description: "Retained layer detached")
        nagramiXCameraSessionQueue.async {
            binding.detach(from: session)
            XCTAssertNil(binding.layer.session)
            detached.fulfill()
        }
        self.wait(for: [detached], timeout: 3.0)
    }
}

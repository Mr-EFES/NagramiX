"""Compile the real settings module and complete exporter with Apple Photos/UIKit."""
import subprocess
import sys
from validate_quick_format import block
from original_video_media_runtime import MEDIA, parts


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    flags = []
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        flags = ['-sdk', sdk, '-target', 'arm64-apple-ios15.0']
    command = [str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', str(folder / 'cache'), *flags]
    module = folder / 'NagramiXMediaSettings.swiftmodule'
    result = subprocess.run(command + ['-parse-as-library', '-emit-module', '-module-name', 'NagramiXMediaSettings', '-emit-module-path', str(module), str(source / MEDIA)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    caller = folder / 'settings.swift'
    caller.write_text('import NagramiXMediaSettings\nfunc readVideoMode()->Bool { NagramiXMediaSettings.current.originalVideos }\n')
    result = subprocess.run(command + ['-typecheck', '-I', str(folder), str(caller)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = {'actual_settings_module_and_import': 'passed', 'complete_exporter_apple_api': 'not_run', 'full_application_sdk': 'pending', 'physical_iphone': 'pending'}
    if sys.platform != 'darwin':
        report['reason'] = 'Linux; the full exporter runtime uses explicit Photos/UIKit/MediaBox adapters. No Apple API success claimed.'
        return report
    core, boundary, actual, _ = parts(source)
    for marker in ['public final class UIImage {', 'public final class PHAssetResource {', 'public final class PHAsset {', 'final class PHAssetResourceRequestOptions {', 'final class PHAssetResourceManager {', 'struct UTType {']:
        boundary = boundary.replace(block(boundary, marker), '', 1)
    # The entire producer/stream parser and actual SignalKit remain. Only the
    # Apple adapters are removed; Telegram media/resource/storage remain edges.
    path = folder / 'complete-exporter.swift'
    path.write_text('import UIKit\nimport Photos\nimport UniformTypeIdentifiers\n' + core + '\n' + boundary + '\n' + actual)
    result = subprocess.run(command + ['-parse-as-library', '-typecheck', str(path)], capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    report['complete_exporter_apple_api'] = 'passed arm64/iPhoneOS15; actual entire producer/parser/SignalKit with real Photos/UIKit/UTType; Telegram MediaBox/models and scaler remain explicit edges'
    return report

#!/usr/bin/env python3
"""Replay the build 229 worker layout against the real bitrate slider and cell."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from late_source_stages import ROOT
from round_bitrate_levels_runtime import G, ui_fixture
from validate_local_copy_delivery import execute, run
from validate_upstream_13_2_release import checked_plan, digest


STAGE = 'slider_main_thread_layout'
DIAGNOSTIC = 'UIKit slider layout reached a worker thread'


def fixture(source, slider_code=None):
    host = ui_fixture(source, slider_code=slider_code)
    substitutions = {
        '@main struct RoundBitrateControlTests': 'struct RoundBitrateControlTests',
        ' func setNeedsLayout(){layoutRequested=true}': '''
 func setNeedsLayout() {
    check(Thread.isMainThread, "off-main invalidation")
    layoutRequested = true
 }
''',
        ' func layoutSubviews(){}': '''
 var nativeLayoutCount = 0
 func layoutSubviews() {
    guard Thread.isMainThread else {
        FileHandle.standardError.write(Data("''' + DIAGNOSTIC + '''\\n".utf8))
        exit(91)
    }
    nativeLayoutCount += 1
 }
''',
    }
    for original, replacement in substitutions.items():
        assert host.count(original) == 1, original
        host = host.replace(original, replacement)
    return host + '\n' + (ROOT / 'scripts/tests/NagramiXSliderMainThreadLayout.swift').read_text()


def validate(source, swiftc, folder):
    plan = checked_plan(STAGE)
    for name, expected in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == expected, name
    old = (ROOT / 'ios' / plan['previous'][G]).read_text()
    release_slider = '\n'.join(line for line in old.splitlines() if not line.startswith('import '))
    results = execute(swiftc, folder, 'Build229', fixture(source, release_slider), DIAGNOSTIC)
    results += execute(swiftc, folder, 'FixedLayout', fixture(source))
    for result in results:
        print(f"{result['name']} {result['mode']} | {result['output']}", flush=True)

    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', folder / 'cache',
             '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-typecheck', source / G])
    else:
        run([swiftc, '-frontend', '-parse', source / G])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='slider-layout-') as temporary:
        validate(args.source, args.swiftc, Path(temporary))

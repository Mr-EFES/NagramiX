#!/usr/bin/env python3
"""Run upgrade and delivery checks for the installation counter starting with 1.0.4."""
import argparse
from pathlib import Path
import tempfile

from validate_installation_metrics import validate
from validate_release_095_apple_preflight import canonical_projection


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source', type=Path)
    mode.add_argument('--canonical', action='store_true')
    parser.add_argument('--swiftc', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nagramix-v2-') as tmp:
        source = args.source
        if args.canonical:
            source = Path(tmp) / 'source'
            canonical_projection(source, 'installation_metrics_v2')
        validate(source, args.swiftc, v2=True)

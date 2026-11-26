#!/usr/bin/env python3
"""Materialize the exact guarded inputs for a source-check worker or the SDK."""
import argparse
from importlib import import_module
from pathlib import Path
import sys

from validate_upstream_13_2_release import OVERLAY, SDK_STAGES

STAGES = ('upstream_13_2_post', 'upstream_13_2_release_post', *SDK_STAGES)


def apply(source, before):
    if before == 'foundation':
        return
    end = STAGES.index(before) if before else len(STAGES)
    sys.path.insert(0, str(OVERLAY))
    try:
        for stage in STAGES[:end]:
            module = import_module(stage)
            getattr(module, 'apply_' + stage)(source, OVERLAY)
    finally:
        sys.path.pop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--before', choices=('foundation', *STAGES))
    mode.add_argument('--all', action='store_true')
    args = parser.parse_args()
    apply(args.source.resolve(), args.before)

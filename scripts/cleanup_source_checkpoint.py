#!/usr/bin/env python3
"""Remove one successful validator's owned checkpoint, never the active source."""
import argparse
import os
from pathlib import Path
import shutil
import stat


CHECKPOINT_NAMES = frozenset({
    'nagramix-pre-pip',
    'nagramix-pre-temporary-interaction',
    'nagramix-pre-account-settings-entry',
    'nagramix-pre-release-090-preflight',
})


class CleanupRefused(ValueError):
    pass


def _directory_flags():
    if not shutil.rmtree.avoids_symlink_attacks or not hasattr(os, 'O_NOFOLLOW'):
        raise CleanupRefused('Safe directory-fd cleanup is unavailable')
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _check_marker(directory_fd):
    # Both marker components must belong to this checkpoint, not a symlink to
    # the live checkout. Other contained symlinks are unlinked by rmtree.
    telegram_fd = os.open('Telegram', _directory_flags(), dir_fd=directory_fd)
    try:
        marker = os.stat('BUILD', dir_fd=telegram_fd, follow_symlinks=False)
        if not stat.S_ISREG(marker.st_mode):
            raise CleanupRefused('Telegram/BUILD must be a regular checkpoint marker')
    finally:
        os.close(telegram_fd)


def cleanup_checkpoint(root: Path, name: str, active_source: Path) -> Path:
    if name not in CHECKPOINT_NAMES:
        raise CleanupRefused('Unknown checkpoint name')
    if not root.is_absolute() or '..' in root.parts or root.is_symlink():
        raise CleanupRefused('Checkpoint root must be an absolute directory')
    # Canonicalize ancestor aliases such as macOS /var -> /private/var. The
    # actual root descriptor is then opened without following a final symlink.
    root = root.resolve(strict=True)
    unsafe = {Path('/'), Path('/tmp'), Path('/var/tmp'), Path('/private'),
              Path('/private/tmp'), Path('/private/var'), Path('/private/var/tmp'),
              Path.home().resolve(), Path.cwd().resolve()}
    if len(root.parts) < 3 or root in unsafe or not root.is_dir():
        raise CleanupRefused('Unsafe checkpoint root')
    active_source = active_source.resolve(strict=True)
    if not active_source.is_dir():
        raise CleanupRefused('Active application source is missing')
    target = root / name
    if target.is_symlink() or not target.is_dir():
        raise CleanupRefused('Checkpoint must be an existing real directory')
    if (target == active_source or target.is_relative_to(active_source)
            or active_source.is_relative_to(target)):
        raise CleanupRefused('Checkpoint overlaps the active application source')
    root_fd = os.open(root, _directory_flags())
    try:
        target_fd = os.open(name, _directory_flags(), dir_fd=root_fd)
        try:
            active_fd = os.open(active_source, _directory_flags())
            try:
                _check_marker(active_fd)
                _check_marker(target_fd)
                target_stat = os.fstat(target_fd)
                active_stat = os.fstat(active_fd)
                if (target_stat.st_dev, target_stat.st_ino) == (active_stat.st_dev, active_stat.st_ino):
                    raise CleanupRefused('Checkpoint aliases the active application source')
                current = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (target_stat.st_dev, target_stat.st_ino):
                    raise CleanupRefused('Checkpoint changed during validation')
            finally:
                os.close(active_fd)
            # rmtree uses the already opened root and refuses symlink races;
            # it never follows symlinks contained within the copied tree.
            shutil.rmtree(name, dir_fd=root_fd)
        finally:
            os.close(target_fd)
    finally:
        os.close(root_fd)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--active-source', type=Path, required=True)
    args = parser.parse_args()
    try:
        removed = cleanup_checkpoint(args.root, args.name, args.active_source)
    except (CleanupRefused, OSError) as error:
        parser.exit(2, 'Checkpoint cleanup refused: ' + str(error) + '\n')
    print('Removed validated source checkpoint: ' + str(removed))


if __name__ == '__main__':
    main()

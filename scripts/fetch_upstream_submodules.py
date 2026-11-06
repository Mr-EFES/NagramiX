#!/usr/bin/env python3
"""Fetch exact13.2 dependencies with one documented unavailable-gitlink repair."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'ios/upstream_13_2_release/dependencies.json'
CALLS = 'submodules/TgVoipWebrtc/tgcalls'
UNAVAILABLE = 'c1de0882de9013df246252129b95430f48b20eec'
PUBLISHED = '38dcea121f10638c42098f226f05c298a392f95c'


def git(source, *args, capture=False):
    result = subprocess.run(['git', '-C', str(source), *args], check=True,
                            text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def load_plan():
    plan = json.loads(PLAN.read_text())
    pins = dict(line.split('=', 1) for line in (ROOT / 'ios/upstream.env').read_text().splitlines() if '=' in line)
    assert plan['target_pin'] == pins['TELEGRAM_IOS_REF'] == '24638bc69bd083981b178dd1e7f921eebbf7fc46'
    items = plan['submodules']
    assert len(items) == 12 and len({item['path'] for item in items}) == 12
    overrides = [item for item in items if item['expected_ref'] != item['checkout_ref']]
    assert len(overrides) == 1
    item = overrides[0]
    assert item['path'] == CALLS and item['expected_ref'] == UNAVAILABLE and item['checkout_ref'] == PUBLISHED
    assert item['repository'] == 'https://github.com/TelegramMessenger/tgcalls.git'
    for item in items:
        relative = Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert item['repository'].startswith('https://github.com/')
        assert len(item['checkout_ref']) == 40 and all(c in '0123456789abcdef' for c in item['checkout_ref'])
    return plan


def provenance_lines(plan):
    return [f"Dependency override: {item['path']} {item['expected_ref']} -> {item['checkout_ref']} ({item['repository']})"
            for item in plan['submodules'] if item['checkout_ref'] != item['expected_ref']]


def validate_source(source, plan):
    assert git(source, 'rev-parse', 'HEAD', capture=True) == plan['target_pin'], 'Unexpected parent source'
    assert hashlib.sha256((source / '.gitmodules').read_bytes()).hexdigest() == plan['gitmodules_sha256']
    config = configparser.ConfigParser()
    config.read(source / '.gitmodules')
    declared = {config[section]['path']: config[section]['url'] for section in config.sections()}
    tree = git(source, 'ls-tree', '-r', 'HEAD', capture=True)
    links = {}
    for line in tree.splitlines():
        metadata, path = line.split('\t', 1)
        mode, kind, sha = metadata.split()
        if mode == '160000' and kind == 'commit':
            links[path] = sha
    assert set(links) == {item['path'] for item in plan['submodules']}, 'Unexpected submodule set'
    for item in plan['submodules']:
        assert links[item['path']] == item['expected_ref'], item['path']
        assert declared[item['path']] == item['declared_url'], item['path']
        assert (source / item['path']).resolve().is_relative_to(source.resolve()), item['path']


def fetch(source, provenance):
    plan = load_plan()
    validate_source(source, plan)  # Validate every native gitlink before network or writes.
    native = [item['path'] for item in plan['submodules'] if item['checkout_ref'] == item['expected_ref']]
    git(source, 'submodule', 'sync', '--recursive')
    git(source, '-c', 'protocol.version=2', 'submodule', 'update', '--init', '--depth=1', '--recursive', '--', *native)
    for item in plan['submodules']:
        destination = source / item['path']
        if item['checkout_ref'] != item['expected_ref']:
            if not (destination / '.git').exists():
                assert not destination.exists() or not any(destination.iterdir()), 'Nonempty dependency destination'
                destination.mkdir(parents=True, exist_ok=True)
                git(destination, 'init', '--quiet')
                git(destination, 'remote', 'add', 'origin', item['repository'])
                git(destination, 'fetch', '--depth=1', 'origin', item['checkout_ref'])
                git(destination, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
            assert git(destination, 'remote', 'get-url', 'origin', capture=True) == item['repository']
        assert git(destination, 'rev-parse', 'HEAD', capture=True) == item['checkout_ref'], item['path']
        for name, expected in item.get('required_files', {}).items():
            assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected, name
    provenance.write_text('\n'.join(provenance_lines(plan)) + '\n')
    print('PASS:12 exact dependency checkouts; one explicit official tgcalls repair recorded in provenance', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    args = parser.parse_args()
    fetch(args.source, args.provenance)


if __name__ == '__main__':
    main()

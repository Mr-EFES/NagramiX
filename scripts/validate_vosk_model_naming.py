#!/usr/bin/env python3
"""Проверить утверждённое название Vosk и переводы всех 71 языка."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from validate_app_language_localization import runtime_checks, strings
from validate_localization_standard import catalog_contract, source_contract
from validate_quick_format import manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
sys.path.insert(0, str(OVERLAY))
from vosk_model_naming import apply_vosk_model_naming, KEY, PREFERENCES, ANCHOR, REPLACEMENT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    args = parser.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(args, Path(__file__), 'rich_draft_upload_retry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_transition_geometry'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'transfer_consistency'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'editor_attachment_delivery'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_size'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_effect'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'pip_visual_handoff'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'local_model_menu'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'archive_deletion_visibility'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'temporary_media_actions'):
        return
    if delegate_icon_stage_if_applied(args, Path(__file__), 'message_copy_availability'):
        return
    plan = json.loads((OVERLAY / 'vosk_model_naming_patches.json').read_text())
    labels = json.loads((OVERLAY / 'vosk_model_naming/labels.json').read_text())
    sha = lambda data: hashlib.sha256(data).hexdigest()
    for name, digest in {**plan['outputs'], **plan['guards']}.items():
        assert sha((args.source / name).read_bytes()) == digest, name
    for name, digest in plan['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name
    assert labels['ru'] == 'Альтернативная' and labels['en'] == 'Alternative'
    assert catalog_contract(args.source) == (71, 613)
    source_contract(args.source)
    preferences = (args.source / PREFERENCES).read_text()
    assert preferences == (OVERLAY / plan['previous'][PREFERENCES]).read_text().replace(ANCHOR, REPLACEMENT)
    for code, label in labels.items():
        name = f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings'
        values = strings(args.source / name)
        assert values[KEY] == label
        previous = strings(OVERLAY / plan['previous'][name])
        assert {key: value for key, value in values.items() if key != KEY} == previous
    with tempfile.TemporaryDirectory(prefix='nagramix-vosk-labels-') as folder:
        temp = Path(folder)
        def seed(label):
            tree = temp / label
            for name in {**plan['inputs'], **plan['guards']}:
                data = (OVERLAY / plan['previous'][name] if name in plan['previous'] else args.source / name).read_bytes()
                path = tree / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return tree
        valid = seed('valid')
        apply_vosk_model_naming(valid, OVERLAY)
        for name in plan['outputs']:
            assert (valid / name).read_bytes() == (args.source / name).read_bytes()
        def reject(tree):
            before = manifest(tree)
            try:
                apply_vosk_model_naming(tree, OVERLAY)
            except (SystemExit, OSError):
                pass
            else:
                raise AssertionError('Invalid Vosk naming input accepted')
            assert manifest(tree) == before, 'Partial writes'
        reject(valid)
        # A failure in the last language must not update Preferences or any catalog.
        invalid = seed('last-language')
        (invalid / next(reversed(plan['inputs']))).write_bytes(b'changed')
        reject(invalid)
        invalid = seed('missing-row')
        (invalid / PREFERENCES).unlink()
        reject(invalid)
        if args.swiftc:
            runtime_checks(args.source, args.swiftc)
    print('PASS: Vosk Alternative label; 71 × 613 keys, existing translations unchanged, atomic guards and actual Core lookup verified.')


if __name__ == '__main__':
    main()
